from app.github.base import GitHubClient, GitHubError, NotFound, WaitCallback
from app.github.fixture import FixtureGitHubClient
from app.github.live import LiveGitHubClient


def make_client(mode: str, on_wait: WaitCallback | None = None) -> GitHubClient:
    if mode == "fixture":
        return FixtureGitHubClient()
    if mode == "live":
        return LiveGitHubClient(on_wait=on_wait)
    raise ValueError(f"unknown mode {mode!r}")


__all__ = ["GitHubClient", "GitHubError", "NotFound", "WaitCallback", "make_client", "FixtureGitHubClient", "LiveGitHubClient"]
