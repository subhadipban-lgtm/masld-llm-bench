"""Persistence layer: SQLAlchemy 2.0 models, repositories, audit chain."""

from masld_persistence.audit import append_audit, verify_audit_chain
from masld_persistence.database import init_db, make_engine, make_session_factory
from masld_persistence.models import (
    AuditEvent,
    Base,
    Corpus,
    EvalArchive,
    LeaderboardSnapshot,
    Run,
)

__all__ = [
    "AuditEvent",
    "Base",
    "Corpus",
    "EvalArchive",
    "LeaderboardSnapshot",
    "Run",
    "append_audit",
    "init_db",
    "make_engine",
    "make_session_factory",
    "verify_audit_chain",
]
