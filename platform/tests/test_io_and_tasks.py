"""I/O round-trip, truncation recovery, and task-registry tests."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from masld_platform.io_jsonl import (
    append_jsonl,
    archive_model_name,
    load_jsonl,
    read_jsonl_resilient,
    sha16,
    write_jsonl,
)
from masld_platform.schemas import TaskType
from masld_platform.tasks import answer_type_for, resolve_task_type, sniff_answer_type
from tests.conftest import prompt_record


def test_roundtrip_with_meta(tmp_path: Path) -> None:
    path = tmp_path / "c.jsonl.gz"
    recs = [prompt_record("MB-2001", f"S{i}", "yes") for i in range(3)]
    n = write_jsonl(path, recs, meta={"n_records": 3, "seed": 1, "built": "x", "builder": "t"})
    assert n == 3
    loaded, meta = load_jsonl(path, skip_meta=True)
    assert loaded == recs
    assert meta is not None and meta.n_records == 3


def test_meta_stays_when_not_skipped(tmp_path: Path) -> None:
    path = tmp_path / "c.jsonl.gz"
    write_jsonl(path, [prompt_record("MB-2001", "S", "no")], meta={"n_records": 1, "seed": 1, "built": "x", "builder": "t"})
    loaded, _ = load_jsonl(path, skip_meta=False)
    # Research convention: header nested under "__meta__" as the first line.
    assert loaded[0].get("__meta__", {}).get("n_records") == 1


def test_append_resume_protocol(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl.gz"
    write_jsonl(path, [prompt_record("MB-2001", "S1", "yes")])
    append_jsonl(path, [prompt_record("MB-2001", "S2", "no")])
    loaded, _ = load_jsonl(path, skip_meta=True)
    assert [r["sample"] for r in loaded] == ["S1", "S2"]


def test_truncated_gzip_recovery(tmp_path: Path) -> None:
    """A writer killed mid-record must not lose the complete lines."""
    good = tmp_path / "good.jsonl.gz"
    recs = [
        prompt_record("MB-2001", f"S{i}", "yes", prompt=f"genes: G{i}={i}.5, G9=-1.0")
        for i in range(40)
    ]
    write_jsonl(good, recs)
    raw = good.read_bytes()
    truncated = tmp_path / "trunc.jsonl.gz"
    truncated.write_bytes(raw[: len(raw) // 2])  # cut inside the stream
    recovered = read_jsonl_resilient(truncated)
    assert 0 < len(recovered) <= 40
    assert all("task" in r for r in recovered)


def test_recovery_handles_appended_gzip_members(tmp_path: Path) -> None:
    """Append-mode archives concatenate gzip members; recovery reads them all."""
    path = tmp_path / "appended.jsonl.gz"
    write_jsonl(path, [prompt_record("MB-2001", f"S{i}", "yes") for i in range(10)])
    append_jsonl(path, [prompt_record("MB-2001", f"S{i}", "yes") for i in range(10, 20)])
    # Corrupt the tail so the normal reader fails and recovery kicks in.
    raw = path.read_bytes()
    path.write_bytes(raw[:-8])
    recovered = read_jsonl_resilient(path)
    assert 10 <= len(recovered) <= 20  # first member full, second partial


def test_archive_model_name_decoding() -> None:
    model, tag = archive_model_name("nvidia__nemotron-3-super-120b-a12b:free__MB-20xx.jsonl.gz")
    assert model == "nvidia"
    # NOTE: research convention splits on FIRST '__'; flattened provider ids
    # keep their remaining '__' inside the model name.
    model2, tag2 = archive_model_name("qwen3-0.6b-masld__MB-20xx.jsonl.gz")
    assert (model2, tag2) == ("qwen3-0.6b-masld", "MB-20xx")


def test_sha16_format(tmp_path: Path) -> None:
    p = tmp_path / "f.bin"
    p.write_bytes(b"hello")
    assert len(sha16(p)) == 16


def test_task_registry() -> None:
    assert answer_type_for("MB-2001").kind is TaskType.YES_NO
    assert answer_type_for("MB-2002").name == "f_stage"
    assert answer_type_for("MB-2003").kind is TaskType.LETTER
    assert answer_type_for("MB-2005").kind is TaskType.NUMBER
    assert answer_type_for("MB-4001").kind is TaskType.YES_NO
    assert answer_type_for("MB-11001").kind is TaskType.YES_NO
    # Suffix fallback for unknown-but-shaped ids.
    assert answer_type_for("MB-12301").kind is TaskType.YES_NO


def test_sniff_answer_type() -> None:
    assert sniff_answer_type("yes").kind is TaskType.YES_NO
    assert sniff_answer_type("A").kind is TaskType.LETTER
    assert sniff_answer_type("F3").name == "f_stage"  # custom token sniffing
    assert sniff_answer_type("2").kind is TaskType.NUMBER
    assert sniff_answer_type(None) is None


def test_resolve_task_type_sniffs_from_records() -> None:
    recs = [prompt_record("MB-9501", "S1", "no")]
    assert resolve_task_type("MB-9501", recs).kind is TaskType.YES_NO


def test_write_jsonl_is_atomic_no_partial(tmp_path: Path) -> None:
    path = tmp_path / "c.jsonl.gz"
    write_jsonl(path, [prompt_record("MB-2001", "S", "yes")] * 10)
    assert not (tmp_path / "c.jsonl.gz.tmp").exists()
    with gzip.open(path, "rt") as f:
        assert len(f.readlines()) == 10
