from datetime import UTC, datetime

import httpx
import pytest
import respx

from app.github.base import NotFound, RateLimiter
from app.github.fixture import FixtureGitHubClient
from app.github.live import build_search_queries
from app.schemas import Criteria

NOW = datetime(2026, 10, 17, tzinfo=UTC)


async def test_fixture_search_respects_window():
    gh = FixtureGitHubClient(now=NOW)
    res = await gh.search_merged_prs(Criteria(languages=["Rust"], window_days=180))
    logins = {h.login for h in res.hits}
    assert "tc1-active-rustacean" in logins
    assert "tc3-stale-dev" not in logins  # 3-year-old PRs never appear in a windowed search
    assert all(h.merged_at >= Criteria(window_days=180).window_start(NOW) for h in res.hits)


async def test_fixture_contributors_include_stale_devs_but_not_bots():
    gh = FixtureGitHubClient(now=NOW)
    contributors = await gh.repo_contributors("asyncforge/reactor")
    assert "tc3-stale-dev" in contributors
    assert not any(c.endswith("[bot]") for c in contributors)


async def test_fixture_candidate_shapes():
    gh = FixtureGitHubClient(now=NOW)
    fork = await gh.get_candidate("tc2-fork-only")
    assert fork and all(pr.base_repo.is_fork for pr in fork.pull_requests)
    no_email = await gh.get_candidate("tc4-no-email")
    assert no_email.profile.public_email is None
    assert await gh.get_candidate("does-not-exist") is None


async def test_fixture_rest_override_404():
    gh = FixtureGitHubClient(now=NOW)
    with pytest.raises(NotFound):
        await gh.get_pr_rest("ghostwire/fastpath", 14)
    ok = await gh.get_pr_rest("asyncforge/reactor", 4821)
    assert ok["user"]["login"] == "tc1-active-rustacean" and ok["merged_at"]


def test_search_queries_exclude_bots_and_use_window():
    c = Criteria(languages=["Rust"], keywords=["async"], seed_repos=["a/b"], window_days=30)
    qs = build_search_queries(c, NOW)
    assert all("is:pr is:merged merged:>=2026-10-17" in q for q in qs)
    assert all("-author:app/dependabot" in q for q in qs)
    assert any('language:"Rust"' in q for q in qs) and any("repo:a/b" in q for q in qs)


async def test_rate_limiter_waits_and_reports():
    waits: list[float] = []

    async def on_wait(sec, reason):
        waits.append(sec)

    rl = RateLimiter(rate=2, per=0.2)
    for _ in range(3):
        await rl.acquire(on_wait)
    assert len(waits) == 1 and 0 < waits[0] <= 0.3


@respx.mock
async def test_live_client_etag_and_rate_limit(monkeypatch):
    from app.config import get_settings
    from app.db import init_db
    from app.github import live

    await init_db()
    monkeypatch.setattr(get_settings(), "github_token", "test-token")
    waits: list[float] = []

    async def on_wait(sec, reason):
        waits.append(sec)

    monkeypatch.setattr(live.asyncio, "sleep", _no_sleep)
    route = respx.get("https://api.github.com/repos/o/r/pulls/1").mock(
        side_effect=[
            httpx.Response(403, headers={"x-ratelimit-remaining": "0", "retry-after": "3"}),
            httpx.Response(200, json={"merged_at": "2026-10-01T00:00:00Z"}, headers={"etag": '"abc"'}),
            httpx.Response(304),
        ]
    )
    gh = live.LiveGitHubClient(on_wait=on_wait)
    first = await gh.get_pr_rest("o/r", 1)
    second = await gh.get_pr_rest("o/r", 1)  # fresh=True -> conditional request -> 304 -> cached body
    await gh.aclose()
    assert first == second == {"merged_at": "2026-10-01T00:00:00Z"}
    assert waits == [3.0]
    assert route.calls[-1].request.headers["if-none-match"] == '"abc"'


async def _no_sleep(_):
    return None


@respx.mock
async def test_live_client_waits_out_secondary_rate_limit(monkeypatch):
    from app.config import get_settings
    from app.db import init_db
    from app.github import live

    await init_db()
    monkeypatch.setattr(get_settings(), "github_token", "test-token")
    waits: list[float] = []

    async def on_wait(sec, reason):
        waits.append(sec)

    monkeypatch.setattr(live.asyncio, "sleep", _no_sleep)
    respx.get("https://api.github.com/repos/o/r/pulls/2").mock(
        side_effect=[
            httpx.Response(403, json={"message": "You have exceeded a secondary rate limit."}),
            httpx.Response(200, json={"merged_at": "2026-10-02T00:00:00Z"}),
        ]
    )
    gh = live.LiveGitHubClient(on_wait=on_wait)
    body = await gh.get_pr_rest("o/r", 2)
    await gh.aclose()
    assert body == {"merged_at": "2026-10-02T00:00:00Z"}
    assert waits == [60.0]
