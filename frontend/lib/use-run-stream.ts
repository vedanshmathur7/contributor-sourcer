"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { Candidate, RunDetail, RunSummary, Step } from "./types";

export interface WaitInfo {
  seconds: number;
  reason: string;
  until: number;
}

function upsert<T extends { id: string }>(list: T[], item: T): T[] {
  const i = list.findIndex((x) => x.id === item.id);
  if (i === -1) return [...list, item];
  const next = list.slice();
  next[i] = item;
  return next;
}

/** Snapshot + live SSE updates for one run. Reconnects automatically; `restart()` after starting a run. */
export function useRunStream(id: string) {
  const [run, setRun] = useState<RunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [wait, setWait] = useState<WaitInfo | null>(null);
  const [live, setLive] = useState(false);
  const [nonce, setNonce] = useState(0);
  const esRef = useRef<EventSource | null>(null);

  const reload = useCallback(async () => {
    try {
      setRun(await api.run(id));
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [id]);

  useEffect(() => {
    const es = new EventSource(api.eventsUrl(id));
    esRef.current = es;
    const parse = (e: MessageEvent) => JSON.parse(e.data);

    es.addEventListener("snapshot", (e) => {
      setRun(parse(e as MessageEvent));
      setError(null);
      setLive(true);
    });
    es.addEventListener("step", (e) => {
      const { step } = parse(e as MessageEvent) as { step: Step };
      setRun((r) => (r ? { ...r, steps: upsert(r.steps, step).sort((a, b) => a.seq - b.seq) } : r));
    });
    es.addEventListener("candidate", (e) => {
      const { candidate } = parse(e as MessageEvent) as { candidate: Candidate };
      setRun((r) => (r ? { ...r, candidates: upsert(r.candidates, candidate) } : r));
    });
    es.addEventListener("run", (e) => {
      const { run: summary } = parse(e as MessageEvent) as { run: RunSummary };
      setRun((r) => (r ? { ...r, ...summary } : r));
    });
    es.addEventListener("wait", (e) => {
      const w = parse(e as MessageEvent) as { seconds: number; reason: string };
      setWait({ ...w, until: Date.now() + w.seconds * 1000 });
    });
    es.addEventListener("done", () => {
      es.close();
      setLive(false);
      setWait(null);
      reload();
    });
    es.addEventListener("error", (e) => {
      const data = (e as MessageEvent).data;
      if (data) {
        setError(JSON.parse(data).detail);
        es.close();
      } else if (es.readyState === EventSource.CLOSED) {
        setLive(false);
        reload();
      }
    });
    return () => es.close();
  }, [id, nonce, reload]);

  return { run, setRun, error, wait, live, reload, restart: () => setNonce((n) => n + 1) };
}
