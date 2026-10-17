import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { Classification, RunStatus } from "./types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function fmtDate(iso: string | null | undefined, opts: Intl.DateTimeFormatOptions = { dateStyle: "medium" }) {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("en-IN", opts).format(new Date(iso));
}

export function fmtDateTime(iso: string | null | undefined) {
  return fmtDate(iso, { dateStyle: "medium", timeStyle: "short" });
}

export function daysAgo(iso: string | null | undefined) {
  if (!iso) return null;
  return Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000));
}

export function relTime(iso: string | null | undefined) {
  const d = daysAgo(iso);
  if (d === null) return "—";
  if (d === 0) return "today";
  if (d === 1) return "yesterday";
  if (d < 31) return `${d}d ago`;
  if (d < 365) return `${Math.round(d / 30)}mo ago`;
  return `${(d / 365).toFixed(1)}y ago`;
}

export function compact(n: number) {
  return new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(n);
}

export const CLASS_META: Record<Classification, { label: string; short: string; tone: "success" | "warning" | "danger" | "muted" }> = {
  SHORTLISTED: { label: "Shortlisted", short: "Shortlisted", tone: "success" },
  EXCLUDED_RECENCY: { label: "Excluded · outside recency window", short: "Too old", tone: "warning" },
  EXCLUDED_FORK_ONLY: { label: "Excluded · fork-only activity", short: "Fork only", tone: "warning" },
  EXCLUDED_STACK: { label: "Excluded · different stack", short: "Off-stack", tone: "muted" },
  EXCLUDED_BOT: { label: "Excluded · automated account", short: "Bot", tone: "muted" },
  INSUFFICIENT_EVIDENCE: { label: "Insufficient evidence", short: "Not enough", tone: "muted" },
};

export const STATUS_META: Record<RunStatus, { label: string; tone: "success" | "warning" | "danger" | "muted" | "primary" }> = {
  PLANNED: { label: "Plan ready", tone: "primary" },
  RUNNING: { label: "Running", tone: "primary" },
  PENDING_APPROVAL: { label: "Awaiting approval", tone: "warning" },
  FINALISED: { label: "Finalised", tone: "success" },
  EXPORTED: { label: "Exported", tone: "success" },
  FAILED: { label: "Failed", tone: "danger" },
  CANCELLED: { label: "Cancelled", tone: "muted" },
};

export const RULE_LABELS: Record<string, string> = {
  merged: "Merged",
  in_window: "In window",
  base_not_fork: "Upstream, not a fork",
  not_own_repo: "Not own repo",
  stack_match: "Stack match",
  resolves: "URL resolves",
  author_match: "Author matches",
};

export const EXAMPLES = [
  "Rust async networking engineers active in the last 6 months, India preferred",
  "TypeScript React component library contributors, last 90 days, at least 2 merged PRs",
  "Python data-pipeline contributors in the last year",
  "Vet @tc3-stale-dev and @tc4-no-email for Rust, last 6 months",
];
