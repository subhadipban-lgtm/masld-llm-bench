"""Metric tests: determinism, guards, degenerate cases."""

from __future__ import annotations

import pytest

from masld_platform.metrics import accuracy, bootstrap_ci, mae, per_item_scores, spearman, validity
from masld_platform.guardrails import GuardrailError


def test_accuracy_counts_none_as_wrong() -> None:
    assert accuracy(["yes", None, "no"], ["yes", "yes", "no"]) == pytest.approx(2 / 3)


def test_validity() -> None:
    assert validity(["a", None, "b", None]) == pytest.approx(0.5)


def test_mae_skips_unparseable() -> None:
    assert mae([1.0, None, 3.0], [2.0, 99.0, 5.0]) == pytest.approx(1.5)


def test_mae_requires_one_parseable() -> None:
    with pytest.raises(GuardrailError):
        mae([None, None], [1.0, 2.0])


def test_spearman_none_on_constant_predictions() -> None:
    assert spearman([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]) is None


def test_spearman_perfect() -> None:
    assert spearman([1.0, 2.0, 3.0], [10.0, 20.0, 30.0]) == pytest.approx(1.0)


def test_bootstrap_ci_deterministic_and_contains_mean() -> None:
    vals = [1.0, 0.0, 1.0, 1.0, 0.0, 1.0]
    a = bootstrap_ci(vals, n_boot=500, seed=7)
    b = bootstrap_ci(vals, n_boot=500, seed=7)
    assert a == b
    lo, hi = a
    assert lo <= 4 / 6 <= hi


def test_bootstrap_rejects_nonfinite() -> None:
    with pytest.raises(GuardrailError):
        bootstrap_ci([1.0, float("nan")])


def test_per_item_scores_accuracy_and_mae() -> None:
    assert per_item_scores(["yes", "no"], ["yes", "no"], metric="accuracy") == [1.0, 1.0]
    assert per_item_scores(["yes", None], ["no", "no"], metric="accuracy") == [0.0, 0.0]
    errs = per_item_scores([2.0, 5.0], [1.0, 4.0], metric="mae")
    assert errs == [1.0, 1.0]
