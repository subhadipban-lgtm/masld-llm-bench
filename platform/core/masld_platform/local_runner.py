"""Local compact-model evaluation (HuggingFace + PEFT adapters).

The heavy ML stack (torch/transformers/peft) is imported lazily inside
functions so the rest of the platform — and the API container — works without
it. Device selection follows the research hardening: CUDA if available, then
MPS behind a forced-synchronisation warmup probe (a wedged Metal stream is
detected, not hung on), else CPU; an explicit device override is honoured.

Generation protocol (matches the validated one-shot eval chain): greedy
decoding, continuation-only decode, first line = answer (newline stop),
adaptive batch halving on failure down to 1.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field

from masld_platform.answers import parse_answer
from masld_platform.io_jsonl import load_jsonl
from masld_platform.schemas import EvalRecord
from masld_platform.tasks import resolve_task_type


class LocalEvalConfig(BaseModel):
    """Parameters for one local-model evaluation run."""

    base_model: str = "Qwen/Qwen3-0.6B"
    adapter_path: str
    corpus: str
    dataset_tag: str
    batch: int = Field(default=4, ge=1)
    max_new_tokens: int = Field(default=24, ge=1)
    max_length: int = Field(default=4096, ge=64)
    device: str = ""  # "", "cpu", "mps", "cuda"
    dtype: str = "float16"
    hf_token: str | None = None


class LocalEvalSummary(BaseModel):
    model: str
    n_items: int
    n_valid: int
    elapsed_min: float
    device: str


def probe_device(preferred: str = "") -> str:
    """Pick cuda > mps(warmup-probed) > cpu, honouring an explicit override."""
    import torch

    if preferred == "cuda" or (not preferred and torch.cuda.is_available()):
        return "cuda"
    if preferred == "mps" or (not preferred and torch.backends.mps.is_available()):
        try:  # warmup probe: a wedged Metal stream fails fast here, not mid-eval
            x = torch.ones(8, device="mps") * 2
            if float(x.sum().item()) != 16.0:
                raise RuntimeError("mps probe returned garbage")
            return "mps"
        except Exception:  # noqa: BLE001 - any probe failure falls back
            return "cpu"
    if preferred == "mps":
        return "cpu"  # explicit mps but unavailable
    return "cpu"


def load_model(
    base_model: str,
    adapter_path: str,
    *,
    device: str,
    dtype: str = "float16",
    hf_token: str | None = None,
) -> tuple[Any, Any]:
    """Load tokenizer + PEFT-wrapped model (deliberately unmerged: halves peak RAM)."""
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(base_model, padding_side="left", token=hf_token)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    torch_dtype = getattr(__import__("torch"), dtype, None)
    model = AutoModelForCausalLM.from_pretrained(
        base_model, dtype=torch_dtype, token=hf_token
    )
    model = PeftModel.from_pretrained(model, adapter_path)
    model.to(device).eval()
    return tok, model


def run_local_eval(
    config: LocalEvalConfig,
    *,
    prompts_dir: str | Path,
    progress_cb: Callable[[str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> tuple[list[EvalRecord], LocalEvalSummary]:
    """Evaluate the local model on a full corpus; returns records + summary."""
    corpus_path = Path(prompts_dir) / config.corpus
    if not corpus_path.exists():
        raise FileNotFoundError(f"corpus not found: {corpus_path}")
    records, _ = load_jsonl(corpus_path, skip_meta=True)
    if not records:
        raise ValueError(f"corpus is empty: {corpus_path}")

    device = probe_device(config.device or "")
    if progress_cb:
        progress_cb(f"device={device}; loading {config.base_model} + adapter")
    tok, model = load_model(
        config.base_model,
        config.adapter_path,
        device=device,
        dtype=config.dtype,
        hf_token=config.hf_token,
    )
    if progress_cb:
        progress_cb(f"evaluating {len(records)} items, batch={config.batch}")

    import torch

    out: list[EvalRecord] = []
    batch = config.batch
    t0 = time.time()
    i = 0
    while i < len(records):
        if should_cancel and should_cancel():
            break
        chunk = records[i : i + batch]
        try:
            enc = tok(
                [r["prompt"] for r in chunk],
                padding=True,
                truncation=True,
                max_length=config.max_length,
                return_tensors="pt",
            ).to(device)
            with torch.no_grad():
                gen = model.generate(
                    **enc,
                    max_new_tokens=config.max_new_tokens,
                    do_sample=False,
                    pad_token_id=tok.pad_token_id,
                )
            for j, r in enumerate(chunk):
                text = tok.decode(gen[j][enc["input_ids"].shape[1] :], skip_special_tokens=True)
                first_line = text.split("\n")[0].strip()
                at = resolve_task_type(r["task"], [])
                out.append(
                    EvalRecord(
                        task=r["task"],
                        sample=r["sample"],
                        answer=r.get("answer"),
                        raw=first_line,
                        error=None,
                        model_version=Path(config.adapter_path).name,
                        parsed=parse_answer(first_line, at),
                    )
                )
            i += len(chunk)
            if progress_cb and (i // max(batch, 1)) % 25 == 0:
                rate = i / max(time.time() - t0, 1e-9)
                progress_cb(f"  {i}/{len(records)} ({rate:.1f} items/s)")
        except RuntimeError as exc:  # OOM / device faults: halve the batch
            if batch > 1:
                batch = max(batch // 2, 1)
                if progress_cb:
                    progress_cb(f"batch failure ({exc}); halving to {batch}")
                continue
            raise

    n_valid = sum(1 for r in out if r.parsed is not None)
    summary = LocalEvalSummary(
        model=config.base_model,
        n_items=len(out),
        n_valid=n_valid,
        elapsed_min=round((time.time() - t0) / 60, 2),
        device=device,
    )
    return out, summary
