"""Paired statistics: McNemar exact and Wilcoxon signed-rank.

Makes the C2 headline comparison rigorous: the candidate model is re-run on
the reference model's exact items (paired archive), then discordant pairs are
tested instead of comparing two independent proportions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from masld_platform.answers import gold_value, parse_answer
from masld_platform.io_jsonl import archive_model_name, read_jsonl_resilient
from masld_platform.metrics import accuracy, mae, per_item_scores
from masld_platform.schemas import PairedCell, PairedResult, TaskType
from masld_platform.tasks import resolve_task_type

def load_indexed(path: str | Path) -> dict[tuple[str, str], dict[str, Any]]:
    """Load an archive indexed by ``(task, sample)``; last record wins."""
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for r in read_jsonl_resilient(path):
        if r.get("task") and r.get("sample"):
            out[(r["task"], r["sample"])] = r
    return out


def paired_compare(
    candidate_path: str | Path,
    reference_path: str | Path,
    *,
    tasks: list[str] | None = None,
) -> list[PairedResult]:
    """Compare two archives on their overlapping (task, sample) items.

    Only items present in BOTH archives with parseable golds are used. Raises
    ``ValueError`` when the overlap is too small to test (< 1 usable task).
    """
    cand = load_indexed(candidate_path)
    ref = load_indexed(reference_path)
    cand_name, _ = archive_model_name(candidate_path)
    ref_name, _ = archive_model_name(reference_path)

    keys = sorted(set(cand) & set(ref))
    if not keys:
        raise ValueError(
            f"no overlapping items between {Path(candidate_path).name} and {Path(reference_path).name}"
        )

    by_task: dict[str, list[tuple[str, str]]] = {}
    for k in keys:
        by_task.setdefault(k[0], []).append(k)

    results: list[PairedResult] = []
    for task in sorted(by_task):
        if tasks and task not in tasks:
            continue
        task_keys = by_task[task]
        try:
            at = resolve_task_type(task, [])
        except ValueError:
            continue
        # Keep only items with a valid gold in the candidate archive
        # (pre-freeze-6 archives carry documented fake Gubra F5-F9 labels).
        kept: list[tuple[str, str]] = []
        golds: list[str | float] = []
        for k in task_keys:
            answer = cand[k].get("answer")
            if answer is None:
                continue
            try:
                golds.append(gold_value(answer, at))
            except ValueError:
                continue
            kept.append(k)
        if not kept:
            continue
        cand_preds = [parse_answer(cand[k].get("raw"), at) for k in kept]
        ref_preds = [parse_answer(ref[k].get("raw"), at) for k in kept]

        if at.kind is TaskType.NUMBER:
            metric = "mae"
            cand_value = mae(cand_preds, golds)
            ref_value = mae(ref_preds, golds)
            c_scores = per_item_scores(cand_preds, golds, metric="mae")
            r_scores = per_item_scores(ref_preds, golds, metric="mae")
            # For MAE, "correctness" cells are defined by strictly smaller error.
            both = sum(1 for c, r in zip(c_scores, r_scores) if c == r)
            c_only = sum(1 for c, r in zip(c_scores, r_scores) if c < r)
            r_only = sum(1 for c, r in zip(c_scores, r_scores) if c > r)
            deltas: list[float] = []
            for cp, rp, g in zip(cand_preds, ref_preds, golds):
                if cp is not None and rp is not None:
                    deltas.append(abs(rp - g) - abs(cp - g))  # >0 => candidate better
            wilcoxon_p = _wilcoxon(deltas)
            mcnemar_p = _mcnemar_exact(c_only, r_only)
        else:
            metric = "accuracy"
            cand_value = accuracy(cand_preds, golds)
            ref_value = accuracy(ref_preds, golds)
            c_correct = [p is not None and p == g for p, g in zip(cand_preds, golds)]
            r_correct = [p is not None and p == g for p, g in zip(ref_preds, golds)]
            both = sum(1 for c, r in zip(c_correct, r_correct) if c and r)
            c_only = sum(1 for c, r in zip(c_correct, r_correct) if c and not r)
            r_only = sum(1 for c, r in zip(c_correct, r_correct) if r and not c)
            mcnemar_p = _mcnemar_exact(c_only, r_only)
            wilcoxon_p = _wilcoxon(
                [
                    float(c) - float(r)
                    for c, r in zip(c_correct, r_correct)
                    if c is not r
                ]
                or []
            )

        results.append(
            PairedResult(
                candidate=cand_name,
                reference=ref_name,
                task=task,
                metric=metric,
                cand_value=round(cand_value, 6),
                ref_value=round(ref_value, 6),
                cell=PairedCell(
                    n=len(kept),
                    both_correct=both,
                    cand_only=c_only,
                    ref_only=r_only,
                    neither=len(kept) - both - c_only - r_only,
                ),
                mcnemar_p=mcnemar_p,
                wilcoxon_p=wilcoxon_p,
            )
        )
    if not results:
        raise ValueError("paired comparison produced no usable tasks")
    return results


def _mcnemar_exact(b: int, c: int) -> float | None:
    """Exact McNemar two-sided p (binomial test on discordant pairs)."""
    n = b + c
    if n == 0:
        return None
    from scipy.stats import binomtest  # lazy: heavy import

    return float(binomtest(b, n, 0.5).pvalue)


def _wilcoxon(deltas: list[float]) -> float | None:
    """Wilcoxon signed-rank p over deltas; ``None`` when undefined."""
    nz = [d for d in deltas if d != 0]
    if len(nz) < 3:
        return None
    from scipy.stats import wilcoxon  # lazy: heavy import

    try:
        return float(wilcoxon(nz).pvalue)
    except ValueError:  # pragma: no cover - degenerate input guard
        return None
