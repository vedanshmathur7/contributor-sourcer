"use client";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowRight,
  BadgeCheck,
  Brain,
  ChevronDown,
  FlaskConical,
  GitMerge,
  Globe,
  Loader2,
  Scale,
  Search,
  ShieldCheck,
  Sparkles,
  UserCheck,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { CriteriaEditor, DEFAULT_CRITERIA } from "@/components/criteria-editor";
import { RecentRuns } from "@/components/recent-runs";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/input";
import { Tooltip } from "@/components/ui/tooltip";
import { api } from "@/lib/api";
import type { Criteria, Meta, Mode } from "@/lib/types";
import { EXAMPLES, cn } from "@/lib/utils";

const PIPELINE = [
  { icon: Brain, title: "Plan", text: "LLM turns your brief into editable criteria." },
  { icon: Search, title: "Search", text: "Starts from merged PRs, not profiles." },
  { icon: Scale, title: "Judge", text: "Deterministic rules: window, forks, stack, bots." },
  { icon: BadgeCheck, title: "Verify", text: "Independent re-fetch of every cited PR." },
  { icon: UserCheck, title: "Approve", text: "Nothing is final until you sign off." },
];

function diff(c: Criteria): Partial<Criteria> {
  const out: Partial<Criteria> = {};
  (Object.keys(c) as (keyof Criteria)[]).forEach((k) => {
    if (JSON.stringify(c[k]) !== JSON.stringify(DEFAULT_CRITERIA[k])) (out as Record<string, unknown>)[k] = c[k];
  });
  return out;
}

export default function Home() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<Mode>("fixture");
  const [meta, setMeta] = useState<Meta | null>(null);
  const [refine, setRefine] = useState(false);
  const [criteria, setCriteria] = useState<Criteria>(DEFAULT_CRITERIA);
  const [busy, setBusy] = useState(false);
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    api.meta().then(setMeta).catch(() => {});
    ref.current?.focus();
  }, []);

  const overrides = diff(criteria);
  const canSubmit = query.trim().length > 0 || Object.keys(overrides).length > 0;

  async function submit() {
    if (!canSubmit || busy) return;
    setBusy(true);
    try {
      const run = await api.plan({ query, mode, overrides: Object.keys(overrides).length ? overrides : undefined });
      router.push(`/runs/${run.id}`);
    } catch (e) {
      toast.error((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <div className="relative">
      <div className="pointer-events-none absolute inset-0 -z-10 h-[620px] bg-grid" />
      <div className="pointer-events-none absolute inset-0 -z-10 h-[620px] glow" />

      <section className="container max-w-3xl pb-10 pt-16 sm:pt-24">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="text-center">
          <Link href="/about" className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border bg-background/60 px-3 py-1 text-xs text-muted-foreground backdrop-blur transition-colors hover:text-foreground">
            <Sparkles className="h-3.5 w-3.5 text-primary" />
            Agentic sourcing · evidence-first · human-approved
            <ArrowRight className="h-3 w-3" />
          </Link>
          <h1 className="text-balance text-4xl font-semibold tracking-tight sm:text-5xl">
            Hire from the <span className="bg-gradient-to-r from-primary to-sky-400 bg-clip-text text-transparent">merge log</span>,
            <br className="hidden sm:block" /> not the résumé.
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-balance text-muted-foreground">
            Describe who you need. The agent finds developers with real, recent merged contributions in that stack — every claim linked to a PR, re-verified, and waiting for your approval.
          </p>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, delay: 0.08 }}>
          <Card className="mt-10 overflow-hidden p-0 shadow-xl shadow-primary/[0.04] ring-1 ring-primary/5">
            <div className="p-4 pb-2">
              <Textarea
                ref={ref}
                rows={3}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
                }}
                placeholder="e.g. Rust async networking engineers active in the last 6 months, at least 2 merged PRs, India preferred"
                aria-label="Describe who you're looking for"
                className="resize-none border-0 bg-transparent p-1 text-base shadow-none focus-visible:ring-0"
              />
            </div>
            <div className="flex flex-wrap items-center gap-2 border-t bg-muted/30 px-4 py-3">
              <div role="radiogroup" aria-label="Data mode" className="inline-flex rounded-lg border bg-background p-0.5">
                {(["fixture", "live"] as Mode[]).map((m) => {
                  const disabled = m === "live" && meta !== null && !meta.live_available;
                  const btn = (
                    <button
                      key={m}
                      role="radio"
                      aria-checked={mode === m}
                      disabled={disabled}
                      onClick={() => setMode(m)}
                      className={cn(
                        "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40",
                        mode === m ? "bg-secondary text-foreground" : "text-muted-foreground hover:text-foreground",
                      )}
                    >
                      {m === "fixture" ? <FlaskConical className="h-3.5 w-3.5" /> : <Globe className="h-3.5 w-3.5" />}
                      {m === "fixture" ? "Fixture" : "Live GitHub"}
                    </button>
                  );
                  return (
                    <Tooltip
                      key={m}
                      content={
                        m === "fixture"
                          ? "Synthetic, GitHub-shaped personas — required by the brief wherever personal data is involved. Fully reproducible."
                          : disabled
                            ? "The server has no GitHub token configured."
                            : "Real public GitHub data through the official API, read-only."
                      }
                    >
                      <span>{btn}</span>
                    </Tooltip>
                  );
                })}
              </div>
              <button
                onClick={() => setRefine(!refine)}
                className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
                aria-expanded={refine}
              >
                Refine criteria
                {Object.keys(overrides).length > 0 && (
                  <span className="rounded-full bg-primary/15 px-1.5 text-[10px] font-semibold text-primary">{Object.keys(overrides).length}</span>
                )}
                <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", refine && "rotate-180")} />
              </button>
              <div className="ml-auto flex items-center gap-3">
                <span className="hidden text-[11px] text-muted-foreground sm:inline">⌘/Ctrl + Enter</span>
                <Button onClick={submit} disabled={!canSubmit || busy}>
                  {busy ? <Loader2 className="animate-spin" /> : <Sparkles />}
                  Plan search
                </Button>
              </div>
            </div>
            <AnimatePresence initial={false}>
              {refine && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden border-t">
                  <div className="p-5">
                    <p className="mb-4 text-xs text-muted-foreground">Anything you set here overrides the planner. You can still edit everything on the next screen.</p>
                    <CriteriaEditor value={criteria} onChange={setCriteria} compact />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </Card>

          <div className="mt-4 flex flex-wrap justify-center gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                onClick={() => {
                  setQuery(ex);
                  ref.current?.focus();
                }}
                className="rounded-full border bg-background/60 px-3 py-1 text-xs text-muted-foreground backdrop-blur transition-colors hover:border-primary/40 hover:text-foreground"
              >
                {ex}
              </button>
            ))}
          </div>
        </motion.div>
      </section>

      <section className="container max-w-5xl">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {PIPELINE.map((p, i) => (
            <motion.div
              key={p.title}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 + i * 0.05 }}
              className={cn("rounded-xl border bg-card/60 p-4", i === 4 && "col-span-2 sm:col-span-1")}
            >
              <div className="flex items-center gap-2">
                <span className="grid h-7 w-7 place-items-center rounded-md bg-primary/10 text-primary">
                  <p.icon className="h-4 w-4" />
                </span>
                <span className="text-[11px] font-medium text-muted-foreground">0{i + 1}</span>
              </div>
              <div className="mt-3 text-sm font-medium">{p.title}</div>
              <div className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{p.text}</div>
            </motion.div>
          ))}
        </div>

        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          {[
            { icon: GitMerge, t: "Forks don't count", d: "PRs merged into someone's fork, or work that never left yours, are never counted (TC2)." },
            { icon: ShieldCheck, t: "Contact never guessed", d: "Only the public profile email field. No commit-email harvesting, no pattern guessing (TC4)." },
            { icon: BadgeCheck, t: "Verified, then approved", d: "A separate verifier re-checks every cited PR; failures are blocked until a human reviews." },
          ].map((f) => (
            <div key={f.t} className="flex gap-3 rounded-xl border p-4">
              <f.icon className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
              <div>
                <div className="text-sm font-medium">{f.t}</div>
                <div className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{f.d}</div>
              </div>
            </div>
          ))}
        </div>

        <RecentRuns />
      </section>
    </div>
  );
}
