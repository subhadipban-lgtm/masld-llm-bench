"""Liveness/readiness probes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from masld_api.deps import get_api_settings, get_db
from masld_platform.config import Settings

router = APIRouter(tags=["health"])


@router.get("/healthz", summary="Liveness")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/profile", summary="Active benchmark profile (domain vocabulary)")
def get_profile() -> dict[str, object]:
    from masld_platform.profile import get_active_profile

    return get_active_profile().summary()  # type: ignore[no-any-return]


@router.get("/readyz", summary="Readiness (DB + research root reachable)")
def readyz(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_api_settings),
) -> dict[str, object]:
    db.execute(text("SELECT 1"))
    if not settings.prompts_dir().exists():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"research root not found: {settings.root}",
        )
    return {"status": "ready", "root": str(settings.root)}
