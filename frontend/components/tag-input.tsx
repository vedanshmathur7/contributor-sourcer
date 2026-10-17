"use client";
import { X } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

export function TagInput({
  value,
  onChange,
  placeholder,
  suggestions = [],
  prefix,
  className,
  id,
}: {
  value: string[];
  onChange: (v: string[]) => void;
  placeholder?: string;
  suggestions?: string[];
  prefix?: string;
  className?: string;
  id?: string;
}) {
  const [draft, setDraft] = useState("");
  const add = (raw: string) => {
    const items = raw.split(",").map((s) => s.trim().replace(/^@/, "")).filter(Boolean);
    const next = [...value];
    for (const it of items) if (!next.some((v) => v.toLowerCase() === it.toLowerCase())) next.push(it);
    onChange(next);
    setDraft("");
  };
  const remaining = suggestions.filter((s) => !value.some((v) => v.toLowerCase() === s.toLowerCase())).slice(0, 6);
  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex min-h-9 flex-wrap items-center gap-1.5 rounded-md border border-input bg-background px-2 py-1.5 focus-within:ring-2 focus-within:ring-ring/60">
        {value.map((v) => (
          <span key={v} className="inline-flex items-center gap-1 rounded bg-secondary px-1.5 py-0.5 text-xs font-medium">
            {prefix}
            {v}
            <button type="button" aria-label={`Remove ${v}`} onClick={() => onChange(value.filter((x) => x !== v))} className="text-muted-foreground hover:text-foreground">
              <X className="h-3 w-3" />
            </button>
          </span>
        ))}
        <input
          id={id}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if ((e.key === "Enter" || e.key === ",") && draft.trim()) {
              e.preventDefault();
              add(draft);
            } else if (e.key === "Backspace" && !draft && value.length) {
              onChange(value.slice(0, -1));
            }
          }}
          onBlur={() => draft.trim() && add(draft)}
          placeholder={value.length ? "" : placeholder}
          className="min-w-[6rem] flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
        />
      </div>
      {remaining.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {remaining.map((s) => (
            <button key={s} type="button" onClick={() => add(s)} className="rounded-full border border-dashed px-2 py-0.5 text-[11px] text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground">
              + {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
