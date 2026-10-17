"""The agent loop.

Plan → Search → Enrich → Classify → (Adapt → Search/Enrich/Classify)* → Score → Explain → Verify → Propose
→ wait for a human → Finalise.

Every step is a recorded tool call (inputs, duration, summary, per-candidate decisions) persisted to the DB and
streamed over SSE. Keep/exclude decisions come from `rules.py`; the LLM only plans, steers discovery and writes
grounded summaries.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from app import events
from app.contact import resolve_contact
from app.crud import audit
from app.db import SessionLocal
from app.github import GitHubError, make_client
from app.github.base import GitHubClient
from app.models import Candidate, Evidence, Run, Step
from app.rules import Classification, Decision, classify
from app.schemas import CandidateData, Criteria
from app.scoring import score
from app.serializers import candidate_dict, run_summary, step_dict
from app.strategist import candidate_repos, decide
from app.summarizer import summarize
from app.verifier import verify_many

log = logging.getLogger("agent")

MAX_PASSES = 3
ENRICH_CONCURRENCY = 5
SECRET_HINTS = ("token", "key", "secret", "password", "authorization")

_tasks: set[asyncio.Task] = set()


def redact(d: dict) -> dict:
    return {k: ("•••" if any(h in k.lower() for h in SECRET_HINTS) else v) for k, v in d.items()}


class StepRecorder:
    def __init__(self, step: Step):
        self.step = step
        self.summary = ""
        self.decisions: list[dict] = []

    def decide(self, login: str, verdict: str, text: str) -> None:
        if len(self.decisions) < 300:
            self.decisions.append({"login": login, "verdict": verdict, "text": text})


class Agent:
    def __init__(self, run_id: str, now: datetime | None = None, gh: GitHubClient | None = None):
        self.run_id = run_id
        self.now = now
        self._gh = gh
        self.seq = 0
        self.candidates: dict[str, Candidate] = {}
        self.cand_evidence: dict[str, list[Evidence]] = {}
        self.data: dict[str, CandidateData] = {}
        self.decisions: dict[str, Decision] = {}
        self.examined: set[str] = set()
        self.hit_repos: list[str] = []
        self.prs_examined = 0
        self.t0 = time.perf_counter()

    # ---------- plumbing ----------

    def publish(self, event: dict) -> None:
        events.publish(self.run_id, event)

    async def on_wait(self, seconds: float, reason: str) -> None:
        self.publish({"type": "wait", "seconds": round(seconds, 1), "reason": reason})

    @asynccontextmanager
    async def step(self, phase: str, tool: str, inputs: dict, rationale: str | None = None):
        s = Step(run_id=self.run_id, seq=self.seq, phase=phase, tool=tool, status="running",
                 inputs=redact(inputs), rationale=rationale)
        self.seq += 1
        self.db.add(s)
        await self.db.commit()
        self.publish({"type": "step", "step": step_dict(s)})
        rec = StepRecorder(s)
        t0 = time.perf_counter()
        try:
            yield rec
            s.status = "ok"
        except Exception as e:
            s.status = "failed"
            s.error = str(e)[:500]
            raise
        finally:
            s.duration_ms = int((time.perf_counter() - t0) * 1000)
            s.summary = rec.summary
            s.decisions = rec.decisions
            await self.db.commit()
            self.publish({"type": "step", "step": step_dict(s)})

    async def save_stats(self, **extra) -> None:
        cl = [c.classification for c in self.candidates.values()]
        self.run.stats = {
            **(self.run.stats or {}),
            "developers_checked": len(self.examined),
            "prs_examined": self.prs_examined,
            "api_requests": getattr(self.gh, "request_count", 0),
            "shortlisted": cl.count("SHORTLISTED"),
            "excluded": sum(1 for x in cl if x.startswith("EXCLUDED")),
            "needs_review": sum(1 for c in self.candidates.values() if c.blocked),
            "insufficient": cl.count("INSUFFICIENT_EVIDENCE"),
            "elapsed_s": round(time.perf_counter() - self.t0, 1),
            **extra,
        }
        await self.db.commit()
        self.publish({"type": "run", "run": run_summary(self.run)})

    # ---------- main ----------

    async def execute(self) -> None:
        async with SessionLocal() as db:
            self.db = db
            self.run = await db.get(Run, self.run_id)
            self.seq = len((await db.execute(Step.__table__.select().where(Step.run_id == self.run_id))).all())
            self.criteria = Criteria.model_validate(self.run.criteria)
            self.run.status = "RUNNING"
            self.run.started_at = datetime.now(UTC)
            self.run.error = None
            await db.commit()
            self.publish({"type": "run", "run": run_summary(self.run)})
            try:
                self.gh = self._gh or make_client(self.run.mode, on_wait=self.on_wait)
                await self._loop()
                await self._finish()
            except Exception as e:
                log.exception("run %s failed", self.run_id)
                self.run.status = "FAILED"
                self.run.error = str(e)[:500]
                self.run.completed_at = datetime.now(UTC)
                await self.save_stats()
                await audit(db, "run.failed", run_id=self.run_id, error=self.run.error)
            finally:
                if getattr(self, "gh", None) is not None and self._gh is None:
                    await self.gh.aclose()
                self.publish({"type": "done", "status": self.run.status})

    async def _loop(self) -> None:
        c = self.criteria
        seeded: list[str] = []
        keywords_dropped = False
        target = min(c.max_candidates, 5)

        # Pass 1 discovery
        pool = await self._discover(c, seed_repos=c.seed_repos if c.search else [], seed_users=c.seed_users,
                                    search=c.search)
        seeded.extend(c.seed_repos)
        await self._enrich_and_classify(pool, pass_no=1)
        if not c.search:
            return  # vet-only: judge exactly the profiles the recruiter listed

        for pass_no in range(2, MAX_PASSES + 1):
            shortlisted = sum(1 for d in self.decisions.values() if d.classification == Classification.SHORTLISTED)
            qual_repos = [ck.pr.base_repo.name_with_owner for d in self.decisions.values() for ck in d.qualifying]
            state = {
                "pass": pass_no - 1,
                "max_passes": MAX_PASSES - 1,
                "target": target,
                "shortlisted": shortlisted,
                "examined": len(self.examined),
                "keywords": c.keywords,
                "keywords_dropped": keywords_dropped,
                "seeded": seeded,
                "candidate_repos": candidate_repos(qual_repos, self.hit_repos),
                "classification_counts": _counts(self.decisions),
            }
            async with self.step("Adapt", "adapt_search", {"pass": pass_no - 1, "shortlisted": shortlisted,
                                                           "target": target}) as rec:
                plan, source = await decide(state)
                rec.step.rationale = plan["rationale"]
                rec.summary = (
                    f"[{source}] " + ("Expand: " + ", ".join(plan["add_seed_repos"] or ["drop keyword filter"])
                                      if plan["action"] == "expand" else "Stop discovery") + f" — {plan['rationale']}"
                )
            if plan["action"] != "expand":
                break
            new_seeds = plan["add_seed_repos"]
            seeded.extend(new_seeds)
            crit = c
            if plan["drop_keywords"] and c.keywords:
                crit = c.model_copy(update={"keywords": []})
                keywords_dropped = True
            pool = await self._discover(crit, seed_repos=new_seeds, seed_users=[], search=bool(plan["drop_keywords"]))
            await self._enrich_and_classify(pool, pass_no=pass_no)

    async def _discover(self, c: Criteria, seed_repos: list[str], seed_users: list[str], search: bool = True) -> list[tuple[str, str]]:
        """Returns ordered [(login, via)] not yet examined."""
        order: dict[str, str] = {}
        for u in seed_users:
            order.setdefault(u, "seed_user")

        if search:
            async with self.step("Search", "search_merged_prs", {"languages": c.languages, "keywords": c.keywords,
                                                                 "seed_repos": c.seed_repos, "window_days": c.window_days},
                                 rationale="Start from contributions, not profiles: find merged PRs in the window.") as rec:
                try:
                    res = await self.gh.search_merged_prs(c)
                except GitHubError as e:
                    rec.summary = f"Search failed after retries: {e}. Continuing with seed sources."
                    res = None
                if res:
                    counts: dict[str, int] = {}
                    for h in res.hits:
                        if h.login:
                            counts[h.login] = counts.get(h.login, 0) + 1
                        self.hit_repos.append(h.repo)
                    for login, _ in sorted(counts.items(), key=lambda kv: -kv[1]):
                        order.setdefault(login, "search")
                    rec.step.inputs = {**rec.step.inputs, "queries": res.queries}
                    rec.summary = (f"{len(res.hits)} merged PRs by {len(counts)} authors "
                                   f"(GitHub reported {res.total_count} total matches).")

        for repo in seed_repos:
            async with self.step("Search", "repo_contributors", {"repo": repo},
                                 rationale="Mine all-time contributors of a central upstream repo.") as rec:
                try:
                    logins = await self.gh.repo_contributors(repo)
                except GitHubError as e:
                    rec.summary = f"Could not list contributors: {e}"
                    logins = []
                for login in logins:
                    order.setdefault(login, f"contributor:{repo}")
                rec.summary = rec.summary or f"{len(logins)} contributors of {repo}."

        fresh = [(login, via) for login, via in order.items() if login.lower() not in self.examined]
        return fresh

    async def _enrich_and_classify(self, pool: list[tuple[str, str]], pass_no: int) -> None:
        c = self.criteria
        budget = max(10, min(60, c.max_candidates * 3)) - len(self.examined)
        selected, skipped = pool[: max(0, budget)], pool[max(0, budget):]
        if not selected:
            return

        async with self.step("Enrich", "get_profile + get_user_prs",
                             {"pass": pass_no, "developers": len(selected)},
                             rationale="Fetch each profile and its merged PRs (with base-repo fork status).") as rec:
            sem = asyncio.Semaphore(ENRICH_CONCURRENCY)

            async def fetch(login: str):
                async with sem:
                    try:
                        return login, await self.gh.get_candidate(login), None
                    except Exception as e:
                        return login, None, str(e)

            results = await asyncio.gather(*(fetch(login) for login, _ in selected))
            ok = 0
            for (login, via), (_, data, err) in zip(selected, results, strict=True):
                self.examined.add(login.lower())
                if data is None:
                    await self._record_unfetchable(login, via, err)
                    rec.decide(login, "INSUFFICIENT_EVIDENCE", err or "Profile not found (deleted, renamed or an organisation).")
                    continue
                self.data[login.lower()] = data
                self.prs_examined += len(data.pull_requests)
                ok += 1
            rec.summary = f"Enriched {ok}/{len(selected)} developers; {sum(len(self.data[k].pull_requests) for k in self.data)} PRs in scope so far."
            if skipped:
                rec.summary += f" {len(skipped)} more authors not examined (enrichment budget)."
                for login, via in skipped[:50]:
                    rec.decide(login, "NOT_EXAMINED", f"Found via {via}; outside this run's enrichment budget.")

        async with self.step("Classify", "check_repo + classify_candidate", {"pass": pass_no},
                             rationale="Apply deterministic rules: merged, in window, non-fork upstream, not own repo, stack match.") as rec:
            for login, via in selected:
                data = self.data.get(login.lower())
                if data is None:
                    continue
                d = classify(data, c, self.now)
                self.decisions[login.lower()] = d
                cand = await self._persist_candidate(data, d, via)
                rec.decide(data.profile.login, d.classification.value, d.reason_text)
                self.publish({"type": "candidate", "candidate": candidate_dict(cand, self.cand_evidence[cand.id])})
            counts = _counts({k: self.decisions[k.lower()] for k, _ in selected if k.lower() in self.decisions})
            rec.summary = ", ".join(f"{v} {k.lower().replace('_', ' ')}" for k, v in counts.items()) or "nothing to classify"
        await self.save_stats()

    async def _record_unfetchable(self, login: str, via: str, err: str | None) -> None:
        cand = Candidate(
            run_id=self.run_id, login=login, profile={"login": login, "html_url": f"https://github.com/{login}", "via": via},
            contact_email=None, classification="INSUFFICIENT_EVIDENCE", reason_code="FETCH_FAILED",
            reason_text=f"Could not load this profile: {err or 'not found (deleted, renamed or an organisation)'}.",
            fixture=self.run.mode == "fixture",
        )
        self.db.add(cand)
        await self.db.commit()
        self.candidates[login.lower()] = cand
        self.cand_evidence[cand.id] = []
        self.publish({"type": "candidate", "candidate": candidate_dict(cand, [])})

    async def _persist_candidate(self, data: CandidateData, d: Decision, via: str) -> Candidate:
        p = data.profile
        cand = Candidate(
            run_id=self.run_id,
            login=p.login,
            profile={**p.model_dump(exclude={"public_email"}), "via": via, "location_match": d.location_match},
            contact_email=resolve_contact(p),
            classification=d.classification.value,
            reason_code=d.reason_code,
            reason_text=d.reason_text,
            fixture=data.fixture,
        )
        self.db.add(cand)
        await self.db.flush()
        ev: list[Evidence] = []
        checks = sorted(d.pr_checks, key=lambda ck: ck.pr.merged_at or datetime.min.replace(tzinfo=UTC), reverse=True)
        for ck in checks[:40]:
            pr = ck.pr
            ev.append(Evidence(
                candidate_id=cand.id, kind=ck.kind, url=pr.url, title=pr.title, repo=pr.base_repo.name_with_owner,
                repo_stars=pr.base_repo.stars, repo_is_fork=pr.base_repo.is_fork, repo_language=pr.base_repo.primary_language,
                merged_at=pr.merged_at, additions=pr.additions, deletions=pr.deletions, qualifies=ck.qualifies,
                rule_checks=ck.checks, source_id=pr.source_id,
            ))
        for r in d.fork_repos:
            ev.append(Evidence(
                candidate_id=cand.id, kind="fork_repo", url=f"https://github.com/{r.name_with_owner}",
                title=f"Fork of {r.parent or 'unknown'} — last push", repo=r.name_with_owner, repo_stars=r.stars,
                repo_is_fork=True, repo_language=r.primary_language, merged_at=r.pushed_at, qualifies=False,
                rule_checks={"base_not_fork": False}, source_id=r.name_with_owner,
            ))
        self.db.add_all(ev)
        await self.db.commit()
        self.candidates[p.login.lower()] = cand
        self.cand_evidence[cand.id] = ev
        return cand

    async def _finish(self) -> None:
        c = self.criteria
        shortlisted = [x for x in self.candidates.values() if x.classification == "SHORTLISTED"]

        async with self.step("Score", "score_candidate", {"candidates": len(self.decisions)},
                             rationale="Deterministic evidence score: volume, recency, repo significance, diversity, size.") as rec:
            for login, d in self.decisions.items():
                cand = self.candidates[login]
                cand.score, cand.score_breakdown = score(d, c, self.now)
            await self.db.commit()
            top = sorted(shortlisted, key=lambda x: -x.score)[:3]
            rec.summary = "Top: " + ", ".join(f"@{x.login} {x.score:.0f}" for x in top) if top else "No shortlisted candidates to score."
            for x in sorted(shortlisted, key=lambda x: -x.score):
                rec.decide(x.login, "SCORED", f"{x.score:.1f}/100")

        if shortlisted:
            async with self.step("Explain", "summarize_evidence", {"candidates": len(shortlisted)},
                                 rationale="LLM writes 'why this person' from evidence JSON only; uncited URLs are stripped.") as rec:
                sem = asyncio.Semaphore(4)
                sources: set[str] = set()

                async def explain(cand: Candidate):
                    ev = [e for e in self.cand_evidence[cand.id] if e.qualifies]
                    payload = {
                        "login": cand.login, "window_days": c.window_days, "target_stack": c.languages + c.keywords,
                        "qualifying_prs": [{"url": e.url, "title": e.title, "repo": e.repo, "repo_stars": e.repo_stars,
                                            "merged_at": e.merged_at.isoformat(), "lines_changed": e.additions + e.deletions}
                                           for e in ev],
                    }
                    async with sem:
                        return cand, await summarize(payload)

                for cand, (text, cites, src) in await asyncio.gather(*(explain(x) for x in shortlisted)):
                    cand.summary, cand.summary_citations = text, cites
                    sources.add(src)
                    rec.decide(cand.login, "EXPLAINED", f"{len(cites)} citation(s) ({src})")
                await self.db.commit()
                rec.summary = f"Wrote {len(shortlisted)} grounded summaries via {', '.join(sorted(sources))}."

        async with self.step("Verify", "verify_evidence", {"candidates": len(shortlisted)},
                             rationale="Independent re-check: re-fetch every cited PR via REST and compare.") as rec:
            items = [(e.url, x.login) for x in shortlisted for e in self.cand_evidence[x.id] if e.qualifies]
            results, at = await verify_many(self.gh, items, c.window_start(self.now))
            n_ok = 0
            for x in shortlisted:
                rows = [e for e in self.cand_evidence[x.id] if e.qualifies]
                failed = []
                for e in rows:
                    r = results[e.url]
                    e.verified, e.verified_at, e.observed, e.verify_error = r.verified, at, r.observed, r.error
                    n_ok += r.verified
                    if not r.verified:
                        failed.append(e)
                if failed:
                    x.verification_status, x.blocked = "failed", True
                    rec.decide(x.login, "VERIFY_FAILED",
                               f"{len(failed)}/{len(rows)} cited PR(s) failed re-verification: {failed[0].verify_error}. Blocked until reviewed.")
                else:
                    x.verification_status = "verified"
                    rec.decide(x.login, "VERIFIED", f"All {len(rows)} cited PR(s) re-verified.")
                self.publish({"type": "candidate", "candidate": candidate_dict(x, self.cand_evidence[x.id])})
            await self.db.commit()
            rec.summary = f"{n_ok}/{len(items)} cited PRs re-verified; {sum(x.blocked for x in shortlisted)} candidate(s) blocked for review."

        async with self.step("Propose", "propose_shortlist", {"max_candidates": c.max_candidates},
                             rationale="Draft only — nothing is final until a human approves.") as rec:
            ranked = sorted(shortlisted, key=lambda x: -x.score)
            for i, x in enumerate(ranked):
                if i >= c.max_candidates:
                    x.review_decision, x.review_note = "rejected", f"Outside the top-{c.max_candidates} cap for this run."
                    rec.decide(x.login, "OVER_CAP", x.review_note)
            self.run.status = "PENDING_APPROVAL"
            self.run.completed_at = datetime.now(UTC)
            await self.db.commit()
            in_draft = min(len(ranked), c.max_candidates)
            rec.summary = f"Draft shortlist of {in_draft} awaiting human approval ({sum(x.blocked for x in ranked[:in_draft])} need review)."
        await self.save_stats()
        await audit(self.db, "run.proposed", run_id=self.run_id, shortlisted=len(shortlisted))


def _counts(decisions: dict[str, Decision]) -> dict[str, int]:
    out: dict[str, int] = {}
    for d in decisions.values():
        out[d.classification.value] = out.get(d.classification.value, 0) + 1
    return out


async def claim_inline(run_id: str) -> bool:
    """Atomically claim a RUNNING run that nobody has started yet (serverless inline mode)."""
    from sqlalchemy import update

    async with SessionLocal() as db:
        res = await db.execute(
            update(Run).where(Run.id == run_id, Run.status == "RUNNING", Run.started_at.is_(None))
            .values(started_at=datetime.now(UTC))
        )
        await db.commit()
        return res.rowcount == 1


def start_run(run_id: str) -> asyncio.Task:
    task = asyncio.create_task(Agent(run_id).execute())
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return task
