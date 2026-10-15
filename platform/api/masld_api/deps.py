"""FastAPI dependency wiring (request-state pattern).

``app.state`` carries the settings, session factory and run executor created
in the lifespan; these deps expose them to the routers with proper typing.
"""

from __future__ import annotations

from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from masld_api.execution import RunExecutor
from masld_platform.config import Settings


def get_api_settings(request: Request) -> Settings:
    """App settings (paths, credentials) from the lifespan."""
    return request.app.state.settings  # type: ignore[no-any-return]


def get_db(request: Request) -> Generator[Session, None, None]:
    """One DB session per request; closed on exit."""
    session: Session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def get_executor(request: Request) -> RunExecutor:
    """The process-wide run executor from the lifespan."""
    return request.app.state.executor  # type: ignore[no-any-return]
