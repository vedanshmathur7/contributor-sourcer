# Official test cases: TC1–TC4

Each case runs as a **labelled run of the real agent**. The agent runs in vet-only mode on the scenario's profile, and each run stores:
- the input
- the expected result
- the actual result (taken from what the agent stored)
- the evidence
- a pass/fail verdict
- an explanation of any difference

This document is **generated** from those stored records by `backend/scripts/export_testcases.py`. The same records appear on the `/tests` page, and each one links to its full agent trace.

* **Fixture mode** uses synthetic, GitHub-shaped personas. The brief requires mock or synthetic data wherever personal information is involved. The results are fully reproducible (`pytest tests/test_testcases.py`).
* **Live mode** runs the same harness against real public GitHub accounts. Live data changes over time. Any mismatch is recorded as a failure or as inconclusive, with the reason. It is never reported as a pass.

| Rule (code) | Proves |
|---|---|
| `merged` and `in_window` | TC1 (recent merged PRs count) and TC3 (3-year-old activity is excluded, with the date stated) |
| `base_not_fork` | TC2: PRs merged into forks, and work that never left a fork, are not counted |
| `contact.resolve_contact()` reads only the public profile email field | TC4: a blank contact stays blank and is never guessed |
| `verifier.py` re-fetches every cited PR via REST | TC1 evidence is independently re-verified |

