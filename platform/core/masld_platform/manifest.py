"""Prompt-corpus manifest model and integrity verification.

The frozen corpora are the program's reviewer-defense anchor: the platform
must be able to prove that the files on disk still match the counts and
checksums recorded at freeze time (manifest convention: counts exclude the
``__meta__`` header; checksums are sha16 of the gzip bytes).
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from masld_platform.io_jsonl import load_jsonl, sha16
from masld_platform.schemas import VerificationItem, VerificationReport


class Manifest(BaseModel):
    """Typed view of ``prompts/MANIFEST.json`` (unknown keys preserved)."""

    model_config = ConfigDict(extra="allow")

    version: str
    created: str
    seed: int
    recipe: str = ""
    rules: list[str] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
    files: dict[str, str] = Field(default_factory=dict)


def load_manifest(path: str | Path) -> Manifest:
    with open(path, encoding="utf-8") as f:
        return Manifest.model_validate(json.load(f))


def verify_manifest(
    manifest_path: str | Path,
    prompts_dir: str | Path,
    *,
    verify_sha: bool = True,
) -> VerificationReport:
    """Verify counts (and sha16 checksums) of every manifest-registered corpus.

    Files on disk that the manifest does not list are reported as ``extras``
    (informational — e.g. the k-shot variant corpora added after freeze-7).
    """
    manifest_path = Path(manifest_path)
    prompts_dir = Path(prompts_dir)
    m = load_manifest(manifest_path)

    items: list[VerificationItem] = []
    missing: list[str] = []
    ok = True
    for name in sorted(set(m.counts) | set(m.files)):
        path = prompts_dir / name
        if not path.exists():
            missing.append(name)
            ok = False
            items.append(VerificationItem(file=name, ok=False, detail="file missing"))
            continue
        expected_count = m.counts.get(name)
        expected_sha = m.files.get(name)
        actual_count: int | None = None
        actual_sha: str | None = None
        detail_parts: list[str] = []
        item_ok = True
        if expected_count is not None:
            records, _ = load_jsonl(path, skip_meta=True)
            actual_count = len(records)
            if actual_count != expected_count:
                item_ok = False
                detail_parts.append(f"count {actual_count} != {expected_count}")
        if verify_sha and expected_sha is not None:
            actual_sha = sha16(path)
            if actual_sha != expected_sha:
                item_ok = False
                detail_parts.append(f"sha16 {actual_sha} != {expected_sha}")
        ok = ok and item_ok
        items.append(
            VerificationItem(
                file=name,
                ok=item_ok,
                expected_count=expected_count,
                actual_count=actual_count,
                expected_sha16=expected_sha,
                actual_sha16=actual_sha,
                detail="; ".join(detail_parts),
            )
        )

    known = set(m.counts) | set(m.files)
    extras = sorted(
        p.name for p in prompts_dir.glob("*.jsonl.gz") if p.name not in known
    )
    return VerificationReport(
        manifest_version=m.version,
        ok=ok and not missing,
        items=items,
        extras=extras,
        missing=missing,
    )
