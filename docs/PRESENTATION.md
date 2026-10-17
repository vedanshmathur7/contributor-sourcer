# Presentation outline (10 slides)

**1. Problem.** Recruiters can't tell real, recent open-source work from noise.
- Profiles, stars and follower counts are proxies, and they are gameable.
- Forks look like activity. Old fame looks current. Guessed emails are a privacy liability.
- One line: *"Hire from the merge log, not the résumé."*

**2. Why existing sourcing fails**
- Keyword search on profiles misses the people who actually ship upstream.
- Tools count commits in forks and self-owned repos as contributions.
- There is no evidence trail, so a recruiter can't defend a shortlist.
- "AI sourcing" black boxes guess contact details and hallucinate claims.

**3. Demo.** Live: request, plan, trace, evidence, approval. Follow `DEMO_SCRIPT.md`.

**4. Architecture**
- Next.js (Vercel) talks to FastAPI (Render) over REST and SSE, with Supabase Postgres for storage.
- The official GitHub REST and GraphQL APIs are called with ETag caching, rate limiting and retries.
- Fixture mode uses a synthetic GitHub-shaped world, so the brief's personal-data rule is satisfied.
- Pluggable LLM: Anthropic `claude-opus-5-5`, OpenAI, or a deterministic fallback.

**5. The agent loop** (agentic capability, 25 pts)
- Plan → Search → Enrich → Classify → **Adapt** → Score → Explain → **Verify** → Propose → Human → Finalise.
- Every step is a recorded tool call: inputs, rationale, duration, decisions. All of it is streamed live and permalinked.
- Adaptive discovery: the agent decides to widen *where* it looks, under guardrails. It never changes *what counts*.
- Failure handling: rate-limit countdowns, retry with backoff, and no candidate is ever silently dropped.

**6. Decision rules** (problem fit)
- Deterministic and unit-tested: merged, in window, upstream not a fork, not own repo, stack match, not a bot.
- Reason codes plus human sentences, and "Why excluded?" for every exclusion.
- Contact comes from the public email field only. It is never guessed.
- A transparent 0–100 evidence score with its breakdown.

**7. Verification**
- A separate module and a separate step: every cited PR is re-fetched via REST, never from the cached search.
- Five checks: resolves, merged, in window, author matches, upstream not a fork.
- Failures block approval, and an override requires a note, which is audited.
- The LLM summaries are grounded as well: citations are validated and unknown URLs are stripped.

**8. Test cases**
- TC1–TC4 run as labelled agent runs, with input, expected, actual, evidence and verdict. Fixture mode: **4 of 4 pass**.
- Live-mode runs are recorded honestly.
- 54 automated tests cover every rule, the full loop, the approval gate and the harness. They run in CI.

**9. Safety**
- Public data only, through the official API. Limits are respected and never bypassed. No CAPTCHA or OTP bypass.
- Read-only, server-side token. Synthetic data for testing. Runs can be deleted. Full audit log.
- A human is required for finalise, export and share, and undo works until export.

**10. Impact and next steps**
- Minutes instead of hours per role, and a shortlist the recruiter can defend line by line.
- Next steps:
  - more code hosts (GitLab, Codeberg)
  - PR-review and issue-triage signals
  - ATS export (Greenhouse, Lever)
  - team-level dedupe
  - an opt-in candidate outreach flow with consent
