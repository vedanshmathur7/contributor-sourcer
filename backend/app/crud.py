from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AuditLog, Candidate, Run


async def load_run(db: AsyncSession, run_id: str, populate: bool = True) -> Run | None:
    stmt = (
        select(Run)
        .where(Run.id == run_id)
        .options(selectinload(Run.steps), selectinload(Run.candidates).selectinload(Candidate.evidence))
        .execution_options(populate_existing=populate)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def audit(db: AsyncSession, action: str, actor: str = "system", run_id: str | None = None, **details) -> None:
    db.add(AuditLog(action=action, actor=actor, run_id=run_id, details=details))
    await db.commit()
