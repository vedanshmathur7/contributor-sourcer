"""Persistence model. Every run, step, decision, piece of evidence, verification and approval is stored."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def utcnow() -> datetime:
    return datetime.now(UTC)


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    mode: Mapped[str] = mapped_column(String(16))  # fixture | live
    query: Mapped[str] = mapped_column(Text, default="")
    criteria: Mapped[dict] = mapped_column(JSON, default=dict)
    plan_notes: Mapped[dict] = mapped_column(JSON, default=dict)  # planner rationale + provider
    # PLANNED -> RUNNING -> PENDING_APPROVAL -> FINALISED -> EXPORTED ; FAILED ; CANCELLED
    status: Mapped[str] = mapped_column(String(32), default="PLANNED")
    stats: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    label: Mapped[str | None] = mapped_column(String(64), nullable=True)  # e.g. "TC1" for harness runs
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approver: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approval_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    share_token: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)

    steps: Mapped[list["Step"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="Step.seq"
    )
    candidates: Mapped[list["Candidate"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="Candidate.score.desc()"
    )


class Step(Base):
    __tablename__ = "steps"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    phase: Mapped[str] = mapped_column(String(32))  # Plan, Search, Enrich, Classify, Score, Verify, Propose
    tool: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="running")  # running | ok | failed | waiting
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    summary: Mapped[str] = mapped_column(Text, default="")
    decisions: Mapped[list] = mapped_column(JSON, default=list)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)  # why the agent chose this step
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped[Run] = relationship(back_populates="steps")


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    login: Mapped[str] = mapped_column(String(128))
    profile: Mapped[dict] = mapped_column(JSON, default=dict)
    contact_email: Mapped[str | None] = mapped_column(String(256), nullable=True)
    classification: Mapped[str] = mapped_column(String(32))
    reason_code: Mapped[str] = mapped_column(String(48))
    reason_text: Mapped[str] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    score_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_citations: Mapped[list] = mapped_column(JSON, default=list)
    # verification: unverified | verified | failed
    verification_status: Mapped[str] = mapped_column(String(16), default="unverified")
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    # review: pending | approved | rejected
    review_decision: Mapped[str] = mapped_column(String(16), default="pending")
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    fixture: Mapped[bool] = mapped_column(Boolean, default=False)

    run: Mapped[Run] = relationship(back_populates="candidates")
    evidence: Mapped[list["Evidence"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", order_by="Evidence.merged_at.desc()"
    )


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(24))  # pr | own_project | fork_activity
    url: Mapped[str] = mapped_column(String(512))
    title: Mapped[str] = mapped_column(Text, default="")
    repo: Mapped[str] = mapped_column(String(256))
    repo_stars: Mapped[int] = mapped_column(Integer, default=0)
    repo_is_fork: Mapped[bool] = mapped_column(Boolean, default=False)
    repo_language: Mapped[str | None] = mapped_column(String(64), nullable=True)
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    additions: Mapped[int] = mapped_column(Integer, default=0)
    deletions: Mapped[int] = mapped_column(Integer, default=0)
    qualifies: Mapped[bool] = mapped_column(Boolean, default=False)
    rule_checks: Mapped[dict] = mapped_column(JSON, default=dict)  # rule name -> bool
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    source_id: Mapped[str | None] = mapped_column(String(128), nullable=True)  # GitHub node id / fixture id
    verified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    observed: Mapped[dict] = mapped_column(JSON, default=dict)
    verify_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    candidate: Mapped[Candidate] = relationship(back_populates="evidence")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    run_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    actor: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(64))
    details: Mapped[dict] = mapped_column(JSON, default=dict)


class TestRun(Base):
    __tablename__ = "test_runs"
    __test__ = False  # not a pytest class

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    batch_id: Mapped[str] = mapped_column(String(32), index=True)
    tc_id: Mapped[str] = mapped_column(String(8))
    label: Mapped[str] = mapped_column(String(128))
    mode: Mapped[str] = mapped_column(String(16))
    input: Mapped[dict] = mapped_column(JSON, default=dict)
    expected: Mapped[str] = mapped_column(Text)
    actual: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # None = inconclusive
    explanation: Mapped[str] = mapped_column(Text, default="")
    commit_sha: Mapped[str] = mapped_column(String(40), default="local")
    run_id: Mapped[str | None] = mapped_column(String(32), nullable=True)


class ApiCache(Base):
    __tablename__ = "api_cache"

    key: Mapped[str] = mapped_column(String(512), primary_key=True)
    etag: Mapped[str | None] = mapped_column(String(256), nullable=True)
    body: Mapped[dict | list] = mapped_column(JSON)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
