"use client";
import { motion } from "framer-motion";
import { ArrowUpRight, Check, CircleHelp, FlaskConical, GitFork, GitMerge, Globe, Loader2, Play, X } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import type { Mode, TestCaseDef, TestResult } from "@/lib/types";
import { cn, fmtDate, fmtDateTime } from "@/lib/utils";

type Latest = Record<Mode, { running: boolean; batch_id: string | null; results: TestResult[] }>;
type LiveInputs = Record<string, { login: string | null; languages: string[]; window_days: number }>;

function Verdict({ passed }: { passed: boolean | null | undefined }) {
  if (passed === true) return <Badge tone="success" className="px-2.5 py-1 text-xs"><Check /> PASS</Badge>;
  if (passed === false) return <Badge tone="danger" className="px-2.5 py-1 text-xs"><X /> FAIL</Badge>;
  return <Badge tone="muted" className="px-2.5 py-1 text-xs"><CircleHelp /> {passed === null ? "INCONCLUSIVE" : "NOT RUN"}</Badge>;
}

function CaseCard({ def, result, running }: { def: TestCaseDef; result?: TestResult; running: boolean }) {
  const items = result?.evidence.items ?? [];
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <Card className={cn("h-full p-5", result?.passed === true && "border-success/30", result?.passed === false && "border-danger/40")}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="font-mono text-xs font-semibold text-primary">{def.id}</div>
            <h3 className="mt-0.5 font-semibold">{def.label}</h3>
            <p className="mt-1 text-xs text-muted-foreground">{def.scenario}</p>
          </div>
          {running && !result ? <Loader2 className="h-5 w-5 animate-spin text-primary" /> : <Verdict passed={result ? result.passed : undefined} />}
        </div>

        <dl className="mt-4 grid min-w-0 gap-3 break-words text-xs [&>div]:min-w-0 [&_div]:min-w-0">
          <div className="rounded-lg border bg-muted/30 p-3">
            <dt className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Input</dt>
            <dd className="mt-1 font-mono">
              {result?.input.login ? <>@{result.input.login} · {result.input.criteria?.languages.join(", ")} · {result.input.criteria?.window_days}d window · ≥{result.input.criteria?.min_merged_prs} PRs</> : <span className="text-muted-foreground">—</span>}
            </dd>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg border p-3">
              <dt className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Expected</dt>
              <dd className="mt-1 font-medium">{def.expected}</dd>
            </div>
            <div className={cn("rounded-lg border p-3", result?.passed === true && "border-success/30 bg-success/[0.04]", result?.passed === false && "border-danger/30 bg-danger/[0.04]")}>
              <dt className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Actual</dt>
              <dd className="mt-1">{result?.actual ?? (running ? "Running…" : "—")}</dd>
            </div>
          </div>
          {result?.explanation && (
            <div className="rounded-lg border border-warning/30 bg-warning/5 p-3">
              <dt className="text-[10px] font-semibold uppercase tracking-wider text-warning">Explanation of difference</dt>
              <dd className="mt-1">{result.explanation}</dd>
            </div>
          )}
          {result?.evidence.candidate && (
            <div className="rounded-lg border p-3">
              <dt className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Evidence</dt>
              <dd className="mt-1.5 space-y-1">
                <div className="text-muted-foreground">
                  contact_email: <span className="font-mono text-foreground">{result.evidence.candidate.contact_email ?? "null (not public)"}</span>
                </div>
                {items.slice(0, 4).map((it) => (
                  <a key={it.url} href={it.url} target="_blank" rel="noreferrer" className="flex items-center gap-1.5 truncate hover:text-primary">
                    {it.repo_is_fork ? <GitFork className="h-3 w-3 shrink-0 text-warning" /> : <GitMerge className={cn("h-3 w-3 shrink-0", it.qualifies ? "text-success" : "text-muted-foreground")} />}
                    <span className="truncate">{it.title}</span>
                    <span className="ml-auto shrink-0 font-mono text-[10px] text-muted-foreground">
                      {fmtDate(it.merged_at)} · {it.qualifies ? (it.verified ? "counted ✓ verified" : "counted") : "not counted"}
                    </span>
                  </a>
                ))}
              </dd>
            </div>
          )}
        </dl>
        {result && (
          <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-[11px] text-muted-foreground">
            <span>{fmtDateTime(result.ts)} · commit <span className="font-mono">{result.commit_sha}</span></span>
            {result.run_id && (
              <Link href={`/runs/${result.run_id}`} className="inline-flex items-center gap-0.5 text-primary hover:underline">
                Full agent trace <ArrowUpRight className="h-3 w-3" />
              </Link>
            )}
          </div>
        )}
      </Card>
    </motion.div>
  );
}

export default function TestsPage() {
  const [defs, setDefs] = useState<TestCaseDef[] | null>(null);
  const [liveAvail, setLiveAvail] = useState(false);
  const [liveInputs, setLiveInputs] = useState<LiveInputs>({});
  const [latest, setLatest] = useState<Latest | null>(null);
  const [mode, setMode] = useState<Mode>("fixture");

  const refresh = useCallback(() => api.testLatest().then(setLatest).catch(() => {}), []);
  useEffect(() => {
    api.testDefinitions().then((d) => {
      setDefs(d.cases);
      setLiveAvail(d.live_available);
      setLiveInputs(d.live_inputs);
    }).catch((e) => toast.error(e.message));
    refresh();
  }, [refresh]);
  const anyRunning = latest?.fixture.running || latest?.live.running;
  useEffect(() => {
    if (!anyRunning) return;
    const t = setInterval(refresh, 1200);
    return () => clearInterval(t);
  }, [anyRunning, refresh]);

  async function run(m: Mode) {
    try {
      await api.runTests(m, m === "live" ? liveInputs : undefined);
      toast(`Running TC1–TC4 in ${m} mode…`);
      setTimeout(refresh, 300);
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  return (
    <div className="container max-w-6xl py-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Official test cases</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Each case is a labelled run of the real agent, stored with its input, expected result, actual result and evidence. Differences are explained, never presented as success.
          </p>
        </div>
      </div>
      <Tabs value={mode} onValueChange={(v) => setMode(v as Mode)} className="mt-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <TabsList>
            <TabsTrigger value="fixture"><FlaskConical className="h-3.5 w-3.5" /> Fixture (synthetic)</TabsTrigger>
            <TabsTrigger value="live"><Globe className="h-3.5 w-3.5" /> Live GitHub</TabsTrigger>
          </TabsList>
          {latest && (
            <div className="flex items-center gap-3">
              {latest[mode].results.length > 0 && (
                <span className="text-sm">
                  <b className="tabular-nums text-success">{latest[mode].results.filter((r) => r.passed).length}</b>
                  <span className="text-muted-foreground"> / {latest[mode].results.length} passed</span>
                </span>
              )}
              <Button onClick={() => run(mode)} disabled={latest[mode].running || (mode === "live" && !liveAvail)}>
                {latest[mode].running ? <Loader2 className="animate-spin" /> : <Play />}
                {latest[mode].results.length ? "Re-run" : "Run"} TC1–TC4
              </Button>
            </div>
          )}
        </div>

        {(["fixture", "live"] as Mode[]).map((m) => (
          <TabsContent key={m} value={m} className="mt-5 focus-visible:outline-none">
            {m === "live" && (
              <Card className="mb-5 p-4">
                <p className="text-xs text-muted-foreground">
                  {liveAvail
                    ? "Choose a real public GitHub account that matches each scenario. Live data changes over time — results are recorded as they are."
                    : "The server has no GitHub token, so Live mode is unavailable here. Fixture results above are the reproducible baseline."}
                </p>
                <div className="mt-3 grid gap-3 sm:grid-cols-4">
                  {(defs ?? []).map((d) => (
                    <div key={d.id} className="space-y-1">
                      <Label htmlFor={`live-${d.id}`}>{d.id} login</Label>
                      <Input
                        id={`live-${d.id}`}
                        disabled={!liveAvail}
                        value={liveInputs[d.id]?.login ?? ""}
                        placeholder="github-login"
                        onChange={(e) =>
                          setLiveInputs((li) => ({ ...li, [d.id]: { ...(li[d.id] ?? { languages: ["Rust"], window_days: 180 }), login: e.target.value.replace(/^@/, "") || null } }))
                        }
                      />
                      <Input
                        aria-label={`${d.id} language`}
                        disabled={!liveAvail}
                        className="h-8 text-xs"
                        value={(liveInputs[d.id]?.languages ?? ["Rust"]).join(", ")}
                        onChange={(e) =>
                          setLiveInputs((li) => ({ ...li, [d.id]: { ...(li[d.id] ?? { login: null, window_days: 180 }), languages: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) } }))
                        }
                      />
                    </div>
                  ))}
                </div>
              </Card>
            )}
            <div className="grid gap-4 md:grid-cols-2">
              {!defs || !latest
                ? Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-72 rounded-xl" />)
                : defs.map((d) => (
                    <CaseCard key={d.id} def={d} running={latest[m].running} result={latest[m].results.find((r) => r.tc_id === d.id)} />
                  ))}
            </div>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
