import { Download, ExternalLink, Presentation } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Demo video" };

export default function DemoPage() {
  return (
    <div className="container max-w-5xl py-10">
      <h1 className="text-2xl font-semibold tracking-tight">Demo video · 2 min</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        A captioned, unedited walkthrough of the real app in Fixture mode: plan → live agent trace → evidence → TC1–TC4 → human approval → official test-case run.
      </p>
      <div className="mt-6 overflow-hidden rounded-2xl border bg-black shadow-xl">
        <video src="/demo.mp4" poster="/demo-poster.jpg" controls playsInline preload="metadata" className="aspect-video w-full" />
      </div>
      <div className="mt-4 flex flex-wrap gap-2 text-sm">
        <a href="/demo.mp4" download className="inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 hover:bg-secondary"><Download className="h-4 w-4" /> Download MP4</a>
        <Link href="/" className="inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 hover:bg-secondary"><ExternalLink className="h-4 w-4" /> Try it live</Link>
        <Link href="/deck" className="inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 hover:bg-secondary"><Presentation className="h-4 w-4" /> Presentation</Link>
      </div>
    </div>
  );
}
