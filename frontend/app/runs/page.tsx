"use client";
import { Plus } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { RunRow } from "@/components/recent-runs";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { RunSummary } from "@/lib/types";

export default function RunsPage() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    api.runs(100).then((r) => setRuns(r.runs)).catch((e) => setErr(e.message));
  }, []);
  return (
    <div className="container max-w-4xl py-10">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Runs</h1>
          <p className="mt-1 text-sm text-muted-foreground">Every run keeps its full trace, evidence and approval history at a permanent link.</p>
        </div>
        <Button asChild><Link href="/"><Plus /> New search</Link></Button>
      </div>
      <div className="mt-6 divide-y overflow-hidden rounded-xl border">
        {err && <div className="p-6 text-sm text-danger">{err}</div>}
        {!runs && !err && Array.from({ length: 5 }).map((_, i) => <div key={i} className="p-4"><Skeleton className="h-10 w-full" /></div>)}
        {runs?.length === 0 && <div className="p-12 text-center text-sm text-muted-foreground">No runs yet.</div>}
        {runs?.map((r) => <RunRow key={r.id} r={r} />)}
      </div>
    </div>
  );
}
