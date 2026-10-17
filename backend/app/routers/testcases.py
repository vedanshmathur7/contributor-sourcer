from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import testcases as tcs
from app.config import get_settings
from app.db import get_session
from app.models import TestRun
from app.serializers import iso

router = APIRouter(prefix="/api/testcases", tags=["testcases"])


class RunRequest(BaseModel):
    mode: Literal["fixture", "live"] = "fixture"
    inputs: dict | None = None  # live: {"TC1": {"login": "...", "languages": ["Rust"]}}


def tr_dict(t: TestRun) -> dict:
    return {
        "id": t.id, "ts": iso(t.ts), "batch_id": t.batch_id, "tc_id": t.tc_id, "label": t.label, "mode": t.mode,
        "input": t.input, "expected": t.expected, "actual": t.actual, "passed": t.passed,
        "explanation": t.explanation, "evidence": t.evidence, "commit_sha": t.commit_sha, "run_id": t.run_id,
    }


@router.get("/definitions")
async def definitions():
    return {
        "cases": [{"id": c.id, "label": c.label, "scenario": c.scenario, "expected": c.expected,
                   "fixture_login": c.fixture_login} for c in tcs.CASES],
        "live_inputs": {k: v for k, v in tcs.live_inputs().items() if not k.startswith("_")},
        "live_available": get_settings().live_available,
    }


@router.post("/run")
async def run(body: RunRequest):
    if body.mode == "live" and not get_settings().live_available:
        raise HTTPException(400, "Live mode needs a GITHUB_TOKEN on the server.")
    if tcs.is_running(body.mode):
        raise HTTPException(409, "a test batch is already running in this mode")
    tcs.start_batch(body.mode, body.inputs)
    return {"started": True, "mode": body.mode}


@router.get("/latest")
async def latest(db: AsyncSession = Depends(get_session)):
    out = {}
    for mode in ("fixture", "live"):
        last = (await db.execute(select(TestRun).where(TestRun.mode == mode).order_by(TestRun.ts.desc()).limit(1))).scalar_one_or_none()
        rows = []
        if last:
            rows = (await db.execute(select(TestRun).where(TestRun.batch_id == last.batch_id).order_by(TestRun.tc_id))).scalars().all()
        out[mode] = {"running": tcs.is_running(mode), "batch_id": last.batch_id if last else None,
                     "results": [tr_dict(r) for r in rows]}
    return out


@router.get("/history")
async def history(limit: int = 40, db: AsyncSession = Depends(get_session)):
    rows = (await db.execute(select(TestRun).order_by(TestRun.ts.desc()).limit(limit))).scalars().all()
    return [tr_dict(r) for r in rows]
