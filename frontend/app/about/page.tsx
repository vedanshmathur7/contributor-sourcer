import { BadgeCheck, Ban, Brain, Database, Eye, GitFork, KeyRound, Lock, MailX, Scale, Search, ShieldCheck, Trash2, UserCheck } from "lucide-react";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "How it works · Privacy & safety" };

const LOOP = [
  { icon: Brain, t: "Plan", d: "The LLM turns the recruiter's request into structured, editable criteria (languages, keywords, seed repos, window, minimum PRs). The recruiter reviews it before anything runs." },
  { icon: Search, t: "Search", d: "Start from contributions, not profiles: GitHub's search API for merged PRs inside the window, plus all-time contributors of seed repos, plus any profiles the recruiter asked to vet." },
  { icon: Eye, t: "Enrich", d: "GraphQL fetch of each profile and its merged PRs, including each base repository's fork status, owner, stars and language." },
  { icon: Scale, t: "Classify", d: "Deterministic code — not the LLM — decides who qualifies, with a machine-readable reason code and a human sentence for every decision." },
  { icon: Brain, t: "Adapt", d: "If too few people qualify, the agent widens where it looks (new seed repos from the evidence, or no keyword filter). It can never loosen what counts." },
  { icon: BadgeCheck, t: "Verify", d: "A separate verifier re-fetches every cited PR via REST and re-checks it. Any failure blocks the candidate until a human reviews it." },
  { icon: UserCheck, t: "Approve", d: "The agent only proposes a draft. A named human approves per candidate and finalises; undo is possible until export." },
];

const RULES = [
  ["merged", "The PR was merged — opened or closed PRs never count."],
  ["in_window", "Merged inside the recency window (TC3: activity three years ago is excluded, and the date is stated)."],
  ["base_not_fork", "Merged into a repository that is not itself a fork (TC2). PRs from your fork into a real upstream do count."],
  ["not_own_repo", "Not self-merged into the candidate's own repo. Own projects are a small bonus, never sufficient alone."],
  ["stack_match", "The upstream repo's primary language matches the target stack."],
  ["not a bot", "dependabot, renovate and other automated accounts are excluded."],
];

const SAFETY = [
  { icon: Database, t: "Public data only", d: "Only public GitHub data via the official REST and GraphQL APIs. No scraping, no logged-in sessions, no private repos." },
  { icon: MailX, t: "Public email field only", d: "Contact comes only from the profile's public email field. We never harvest commit emails, pattern-guess addresses or let an LLM infer them (TC4)." },
  { icon: Ban, t: "Limits respected", d: "Rate limits are waited out with a visible countdown — never bypassed. No CAPTCHA or OTP is ever bypassed." },
  { icon: KeyRound, t: "Read-only, server-side token", d: "A fine-grained token with public read-only access lives on the server and is never sent to the browser." },
  { icon: GitFork, t: "Synthetic test data", d: "Fixture mode uses fictional, GitHub-shaped personas, as the brief requires wherever personal information is involved." },
  { icon: Trash2, t: "Retention & deletion", d: "Runs are kept so recruiters can audit decisions. Any run — trace, candidates, evidence — can be deleted from its page; the audit log records the deletion." },
  { icon: Lock, t: "Human in control", d: "Nothing irreversible happens without approval: finalising, exporting and sharing all require an explicit human action, recorded with name and time." },
  { icon: ShieldCheck, t: "Grounded explanations", d: "LLM summaries are generated only from the evidence JSON; any URL not present in the evidence is stripped before display." },
];

export default function About() {
  return (
    <div className="container max-w-4xl py-12">
      <h1 className="text-3xl font-semibold tracking-tight">How it works</h1>
      <p className="mt-2 max-w-2xl text-muted-foreground">
        A recruiter describes who they need. The agent finds developers whose <em>recent, merged, upstream</em> work proves it — and shows its reasoning at every step.
      </p>

      <ol className="mt-8 grid gap-3 sm:grid-cols-2">
        {LOOP.map((s, i) => (
          <li key={s.t} className="flex gap-3 rounded-xl border p-4">
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-primary/10 text-primary"><s.icon className="h-4 w-4" /></span>
            <div>
              <div className="text-sm font-medium"><span className="mr-1.5 font-mono text-xs text-muted-foreground">0{i + 1}</span>{s.t}</div>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{s.d}</p>
            </div>
          </li>
        ))}
      </ol>

      <h2 className="mt-14 text-xl font-semibold tracking-tight">What counts as a contribution</h2>
      <p className="mt-1 text-sm text-muted-foreground">A merged PR qualifies only if every rule passes. These are plain, unit-tested code paths.</p>
      <div className="mt-4 divide-y overflow-hidden rounded-xl border">
        {RULES.map(([k, d]) => (
          <div key={k} className="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:gap-6">
            <code className="w-36 shrink-0 font-mono text-xs text-primary">{k}</code>
            <span className="text-sm text-muted-foreground">{d}</span>
          </div>
        ))}
      </div>

      <h2 id="privacy" className="mt-14 text-xl font-semibold tracking-tight">Privacy & safety</h2>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {SAFETY.map((s) => (
          <div key={s.t} className="flex gap-3 rounded-xl border p-4">
            <s.icon className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
            <div>
              <div className="text-sm font-medium">{s.t}</div>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{s.d}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
