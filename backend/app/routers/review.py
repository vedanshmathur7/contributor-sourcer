"""Human approval gate. The agent only ever produces a draft; these endpoints are the only way to finalise it."""

import csv
import io
import json
import secrets
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import audit, load_run
from app.db import get_session
from app.models import AuditLog, Candidate, Run
from app.serializers import candidate_dict, iso, run_detail, run_summary

router = APIRouter(prefix="/api", tags=["review"])


class ReviewRequest(BaseModel):
    decision: Literal["approved", "rejected", "pending"]
    note: str | None = Field(default=None, max_length=2000)
    reviewer: str = Field(default="recruiter", max_length=128)
    override_verification: bool = False


class FinaliseRequest(BaseModel):
    approver: str = Field(min_length=2, max_length=128)
    note: str | None = Field(default=None, max_length=2000)


def draft(run: Run) -> list[Candidate]:
    return [c for c in run.candidates if c.classification == "SHORTLISTED"]


def proposal(run: Run) -> dict:
    d = draft(run)
    return {
        "destination": f"Final shortlist · run {run.id}",
        "status": run.status,
        "approve": [c.login for c in d if c.review_decision == "approved"],
        "reject": [c.login for c in d if c.review_decision == "rejected"],
        "pending": [c.login for c in d if c.review_decision == "pending"],
        "blocked": [c.login for c in d if c.blocked],
    }


async def _run_or_404(db: AsyncSession, run_id: str) -> Run:
    run = await load_run(db, run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return run


@router.post("/runs/{run_id}/candidates/{cand_id}/review")
async def review(run_id: str, cand_id: str, body: ReviewRequest, db: AsyncSession = Depends(get_session)):
    run = await _run_or_404(db, run_id)
    if run.status != "PENDING_APPROVAL":
        raise HTTPException(409, f"run is {run.status}; reviews are only possible while it awaits approval")
    cand = next((c for c in run.candidates if c.id == cand_id), None)
    if not cand or cand.classification != "SHORTLISTED":
        raise HTTPException(404, "candidate is not part of the draft shortlist")
    if body.decision == "approved" and cand.blocked:
        if not body.override_verification or not (body.note or "").strip():
            raise HTTPException(
                422, "This candidate failed re-verification. Review the failed evidence, then approve with "
                "override_verification=true and a note explaining why.")
        cand.blocked = False
    before = cand.review_decision
    cand.review_decision, cand.review_note = body.decision, body.note
    await db.commit()
    await audit(db, "candidate.reviewed", actor=body.reviewer, run_id=run_id, login=cand.login,
                before=before, after=body.decision, note=body.note, override=body.override_verification)
    return candidate_dict(cand)


@router.get("/runs/{run_id}/proposal")
async def get_proposal(run_id: str, db: AsyncSession = Depends(get_session)):
    return proposal(await _run_or_404(db, run_id))


@router.post("/runs/{run_id}/finalise")
async def finalise(run_id: str, body: FinaliseRequest, db: AsyncSession = Depends(get_session)):
    run = await _run_or_404(db, run_id)
    if run.status in ("FINALISED", "EXPORTED"):
        # Idempotent: a retried click never finalises (or audits) twice.
        return {**run_detail(run), "already_finalised": True}
    if run.status != "PENDING_APPROVAL":
        raise HTTPException(409, f"run is {run.status}")
    p = proposal(run)
    if not p["approve"]:
        raise HTTPException(422, "approve at least one candidate before finalising")
    blocked_approved = [c.login for c in draft(run) if c.review_decision == "approved" and c.blocked]
    if blocked_approved:
        raise HTTPException(422, f"blocked candidates cannot be finalised: {blocked_approved}")
    run.status = "FINALISED"
    run.finalised_at = datetime.now(UTC)
    run.approver, run.approval_note = body.approver.strip(), body.note
    await db.commit()
    await audit(db, "run.finalised", actor=run.approver, run_id=run_id, note=body.note, **p)
    return run_detail(await load_run(db, run_id))


@router.post("/runs/{run_id}/undo")
async def undo(run_id: str, actor: str = Query("recruiter"), db: AsyncSession = Depends(get_session)):
    run = await _run_or_404(db, run_id)
    if run.status == "EXPORTED":
        raise HTTPException(409, "already exported — undo is only available until export")
    if run.status != "FINALISED":
        raise HTTPException(409, f"run is {run.status}")
    run.status, run.finalised_at = "PENDING_APPROVAL", None
    await db.commit()
    await audit(db, "run.finalise_undone", actor=actor, run_id=run_id, previous_approver=run.approver)
    return run_detail(await load_run(db, run_id))


def _final_rows(run: Run) -> list[dict]:
    approved = sorted([c for c in draft(run) if c.review_decision == "approved"], key=lambda c: -c.score)
    rows = []
    for i, c in enumerate(approved, 1):
        ev = [e for e in c.evidence if e.qualifies]
        rows.append({
            "rank": i,
            "login": c.login,
            "name": (c.profile or {}).get("name") or "",
            "profile_url": (c.profile or {}).get("html_url", f"https://github.com/{c.login}"),
            "contact_email": c.contact_email or "",
            "contact_status": "public profile email" if c.contact_email else "not public (never guessed)",
            "location": (c.profile or {}).get("location") or "",
            "score": c.score,
            "verification": c.verification_status,
            "qualifying_prs": len(ev),
            "evidence_urls": [e.url for e in ev],
            "summary": c.summary or "",
            "review_note": c.review_note or "",
            "synthetic_fixture": c.fixture,
        })
    return rows


@router.get("/runs/{run_id}/export")
async def export(run_id: str, format: Literal["csv", "json"] = "csv", actor: str = Query("recruiter"),
                 db: AsyncSession = Depends(get_session)):
    run = await _run_or_404(db, run_id)
    if run.status not in ("FINALISED", "EXPORTED"):
        raise HTTPException(409, "export is available after the shortlist is approved and finalised")
    rows = _final_rows(run)
    if run.status == "FINALISED":
        run.status, run.exported_at = "EXPORTED", datetime.now(UTC)
        await db.commit()
    await audit(db, "run.exported", actor=actor, run_id=run_id, format=format, rows=len(rows))
    if format == "json":
        payload = {"run": run_summary(run), "shortlist": rows, "exported_at": iso(run.exported_at)}
        return Response(json.dumps(payload, indent=2), media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="shortlist-{run_id}.json"'})
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()) if rows else ["rank"])
    w.writeheader()
    for r in rows:
        w.writerow({**r, "evidence_urls": " ".join(r["evidence_urls"])})
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="shortlist-{run_id}.csv"'})


@router.post("/runs/{run_id}/share")
async def share(run_id: str, actor: str = Query("recruiter"), db: AsyncSession = Depends(get_session)):
    run = await _run_or_404(db, run_id)
    if run.status not in ("FINALISED", "EXPORTED"):
        raise HTTPException(409, "only finalised shortlists can be shared")
    if not run.share_token:
        run.share_token = secrets.token_urlsafe(16)
        await db.commit()
        await audit(db, "run.shared", actor=actor, run_id=run_id)
    return {"token": run.share_token}


@router.get("/share/{token}")
async def shared(token: str, db: AsyncSession = Depends(get_session)):
    run = (await db.execute(select(Run).where(Run.share_token == token))).scalar_one_or_none()
    if not run or run.status not in ("FINALISED", "EXPORTED"):
        raise HTTPException(404, "link not found or revoked")
    run = await load_run(db, run.id)
    approved = [c for c in draft(run) if c.review_decision == "approved"]
    return {
        "run": {k: v for k, v in run_summary(run).items() if k != "share_token"},
        "candidates": [candidate_dict(c) for c in sorted(approved, key=lambda c: -c.score)],
    }


@router.get("/audit")
async def audit_log(run_id: str | None = None, limit: int = Query(100, le=500), db: AsyncSession = Depends(get_session)):
    stmt = select(AuditLog).order_by(AuditLog.ts.desc()).limit(limit)
    if run_id:
        stmt = stmt.where(AuditLog.run_id == run_id)
    rows = (await db.execute(stmt)).scalars().all()
    return [{"id": a.id, "ts": iso(a.ts), "run_id": a.run_id, "actor": a.actor, "action": a.action, "details": a.details}
            for a in rows]
