"""Colab bridge protocol + audit hash-chain tests."""

from __future__ import annotations

import json
from pathlib import Path

from masld_platform.colab_bridge import BridgeJob, JobStatus, JobType, enqueue_job, ingest_results, list_jobs, read_status
from masld_platform.io_jsonl import write_jsonl
from masld_persistence.audit import append_audit, verify_audit_chain
from masld_persistence.database import init_db, make_engine, make_session_factory
from tests.conftest import eval_record


def test_bridge_job_lifecycle(tmp_path: Path) -> None:
    root = tmp_path / "bridge"
    job = BridgeJob(type=JobType.EVAL_LOCAL, params={"corpus": "MB-20xx_liver_test.jsonl.gz"})
    enqueue_job(root, job)

    jobs = list_jobs(root)
    assert [j.job_id for j in jobs["outbox"]] == [job.job_id]
    assert read_status(root, job.job_id) is None

    # Worker claims the job and finishes with an archive in the inbox.
    (root / "inbox").mkdir(parents=True, exist_ok=True)
    archive = root / "inbox" / f"{job.job_id}__qwen3-0.6b__MB-20xx.jsonl.gz"
    write_jsonl(archive, [eval_record("MB-2001", "S1", "yes", "yes")])
    status = job.model_copy(update={"status": JobStatus.DONE, "updated_at": "2026-10-14T00:00:00Z"})
    (root / "inbox" / f"{job.job_id}.status.json").write_text(status.model_dump_json())

    ingested = ingest_results(root, into_archive_dir=tmp_path / "archives")
    assert len(ingested) == 1
    assert (tmp_path / "archives" / archive.name).exists()
    # Job moved to done/ (immutable history), outbox cleaned.
    assert not (root / "outbox" / f"{job.job_id}.json").exists()
    assert (root / "done" / f"{job.job_id}.json").exists()
    assert not list_jobs(root)["outbox"]


def test_audit_chain_verifies_and_detects_tampering(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'a.db'}")
    init_db(engine)
    Session = make_session_factory(engine)
    with Session() as s:
        append_audit(s, event="run.created", payload={"run_id": "x1"})
        append_audit(s, event="run.started", payload={"run_id": "x1"})
        assert verify_audit_chain(s)

        # Tamper retroactively with the first event's payload.
        from sqlalchemy import select, update
        from masld_persistence.models import AuditEvent

        first = s.execute(select(AuditEvent).order_by(AuditEvent.id)).scalars().first()
        s.execute(update(AuditEvent).where(AuditEvent.id == first.id).values(payload={"run_id": "HACKED"}))
        s.commit()
        assert not verify_audit_chain(s)
