"""Colab/Drive bridge endpoints (outbox/inbox visibility)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from masld_api.deps import get_api_settings
from masld_platform.colab_bridge import BridgeJob, JobStatus, JobType, enqueue_job, list_jobs
from masld_platform.config import Settings

router = APIRouter(prefix="/bridge", tags=["bridge"])


@router.get("/jobs", summary="Snapshot of bridge jobs across Drive folders")
def list_bridge_jobs(settings: Settings = Depends(get_api_settings)) -> dict[str, object]:
    if settings.drive_sync_dir is None:
        raise HTTPException(
            503, "DRIVE_SYNC_DIR not configured — set it in platform/.env to enable the bridge"
        )
    jobs = {
        section: [j.model_dump() for j in items]
        for section, items in list_jobs(settings.bridge_dir()).items()
    }
    return {"bridge_dir": str(settings.bridge_dir()), "jobs": jobs}


@router.post("/jobs", status_code=202, summary="Enqueue a job for the Colab worker")
def create_bridge_job(
    job_type: JobType,
    params: dict[str, object] | None = None,
    settings: Settings = Depends(get_api_settings),
) -> dict[str, object]:
    if settings.drive_sync_dir is None:
        raise HTTPException(503, "DRIVE_SYNC_DIR not configured")
    job = BridgeJob(type=job_type, params=params or {})
    path = enqueue_job(settings.bridge_dir(), job)
    return {"job_id": job.job_id, "status": JobStatus.QUEUED.value, "path": str(path)}
