"""ORM models.

Run rows are the durable state machine; prompt corpora and archives remain
files on disk (immutable by protocol) and are referenced by path. The audit
log is append-only and hash-chained so tampering is detectable.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Corpus(Base):
    """A frozen prompt corpus registered with the platform."""

    __tablename__ = "corpora"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    path: Mapped[str] = mapped_column(Text)
    manifest_version: Mapped[str] = mapped_column(String(50), default="")
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    sha16: Mapped[str] = mapped_column(String(16), default="")
    verified_ok: Mapped[bool] = mapped_column(default=False)
    verified_at: Mapped[datetime | None] = mapped_column(default=None)


class Run(Base):
    """One orchestrated execution (frontier/local/score/paired/verify/...)."""

    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    type: Mapped[str] = mapped_column(String(32))
    state: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(default=None)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)
    error: Mapped[str | None] = mapped_column(Text, default=None)
    log_path: Mapped[str | None] = mapped_column(Text, default=None)
    result_path: Mapped[str | None] = mapped_column(Text, default=None)
    attempts: Mapped[int] = mapped_column(Integer, default=0)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "state": self.state,
            "params": self.params,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "error": self.error,
            "log_path": self.log_path,
            "result_path": self.result_path,
            "attempts": self.attempts,
        }


class EvalArchive(Base):
    """An evaluation archive file produced or ingested by a run."""

    __tablename__ = "eval_archives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("runs.id"), default=None)
    path: Mapped[str] = mapped_column(Text, unique=True)
    model: Mapped[str] = mapped_column(String(200))
    dataset_tag: Mapped[str] = mapped_column(String(100), default="")
    n_records: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class LeaderboardSnapshot(Base):
    """Immutable snapshot of scored rows (JSON list of LeaderboardRow dicts)."""

    __tablename__ = "leaderboard_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("runs.id"), default=None)
    n_rows: Mapped[int] = mapped_column(Integer, default=0)
    rows: Mapped[list] = mapped_column(JSON, default=list)


class AuditEvent(Base):
    """Append-only, hash-chained audit record."""

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    actor: Mapped[str] = mapped_column(String(100), default="system")
    event: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64), default="")
    hash: Mapped[str] = mapped_column(String(64))
