#!/usr/bin/env python3
"""C2 paired-significance sweep: candidate(s) vs every frontier reference.

For each candidate archive (default: every ``*_PAIRED*.jsonl.gz`` local run)
this calls the platform's existing ``masld_platform.paired.paired_compare``
(McNemar exact + Wilcoxon signed-rank per task) against every frontier
reference archive matching ``results/frontier_runs/*__MB-20xx.jsonl.gz``.
Local ``qwen3-*`` archives are excluded from the reference side (they are
candidates, not frontier baselines).

Verdicts (per task): WIN/LOSS when the candidate is better/worse AND the
task-appropriate p-value is < 0.05 (McNemar for accuracy, Wilcoxon for MAE;
MAE better = lower); otherwise TIE.

Output: results/c2_significance.csv (one row per candidate x reference x
task, with a leading ``candidate`` column) and results/c2_significance.md
(one markdown block per candidate).

Usage:
  platform/.venv/bin/python scripts/c2_significance.py
  platform/.venv/bin/python scripts/c2_significance.py \
      --candidate results/frontier_runs/qwen3-1.7b-masld__MB-20xx_PAIRED.jsonl.gz
"""
from __future__ import annotations

import argparse
from pathlib import Path

from masld_platform.paired import paired_compare

ROOT = Path(__file__).resolve().parents[1]
ARCHIVES = ROOT / "results" / "frontier_runs"
OUT_CSV = ROOT / "results" / "c2_significance.csv"
OUT_MD = ROOT / "results" / "c2_significance.md"

COLUMNS = [
    "candidate",
    "reference",
    "task",
    "metric",
    "n",
    "cand_value",
    "ref_value",
    "both_correct",
    "cand_only",
    "ref_only",
    "neither",
    "mcnemar_p",
    "wilcoxon_p",
    "verdict",
]

ALPHA = 0.05

#: The five canonical MB-20xx benchmark tasks, tried one at a time so a
#: reference that is untestable on one task (e.g. zero parseable numeric
#: predictions -> mae() raises) still contributes its other tasks.
CANONICAL_TASKS = ["MB-2001", "MB-2002", "MB-2003", "MB-2005", "MB-2006"]


def discover_references() -> list[Path]:
    """Frontier reference archives: MB-20xx, no candidates, no local runs."""
    refs: list[Path] = []
    for p in sorted(ARCHIVES.glob("*__MB-20xx.jsonl.gz")):
        if "PAIRED" in p.name:  # candidate archives
            continue
        if p.name.startswith("qwen3-"):  # local compact-model archives
            continue
        refs.append(p)
    return refs


def verdict(
    metric: str,
    cand_value: float,
    ref_value: float,
    mcnemar_p: float | None,
    wilcoxon_p: float | None,
) -> str:
    if cand_value == ref_value:
        return "TIE"
    if metric == "mae":
        better = cand_value < ref_value
        p = wilcoxon_p
    else:
        better = cand_value > ref_value
        p = mcnemar_p
    if p is not None and p < ALPHA:
        return "WIN" if better else "LOSS"
    return "TIE"


def _fmt_p(p: float | None) -> str:
    return "" if p is None else f"{p:.4g}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--candidate",
        action="append",
        type=Path,
        default=None,
        help="candidate archive path (repeatable); default: all *_PAIRED*.jsonl.gz",
    )
    ap.add_argument("--out-csv", type=Path, default=OUT_CSV)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    args = ap.parse_args()

    candidates = args.candidate or sorted(ARCHIVES.glob("*PAIRED*.jsonl.gz"))
    if not candidates:
        raise SystemExit(f"no candidate archives found under {ARCHIVES}")
    references = discover_references()
    print(f"candidates: {[c.name for c in candidates]}")
    print(f"references ({len(references)}): {[r.name for r in references]}")

    by_candidate: dict[str, list[dict]] = {}
    for cand in candidates:
        if not cand.exists():
            print(f"SKIP missing candidate: {cand}")
            continue
        rows: list[dict] = []
        for ref in references:
            try:
                results = paired_compare(cand, ref, tasks=CANONICAL_TASKS)
            except ValueError as exc:
                # a single untestable task (e.g. reference has zero parseable
                # numeric predictions) aborts the whole call -> retry per task
                results = []
                for task in CANONICAL_TASKS:
                    try:
                        results.extend(paired_compare(cand, ref, tasks=[task]))
                    except ValueError as exc2:
                        print(f"  SKIP {ref.name} / {task}: {exc2}")
            for res in results:
                rows.append(
                    {
                        "candidate": res.candidate,
                        "reference": res.reference,
                        "task": res.task,
                        "metric": res.metric,
                        "n": res.cell.n,
                        "cand_value": res.cand_value,
                        "ref_value": res.ref_value,
                        "both_correct": res.cell.both_correct,
                        "cand_only": res.cell.cand_only,
                        "ref_only": res.cell.ref_only,
                        "neither": res.cell.neither,
                        "mcnemar_p": res.mcnemar_p,
                        "wilcoxon_p": res.wilcoxon_p,
                        "verdict": verdict(
                            res.metric,
                            res.cand_value,
                            res.ref_value,
                            res.mcnemar_p,
                            res.wilcoxon_p,
                        ),
                    }
                )
        if not rows:
            print(f"SKIP candidate with no usable comparisons: {cand.name}")
            continue
        by_candidate[cand.name] = rows
        counts = {"WIN": 0, "LOSS": 0, "TIE": 0}
        for r in rows:
            counts[r["verdict"]] += 1
        print(f"{cand.name}: {len(rows)} rows -> WIN {counts['WIN']} / "
              f"LOSS {counts['LOSS']} / TIE {counts['TIE']}")

    if not by_candidate:
        raise SystemExit("no comparisons produced; nothing to write")

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    import csv

    with open(args.out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for rows in by_candidate.values():
            w.writerows(rows)
    print(f"wrote {args.out_csv}")

    md = ["# C2 paired significance (McNemar exact + Wilcoxon signed-rank)",
          "",
          f"Verdicts at p < {ALPHA}: accuracy -> McNemar, MAE -> Wilcoxon (better = lower).",
          ""]
    for cand_name, rows in by_candidate.items():
        counts = {"WIN": 0, "LOSS": 0, "TIE": 0}
        for r in rows:
            counts[r["verdict"]] += 1
        md += [
            f"## Candidate: {rows[0]['candidate']} (`{cand_name}`)",
            "",
            f"{len(rows)} comparisons — WIN {counts['WIN']} / LOSS {counts['LOSS']} / TIE {counts['TIE']}",
            "",
            "| reference | task | metric | n | cand | ref | both | cand_only | ref_only | neither | mcnemar_p | wilcoxon_p | verdict |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for r in rows:
            md.append(
                f"| {r['reference']} | {r['task']} | {r['metric']} | {r['n']} "
                f"| {r['cand_value']:.4g} | {r['ref_value']:.4g} "
                f"| {r['both_correct']} | {r['cand_only']} | {r['ref_only']} | {r['neither']} "
                f"| {_fmt_p(r['mcnemar_p'])} | {_fmt_p(r['wilcoxon_p'])} | {r['verdict']} |"
            )
        md.append("")
    args.out_md.write_text("\n".join(md))
    print(f"wrote {args.out_md}")


if __name__ == "__main__":
    main()
