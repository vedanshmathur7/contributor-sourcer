export type Mode = "fixture" | "live";

export type RunStatus =
  | "PLANNED"
  | "RUNNING"
  | "PENDING_APPROVAL"
  | "FINALISED"
  | "EXPORTED"
  | "FAILED"
  | "CANCELLED";

export type Classification =
  | "SHORTLISTED"
  | "EXCLUDED_RECENCY"
  | "EXCLUDED_FORK_ONLY"
  | "EXCLUDED_STACK"
  | "EXCLUDED_BOT"
  | "INSUFFICIENT_EVIDENCE";

export interface Criteria {
  languages: string[];
  keywords: string[];
  seed_repos: string[];
  seed_users: string[];
  window_days: number;
  min_merged_prs: number;
  max_candidates: number;
  location: string | null;
  search: boolean;
}

export interface Decision {
  login: string;
  verdict: string;
  text: string;
}

export interface Step {
  id: string;
  seq: number;
  phase: string;
  tool: string;
  status: "running" | "ok" | "failed" | "waiting";
  inputs: Record<string, unknown>;
  summary: string;
  decisions: Decision[];
  rationale: string | null;
  started_at: string;
  duration_ms: number | null;
  error: string | null;
}

export interface Evidence {
  id: string;
  kind: "pr" | "own_project" | "fork_activity" | "fork_repo";
  url: string;
  raw_url: string | null;
  title: string;
  repo: string;
  repo_stars: number;
  repo_is_fork: boolean;
  repo_language: string | null;
  merged_at: string | null;
  additions: number;
  deletions: number;
  qualifies: boolean;
  rule_checks: Record<string, boolean>;
  retrieved_at: string;
  source_id: string | null;
  verified: boolean | null;
  verified_at: string | null;
  observed: Record<string, unknown>;
  verify_error: string | null;
}

export interface ScorePart {
  points: number;
  max: number;
  note: string;
}

export interface Candidate {
  id: string;
  login: string;
  profile: {
    login: string;
    name?: string | null;
    bio?: string | null;
    location?: string | null;
    company?: string | null;
    blog?: string | null;
    followers?: number;
    avatar_url?: string | null;
    html_url: string;
    account_type?: string;
    via?: string;
    location_match?: boolean | null;
  };
  contact_email: string | null;
  contact_note: string | null;
  classification: Classification;
  reason_code: string;
  reason_text: string;
  score: number;
  score_breakdown: Record<string, ScorePart>;
  summary: string | null;
  summary_citations: string[];
  verification_status: "unverified" | "verified" | "failed";
  blocked: boolean;
  review_decision: "pending" | "approved" | "rejected";
  review_note: string | null;
  fixture: boolean;
  evidence: Evidence[];
}

export interface RunStats {
  developers_checked?: number;
  prs_examined?: number;
  api_requests?: number;
  shortlisted?: number;
  excluded?: number;
  needs_review?: number;
  insufficient?: number;
  elapsed_s?: number;
}

export interface RunSummary {
  id: string;
  created_at: string;
  mode: Mode;
  query: string;
  criteria: Criteria;
  plan_notes: { planner?: string; rationale?: string };
  status: RunStatus;
  stats: RunStats;
  error: string | null;
  label: string | null;
  started_at: string | null;
  completed_at: string | null;
  finalised_at: string | null;
  approver: string | null;
  approval_note: string | null;
  exported_at: string | null;
  share_token: string | null;
}

export interface RunDetail extends RunSummary {
  steps: Step[];
  candidates: Candidate[];
}

export interface Meta {
  live_available: boolean;
  llm_enabled: boolean;
  llm_provider: string;
  llm_model: string | null;
  commit: string;
}

export interface AuditEntry {
  id: string;
  ts: string;
  run_id: string | null;
  actor: string;
  action: string;
  details: Record<string, unknown>;
}

export interface TestCaseDef {
  id: string;
  label: string;
  scenario: string;
  expected: string;
  fixture_login: string;
}

export interface TestResult {
  id: string;
  ts: string;
  batch_id: string;
  tc_id: string;
  label: string;
  mode: Mode;
  input: { scenario?: string; login?: string; criteria?: Criteria };
  expected: string;
  actual: string;
  passed: boolean | null;
  explanation: string;
  evidence: {
    run_id?: string;
    candidate?: {
      login: string;
      classification: string;
      reason: string;
      contact_email: string | null;
      score: number;
      verification: string;
      profile_url?: string;
      fixture: boolean;
    } | null;
    items?: {
      url: string;
      title: string;
      repo: string;
      kind: string;
      merged_at: string | null;
      repo_is_fork: boolean;
      qualifies: boolean;
      rule_checks: Record<string, boolean>;
      verified: boolean | null;
      verify_error: string | null;
    }[];
    trace?: { phase: string; tool: string; summary: string }[];
  };
  commit_sha: string;
  run_id: string | null;
}

export interface Proposal {
  destination: string;
  status: RunStatus;
  approve: string[];
  reject: string[];
  pending: string[];
  blocked: string[];
}
