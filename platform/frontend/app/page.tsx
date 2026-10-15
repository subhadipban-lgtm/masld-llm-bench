"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { api, LeaderboardRow } from "@/lib/api";
import { CiBar, ErrorNote, Panel } from "@/components/ui";

export default function LeaderboardPage() {
  const [rows, setRows] = useState<LeaderboardRow[] | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const body = await api.leaderboard();
      setRows(body.rows);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const byTask = useMemo(() => {
    const groups = new Map<string, LeaderboardRow[]>();
    for (const r of rows ?? []) {
      if (!groups.has(r.task)) groups.set(r.task, []);
      groups.get(r.task)!.push(r);
    }
    for (const list of groups.values()) {
      list.sort((a, b) =>
        a.metric === "mae" ? a.value - b.value : b.value - a.value,
      );
    }
    return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [rows]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Leaderboard</h1>
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            Scored evaluation archives · bootstrap 95% CI · unified parser
          </p>
        </div>
        <button
          onClick={() => void load()}
          disabled={loading}
          className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm disabled:opacity-50 dark:border-neutral-700"
        >
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>

      {error && <ErrorNote error={error} />}
      {rows === null && !error && <p className="text-sm text-neutral-500">Loading…</p>}

      {byTask.map(([task, taskRows]) => (
        <Panel key={task} title={`${task} · ${taskRows[0]?.metric ?? ""} (n=${taskRows[0]?.n ?? 0})`}>
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-neutral-500">
              <tr>
                <th className="pb-2">Model</th>
                <th className="pb-2">Value</th>
                <th className="pb-2">95% CI</th>
                <th className="pb-2">Validity</th>
                <th className="pb-2">rho</th>
              </tr>
            </thead>
            <tbody>
              {taskRows.map((r) => (
                <tr key={r.model} className="border-t border-neutral-100 dark:border-neutral-900">
                  <td className="py-1.5 pr-4 font-mono text-xs">{r.model}</td>
                  <td className="py-1.5 pr-4 font-mono tabular-nums">
                    {r.value >= 1e6 && r.metric === "mae" ? r.value.toExponential(2) : r.value.toFixed(3)}
                  </td>
                  <td className="py-1.5 pr-4">
                    <CiBar value={r.value} lo={r.ci_lo} hi={r.ci_hi} metric={r.metric} />
                  </td>
                  <td className="py-1.5 pr-4 font-mono tabular-nums">{(r.validity * 100).toFixed(0)}%</td>
                  <td className="py-1.5 font-mono tabular-nums">{r.rho === null ? "—" : r.rho.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      ))}
    </div>
  );
}
