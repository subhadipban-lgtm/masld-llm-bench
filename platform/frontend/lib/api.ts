/** Typed API client for the MASLD-Bench platform backend. */

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export interface LeaderboardRow {
  model: string;
  task: string;
  n: number;
  metric: string;
  value: number;
  ci_lo: number;
  ci_hi: number;
  validity: number;
  rho: number | null;
}

export interface Run {
  id: string;
  type: string;
  state: "pending" | "running" | "succeeded" | "failed" | "cancelled";
  params: Record<string, unknown>;
  created_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
  log_path: string | null;
  result_path: string | null;
  attempts: number;
}

export interface CorpusEntry {
  name: string;
  exists: boolean;
  manifest_count: number | null;
  manifest_sha16: string | null;
}

export interface VerifyReport {
  manifest_version: string;
  ok: boolean;
  items: Array<{
    file: string;
    ok: boolean;
    expected_count: number | null;
    actual_count: number | null;
    detail: string;
  }>;
  extras: string[];
  missing: string[];
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status}: ${detail.slice(0, 200)}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  leaderboard: () => json<{ n_rows: number; rows: LeaderboardRow[] }>("/leaderboard"),
  runs: () => json<{ runs: Run[] }>("/runs"),
  runLog: (id: string, tail = 60) =>
    json<{ run_id: string; state: string; log: string[] }>(`/runs/${id}/log?tail=${tail}`),
  corpora: () => json<{ manifest_version: string; corpora: CorpusEntry[] }>("/corpora"),
  verifyAll: () => json<VerifyReport>("/corpora/verify-all", { method: "POST" }),
};
