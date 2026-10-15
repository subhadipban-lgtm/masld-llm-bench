"use client";

import { useCallback, useEffect, useState } from "react";
import { api, CorpusEntry, VerifyReport } from "@/lib/api";
import { ErrorNote, Panel } from "@/components/ui";

export default function CorporaPage() {
  const [manifestVersion, setManifestVersion] = useState("");
  const [corpora, setCorpora] = useState<CorpusEntry[] | null>(null);
  const [report, setReport] = useState<VerifyReport | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const body = await api.corpora();
      setCorpora(body.corpora);
      setManifestVersion(body.manifest_version);
      setError("");
    } catch (e) {
      setError(String(e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const verifyAll = async () => {
    setBusy(true);
    setError("");
    try {
      setReport(await api.verifyAll());
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Corpora</h1>
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            Frozen prompt corpora · manifest {manifestVersion || "—"}
          </p>
        </div>
        <button
          onClick={() => void verifyAll()}
          disabled={busy}
          className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm disabled:opacity-50 dark:border-neutral-700"
        >
          {busy ? "Verifying…" : "Verify all"}
        </button>
      </div>

      {error && <ErrorNote error={error} />}
      {corpora === null && !error && <p className="text-sm text-neutral-500">Loading…</p>}

      {corpora && (
        <Panel title={`${corpora.length} corpus files`}>
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-neutral-500">
              <tr>
                <th className="pb-2">File</th>
                <th className="pb-2">On disk</th>
                <th className="pb-2">Manifest count</th>
                <th className="pb-2">sha16</th>
              </tr>
            </thead>
            <tbody>
              {corpora.map((c) => (
                <tr key={c.name} className="border-t border-neutral-100 dark:border-neutral-900">
                  <td className="py-1.5 pr-4 font-mono text-xs">{c.name}</td>
                  <td className="py-1.5 pr-4">{c.exists ? "✓" : "✗"}</td>
                  <td className="py-1.5 pr-4 tabular-nums">{c.manifest_count ?? "—"}</td>
                  <td className="py-1.5 font-mono text-xs text-neutral-500">
                    {c.manifest_sha16 ?? "(not in manifest)"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      )}

      {report && (
        <Panel
          title={`Verification · ${report.manifest_version}`}
          actions={
            <span className={report.ok ? "text-sm text-emerald-600 dark:text-emerald-400" : "text-sm text-red-600 dark:text-red-400"}>
              {report.ok ? "OK" : "MISMATCH"}
            </span>
          }
        >
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-neutral-500">
              <tr>
                <th className="pb-2">File</th>
                <th className="pb-2">Status</th>
                <th className="pb-2">Expected</th>
                <th className="pb-2">Actual</th>
                <th className="pb-2">Detail</th>
              </tr>
            </thead>
            <tbody>
              {report.items.map((i) => (
                <tr key={i.file} className="border-t border-neutral-100 dark:border-neutral-900">
                  <td className="py-1.5 pr-4 font-mono text-xs">{i.file}</td>
                  <td className="py-1.5 pr-4">{i.ok ? "✓" : "✗"}</td>
                  <td className="py-1.5 pr-4 tabular-nums">{i.expected_count ?? "—"}</td>
                  <td className="py-1.5 pr-4 tabular-nums">{i.actual_count ?? "—"}</td>
                  <td className="py-1.5 font-mono text-xs text-neutral-500">{i.detail || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {report.extras.length > 0 && (
            <p className="mt-3 text-xs text-neutral-500">
              Extras on disk (not in manifest): {report.extras.join(", ")}
            </p>
          )}
          {report.missing.length > 0 && (
            <p className="mt-1 text-xs text-red-600 dark:text-red-400">
              Missing: {report.missing.join(", ")}
            </p>
          )}
        </Panel>
      )}
    </div>
  );
}
