"""Human approval gate: nothing is final without explicit approval; blocked evidence needs an override; undo until export."""

from datetime import UTC, datetime

from app.agent import Agent
from app.db import SessionLocal
from app.github.fixture import FixtureGitHubClient
from app.routers.runs import PlanRequest, create_planned_run

NOW = datetime(2026, 10, 17, tzinfo=UTC)


async def _pending_run() -> str:
    async with SessionLocal() as db:
        run = await create_planned_run(db, PlanRequest(query="Rust async devs last 6 months", mode="fixture"))
    await Agent(run.id, now=NOW, gh=FixtureGitHubClient(now=NOW)).execute()
    return run.id


async def test_approval_lifecycle(client):
    rid = await _pending_run()
    run = (await client.get(f"/api/runs/{rid}")).json()
    assert run["status"] == "PENDING_APPROVAL"
    cands = {c["login"]: c for c in run["candidates"]}

    # Export / share are impossible before finalisation
    assert (await client.get(f"/api/runs/{rid}/export")).status_code == 409
    assert (await client.post(f"/api/runs/{rid}/share")).status_code == 409
    # Finalising with zero approvals is refused
    assert (await client.post(f"/api/runs/{rid}/finalise", json={"approver": "Riya"})).status_code == 422

    # Excluded candidates can't be reviewed into the shortlist
    tc2 = cands["tc2-fork-only"]
    assert (await client.post(f"/api/runs/{rid}/candidates/{tc2['id']}/review", json={"decision": "approved"})).status_code == 404

    # Blocked (verification failed) needs an explicit override + note
    ghost = cands["synth-vanishing-repo"]
    url = f"/api/runs/{rid}/candidates/{ghost['id']}/review"
    assert (await client.post(url, json={"decision": "approved"})).status_code == 422
    assert (await client.post(url, json={"decision": "rejected", "note": "evidence repo deleted"})).status_code == 200

    for login in ["tc1-active-rustacean", "tc4-no-email", "synth-kernel-hacker"]:
        r = await client.post(f"/api/runs/{rid}/candidates/{cands[login]['id']}/review",
                              json={"decision": "approved", "reviewer": "Riya"})
        assert r.json()["review_decision"] == "approved"

    prop = (await client.get(f"/api/runs/{rid}/proposal")).json()
    assert set(prop["approve"]) == {"tc1-active-rustacean", "tc4-no-email", "synth-kernel-hacker"}
    assert prop["reject"] == ["synth-vanishing-repo"]

    r = await client.post(f"/api/runs/{rid}/finalise", json={"approver": "Riya", "note": "Looks good"})
    assert r.json()["status"] == "FINALISED" and r.json()["approver"] == "Riya"
    again = await client.post(f"/api/runs/{rid}/finalise", json={"approver": "Riya"})
    assert again.json()["already_finalised"] is True  # idempotent

    # Undo is available until export
    assert (await client.post(f"/api/runs/{rid}/undo")).json()["status"] == "PENDING_APPROVAL"
    await client.post(f"/api/runs/{rid}/finalise", json={"approver": "Riya"})

    share = (await client.post(f"/api/runs/{rid}/share")).json()["token"]
    public = (await client.get(f"/api/share/{share}")).json()
    assert {c["login"] for c in public["candidates"]} == set(prop["approve"])
    assert "share_token" not in public["run"]

    csv = await client.get(f"/api/runs/{rid}/export?format=csv")
    assert csv.status_code == 200 and "tc4-no-email" in csv.text
    tc4_line = next(line for line in csv.text.splitlines() if "tc4-no-email" in line)
    assert "not public (never guessed)" in tc4_line and "@" not in tc4_line.split(",")[4]
    assert (await client.get(f"/api/runs/{rid}")).json()["status"] == "EXPORTED"
    assert (await client.post(f"/api/runs/{rid}/undo")).status_code == 409

    actions = [a["action"] for a in (await client.get(f"/api/audit?run_id={rid}")).json()]
    for a in ["run.planned", "run.proposed", "candidate.reviewed", "run.finalised", "run.finalise_undone", "run.exported", "run.shared"]:
        assert a in actions
    assert actions.count("run.finalised") == 2  # idempotent retry did not add a third


async def test_delete_run(client):
    rid = await _pending_run()
    assert (await client.delete(f"/api/runs/{rid}")).status_code == 200
    assert (await client.get(f"/api/runs/{rid}")).status_code == 404
