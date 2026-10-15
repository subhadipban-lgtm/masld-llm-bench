"""Task registry: maps a validated :class:`RunSpec` to core-engine execution.

Tasks are pure orchestration: they receive settings (paths + credentials),
a log callback and a cancellation hook, and return a :class:`RunOutcome` with
a JSON-safe summary plus artifact paths. Database state is managed by the
caller (API executor or supervisor), keeping this layer stateless and
testable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from masld_platform.colab_bridge import BridgeJob, JobType, enqueue_job
from masld_platform.config import Settings
from masld_platform.frontier_runner import FrontierConfig, run_frontier_eval
from masld_platform.guardrails import GuardrailError, validate_run_spec
from masld_platform.io_jsonl import write_jsonl
from masld_platform.leaderboard import rows_to_csv, score_archives
from masld_platform.manifest import verify_manifest
from masld_platform.schemas import LeaderboardRow, RunSpec, RunType

LogFn = Callable[[str], None]
CancelFn = Callable[[], bool]


@dataclass
class RunOutcome:
    """Result of one executed task."""

    summary: dict[str, Any] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    #: For score runs: the materialised leaderboard rows.
    rows: list[LeaderboardRow] = field(default_factory=list)


def execute_spec(
    spec: RunSpec,
    *,
    settings: Settings,
    log: LogFn | None = None,
    should_cancel: CancelFn | None = None,
) -> RunOutcome:
    """Validate and execute a run spec against the core engines.

    Raises:
        GuardrailError: invalid spec, missing credentials/data.
        ImportError: local-model runs without the ``local-model`` extra.
    """
    validate_run_spec(spec)
    log = log or (lambda _msg: None)
    should_cancel = should_cancel or (lambda: False)
    p = spec.params
    out_dir = settings.resolved_data_dir()
    (out_dir / "runs").mkdir(parents=True, exist_ok=True)

    if spec.type is RunType.FRONTIER:
        return _task_frontier(spec, settings=settings, log=log, cancel=should_cancel)
    if spec.type is RunType.LOCAL:
        return _task_local(spec, settings=settings, log=log, cancel=should_cancel)
    if spec.type is RunType.SCORE:
        return _task_score(spec, settings=settings, log=log, out_dir=out_dir)
    if spec.type is RunType.PAIRED:
        return _task_paired(spec, settings=settings, log=log, out_dir=out_dir)
    if spec.type is RunType.VERIFY:
        return _task_verify(spec, settings=settings, log=log)
    if spec.type is RunType.BASELINE:
        return _task_baseline(spec, settings=settings, log=log, out_dir=out_dir)
    if spec.type is RunType.BRIDGE_DISPATCH:
        return _task_bridge_dispatch(spec, settings=settings, log=log)
    raise GuardrailError(f"no task implementation for run type {spec.type}")


def _archive_name(model: str, tag: str) -> str:
    return f"{model.replace('/', '__')}__{tag}.jsonl.gz"


def _task_frontier(spec: RunSpec, *, settings: Settings, log: LogFn, cancel: CancelFn) -> RunOutcome:
    cfg = FrontierConfig(
        model=spec.params["model"],
        corpus=spec.params.get("corpus", "MB-20xx_liver_test.jsonl.gz"),
        dataset_tag=spec.params.get("dataset_tag", "MB-20xx"),
        n_per_task=int(spec.params.get("n_per_task", 300)),
        max_tokens=int(spec.params.get("max_tokens", 200)),
        workers=int(spec.params.get("workers", 6)),
        seed=settings.seed,
    )
    key = settings.openrouter_api_key.get_secret_value() if settings.openrouter_api_key else None
    archive = settings.archives_dir() / _archive_name(cfg.model, cfg.dataset_tag)
    settings.archives_dir().mkdir(parents=True, exist_ok=True)
    summary = run_frontier_eval(
        cfg,
        prompts_dir=settings.prompts_dir(),
        archive_path=archive,
        api_key=key,
        progress_cb=log,
        should_cancel=cancel,
    )
    return RunOutcome(
        summary=summary.model_dump(),
        artifacts=[str(archive)],
    )


def _task_local(spec: RunSpec, *, settings: Settings, log: LogFn, cancel: CancelFn) -> RunOutcome:
    from masld_platform.local_runner import LocalEvalConfig, run_local_eval

    adapter = Path(spec.params["adapter_path"])
    if not adapter.is_absolute():
        adapter = settings.root / adapter
    if not adapter.exists():
        raise GuardrailError(f"adapter path not found: {adapter}")
    cfg = LocalEvalConfig(
        base_model=spec.params.get("base_model", "Qwen/Qwen3-0.6B"),
        adapter_path=str(adapter),
        corpus=spec.params["corpus"],
        dataset_tag=spec.params.get("dataset_tag", Path(spec.params["corpus"]).stem.split("_")[0]),
        batch=int(spec.params.get("batch", 4)),
        device=spec.params.get("device", settings.device),
        hf_token=(
            settings.huggingface_token.get_secret_value() if settings.huggingface_token else None
        ),
    )
    records, summary = run_local_eval(
        cfg,
        prompts_dir=settings.prompts_dir(),
        progress_cb=log,
        should_cancel=cancel,
    )
    archive = settings.archives_dir() / _archive_name(
        cfg.adapter_path.rstrip("/").split("/")[-1], cfg.dataset_tag
    )
    settings.archives_dir().mkdir(parents=True, exist_ok=True)
    write_jsonl(archive, [r.model_dump() for r in records])
    log(f"archived {len(records)} records -> {archive}")
    return RunOutcome(summary=summary.model_dump(), artifacts=[str(archive)])


def _task_score(spec: RunSpec, *, settings: Settings, log: LogFn, out_dir: Path) -> RunOutcome:
    archive_dir = Path(spec.params.get("archive_dir", str(settings.archives_dir())))
    if not archive_dir.exists():
        raise GuardrailError(f"archive dir not found: {archive_dir}")
    rows = score_archives(archive_dir, seed=settings.seed, progress_cb=log)
    out_csv = Path(spec.params.get("out_csv", str(out_dir / "leaderboard.csv")))
    n = rows_to_csv(rows, out_csv)
    log(f"{n} rows -> {out_csv}")
    return RunOutcome(
        summary={"n_rows": n, "csv": str(out_csv)},
        artifacts=[str(out_csv)],
        rows=rows,
    )


def _task_paired(spec: RunSpec, *, settings: Settings, log: LogFn, out_dir: Path) -> RunOutcome:
    from masld_platform.paired import paired_compare

    archive_dir = Path(spec.params.get("archive_dir", str(settings.archives_dir())))
    candidate = archive_dir / f"{spec.params['candidate']}.jsonl.gz"
    if not candidate.exists():
        candidate = archive_dir / f"{spec.params['candidate']}"
    if not candidate.exists():
        raise GuardrailError(f"candidate archive not found: {spec.params['candidate']}")
    reference = None
    if ref := spec.params.get("reference"):
        reference = archive_dir / f"{ref}.jsonl.gz"
        if not reference.exists():
            reference = archive_dir / f"{ref}"
    if reference is None:
        reference = _default_reference(archive_dir)
    log(f"paired: {candidate.name} vs {reference.name}")
    results = paired_compare(candidate, reference)
    payload = [r.model_dump() for r in results]
    out_json = out_dir / "runs" / "paired_latest.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return RunOutcome(
        summary={"n_tasks": len(results), "out": str(out_json), "reference": reference.name},
        artifacts=[str(out_json)],
    )


def _default_reference(archive_dir: Path) -> Path:
    """Full frontier archive with the most records; explicit param preferred."""
    best, best_n = None, -1
    for p in sorted(archive_dir.glob("*.jsonl.gz")):
        try:
            size = p.stat().st_size
        except OSError:
            continue
        if size > best_n and "qwen3" not in p.name:
            best, best_n = p, size
    if best is None:
        raise GuardrailError(f"no reference archive found in {archive_dir}")
    return best


def _task_verify(spec: RunSpec, *, settings: Settings, log: LogFn) -> RunOutcome:
    prompts_dir = Path(spec.params.get("prompts_dir", str(settings.prompts_dir())))
    manifest_path = prompts_dir / "MANIFEST.json"
    if not manifest_path.exists():
        raise GuardrailError(f"manifest not found: {manifest_path}")
    report = verify_manifest(manifest_path, prompts_dir)
    log(f"manifest {report.manifest_version}: ok={report.ok} extras={len(report.extras)}")
    return RunOutcome(
        summary={
            "manifest_version": report.manifest_version,
            "ok": report.ok,
            "n_checked": len(report.items),
            "extras": report.extras,
            "missing": report.missing,
        },
        rows=[],
    )


def _task_baseline(spec: RunSpec, *, settings: Settings, log: LogFn, out_dir: Path) -> RunOutcome:
    from masld_platform.baselines import fit_baselines

    train = settings.prompts_dir() / spec.params["train_corpus"]
    test = Path(
        spec.params.get("test_corpus", "MB-20xx_liver_test.jsonl.gz")
    )
    test_path = settings.prompts_dir() / test if not test.is_absolute() else test
    if not train.exists() or not test_path.exists():
        raise GuardrailError(f"corpus missing: {train} or {test_path}")
    report = fit_baselines(
        str(train), str(test_path), feature_mode=spec.params.get("feature_mode", "genes")
    )
    out_json = out_dir / "runs" / "baselines_latest.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log(f"baselines -> {out_json}")
    return RunOutcome(summary={"tasks": list(report.get("tasks", {}))}, artifacts=[str(out_json)])


def _task_bridge_dispatch(spec: RunSpec, *, settings: Settings, log: LogFn) -> RunOutcome:
    job_type = JobType(spec.params["job_type"])
    job = BridgeJob(type=job_type, params=spec.params.get("params", {}))
    path = enqueue_job(settings.bridge_dir(), job)
    log(f"bridge job {job.job_id} ({job_type.value}) queued -> {path}")
    return RunOutcome(summary={"job_id": job.job_id, "type": job_type.value}, artifacts=[str(path)])
