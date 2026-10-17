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

<!-- fixture -->
## Fixture mode — batch `91d2e810bb69` · commit `local` · 2026-10-17 13:47 UTC

| Case | Scenario | Expected | Actual | Result |
|---|---|---|---|---|
| **TC1** | Recent merged PRs in target stack | Shortlisted with PR links | SHORTLISTED — 3 qualifying PR link(s), 3/3 re-verified | ✅ PASS |
| **TC2** | Repository is only a fork | Not counted as contribution | EXCLUDED_FORK_ONLY — 5 fork item(s) seen, 0 counted | ✅ PASS |
| **TC3** | Last activity 3 years ago | Excluded by recency window | EXCLUDED_RECENCY — Relevant work exists, but the latest qualifying merged PR was 2023-10-09 (1104 days ago), outside the 180-day window. | ✅ PASS |
| **TC4** | No public email | Contact left blank, never guessed | contact_email = None; SHORTLISTED | ✅ PASS |

### TC1 — Recent merged PRs in target stack

- **Input:** `@tc1-active-rustacean` · languages `['Rust']` · window `180` days · min merged PRs `2` (vet-only run)
- **Expected:** Shortlisted with PR links
- **Actual:** SHORTLISTED — 3 qualifying PR link(s), 3/3 re-verified
- **Result:** ✅ PASS
- **Agent run:** `/runs/9f83bfc378bb` (full trace, evidence, verification)
- **Contact field:** `'asha.verma@example.com'`

| Evidence | Repo | Merged | Counted | Rule checks | Re-verified |
|---|---|---|---|---|---|
| [io: avoid spurious wakeups in the epoll driver under contention](https://github.com/asyncforge/reactor/pull/4821) | `asyncforge/reactor` | 2026-10-11 | yes | ✓merged ✓in_window ✓base_not_fork ✓not_own_repo ✓stack_match | ✓ |
| [sync: add cancellation-safe Notify::notified_owned](https://github.com/asyncforge/reactor/pull/4790) | `asyncforge/reactor` | 2026-09-28 | yes | ✓merged ✓in_window ✓base_not_fork ✓not_own_repo ✓stack_match | ✓ |
| [Implement async stream prioritisation for HTTP/3 frames](https://github.com/meshwire/quic-rs/pull/1312) | `meshwire/quic-rs` | 2026-09-20 | yes | ✓merged ✓in_window ✓base_not_fork ✓not_own_repo ✓stack_match | ✓ |

### TC2 — Repository is only a fork

- **Input:** `@tc2-fork-only` · languages `['Rust']` · window `180` days · min merged PRs `2` (vet-only run)
- **Expected:** Not counted as contribution
- **Actual:** EXCLUDED_FORK_ONLY — 5 fork item(s) seen, 0 counted
- **Result:** ✅ PASS
- **Agent run:** `/runs/616c608c8a80` (full trace, evidence, verification)
- **Contact field:** `'rohan.m@example.com'`

| Evidence | Repo | Merged | Counted | Rule checks | Re-verified |
|---|---|---|---|---|---|
| [Fork of asyncforge/reactor — last push](https://github.com/tc2-fork-only/reactor) | `tc2-fork-only/reactor` (fork) | 2026-10-14 | no | ✗base_not_fork | — |
| [Experiment: custom async scheduler (fork only)](https://github.com/tc2-fork-only/reactor/pull/3) | `tc2-fork-only/reactor` (fork) | 2026-10-13 | no | ✓merged ✓in_window ✗base_not_fork ✗not_own_repo ✓stack_match | — |
| [Rebase on upstream + tweak timer wheel](https://github.com/tc2-fork-only/reactor/pull/2) | `tc2-fork-only/reactor` (fork) | 2026-10-05 | no | ✓merged ✓in_window ✗base_not_fork ✗not_own_repo ✓stack_match | — |
| [Fork of meshwire/quic-rs — last push](https://github.com/tc2-fork-only/quic-rs) | `tc2-fork-only/quic-rs` (fork) | 2026-09-25 | no | ✗base_not_fork | — |
| [Try zero-copy async recv path](https://github.com/tc2-fork-only/quic-rs/pull/1) | `tc2-fork-only/quic-rs` (fork) | 2026-09-22 | no | ✓merged ✓in_window ✗base_not_fork ✗not_own_repo ✓stack_match | — |

### TC3 — Last activity 3 years ago

- **Input:** `@tc3-stale-dev` · languages `['Rust']` · window `180` days · min merged PRs `2` (vet-only run)
- **Expected:** Excluded by recency window
- **Actual:** EXCLUDED_RECENCY — Relevant work exists, but the latest qualifying merged PR was 2023-10-09 (1104 days ago), outside the 180-day window.
- **Result:** ✅ PASS
- **Agent run:** `/runs/59007bf85107` (full trace, evidence, verification)
- **Contact field:** `'meera.iyer@example.com'`

| Evidence | Repo | Merged | Counted | Rule checks | Re-verified |
|---|---|---|---|---|---|
| [runtime: work-stealing scheduler rewrite](https://github.com/asyncforge/reactor/pull/2210) | `asyncforge/reactor` | 2023-10-09 | no | ✓merged ✗in_window ✓base_not_fork ✓not_own_repo ✓stack_match | — |
| [time: hierarchical timer wheel](https://github.com/asyncforge/reactor/pull/2188) | `asyncforge/reactor` | 2023-09-12 | no | ✓merged ✗in_window ✓base_not_fork ✓not_own_repo ✓stack_match | — |
| [net: async UDP socket support](https://github.com/asyncforge/reactor/pull/2101) | `asyncforge/reactor` | 2023-07-15 | no | ✓merged ✗in_window ✓base_not_fork ✓not_own_repo ✓stack_match | — |
| [Initial async congestion control](https://github.com/meshwire/quic-rs/pull/640) | `meshwire/quic-rs` | 2023-06-30 | no | ✓merged ✗in_window ✓base_not_fork ✓not_own_repo ✓stack_match | — |

### TC4 — No public email

- **Input:** `@tc4-no-email` · languages `['Rust']` · window `180` days · min merged PRs `2` (vet-only run)
- **Expected:** Contact left blank, never guessed
- **Actual:** contact_email = None; SHORTLISTED
- **Result:** ✅ PASS
- **Agent run:** `/runs/dfd325a43017` (full trace, evidence, verification)
- **Contact field:** `None`

| Evidence | Repo | Merged | Counted | Rule checks | Re-verified |
|---|---|---|---|---|---|
| [Fix async flow-control window update race](https://github.com/meshwire/quic-rs/pull/1340) | `meshwire/quic-rs` | 2026-10-08 | yes | ✓merged ✓in_window ✓base_not_fork ✓not_own_repo ✓stack_match | ✓ |
| [Add async connection migration tests](https://github.com/meshwire/quic-rs/pull/1298) | `meshwire/quic-rs` | 2026-09-14 | yes | ✓merged ✓in_window ✓base_not_fork ✓not_own_repo ✓stack_match | ✓ |
| [async compaction: bound memory during merges](https://github.com/ferrous-db/tidekv/pull/910) | `ferrous-db/tidekv` | 2026-08-20 | yes | ✓merged ✓in_window ✓base_not_fork ✓not_own_repo ✓stack_match | ✓ |
<!-- /fixture -->

<!-- live --><!-- /live -->

