"""Normalised domain types shared by the GitHub clients, rules, scoring and agent."""

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field, field_validator


def now_utc() -> datetime:
    return datetime.now(UTC)


class Criteria(BaseModel):
    languages: list[str] = Field(default_factory=list, description="Target languages, e.g. ['Rust']")
    keywords: list[str] = Field(default_factory=list, description="Topic keywords, e.g. ['async', 'quic']")
    seed_repos: list[str] = Field(default_factory=list, description="owner/name repos to mine contributors from")
    seed_users: list[str] = Field(default_factory=list, description="Specific GitHub logins to vet")
    window_days: int = Field(default=180, ge=7, le=1825)
    min_merged_prs: int = Field(default=2, ge=1, le=20)
    max_candidates: int = Field(default=15, ge=1, le=50)
    location: str | None = None

    @field_validator("languages", "keywords", "seed_repos", "seed_users")
    @classmethod
    def _clean(cls, v: list[str]) -> list[str]:
        seen: list[str] = []
        for item in v:
            item = item.strip()
            if item and item.lower() not in {s.lower() for s in seen}:
                seen.append(item)
        return seen

    def window_start(self, now: datetime | None = None) -> datetime:
        return (now or now_utc()) - timedelta(days=self.window_days)


class RepoInfo(BaseModel):
    name_with_owner: str
    owner: str
    is_fork: bool = False
    parent: str | None = None
    stars: int = 0
    primary_language: str | None = None
    topics: list[str] = Field(default_factory=list)
    pushed_at: datetime | None = None


class PullRequest(BaseModel):
    source_id: str
    number: int
    title: str
    url: str
    merged_at: datetime | None
    additions: int = 0
    deletions: int = 0
    author_login: str
    base_repo: RepoInfo


class Profile(BaseModel):
    login: str
    name: str | None = None
    bio: str | None = None
    location: str | None = None
    company: str | None = None
    # Raw value of the profile's *public* email field. Empty / missing means "not public".
    public_email: str | None = None
    blog: str | None = None
    followers: int = 0
    avatar_url: str | None = None
    html_url: str
    account_type: str = "User"  # User | Bot | Organization


class CandidateData(BaseModel):
    profile: Profile
    pull_requests: list[PullRequest] = Field(default_factory=list)
    owned_repos: list[RepoInfo] = Field(default_factory=list)
    fixture: bool = False


class SearchHit(BaseModel):
    login: str
    pr_url: str
    repo: str
    merged_at: datetime | None = None
    via: str = "search"  # search | seed_repo | seed_user


class SearchResult(BaseModel):
    hits: list[SearchHit]
    queries: list[str]
    total_count: int
