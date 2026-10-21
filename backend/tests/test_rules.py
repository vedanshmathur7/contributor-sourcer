"""Unit tests for every decision rule, the contact rule, scoring, and TC1–TC4 logic on fixtures."""

from datetime import UTC, datetime, timedelta

import pytest

from app.contact import resolve_contact
from app.github.fixture import FixtureGitHubClient
from app.rules import Classification, classify, evaluate_pr, is_bot, stack_matches
from app.schemas import CandidateData, Criteria, Profile, PullRequest, RepoInfo
from app.scoring import score

NOW = datetime(2026, 10, 17, tzinfo=UTC)
RUST = Criteria(languages=["Rust"], keywords=["async"], window_days=180, min_merged_prs=2)


def repo(name="up/stream", fork=False, lang="Rust", stars=1000, topics=()):
    return RepoInfo(name_with_owner=name, owner=name.split("/")[0], is_fork=fork, primary_language=lang, stars=stars, topics=list(topics))


def pr(days_ago=10, base=None, n=1, author="dev", merged=True, size=100):
    return PullRequest(
        source_id=f"x{n}", number=n, title="feat: async thing", url=f"https://github.com/{(base or repo()).name_with_owner}/pull/{n}",
        merged_at=NOW - timedelta(days=days_ago) if merged else None, additions=size, deletions=0,
        author_login=author, base_repo=base or repo(),
    )


def cand(*prs, login="dev", email=None, owned=(), kind="User"):
    return CandidateData(
        profile=Profile(login=login, public_email=email, html_url=f"https://github.com/{login}", account_type=kind),
        pull_requests=list(prs), owned_repos=list(owned),
    )


# ---------- single-PR rules ----------

def test_rule_merged_required():
    assert evaluate_pr(pr(merged=False), "dev", RUST, NOW).checks["merged"] is False


def test_rule_in_window_boundaries():
    assert evaluate_pr(pr(days_ago=179), "dev", RUST, NOW).checks["in_window"]
    assert not evaluate_pr(pr(days_ago=181), "dev", RUST, NOW).checks["in_window"]
    assert not evaluate_pr(pr(days_ago=-1), "dev", RUST, NOW).checks["in_window"]  # future dates rejected


def test_rule_base_not_fork():
    c = evaluate_pr(pr(base=repo("dev/stream", fork=True)), "dev", RUST, NOW)
    assert not c.checks["base_not_fork"] and c.kind == "fork_activity" and not c.qualifies


def test_fork_contributor_pr_into_upstream_counts():
    # Opening a PR *from* your fork into a real upstream is a genuine contribution.
    assert evaluate_pr(pr(base=repo("upstream/real")), "dev", RUST, NOW).qualifies


def test_rule_not_own_repo():
    c = evaluate_pr(pr(base=repo("dev/mine")), "dev", RUST, NOW)
    assert c.kind == "own_project" and not c.qualifies


def test_rule_stack_language_is_hard_requirement():
    assert not stack_matches(repo(lang="Python", topics=["async"]), RUST)
    assert stack_matches(repo(lang="rust"), RUST)  # case-insensitive


def test_rule_stack_keywords_when_no_language():
    c = Criteria(keywords=["quic"])
    assert stack_matches(repo(name="m/quic-rs"), c)
    assert stack_matches(repo(topics=["quic"]), c)
    assert not stack_matches(repo(name="m/http"), c)


def test_rule_bot_detection():
    assert is_bot("dependabot[bot]") and is_bot("renovate") and is_bot("anything", "Bot")
    assert not is_bot("robert")
    assert is_bot("meeseeksmachine") and is_bot("k8s-ci-robot")  # automation registered as a User


# ---------- classifications ----------

def test_shortlisted_needs_min_prs():
    d = classify(cand(pr(n=1), pr(n=2)), RUST, NOW)
    assert d.classification == Classification.SHORTLISTED and len(d.qualifying) == 2
    d1 = classify(cand(pr(n=1)), RUST, NOW)
    assert d1.classification == Classification.INSUFFICIENT_EVIDENCE and d1.reason_code == "BELOW_MIN_PRS"


def test_excluded_recency_states_the_date():
    d = classify(cand(pr(days_ago=1100, n=1), pr(days_ago=1200, n=2)), RUST, NOW)
    assert d.classification == Classification.EXCLUDED_RECENCY
    assert (NOW - timedelta(days=1100)).date().isoformat() in d.reason_text


def test_excluded_fork_only():
    fork = repo("dev/stream", fork=True)
    d = classify(cand(pr(base=fork, n=1), pr(base=fork, n=2)), RUST, NOW)
    assert d.classification == Classification.EXCLUDED_FORK_ONLY


def test_excluded_fork_only_from_pushed_fork_repos():
    fork = repo("dev/stream", fork=True).model_copy(update={"pushed_at": NOW - timedelta(days=2)})
    assert classify(cand(owned=[fork]), RUST, NOW).classification == Classification.EXCLUDED_FORK_ONLY


def test_excluded_stack():
    d = classify(cand(pr(base=repo(lang="Go"), n=1), pr(base=repo(lang="Go"), n=2)), RUST, NOW)
    assert d.classification == Classification.EXCLUDED_STACK and "Go" in d.reason_text


def test_excluded_bot_even_with_prs():
    d = classify(cand(pr(n=1), pr(n=2), login="deps-bot[bot]", kind="Bot"), RUST, NOW)
    assert d.classification == Classification.EXCLUDED_BOT


def test_own_projects_never_sufficient_alone():
    mine = repo("dev/mine")
    d = classify(cand(pr(base=mine, n=1), pr(base=mine, n=2), pr(base=mine, n=3)), RUST, NOW)
    assert d.classification == Classification.INSUFFICIENT_EVIDENCE and d.reason_code == "OWN_PROJECTS_ONLY"


def test_no_contributions():
    assert classify(cand(), RUST, NOW).reason_code == "NO_PUBLIC_CONTRIBUTIONS"


# ---------- contact rule (TC4) ----------

def test_contact_uses_public_field_only():
    assert resolve_contact(Profile(login="a", public_email="a@example.com", html_url="u")) == "a@example.com"


@pytest.mark.parametrize("value", [None, "", "   ", "not-an-email", "a@b"])
def test_contact_never_guessed(value):
    p = Profile(login="karan", name="Karan Shah", company="@meshwire", blog="https://meshwire.dev",
                public_email=value, html_url="u")
    # Even with name + company + domain available (enough to pattern-guess), contact stays blank.
    assert resolve_contact(p) is None


# ---------- scoring ----------

def test_score_bounds_and_breakdown():
    d = classify(cand(*[pr(n=i, days_ago=i, base=repo(f"o{i}/r", stars=50000)) for i in range(1, 10)]), RUST, NOW)
    total, parts = score(d, RUST, NOW)
    assert 90 <= total <= 100
    assert set(parts) == {"volume", "recency", "significance", "diversity", "size", "own_projects"}
    assert all(0 <= v["points"] <= v["max"] for v in parts.values())


def test_score_zero_without_qualifying_prs():
    d = classify(cand(pr(days_ago=900)), RUST, NOW)
    assert score(d, RUST, NOW)[0] == 0


def test_more_recent_scores_higher():
    a = classify(cand(pr(n=1, days_ago=2), pr(n=2, days_ago=3)), RUST, NOW)
    b = classify(cand(pr(n=1, days_ago=150), pr(n=2, days_ago=160)), RUST, NOW)
    assert score(a, RUST, NOW)[0] > score(b, RUST, NOW)[0]


# ---------- official test cases on fixture personas ----------

@pytest.mark.parametrize(
    "login,expected",
    [
        ("tc1-active-rustacean", Classification.SHORTLISTED),
        ("tc2-fork-only", Classification.EXCLUDED_FORK_ONLY),
        ("tc3-stale-dev", Classification.EXCLUDED_RECENCY),
        ("tc4-no-email", Classification.SHORTLISTED),
        ("synth-pythonista", Classification.EXCLUDED_STACK),
        ("reactor-ci-bot[bot]", Classification.EXCLUDED_BOT),
        ("synth-solo-builder", Classification.INSUFFICIENT_EVIDENCE),
        ("synth-newcomer", Classification.INSUFFICIENT_EVIDENCE),
    ],
)
async def test_fixture_personas(login, expected):
    gh = FixtureGitHubClient(now=NOW)
    data = await gh.get_candidate(login)
    assert classify(data, RUST, NOW).classification == expected


async def test_tc1_has_pr_links():
    data = await FixtureGitHubClient(now=NOW).get_candidate("tc1-active-rustacean")
    d = classify(data, RUST, NOW)
    assert all(c.pr.url.startswith("https://github.com/") and "/pull/" in c.pr.url for c in d.qualifying)


async def test_tc4_contact_blank():
    data = await FixtureGitHubClient(now=NOW).get_candidate("tc4-no-email")
    assert resolve_contact(data.profile) is None
