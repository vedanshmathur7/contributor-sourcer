"""Official GitHub REST + GraphQL client: ETag/DB caching, rate-limit waits, retries with backoff."""

import asyncio
import hashlib
import json
from datetime import UTC, datetime, timedelta

import httpx

from app.config import get_settings
from app.db import SessionLocal
from app.github.base import GitHubError, NotFound, RateLimiter, WaitCallback
from app.models import ApiCache
from app.schemas import CandidateData, Criteria, Profile, PullRequest, RepoInfo, SearchHit, SearchResult

USER_QUERY = """
query($login: String!) {
  user(login: $login) {
    login name bio location company email websiteUrl avatarUrl url
    followers { totalCount }
    pullRequests(first: 60, states: MERGED, orderBy: {field: CREATED_AT, direction: DESC}) {
      nodes {
        id number title url mergedAt additions deletions
        baseRepository {
          nameWithOwner isFork stargazerCount pushedAt
          owner { login } primaryLanguage { name } parent { nameWithOwner }
          repositoryTopics(first: 8) { nodes { topic { name } } }
        }
      }
    }
    repositories(first: 30, ownerAffiliations: OWNER, orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes {
        nameWithOwner isFork stargazerCount pushedAt
        owner { login } primaryLanguage { name } parent { nameWithOwner }
        repositoryTopics(first: 8) { nodes { topic { name } } }
      }
    }
  }
}
"""

SEARCH_ENOUGH_AUTHORS = 80
_search_limiter = RateLimiter(get_settings().search_rate_per_min, 60.0)
CACHE_TTL = timedelta(minutes=15)


def _dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _repo_from_gql(node: dict) -> RepoInfo:
    return RepoInfo(
        name_with_owner=node["nameWithOwner"],
        owner=node["owner"]["login"],
        is_fork=bool(node["isFork"]),
        parent=(node.get("parent") or {}).get("nameWithOwner"),
        stars=node.get("stargazerCount") or 0,
        primary_language=(node.get("primaryLanguage") or {}).get("name"),
        topics=[t["topic"]["name"] for t in (node.get("repositoryTopics") or {}).get("nodes", [])],
        pushed_at=_dt(node.get("pushedAt")),
    )


def build_search_queries(criteria: Criteria, since: datetime) -> list[str]:
    base = f"is:pr is:merged merged:>={since.date().isoformat()} -author:app/dependabot -author:app/renovate"
    # Most specific first (seed repos, then keyword matches), the bare language query last as a fallback.
    queries: list[str] = []
    if criteria.seed_repos:
        queries.append(base + " " + " ".join(f"repo:{r}" for r in criteria.seed_repos[:5]))
    langs = criteria.languages or [None]
    scoped = [base + (f' language:"{lang}"' if lang else "") for lang in langs[:3]]
    for q in scoped:
        for kw in criteria.keywords[:2]:
            queries.append(f'{q} "{kw}" in:title,body')
    queries.extend(scoped)
    return queries


class LiveGitHubClient:
    mode = "live"

    def __init__(self, on_wait: WaitCallback | None = None):
        s = get_settings()
        if not s.github_token:
            raise GitHubError("GITHUB_TOKEN is not configured — Live mode is unavailable, use Fixture mode.")
        self.on_wait = on_wait
        self._http = httpx.AsyncClient(
            base_url=s.github_api_url,
            timeout=s.http_timeout_s,
            headers={
                "Authorization": f"Bearer {s.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "contributor-sourcer",
            },
        )
        self.request_count = 0

    async def aclose(self) -> None:
        await self._http.aclose()

    # ---------- transport ----------

    async def _cache_get(self, key: str) -> ApiCache | None:
        async with SessionLocal() as s:
            return await s.get(ApiCache, key)

    async def _cache_put(self, key: str, body, etag: str | None) -> None:
        async with SessionLocal() as s:
            row = await s.get(ApiCache, key)
            if row is None:
                s.add(ApiCache(key=key, etag=etag, body=body, fetched_at=datetime.now(UTC)))
            else:
                row.body, row.etag, row.fetched_at = body, etag, datetime.now(UTC)
            try:
                await s.commit()
            except Exception:  # concurrent writer won the insert; the cache is best-effort
                await s.rollback()

    async def _send(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Retries 5xx/network errors with backoff; waits out rate limits (never bypasses them)."""
        delay = 1.0
        for attempt in range(5):
            try:
                self.request_count += 1
                r = await self._http.request(method, url, **kwargs)
            except httpx.TransportError as e:
                if attempt == 4:
                    raise GitHubError(f"network error: {e}") from e
                await asyncio.sleep(delay)
                delay *= 2
                continue
            # GitHub's secondary limit can arrive with neither header; its docs say wait >= 60s.
            secondary = r.status_code in (403, 429) and "secondary rate limit" in r.text.lower()
            if r.status_code in (403, 429) and (
                r.headers.get("x-ratelimit-remaining") == "0" or "retry-after" in r.headers or secondary
            ):
                if attempt == 4:
                    return r
                if "retry-after" in r.headers:
                    wait = float(r.headers["retry-after"])
                elif secondary:
                    wait = 60.0
                else:
                    reset = int(r.headers.get("x-ratelimit-reset", "0"))
                    wait = max(1.0, reset - datetime.now(UTC).timestamp() + 1)
                wait = min(wait, 120.0)
                if self.on_wait:
                    await self.on_wait(wait, "GitHub rate limit reached — waiting for reset")
                await asyncio.sleep(wait)
                continue
            if r.status_code >= 500 and attempt < 4:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            return r
        raise GitHubError(f"GitHub request failed after retries: {method} {url}")

    async def _get_json(self, path: str, params: dict | None = None, fresh: bool = False):
        key = _cache_key("GET " + path + ("?" + json.dumps(params, sort_keys=True) if params else ""))
        cached = await self._cache_get(key)
        if cached and not fresh and datetime.now(UTC) - _aware(cached.fetched_at) < CACHE_TTL:
            return cached.body
        headers = {"If-None-Match": cached.etag} if cached and cached.etag else {}
        r = await self._send("GET", path, params=params, headers=headers)
        if r.status_code == 304 and cached:
            await self._cache_put(key, cached.body, cached.etag)
            return cached.body
        if r.status_code == 404:
            raise NotFound(path)
        if r.status_code >= 400:
            raise GitHubError(f"GitHub {r.status_code} on {path}: {r.text[:200]}")
        body = r.json()
        await self._cache_put(key, body, r.headers.get("etag"))
        return body

    async def _graphql(self, query: str, variables: dict):
        key = "GQL " + hashlib.sha256((query + json.dumps(variables, sort_keys=True)).encode()).hexdigest()
        cached = await self._cache_get(key)
        if cached and datetime.now(UTC) - _aware(cached.fetched_at) < CACHE_TTL:
            return cached.body
        r = await self._send("POST", "/graphql", json={"query": query, "variables": variables})
        if r.status_code >= 400:
            raise GitHubError(f"GraphQL {r.status_code}: {r.text[:200]}")
        body = r.json()
        if body.get("errors") and not body.get("data"):
            raise GitHubError(f"GraphQL error: {body['errors'][0].get('message')}")
        await self._cache_put(key, body, None)
        return body

    # ---------- API ----------

    async def search_merged_prs(self, criteria: Criteria) -> SearchResult:
        since = criteria.window_start()
        queries = build_search_queries(criteria, since)
        hits: list[SearchHit] = []
        total = 0
        for q in queries:
            if len({h.login for h in hits}) >= SEARCH_ENOUGH_AUTHORS:
                break  # enough authors for the enrichment budget; skip broader queries
            for page in range(1, get_settings().max_search_pages + 1):
                await _search_limiter.acquire(self.on_wait)
                body = await self._get_json(
                    "/search/issues", {"q": q, "per_page": 100, "page": page, "sort": "updated", "order": "desc"}
                )
                total += body.get("total_count", 0) if page == 1 else 0
                items = body.get("items", [])
                for it in items:
                    user = it.get("user") or {}
                    repo = it["repository_url"].split("/repos/", 1)[-1]
                    hits.append(
                        SearchHit(
                            login=user.get("login", ""),
                            pr_url=it["html_url"],
                            repo=repo,
                            merged_at=_dt((it.get("pull_request") or {}).get("merged_at")),
                        )
                    )
                if len(items) < 100:
                    break
        return SearchResult(hits=hits, queries=queries, total_count=total)

    async def repo_contributors(self, repo: str, limit: int = 30) -> list[str]:
        body = await self._get_json(f"/repos/{repo}/contributors", {"per_page": limit})
        return [c["login"] for c in body if c.get("type") == "User"]

    async def get_candidate(self, login: str) -> CandidateData | None:
        if login.endswith("[bot]"):
            return CandidateData(
                profile=Profile(login=login, html_url=f"https://github.com/apps/{login[:-5]}", account_type="Bot")
            )
        body = await self._graphql(USER_QUERY, {"login": login})
        u = (body.get("data") or {}).get("user")
        if not u:
            return None
        profile = Profile(
            login=u["login"],
            name=u.get("name"),
            bio=u.get("bio"),
            location=u.get("location"),
            company=u.get("company"),
            public_email=u.get("email") or None,  # GraphQL returns "" when the email is not public
            blog=u.get("websiteUrl"),
            followers=(u.get("followers") or {}).get("totalCount", 0),
            avatar_url=u.get("avatarUrl"),
            html_url=u["url"],
        )
        prs = [
            PullRequest(
                source_id=n["id"],
                number=n["number"],
                title=n["title"],
                url=n["url"],
                merged_at=_dt(n.get("mergedAt")),
                additions=n.get("additions") or 0,
                deletions=n.get("deletions") or 0,
                author_login=u["login"],
                base_repo=_repo_from_gql(n["baseRepository"]),
            )
            for n in u["pullRequests"]["nodes"]
            if n.get("baseRepository")
        ]
        repos = [_repo_from_gql(n) for n in u["repositories"]["nodes"]]
        return CandidateData(profile=profile, pull_requests=prs, owned_repos=repos)

    async def get_pr_rest(self, repo: str, number: int) -> dict:
        return await self._get_json(f"/repos/{repo}/pulls/{number}", fresh=True)


def _cache_key(raw: str) -> str:
    return raw if len(raw) <= 200 else raw[:120] + "#" + hashlib.sha256(raw.encode()).hexdigest()


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
