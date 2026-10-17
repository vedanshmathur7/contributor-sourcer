"""Deterministic evidence score (0–100) with a transparent breakdown. Computed only from qualifying PRs."""

import math
from datetime import datetime

from app.rules import Decision
from app.schemas import Criteria, now_utc

WEIGHTS = {"volume": 35, "recency": 25, "significance": 20, "diversity": 10, "size": 5, "own_projects": 5}


def score(decision: Decision, criteria: Criteria, now: datetime | None = None) -> tuple[float, dict]:
    now = now or now_utc()
    q = [c.pr for c in decision.qualifying]
    own = [c.pr for c in decision.pr_checks if c.kind == "own_project" and c.checks["merged"] and c.checks["in_window"]]

    half_life = max(30.0, criteria.window_days / 2)
    recency_w = sorted((0.5 ** ((now - pr.merged_at).days / half_life) for pr in q), reverse=True)[:3]
    repos: dict[str, int] = {}
    for pr in q:
        repos[pr.base_repo.name_with_owner] = pr.base_repo.stars
    sig = [min(1.0, math.log10(stars + 1) / 4.5) for stars in repos.values()]
    sane = [pr for pr in q if 3 <= pr.additions + pr.deletions <= 5000]

    parts = {
        "volume": WEIGHTS["volume"] * min(len(q), 8) / 8,
        "recency": WEIGHTS["recency"] * (sum(recency_w) / len(recency_w) if recency_w else 0),
        "significance": WEIGHTS["significance"] * (sum(sig) / len(sig) if sig else 0),
        "diversity": WEIGHTS["diversity"] * min(len(repos), 4) / 4,
        "size": WEIGHTS["size"] * (len(sane) / len(q) if q else 0),
        "own_projects": WEIGHTS["own_projects"] * min(len(own), 3) / 3 if q else 0,
    }
    notes = {
        "volume": f"{len(q)} qualifying merged PR(s) (max credit at 8)",
        "recency": f"half-life {half_life:.0f} days over the 3 most recent",
        "significance": f"log-stars of {len(repos)} upstream repo(s)",
        "diversity": f"{len(repos)} distinct upstream repo(s) (max credit at 4)",
        "size": f"{len(sane)}/{len(q)} PRs with a sane diff size (3–5000 lines)",
        "own_projects": f"{len(own)} self-merged PR(s) in own repos (bonus only, never sufficient alone)",
    }
    breakdown = {
        k: {"points": round(v, 1), "max": WEIGHTS[k], "note": notes[k]} for k, v in parts.items()
    }
    return round(sum(parts.values()), 1), breakdown
