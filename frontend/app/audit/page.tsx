"use client";
import { ScrollText } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { AuditEntry } from "@/lib/types";
import { fmtDateTime } from "@/lib/utils";

const TONE: Record<string, "success" | "warning" | "danger" | "primary" | "muted"> = {
  "run.finalised": "success",
  "run.exported": "success",
  "run.shared": "success",
  "candidate.reviewed": "primary",
  "run.finalise_undone": "warning",
  "run.failed": "danger",
  "run.deleted": "danger",
};

function describe(a: AuditEntry) {
  const d = a.details as Record<string, unknown>;
  switch (a.action) {
    case "candidate.reviewed":
      return `@${d.login}: ${d.before} → ${d.after}${d.override ? " (verification override)" : ""}${d.note ? ` — “${d.note}”` : ""}`;
    case "run.finalised":
      return `Finalised ${(d.approve as string[])?.length ?? 0} candidate(s): ${(d.approve as string[])?.map((x) => "@" + x).join(", ")}`;
    case "run.proposed":
      return `Agent proposed a draft with ${d.shortlisted} shortlisted (pending approval)`;
    case "run.exported":
      return `Exported ${d.rows} row(s) as ${String(d.format).toUpperCase()}`;
    case "run.planned":
      return `Planned in ${d.mode} mode by ${d.planner}`;
    case "testcases.run":
      return `Ran TC1–TC4 in ${d.mode} mode`;
    default:
      return Object.keys(d).length ? JSON.stringify(d).slice(0, 140) : "";
  }
}

export default function AuditPage() {
  const [rows, setRows] = useState<AuditEntry[] | null>(null);
  useEffect(() => {
    api.audit().then(setRows).catch(() => setRows([]));
  }, []);
  return (
    <div className="container max-w-4xl py-10">
      <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight"><ScrollText className="h-5 w-5 text-muted-foreground" /> Audit log</h1>
      <p className="mt-1 text-sm text-muted-foreground">Every plan, run, review decision, approval, undo, export and share — who, what and when.</p>
      <div className="mt-6 overflow-hidden rounded-xl border">
        {!rows && Array.from({ length: 6 }).map((_, i) => <div key={i} className="border-b p-4"><Skeleton className="h-5 w-full" /></div>)}
        {rows?.length === 0 && <div className="p-12 text-center text-sm text-muted-foreground">Nothing recorded yet.</div>}
        {rows?.map((a) => (
          <div key={a.id} className="flex flex-col gap-1 border-b px-4 py-3 last:border-0 sm:flex-row sm:items-center sm:gap-4">
            <span className="w-40 shrink-0 font-mono text-[11px] text-muted-foreground">{fmtDateTime(a.ts)}</span>
            <Badge tone={TONE[a.action] ?? "muted"} className="w-fit font-mono">{a.action}</Badge>
            <span className="min-w-0 flex-1 truncate text-xs" title={describe(a)}>{describe(a)}</span>
            <span className="shrink-0 text-xs text-muted-foreground">{a.actor}</span>
            {a.run_id && <Link href={`/runs/${a.run_id}`} className="shrink-0 font-mono text-[11px] text-primary hover:underline">#{a.run_id}</Link>}
          </div>
        ))}
      </div>
    </div>
  );
}
