"""Run execution for the API: thread pool, per-run logs, cancellation.

Runs execute on a small worker pool inside the API process (adequate for the
laptop/docker deployment scope; swap for a queue without touching the core
engines). Every state transition is written to the DB and audited; progress
lines land in ``<data>/runs/{run_id}.log``.

Cancellation is cooperative: ``DELETE /runs/{id}`` drops a ``.cancel`` marker
file that the engines poll between items.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from masld_agents.tasks import RunOutcome, execute_spec
from masld_platform.config import Settings
from masld_platform.schemas import RunSpec, RunState
from masld_persistence.audit import append_audit
from masld_persistence.repo import RunRepo, SnapshotRepo


class RunExecutor:
    """Submits validated run specs to the worker pool and settles their rows."""

    def __init__(self, settings: Settings, session_factory: sessionmaker[Session], *, max_workers: int = 2) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="run")
        self._lock = threading.Lock()
        self._active: set[str] = set()

    # ------------------------------------------------------------- lifecycle
    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)

    # ------------------------------------------------------------- submission
    def submit(self, run_id: str, spec: RunSpec) -> None:
        with self._lock:
            self._active.add(run_id)
        self._pool.submit(self._worker, run_id, spec)

    def is_active(self, run_id: str) -> bool:
        with self._lock:
            return run_id in self._active

    # --------------------------------------------------------------- worker
    def _worker(self, run_id: str, spec: RunSpec) -> None:
        try:
            self._execute_and_settle(run_id, spec)
        except Exception as exc:  # noqa: BLE001 - never die silently
            # The settling path itself failed; record it on the run row.
            try:
                with self.session_factory() as session:
                    from masld_platform.schemas import RunState

                    RunRepo(session).mark(run_id, RunState.FAILED.value, error=f"executor: {exc}")
            except Exception:  # pragma: no cover - DB unavailable
                pass
        finally:
            with self._lock:
                self._active.discard(run_id)

    def _execute_and_settle(self, run_id: str, spec: RunSpec) -> RunOutcome | None:
        runs_dir = self.settings.resolved_data_dir() / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        log_path = runs_dir / f"{run_id}.log"
        cancel_path = runs_dir / f"{run_id}.cancel"

        def log(msg: str) -> None:
            stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{stamp}] {msg}\n")

        should_cancel: Callable[[], bool] = lambda: cancel_path.exists()

        with self.session_factory() as session:
            RunRepo(session).mark(run_id, RunState.RUNNING.value, log_path=str(log_path))
            append_audit(session, event="run.started", payload={"run_id": run_id, "type": spec.type.value})

        try:
            outcome = execute_spec(spec, settings=self.settings, log=log, should_cancel=should_cancel)
        except Exception as exc:  # noqa: BLE001 - run failure is state, not crash
            log(f"FAILED: {exc}")
            with self.session_factory() as session:
                RunRepo(session).mark(run_id, RunState.FAILED.value, error=str(exc))
                append_audit(
                    session, event="run.failed", payload={"run_id": run_id, "error": str(exc)[:500]}
                )
            return None

        cancelled = should_cancel()
        with self.session_factory() as session:
            repo = RunRepo(session)
            repo.mark(
                run_id,
                RunState.CANCELLED.value if cancelled else RunState.SUCCEEDED.value,
                result_path=outcome.artifacts[0] if outcome.artifacts else None,
                error="cancelled by user" if cancelled else None,
            )
            if outcome.rows and spec.type.value == "score":
                SnapshotRepo(session).save(
                    [r.model_dump() for r in outcome.rows], run_id=run_id
                )
            append_audit(
                session,
                event="run.cancelled" if cancelled else "run.succeeded",
                payload={"run_id": run_id, **_json_safe(outcome.summary)},
            )
        return outcome


def _json_safe(d: dict[str, Any]) -> dict[str, Any]:
    import json

    return json.loads(json.dumps(d, default=str))
