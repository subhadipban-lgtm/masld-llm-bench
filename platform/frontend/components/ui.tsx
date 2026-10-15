"use client";

/** Small shared UI primitives (badges, CI bar, tables). */

export function StateBadge({ state }: { state: string }) {
  const tone: Record<string, string> = {
    pending: "bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300",
    running: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300",
    succeeded: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
    failed: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
    cancelled: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  };
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${tone[state] ?? tone.pending}`}>
      {state}
    </span>
  );
}

export function CiBar({
  value,
  lo,
  hi,
  metric,
}: {
  value: number;
  lo: number;
  hi: number;
  metric: string;
}) {
  // MAE is inverted-better; normalise both onto [0, 1] "goodness" for the bar.
  const max = metric === "mae" ? 5 : 1;
  const clamp = (x: number) => Math.max(0, Math.min(1, x / max));
  const good = metric === "mae" ? 1 - clamp(value) : clamp(value);
  const goodLo = metric === "mae" ? 1 - clamp(hi) : clamp(lo);
  const goodHi = metric === "mae" ? 1 - clamp(lo) : clamp(hi);
  return (
    <div className="relative h-2 w-40 rounded bg-neutral-200 dark:bg-neutral-800">
      <div
        className="absolute top-0 h-2 rounded bg-emerald-500/40"
        style={{ left: `${goodLo * 100}%`, width: `${Math.max(0.5, (goodHi - goodLo) * 100)}%` }}
      />
      <div
        className="absolute top-0 h-2 w-1 rounded bg-emerald-600"
        style={{ left: `calc(${good * 100}% - 2px)` }}
      />
    </div>
  );
}

export function Panel({
  title,
  actions,
  children,
}: {
  title: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-neutral-200 dark:border-neutral-800">
      <div className="flex items-center justify-between border-b border-neutral-200 px-4 py-2 dark:border-neutral-800">
        <h2 className="text-sm font-semibold">{title}</h2>
        {actions}
      </div>
      <div className="overflow-x-auto p-4">{children}</div>
    </section>
  );
}

export function ErrorNote({ error }: { error: string }) {
  return (
    <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
      {error}
    </div>
  );
}
