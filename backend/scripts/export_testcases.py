"""Run TC1–TC4 through the real harness and write docs/TEST_CASES.md from the stored records.

    uv run python scripts/export_testcases.py            # fixture mode
    uv run python scripts/export_testcases.py --live     # live mode (needs GITHUB_TOKEN + logins)
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal, init_db  # noqa: E402
from app.models import TestRun  # noqa: E402
from app.testcases import CASES, run_all  # noqa: E402

DOCS = Path(__file__).resolve().parents[2] / "docs"


def verdict(p):
    return "✅ PASS" if p is True else "❌ FAIL" if p is False else "⚪ INCONCLUSIVE"


async def main(mode: str):
    await init_db()
    batch = await run_all(mode)
    async with SessionLocal() as db:
        rows = (await db.execute(select(TestRun).where(TestRun.batch_id == batch).order_by(TestRun.tc_id))).scalars().all()

    out = [f"## {mode.capitalize()} mode — batch `{batch}` · commit `{rows[0].commit_sha}` · {rows[0].ts:%Y-%m-%d %H:%M UTC}\n"]
    out.append("| Case | Scenario | Expected | Actual | Result |\n|---|---|---|---|---|")
    for r, c in zip(rows, CASES, strict=True):
        out.append(f"| **{r.tc_id}** | {c.label} | {r.expected} | {r.actual} | {verdict(r.passed)} |")
    for r in rows:
        cand = r.evidence.get("candidate") or {}
        out.append(f"\n### {r.tc_id} — {r.label}\n")
        out.append(f"- **Input:** `@{r.input.get('login')}` · languages `{(r.input.get('criteria') or {}).get('languages')}` · "
                   f"window `{(r.input.get('criteria') or {}).get('window_days')}` days · min merged PRs "
                   f"`{(r.input.get('criteria') or {}).get('min_merged_prs')}` (vet-only run)")
        out.append(f"- **Expected:** {r.expected}")
        out.append(f"- **Actual:** {r.actual}")
        out.append(f"- **Result:** {verdict(r.passed)}" + (f" — {r.explanation}" if r.explanation else ""))
        out.append(f"- **Agent run:** `/runs/{r.run_id}` (full trace, evidence, verification)")
        out.append(f"- **Contact field:** `{cand.get('contact_email')!r}`")
        out.append("\n| Evidence | Repo | Merged | Counted | Rule checks | Re-verified |\n|---|---|---|---|---|---|")
        for it in r.evidence.get("items", [])[:8]:
            checks = " ".join(("✓" if v else "✗") + k for k, v in it["rule_checks"].items())
            ver = "—" if it["verified"] is None else ("✓" if it["verified"] else f"✗ {it['verify_error']}")
            out.append(f"| [{it['title']}]({it['url']}) | `{it['repo']}`{' (fork)' if it['repo_is_fork'] else ''} | "
                       f"{(it['merged_at'] or '')[:10]} | {'yes' if it['qualifies'] else 'no'} | {checks} | {ver} |")
    return "\n".join(out)


if __name__ == "__main__":
    mode = "live" if "--live" in sys.argv else "fixture"
    body = asyncio.run(main(mode))
    header = (DOCS / "TEST_CASES.header.md").read_text()
    target = DOCS / "TEST_CASES.md"
    existing = target.read_text() if target.exists() else ""
    sections = {"fixture": "", "live": ""}
    for m in sections:
        marker = f"<!-- {m} -->"
        if marker in existing:
            sections[m] = existing.split(marker)[1].split("<!-- /")[0]
    sections[mode] = "\n" + body + "\n"
    target.write_text(header + "".join(f"<!-- {m} -->{sections[m]}<!-- /{m} -->\n\n" for m in sections))
    print(f"wrote {target}")
