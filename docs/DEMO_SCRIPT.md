# 3-minute demo script

**Setup:** open the deployed site a minute early so the backend is awake. Have two tabs ready: `/` and `/tests`. Use dark mode.

---

### 0:00–0:20 · The problem
> "Recruiters source developers from profiles and keywords, and both are easy to fake. A fork with 40 commits looks active. A famous name from three years ago looks current. A guessed email is a privacy problem. Our agent starts from **merged contributions**, and it shows its evidence at every step."

### 0:20–0:45 · Plan
1. On `/`, click the example chip **"Rust async networking engineers active in the last 6 months, India preferred"**, then **Plan search**.
2. On the plan review screen:
   > "The LLM turned my sentence into structured criteria. I can edit any of them. Notice the guardrail note: the agent may widen *where it looks*, never *what counts*."
3. Click **Run agent**.

### 0:45–1:35 · The live agent trace
Point at the left panel while it streams:
- **Search:** "It starts from merged PRs in the window, not from profiles."
- **Classify:** expand the step and show the decisions:
  - "@tc2-fork-only is **excluded, fork-only**: their work never reached an upstream." *(TC2)*
  - "The bot is excluded, and so is the Python developer: off-stack."
- **Adapt:** "Only 4 shortlisted, so the agent *decided* to mine contributors of the repos it found. That surfaced @tc3-stale-dev, and the rules excluded them: last merged PR three years ago, with the date stated." *(TC3)*
- **Verify:** "A separate verifier re-fetched every cited PR from the REST API. One repo has since been deleted, so that candidate is **blocked** until a human reviews it."
- Show the bar at the bottom: *"Checked N PRs across N developers in N s."*

### 1:35–2:10 · Evidence
1. Click **Karan Shah (@tc4-no-email)**.
   - Contact: **"Not public: we never guess or harvest addresses."** *(TC4)*
   - "Why this person": the summary's citation chips link to real PR URLs. URLs not found in the evidence are stripped.
   - Score breakdown, then the evidence table with rule checks and **re-verified** stamps. *(TC1)*
2. Close, open the **Excluded** tab, and click **@tc3-stale-dev** to show "Why excluded?".

### 2:10–2:40 · The human approval gate
1. Click **Review & approve**, then **Approve all verified**.
2. Try approving the blocked candidate. A modal requires an override note. Cancel it.
3. Type your name and click **Approve & finalise**. The confirmation shows the exact diff.
4. Show the export options: **CSV**, **read-only share link**, and **Undo** (available until export).
   > "Nothing is final, exported or shared without a named human. All of it is in the audit log."

### 2:40–3:00 · Proof
1. Go to `/tests` and click **Re-run TC1–TC4**. All four show **PASS**, each with input, expected, actual, evidence and a link to its agent trace.
2. Close with:
   > "Deterministic rules, a real agent loop, independent verification and a human in control. 54 automated tests back it up."

---

**Backup:** if the network fails, play the recorded video of this same script, recorded beforehand.
