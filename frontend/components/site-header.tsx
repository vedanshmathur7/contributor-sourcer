"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Github, Menu, X } from "lucide-react";
import { Logo } from "@/components/logo";
import { ThemeToggle } from "@/components/theme-toggle";
import { Badge } from "@/components/ui/badge";
import { Tooltip } from "@/components/ui/tooltip";
import { api } from "@/lib/api";
import type { Meta } from "@/lib/types";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "New search" },
  { href: "/runs", label: "Runs" },
  { href: "/tests", label: "Test cases" },
  { href: "/audit", label: "Audit log" },
  { href: "/about", label: "How it works" },
];

export function SiteHeader() {
  const path = usePathname();
  const [meta, setMeta] = useState<Meta | null>(null);
  const [offline, setOffline] = useState(false);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    api.meta().then(setMeta).catch(() => setOffline(true));
  }, []);
  useEffect(() => setOpen(false), [path]);

  const active = (href: string) => (href === "/" ? path === "/" : path.startsWith(href));
  return (
    <header className="sticky top-0 z-40 border-b bg-background/75 backdrop-blur-xl">
      <div className="container flex h-14 items-center gap-6">
        <Link href="/" className="flex items-center gap-2.5 font-semibold tracking-tight">
          <Logo />
          <span className="hidden sm:inline">Contributor Sourcer</span>
        </Link>
        <nav className="hidden items-center gap-1 md:flex">
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              className={cn(
                "rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground",
                active(n.href) && "bg-secondary text-foreground",
              )}
            >
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          {offline ? (
            <Badge tone="danger">API offline</Badge>
          ) : meta ? (
            <Tooltip
              content={
                <div className="space-y-1">
                  <div>Fixture mode: always available (synthetic data)</div>
                  <div>Live mode: {meta.live_available ? "GitHub token configured (read-only)" : "no GitHub token on server"}</div>
                  <div>LLM: {meta.llm_enabled ? `${meta.llm_provider} · ${meta.llm_model}` : "deterministic fallback"}</div>
                  <div className="text-muted-foreground">build {meta.commit}</div>
                </div>
              }
            >
              <span className="hidden cursor-default items-center gap-1.5 sm:flex">
                <Badge tone={meta.live_available ? "success" : "muted"}>
                  <span className={cn("h-1.5 w-1.5 rounded-full", meta.live_available ? "bg-success" : "bg-muted-foreground")} />
                  {meta.live_available ? "Live ready" : "Fixture"}
                </Badge>
                <Badge tone={meta.llm_enabled ? "primary" : "muted"}>{meta.llm_enabled ? meta.llm_provider : "no-LLM"}</Badge>
              </span>
            </Tooltip>
          ) : null}
          <ThemeToggle />
          <button className="rounded-md p-2 hover:bg-secondary md:hidden" aria-label="Menu" onClick={() => setOpen(!open)}>
            {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>
      </div>
      {open && (
        <nav className="container flex flex-col gap-1 border-t py-2 md:hidden">
          {NAV.map((n) => (
            <Link key={n.href} href={n.href} className={cn("rounded-md px-3 py-2 text-sm", active(n.href) && "bg-secondary")}>
              {n.label}
            </Link>
          ))}
        </nav>
      )}
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="mt-24 border-t">
      <div className="container flex flex-col items-start justify-between gap-3 py-8 text-xs text-muted-foreground sm:flex-row sm:items-center">
        <div className="flex items-center gap-2">
          <Logo className="h-4 w-4" />
          Public data only · public email field only · read-only GitHub token · human approval required
        </div>
        <div className="flex items-center gap-4">
          <Link href="/about" className="hover:text-foreground">Privacy & safety</Link>
          <span className="inline-flex items-center gap-1"><Github className="h-3.5 w-3.5" /> Built on the official GitHub API</span>
        </div>
      </div>
    </footer>
  );
}
