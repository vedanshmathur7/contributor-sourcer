# Submission checklist (Ziro portal · Build & Submit opens 20 Oct 2026, 11:00 AM IST)

## Links to paste
| Field | Value |
|---|---|
| Deployed agent | https://contributor-sourcer.onrender.com |
| API / OpenAPI docs | https://contributor-sourcer-api.onrender.com/docs |
| Source code | https://github.com/vedanshmathur7/contributor-sourcer (private: make it public, or add the organisers as collaborators, before submitting) |
| Test cases (live page) | https://contributor-sourcer.onrender.com/tests |
| Test cases (document) | `docs/TEST_CASES.md` in the repo |
| Demo script | `docs/DEMO_SCRIPT.md` |
| Presentation outline | `docs/PRESENTATION.md` (10 slides) |

## Before you submit
1. **Add the secrets in Render** (Dashboard → `contributor-sourcer-api` → Environment), then save. The service redeploys automatically.
   - `LLM_API_KEY`: an Anthropic API key. It switches the planner, adaptation and summaries from deterministic to `claude-opus-5-5`.
   - `GITHUB_TOKEN`: a fine-grained token with public repositories read-only access. It enables Live mode.
   - `DATABASE_URL` (recommended): a Supabase Transaction-pooler URL, so runs survive restarts.
2. **Live-mode test cases:** on `/tests`, open the Live tab and enter a real public login per case:
   - TC1: someone with recent merged PRs in the stack
   - TC2: an account whose work is only in forks
   - TC3: someone last active about 3 years ago
   - TC4: someone with no public email

   Then click Run, and run `uv run python scripts/export_testcases.py --live` to add the live results to `docs/TEST_CASES.md`.
3. **Screenshots:** capture `/`, a run trace, the candidate drawer, the review screen and `/tests` for the deck.
4. **Backup video:** record the 3-minute `DEMO_SCRIPT.md` walkthrough (Fixture mode is fully reproducible).
5. **Repo visibility:** make the GitHub repo public, or share it with the organisers.
6. **Warm-up:** open the site a minute before judging (the keep-alive workflow already pings it).

## How the brief maps to the build
| Brief | Where |
|---|---|
| Collect details: skills and recency | `/` search box and criteria chips, then the plan review screen (`planner.py`) |
| Judge public contributions only | `backend/app/rules.py`: deterministic and unit-tested |
| Find: public code-hosting profiles | `backend/app/github/live.py`: the official REST and GraphQL APIs |
| Take action: compile shortlist, with human approval | `/runs/{id}/review` and `routers/review.py`: approve, finalise, audit, undo, export |
| Verify: repos and activity | `backend/app/verifier.py`: a separate REST re-fetch step |
| Output: shortlist with evidence | Candidate drawer, CSV/JSON export and a read-only share link |
| Safety rules | Approval gate, synthetic fixtures, rate limits respected, no CAPTCHA/OTP handling, `/about` |
