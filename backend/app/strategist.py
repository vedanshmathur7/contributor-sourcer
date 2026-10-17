"""Adaptive discovery: after a pass, decide whether to look further. It may widen *where* the agent looks
(new seed repositories, dropping keyword filters), never *what counts* — rules and window are untouchable."""

import json
from collections import Counter

from app.llm import get_llm

SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["expand", "stop"]},
        "add_seed_repos": {"type": "array", "items": {"type": "string"}},
        "drop_keywords": {"type": "boolean"},
        "rationale": {"type": "string"},
    },
    "required": ["action", "add_seed_repos", "drop_keywords", "rationale"],
    "additionalProperties": False,
}

SYSTEM = """You steer discovery for a contributor-sourcing agent. After each pass you see what was found.
If fewer candidates were shortlisted than the target, you may EXPAND discovery by:
  - add_seed_repos: up to 2 repositories taken ONLY from CANDIDATE_REPOS (mine their contributors);
  - drop_keywords: true to re-search without keyword filters.
You must NOT change the recency window, minimum PRs, stack or any judging rule.
Choose "stop" if the target is met, nothing useful is left to try, or this is the last pass.
rationale: one short sentence for the live trace."""


def heuristic(state: dict) -> dict:
    if state["shortlisted"] >= state["target"] or state["pass"] >= state["max_passes"]:
        return {"action": "stop", "add_seed_repos": [], "drop_keywords": False,
                "rationale": "Target reached." if state["shortlisted"] >= state["target"] else "Discovery budget used."}
    new = [r for r in state["candidate_repos"] if r not in state["seeded"]][:2]
    drop = bool(state["keywords"]) and not state["keywords_dropped"]
    if not new and not drop:
        return {"action": "stop", "add_seed_repos": [], "drop_keywords": False,
                "rationale": "No unexplored upstream repositories left in the evidence."}
    return {"action": "expand", "add_seed_repos": new, "drop_keywords": drop and not new,
            "rationale": f"Only {state['shortlisted']}/{state['target']} shortlisted — mining contributors of "
            + (", ".join(new) if new else "the stack without keyword filters") + "."}


def candidate_repos(qualifying_repos: list[str], hit_repos: list[str]) -> list[str]:
    counts = Counter(qualifying_repos) + Counter(hit_repos)
    return [r for r, _ in counts.most_common(8)]


async def decide(state: dict) -> tuple[dict, str]:
    base = heuristic(state)
    if base["action"] == "stop" and state["shortlisted"] >= state["target"]:
        return base, "deterministic"
    llm = get_llm()
    out = await llm.json(SYSTEM, "STATE:\n" + json.dumps(state, indent=1), SCHEMA, max_tokens=2000)
    if out:
        allowed = set(state["candidate_repos"]) - set(state["seeded"])
        out["add_seed_repos"] = [r for r in out["add_seed_repos"] if r in allowed][:2]
        if state["pass"] >= state["max_passes"]:
            out["action"] = "stop"
        if out["action"] == "expand" and not out["add_seed_repos"] and not out["drop_keywords"]:
            out["action"] = "stop"
        return out, llm.label
    return base, "deterministic"
