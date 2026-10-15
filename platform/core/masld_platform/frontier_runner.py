"""Frontier-model evaluation runner (OpenRouter).

Production hygiene over the research script:

* the API key comes from the environment ONLY (``require_secret``); no
  plaintext-file fallbacks;
* retries honour ``Retry-After`` on 429 with exponential backoff otherwise;
* resume is keyed by ``(task, sample)`` of successful records only;
* the archive is append-only gzip JSONL in the universal EvalRecord format.

Deterministic sampling: stratified ``n_per_task`` draws from the frozen test
corpus with the platform seed, matching the research bracket protocol.
"""

from __future__ import annotations

import random
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field

from masld_platform.answers import parse_answer
from masld_platform.guardrails import GuardrailError, require_secret
from masld_platform.io_jsonl import append_jsonl, load_jsonl, read_jsonl_resilient
from masld_platform.schemas import EvalRecord, TaskType
from masld_platform.tasks import resolve_task_type

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class FrontierConfig(BaseModel):
    """Decoding + transport parameters for one frontier run."""

    model: str
    corpus: str = "MB-20xx_liver_test.jsonl.gz"
    dataset_tag: str = "MB-20xx"
    n_per_task: int = Field(default=300, ge=1)
    max_tokens: int = Field(default=200, ge=1)
    temperature: float = 0.0
    top_p: float = 1.0
    workers: int = Field(default=6, ge=1, le=32)
    timeout: float = Field(default=240.0, gt=0)
    retries: int = Field(default=4, ge=0)
    seed: int = 20260929


class FrontierSummary(BaseModel):
    """Headline counters of a (possibly resumed) frontier run."""

    model: str
    n_target: int
    n_done_before: int
    n_new: int
    n_failed: int
    elapsed_min: float


def stratified_sample(
    records: list[dict[str, Any]], n_per_task: int, *, seed: int
) -> list[dict[str, Any]]:
    """Deterministic stratified draw: ``n_per_task`` per task, sorted tasks."""
    rng = random.Random(seed)
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        if "task" in r and "sample" in r:
            by_task[r["task"]].append(r)
    out: list[dict[str, Any]] = []
    for task in sorted(by_task):
        group = list(by_task[task])
        rng.shuffle(group)
        out.extend(group[:n_per_task])
    return out


def call_openrouter(
    body: dict[str, Any],
    api_key: str,
    *,
    timeout: float = 240.0,
    retries: int = 4,
) -> tuple[str | None, str | None, str | None]:
    """One chat completion call with retry/backoff.

    Returns:
        ``(content, model_version, error)`` — exactly one of content/error set.
    """
    import httpx  # lazy: keeps core importable without the API extra

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    backoff = 5.0
    for attempt in range(retries + 1):
        try:
            resp = httpx.post(
                OPENROUTER_URL, json=body, headers=headers, timeout=timeout
            )
        except httpx.HTTPError as exc:
            err = f"transport: {type(exc).__name__}"
            if attempt == retries:
                return None, None, err
            time.sleep(backoff)
            backoff *= 2
            continue
        if resp.status_code == 429:
            if attempt == retries:
                return None, None, "HTTP 429"
            retry_after = min(float(resp.headers.get("Retry-After", 0) or 0), 120.0)
            time.sleep(retry_after if retry_after > 0 else 20.0 * (attempt + 1))
            continue
        if resp.status_code >= 400:
            if attempt == retries:
                return None, None, f"HTTP {resp.status_code}"
            time.sleep(backoff)
            backoff *= 2
            continue
        try:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            version = data.get("model") or body["model"]
            return (content or "").strip(), version, None
        except (KeyError, IndexError, ValueError):
            return None, None, "malformed response body"
    return None, None, "unreachable"  # pragma: no cover


def run_frontier_eval(
    config: FrontierConfig,
    *,
    prompts_dir: str | Path,
    archive_path: str | Path,
    api_key: str | None,
    progress_cb: Callable[[str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> FrontierSummary:
    """Execute (or resume) one frontier evaluation run.

    Raises:
        GuardrailError: missing API key, missing corpus, or invalid corpus.
    """
    key = require_secret(api_key, name="OPENROUTER_API_KEY")
    corpus_path = Path(prompts_dir) / config.corpus
    if not corpus_path.exists():
        raise GuardrailError(f"corpus not found: {corpus_path}")

    records, _ = load_jsonl(corpus_path, skip_meta=True)
    if not records:
        raise GuardrailError(f"corpus is empty: {corpus_path}")
    sample = stratified_sample(records, config.n_per_task, seed=config.seed)

    # Resume: successful records only, keyed by (task, sample).
    done: set[tuple[str, str]] = set()
    n_before = 0
    archive_path = Path(archive_path)
    if archive_path.exists():
        for r in read_jsonl_resilient(archive_path):
            if r.get("raw") is not None and r.get("task") and r.get("sample"):
                done.add((r["task"], r["sample"]))
                n_before += 1
    todo = [r for r in sample if (r["task"], r["sample"]) not in done]

    def log(msg: str) -> None:
        if progress_cb:
            progress_cb(msg)

    log(
        f"frontier {config.model}: target={len(sample)} done={n_before} todo={len(todo)}"
    )

    t0 = time.time()
    n_new = n_failed = 0

    def one(item: dict[str, Any]) -> dict[str, Any]:
        body = {
            "model": config.model,
            "messages": [{"role": "user", "content": item["prompt"]}],
            "temperature": config.temperature,
            "top_p": config.top_p,
            "max_tokens": config.max_tokens,
        }
        content, version, err = call_openrouter(
            body, key, timeout=config.timeout, retries=config.retries
        )
        at = resolve_task_type(item["task"], [])
        parsed = parse_answer(content, at) if content else None
        rec = EvalRecord(
            task=item["task"],
            sample=item["sample"],
            answer=item.get("answer"),
            raw=content,
            error=err,
            model_version=version,
            parsed=parsed,
        )
        return rec.model_dump()

    buffer: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=config.workers) as pool:
        futures = {pool.submit(one, item): item for item in todo}
        for fut in as_completed(futures):
            if should_cancel and should_cancel():
                pool.shutdown(wait=False, cancel_futures=True)
                break
            rec = fut.result()
            ok = rec.get("error") is None
            n_new += 1 if ok else 0
            n_failed += 0 if ok else 1
            buffer.append(rec)
            if len(buffer) >= 25:
                append_jsonl(archive_path, buffer)
                log(f"  +{len(buffer)} (total {n_new}/{len(todo)})")
                buffer = []
    if buffer:
        append_jsonl(archive_path, buffer)

    return FrontierSummary(
        model=config.model,
        n_target=len(sample),
        n_done_before=n_before,
        n_new=n_new,
        n_failed=n_failed,
        elapsed_min=round((time.time() - t0) / 60, 2),
    )
