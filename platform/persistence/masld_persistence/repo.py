"""Repositories: thin, typed data-access helpers over the ORM models."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from masld_persistence.models import Corpus, EvalArchive, LeaderboardSnapshot, Run


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


class RunRepo:
    """CRUD + state transitions for :class:`Run` rows."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, *, type_: str, params: dict[str, Any], log_path: str | None = None) -> Run:
        run = Run(id=new_run_id(), type=type_, params=params, state="pending", log_path=log_path)
        self.session.add(run)
        self.session.commit()
        return run

    def get(self, run_id: str) -> Run | None:
        return self.session.get(Run, run_id)

    def list(self, *, state: str | None = None, limit: int = 100) -> list[Run]:
        q = select(Run).order_by(Run.created_at.desc()).limit(limit)
        if state:
            q = q.where(Run.state == state)
        return list(self.session.scalars(q))

    def mark(
        self,
        run_id: str,
        state: str,
        *,
        error: str | None = None,
        result_path: str | None = None,
        log_path: str | None = None,
    ) -> Run | None:
        run = self.get(run_id)
        if run is None:
            return None
        if run.state in ("succeeded", "failed", "cancelled"):
            raise ValueError(f"run {run_id} is terminal ({run.state})")
        run.state = state
        if error is not None:
            run.error = error[:4000]
        if result_path is not None:
            run.result_path = result_path
        if log_path is not None:
            run.log_path = log_path
        from masld_persistence.models import utcnow

        if state == "running":
            run.started_at = utcnow()
            run.attempts += 1
        if state in ("succeeded", "failed", "cancelled"):
            run.finished_at = utcnow()
        self.session.commit()
        return run


class ArchiveRepo:
    """Registry of evaluation archives."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def register(
        self, *, path: str, model: str, dataset_tag: str = "", n_records: int = 0, run_id: str | None = None
    ) -> EvalArchive:
        existing = self.session.execute(
            select(EvalArchive).where(EvalArchive.path == path)
        ).scalar_one_or_none()
        if existing:
            return existing
        row = EvalArchive(
            run_id=run_id, path=path, model=model, dataset_tag=dataset_tag, n_records=n_records
        )
        self.session.add(row)
        self.session.commit()
        return row

    def list(self) -> list[EvalArchive]:
        return list(self.session.scalars(select(EvalArchive).order_by(EvalArchive.created_at)))


class SnapshotRepo:
    """Leaderboard snapshot writes/reads."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def save(self, rows: list[dict[str, Any]], *, run_id: str | None = None) -> LeaderboardSnapshot:
        snap = LeaderboardSnapshot(run_id=run_id, n_rows=len(rows), rows=rows)
        self.session.add(snap)
        self.session.commit()
        return snap

    def latest(self) -> LeaderboardSnapshot | None:
        return self.session.execute(
            select(LeaderboardSnapshot).order_by(LeaderboardSnapshot.id.desc()).limit(1)
        ).scalar_one_or_none()


class CorpusRepo:
    """Registered corpora (files stay on disk; rows cache verification state)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert(
        self, *, name: str, path: str, manifest_version: str = "", record_count: int = 0, sha16: str = "", verified_ok: bool = False
    ) -> Corpus:
        row = self.session.execute(select(Corpus).where(Corpus.name == name)).scalar_one_or_none()
        from masld_persistence.models import utcnow

        if row is None:
            row = Corpus(name=name, path=path)
            self.session.add(row)
        row.path = path
        row.manifest_version = manifest_version
        row.record_count = record_count
        row.sha16 = sha16
        row.verified_ok = verified_ok
        row.verified_at = utcnow() if verified_ok else None
        self.session.commit()
        return row

    def list(self) -> list[Corpus]:
        return list(self.session.scalars(select(Corpus).order_by(Corpus.name)))
