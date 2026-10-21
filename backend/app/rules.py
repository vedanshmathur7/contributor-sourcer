"""Deterministic decision rules. No LLM is involved in any keep/exclude decision.

A merged PR is a *qualifying contribution* only if every check passes:
  merged        — the PR was merged (not just opened/closed)
  in_window     — merged inside the recruiter's recency window                     (TC3)
  base_not_fork — merged into a repository that is not itself a fork              (TC2)
  not_own_repo  — the base repository is not owned by the candidate (self-merges are "own projects")
  stack_match   — the base repository matches the target stack
The author must also not be a bot.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.schemas import CandidateData, Criteria, PullRequest, RepoInfo, now_utc

BOT_MARKERS = ("[bot]", "dependabot", "renovate", "github-actions", "-ci-bot", "greenkeeper", "snyk-bot")
# Well-known automation accounts registered as ordinary users (no "[bot]" suffix).
KNOWN_BOT_USERS = {"meeseeksmachine", "pre-commit-ci", "allcontributors", "codecov-commenter", "imgbot",
                   "mergify", "kodiakhq", "web-flow", "bors", "homu", "k8s-ci-robot", "copybara-service"}


class Classification(StrEnum):
    SHORTLISTED = "SHORTLISTED"
    EXCLUDED_RECENCY = "EXCLUDED_RECENCY"
    EXCLUDED_FORK_ONLY = "EXCLUDED_FORK_ONLY"
    EXCLUDED_STACK = "EXCLUDED_STACK"
    EXCLUDED_BOT = "EXCLUDED_BOT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


CHECK_LABELS = {
    "merged": "PR was merged",
    "in_window": "Merged inside the recency window",
    "base_not_fork": "Base repository is not a fork",
    "not_own_repo": "Base repository not owned by the candidate",
    "stack_match": "Repository matches the target stack",
}


@dataclass
class PRCheck:
    pr: PullRequest
    checks: dict[str, bool]
    kind: str  # pr | own_project | fork_activity

    @property
    def qualifies(self) -> bool:
        return all(self.checks.values())


@dataclass
class Decision:
    classification: Classification
    reason_code: str
    reason_text: str
    pr_checks: list[PRCheck] = field(default_factory=list)
    fork_repos: list[RepoInfo] = field(default_factory=list)
    location_match: bool | None = None

    @property
    def qualifying(self) -> list[PRCheck]:
        return [c for c in self.pr_checks if c.qualifies]


def is_bot(login: str, account_type: str = "User") -> bool:
    if account_type == "Bot":
        return True
    low = login.lower()
    return low in KNOWN_BOT_USERS or any(m in low for m in BOT_MARKERS)


def stack_matches(repo: RepoInfo, criteria: Criteria) -> bool:
    """Languages are a hard requirement when given; otherwise keywords must match repo topics/name."""
    if criteria.languages:
        return (repo.primary_language or "").lower() in {lang.lower() for lang in criteria.languages}
    if criteria.keywords:
        haystack = " ".join([repo.name_with_owner, *repo.topics]).lower()
        return any(k.lower() in haystack for k in criteria.keywords)
    return True


def evaluate_pr(pr: PullRequest, login: str, criteria: Criteria, now: datetime) -> PRCheck:
    start = criteria.window_start(now)
    checks = {
        "merged": pr.merged_at is not None,
        "in_window": pr.merged_at is not None and start <= pr.merged_at <= now,
        "base_not_fork": not pr.base_repo.is_fork,
        "not_own_repo": pr.base_repo.owner.lower() != login.lower(),
        "stack_match": stack_matches(pr.base_repo, criteria),
    }
    if pr.base_repo.is_fork:
        kind = "fork_activity"
    elif not checks["not_own_repo"]:
        kind = "own_project"
    else:
        kind = "pr"
    return PRCheck(pr=pr, checks=checks, kind=kind)


def _days(now: datetime, then: datetime) -> int:
    return max(0, (now - then).days)


def classify(data: CandidateData, criteria: Criteria, now: datetime | None = None) -> Decision:
    now = now or now_utc()
    p = data.profile
    loc = None
    if criteria.location and p.location:
        loc = criteria.location.lower() in p.location.lower()

    if is_bot(p.login, p.account_type):
        return Decision(
            Classification.EXCLUDED_BOT,
            "EXCLUDED_BOT",
            f"@{p.login} is an automated account; bot activity is never counted as a contribution.",
            location_match=loc,
        )

    checks = [evaluate_pr(pr, p.login, criteria, now) for pr in data.pull_requests]
    qualifying = [c for c in checks if c.qualifies]
    window = criteria.window_days
    start = criteria.window_start(now)
    fork_repos = [
        r for r in data.owned_repos if r.is_fork and r.pushed_at and r.pushed_at >= start and stack_matches(r, criteria)
    ]

    def decision(cls: Classification, text: str) -> Decision:
        return Decision(cls, cls.value, text, checks, fork_repos, loc)

    if len(qualifying) >= criteria.min_merged_prs:
        repos = sorted({c.pr.base_repo.name_with_owner for c in qualifying})
        latest = max(c.pr.merged_at for c in qualifying)
        return decision(
            Classification.SHORTLISTED,
            f"{len(qualifying)} merged PRs into {len(repos)} upstream repo(s) ({', '.join(repos[:3])}) "
            f"in the last {window} days; most recent {latest.date().isoformat()}.",
        )

    if qualifying:
        return Decision(
            Classification.INSUFFICIENT_EVIDENCE,
            "BELOW_MIN_PRS",
            f"Only {len(qualifying)} qualifying merged PR in the window; at least {criteria.min_merged_prs} required.",
            checks,
            fork_repos,
            loc,
        )

    stale = [
        c
        for c in checks
        if c.checks["merged"] and c.checks["base_not_fork"] and c.checks["not_own_repo"] and c.checks["stack_match"]
    ]
    if stale:
        latest = max(c.pr.merged_at for c in stale)
        return decision(
            Classification.EXCLUDED_RECENCY,
            f"Relevant work exists, but the latest qualifying merged PR was {latest.date().isoformat()} "
            f"({_days(now, latest)} days ago), outside the {window}-day window.",
        )

    fork_prs = [c for c in checks if c.kind == "fork_activity" and c.checks["merged"]]
    if fork_prs or fork_repos:
        forks = sorted({c.pr.base_repo.name_with_owner for c in fork_prs} | {r.name_with_owner for r in fork_repos})
        return decision(
            Classification.EXCLUDED_FORK_ONLY,
            f"All activity lives in personal forks ({', '.join(forks[:3])}); work that never reached a "
            f"non-fork upstream is not counted as a contribution.",
        )

    off_stack = [c for c in checks if c.checks["merged"] and c.checks["in_window"] and c.checks["base_not_fork"] and c.checks["not_own_repo"]]
    if off_stack:
        langs = sorted({c.pr.base_repo.primary_language or "unknown" for c in off_stack})
        return decision(
            Classification.EXCLUDED_STACK,
            f"Has {len(off_stack)} recent merged PR(s), but in {', '.join(langs)} — not the target stack "
            f"({', '.join(criteria.languages or criteria.keywords)}).",
        )

    own = [c for c in checks if c.kind == "own_project" and c.checks["merged"] and c.checks["in_window"]]
    if own:
        return Decision(
            Classification.INSUFFICIENT_EVIDENCE,
            "OWN_PROJECTS_ONLY",
            f"{len(own)} recent PR(s), all self-merged into the candidate's own repositories; own projects are "
            "tracked but never sufficient on their own.",
            checks,
            fork_repos,
            loc,
        )

    return Decision(
        Classification.INSUFFICIENT_EVIDENCE,
        "NO_PUBLIC_CONTRIBUTIONS",
        "No merged public pull requests were found on this profile.",
        checks,
        fork_repos,
        loc,
    )
