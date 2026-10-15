"""Leaderboard and paired-statistics endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from masld_api.deps import get_api_settings, get_db
from masld_platform.config import Settings
from masld_platform.guardrails import GuardrailError
from masld_platform.leaderboard import score_archives
from masld_platform.paired import paired_compare
from masld_persistence.repo import SnapshotRepo

router = APIRouter(tags=["leaderboard"])


@router.get("/leaderboard", summary="Leaderboard rows (latest snapshot or live scan)")
def get_leaderboard(
    refresh: bool = Query(False, description="Rescore all archives before responding"),
    settings: Settings = Depends(get_api_settings),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    rows: list[dict] | None = None
    snap = SnapshotRepo(db).latest()
    if snap is not None and not refresh:
        rows = snap.rows
    if rows is None:
        try:
            scored = score_archives(settings.archives_dir(), seed=settings.seed)
        except GuardrailError as exc:
            raise HTTPException(400, str(exc)) from exc
        rows = [r.model_dump() for r in scored]
        SnapshotRepo(db).save(rows)
    return {"n_rows": len(rows), "rows": rows}


@router.get("/leaderboard/paired", summary="Paired comparison (McNemar/Wilcoxon)")
def get_paired(
    candidate: str = Query(..., description="archive stem or filename"),
    reference: str = Query(..., description="archive stem or filename"),
    settings: Settings = Depends(get_api_settings),
) -> dict[str, object]:
    archive_dir = settings.archives_dir()
    cand = _resolve_archive(archive_dir, candidate)
    ref = _resolve_archive(archive_dir, reference)
    if cand is None:
        raise HTTPException(404, f"candidate archive not found: {candidate}")
    if ref is None:
        raise HTTPException(404, f"reference archive not found: {reference}")
    try:
        results = paired_compare(cand, ref)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"results": [r.model_dump() for r in results]}


def _resolve_archive(archive_dir: Path, name: str) -> Path | None:
    """Accept a bare stem, a ``.jsonl.gz`` name, or a full path inside the dir."""
    for candidate in (
        archive_dir / name,
        archive_dir / f"{name}.jsonl.gz",
    ):
        if candidate.exists():
            return candidate
    return None
