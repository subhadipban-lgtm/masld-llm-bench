"""FastAPI application factory.

Wires the lifespan (settings, engine, session factory, run executor, audit),
CORS for the local frontend, guardrail exception mapping, and all routers.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from masld_api.execution import RunExecutor
from masld_api.routers import bridge, corpora, health, leaderboard, runs
from masld_platform.config import Settings, get_settings
from masld_platform.guardrails import GuardrailError
from masld_persistence.audit import append_audit
from masld_persistence.database import init_db, make_engine, make_session_factory


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the API app; settings injected for tests, env-loaded otherwise."""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        from masld_platform.profile import set_active_profile

        set_active_profile(settings.profile)
        engine = make_engine(settings.resolved_db_url())
        init_db(engine)
        session_factory = make_session_factory(engine)
        app.state.settings = settings
        app.state.session_factory = session_factory
        app.state.executor = RunExecutor(settings, session_factory)
        with session_factory() as session:
            append_audit(session, event="api.start", payload={"root": str(settings.root)})
        yield
        app.state.executor.shutdown()
        engine.dispose()

    app = FastAPI(
        title="MASLD-Bench Platform API",
        version="0.1.0",
        description=(
            "Benchmark management, frontier + local model evaluation, scoring, "
            "paired statistics and Colab/Drive orchestration for the MASLD-LLM program."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(GuardrailError)
    async def guardrail_handler(request: Request, exc: GuardrailError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    app.include_router(health.router)
    app.include_router(corpora.router)
    app.include_router(runs.router)
    app.include_router(leaderboard.router)
    app.include_router(bridge.router)
    return app
