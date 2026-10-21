"use client";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowLeft,
  ArrowRight,
  BadgeCheck,
  Brain,
  Compass,
  FileSearch,
  GitFork,
  GitMerge,
  Lock,
  MailX,
  MessageSquareQuote,
  Scale,
  Search,
  Send,
  ShieldCheck,
  Sigma,
  UserCheck,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Logo } from "@/components/logo";
import { cn } from "@/lib/utils";

const SITE = "https://contributor-sourcer.onrender.com";

function Bullets({ items }: { items: React.ReactNode[] }) {
  return (
    <ul className="mt-6 space-y-3 text-base text-muted-foreground sm:text-lg">
      {items.map((it, i) => (
        <li key={i} className="flex gap-3">
          <span className="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
          <span>{it}</span>
        </li>
      ))}
    </ul>
  );
}

function Kicker({ n, children }: { n: number; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.18em] text-primary">
      <span className="font-mono">{String(n).padStart(2, "0")}</span>
      <span className="h-px w-6 bg-primary/40" />
      {children}
    </div>
  );
}

const LOOP = [
  { icon: Brain, t: "Plan", d: "LLM → editable criteria" },
  { icon: Search, t: "Search", d: "merged PRs in window" },
  { icon: FileSearch, t: "Enrich", d: "GraphQL + fork status" },
  { icon: Scale, t: "Classify", d: "deterministic rules" },
  { icon: Compass, t: "Adapt", d: "widen where it looks" },
  { icon: Sigma, t: "Score", d: "0–100 breakdown" },
  { icon: MessageSquareQuote, t: "Explain", d: "grounded, cited" },
  { icon: BadgeCheck, t: "Verify", d: "independent REST re-fetch" },
  { icon: Send, t: "Propose", d: "draft only" },
  { icon: UserCheck, t: "Approve", d: "human, audited" },
];

const SLIDES: { title: string; body: React.ReactNode }[] = [
  {
    title: "Title",
    body: (
      <div className="flex h-full flex-col justify-center">
        <Logo className="h-12 w-12" />
        <h1 className="mt-8 text-balance text-5xl font-semibold tracking-tight sm:text-7xl">
          Hire from the <span className="bg-gradient-to-r from-primary to-sky-400 bg-clip-text text-transparent">merge log</span>,<br />not the résumé.
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-muted-foreground sm:text-xl">
          Open-Source Contributor Sourcer: an AI agent that finds developers with <b className="text-foreground">real, recent</b> public contributions, with evidence for every claim,
          independent verification, and a human approval gate.
        </p>
        <div className="mt-10 flex flex-wrap gap-3 text-sm text-muted-foreground">
          <span className="rounded-full border px-3 py-1">Ziro Agentic AI Hackathon 2026</span>
          <span className="rounded-full border px-3 py-1">Developer & Enterprise AI</span>
          <span className="rounded-full border px-3 py-1">Vedansh Mathur · solo</span>
        </div>
      </div>
    ),
  },
  {
    title: "Problem",
    body: (
      <>
        <Kicker n={1}>Problem</Kicker>
        <h2 className="mt-4 text-4xl font-semibold tracking-tight sm:text-5xl">Recruiters can&apos;t tell real work from noise.</h2>
        <Bullets
          items={[
            "Profiles, stars and follower counts are proxies, and they're gameable.",
            "A fork with 40 commits looks like activity. A famous name from 2021 looks current.",
            "An email guessed from a commit header is a privacy liability.",
            <>Recruiters need a shortlist they can <b className="text-foreground">defend line by line</b>.</>,
          ]}
        />
      </>
    ),
  },
  {
    title: "Why sourcing fails",
    body: (
      <>
        <Kicker n={2}>Why existing sourcing fails</Kicker>
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          {[
            ["Profile keyword search", "misses the people who actually ship upstream."],
            ["Commit counters", "count work in forks and self-owned repos as contributions."],
            ["No evidence trail", "nobody can check why someone was picked."],
            ["Black-box “AI sourcing”", "guesses contact details and hallucinates claims."],
          ].map(([t, d]) => (
            <div key={t} className="rounded-2xl border bg-card p-6">
              <div className="text-lg font-semibold">{t}</div>
              <div className="mt-1 text-muted-foreground">{d}</div>
            </div>
          ))}
        </div>
      </>
    ),
  },
  {
    title: "Demo",
    body: (
      <>
        <Kicker n={3}>Live demo</Kicker>
        <h2 className="mt-4 text-4xl font-semibold tracking-tight sm:text-5xl">Request → plan → live trace → evidence → approval</h2>
        <Bullets
          items={[
            <>The recruiter types: <i className="text-foreground">&ldquo;Rust async networking engineers active in the last 6 months, India preferred&rdquo;</i></>,
            "The planner proposes criteria, and the recruiter edits them and runs the agent.",
            "The trace streams every tool call, decision and reason live.",
            "The evidence drawer shows PR links, rule checks, re-verified stamps and a score breakdown.",
            "Approve & finalise, then export CSV/JSON or share a read-only link.",
          ]}
        />
        <div className="mt-8 flex flex-wrap gap-3">
          <a href={SITE} target="_blank" rel="noreferrer" className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">Open the live app ↗</a>
          <a href="/demo" className="rounded-lg border px-4 py-2 text-sm font-medium">Watch the demo video</a>
        </div>
      </>
    ),
  },
  {
    title: "Architecture",
    body: (
      <>
        <Kicker n={4}>Architecture</Kicker>
        <div className="mt-8 grid items-stretch gap-4 sm:grid-cols-3">
          {[
            ["Next.js 14 UI", "Search, plan review, live SSE trace, evidence drawer, approval, exports, test-case harness, audit log."],
            ["FastAPI agent", "Agent loop, deterministic rules, scoring, separate verifier, LLM layer (Claude, with a deterministic fallback), persistence."],
            ["Data & sources", "Official GitHub REST + GraphQL (ETag cache, rate limiter, retries). Synthetic fixture world for personal-data-safe testing."],
          ].map(([t, d], i) => (
            <div key={t} className="relative rounded-2xl border bg-card p-6">
              <div className="font-mono text-xs text-primary">0{i + 1}</div>
              <div className="mt-2 text-lg font-semibold">{t}</div>
              <div className="mt-1 text-sm leading-relaxed text-muted-foreground">{d}</div>
            </div>
          ))}
        </div>
        <p className="mt-6 text-sm text-muted-foreground">Every run, step, candidate, evidence row, verification and approval is persisted, and every run has a permalink.</p>
      </>
    ),
  },
  {
    title: "Agent loop",
    body: (
      <>
        <Kicker n={5}>The agent loop · agentic capability</Kicker>
        <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-5">
          {LOOP.map((s, i) => (
            <div key={s.t} className={cn("rounded-xl border p-4", (s.t === "Adapt" || s.t === "Verify" || s.t === "Approve") && "border-primary/50 bg-primary/[0.06]")}>
              <s.icon className="h-5 w-5 text-primary" />
              <div className="mt-2 text-sm font-semibold"><span className="mr-1 font-mono text-xs text-muted-foreground">{i + 1}</span>{s.t}</div>
              <div className="text-xs text-muted-foreground">{s.d}</div>
            </div>
          ))}
        </div>
        <Bullets
          items={[
            "Every step is a recorded tool call, with inputs, rationale, duration and decisions, streamed live over SSE.",
            <><b className="text-foreground">Adaptive discovery:</b> it widens <i>where</i> it looks (seed repos found in the evidence), never <i>what counts</i>.</>,
            "Rate limits are shown as countdowns, failures are retried with backoff, and no candidate is ever silently dropped.",
          ]}
        />
      </>
    ),
  },
  {
    title: "Rules",
    body: (
      <>
        <Kicker n={6}>Decision rules · problem fit</Kicker>
        <h2 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">The rules decide, not the LLM.</h2>
        <div className="mt-6 divide-y overflow-hidden rounded-2xl border">
          {[
            ["merged + in_window", "TC1 counts; TC3 is excluded, with the date stated"],
            ["base_not_fork", "TC2: work that never left a fork is not counted"],
            ["not_own_repo", "self-merges are a bonus, never sufficient alone"],
            ["stack_match · not a bot", "upstream language must match; bots excluded"],
            ["public email field only", "TC4: blank stays blank, never guessed"],
          ].map(([k, d]) => (
            <div key={k} className="flex flex-col gap-1 px-5 py-3 sm:flex-row sm:gap-6">
              <code className="w-56 shrink-0 font-mono text-sm text-primary">{k}</code>
              <span className="text-muted-foreground">{d}</span>
            </div>
          ))}
        </div>
      </>
    ),
  },
  {
    title: "Verification",
    body: (
      <>
        <Kicker n={7}>Verification</Kicker>
        <h2 className="mt-4 text-4xl font-semibold tracking-tight sm:text-5xl">Trust, but re-fetch.</h2>
        <Bullets
          items={[
            "A separate module and a separate step: every cited PR is re-fetched via REST, never from the cached search.",
            "Five checks: resolves · merged · in window · author matches · upstream not a fork.",
            <>Any failure <b className="text-foreground">blocks approval</b>, and an override needs a written note, which is audited.</>,
            "The LLM summaries are grounded: citations are validated, and URLs not found in the evidence are stripped.",
          ]}
        />
      </>
    ),
  },
  {
    title: "Test cases",
    body: (
      <>
        <Kicker n={8}>Official test cases</Kicker>
        <div className="mt-8 grid gap-3 sm:grid-cols-2">
          {[
            ["TC1", "Recent merged PRs in stack", "SHORTLISTED · 3 PR links · 3/3 re-verified"],
            ["TC2", "Repository is only a fork", "EXCLUDED_FORK_ONLY · 0 of 5 counted"],
            ["TC3", "Last activity 3 years ago", "EXCLUDED_RECENCY · 1104 days, outside 180-day window"],
            ["TC4", "No public email", "contact = null · “Not public, never guessed”"],
          ].map(([id, t, a]) => (
            <div key={id} className="rounded-2xl border border-success/30 bg-success/[0.05] p-5">
              <div className="flex items-center justify-between">
                <span className="font-mono text-sm font-semibold text-primary">{id}</span>
                <span className="rounded-full bg-success/15 px-2.5 py-0.5 text-xs font-semibold text-success">PASS</span>
              </div>
              <div className="mt-2 font-semibold">{t}</div>
              <div className="mt-1 text-sm text-muted-foreground">{a}</div>
            </div>
          ))}
        </div>
        <p className="mt-6 text-sm text-muted-foreground">
          Labelled runs of the real agent, each with input, expected, actual, evidence and a trace link, at <a className="text-primary underline" href={`${SITE}/tests`}>/tests</a>. 55 automated tests run in CI.
        </p>
      </>
    ),
  },
  {
    title: "Safety",
    body: (
      <>
        <Kicker n={9}>Safety & privacy</Kicker>
        <div className="mt-8 grid gap-3 sm:grid-cols-2">
          {[
            [ShieldCheck, "Public data only", "Official API, read-only server-side token, limits respected, no CAPTCHA/OTP bypass."],
            [MailX, "No guessed contacts", "Only the public profile email field; no commit-email harvesting."],
            [Lock, "Human in control", "Finalise, export and share are explicit actions, recorded with name and time; undo until export."],
            [GitFork, "Synthetic test data", "Fixture personas wherever personal data would otherwise be needed. Runs can be deleted."],
          ].map(([Icon, t, d]) => {
            const I = Icon as typeof ShieldCheck;
            return (
              <div key={t as string} className="flex gap-3 rounded-2xl border p-5">
                <I className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
                <div>
                  <div className="font-semibold">{t as string}</div>
                  <div className="mt-1 text-sm text-muted-foreground">{d as string}</div>
                </div>
              </div>
            );
          })}
        </div>
      </>
    ),
  },
  {
    title: "Impact",
    body: (
      <>
        <Kicker n={10}>Impact & next steps</Kicker>
        <h2 className="mt-4 text-4xl font-semibold tracking-tight sm:text-5xl">Minutes, not hours. Defensible, not guessed.</h2>
        <Bullets
          items={[
            "Checks dozens of developers and hundreds of PRs per run, versus about 6 minutes of manual review per profile.",
            "Every shortlisted name comes with links a hiring manager can click.",
            "Next: GitLab/Codeberg, review and triage signals, ATS export (Greenhouse/Lever), consented outreach.",
          ]}
        />
        <div className="mt-10 flex flex-wrap items-center gap-3">
          <GitMerge className="h-5 w-5 text-primary" />
          <a href={SITE} className="font-mono text-sm text-primary underline">{SITE.replace("https://", "")}</a>
        </div>
      </>
    ),
  },
];

export default function Deck() {
  const [i, setI] = useState(0);
  const go = useCallback((d: number) => setI((x) => Math.max(0, Math.min(SLIDES.length - 1, x + d))), []);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (["ArrowRight", "PageDown", " "].includes(e.key)) {
        e.preventDefault();
        go(1);
      } else if (["ArrowLeft", "PageUp"].includes(e.key)) {
        e.preventDefault();
        go(-1);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go]);

  return (
    <div className="container max-w-6xl py-6">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <Link href="/" className="hover:text-foreground">← Back to the app</Link>
        <span>Use ← → to navigate · {i + 1} / {SLIDES.length}</span>
      </div>
      <div className="relative mt-4 aspect-auto min-h-[560px] overflow-hidden rounded-3xl border bg-card p-8 shadow-xl shadow-primary/[0.05] sm:aspect-video sm:min-h-0 sm:p-14">
        <div className="pointer-events-none absolute inset-0 glow" />
        <AnimatePresence mode="wait">
          <motion.section
            key={i}
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -24 }}
            transition={{ duration: 0.25 }}
            className="relative h-full"
            aria-label={`Slide ${i + 1}: ${SLIDES[i].title}`}
          >
            {SLIDES[i].body}
          </motion.section>
        </AnimatePresence>
      </div>
      <div className="mt-4 flex items-center justify-between gap-4">
        <button onClick={() => go(-1)} disabled={i === 0} className="inline-flex items-center gap-1 rounded-lg border px-3 py-2 text-sm disabled:opacity-40" aria-label="Previous slide">
          <ArrowLeft className="h-4 w-4" /> Prev
        </button>
        <div className="flex flex-wrap justify-center gap-1.5">
          {SLIDES.map((s, k) => (
            <button key={s.title} onClick={() => setI(k)} aria-label={`Go to slide ${k + 1}`} className={cn("h-1.5 rounded-full transition-all", k === i ? "w-6 bg-primary" : "w-1.5 bg-border hover:bg-muted-foreground")} />
          ))}
        </div>
        <button onClick={() => go(1)} disabled={i === SLIDES.length - 1} className="inline-flex items-center gap-1 rounded-lg border px-3 py-2 text-sm disabled:opacity-40" aria-label="Next slide">
          Next <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
