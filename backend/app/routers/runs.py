import asyncio
import json
import time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app import events
from app.agent import start_run
from app.config import get_settings
from app.crud import audit, load_run
from app.db import SessionLocal, get_session
from app.github.fixture import FixtureGitHubClient, load_world
from app.models import Run, Step
from app.planner import plan_criteria
from app.schemas import Criteria
from app.serializers import run_detail, run_summary, step_dict

router = APIRouter(prefix="/api", tags=["runs"])

TERMINAL = {"PENDING_APPROVAL", "FINALISED", "EXPORTED", "FAILED", "CANCELLED"}


class PlanRequest(BaseModel):
    query: str = Field(default="", max_length=2000)
    mode: Literal["fixture", "live"] = "fixture"
    overrides: dict | None = None  # structured chips from the UI win over the planner
    label: str | None = None


class CriteriaUpdate(BaseModel):
    criteria: Criteria


def _check_mode(mode: str) -> None:
    if mode == "live" and not get_settings().live_available:
        raise HTTPException(400, "Live mode needs a GITHUB_TOKEN on the server. Use Fixture mode, or configure the token.")


async def create_planned_run(db: AsyncSession, req: PlanRequest) -> Run:
    _check_mode(req.mode)
    t0 = time.perf_counter()
    known = list(load_world()["repos"]) if req.mode == "fixture" else None
    criteria, notes = await plan_criteria(req.query, known_repos=known) if req.query.strip() else (Criteria(), {
        "planner": "manual", "rationale": "Criteria entered manually."})
    if req.overrides:
        criteria = Criteria.model_validate({**criteria.model_dump(), **{k: v for k, v in req.overrides.items() if v is not None}})
    run = Run(mode=req.mode, query=req.query, criteria=criteria.model_dump(), plan_notes=notes, label=req.label)
    db.add(run)
    await db.flush()
    db.add(Step(
        run_id=run.id, seq=0, phase="Plan", tool="plan_criteria", status="ok",
        inputs={"query": req.query, "mode": req.mode}, rationale=notes.get("rationale"),
        summary=f"[{notes['planner']}] " + _criteria_line(criteria),
        duration_ms=int((time.perf_counter() - t0) * 1000),
    ))
    await db.commit()
    await audit(db, "run.planned", run_id=run.id, mode=req.mode, planner=notes["planner"])
    return run


def _criteria_line(c: Criteria) -> str:
    parts = [
        f"languages={c.languages or 'any'}",
        f"keywords={c.keywords or '-'}",
        f"window={c.window_days}d",
        f"min_prs={c.min_merged_prs}",
        f"max={c.max_candidates}",
    ]
    if c.seed_repos:
        parts.append(f"seed_repos={c.seed_repos}")
    if c.seed_users:
        parts.append(f"vet={c.seed_users}")
    if c.location:
        parts.append(f"location={c.location}")
    return " · ".join(parts)


@router.post("/runs/plan")
async def plan(req: PlanRequest, db: AsyncSession = Depends(get_session)):
    run = await create_planned_run(db, req)
    return run_detail(await load_run(db, run.id))


@router.patch("/runs/{run_id}/criteria")
async def update_criteria(run_id: str, body: CriteriaUpdate, db: AsyncSession = Depends(get_session)):
    run = await db.get(Run, run_id)
    if not run:
        raise HTTPException(404, "run not found")
    if run.status != "PLANNED":
        raise HTTPException(409, "criteria can only be edited before the run starts")
    run.criteria = body.criteria.model_dump()
    step = (await db.execute(select(Step).where(Step.run_id == run_id, Step.seq == 0))).scalar_one_or_none()
    if step:
        step.summary = "[edited by recruiter] " + _criteria_line(body.criteria)
    await db.commit()
    await audit(db, "run.criteria_edited", actor="recruiter", run_id=run_id, criteria=run.criteria)
    return run_detail(await load_run(db, run_id))


@router.post("/runs/{run_id}/start")
async def start(run_id: str, db: AsyncSession = Depends(get_session)):
    run = await db.get(Run, run_id)
    if not run:
        raise HTTPException(404, "run not found")
    if run.status not in ("PLANNED", "FAILED"):
        raise HTTPException(409, f"run is {run.status}")
    _check_mode(run.mode)
    run.status = "RUNNING"
    await db.commit()
    start_run(run_id)
    return run_summary(run)


@router.get("/runs")
async def list_runs(limit: int = Query(30, le=100), include_tests: bool = False, db: AsyncSession = Depends(get_session)):
    stmt = select(Run).order_by(Run.created_at.desc()).limit(limit)
    if not include_tests:
        stmt = stmt.where(Run.label.is_(None))
    runs = (await db.execute(stmt)).scalars().all()
    total = (await db.execute(select(func.count()).select_from(Run))).scalar_one()
    return {"runs": [run_summary(r) for r in runs], "total": total}


@router.get("/runs/{run_id}")
async def get_run(run_id: str, db: AsyncSession = Depends(get_session)):
    run = await load_run(db, run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return run_detail(run)


@router.delete("/runs/{run_id}")
async def delete_run(run_id: str, db: AsyncSession = Depends(get_session)):
    run = await db.get(Run, run_id)
    if not run:
        raise HTTPException(404, "run not found")
    if run.status == "RUNNING":
        raise HTTPException(409, "wait for the run to finish before deleting it")
    await db.delete(run)
    await db.commit()
    await audit(db, "run.deleted", actor="recruiter", run_id=run_id)
    return {"deleted": run_id}


@router.get("/runs/{run_id}/events")
async def run_events(run_id: str):
    """SSE: a full snapshot first, then live step/candidate/run/wait events until the run settles."""
    q = events.subscribe(run_id)

    async def gen():
        try:
            async with SessionLocal() as db:
                run = await load_run(db, run_id)
                if not run:
                    yield {"event": "error", "data": json.dumps({"detail": "run not found"})}
                    return
                yield {"event": "snapshot", "data": json.dumps(run_detail(run))}
                if run.status in TERMINAL or run.status == "PLANNED":
                    yield {"event": "done", "data": json.dumps({"status": run.status})}
                    return
            while True:
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=15)
                except TimeoutError:
                    yield {"event": "ping", "data": "{}"}
                    continue
                yield {"event": ev["type"], "data": json.dumps(ev)}
                if ev["type"] == "done":
                    return
        finally:
            events.unsubscribe(run_id, q)

    return EventSourceResponse(gen(), headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})


@router.get("/runs/{run_id}/steps")
async def get_steps(run_id: str, db: AsyncSession = Depends(get_session)):
    steps = (await db.execute(select(Step).where(Step.run_id == run_id).order_by(Step.seq))).scalars().all()
    return [step_dict(s) for s in steps]


@router.get("/fixtures/pr")
async def fixture_pr(repo: str, number: int):
    """The recorded synthetic JSON behind a fixture-mode evidence link."""
    rec = FixtureGitHubClient().raw_record(repo, number)
    if not rec:
        raise HTTPException(404, "no fixture record")
    return {"synthetic": True, "note": "Recorded GitHub-shaped fixture data; this person and PR are fictional.", **rec}
