"""Corpus browsing and manifest integrity endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from masld_api.deps import get_api_settings, get_db
from masld_platform.config import Settings
from masld_platform.io_jsonl import load_jsonl, sha16
from masld_platform.manifest import load_manifest, verify_manifest
from masld_persistence.audit import append_audit
from masld_persistence.repo import CorpusRepo

router = APIRouter(prefix="/corpora", tags=["corpora"])


@router.get("", summary="List corpora (manifest + disk state)")
def list_corpora(
    settings: Settings = Depends(get_api_settings),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    prompts_dir = settings.prompts_dir()
    manifest_path = prompts_dir / "MANIFEST.json"
    files: list[dict[str, object]] = []
    version = ""
    if manifest_path.exists():
        m = load_manifest(manifest_path)
        version = m.version
        for name in sorted(set(m.counts) | set(m.files)):
            p = prompts_dir / name
            files.append(
                {
                    "name": name,
                    "exists": p.exists(),
                    "manifest_count": m.counts.get(name),
                    "manifest_sha16": m.files.get(name),
                }
            )
    for p in sorted(prompts_dir.glob("*.jsonl.gz")):
        if not any(f["name"] == p.name for f in files):
            files.append({"name": p.name, "exists": True, "manifest_count": None, "manifest_sha16": None})
    return {"manifest_version": version, "prompts_dir": str(prompts_dir), "corpora": files}


@router.get("/{name}/verify", summary="Verify one corpus against the manifest")
def verify_corpus(
    name: str,
    settings: Settings = Depends(get_api_settings),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    prompts_dir = settings.prompts_dir()
    path = prompts_dir / name
    if not path.exists():
        raise HTTPException(404, f"corpus not found: {name}")
    manifest_path = prompts_dir / "MANIFEST.json"
    expected_count = None
    expected_sha = None
    version = ""
    if manifest_path.exists():
        m = load_manifest(manifest_path)
        version = m.version
        expected_count = m.counts.get(name)
        expected_sha = m.files.get(name)

    records, _ = load_jsonl(path, skip_meta=True)
    actual_sha = sha16(path)
    count_ok = expected_count is None or len(records) == expected_count
    sha_ok = expected_sha is None or actual_sha == expected_sha
    ok = bool(count_ok and sha_ok)

    repo = CorpusRepo(db)
    repo.upsert(
        name=name,
        path=str(path),
        manifest_version=version,
        record_count=len(records),
        sha16=actual_sha,
        verified_ok=ok,
    )
    append_audit(db, event="corpus.verified", payload={"name": name, "ok": ok})
    return {
        "name": name,
        "ok": ok,
        "manifest_version": version,
        "count": {"expected": expected_count, "actual": len(records), "ok": count_ok},
        "sha16": {"expected": expected_sha, "actual": actual_sha, "ok": sha_ok},
    }


@router.post("/verify-all", summary="Verify every manifest corpus")
def verify_all(
    settings: Settings = Depends(get_api_settings),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    prompts_dir: Path = settings.prompts_dir()
    manifest_path = prompts_dir / "MANIFEST.json"
    if not manifest_path.exists():
        raise HTTPException(404, "MANIFEST.json not found")
    report = verify_manifest(manifest_path, prompts_dir)
    append_audit(
        db, event="corpus.verify_all", payload={"ok": report.ok, "version": report.manifest_version}
    )
    return report.model_dump()
