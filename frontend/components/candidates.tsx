"use client";
import { motion } from "framer-motion";
import {
  Building2,
  Check,
  ExternalLink,
  FileJson,
  GitFork,
  GitMerge,
  Github,
  Link2,
  Mail,
  MailX,
  MapPin,
  ShieldAlert,
  Star,
  Users,
  X,
} from "lucide-react";
import { ClassBadge, SyntheticBadge, VerifyBadge } from "@/components/status";
import { Badge } from "@/components/ui/badge";
import { Sheet } from "@/components/ui/dialog";
import { Tooltip } from "@/components/ui/tooltip";
import { api } from "@/lib/api";
import type { Candidate, Evidence } from "@/lib/types";
import { CLASS_META, RULE_LABELS, cn, compact, fmtDate, relTime } from "@/lib/utils";

export function Avatar({ c, size = 40 }: { c: Candidate; size?: number }) {
  const name = c.profile.name || c.login;
  const initials = name.replace(/\(.*\)/, "").trim().split(/\s+/).map((p) => p[0]).slice(0, 2).join("").toUpperCase();
  const hue = [...c.login].reduce((a, ch) => a + ch.charCodeAt(0), 0) % 360;
  if (c.profile.avatar_url)
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={c.profile.avatar_url} alt="" width={size} height={size} className="shrink-0 rounded-full border" style={{ width: size, height: size }} />;
  return (
    <span
      className="grid shrink-0 place-items-center rounded-full text-xs font-semibold text-white"
      style={{ width: size, height: size, background: `linear-gradient(135deg, hsl(${hue} 70% 55%), hsl(${(hue + 50) % 360} 70% 45%))` }}
      aria-hidden
    >
      {initials}
    </span>
  );
}

export function ScoreRing({ score, size = 44, muted = false }: { score: number; size?: number; muted?: boolean }) {
  const r = (size - 6) / 2;
  const circ = 2 * Math.PI * r;
  return (
    <Tooltip content="Deterministic evidence score (0–100) — open the candidate for the breakdown.">
      <span className="relative inline-grid shrink-0 place-items-center" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="hsl(var(--border))" strokeWidth={3} />
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={muted ? "hsl(var(--muted-foreground))" : "hsl(var(--primary))"}
            strokeWidth={3}
            strokeLinecap="round"
            strokeDasharray={circ}
            initial={{ strokeDashoffset: circ }}
            animate={{ strokeDashoffset: circ * (1 - Math.min(score, 100) / 100) }}
            transition={{ duration: 0.8, ease: "easeOut" }}
          />
        </svg>
        <span className="absolute text-xs font-semibold tabular-nums">{Math.round(score)}</span>
      </span>
    </Tooltip>
  );
}

export function ContactChip({ c }: { c: Candidate }) {
  if (c.contact_email)
    return (
      <Tooltip content="Taken from the profile's public email field — the only source we ever use.">
        <a href={`mailto:${c.contact_email}`} className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground" onClick={(e) => e.stopPropagation()}>
          <Mail className="h-3 w-3" /> {c.contact_email}
        </a>
      </Tooltip>
    );
  return (
    <Tooltip content={c.contact_note ?? "Not public"}>
      <span className="inline-flex items-center gap-1 text-xs text-muted-foreground"><MailX className="h-3 w-3" /> Not public</span>
    </Tooltip>
  );
}

export function CandidateCard({ c, onOpen, rank }: { c: Candidate; onOpen: () => void; rank?: number }) {
  const short = c.classification === "SHORTLISTED";
  const q = c.evidence.filter((e) => e.qualifies);
  const repos = [...new Set(q.map((e) => e.repo))];
  return (
    <motion.button
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      onClick={onOpen}
      className={cn(
        "group w-full rounded-xl border bg-card p-4 text-left transition-all hover:border-primary/40 hover:shadow-md hover:shadow-primary/[0.04] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        c.blocked && "border-danger/40",
      )}
    >
      <div className="flex items-start gap-3">
        {rank !== undefined && <span className="mt-2.5 w-4 text-xs font-medium tabular-nums text-muted-foreground">{rank}</span>}
        <Avatar c={c} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="truncate text-sm font-medium">{c.profile.name || c.login}</span>
            <span className="font-mono text-xs text-muted-foreground">@{c.login}</span>
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            {c.profile.location && (
              <span className={cn("inline-flex items-center gap-1", c.profile.location_match && "text-success")}>
                <MapPin className="h-3 w-3" /> {c.profile.location}
              </span>
            )}
            <ContactChip c={c} />
          </div>
        </div>
        {short ? <ScoreRing score={c.score} /> : <ClassBadge value={c.classification} short />}
      </div>
      <p className="mt-3 line-clamp-2 text-xs leading-relaxed text-muted-foreground">{c.reason_text}</p>
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        {short && <VerifyBadge c={c} />}
        {short && repos.slice(0, 3).map((r) => <Badge key={r} tone="outline"><GitMerge /> {r}</Badge>)}
        {c.review_decision === "approved" && <Badge tone="success"><Check /> Approved</Badge>}
        {c.review_decision === "rejected" && <Badge tone="muted"><X /> Rejected</Badge>}
        {c.fixture && <SyntheticBadge />}
      </div>
    </motion.button>
  );
}

function RuleChips({ checks }: { checks: Record<string, boolean> }) {
  return (
    <div className="flex flex-wrap gap-1">
      {Object.entries(checks).map(([k, ok]) => (
        <span key={k} className={cn("inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[10px] font-medium", ok ? "bg-success/10 text-success" : "bg-danger/10 text-danger")}>
          {ok ? <Check className="h-2.5 w-2.5" /> : <X className="h-2.5 w-2.5" />} {RULE_LABELS[k] ?? k}
        </span>
      ))}
    </div>
  );
}

function EvidenceRow({ e }: { e: Evidence }) {
  const kindLabel = e.kind === "pr" ? null : e.kind === "own_project" ? "Own repo" : e.kind === "fork_repo" ? "Fork repo" : "Into a fork";
  return (
    <div className={cn("rounded-lg border p-3", e.qualifies ? "bg-card" : "bg-muted/30")}>
      <div className="flex items-start gap-2">
        {e.repo_is_fork ? <GitFork className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warning" /> : <GitMerge className={cn("mt-0.5 h-3.5 w-3.5 shrink-0", e.qualifies ? "text-success" : "text-muted-foreground")} />}
        <div className="min-w-0 flex-1">
          <a href={e.url} target="_blank" rel="noreferrer" className="text-sm font-medium leading-snug hover:text-primary hover:underline">
            {e.title}
          </a>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            <span className="font-mono">{e.repo}</span>
            <span className="inline-flex items-center gap-0.5"><Star className="h-3 w-3" /> {compact(e.repo_stars)}</span>
            {e.repo_language && <span>{e.repo_language}</span>}
            {e.merged_at && <span>{e.kind === "fork_repo" ? "pushed" : "merged"} {fmtDate(e.merged_at)} · {relTime(e.merged_at)}</span>}
            {e.kind !== "fork_repo" && <span className="font-mono"><span className="text-success">+{e.additions}</span> <span className="text-danger">−{e.deletions}</span></span>}
            {kindLabel && <Badge tone="warning">{kindLabel}</Badge>}
          </div>
          <div className="mt-2"><RuleChips checks={e.rule_checks} /></div>
          {e.verified !== null && (
            <div className={cn("mt-2 rounded-md px-2 py-1.5 text-[11px]", e.verified ? "bg-success/5 text-success" : "bg-danger/5 text-danger")}>
              {e.verified ? (
                <>Re-verified via REST {fmtDate(e.verified_at, { dateStyle: "medium", timeStyle: "short" })} · merged_at {String(e.observed.merged_at ?? "").slice(0, 10)} · author @{String(e.observed.author ?? "")} · upstream not a fork</>
              ) : (
                <>Verification failed: {e.verify_error}</>
              )}
            </div>
          )}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <a href={e.url} target="_blank" rel="noreferrer" aria-label="Open source" className="rounded p-1 text-muted-foreground hover:bg-secondary hover:text-foreground"><ExternalLink className="h-3.5 w-3.5" /></a>
          {e.raw_url && (
            <Tooltip content="Recorded synthetic JSON behind this evidence">
              <a href={api.fixtureUrl(e.raw_url)} target="_blank" rel="noreferrer" aria-label="View recorded JSON" className="rounded p-1 text-muted-foreground hover:bg-secondary hover:text-foreground"><FileJson className="h-3.5 w-3.5" /></a>
            </Tooltip>
          )}
        </div>
      </div>
    </div>
  );
}

function CitedSummary({ text, citations }: { text: string; citations: string[] }) {
  const parts = text.replace(/\(\s*(https?:\/\/[^\s)]+)\s*\)/g, "$1").split(/(https?:\/\/[^\s)]+)/g);
  return (
    <p className="text-sm leading-relaxed">
      {parts.map((p, i) => {
        const idx = citations.indexOf(p.replace(/[.,;]$/, ""));
        if (idx >= 0)
          return (
            <a key={i} href={p} target="_blank" rel="noreferrer" className="mx-0.5 inline-flex items-center rounded bg-primary/10 px-1 align-baseline font-mono text-[10px] font-semibold text-primary hover:bg-primary/20">
              [{idx + 1}]
            </a>
          );
        return <span key={i}>{p}</span>;
      })}
    </p>
  );
}

export function CandidateDrawer({ c, open, onOpenChange, window_days }: { c: Candidate | null; open: boolean; onOpenChange: (o: boolean) => void; window_days: number }) {
  if (!c) return null;
  const q = c.evidence.filter((e) => e.qualifies);
  const other = c.evidence.filter((e) => !e.qualifies);
  const short = c.classification === "SHORTLISTED";
  return (
    <Sheet open={open} onOpenChange={onOpenChange} title={`Candidate @${c.login}`} description={c.reason_text}>
      <div className="border-b bg-gradient-to-b from-primary/[0.06] to-transparent p-6">
        <div className="flex items-start gap-4">
          <Avatar c={c} size={56} />
          <div className="min-w-0 flex-1">
            <h2 className="text-lg font-semibold">{c.profile.name || c.login}</h2>
            <a href={c.profile.html_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-mono text-xs text-muted-foreground hover:text-foreground">
              <Github className="h-3 w-3" /> @{c.login}
            </a>
            {c.profile.bio && <p className="mt-2 text-sm text-muted-foreground">{c.profile.bio}</p>}
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
              {c.profile.location && <span className="inline-flex items-center gap-1"><MapPin className="h-3 w-3" /> {c.profile.location}{c.profile.location_match && <Badge tone="success" className="ml-1">matches preference</Badge>}</span>}
              {c.profile.company && <span className="inline-flex items-center gap-1"><Building2 className="h-3 w-3" /> {c.profile.company}</span>}
              {c.profile.followers !== undefined && <span className="inline-flex items-center gap-1"><Users className="h-3 w-3" /> {compact(c.profile.followers)} followers</span>}
              {c.profile.blog && <a href={c.profile.blog.startsWith("http") ? c.profile.blog : `https://${c.profile.blog}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:text-foreground"><Link2 className="h-3 w-3" /> website</a>}
              {c.profile.via && <span>found via {c.profile.via.replace("contributor:", "contributors of ")}</span>}
            </div>
          </div>
          {short && <ScoreRing score={c.score} size={60} />}
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <ClassBadge value={c.classification} />
          {short && <VerifyBadge c={c} />}
          {c.fixture && <SyntheticBadge />}
        </div>
      </div>

      <div className="space-y-6 p-6">
        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Contact</h3>
          {c.contact_email ? (
            <div className="flex items-center gap-2 rounded-lg border p-3 text-sm">
              <Mail className="h-4 w-4 text-muted-foreground" />
              <a href={`mailto:${c.contact_email}`} className="hover:underline">{c.contact_email}</a>
              <span className="ml-auto text-xs text-muted-foreground">public profile field</span>
            </div>
          ) : (
            <div className="flex items-start gap-2 rounded-lg border border-dashed p-3 text-sm">
              <MailX className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
              <div>
                <div className="font-medium">Not public</div>
                <div className="text-xs text-muted-foreground">{c.contact_note}</div>
              </div>
            </div>
          )}
        </section>

        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">{short ? "Why this person" : "Why excluded?"}</h3>
          <div className={cn("rounded-lg border p-4", !short && "border-warning/30 bg-warning/5")}>
            {short && c.summary ? <CitedSummary text={c.summary} citations={c.summary_citations} /> : <p className="text-sm leading-relaxed">{c.reason_text}</p>}
            <div className="mt-2 font-mono text-[10.5px] text-muted-foreground">rule: {c.reason_code} · {CLASS_META[c.classification].label}</div>
            {c.blocked && (
              <div className="mt-3 flex items-start gap-2 rounded-md bg-danger/10 p-2 text-xs text-danger">
                <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" /> Blocked from approval: some cited evidence failed independent re-verification. Review it below before deciding.
              </div>
            )}
          </div>
        </section>

        {short && Object.keys(c.score_breakdown).length > 0 && (
          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Score breakdown · {c.score.toFixed(1)} / 100</h3>
            <div className="space-y-2.5 rounded-lg border p-4">
              {Object.entries(c.score_breakdown).map(([k, v]) => (
                <div key={k}>
                  <div className="flex justify-between text-xs">
                    <span className="font-medium capitalize">{k.replace("_", " ")}</span>
                    <span className="tabular-nums text-muted-foreground">{v.points} / {v.max}</span>
                  </div>
                  <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-secondary">
                    <motion.div className="h-full rounded-full bg-primary" initial={{ width: 0 }} animate={{ width: `${(v.points / v.max) * 100}%` }} transition={{ duration: 0.6 }} />
                  </div>
                  <div className="mt-0.5 text-[11px] text-muted-foreground">{v.note}</div>
                </div>
              ))}
            </div>
          </section>
        )}

        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Qualifying evidence · {q.length} merged PR{q.length === 1 ? "" : "s"} in the last {window_days} days
          </h3>
          <div className="space-y-2">
            {q.length ? q.map((e) => <EvidenceRow key={e.id} e={e} />) : <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">No PR passed every rule.</p>}
          </div>
        </section>

        {other.length > 0 && (
          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Seen but not counted · {other.length}</h3>
            <div className="space-y-2">{other.slice(0, 15).map((e) => <EvidenceRow key={e.id} e={e} />)}</div>
          </section>
        )}
      </div>
    </Sheet>
  );
}
