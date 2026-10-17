"""'Why this person' — written only from the evidence JSON, with citations that must exist in that evidence."""

import json
import re

from app.llm import get_llm

SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "citations": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "citations"],
    "additionalProperties": False,
}

SYSTEM = """You write a 2-sentence recruiter-facing summary of why a developer fits a search.
Use ONLY facts in the EVIDENCE JSON. Do not mention gender, age, nationality, or anything not in the evidence.
Do not speculate about the person, their employer or contact details.
Reference specific PRs by putting their exact URL from the evidence in parentheses after the claim.
Return the URLs you cited in `citations`. Keep it under 60 words."""

URL_RE = re.compile(r"https?://[^\s)\]]+")


def ground(summary: str, citations: list[str], allowed: set[str]) -> tuple[str, list[str]]:
    """Strip any URL not present in the evidence — the LLM cannot introduce new sources."""
    clean = URL_RE.sub(lambda m: m.group(0) if m.group(0).rstrip(".,;") in allowed else "", summary)
    clean = re.sub(r"\(\s*\)", "", clean)
    clean = re.sub(r"\s{2,}", " ", clean).strip()
    cites = [c for c in dict.fromkeys(citations) if c in allowed]
    for url in URL_RE.findall(clean):
        u = url.rstrip(".,;")
        if u in allowed and u not in cites:
            cites.append(u)
    return clean, cites


def template_summary(evidence: dict) -> tuple[str, list[str]]:
    prs = evidence["qualifying_prs"]
    if not prs:
        return "", []
    top = max(prs, key=lambda p: p["repo_stars"])
    latest = max(prs, key=lambda p: p["merged_at"])
    repos = sorted({p["repo"] for p in prs})
    text = (
        f"Merged {len(prs)} PR(s) into {', '.join(repos[:3])} within the last {evidence['window_days']} days, "
        f"most recently “{latest['title']}” on {latest['merged_at'][:10]} ({latest['url']}). "
        f"Strongest signal: work in {top['repo']} ({top['repo_stars']:,}★) ({top['url']})."
    )
    return text, list(dict.fromkeys([latest["url"], top["url"]]))


async def summarize(evidence: dict) -> tuple[str, list[str], str]:
    """Returns (summary, citations, source_label)."""
    allowed = {p["url"] for p in evidence["qualifying_prs"]}
    llm = get_llm()
    out = await llm.json(SYSTEM, "EVIDENCE:\n" + json.dumps(evidence, indent=1), SCHEMA, max_tokens=3000)
    if out and out.get("summary"):
        text, cites = ground(out["summary"], out.get("citations", []), allowed)
        if text and cites:
            return text, cites, llm.label
    text, cites = template_summary(evidence)
    return text, cites, "template"
