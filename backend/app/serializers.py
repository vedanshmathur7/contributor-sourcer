from datetime import UTC, datetime
from urllib.parse import urlencode

from app.contact import NOT_PUBLIC_REASON
from app.models import Candidate, Evidence, Run, Step


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.isoformat().replace("+00:00", "Z")


def step_dict(s: Step) -> dict:
    return {
        "id": s.id,
        "seq": s.seq,
        "phase": s.phase,
        "tool": s.tool,
        "status": s.status,
        "inputs": s.inputs,
        "summary": s.summary,
        "decisions": s.decisions,
        "rationale": s.rationale,
        "started_at": iso(s.started_at),
        "duration_ms": s.duration_ms,
        "error": s.error,
    }


def evidence_dict(e: Evidence, fixture: bool) -> dict:
    raw_url = None
    if fixture and e.kind != "fork_repo" and "/pull/" in e.url:
        parts = e.url.rstrip("/").split("/")
        raw_url = "/api/fixtures/pr?" + urlencode({"repo": f"{parts[3]}/{parts[4]}", "number": parts[6]})
    return {
        "id": e.id,
        "kind": e.kind,
        "url": e.url,
        "raw_url": raw_url,
        "title": e.title,
        "repo": e.repo,
        "repo_stars": e.repo_stars,
        "repo_is_fork": e.repo_is_fork,
        "repo_language": e.repo_language,
        "merged_at": iso(e.merged_at),
        "additions": e.additions,
        "deletions": e.deletions,
        "qualifies": e.qualifies,
        "rule_checks": e.rule_checks,
        "retrieved_at": iso(e.retrieved_at),
        "source_id": e.source_id,
        "verified": e.verified,
        "verified_at": iso(e.verified_at),
        "observed": e.observed,
        "verify_error": e.verify_error,
    }


def candidate_dict(c: Candidate, evidence: list[Evidence] | None = None) -> dict:
    ev = evidence if evidence is not None else c.evidence
    return {
        "id": c.id,
        "login": c.login,
        "profile": c.profile,
        "contact_email": c.contact_email,
        "contact_note": None if c.contact_email else NOT_PUBLIC_REASON,
        "classification": c.classification,
        "reason_code": c.reason_code,
        "reason_text": c.reason_text,
        "score": c.score,
        "score_breakdown": c.score_breakdown,
        "summary": c.summary,
        "summary_citations": c.summary_citations,
        "verification_status": c.verification_status,
        "blocked": c.blocked,
        "review_decision": c.review_decision,
        "review_note": c.review_note,
        "fixture": c.fixture,
        "evidence": [evidence_dict(e, c.fixture) for e in ev],
    }


def run_summary(r: Run) -> dict:
    return {
        "id": r.id,
        "created_at": iso(r.created_at),
        "mode": r.mode,
        "query": r.query,
        "criteria": r.criteria,
        "plan_notes": r.plan_notes,
        "status": r.status,
        "stats": r.stats,
        "error": r.error,
        "label": r.label,
        "started_at": iso(r.started_at),
        "completed_at": iso(r.completed_at),
        "finalised_at": iso(r.finalised_at),
        "approver": r.approver,
        "approval_note": r.approval_note,
        "exported_at": iso(r.exported_at),
        "share_token": r.share_token,
    }


def run_detail(r: Run) -> dict:
    return {
        **run_summary(r),
        "steps": [step_dict(s) for s in r.steps],
        "candidates": [candidate_dict(c) for c in r.candidates],
    }
