"use client";

import { useCallback, useEffect, useState } from "react";
import { api, Run } from "@/lib/api";
import { ErrorNote, Panel, StateBadge } from "@/components/ui";

export default function RunsPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [log, setLog] = useState<string[]>([]);
  const [logBusy, setLogBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const body = await api.runs();
      setRuns(body.runs);
      setError("");
    } catch (e) {
      setError(String(e));
    }
  }, []);

  useEffect(() => {
    void load();
    const t = setInterval(() => void load(), 5000);
    return () => clearInterval(t);
  }, [load]);

  const toggleLog = async (id: string) => {
    if (expanded === id) {
      setExpanded(null);
      return;
    }
    setExpanded(id);
    setLogBusy(true);
    try {
      const body = await api.runLog(id);
      setLog(body.log);
    } catch (e) {
      setLog([`failed to load log: ${String(e)}`]);
    } finally {
      setLogBusy(false);
    }
  };

  const cancel = async (id: string) => {
    await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000"}/runs/${id}`, {
      method: "DELETE",
    }).catch(() => undefined);
    void load();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Runs</h1>
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          Orchestrated executions · auto-refresh every 5s
        </p>
      </div>
      {error && <ErrorNote error={error} />}
      <Panel title={`${runs.length} run${runs.length === 1 ? "" : "s"}`}>
        {runs.length === 0 ? (
          <p className="text-sm text-neutral-500">No runs yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-neutral-500">
              <tr>
                <th className="pb-2">ID</th>
                <th className="pb-2">Type</th>
                <th className="pb-2">State</th>
                <th className="pb-2">Created</th>
                <th className="pb-2">Attempts</th>
                <th className="pb-2" />
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id} className="border-t border-neutral-100 dark:border-neutral-900">
                  <td className="py-1.5 pr-4 font-mono text-xs">{r.id}</td>
                  <td className="py-1.5 pr-4">{r.type}</td>
                  <td className="py-1.5 pr-4">
                    <StateBadge state={r.state} />
                  </td>
                  <td className="py-1.5 pr-4 font-mono text-xs">
                    {r.created_at?.slice(0, 19).replace("T", " ") ?? "—"}
                  </td>
                  <td className="py-1.5 pr-4 tabular-nums">{r.attempts}</td>
                  <td className="py-1.5 text-right">
                    <button
                      onClick={() => void toggleLog(r.id)}
                      className="mr-2 rounded border border-neutral-300 px-2 py-0.5 text-xs dark:border-neutral-700"
                    >
                      log
                    </button>
                    {(r.state === "running" || r.state === "pending") && (
                      <button
                        onClick={() => void cancel(r.id)}
                        className="rounded border border-red-300 px-2 py-0.5 text-xs text-red-700 dark:border-red-900 dark:text-red-400"
                      >
                        cancel
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      {expanded && (
        <Panel title={`log · ${expanded}`} actions={
          <button
            onClick={() => void toggleLog(expanded)}
            className="text-xs text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-100"
          >
            close
          </button>
        }>
          {logBusy ? (
            <p className="text-sm text-neutral-500">Loading…</p>
          ) : (
            <pre className="max-h-96 overflow-auto rounded bg-neutral-50 p-3 font-mono text-xs leading-5 dark:bg-neutral-900">
              {log.length ? log.join("\n") : "(empty log)"}
            </pre>
          )}
        </Panel>
      )}
    </div>
  );
}
