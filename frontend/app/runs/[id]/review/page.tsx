"use client";
import {
  ArrowLeft,
  Check,
  Download,
  FileJson,
  Link2,
  Loader2,
  Lock,
  Minus,
  Plus,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  X,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Avatar, CandidateDrawer, ContactChip, ScoreRing } from "@/components/candidates";
import { StatusBadge, SyntheticBadge, VerifyBadge } from "@/components/status";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogClose, DialogContent } from "@/components/ui/dialog";
import { Input, Label, Textarea } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { Candidate, RunDetail } from "@/lib/types";
import { cn, fmtDateTime } from "@/lib/utils";

const NAME_KEY = "sourcer.reviewer";

function useReviewer() {
  const [name, setName] = useState("");
  useEffect(() => {
    try {
      setName(localStorage.getItem(NAME_KEY) || "");
    } catch {}
  }, []);
  const save = (n: string) => {
    setName(n);
    try {
      localStorage.setItem(NAME_KEY, n);
    } catch {}
  };
  return [name, save] as const;
}

function ReviewRow({
  c,
  locked,
  onDecide,
  onOpen,
}: {
  c: Candidate;
  locked: boolean;
  onDecide: (c: Candidate, d: Candidate["review_decision"], note?: string, override?: boolean) => Promise<void>;
  onOpen: () => void;
}) {
  const [note, setNote] = useState(c.review_note ?? "");
  const [overrideOpen, setOverrideOpen] = useState(false);
  const [ack, setAck] = useState(false);
  const failed = c.evidence.filter((e) => e.qualifies && e.verified === false);
  const approve = () => (c.blocked ? setOverrideOpen(true) : onDecide(c, c.review_decision === "approved" ? "pending" : "approved", note));
  return (
    <div className={cn("rounded-xl border p-4 transition-colors", c.review_decision === "approved" && "border-success/40 bg-success/[0.03]", c.review_decision === "rejected" && "opacity-60", c.blocked && "border-danger/40")}>
      <div className="flex flex-wrap items-start gap-3">
        <Avatar c={c} />
        <button onClick={onOpen} className="min-w-0 flex-1 text-left">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium hover:underline">{c.profile.name || c.login}</span>
            <span className="font-mono text-xs text-muted-foreground">@{c.login}</span>
          </div>
          <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{c.summary || c.reason_text}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <VerifyBadge c={c} />
            <ContactChip c={c} />
            {c.fixture && <SyntheticBadge />}
          </div>
        </button>
        <ScoreRing score={c.score} />
        <div className="flex items-center gap-1" role="group" aria-label={`Decision for ${c.login}`}>
          <Button size="sm" variant={c.review_decision === "approved" ? "success" : "outline"} disabled={locked} onClick={approve} aria-pressed={c.review_decision === "approved"}>
            <Check /> Approve
          </Button>
          <Button size="sm" variant={c.review_decision === "rejected" ? "secondary" : "ghost"} disabled={locked} onClick={() => onDecide(c, c.review_decision === "rejected" ? "pending" : "rejected", note)} aria-pressed={c.review_decision === "rejected"}>
            <X /> Reject
          </Button>
        </div>
      </div>
      {c.blocked && (
        <div className="mt-3 rounded-lg bg-danger/10 p-3 text-xs text-danger">
          <div className="flex items-center gap-1.5 font-medium"><ShieldAlert className="h-3.5 w-3.5" /> Blocked: {failed.length} cited PR(s) failed independent re-verification</div>
          {failed.map((e) => (
            <div key={e.id} className="mt-1 font-mono text-[11px]">
              {e.repo} — {e.verify_error}
            </div>
          ))}
        </div>
      )}
      {!locked && (
        <Input
          className="mt-3 h-8 text-xs"
          placeholder="Add a note (optional) — saved with your decision"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          onBlur={() => note !== (c.review_note ?? "") && onDecide(c, c.review_decision, note)}
        />
      )}
      {locked && c.review_note && <p className="mt-2 text-xs text-muted-foreground">Note: {c.review_note}</p>}

      <Dialog open={overrideOpen} onOpenChange={setOverrideOpen}>
        <DialogContent title="Approve despite failed verification?" description="This candidate's evidence did not re-verify. Approving requires an explicit override and a note, both recorded in the audit log.">
          <div className="space-y-3">
            <Textarea rows={3} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Why is this candidate still valid? e.g. 'Checked manually: the remaining PR into asyncforge/reactor is genuine.'" />
            <label className="flex items-start gap-2 text-xs">
              <input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} className="mt-0.5 accent-[hsl(var(--primary))]" />
              I reviewed the failed evidence and take responsibility for this override.
            </label>
            <div className="flex justify-end gap-2">
              <DialogClose asChild><Button variant="outline">Cancel</Button></DialogClose>
              <Button
                variant="danger"
                disabled={!ack || note.trim().length < 5}
                onClick={async () => {
                  await onDecide(c, "approved", note, true);
                  setOverrideOpen(false);
                }}
              >
                Override & approve
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function ReviewPage({ params }: { params: { id: string } }) {
  const [run, setRun] = useState<RunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reviewer, setReviewer] = useReviewer();
  const [confirm, setConfirm] = useState(false);
  const [finalNote, setFinalNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [selected, setSelected] = useState<Candidate | null>(null);

  const load = useCallback(() => api.run(params.id).then(setRun).catch((e) => setError(e.message)), [params.id]);
  useEffect(() => {
    load();
  }, [load]);
  useEffect(() => {
    if (run?.share_token) setShareUrl(`${window.location.origin}/share/${run.share_token}`);
  }, [run?.share_token]);

  const draft = useMemo(() => (run?.candidates ?? []).filter((c) => c.classification === "SHORTLISTED").sort((a, b) => b.score - a.score), [run]);
  const approved = draft.filter((c) => c.review_decision === "approved");
  const rejected = draft.filter((c) => c.review_decision === "rejected");
  const pending = draft.filter((c) => c.review_decision === "pending");
  const blocked = draft.filter((c) => c.blocked);

  if (error) return <div className="container py-24 text-center text-sm text-muted-foreground">{error}</div>;
  if (!run)
    return (
      <div className="container max-w-5xl py-10 space-y-3">
        <Skeleton className="h-8 w-1/2" />
        {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 w-full rounded-xl" />)}
      </div>
    );

  const locked = run.status !== "PENDING_APPROVAL";
  const finalised = run.status === "FINALISED" || run.status === "EXPORTED";

  async function decide(c: Candidate, decision: Candidate["review_decision"], note?: string, override = false) {
    try {
      const updated = await api.review(run!.id, c.id, { decision, note: note || null, reviewer: reviewer || "recruiter", override_verification: override });
      setRun((r) => (r ? { ...r, candidates: r.candidates.map((x) => (x.id === updated.id ? updated : x)) } : r));
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  async function bulkApproveVerified() {
    for (const c of draft.filter((c) => !c.blocked && c.review_decision === "pending")) await decide(c, "approved");
  }

  async function finalise() {
    setBusy(true);
    try {
      const r = await api.finalise(run!.id, reviewer.trim(), finalNote || undefined);
      setRun(r);
      setConfirm(false);
      toast.success(`Shortlist finalised with ${approved.length} candidate(s)`);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function undo() {
    try {
      setRun(await api.undo(run!.id));
      toast("Finalisation undone — the draft is editable again");
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  async function share() {
    try {
      const { token } = await api.share(run!.id);
      const url = `${window.location.origin}/share/${token}`;
      setShareUrl(url);
      await navigator.clipboard.writeText(url);
      toast.success("Read-only link copied");
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  return (
    <div className="container max-w-6xl py-8">
      <Link href={`/runs/${run.id}`} className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to run trace
      </Link>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">{finalised ? "Final shortlist" : "Review & approve"}</h1>
        <StatusBadge status={run.status} />
      </div>
      <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
        {finalised
          ? `Approved by ${run.approver} on ${fmtDateTime(run.finalised_at)}.`
          : "The agent proposed this draft. Approve or reject each person — nothing is finalised, exported or shared until you confirm."}
      </p>

      <div className="mt-6 grid gap-6 lg:grid-cols-12">
        <div className="space-y-3 lg:col-span-8">
          {!locked && draft.some((c) => !c.blocked && c.review_decision === "pending") && (
            <div className="flex items-center justify-between rounded-lg border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
              <span>{pending.length} pending · {blocked.length} blocked by verification</span>
              <Button size="sm" variant="ghost" onClick={bulkApproveVerified}><ShieldCheck /> Approve all verified</Button>
            </div>
          )}
          {draft.length === 0 && <div className="rounded-xl border border-dashed p-10 text-center text-sm text-muted-foreground">No candidates were shortlisted in this run.</div>}
          {draft.map((c) => (
            <ReviewRow key={c.id} c={c} locked={locked} onDecide={decide} onOpen={() => setSelected(c)} />
          ))}
        </div>

        <div className="lg:col-span-4">
          <div className="space-y-4 lg:sticky lg:top-20">
            <Card>
              <CardHeader className="border-b pb-3">
                <CardTitle>Proposed change</CardTitle>
                <p className="font-mono text-[11px] text-muted-foreground">→ Final shortlist · run #{run.id}</p>
              </CardHeader>
              <CardContent className="space-y-1 pt-4 font-mono text-xs">
                {approved.map((c) => <div key={c.id} className="flex items-center gap-2 text-success"><Plus className="h-3 w-3" /> @{c.login} <span className="ml-auto tabular-nums">{c.score.toFixed(0)}</span></div>)}
                {rejected.map((c) => <div key={c.id} className="flex items-center gap-2 text-danger line-through decoration-danger/50"><Minus className="h-3 w-3" /> @{c.login}</div>)}
                {pending.map((c) => <div key={c.id} className="flex items-center gap-2 text-muted-foreground"><span className="w-3 text-center">?</span> @{c.login} <span className="ml-auto text-[10px]">{c.blocked ? "blocked" : "pending"}</span></div>)}
                {draft.length === 0 && <div className="text-muted-foreground">nothing to change</div>}
                {pending.length > 0 && !locked && <p className="pt-2 font-sans text-[11px] text-muted-foreground">Pending candidates are left out of the final list.</p>}
              </CardContent>
            </Card>

            {!finalised ? (
              <Card>
                <CardContent className="space-y-3 pt-5">
                  <div className="space-y-1.5">
                    <Label htmlFor="approver">Approver name</Label>
                    <Input id="approver" value={reviewer} onChange={(e) => setReviewer(e.target.value)} placeholder="Your name" />
                  </div>
                  <Button className="w-full" size="lg" disabled={!approved.length || reviewer.trim().length < 2 || locked} onClick={() => setConfirm(true)}>
                    <Lock /> Approve & finalise ({approved.length})
                  </Button>
                  <p className="text-[11px] leading-relaxed text-muted-foreground">Timestamped and written to the audit log with your name. You can undo until the shortlist is exported.</p>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardHeader className="pb-2"><CardTitle>Export & share</CardTitle></CardHeader>
                <CardContent className="space-y-2">
                  <div className="grid grid-cols-2 gap-2">
                    <Button asChild variant="outline"><a href={api.exportUrl(run.id, "csv")} onClick={() => setTimeout(load, 800)}><Download /> CSV</a></Button>
                    <Button asChild variant="outline"><a href={api.exportUrl(run.id, "json")} target="_blank" rel="noreferrer" onClick={() => setTimeout(load, 800)}><FileJson /> JSON</a></Button>
                  </div>
                  <Button variant="outline" className="w-full" onClick={share}><Link2 /> {shareUrl ? "Copy read-only link" : "Create read-only link"}</Button>
                  {shareUrl && <a href={shareUrl} target="_blank" rel="noreferrer" className="block truncate font-mono text-[11px] text-primary hover:underline">{shareUrl}</a>}
                  {run.status === "FINALISED" ? (
                    <>
                      <Button variant="ghost" className="w-full" onClick={undo}><RotateCcw /> Undo finalisation</Button>
                      <p className="text-[11px] text-muted-foreground">Exporting locks the shortlist; undo is no longer possible afterwards.</p>
                    </>
                  ) : (
                    <p className="flex items-center gap-1 text-[11px] text-muted-foreground"><Lock className="h-3 w-3" /> Exported {fmtDateTime(run.exported_at)} — locked.</p>
                  )}
                </CardContent>
              </Card>
            )}
            {blocked.length > 0 && !locked && (
              <div className="rounded-lg border border-danger/30 bg-danger/5 p-3 text-xs text-danger">
                <ShieldAlert className="mb-1 h-3.5 w-3.5" />
                {blocked.length} candidate(s) can&apos;t be approved until their failed evidence is reviewed (override requires a note).
              </div>
            )}
          </div>
        </div>
      </div>

      <Dialog open={confirm} onOpenChange={setConfirm}>
        <DialogContent title={`Finalise ${approved.length} candidate(s)?`} description={`Destination: final shortlist for run #${run.id}. Approver: ${reviewer}.`}>
          <div className="space-y-3">
            <div className="max-h-40 space-y-1 overflow-y-auto rounded-md border bg-muted/30 p-2 font-mono text-xs">
              {approved.map((c) => <div key={c.id} className="text-success">+ @{c.login}</div>)}
              {[...rejected, ...pending].map((c) => <div key={c.id} className="text-muted-foreground">− @{c.login} (left out)</div>)}
            </div>
            <Textarea rows={2} placeholder="Approval note (optional)" value={finalNote} onChange={(e) => setFinalNote(e.target.value)} />
            <div className="flex justify-end gap-2">
              <DialogClose asChild><Button variant="outline">Cancel</Button></DialogClose>
              <Button onClick={finalise} disabled={busy}>{busy ? <Loader2 className="animate-spin" /> : <Check />} Confirm & finalise</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <CandidateDrawer c={selected} open={!!selected} onOpenChange={(o) => !o && setSelected(null)} window_days={run.criteria.window_days} />
      {finalised && approved.length > 0 && (
        <p className="mt-6 text-center text-xs text-muted-foreground">
          <Badge tone="success" className="mr-1"><Check /> {approved.length} approved</Badge> Contacts only from public profile fields — blank ones were never guessed.
        </p>
      )}
    </div>
  );
}
