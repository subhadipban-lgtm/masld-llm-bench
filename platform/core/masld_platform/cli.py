"""Typer CLI for the MASLD-Bench platform.

Every command is a thin, typed shell over the core engines and the agents
layer; configuration comes from the environment (``platform/.env``).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import typer

from masld_platform.config import Settings, get_settings
from masld_platform.guardrails import GuardrailError, validate_run_spec
from masld_platform.schemas import RunSpec, RunType

app = typer.Typer(help="MASLD-Bench platform CLI", no_args_is_help=True, add_completion=False)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


def _out(obj: object) -> None:
    typer.echo(json.dumps(obj, indent=2, default=str))


@app.callback()
def _bootstrap(
    profile: Optional[Path] = typer.Option(
        None, envvar="MASLD_PROFILE", help="Benchmark profile YAML (domain vocabulary)."
    ),
) -> None:
    """Load the active benchmark profile before any command runs."""
    from masld_platform.profile import set_active_profile

    set_active_profile(profile or get_settings().profile)


@app.command("profile")
def profile_cmd() -> None:
    """Print the active benchmark profile (name, tasks, answer types)."""
    from masld_platform.profile import get_active_profile

    _out(get_active_profile().summary())


@app.command("verify-manifest")
def verify_manifest(
    prompts_dir: Optional[Path] = typer.Option(None, help="Defaults to <root>/prompts"),
) -> None:
    """Verify frozen corpora counts + checksums against MANIFEST.json."""
    s = get_settings()
    from masld_platform.manifest import verify_manifest as run_verify

    report = run_verify(
        (prompts_dir or s.prompts_dir()) / "MANIFEST.json", prompts_dir or s.prompts_dir()
    )
    _out(report.model_dump())
    raise typer.Exit(0 if report.ok else 1)


@app.command("score")
def score(
    archive_dir: Optional[Path] = typer.Option(None),
    out_csv: Optional[Path] = typer.Option(None),
) -> None:
    """Score all evaluation archives into a leaderboard CSV."""
    s = get_settings()
    from masld_platform.leaderboard import rows_to_csv, score_archives

    rows = score_archives(archive_dir or s.archives_dir(), seed=s.seed, progress_cb=typer.echo)
    dest = out_csv or (s.resolved_data_dir() / "leaderboard.csv")
    n = rows_to_csv(rows, dest)
    typer.echo(f"{n} rows -> {dest}")


@app.command("paired-stats")
def paired_stats(
    candidate: str = typer.Argument(..., help="archive stem, e.g. qwen3-0.6b-masld__MB-20xx"),
    reference: Optional[str] = typer.Option(None),
) -> None:
    """Paired comparison (McNemar/Wilcoxon) of two archives."""
    from masld_agents.tasks import execute_spec

    spec = RunSpec(
        type=RunType.PAIRED,
        params={"candidate": candidate, "reference": reference} if reference else {"candidate": candidate},
    )
    outcome = execute_spec(spec, settings=get_settings(), log=typer.echo)
    _out(outcome.summary)


@app.command("run-frontier")
def run_frontier(
    model: str = typer.Argument(..., help="OpenRouter model id"),
    n_per_task: int = typer.Option(300),
    corpus: str = typer.Option("MB-20xx_liver_test.jsonl.gz"),
) -> None:
    """Run (or resume) a frontier-model evaluation."""
    from masld_agents.tasks import execute_spec

    spec = RunSpec(
        type=RunType.FRONTIER,
        params={"model": model, "n_per_task": n_per_task, "corpus": corpus},
    )
    try:
        outcome = execute_spec(spec, settings=get_settings(), log=typer.echo)
        _out(outcome.summary)
    except GuardrailError as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(2) from exc


@app.command("run-local")
def run_local(
    adapter_path: Path = typer.Argument(..., help="PEFT adapter dir"),
    corpus: str = typer.Option("MB-20xx_liver_test.jsonl.gz"),
    base_model: str = typer.Option("Qwen/Qwen3-0.6B"),
    batch: int = typer.Option(4),
    device: Optional[str] = typer.Option(None, help="cpu | mps | cuda"),
) -> None:
    """Evaluate a local fine-tuned model on a corpus (needs [local-model] extra)."""
    from masld_agents.tasks import execute_spec

    spec = RunSpec(
        type=RunType.LOCAL,
        params={
            "adapter_path": str(adapter_path),
            "corpus": corpus,
            "base_model": base_model,
            "batch": batch,
            **({"device": device} if device else {}),
        },
    )
    try:
        outcome = execute_spec(spec, settings=get_settings(), log=typer.echo)
        _out(outcome.summary)
    except ImportError as exc:
        typer.echo(f"ERROR: {exc} — install with: pip install -e '.[local-model]'", err=True)
        raise typer.Exit(2) from exc
    except GuardrailError as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(2) from exc


@app.command("baseline")
def baseline(
    train_corpus: str = typer.Option("MB-10xx_liver_train.jsonl.gz"),
    test_corpus: str = typer.Option("MB-20xx_liver_test.jsonl.gz"),
    feature_mode: str = typer.Option("genes", help="genes | clinical | genes+clinical | manifold | all"),
) -> None:
    """Train + evaluate the classical ML baseline suite."""
    from masld_agents.tasks import execute_spec

    spec = RunSpec(
        type=RunType.BASELINE,
        params={
            "train_corpus": train_corpus,
            "test_corpus": test_corpus,
            "feature_mode": feature_mode,
        },
    )
    outcome = execute_spec(spec, settings=get_settings(), log=typer.echo)
    _out(outcome.summary)


@app.command("bridge-dispatch")
def bridge_dispatch(
    job_type: str = typer.Argument(..., help="eval_local | train"),
    params_json: str = typer.Option("{}", help="JSON string of job params"),
) -> None:
    """Queue a GPU job for the Colab bridge worker (via Drive)."""
    from masld_agents.tasks import execute_spec

    spec = RunSpec(
        type=RunType.BRIDGE_DISPATCH,
        params={"job_type": job_type, "params": json.loads(params_json)},
    )
    validate_run_spec(spec)
    outcome = execute_spec(spec, settings=get_settings(), log=typer.echo)
    _out(outcome.summary)


@app.command("bridge-sync")
def bridge_sync() -> None:
    """Ingest finished Colab bridge results (one supervisor pass)."""
    from masld_agents.supervisor import Supervisor
    from masld_persistence.database import make_engine, make_session_factory, init_db

    s = get_settings()
    engine = make_engine(s.resolved_db_url())
    init_db(engine)
    sup = Supervisor(s, make_session_factory(engine))
    _out(sup.tick())


@app.command("agent")
def agent(
    interval: float = typer.Option(60.0, help="seconds between supervisor ticks"),
) -> None:
    """Run the supervisor daemon (bridge ingestion, stall detection, retries)."""
    from masld_agents.supervisor import Supervisor
    from masld_persistence.database import init_db, make_engine, make_session_factory

    s = get_settings()
    engine = make_engine(s.resolved_db_url())
    init_db(engine)
    Supervisor(s, make_session_factory(engine)).run_forever(interval_s=interval)


@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8000),
) -> None:
    """Start the FastAPI service with uvicorn."""
    import uvicorn

    uvicorn.run("masld_api.app:create_app", factory=True, host=host, port=port)


@app.command("init-db")
def init_db_cmd() -> None:
    """Create all database tables."""
    from masld_persistence.database import init_db as _init
    from masld_persistence.database import make_engine

    s = get_settings()
    _init(make_engine(s.resolved_db_url()))
    typer.echo(f"initialized {s.resolved_db_url()}")


def main() -> None:  # console_scripts entry point
    app()


if __name__ == "__main__":
    main()
