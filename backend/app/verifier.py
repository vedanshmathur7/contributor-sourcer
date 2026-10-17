"""Independent verifier — a separate module and a separate step.

After the agent proposes a draft, every cited PR is re-fetched through the REST API (never the cached search or
GraphQL result) and re-checked. Candidates with any failed check are blocked from approval until reviewed.
"""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime

from app.github.base import GitHubClient, NotFound

CHECKS = ("resolves", "merged", "in_window", "author_match", "base_not_fork")


@dataclass
class VerifyResult:
    verified: bool
    observed: dict
    error: str | None


def _parse(dt: str | None) -> datetime | None:
    return datetime.fromisoformat(dt.replace("Z", "+00:00")) if dt else None


def _repo_and_number(url: str) -> tuple[str, int]:
    # https://github.com/{owner}/{repo}/pull/{n}
    parts = url.rstrip("/").split("/")
    return f"{parts[3]}/{parts[4]}", int(parts[6])


async def verify_one(gh: GitHubClient, url: str, login: str, window_start: datetime) -> VerifyResult:
    checks = dict.fromkeys(CHECKS, False)
    observed: dict = {"checked_url": url}
    try:
        repo, number = _repo_and_number(url)
        data = await gh.get_pr_rest(repo, number)
    except NotFound as e:
        observed["checks"] = checks
        return VerifyResult(False, observed, f"PR no longer resolves: {e}")
    except Exception as e:
        observed["checks"] = checks
        return VerifyResult(False, observed, f"Could not re-fetch PR: {e}")

    merged_at = _parse(data.get("merged_at"))
    base = (data.get("base") or {}).get("repo") or {}
    author = (data.get("user") or {}).get("login", "")
    observed.update(
        merged_at=data.get("merged_at"),
        author=author,
        base_repo=base.get("full_name"),
        base_is_fork=base.get("fork"),
    )
    checks["resolves"] = True
    checks["merged"] = merged_at is not None
    checks["in_window"] = merged_at is not None and merged_at >= window_start
    checks["author_match"] = author.lower() == login.lower()
    checks["base_not_fork"] = base.get("fork") is False
    observed["checks"] = checks
    failed = [k for k, ok in checks.items() if not ok]
    return VerifyResult(not failed, observed, ("Failed: " + ", ".join(failed)) if failed else None)


async def verify_many(gh: GitHubClient, items: list[tuple[str, str]], window_start: datetime, concurrency: int = 6):
    """items: (url, login). Returns {url: VerifyResult} plus the verification timestamp."""
    sem = asyncio.Semaphore(concurrency)

    async def run(url: str, login: str):
        async with sem:
            return url, await verify_one(gh, url, login, window_start)

    results = await asyncio.gather(*(run(u, login) for u, login in items))
    return dict(results), datetime.now(UTC)
