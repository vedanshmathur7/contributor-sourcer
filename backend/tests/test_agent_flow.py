"""Integration: the full agent loop on fixtures — plan, discover, adapt, classify, score, explain, verify, propose."""

from datetime import UTC, datetime

from app.agent import Agent
from app.crud import load_run
from app.db import SessionLocal
from app.github.fixture import FixtureGitHubClient
from app.planner import heuristic_plan
from app.routers.runs import PlanRequest, create_planned_run
from app.summarizer import ground

NOW = datetime(2026, 10, 17, tzinfo=UTC)


def test_heuristic_planner():
    c, why = heuristic_plan("Rust async networking devs, active in last 6 months, at least 3 merged PRs, in India, vet @tc3-stale-dev")
    assert c.languages == ["Rust"]
    assert "async" in c.keywords and "networking" in c.keywords
    assert c.window_days == 180 and c.min_merged_prs == 3
    assert c.location == "India" and c.seed_users == ["tc3-stale-dev"]
    assert "180 days" in why
    assert heuristic_plan("Go devs, India preferred")[0].location == "India"


def test_ground_strips_unknown_urls():
    allowed = {"https://github.com/a/b/pull/1"}
    text, cites = ground("Great work (https://github.com/a/b/pull/1) and (https://evil.example/x).",
                         ["https://github.com/a/b/pull/1", "https://made.up/2"], allowed)
    assert "evil.example" not in text and cites == ["https://github.com/a/b/pull/1"]


async def _run(query: str, **overrides):
    async with SessionLocal() as db:
        run = await create_planned_run(db, PlanRequest(query=query, mode="fixture", overrides=overrides or None))
    await Agent(run.id, now=NOW, gh=FixtureGitHubClient(now=NOW)).execute()
    async with SessionLocal() as db:
        return await load_run(db, run.id)


async def test_full_fixture_run_end_to_end(client):
    run = await _run("Rust async developers active in the last 6 months")
    assert run.status == "PENDING_APPROVAL", run.error
    by_login = {c.login: c for c in run.candidates}

    # TC1 — shortlisted with PR links, verified
    tc1 = by_login["tc1-active-rustacean"]
    assert tc1.classification == "SHORTLISTED" and tc1.verification_status == "verified"
    assert all("/pull/" in e.url for e in tc1.evidence if e.qualifies)
    assert tc1.summary and all(u in {e.url for e in tc1.evidence} for u in tc1.summary_citations)

    # TC2 — fork-only, never counted
    assert by_login["tc2-fork-only"].classification == "EXCLUDED_FORK_ONLY"
    assert not any(e.qualifies for e in by_login["tc2-fork-only"].evidence)

    # TC3 — discovered by the agent's adaptive step (seed-repo contributors) and excluded by recency
    assert by_login["tc3-stale-dev"].classification == "EXCLUDED_RECENCY"
    assert any(s.tool == "adapt_search" for s in run.steps)

    # TC4 — qualifies, contact blank
    tc4 = by_login["tc4-no-email"]
    assert tc4.classification == "SHORTLISTED" and tc4.contact_email is None

    # Verifier catches a PR whose repo vanished; candidate blocked from approval
    ghost = by_login["synth-vanishing-repo"]
    assert ghost.verification_status == "failed" and ghost.blocked

    assert by_login["reactor-ci-bot[bot]"].classification == "EXCLUDED_BOT"
    phases = [s.phase for s in run.steps]
    for p in ["Plan", "Search", "Enrich", "Classify", "Adapt", "Score", "Explain", "Verify", "Propose"]:
        assert p in phases
    assert all(s.status == "ok" for s in run.steps)
    assert run.stats["developers_checked"] >= 8 and run.stats["prs_examined"] > 20


async def test_vet_specific_profiles(client):
    run = await _run("", languages=["Rust"], seed_users=["tc3-stale-dev", "tc4-no-email"], window_days=180)
    by_login = {c.login: c for c in run.candidates}
    assert by_login["tc3-stale-dev"].classification == "EXCLUDED_RECENCY"
    assert by_login["tc4-no-email"].contact_email is None


async def test_api_plan_start_and_get(client):
    r = await client.post("/api/runs/plan", json={"query": "TypeScript react devs, last 90 days", "mode": "fixture"})
    assert r.status_code == 200
    run = r.json()
    assert run["status"] == "PLANNED" and run["criteria"]["languages"] == ["TypeScript"]
    assert run["steps"][0]["tool"] == "plan_criteria"

    r = await client.patch(f"/api/runs/{run['id']}/criteria", json={"criteria": {**run["criteria"], "min_merged_prs": 1}})
    assert r.json()["criteria"]["min_merged_prs"] == 1

    r = await client.post("/api/runs/plan", json={"query": "x", "mode": "live"})
    assert r.status_code == 400 and "GITHUB_TOKEN" in r.json()["detail"]


async def test_sse_snapshot_for_planned_run(client):
    r = await client.post("/api/runs/plan", json={"query": "Rust", "mode": "fixture"})
    rid = r.json()["id"]
    async with client.stream("GET", f"/api/runs/{rid}/events") as s:
        body = ""
        async for chunk in s.aiter_text():
            body += chunk
    assert "event: snapshot" in body and "event: done" in body


async def test_inline_mode_runs_agent_inside_sse_request(client, monkeypatch):
    """Serverless mode: /start does not spawn a task; the SSE request claims and executes the run."""
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "run_inline", True)
    rid = (await client.post("/api/runs/plan", json={"query": "Rust async, last 6 months", "mode": "fixture"})).json()["id"]
    await client.post(f"/api/runs/{rid}/start")
    assert (await client.get(f"/api/runs/{rid}")).json()["status"] == "RUNNING"
    body = ""
    async with client.stream("GET", f"/api/runs/{rid}/events") as s:
        async for chunk in s.aiter_text():
            body += chunk
    assert "event: step" in body and "event: done" in body
    assert (await client.get(f"/api/runs/{rid}")).json()["status"] == "PENDING_APPROVAL"
    # A second stream must not re-run it
    async with client.stream("GET", f"/api/runs/{rid}/events") as s:
        second = "".join([c async for c in s.aiter_text()])
    assert "event: step" not in second
