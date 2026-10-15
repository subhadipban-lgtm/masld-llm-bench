"""Colab Pro / Google Drive bridge: file-based job protocol.

Google Colab exposes no headless API to start notebooks (verified during the
research program); the official unattended path is the Pro+ scheduler plus
background execution. This bridge therefore uses the Drive folder synced by
"Drive for Desktop" as the message bus — no API credentials required:

* ``outbox/{job_id}.json``  — supervisor writes job specs (status=queued).
* ``inbox/{job_id}.status.json`` — Colab worker claims/updates jobs.
* ``inbox/{job_id}__{model}__{tag}.jsonl.gz`` — result archives land here.
* ``done/`` — the supervisor moves finished job files here (immutable log).

The Colab-side worker notebook (``infra/colab/bridge_worker.ipynb``) polls
the outbox on the Pro+ schedule; ngrok tunneling is an optional alternative
for direct Colab->laptop HTTP and is NOT required for this protocol.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class JobType(str, Enum):
    """Kinds of GPU work dispatchable to Colab."""

    EVAL_LOCAL = "eval_local"  # evaluate an adapter on a corpus
    TRAIN = "train"  # LoRA training run (results land on Drive directly)


class JobStatus(str, Enum):
    QUEUED = "queued"
    CLAIMED = "claimed"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class BridgeJob(BaseModel):
    """One job exchanged with the Colab worker through Drive."""

    job_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    type: JobType
    status: JobStatus = JobStatus.QUEUED
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    updated_at: str = ""
    requested_by: str = "platform"
    params: dict[str, Any] = Field(default_factory=dict)


def _subdir(root: Path, name: str) -> Path:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def enqueue_job(bridge_root: Path, job: BridgeJob) -> Path:
    """Write a job spec to the outbox; returns its path."""
    outbox = _subdir(bridge_root, "outbox")
    path = outbox / f"{job.job_id}.json"
    if path.exists():
        raise FileExistsError(f"job {job.job_id} already enqueued")
    path.write_text(job.model_dump_json(indent=2), encoding="utf-8")
    return path


def list_jobs(bridge_root: Path) -> dict[str, list[BridgeJob]]:
    """Snapshot of jobs across outbox / inbox / done."""
    out: dict[str, list[BridgeJob]] = {"outbox": [], "inbox": [], "done": []}
    for section in out:
        d = bridge_root / section
        if not d.exists():
            continue
        for p in sorted(d.glob("*.json")):
            if p.name.endswith(".status.json"):
                continue
            try:
                out[section].append(BridgeJob.model_validate(json.loads(p.read_text())))
            except Exception:  # noqa: BLE001 - foreign files are skipped, not fatal
                continue
    return out


def read_status(bridge_root: Path, job_id: str) -> BridgeJob | None:
    """Read the worker-side status file for a job, if any."""
    p = bridge_root / "inbox" / f"{job_id}.status.json"
    if not p.exists():
        return None
    return BridgeJob.model_validate(json.loads(p.read_text(encoding="utf-8")))


def ingest_results(
    bridge_root: Path,
    *,
    into_archive_dir: Path,
    max_age_seconds: float = 0.0,
) -> list[Path]:
    """Move finished result archives from the Drive inbox into the platform.

    A job is ingestable when its status file says DONE and its archive is
    present. Jobs are then moved to ``done/`` (immutable history). Returns
    the list of ingested archive paths.
    """
    inbox = _subdir(bridge_root, "inbox")
    done_dir = _subdir(bridge_root, "done")
    into_archive_dir.mkdir(parents=True, exist_ok=True)
    ingested: list[Path] = []
    for status_path in sorted(inbox.glob("*.status.json")):
        try:
            job = BridgeJob.model_validate(json.loads(status_path.read_text()))
        except Exception:  # noqa: BLE001
            continue
        if job.status is not JobStatus.DONE:
            continue
        if max_age_seconds and time.time() - status_path.stat().st_mtime < max_age_seconds:
            continue
        archives = sorted(inbox.glob(f"{job.job_id}__*.jsonl.gz"))
        if not archives:
            continue
        for archive in archives:
            dest = into_archive_dir / archive.name
            dest.write_bytes(archive.read_bytes())
            ingested.append(dest)
            (done_dir / archive.name).write_bytes(archive.read_bytes())
            archive.unlink()
        (done_dir / status_path.name).write_text(status_path.read_text(), encoding="utf-8")
        job_outbox = bridge_root / "outbox" / f"{job.job_id}.json"
        if job_outbox.exists():
            (done_dir / job_outbox.name).write_text(job_outbox.read_text(), encoding="utf-8")
            job_outbox.unlink()
        status_path.unlink()
    return ingested
