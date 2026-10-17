"use client";
import { AnimatePresence, motion } from "framer-motion";
import {
  BadgeCheck,
  Brain,
  Check,
  ChevronRight,
  Compass,
  FileSearch,
  Hourglass,
  ListChecks,
  Loader2,
  MessageSquareQuote,
  Scale,
  Search,
  Send,
  Sigma,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { Decision, Step } from "@/lib/types";
import { cn } from "@/lib/utils";
import type { WaitInfo } from "@/lib/use-run-stream";

const PHASE_ICON: Record<string, React.ComponentType<{ className?: string }>> = {
  Plan: Brain,
  Search: Search,
  Enrich: FileSearch,
  Classify: Scale,
  Adapt: Compass,
  Score: Sigma,
  Explain: MessageSquareQuote,
  Verify: BadgeCheck,
  Propose: Send,
};

const VERDICT_TONE: Record<string, string> = {
  SHORTLISTED: "text-success",
  VERIFIED: "text-success",
  SCORED: "text-foreground",
  EXPLAINED: "text-foreground",
  VERIFY_FAILED: "text-danger",
  EXCLUDED_RECENCY: "text-warning",
  EXCLUDED_FORK_ONLY: "text-warning",
  EXCLUDED_STACK: "text-muted-foreground",
  EXCLUDED_BOT: "text-muted-foreground",
  INSUFFICIENT_EVIDENCE: "text-muted-foreground",
  NOT_EXAMINED: "text-muted-foreground",
  OVER_CAP: "text-muted-foreground",
};

function verdictLabel(v: string) {
  return v.replace(/^EXCLUDED_/, "EXCLUDED · ").replace(/_/g, " ").toLowerCase();
}

function Decisions({ items, onSelect }: { items: Decision[]; onSelect?: (login: string) => void }) {
  const [all, setAll] = useState(false);
  const shown = all ? items : items.slice(0, 4);
  return (
    <div className="mt-2 space-y-1">
      {shown.map((d, i) => (
        <div key={`${d.login}-${i}`} className="flex gap-2 rounded-md bg-muted/50 px-2 py-1.5 text-xs leading-relaxed">
          <button onClick={() => onSelect?.(d.login)} className="shrink-0 font-mono font-medium hover:text-primary hover:underline">
            @{d.login}
          </button>
          <span className="min-w-0">
            <span className={cn("mr-1.5 font-medium uppercase tracking-wide text-[10px]", VERDICT_TONE[d.verdict] ?? "text-muted-foreground")}>
              {verdictLabel(d.verdict)}
            </span>
            <span className="text-muted-foreground">{d.text}</span>
          </span>
        </div>
      ))}
      {items.length > 4 && (
        <button onClick={() => setAll(!all)} className="text-xs text-primary hover:underline">
          {all ? "Show less" : `Show all ${items.length} decisions`}
        </button>
      )}
    </div>
  );
}

function StepItem({ step, last, onSelect }: { step: Step; last: boolean; onSelect?: (login: string) => void }) {
  const [open, setOpen] = useState(step.phase === "Classify" || step.phase === "Verify" || step.phase === "Adapt");
  const Icon = PHASE_ICON[step.phase] ?? ListChecks;
  const inputs = Object.entries(step.inputs || {}).filter(([, v]) => v !== null && !(Array.isArray(v) && v.length === 0));
  return (
    <motion.li initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.25 }} className="relative pl-10">
      {!last && <span className="absolute left-[15px] top-8 h-[calc(100%-1.25rem)] w-px bg-border" aria-hidden />}
      <span
        className={cn(
          "absolute left-0 top-0.5 grid h-8 w-8 place-items-center rounded-full border bg-background",
          step.status === "running" && "border-primary/50 text-primary shadow-[0_0_0_4px] shadow-primary/10",
          step.status === "ok" && "text-foreground",
          step.status === "failed" && "border-danger/50 text-danger",
        )}
      >
        {step.status === "running" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Icon className="h-4 w-4" />}
      </span>
      <div className="pb-5">
        <button className="flex w-full items-start gap-2 text-left" onClick={() => setOpen(!open)} aria-expanded={open}>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
              <span className="text-sm font-medium">{step.phase}</span>
              <code className="rounded bg-secondary px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground">{step.tool}</code>
              {step.status === "ok" && <Check className="h-3.5 w-3.5 text-success" />}
              {step.status === "failed" && <X className="h-3.5 w-3.5 text-danger" />}
              {step.duration_ms !== null && step.status !== "running" && (
                <span className="font-mono text-[11px] text-muted-foreground">{step.duration_ms < 1000 ? `${step.duration_ms}ms` : `${(step.duration_ms / 1000).toFixed(1)}s`}</span>
              )}
            </div>
            {step.summary && <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{step.summary}</p>}
            {step.status === "running" && !step.summary && <p className="mt-1 text-xs text-primary">Working…</p>}
            {step.error && <p className="mt-1 text-xs text-danger">{step.error}</p>}
          </div>
          {(step.decisions.length > 0 || inputs.length > 0 || step.rationale) && (
            <ChevronRight className={cn("mt-0.5 h-4 w-4 shrink-0 text-muted-foreground transition-transform", open && "rotate-90")} />
          )}
        </button>
        <AnimatePresence initial={false}>
          {open && (
            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
              {step.rationale && (
                <p className="mt-2 border-l-2 border-primary/40 pl-2 text-xs italic text-muted-foreground">Why: {step.rationale}</p>
              )}
              {inputs.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {inputs.map(([k, v]) => (
                    <span key={k} className="max-w-full truncate rounded border bg-background px-1.5 py-0.5 font-mono text-[10.5px] text-muted-foreground" title={JSON.stringify(v)}>
                      {k}={typeof v === "string" ? v : JSON.stringify(v)}
                    </span>
                  ))}
                </div>
              )}
              {step.decisions.length > 0 && <Decisions items={step.decisions} onSelect={onSelect} />}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.li>
  );
}

export function WaitBanner({ wait }: { wait: WaitInfo | null }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!wait) return;
    const t = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(t);
  }, [wait]);
  if (!wait || now > wait.until) return null;
  return (
    <div className="mb-4 flex items-center gap-2 rounded-lg border border-warning/30 bg-warning/10 px-3 py-2 text-xs text-warning">
      <Hourglass className="h-3.5 w-3.5 animate-pulse" />
      {wait.reason} — resuming in <span className="font-mono font-semibold">{Math.ceil((wait.until - now) / 1000)}s</span>. Limits are respected, never bypassed.
    </div>
  );
}

export function Trace({ steps, running, onSelect }: { steps: Step[]; running: boolean; onSelect?: (login: string) => void }) {
  const end = useRef<HTMLDivElement>(null);
  const count = steps.length;
  useEffect(() => {
    if (running) end.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [count, running]);
  return (
    <ol>
      {steps.map((s, i) => (
        <StepItem key={s.id} step={s} last={i === steps.length - 1 && !running} onSelect={onSelect} />
      ))}
      {running && steps.every((s) => s.status !== "running") && (
        <li className="relative pl-10 text-xs text-muted-foreground">
          <span className="absolute left-0 top-0 grid h-8 w-8 place-items-center rounded-full border border-dashed">
            <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-primary" />
          </span>
          <span className="leading-8">Agent deciding next step…</span>
        </li>
      )}
      <div ref={end} />
    </ol>
  );
}
