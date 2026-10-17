"use client";
import { Info } from "lucide-react";
import { TagInput } from "@/components/tag-input";
import { Input, Label } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Tooltip } from "@/components/ui/tooltip";
import type { Criteria } from "@/lib/types";

const LANG_SUGGESTIONS = ["Rust", "Go", "TypeScript", "Python", "Java", "C++", "Kotlin", "Swift"];
const KW_SUGGESTIONS = ["async", "networking", "database", "react", "compiler", "kubernetes", "llm"];

export const DEFAULT_CRITERIA: Criteria = {
  languages: [],
  keywords: [],
  seed_repos: [],
  seed_users: [],
  window_days: 180,
  min_merged_prs: 2,
  max_candidates: 15,
  location: null,
  search: true,
};

function windowLabel(d: number) {
  if (d < 60) return `${d} days`;
  if (d < 365) return `${Math.round(d / 30)} months`;
  return `${(d / 365).toFixed(d % 365 ? 1 : 0)} year${d >= 730 ? "s" : ""}`;
}

function Field({ label, hint, children, htmlFor }: { label: string; hint?: string; children: React.ReactNode; htmlFor?: string }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-1">
        <Label htmlFor={htmlFor}>{label}</Label>
        {hint && (
          <Tooltip content={hint}>
            <button type="button" aria-label={`About ${label}`} className="text-muted-foreground/70 hover:text-foreground">
              <Info className="h-3 w-3" />
            </button>
          </Tooltip>
        )}
      </div>
      {children}
    </div>
  );
}

export function CriteriaEditor({ value, onChange, compact = false }: { value: Criteria; onChange: (c: Criteria) => void; compact?: boolean }) {
  const set = <K extends keyof Criteria>(k: K, v: Criteria[K]) => onChange({ ...value, [k]: v });
  return (
    <div className={compact ? "grid gap-4 sm:grid-cols-2" : "grid gap-5 sm:grid-cols-2"}>
      <Field label="Languages" hint="Hard requirement: the upstream repository's primary language must match." htmlFor="c-langs">
        <TagInput id="c-langs" value={value.languages} onChange={(v) => set("languages", v)} placeholder="Rust, Go…" suggestions={LANG_SUGGESTIONS} />
      </Field>
      <Field label="Keywords" hint="Used to find PRs (title/body). When no language is set, keywords must match repo name or topics." htmlFor="c-kws">
        <TagInput id="c-kws" value={value.keywords} onChange={(v) => set("keywords", v)} placeholder="async, quic…" suggestions={KW_SUGGESTIONS} />
      </Field>
      <Field label={`Recency window · ${windowLabel(value.window_days)}`} hint="Only PRs merged inside this window count (TC3).">
        <Slider aria-label="Recency window" min={30} max={730} step={15} value={[value.window_days]} onValueChange={([v]) => set("window_days", v)} />
      </Field>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Min merged PRs" htmlFor="c-min">
          <Input id="c-min" type="number" min={1} max={20} value={value.min_merged_prs} onChange={(e) => set("min_merged_prs", Math.max(1, Math.min(20, +e.target.value || 1)))} />
        </Field>
        <Field label="Max candidates" htmlFor="c-max">
          <Input id="c-max" type="number" min={1} max={50} value={value.max_candidates} onChange={(e) => set("max_candidates", Math.max(1, Math.min(50, +e.target.value || 1)))} />
        </Field>
      </div>
      <Field label="Seed repositories" hint="owner/name. The agent also mines all-time contributors of these repos — that's how stale contributors get surfaced and correctly excluded." htmlFor="c-repos">
        <TagInput id="c-repos" value={value.seed_repos} onChange={(v) => set("seed_repos", v)} placeholder="tokio-rs/tokio" />
      </Field>
      <Field label="Vet specific profiles" hint="GitHub logins to evaluate directly, e.g. referrals." htmlFor="c-users">
        <TagInput id="c-users" value={value.seed_users} onChange={(v) => set("seed_users", v)} placeholder="@login" prefix="@" />
      </Field>
      <Field label="Preferred location (optional)" hint="Shown as a match chip only — never used to exclude anyone." htmlFor="c-loc">
        <Input id="c-loc" value={value.location ?? ""} placeholder="e.g. India" onChange={(e) => set("location", e.target.value || null)} />
      </Field>
      <div className="flex items-end">
        <label className="flex w-full cursor-pointer items-center justify-between gap-3 rounded-md border px-3 py-2">
          <span className="text-sm">
            Discover new developers
            <span className="block text-xs text-muted-foreground">Off = only vet the listed profiles</span>
          </span>
          <Switch checked={value.search} onCheckedChange={(v) => set("search", v)} aria-label="Discover new developers" />
        </label>
      </div>
    </div>
  );
}
