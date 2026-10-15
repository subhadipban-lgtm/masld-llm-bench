"""Leaderboard scoring + paired statistics tests on synthetic archives."""

from __future__ import annotations

from pathlib import Path

import pytest

from masld_platform.leaderboard import rows_to_csv, score_archive
from masld_platform.paired import paired_compare
from tests.conftest import eval_record, write_archive


def _binary_archive(archives: Path, stem: str, raws: list[str | None]) -> Path:
    golds = ["yes", "no"] * (len(raws) // 2)
    return write_archive(
        archives,
        stem,
        [eval_record("MB-2001", f"S{i}", g, r) for i, (g, r) in enumerate(zip(golds, raws))],
    )


def test_score_accuracy_archive(repo: dict[str, Path]) -> None:
    path = _binary_archive(repo["archives"], "model-a__MB-20xx", ["yes", "no", "yes", "no"])
    rows = score_archive(path, seed=1)
    assert len(rows) == 1
    row = rows[0]
    assert row.model == "model-a"
    assert row.task == "MB-2001"
    assert row.metric == "accuracy"
    assert row.value == pytest.approx(1.0)
    assert row.validity == pytest.approx(1.0)
    assert row.ci_lo <= row.value <= row.ci_hi


def test_score_counts_invalid_as_wrong(repo: dict[str, Path]) -> None:
    path = _binary_archive(
        repo["archives"], "model-b__MB-20xx", ["yes", None, "garbage text", "no"]
    )
    rows = score_archive(path, seed=1)
    row = rows[0]
    assert row.value == pytest.approx(0.5)  # 2 of 4 correct
    assert row.validity == pytest.approx(0.5)  # "garbage text" is unparseable too


def test_score_regression_archive(repo: dict[str, Path]) -> None:
    recs = [
        eval_record("MB-2005", f"S{i}", str(g), str(float(g)))
        for i, g in enumerate([0, 1, 2, 3, 4, 2])
    ]
    path = write_archive(repo["archives"], "model-c__MB-20xx", recs)
    rows = score_archive(path, seed=1)
    row = rows[0]
    assert row.metric == "mae"
    assert row.value == pytest.approx(0.0)
    assert row.rho == pytest.approx(1.0)


def test_csv_schema_uses_rho_column(repo: dict[str, Path], tmp_path: Path) -> None:
    path = _binary_archive(repo["archives"], "model-a__MB-20xx", ["yes", "no"])
    rows = score_archive(path, seed=1)
    csv_path = tmp_path / "lb.csv"
    rows_to_csv(rows, csv_path)
    header = csv_path.read_text().splitlines()[0]
    assert header == "model,task,n,metric,value,ci_lo,ci_hi,validity,rho"


def test_paired_mcnemar_on_known_discordance(repo: dict[str, Path]) -> None:
    golds = ["yes", "no"] * 6
    # Both models get 10/12 correct; 2 discordant pairs each way.
    cand_raws = ["yes", "no", "yes", "no", "yes", "no", "yes", "no", "yes", "no", "no", "yes"]
    ref_raws = ["yes", "no", "no", "no", "yes", "yes", "yes", "no", "yes", "no", "yes", "no"]
    cand = write_archive(
        repo["archives"],
        "cand__MB-20xx",
        [eval_record("MB-2001", f"S{i}", g, r) for i, (g, r) in enumerate(zip(golds, cand_raws))],
    )
    ref = write_archive(
        repo["archives"],
        "ref__MB-20xx",
        [eval_record("MB-2001", f"S{i}", g, r) for i, (g, r) in enumerate(zip(golds, ref_raws))],
    )
    results = paired_compare(cand, ref)
    assert len(results) == 1
    r = results[0]
    assert r.candidate == "cand" and r.reference == "ref"
    assert r.cell.both_correct == 8
    assert r.cell.cand_only == 2 and r.cell.ref_only == 2
    assert r.mcnemar_p == pytest.approx(1.0)  # symmetric discordance
    assert r.cand_value == pytest.approx(10 / 12)
    assert r.ref_value == pytest.approx(10 / 12)


def test_paired_requires_overlap(repo: dict[str, Path]) -> None:
    a = write_archive(
        repo["archives"], "a__MB-20xx", [eval_record("MB-2001", "S1", "yes", "yes")]
    )
    b = write_archive(
        repo["archives"], "b__MB-20xx", [eval_record("MB-2001", "OTHER", "yes", "yes")]
    )
    with pytest.raises(ValueError, match="no overlapping"):
        paired_compare(a, b)


def test_paired_mcnemar_significant(repo: dict[str, Path]) -> None:
    golds = ["yes"] * 10
    cand_raws = ["yes"] * 9 + ["no"]  # 9 correct
    ref_raws = ["no"] * 10  # 0 correct; all 9 achievable pairs discordant
    cand = write_archive(
        repo["archives"], "c2__MB-20xx",
        [eval_record("MB-2001", f"S{i}", g, r) for i, (g, r) in enumerate(zip(golds, cand_raws))],
    )
    ref = write_archive(
        repo["archives"], "r2__MB-20xx",
        [eval_record("MB-2001", f"S{i}", g, r) for i, (g, r) in enumerate(zip(golds, ref_raws))],
    )
    results = paired_compare(cand, ref)
    assert results[0].cell.cand_only == 9
    assert results[0].cell.ref_only == 0
    assert results[0].mcnemar_p < 0.01
