import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Protocol

from app.schemas import CandidateData, Criteria, SearchResult

# (seconds_to_wait, reason) -> shown as a live countdown in the agent trace
WaitCallback = Callable[[float, str], Awaitable[None]]


class GitHubError(Exception):
    pass


class NotFound(GitHubError):
    pass


class GitHubClient(Protocol):
    mode: str

    async def search_merged_prs(self, criteria: Criteria) -> SearchResult: ...

    async def repo_contributors(self, repo: str, limit: int = 30) -> list[str]: ...

    async def get_candidate(self, login: str) -> CandidateData | None: ...

    async def get_pr_rest(self, repo: str, number: int) -> dict:
        """Fresh REST read of one PR — used only by the independent verifier."""
        ...

    async def aclose(self) -> None: ...


class RateLimiter:
    """Sliding-window limiter: at most `rate` calls per `per` seconds."""

    def __init__(self, rate: int, per: float = 60.0):
        self.rate, self.per = rate, per
        self._calls: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self, on_wait: WaitCallback | None = None) -> None:
        async with self._lock:
            now = time.monotonic()
            self._calls = [t for t in self._calls if now - t < self.per]
            if len(self._calls) >= self.rate:
                wait = self.per - (now - self._calls[0]) + 0.05
                if on_wait:
                    await on_wait(wait, "Search API budget (30 req/min) reached")
                await asyncio.sleep(wait)
            self._calls.append(time.monotonic())
