"""TC1–TC4 through the real harness (fixture mode): stored records with input, expected, actual, evidence, verdict."""

from datetime import UTC, datetime

from sqlalchemy import select

from app.db import SessionLocal
from app.github.fixture import FixtureGitHubClient
from app.models import TestRun
from app.testcases import CASES, run_all

NOW = datetime(2026, 10, 17, tzinfo=UTC)


async def test_official_test_cases_pass_in_fixture_mode(client):
    batch = await run_all("fixture", gh_factory=lambda: FixtureGitHubClient(now=NOW), now=NOW)
    async with SessionLocal() as db:
        rows = (await db.execute(select(TestRun).where(TestRun.batch_id == batch).order_by(TestRun.tc_id))).scalars().all()
    assert [r.tc_id for r in rows] == [c.id for c in CASES]
    for r in rows:
        assert r.passed is True, (r.tc_id, r.actual, r.explanation)
        assert r.input["login"] and r.expected and r.actual and r.run_id and r.commit_sha
        assert r.evidence["candidate"]["fixture"] is True

    tc1, tc2, tc3, tc4 = rows
    assert all("/pull/" in i["url"] for i in tc1.evidence["items"] if i["qualifies"])
    assert all(i["verified"] for i in tc1.evidence["items"] if i["qualifies"])
    assert all(not i["qualifies"] for i in tc2.evidence["items"])
    assert "outside the 180-day window" in tc3.actual
    assert tc4.evidence["candidate"]["contact_email"] is None


async def test_live_cases_without_token_are_inconclusive_not_faked(client):
    r = await client.post("/api/testcases/run", json={"mode": "live"})
    assert r.status_code == 400
    defs = (await client.get("/api/testcases/definitions")).json()
    assert len(defs["cases"]) == 4 and defs["live_available"] is False
