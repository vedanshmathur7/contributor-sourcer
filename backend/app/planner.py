"""Planner: turns a recruiter's natural-language request into editable, structured Criteria."""

import re

from app.llm import get_llm
from app.schemas import Criteria

LANGUAGES = [
    "Rust", "Go", "Python", "TypeScript", "JavaScript", "Java", "Kotlin", "Swift", "C++", "C#", "C", "Ruby",
    "PHP", "Scala", "Elixir", "Haskell", "Zig", "Dart", "Julia", "Lua", "OCaml", "Clojure", "Solidity",
]
LANG_ALIASES = {"golang": "Go", "ts": "TypeScript", "js": "JavaScript", "node": "JavaScript", "cpp": "C++", "py": "Python"}
KEYWORDS = [
    "async", "networking", "quic", "http", "grpc", "database", "storage", "compiler", "wasm", "webassembly",
    "kubernetes", "react", "nextjs", "llm", "ml", "machine learning", "embedded", "cryptography", "security",
    "observability", "graphql", "streaming", "distributed", "runtime", "cli", "gpu", "data", "frontend", "devops",
]

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "languages": {"type": "array", "items": {"type": "string"}},
        "keywords": {"type": "array", "items": {"type": "string"}},
        "seed_repos": {"type": "array", "items": {"type": "string"}},
        "seed_users": {"type": "array", "items": {"type": "string"}},
        "window_days": {"type": "integer"},
        "min_merged_prs": {"type": "integer"},
        "max_candidates": {"type": "integer"},
        "location": {"type": "string"},
        "rationale": {"type": "string"},
    },
    "required": [
        "languages", "keywords", "seed_repos", "seed_users", "window_days", "min_merged_prs",
        "max_candidates", "location", "rationale",
    ],
    "additionalProperties": False,
}

SYSTEM = """You plan searches for an open-source contributor sourcing agent that only reads public GitHub data.
Convert the recruiter's request into search criteria.
- languages: GitHub linguist names (e.g. "Rust", "TypeScript", "Go"). Only languages the recruiter asked for.
- keywords: 0-3 short topical terms that would appear in PR titles or repo topics (e.g. "async", "quic").
- seed_repos: 0-4 well-known upstream repositories ("owner/name") central to that stack. Prefer repos from the
  KNOWN REPOS list when one is given. Never invent repositories.
- seed_users: GitHub logins the recruiter explicitly named (without "@"), else [].
- window_days: recency window in days (default 180; "last year" = 365; "6 months" = 180).
- min_merged_prs: default 2. max_candidates: default 15 (cap 50).
- location: the preferred location if stated, else "".
- rationale: one sentence explaining the plan, addressed to the recruiter.
Never include personal data or guesses about people."""


def heuristic_plan(query: str) -> tuple[Criteria, str]:
    q = query or ""
    low = q.lower()
    langs: list[str] = []
    for lang in LANGUAGES:
        pattern = r"(?<![\w+#])" + re.escape(lang.lower()) + r"(?![\w+#])"
        if re.search(pattern, low) and not (lang == "C" and re.search(r"\bc\s*(?:\+\+|#)", low)):
            langs.append(lang)
    for alias, lang in LANG_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", low) and lang not in langs:
            langs.append(lang)
    kws = [k for k in KEYWORDS if re.search(rf"\b{re.escape(k)}\b", low)][:3]
    repos = re.findall(r"\b([A-Za-z0-9][\w.-]*/[A-Za-z0-9][\w.-]+)\b", q)
    repos = [r for r in repos if "." not in r.split("/")[0] and not r.lower().startswith(("http", "www"))]
    users = re.findall(r"(?<![\w/])@([A-Za-z0-9][\w-]{0,38}(?:\[bot\])?)", q)

    window = 180
    m = re.search(r"(\d+)\s*(day|week|month|year)s?", low)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        window = n * {"day": 1, "week": 7, "month": 30, "year": 365}[unit]
    elif "last year" in low or "past year" in low:
        window = 365
    window = max(7, min(window, 1825))

    min_prs = 2
    m = re.search(r"(?:at least|min(?:imum)?|>=)\s*(\d+)\s*(?:merged\s*)?prs?", low)
    if m:
        min_prs = max(1, min(int(m.group(1)), 20))

    location = None
    m = re.search(r"\b(?:in|from|based in)\s+([A-Z][A-Za-z]+(?:\s[A-Z][A-Za-z]+)?)", q)
    if m and m.group(1).lower() not in {x.lower() for x in LANGUAGES}:
        location = m.group(1)
    else:
        m = re.search(r"\b([A-Z][A-Za-z]+)\s+(?:preferred|only|based)\b", q)
        if m and m.group(1).lower() not in {x.lower() for x in LANGUAGES}:
            location = m.group(1)

    c = Criteria(languages=langs, keywords=kws, seed_repos=repos, seed_users=users, window_days=window,
                 min_merged_prs=min_prs, location=location)
    rationale = (
        f"Search merged PRs from the last {window} days"
        + (f" in {', '.join(langs)}" if langs else "")
        + (f" mentioning {', '.join(kws)}" if kws else "")
        + (f", plus contributors of {', '.join(repos)}" if repos else "")
        + f"; shortlist developers with ≥{min_prs} qualifying PRs."
    )
    return c, rationale


async def plan_criteria(query: str, known_repos: list[str] | None = None) -> tuple[Criteria, dict]:
    llm = get_llm()
    hint = f"\nKNOWN REPOS (prefer these for seed_repos): {', '.join(known_repos)}" if known_repos else ""
    out = await llm.json(SYSTEM + hint, f"Recruiter request:\n{query}", PLAN_SCHEMA, max_tokens=4000)
    if out:
        try:
            c = Criteria(
                languages=out["languages"],
                keywords=out["keywords"][:3],
                seed_repos=[r for r in out["seed_repos"] if re.fullmatch(r"[\w.-]+/[\w.-]+", r)][:4],
                seed_users=[u.lstrip("@") for u in out["seed_users"]][:10],
                window_days=max(7, min(int(out["window_days"]), 1825)),
                min_merged_prs=max(1, min(int(out["min_merged_prs"]), 20)),
                max_candidates=max(1, min(int(out["max_candidates"]), 50)),
                location=out["location"] or None,
            )
            return c, {"planner": llm.label, "rationale": out["rationale"]}
        except Exception:
            pass
    c, rationale = heuristic_plan(query)
    return c, {"planner": "deterministic", "rationale": rationale}
