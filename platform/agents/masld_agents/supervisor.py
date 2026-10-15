"""Supervisory control loop: the portable, deterministic autopilot.

Replaces the research LaunchAgent with a cross-platform daemon:

1. **Bridge ingestion** — finished Colab job archives landing in the Drive
   inbox are imported and scored automatically.
2. **Stall detection** — running runs whose log has not advanced within the
   stall window are failed loudly (with audit + notification).
3. **Bounded retry** — failed runs below the retry cap are re-queued.

Every action is idempotent (driven by DB state) and audited.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from masld_agents.notifications import CompositeNotifier, LogNotifier, MacOSNotifier, Notifier
from masld_agents.tasks import RunOutcome, execute_spec
from masld_platform.colab_bridge import ingest_results, list_jobs
from masld_platform.config import Settings
from masld_platform.schemas import RunSpec, RunState, RunType
from masld_persistence.audit import append_audit
from masld_persistence.repo import ArchiveRepo, RunRepo

logger = logging.getLogger("masld.supervisor")

STALL_AFTER_MIN = 90.0
MAX_ATTEMPTS = 3


class Supervisor:
    """One instance owns the loop; ``tick()`` is safe to call from anywhere."""

    def __init__(
        self,
        settings: Settings,
        session_factory: sessionmaker[Session],
        *,
        notifier: Notifier | None = None,
        stall_after_min: float = STALL_AFTER_MIN,
        max_attempts: int = MAX_ATTEMPTS,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.notifier = notifier or CompositeNotifier(LogNotifier(), MacOSNotifier())
        self.stall_after_min = stall_after_min
        self.max_attempts = max_attempts

    # ------------------------------------------------------------------ loop
    def run_forever(self, *, interval_s: float = 60.0) -> None:
        logger.info("supervisor started (interval=%ss)", interval_s)
        while True:
            try:
                self.tick()
            except Exception as exc:  # noqa: BLE001 - the loop must survive
                logger.exception("tick failed: %s", exc)
            time.sleep(interval_s)

    def tick(self) -> dict[str, int]:
        """One deterministic pass; returns action counters."""
        counts = {"ingested": 0, "stalled": 0, "retried": 0}
        counts["ingested"] = self._ingest_bridge()
        counts["stalled"] += self._fail_stalled()
        counts["retried"] += self._retry_failed()
        return counts

    # ----------------------------------------------------------- bridge pass
    def _ingest_bridge(self) -> int:
        if self.settings.drive_sync_dir is None:
            return 0
        try:
            ingested = ingest_results(
                self.settings.bridge_dir(), into_archive_dir=self.settings.archives_dir()
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("bridge ingest failed: %s", exc)
            return 0
        if not ingested:
            return 0
        with self.session_factory() as session:
            repo = ArchiveRepo(session)
            for path in ingested:
                from masld_platform.io_jsonl import archive_model_name, read_jsonl_resilient

                model, tag = archive_model_name(path)
                n = len(read_jsonl_resilient(path))
                repo.register(path=str(path), model=model, dataset_tag=tag, n_records=n)
            append_audit(
                session, event="bridge.ingested", payload={"archives": [str(p) for p in ingested]}
            )
        self.notifier.send(
            "MASLD platform", f"{len(ingested)} Colab archive(s) ingested and registered"
        )
        # Score the new material automatically.
        with self.session_factory() as session:
            run = RunRepo(session).create(
                type_=RunType.SCORE.value,
                params={},
                log_path=str(self.settings.resolved_data_dir() / "runs" / "auto_score.log"),
            )
            append_audit(session, event="run.auto_score_created", payload={"run_id": run.id})
        self._execute_and_settle(RunSpec(type=RunType.SCORE), run.id)
        return len(ingested)

    # ------------------------------------------------------------ stall pass
    def _fail_stalled(self) -> int:
        now = datetime.now(timezone.utc)
        n = 0
        with self.session_factory() as session:
            repo = RunRepo(session)
            for run in repo.list(state=RunState.RUNNING.value, limit=50):
                log_path = Path(run.log_path) if run.log_path else None
                if log_path is None or not log_path.exists():
                    continue
                age_min = (now - _as_utc(_mtime(log_path))).total_seconds() / 60
                if age_min > self.stall_after_min:
                    repo.mark(run.id, RunState.FAILED.value, error=f"stalled {age_min:.0f} min without log progress")
                    append_audit(
                        session, event="run.stalled", payload={"run_id": run.id, "age_min": round(age_min)}
                    )
                    self.notifier.send("MASLD platform", f"run {run.id} stalled — marked failed")
                    n += 1
        return n

    # ------------------------------------------------------------ retry pass
    def _retry_failed(self) -> int:
        n = 0
        with self.session_factory() as session:
            repo = RunRepo(session)
            for run in repo.list(state=RunState.FAILED.value, limit=50):
                if run.attempts >= self.max_attempts:
                    continue
                repo.mark(run.id, RunState.PENDING.value)
                append_audit(session, event="run.retry", payload={"run_id": run.id, "attempt": run.attempts + 1})
                self._execute_and_settle(RunSpec(type=RunType(run.type), params=run.params), run.id)
                n += 1
        return n

    # ------------------------------------------------------------- execution
    def _execute_and_settle(self, spec: RunSpec, run_id: str) -> RunOutcome | None:
        """Execute a run inline (supervisor context), updating its row."""
        with self.session_factory() as session:
            RunRepo(session).mark(run_id, RunState.RUNNING.value)
            run = RunRepo(session).get(run_id)
            log_path = Path(run.log_path) if run and run.log_path else None
        if log_path is None:
            log_path = self.settings.resolved_data_dir() / "runs" / f"{run_id}.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)

        def log(msg: str) -> None:
            stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
            with open(log_path, "a", encoding="utf-8") as f:  # type: ignore[arg-type]
                f.write(f"[{stamp}] {msg}\n")

        try:
            outcome = execute_spec(spec, settings=self.settings, log=log)
        except Exception as exc:  # noqa: BLE001 - run failure is state, not crash
            log(f"FAILED: {exc}")
            with self.session_factory() as session:
                RunRepo(session).mark(run_id, RunState.FAILED.value, error=str(exc))
                append_audit(session, event="run.failed", payload={"run_id": run_id, "error": str(exc)[:500]})
            self.notifier.send("MASLD platform", f"run {run_id} failed: {str(exc)[:120]}")
            return None
        with self.session_factory() as session:
            RunRepo(session).mark(
                run_id,
                RunState.SUCCEEDED.value,
                result_path=outcome.artifacts[0] if outcome.artifacts else None,
            )
            append_audit(session, event="run.succeeded", payload={"run_id": run_id, **outcome.summary})
        return outcome


def _mtime(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _stall_cutoff(stall_after_min: float) -> datetime:  # kept for tests
    return datetime.now(timezone.utc) - timedelta(minutes=stall_after_min)
