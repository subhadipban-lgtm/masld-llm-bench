"""Archive scoring and leaderboard assembly.

Scores evaluation archives (the universal ``EvalRecord`` JSONL.gz interchange)
into :class:`LeaderboardRow` cells, one per (model, task), with bootstrap CIs,
validity, and Spearman rho for regression tasks. Replaces the research
scorer's answer-value sniffing with the central task registry (sniffing kept
only as a last-resort fallback), and writes the unified CSV schema with the
``rho`` column.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from masld_platform.answers import gold_value, parse_answer
from masld_platform.guardrails import check_min_n
from masld_platform.io_jsonl import archive_model_name, read_jsonl_resilient
from masld_platform.metrics import accuracy, bootstrap_ci, mae, per_item_scores, spearman, validity
from masld_platform.schemas import EvalRecord, LeaderboardRow, MetricName, TaskType
from masld_platform.tasks import resolve_task_type

CSV_COLUMNS = ["model", "task", "n", "metric", "value", "ci_lo", "ci_hi", "validity", "rho"]


def score_archive(
    path: str | Path,
    *,
    seed: int = 20260929,
    min_n: int = 1,
    progress_cb: Callable[[str], None] | None = None,
) -> list[LeaderboardRow]:
    """Score one evaluation archive into leaderboard rows.

    Records are grouped per task; the metric family follows the task's answer
    modality. Failed calls (``error`` set, ``raw`` null) stay in the record
    count and count against validity, exactly like the research scorer.
    """
    path = Path(path)
    model, _tag = archive_model_name(path)
    raw = read_jsonl_resilient(path)
    records = [r for r in raw if "task" in r and "sample" in r]
    check_min_n(len(records), min_n, what=f"archive records ({path.name})")

    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        by_task[r["task"]].append(r)

    rows: list[LeaderboardRow] = []
    for task in sorted(by_task):
        group = by_task[task]
        try:
            at = resolve_task_type(task, _coerce(group))
        except ValueError:
            if progress_cb:
                progress_cb(f"skipping unresolvable task {task} in {path.name}")
            continue

        # Records whose gold fails task validation are excluded and counted,
        # never silently scored: pre-freeze-6 archives still carry Gubra
        # F5-F9 labels that are documented fake (title sequence numbers).
        usable: list[dict[str, Any]] = []
        golds: list[str | float] = []
        n_dropped = 0
        for r in group:
            answer = r.get("answer")
            if answer is None:
                n_dropped += 1
                continue
            try:
                golds.append(gold_value(answer, at))
                usable.append(r)
            except ValueError:
                n_dropped += 1
        if n_dropped and progress_cb:
            progress_cb(f"{path.name}/{task}: dropped {n_dropped} invalid-gold records")
        if not usable:
            if progress_cb:
                progress_cb(f"{path.name}/{task}: no usable golds, skipped")
            continue
        preds = [parse_answer(r.get("raw"), at) for r in usable]
        group_len = len(usable)

        if at.kind is TaskType.NUMBER:
            pairs = [(p, g) for p, g in zip(preds, golds) if p is not None]
            value = mae(preds, golds) if pairs else float("nan")
            lo, hi = bootstrap_ci([abs(float(p) - g) for p, g in pairs], seed=seed) if pairs else (
                float("nan"),
                float("nan"),
            )
            rows.append(
                LeaderboardRow(
                    model=model,
                    task=task,
                    n=group_len,
                    metric=MetricName.MAE.value,
                    value=round(value, 6),
                    ci_lo=round(lo, 6),
                    ci_hi=round(hi, 6),
                    validity=round(validity(preds), 6),
                    rho=(round(r, 6) if (r := spearman(preds, golds)) is not None else None),
                )
            )
        else:
            value = accuracy(preds, golds)
            lo, hi = bootstrap_ci(per_item_scores(preds, golds, metric="accuracy"), seed=seed)
            rows.append(
                LeaderboardRow(
                    model=model,
                    task=task,
                    n=group_len,
                    metric=MetricName.ACCURACY.value,
                    value=round(value, 6),
                    ci_lo=round(lo, 6),
                    ci_hi=round(hi, 6),
                    validity=round(validity(preds), 6),
                )
            )
    return rows


def _coerce(group: list[dict[str, Any]]) -> list[EvalRecord]:
    """Best-effort EvalRecord coercion for task-type resolution."""
    out: list[EvalRecord] = []
    for r in group[:5]:
        try:
            out.append(EvalRecord.model_validate({k: v for k, v in r.items() if k in EvalRecord.model_fields}))
        except Exception:  # noqa: BLE001 - resolution is best-effort
            continue
    return out


def score_archives(
    archive_dir: str | Path,
    *,
    seed: int = 20260929,
    progress_cb: Callable[[str], None] | None = None,
) -> list[LeaderboardRow]:
    """Score every ``*.jsonl.gz`` archive in a directory."""
    archive_dir = Path(archive_dir)
    rows: list[LeaderboardRow] = []
    for path in sorted(archive_dir.glob("*.jsonl.gz")):
        try:
            model, _ = archive_model_name(path)
        except Exception as exc:  # noqa: BLE001 - skip malformed names
            if progress_cb:
                progress_cb(f"skipping {path.name}: {exc}")
            continue
        if progress_cb:
            progress_cb(f"scoring {path.name}")
        rows.extend(score_archive(path, seed=seed, min_n=1))
    return rows


def rows_to_csv(rows: list[LeaderboardRow], path: str | Path) -> int:
    """Write leaderboard rows in the unified CSV schema (``rho`` column)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(CSV_COLUMNS)
        for r in sorted(rows, key=lambda r: (r.task, r.model)):
            w.writerow([r.model, r.task, r.n, r.metric, r.value, r.ci_lo, r.ci_hi, r.validity, "" if r.rho is None else r.rho])
    return len(rows)
