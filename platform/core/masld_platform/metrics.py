"""Scoring metrics: accuracy, MAE, Spearman, validity, bootstrap CIs.

All functions are pure and seeded where randomness is involved, so scoring is
deterministic across processes and reruns.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from masld_platform.guardrails import GuardrailError, check_min_n, require_finite


def accuracy(preds: Sequence[str | float | None], golds: Sequence[str | float]) -> float:
    """Fraction of exact matches; ``None`` predictions count as wrong."""
    if len(preds) != len(golds):
        raise GuardrailError(f"preds/golds length mismatch: {len(preds)} vs {len(golds)}")
    if not preds:
        raise GuardrailError("accuracy: empty sequences")
    correct = sum(1 for p, g in zip(preds, golds) if p is not None and p == g)
    return correct / len(preds)


def validity(preds: Sequence[str | float | None]) -> float:
    """Fraction of non-``None`` (parseable) predictions."""
    if not preds:
        raise GuardrailError("validity: empty sequences")
    return sum(1 for p in preds if p is not None) / len(preds)


def mae(preds: Sequence[float | None], golds: Sequence[float]) -> float:
    """Mean absolute error over parseable predictions only."""
    pairs = [(p, g) for p, g in zip(preds, golds) if p is not None]
    check_min_n(len(pairs), 1, what="parseable regression predictions")
    return float(np.mean([abs(float(p) - float(g)) for p, g in pairs]))


def spearman(preds: Sequence[float | None], golds: Sequence[float]) -> float | None:
    """Spearman rho over parseable predictions; ``None`` when undefined.

    Undefined cases: no variance in either variable (constant predictions —
    the mean-prediction failure mode) or n < 2.
    """
    pairs = [(float(p), float(g)) for p, g in zip(preds, golds) if p is not None]
    if len(pairs) < 2:
        return None
    require_finite([v for pair in pairs for v in pair], what="spearman inputs")
    p = np.array([a for a, _ in pairs])
    g = np.array([b for _, b in pairs])
    if np.std(p) == 0.0 or np.std(g) == 0.0:
        return None
    from scipy.stats import spearmanr  # lazy: heavy import

    r = spearmanr(p, g).statistic
    return None if r is None or np.isnan(r) else float(r)


def bootstrap_ci(
    values: Sequence[float],
    *,
    n_boot: int = 10_000,
    seed: int = 20260929,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Percentile bootstrap CI of the mean; deterministic given the seed."""
    arr = np.asarray(require_finite(values, what="bootstrap inputs"), dtype=float)
    check_min_n(arr.size, 1, what="bootstrap sample")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, arr.size, size=(n_boot, arr.size))
    means = arr[idx].mean(axis=1)
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return float(lo), float(hi)


def per_item_scores(
    preds: Sequence[str | float | None], golds: Sequence[str | float], *, metric: str
) -> list[float]:
    """Per-item scores for paired tests: 1/0 correctness or signed abs-error.

    Unparseable predictions score 0 on accuracy tasks; on regression they are
    excluded (their error is undefined).
    """
    if metric == "accuracy":
        return [1.0 if p is not None and p == g else 0.0 for p, g in zip(preds, golds)]
    if metric == "mae":
        return [
            abs(float(p) - float(g))
            for p, g in zip(preds, golds)
            if p is not None
        ]
    raise GuardrailError(f"per_item_scores: unknown metric {metric!r}")
