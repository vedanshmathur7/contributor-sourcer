"use client";
import { ArrowUpRight, FlaskConical, Globe, History } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { StatusBadge } from "@/components/status";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { RunSummary } from "@/lib/types";
import { relTime } from "@/lib/utils";

export function RunRow({ r }: { r: RunSummary }) {
  return (
    <Link href={`/runs/${r.id}`} className="group flex items-center gap-3 px-4 py-3 transition-colors hover:bg-secondary/50">
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md border bg-background text-muted-foreground">
        {r.mode === "live" ? <Globe className="h-4 w-4" /> : <FlaskConical className="h-4 w-4" />}
      </span>
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium">
          {r.query || [...r.criteria.languages, ...r.criteria.keywords].join(", ") || "Manual criteria"}
        </div>
        <div className="mt-0.5 flex flex-wrap items-center gap-x-3 text-xs text-muted-foreground">
          <span className="font-mono">#{r.id}</span>
          <span>{relTime(r.created_at)}</span>
          {r.stats?.developers_checked !== undefined && <span>{r.stats.developers_checked} devs · {r.stats.prs_examined} PRs</span>}
          {r.stats?.shortlisted !== undefined && <span className="text-success">{r.stats.shortlisted} shortlisted</span>}
        </div>
      </div>
      <StatusBadge status={r.status} />
      <ArrowUpRight className="h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
    </Link>
  );
}

export function RecentRuns({ limit = 6, title = "Recent runs" }: { limit?: number; title?: string }) {
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  useEffect(() => {
    api.runs(limit).then((r) => setRuns(r.runs)).catch(() => setRuns([]));
  }, [limit]);
  return (
    <div className="mt-12">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-sm font-semibold"><History className="h-4 w-4 text-muted-foreground" /> {title}</h2>
        <Link href="/runs" className="text-xs text-muted-foreground hover:text-foreground">View all</Link>
      </div>
      <div className="divide-y overflow-hidden rounded-xl border">
        {runs === null ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 px-4 py-3">
              <Skeleton className="h-8 w-8" />
              <div className="flex-1 space-y-1.5"><Skeleton className="h-3.5 w-2/3" /><Skeleton className="h-3 w-1/3" /></div>
            </div>
          ))
        ) : runs.length === 0 ? (
          <div className="px-4 py-10 text-center text-sm text-muted-foreground">No runs yet — describe who you need above and plan your first search.</div>
        ) : (
          runs.map((r) => <RunRow key={r.id} r={r} />)
        )}
      </div>
    </div>
  );
}
