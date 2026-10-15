"""Run orchestration endpoints (submit, monitor, cancel)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from masld_api.deps import get_api_settings, get_db, get_executor
from masld_api.execution import RunExecutor
from masld_platform.config import Settings
from masld_platform.guardrails import GuardrailError, validate_run_spec
from masld_platform.schemas import RunSpec, RunType
from masld_persistence.audit import append_audit
from masld_persistence.audit import append_audit
from masld_persistence.repo import RunRepo

router = APIRouter(prefix="/runs", tags=["runs"])


class RunCreate(BaseModel):
    """Request body for POST /runs."""

    type: RunType
    params: dict[str, object] = Field(default_factory=dict)


@router.post("", status_code=status.HTTP_202_ACCEPTED, summary="Submit a run")
def create_run(
    body: RunCreate,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_api_settings),
    executor: RunExecutor = Depends(get_executor),
) -> dict[str, object]:
    spec = RunSpec(type=body.type, params=body.params)  # type: ignore[arg-type]
    try:
        validate_run_spec(spec)
    except GuardrailError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    runs_dir = settings.resolved_data_dir() / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run = RunRepo(db).create(
        type_=spec.type.value,
        params=spec.params,
        log_path=str(runs_dir / "pending.log"),
    )
    append_audit(
        db, event="run.created", payload={"run_id": run.id, "type": spec.type.value}
    )
    executor.submit(run.id, spec)
    return {"id": run.id, "state": run.state, "type": run.type}


@router.get("", summary="List runs")
def list_runs(
    state: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    runs = RunRepo(db).list(state=state, limit=min(limit, 200))
    return {"runs": [r.to_dict() for r in runs]}


@router.get("/{run_id}", summary="Run detail")
def get_run(run_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    run = RunRepo(db).get(run_id)
    if run is None:
        raise HTTPException(404, f"run {run_id} not found")
    return run.to_dict()


@router.get("/{run_id}/log", summary="Run log tail")
def get_run_log(
    run_id: str,
    tail: int = 100,
    settings: Settings = Depends(get_api_settings),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    run = RunRepo(db).get(run_id)
    if run is None:
        raise HTTPException(404, f"run {run_id} not found")
    log_path = Path(run.log_path or "")
    lines: list[str] = []
    if run.log_path and log_path.name != "pending.log" and log_path.exists():
        text = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        lines = text[-max(tail, 1) :]
    return {"run_id": run_id, "state": run.state, "log": lines}


@router.delete("/{run_id}", summary="Cancel a run")
def cancel_run(
    run_id: str,
    settings: Settings = Depends(get_api_settings),
    db: Session = Depends(get_db),
    executor: RunExecutor = Depends(get_executor),
) -> dict[str, object]:
    repo = RunRepo(db)
    run = repo.get(run_id)
    if run is None:
        raise HTTPException(404, f"run {run_id} not found")
    if run.state in ("succeeded", "failed", "cancelled"):
        raise HTTPException(409, f"run already {run.state}")
    if run.state == "running":
        cancel_marker = settings.resolved_data_dir() / "runs" / f"{run_id}.cancel"
        cancel_marker.write_text("cancel", encoding="utf-8")
        append_audit(db, event="run.cancel_requested", payload={"run_id": run_id})
        return {"id": run_id, "state": "running", "cancel_requested": True}
    # Still pending: never started — cancel outright.
    repo.mark(run_id, "cancelled", error="cancelled before start")
    append_audit(db, event="run.cancelled", payload={"run_id": run_id})
    return {"id": run_id, "state": "cancelled", "cancel_requested": False}
