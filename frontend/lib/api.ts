import type {
  AuditEntry,
  Candidate,
  Criteria,
  Meta,
  Mode,
  Proposal,
  RunDetail,
  RunSummary,
  TestCaseDef,
  TestResult,
} from "./types";

const RAW_API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
// Render's fromService gives a bare host; accept both "host" and "https://host".
export const API_URL = (/^https?:\/\//.test(RAW_API) ? RAW_API : `https://${RAW_API}`).replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "content-type": "application/json", ...(init?.headers || {}) },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, "Can't reach the agent API. It may be waking up — try again in a few seconds.");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {}
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  meta: () => req<Meta>("/api/meta"),
  health: () => req<{ status: string }>("/api/health"),
  plan: (body: { query: string; mode: Mode; overrides?: Partial<Criteria> }) =>
    req<RunDetail>("/api/runs/plan", { method: "POST", body: JSON.stringify(body) }),
  updateCriteria: (id: string, criteria: Criteria) =>
    req<RunDetail>(`/api/runs/${id}/criteria`, { method: "PATCH", body: JSON.stringify({ criteria }) }),
  start: (id: string) => req<RunSummary>(`/api/runs/${id}/start`, { method: "POST" }),
  run: (id: string) => req<RunDetail>(`/api/runs/${id}`),
  runs: (limit = 30) => req<{ runs: RunSummary[]; total: number }>(`/api/runs?limit=${limit}`),
  deleteRun: (id: string) => req<{ deleted: string }>(`/api/runs/${id}`, { method: "DELETE" }),
  review: (
    runId: string,
    candId: string,
    body: { decision: Candidate["review_decision"]; note?: string | null; reviewer?: string; override_verification?: boolean },
  ) =>
    req<Candidate>(`/api/runs/${runId}/candidates/${candId}/review`, { method: "POST", body: JSON.stringify(body) }),
  proposal: (id: string) => req<Proposal>(`/api/runs/${id}/proposal`),
  finalise: (id: string, approver: string, note?: string) =>
    req<RunDetail & { already_finalised?: boolean }>(`/api/runs/${id}/finalise`, {
      method: "POST",
      body: JSON.stringify({ approver, note }),
    }),
  undo: (id: string) => req<RunDetail>(`/api/runs/${id}/undo`, { method: "POST" }),
  share: (id: string) => req<{ token: string }>(`/api/runs/${id}/share`, { method: "POST" }),
  shared: (token: string) => req<{ run: RunSummary; candidates: Candidate[] }>(`/api/share/${token}`),
  audit: (runId?: string) => req<AuditEntry[]>(`/api/audit${runId ? `?run_id=${runId}` : ""}`),
  testDefinitions: () =>
    req<{ cases: TestCaseDef[]; live_inputs: Record<string, { login: string | null; languages: string[]; window_days: number }>; live_available: boolean }>(
      "/api/testcases/definitions",
    ),
  testLatest: () =>
    req<Record<Mode, { running: boolean; batch_id: string | null; results: TestResult[] }>>("/api/testcases/latest"),
  runTests: (mode: Mode, inputs?: Record<string, unknown>) =>
    req<{ started: boolean }>("/api/testcases/run", { method: "POST", body: JSON.stringify({ mode, inputs }) }),
  exportUrl: (id: string, format: "csv" | "json") => `${API_URL}/api/runs/${id}/export?format=${format}`,
  eventsUrl: (id: string) => `${API_URL}/api/runs/${id}/events`,
  fixtureUrl: (rawPath: string) => `${API_URL}${rawPath}`,
};
