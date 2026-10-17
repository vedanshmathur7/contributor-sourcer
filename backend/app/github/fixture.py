"""Offline client backed by a synthetic, GitHub-shaped world (fixtures/world.json).

It mirrors the live client's semantics — search only sees merged PRs inside the window, contributor lists
are all-time, REST reads come from a separate path — so the same agent code runs on both.
"""

import asyncio
import json
import random
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path

from app.config import get_settings
from app.github.base import NotFound
from app.schemas import CandidateData, Criteria, Profile, PullRequest, RepoInfo, SearchHit, SearchResult

WORLD_PATH = Path(__file__).parent / "fixtures" / "world.json"


@lru_cache
def load_world() -> dict:
    return json.loads(WORLD_PATH.read_text())


def pr_url(repo: str, number: int) -> str:
    return f"https://github.com/{repo}/pull/{number}"


class FixtureGitHubClient:
    mode = "fixture"

    def __init__(self, now: datetime | None = None):
        self.now = now or datetime.now(UTC)
        self.world = load_world()
        self.request_count = 0
        self._users = {u["login"].lower(): u for u in self.world["users"]}

    async def aclose(self) -> None:
        return None

    async def _latency(self, scale: float = 1.0) -> None:
        self.request_count += 1
        ms = get_settings().fixture_latency_ms
        if ms:
            await asyncio.sleep(ms * scale * random.uniform(0.6, 1.4) / 1000)

    def _ago(self, days: int | None) -> datetime | None:
        return None if days is None else self.now - timedelta(days=days)

    def _repo(self, name: str, owner_user: dict | None = None) -> RepoInfo:
        meta = dict(self.world["repos"].get(name, {}))
        if owner_user:
            for r in owner_user.get("repos", []):
                if r["name_with_owner"] == name:
                    meta = {**meta, **r}
        else:
            owner = name.split("/")[0].lower()
            for r in self._users.get(owner, {}).get("repos", []):
                if r["name_with_owner"] == name:
                    meta = {**meta, **r}
        return RepoInfo(
            name_with_owner=name,
            owner=name.split("/")[0],
            is_fork=bool(meta.get("is_fork", False)),
            parent=meta.get("parent"),
            stars=meta.get("stars", 0),
            primary_language=meta.get("primary_language"),
            topics=meta.get("topics", []),
            pushed_at=self._ago(meta.get("pushed_days_ago")),
        )

    def _all_prs(self):
        for u in self.world["users"]:
            for p in u["prs"]:
                yield u, p

    async def search_merged_prs(self, criteria: Criteria) -> SearchResult:
        await self._latency(3)
        since = criteria.window_start(self.now)
        langs = {lang.lower() for lang in criteria.languages}
        kws = [k.lower() for k in criteria.keywords]
        seeds = {r.lower() for r in criteria.seed_repos}
        hits: list[SearchHit] = []
        for u, p in self._all_prs():
            merged = self._ago(p["merged_days_ago"])
            if merged is None or merged < since:
                continue  # GitHub search: merged:>=window_start
            repo = self._repo(p["repo"])
            lang_ok = not langs or (repo.primary_language or "").lower() in langs
            kw_ok = bool(kws) and any(k in p["title"].lower() for k in kws)
            seed_ok = p["repo"].lower() in seeds
            if lang_ok or kw_ok or seed_ok:
                hits.append(SearchHit(login=u["login"], pr_url=pr_url(p["repo"], p["number"]), repo=p["repo"], merged_at=merged))
        queries = [f"[fixture] is:pr is:merged merged:>={since.date().isoformat()} language:{'|'.join(criteria.languages) or '*'}"]
        return SearchResult(hits=hits, queries=queries, total_count=len(hits))

    async def repo_contributors(self, repo: str, limit: int = 30) -> list[str]:
        await self._latency(1)
        return [c for c in self.world["contributors"].get(repo, []) if not c.endswith("[bot]")][:limit]

    async def get_candidate(self, login: str) -> CandidateData | None:
        await self._latency(2)
        u = self._users.get(login.lower())
        if not u:
            return None
        is_bot = u.get("type") == "Bot" or login.endswith("[bot]")
        profile = Profile(
            login=u["login"],
            name=u.get("name"),
            bio=u.get("bio"),
            location=u.get("location"),
            company=u.get("company"),
            public_email=u.get("email") or None,
            blog=u.get("blog"),
            followers=u.get("followers", 0),
            avatar_url=None,
            html_url=f"https://github.com/apps/{u['login'][:-5]}" if is_bot else f"https://github.com/{u['login']}",
            account_type="Bot" if is_bot else "User",
        )
        prs = [
            PullRequest(
                source_id=f"fixture:{p['repo']}#{p['number']}",
                number=p["number"],
                title=p["title"],
                url=pr_url(p["repo"], p["number"]),
                merged_at=self._ago(p["merged_days_ago"]),
                additions=p.get("additions", 0),
                deletions=p.get("deletions", 0),
                author_login=u["login"],
                base_repo=self._repo(p["repo"]),
            )
            for p in u["prs"]
        ]
        owned = [self._repo(r["name_with_owner"], owner_user=u) for r in u.get("repos", [])]
        return CandidateData(profile=profile, pull_requests=prs, owned_repos=owned, fixture=True)

    async def get_pr_rest(self, repo: str, number: int) -> dict:
        """REST-shaped read that goes through a separate path from search/enrich (incl. overrides)."""
        await self._latency(1)
        override = self.world.get("rest_overrides", {}).get(f"{repo}#{number}")
        if override and override.get("status") == 404:
            raise NotFound(override.get("reason", "not found"))
        for u, p in self._all_prs():
            if p["repo"] == repo and p["number"] == number:
                base = self._repo(repo)
                merged = self._ago(p["merged_days_ago"])
                return {
                    "html_url": pr_url(repo, number),
                    "number": number,
                    "state": "closed",
                    "merged_at": merged.isoformat().replace("+00:00", "Z") if merged else None,
                    "user": {"login": u["login"]},
                    "base": {"repo": {"full_name": repo, "fork": base.is_fork, "owner": {"login": base.owner}}},
                }
        raise NotFound(f"{repo}#{number}")

    def raw_record(self, repo: str, number: int) -> dict | None:
        for u, p in self._all_prs():
            if p["repo"] == repo and p["number"] == number:
                return {"author": u["login"], "pr": p, "repo": self.world["repos"].get(repo)}
        return None
