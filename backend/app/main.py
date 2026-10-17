from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.db import SessionLocal, ensure_db, init_db
from app.routers import review, runs, testcases


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Open-Source Contributor Sourcer",
    version="1.0.0",
    description="Finds developers with real, recent public contributions — with evidence, "
    "independent verification and a human approval gate.",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=r"https://.*\.(vercel\.app|onrender\.com)",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _lazy_db(request: Request, call_next):
    await ensure_db()
    return await call_next(request)


app.include_router(runs.router)
app.include_router(review.router)
app.include_router(testcases.router)


@app.get("/api/health")
async def health():
    db_ok = True
    try:
        async with SessionLocal() as s:
            await s.execute(text("select 1"))
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "db": db_ok, "commit": settings.commit_sha}


@app.get("/api/meta")
async def meta():
    return {
        "live_available": settings.live_available,
        "llm_enabled": settings.llm_enabled,
        "llm_provider": settings.llm_provider if settings.llm_enabled else "none",
        "llm_model": settings.llm_model if settings.llm_enabled else None,
        "commit": settings.commit_sha,
        "inline_runs": settings.run_inline,
    }
