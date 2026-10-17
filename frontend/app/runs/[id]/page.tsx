"use client";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Brain,
  Check,
  Clock,
  Copy,
  FlaskConical,
  Globe,
  Loader2,
  Play,
  RotateCcw,
  ShieldAlert,
  Trash2,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { CandidateCard, CandidateDrawer } from "@/components/candidates";
import { CriteriaEditor } from "@/components/criteria-editor";
import { StatusBadge } from "@/components/status";
import { Trace, WaitBanner } from "@/components/trace";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogClose, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import type { Candidate, Criteria, RunDetail } from "@/lib/types";
import { useRunStream } from "@/lib/use-run-stream";
import { cn, fmtDateTime } from "@/lib/utils";

const PHASES = ["Plan", "Search", "Enrich", "Classify", "Score", "Explain", "Verify", "Propose"];

function PlanReview({ run, onStarted }: { run: RunDetail; onStarted: () => void }) {
  const [criteria, setCriteria] = useState<Criteria>(run.criteria);
  const [busy, setBusy] = useState(false);
  const dirty = JSON.stringify(criteria) !== JSON.stringify(run.criteria);
  async function go() {
    setBusy(true);
    try {
      if (dirty) await api.updateCriteria(run.id, criteria);
      await api.start(run.id);
      onStarted();
    } catch (e) {
      toast.error((e as Error).message);
      setBusy(false);
    }
  }
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mx-auto max-w-3xl">
      <Card>
        <CardHeader className="border-b pb-4">
          <div className="flex items-center gap-2">
            <span className="grid h-7 w-7 place-items-center rounded-md bg-primary/10 text-primary"><Brain className="h-4 w-4" /></span>
            <CardTitle className="text-base">Review the agent&apos;s plan</CardTitle>
            <Badge tone="outline" className="ml-auto">planner: {run.plan_notes.planner}</Badge>
          </div>
          {run.plan_notes.rationale && <CardDescription className="mt-2 leading-relaxed">“{run.plan_notes.rationale}”</CardDescription>}
        </CardHeader>
        <CardContent className="pt-5">
          <CriteriaEditor value={criteria} onChange={setCriteria} />
          <div className="mt-6 rounded-lg border bg-muted/30 p-3 text-xs leading-relaxed text-muted-foreground">
            The agent may widen <em>where it looks</em> (more seed repositories, dropping keyword filters) if it finds too few people. It can never change <em>what counts</em>:
            the window, minimum PRs, stack and fork/bot rules above are fixed for this run.
          </div>
          <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
            <span className="text-xs text-muted-foreground">
              {run.mode === "fixture" ? "Fixture mode · synthetic personas" : "Live mode · public GitHub, read-only"}
              {dirty && " · unsaved edits will be applied"}
            </span>
            <Button size="lg" onClick={go} disabled={busy}>
              {busy ? <Loader2 className="animate-spin" /> : <Play />}
              Run agent
            </Button>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

function Stat({ label, value, tone }: { label: string; value: React.ReactNode; tone?: string }) {
  return (
    <div className="min-w-0">
      <div className={cn("text-xl font-semibold tabular-nums tracking-tight", tone)}>{value}</div>
      <div className="text-[11px] text-muted-foreground">{label}</div>
    </div>
  );
}

function groupCandidates(cands: Candidate[]) {
  const shortlisted = cands.filter((c) => c.classification === "SHORTLISTED" && !c.blocked).sort((a, b) => b.score - a.score);
  const review = cands.filter((c) => c.blocked);
  const excluded = cands.filter((c) => c.classification.startsWith("EXCLUDED"));
  const insufficient = cands.filter((c) => c.classification === "INSUFFICIENT_EVIDENCE");
  return { shortlisted, review, excluded, insufficient };
}

export default function RunPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const { run, error, wait, live, restart, reload } = useRunStream(params.id);
  const [selected, setSelected] = useState<string | null>(null);
  const [tab, setTab] = useState("shortlisted");

  const groups = useMemo(() => groupCandidates(run?.candidates ?? []), [run?.candidates]);
  const selectedCand = run?.candidates.find((c) => c.login.toLowerCase() === selected?.toLowerCase()) ?? null;

  if (error && !run)
    return (
      <div className="container max-w-xl py-24 text-center">
        <h1 className="text-lg font-semibold">Run not available</h1>
        <p className="mt-2 text-sm text-muted-foreground">{error}</p>
        <Button asChild className="mt-6" variant="outline"><Link href="/">Start a new search</Link></Button>
      </div>
    );

  if (!run)
    return (
      <div className="container py-10">
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="mt-3 h-4 w-1/3" />
        <div className="mt-8 grid gap-6 lg:grid-cols-12">
          <Skeleton className="h-[480px] lg:col-span-5" />
          <Skeleton className="h-[480px] lg:col-span-7" />
        </div>
      </div>
    );

  const running = run.status === "RUNNING";
  const done = new Set(run.steps.filter((s) => s.status === "ok").map((s) => s.phase));
  const progress = run.status === "PLANNED" ? 0.08 : ["PENDING_APPROVAL", "FINALISED", "EXPORTED"].includes(run.status) ? 1 : PHASES.filter((p) => done.has(p)).length / PHASES.length;
  const s = run.stats || {};
  const awaiting = run.status === "PENDING_APPROVAL";

  async function del() {
    try {
      await api.deleteRun(run!.id);
      toast.success("Run and all its data deleted");
      router.push("/");
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  return (
    <div className="container py-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Link href="/runs" className="hover:text-foreground">Runs</Link>
            <span>/</span>
            <span className="font-mono">#{run.id}</span>
            <StatusBadge status={run.status} />
            <Badge tone="outline">{run.mode === "live" ? <Globe /> : <FlaskConical />} {run.mode === "live" ? "Live GitHub" : "Fixture"}</Badge>
            {run.label && <Badge tone="primary">{run.label}</Badge>}
          </div>
          <h1 className="mt-2 text-balance text-xl font-semibold tracking-tight sm:text-2xl">
            {run.query || "Manual criteria"}
          </h1>
          <div className="mt-1.5 flex flex-wrap gap-1.5 text-xs">
            {run.criteria.languages.map((l) => <Badge key={l}>{l}</Badge>)}
            {run.criteria.keywords.map((k) => <Badge key={k} tone="outline">{k}</Badge>)}
            <Badge tone="outline"><Clock /> last {run.criteria.window_days} days</Badge>
            <Badge tone="outline">≥ {run.criteria.min_merged_prs} merged PRs</Badge>
            {!run.criteria.search && <Badge tone="warning">vet-only</Badge>}
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => { navigator.clipboard.writeText(window.location.href); toast.success("Permalink copied"); }}>
            <Copy /> Permalink
          </Button>
          {run.status === "FAILED" && (
            <Button variant="outline" size="sm" onClick={async () => { await api.start(run.id); restart(); }}>
              <RotateCcw /> Retry
            </Button>
          )}
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="ghost" size="sm" disabled={running} aria-label="Delete run"><Trash2 /></Button>
            </DialogTrigger>
            <DialogContent title="Delete this run?" description="Removes the run, its trace, candidates and evidence from our database. The audit log keeps a record that it was deleted.">
              <div className="flex justify-end gap-2">
                <DialogClose asChild><Button variant="outline">Cancel</Button></DialogClose>
                <Button variant="danger" onClick={del}>Delete run</Button>
              </div>
            </DialogContent>
          </Dialog>
          {(awaiting || run.status === "FINALISED" || run.status === "EXPORTED") && (
            <Button asChild size="sm" variant={awaiting ? "default" : "outline"}>
              <Link href={`/runs/${run.id}/review`}>
                {awaiting ? "Review & approve" : "View final shortlist"} <ArrowRight />
              </Link>
            </Button>
          )}
        </div>
      </div>

      {run.status === "PLANNED" ? (
        <div className="mt-8"><PlanReview run={run} onStarted={() => { restart(); reload(); }} /></div>
      ) : (
        <>
          <Card className="mt-6 overflow-hidden">
            <div className="h-1 w-full bg-secondary">
              <motion.div className="h-full bg-gradient-to-r from-primary to-sky-400" animate={{ width: `${progress * 100}%` }} transition={{ duration: 0.5 }} />
            </div>
            <div className="grid grid-cols-3 gap-4 p-4 sm:grid-cols-6">
              <Stat label="developers checked" value={s.developers_checked ?? 0} />
              <Stat label="PRs examined" value={s.prs_examined ?? 0} />
              <Stat label="shortlisted" value={s.shortlisted ?? 0} tone="text-success" />
              <Stat label="excluded" value={s.excluded ?? 0} />
              <Stat label="need review" value={s.needs_review ?? 0} tone={s.needs_review ? "text-danger" : undefined} />
              <Stat label="API calls" value={s.api_requests ?? 0} />
            </div>
            {!running && s.elapsed_s !== undefined && (
              <div className="flex items-center gap-2 border-t bg-primary/[0.04] px-4 py-2.5 text-xs">
                <Zap className="h-3.5 w-3.5 text-primary" />
                Checked <b className="tabular-nums">{s.prs_examined}</b> PRs across <b className="tabular-nums">{s.developers_checked}</b> developers in{" "}
                <b className="tabular-nums">{s.elapsed_s}s</b>
                <span className="text-muted-foreground">
                  — vs. ≈{Math.max(1, Math.round((s.developers_checked ?? 0) * 6))} min of manual profile review at ~6 min each{run.mode === "fixture" ? " (fixture: GitHub latency simulated)" : ""}.
                </span>
              </div>
            )}
            {run.error && <div className="border-t bg-danger/10 px-4 py-2.5 text-xs text-danger">Run failed: {run.error}</div>}
          </Card>

          {awaiting && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-4 flex flex-wrap items-center gap-3 rounded-xl border border-warning/30 bg-warning/[0.07] px-4 py-3 text-sm">
              <ShieldAlert className="h-4 w-4 text-warning" />
              <span>
                Draft shortlist ready — <b>nothing is final</b> until a human approves it.
                {groups.review.length > 0 && <> {groups.review.length} candidate(s) failed re-verification and need review.</>}
              </span>
              <Button asChild size="sm" className="ml-auto"><Link href={`/runs/${run.id}/review`}>Review & approve <ArrowRight /></Link></Button>
            </motion.div>
          )}
          {(run.status === "FINALISED" || run.status === "EXPORTED") && (
            <div className="mt-4 flex flex-wrap items-center gap-2 rounded-xl border border-success/30 bg-success/[0.07] px-4 py-3 text-sm">
              <Check className="h-4 w-4 text-success" /> Finalised by <b>{run.approver}</b> on {fmtDateTime(run.finalised_at)}.
              <Link href={`/runs/${run.id}/review`} className="ml-auto text-xs text-success hover:underline">Exports & share link →</Link>
            </div>
          )}

          <div className="mt-6 grid gap-6 lg:grid-cols-12">
            <Card className="lg:col-span-5">
              <CardHeader className="flex-row items-center justify-between border-b pb-3">
                <CardTitle className="flex items-center gap-2">
                  Live agent trace
                  {live && running && <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-success" aria-label="live" />}
                </CardTitle>
                <span className="text-xs text-muted-foreground">{run.steps.length} steps</span>
              </CardHeader>
              <CardContent className="scrollbar-thin max-h-[calc(100vh-14rem)] overflow-y-auto pt-5 lg:sticky lg:top-20">
                <WaitBanner wait={wait} />
                <Trace steps={run.steps} running={running} onSelect={setSelected} />
              </CardContent>
            </Card>

            <div className="lg:col-span-7">
              <Tabs value={tab} onValueChange={setTab}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <TabsList>
                    <TabsTrigger value="shortlisted">Shortlisted <span className="tabular-nums text-success">{groups.shortlisted.length}</span></TabsTrigger>
                    <TabsTrigger value="review">Needs review <span className={cn("tabular-nums", groups.review.length && "text-danger")}>{groups.review.length}</span></TabsTrigger>
                    <TabsTrigger value="excluded">Excluded <span className="tabular-nums">{groups.excluded.length}</span></TabsTrigger>
                    <TabsTrigger value="insufficient">Not enough <span className="tabular-nums">{groups.insufficient.length}</span></TabsTrigger>
                  </TabsList>
                </div>
                {(["shortlisted", "review", "excluded", "insufficient"] as const).map((k) => (
                  <TabsContent key={k} value={k} className="mt-4 space-y-3 focus-visible:outline-none">
                    {groups[k].length === 0 ? (
                      running ? (
                        Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-28 w-full rounded-xl" />)
                      ) : (
                        <div className="rounded-xl border border-dashed px-6 py-12 text-center text-sm text-muted-foreground">
                          {k === "shortlisted" ? "No one met every rule. Try a wider window or fewer keywords." : k === "review" ? "Every cited PR re-verified cleanly." : "Nobody in this group."}
                        </div>
                      )
                    ) : (
                      groups[k].map((c, i) => (
                        <CandidateCard key={c.id} c={c} rank={k === "shortlisted" ? i + 1 : undefined} onOpen={() => setSelected(c.login)} />
                      ))
                    )}
                  </TabsContent>
                ))}
              </Tabs>
            </div>
          </div>
        </>
      )}

      <CandidateDrawer c={selectedCand} open={!!selectedCand} onOpenChange={(o) => !o && setSelected(null)} window_days={run.criteria.window_days} />
    </div>
  );
}
