"""Official test-case harness: TC1–TC4 as labelled agent runs with input, expected, actual, evidence, pass/fail.

Each case runs the real agent (vet-only mode, so discovery noise doesn't hide the case) and the verdict is
derived from what the agent actually stored. Live mode never fakes a pass: missing or changed data is recorded
as a failure or as inconclusive, with the reason.
"""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.agent import Agent
from app.config import get_settings
from app.crud import audit, load_run
from app.db import SessionLocal
from app.github.base import GitHubClient
from app.models import Candidate, Run, Step, TestRun, new_id
from app.schemas import Criteria
from app.serializers import iso

LIVE_INPUTS_PATH = Path(__file__).parent / "live_testcases.json"


@dataclass(frozen=True)
class TestCase:
    id: str
    label: str
    scenario: str
    expected: str
    fixture_login: str
    languages: tuple[str, ...] = ("Rust",)
    window_days: int = 180


CASES = [
    TestCase("TC1", "Recent merged PRs in target stack", "Developer has recent merged PRs into non-fork upstream repos in the target stack.",
             "Shortlisted with PR links", "tc1-active-rustacean"),
    TestCase("TC2", "Repository is only a fork", "Developer's activity exists only in personal forks.",
             "Not counted as contribution", "tc2-fork-only"),
    TestCase("TC3", "Last activity 3 years ago", "Developer's relevant merged PRs are ~3 years old.",
             "Excluded by recency window", "tc3-stale-dev"),
    TestCase("TC4", "No public email", "Developer qualifies but has no public email on their profile.",
             "Contact left blank, never guessed", "tc4-no-email"),
]


def live_inputs() -> dict:
    try:
        return json.loads(LIVE_INPUTS_PATH.read_text())
    except FileNotFoundError:
        return {}


def judge(tc: TestCase, cand: Candidate | None) -> tuple[bool | None, str, str]:
    """Returns (passed, actual, explanation)."""
    if cand is None:
        return None, "No candidate record produced", "The profile could not be loaded, so the case is inconclusive."
    q = [e for e in cand.evidence if e.qualifies]
    verified = [e for e in q if e.verified]
    head = cand.classification if cand.reason_code == cand.classification else f"{cand.classification} ({cand.reason_code})"
    if tc.id == "TC1":
        ok = cand.classification == "SHORTLISTED" and bool(q) and all("/pull/" in e.url for e in q)
        actual = f"{head} — {len(q)} qualifying PR link(s), {len(verified)}/{len(q)} re-verified"
        why = "" if ok else f"Expected a shortlist with PR links; agent said: {cand.reason_text}"
        if ok and len(verified) < len(q):
            why = "Shortlisted with PR links, but some PRs failed re-verification (candidate blocked for review)."
        return ok, actual, why
    if tc.id == "TC2":
        fork_ev = [e for e in cand.evidence if e.repo_is_fork]
        ok = cand.classification != "SHORTLISTED" and not any(e.qualifies for e in fork_ev)
        actual = f"{head} — {len(fork_ev)} fork item(s) seen, {sum(e.qualifies for e in fork_ev)} counted"
        why = "" if ok else f"Fork activity was counted; agent said: {cand.reason_text}"
        if ok and cand.classification != "EXCLUDED_FORK_ONLY":
            why = f"Fork work was not counted; the overall classification is {cand.classification} because: {cand.reason_text}"
        return ok, actual, why
    if tc.id == "TC3":
        ok = cand.classification == "EXCLUDED_RECENCY"
        actual = f"{head} — {cand.reason_text}"
        why = "" if ok else f"Expected exclusion by the recency window; agent said: {cand.reason_text}"
        return ok, actual, why
    # TC4
    ok = cand.contact_email is None
    actual = f"contact_email = {cand.contact_email!r}; {head}"
    why = "" if ok else "A contact value was produced although the profile has no public email."
    if ok and cand.classification != "SHORTLISTED":
        why = f"Contact correctly blank; note the candidate itself was {cand.classification}: {cand.reason_text}"
    return ok, actual, why


async def run_case(tc: TestCase, mode: str, batch_id: str, inputs: dict | None = None,
                   gh: GitHubClient | None = None, now: datetime | None = None) -> TestRun:
    settings = get_settings()
    if mode == "fixture":
        login, langs, window = tc.fixture_login, list(tc.languages), tc.window_days
    else:
        spec = (inputs or {}).get(tc.id) or live_inputs().get(tc.id) or {}
        login, langs, window = spec.get("login"), spec.get("languages") or list(tc.languages), spec.get("window_days", tc.window_days)

    base = dict(batch_id=batch_id, tc_id=tc.id, label=tc.label, mode=mode, expected=tc.expected, commit_sha=settings.commit_sha)
    if not login:
        rec = TestRun(**base, input={"scenario": tc.scenario}, actual="Not run — no live GitHub login configured for this case",
                      passed=None, explanation="Provide a real public account that matches the scenario, then re-run.", evidence={})
        async with SessionLocal() as db:
            db.add(rec)
            await db.commit()
        return rec

    criteria = Criteria(languages=langs, seed_users=[login], window_days=window, min_merged_prs=2, max_candidates=5, search=False)
    async with SessionLocal() as db:
        run = Run(mode=mode, query=f"[{tc.id}] {tc.label}", criteria=criteria.model_dump(), label=tc.id,
                  plan_notes={"planner": "test-harness", "rationale": f"{tc.id}: {tc.scenario}"})
        db.add(run)
        await db.flush()
        db.add(Step(run_id=run.id, seq=0, phase="Plan", tool="plan_criteria", status="ok",
                    inputs={"test_case": tc.id, "login": login}, summary=f"[test-harness] vet @{login} · {langs} · {window}d",
                    duration_ms=0))
        await db.commit()
        run_id = run.id

    await Agent(run_id, now=now, gh=gh).execute()

    async with SessionLocal() as db:
        run = await load_run(db, run_id)
        cand = next((c for c in run.candidates if c.login.lower() == login.lower()), None)
        passed, actual, why = judge(tc, cand)
        if run.status == "FAILED":
            passed, actual, why = None, f"Run failed: {run.error}", "Agent error — see the run trace."
        evidence = {
            "run_id": run_id,
            "candidate": None if cand is None else {
                "login": cand.login, "classification": cand.classification, "reason": cand.reason_text,
                "contact_email": cand.contact_email, "score": cand.score, "verification": cand.verification_status,
                "profile_url": (cand.profile or {}).get("html_url"), "fixture": cand.fixture,
            },
            "items": [] if cand is None else [
                {"url": e.url, "title": e.title, "repo": e.repo, "kind": e.kind, "merged_at": iso(e.merged_at),
                 "repo_is_fork": e.repo_is_fork, "qualifies": e.qualifies, "rule_checks": e.rule_checks,
                 "verified": e.verified, "verify_error": e.verify_error}
                for e in cand.evidence[:12]
            ],
            "trace": [{"phase": s.phase, "tool": s.tool, "summary": s.summary} for s in run.steps],
        }
        rec = TestRun(**base, input={"scenario": tc.scenario, "login": login, "criteria": criteria.model_dump()},
                      actual=actual, passed=passed, explanation=why, evidence=evidence, run_id=run_id)
        db.add(rec)
        await db.commit()
        return rec


async def run_all(mode: str, inputs: dict | None = None, gh_factory=None, now: datetime | None = None) -> str:
    batch_id = new_id()
    for tc in CASES:
        await run_case(tc, mode, batch_id, inputs, gh=gh_factory() if gh_factory else None, now=now)
    async with SessionLocal() as db:
        await audit(db, "testcases.run", mode=mode, batch_id=batch_id)
    return batch_id


_running: dict[str, asyncio.Task] = {}


def start_batch(mode: str, inputs: dict | None = None) -> None:
    task = asyncio.create_task(run_all(mode, inputs))
    _running[mode] = task
    task.add_done_callback(lambda _: _running.pop(mode, None))


def is_running(mode: str) -> bool:
    return mode in _running
