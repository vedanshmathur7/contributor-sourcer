"use client";
import { Check, Lock } from "lucide-react";
import { useEffect, useState } from "react";
import { CandidateCard, CandidateDrawer } from "@/components/candidates";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { Candidate, RunSummary } from "@/lib/types";
import { fmtDateTime } from "@/lib/utils";

export default function SharePage({ params }: { params: { token: string } }) {
  const [data, setData] = useState<{ run: RunSummary; candidates: Candidate[] } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [sel, setSel] = useState<Candidate | null>(null);
  useEffect(() => {
    api.shared(params.token).then(setData).catch((e) => setErr(e.message));
  }, [params.token]);
  if (err) return <div className="container py-24 text-center text-sm text-muted-foreground">{err}</div>;
  if (!data) return <div className="container max-w-3xl py-10 space-y-3">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}</div>;
  const { run, candidates } = data;
  return (
    <div className="container max-w-3xl py-10">
      <Badge tone="outline"><Lock /> Read-only shortlist</Badge>
      <h1 className="mt-3 text-2xl font-semibold tracking-tight">{run.query || "Shortlist"}</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        <Check className="mr-1 inline h-3.5 w-3.5 text-success" />
        Approved by {run.approver} · {fmtDateTime(run.finalised_at)} · {candidates.length} candidate(s) · window {run.criteria.window_days} days
      </p>
      <div className="mt-6 space-y-3">
        {candidates.map((c, i) => <CandidateCard key={c.id} c={c} rank={i + 1} onOpen={() => setSel(c)} />)}
      </div>
      <CandidateDrawer c={sel} open={!!sel} onOpenChange={(o) => !o && setSel(null)} window_days={run.criteria.window_days} />
    </div>
  );
}
