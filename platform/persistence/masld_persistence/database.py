"""Engine and session management (SQLite default, Postgres in compose)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def make_engine(db_url: str) -> Engine:
    """Create the SQLAlchemy engine.

    SQLite paths are created lazily; ``check_same_thread=False`` is required
    because run execution happens on worker threads.
    """
    if db_url.startswith("sqlite:///"):
        db_path = db_url.removeprefix("sqlite:///")
        if db_path and db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(
            db_url,
            connect_args={"check_same_thread": False} if db_path != ":memory:" else {},
        )
    return create_engine(db_url, pool_pre_ping=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def init_db(engine: Engine) -> None:
    """Create all tables (idempotent)."""
    from masld_persistence.models import Base

    Base.metadata.create_all(engine)
