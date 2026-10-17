import { AlertTriangle, BadgeCheck, CircleDashed, Loader2, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Tooltip } from "@/components/ui/tooltip";
import type { Candidate, Classification, RunStatus } from "@/lib/types";
import { CLASS_META, STATUS_META } from "@/lib/utils";

export function StatusBadge({ status }: { status: RunStatus }) {
  const m = STATUS_META[status];
  return (
    <Badge tone={m.tone === "primary" ? "primary" : m.tone}>
      {status === "RUNNING" && <Loader2 className="animate-spin" />}
      {m.label}
    </Badge>
  );
}

export function ClassBadge({ value, short = false }: { value: Classification; short?: boolean }) {
  const m = CLASS_META[value];
  return <Badge tone={m.tone}>{short ? m.short : m.label}</Badge>;
}

export function VerifyBadge({ c }: { c: Pick<Candidate, "verification_status" | "blocked"> }) {
  if (c.verification_status === "verified")
    return (
      <Tooltip content="Every cited PR was re-fetched from the REST API after the draft was built and re-checked: resolves, merged, in window, author matches, upstream not a fork.">
        <span><Badge tone="success"><BadgeCheck /> Verified</Badge></span>
      </Tooltip>
    );
  if (c.verification_status === "failed")
    return (
      <Tooltip content="At least one cited PR failed independent re-verification. The candidate is blocked from approval until a human reviews it.">
        <span><Badge tone="danger"><ShieldAlert /> {c.blocked ? "Needs review" : "Reviewed override"}</Badge></span>
      </Tooltip>
    );
  return <Badge tone="muted"><CircleDashed /> Not verified</Badge>;
}

export function SyntheticBadge() {
  return (
    <Tooltip content="Fixture mode: this person, repo and PR are synthetic, GitHub-shaped test data (per the brief's rule on personal data).">
      <span><Badge tone="outline"><AlertTriangle /> Synthetic</Badge></span>
    </Tooltip>
  );
}
