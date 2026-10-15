"""Shared fixtures: synthetic corpora/archives in tmp dirs, isolated settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from masld_platform.config import Settings
from masld_platform.io_jsonl import sha16, write_jsonl


def prompt_record(task: str, sample: str, answer: str, prompt: str | None = None) -> dict[str, Any]:
    return {
        "task": task,
        "split": "test",
        "sample": sample,
        "source": "TEST",
        "prompt": prompt
        or (
            f"Liver biopsy profile.\nPatient: male; no type-2 diabetes.\n"
            f"Gene expression: G1=1.20, G2=-0.50, G3=0.00.\nAnswer:"
        ),
        "answer": answer,
    }


def eval_record(
    task: str, sample: str, answer: str, raw: str | None, error: str | None = None
) -> dict[str, Any]:
    return {
        "task": task,
        "sample": sample,
        "answer": answer,
        "raw": raw,
        "error": error,
        "model_version": "test-model",
        "parsed": None,  # filled by scoring from raw
    }


@pytest.fixture()
def repo(tmp_path: Path) -> dict[str, Any]:
    """A fake research root with prompts/, results/frontier_runs/ and a manifest."""
    prompts = tmp_path / "prompts"
    archives = tmp_path / "results" / "frontier_runs"
    prompts.mkdir(parents=True)
    archives.mkdir(parents=True)
    return {"root": tmp_path, "prompts": prompts, "archives": archives}


def make_settings(repo: dict[str, Any], tmp_path: Path) -> Settings:
    """Settings fully isolated from the real repo and environment files."""
    return Settings(
        _env_file=None,
        root=repo["root"],
        data_dir=tmp_path / "data",
        db_url=f"sqlite:///{tmp_path / 'data' / 'test.db'}",
        seed=20260929,
    )


@pytest.fixture()
def settings(repo: dict[str, Any], tmp_path: Path) -> Settings:
    return make_settings(repo, tmp_path)


def write_corpus(
    prompts_dir: Path,
    name: str,
    records: list[dict[str, Any]],
    *,
    with_manifest: bool = False,
) -> str:
    """Write a corpus file (+ MANIFEST.json entry when requested)."""
    path = prompts_dir / name
    write_jsonl(
        path,
        records,
        meta={"n_records": len(records), "seed": 20260929, "built": "2026-10-14", "builder": "test"},
    )
    if with_manifest:
        import json

        manifest_path = prompts_dir / "MANIFEST.json"
        manifest = {"version": "test-1", "created": "2026-10-14", "seed": 20260929,
                    "recipe": "", "rules": [], "counts": {}, "files": {}}
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
        manifest["counts"][name] = len(records)
        manifest["files"][name] = sha16(path)
        manifest_path.write_text(json.dumps(manifest, indent=1))
    return str(path)


def write_archive(archives_dir: Path, stem: str, records: list[dict[str, Any]]) -> Path:
    path = archives_dir / f"{stem}.jsonl.gz"
    write_jsonl(path, records)
    return path
