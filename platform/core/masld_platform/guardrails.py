"""Input validation and guardrails.

Nothing malformed passes silently: non-finite numbers, out-of-distribution
values, missing credentials, or underpowered samples raise
:class:`GuardrailError`, which the API layer maps to HTTP 400.
"""

from __future__ import annotations

import math
import re
from typing import Any, Iterable

from pydantic import ValidationError

from masld_platform.schemas import EvalRecord, PromptRecord, RunSpec, RunType

#: Tokens that indicate corrupted numeric text inside prompts.
_NONFINITE_TOKEN_RE = re.compile(r"=\s*(nan|inf|-inf|infinity|-infinity)\b", re.IGNORECASE)


class GuardrailError(ValueError):
    """A guardrail rejected the input (maps to HTTP 400 in the API layer)."""


def require_finite(values: Iterable[float], *, what: str = "values") -> list[float]:
    """Validate that every value is a finite float; raise otherwise."""
    out: list[float] = []
    for v in values:
        try:
            f = float(v)
        except (TypeError, ValueError) as exc:
            raise GuardrailError(f"{what}: non-numeric entry {v!r}") from exc
        if not math.isfinite(f):
            raise GuardrailError(f"{what}: non-finite entry {v!r}")
        out.append(f)
    return out


def check_min_n(n: int, min_n: int, *, what: str = "sample") -> None:
    if n < min_n:
        raise GuardrailError(f"{what}: n={n} below minimum {min_n}")


def validate_prompt_records(records: list[dict[str, Any]]) -> list[PromptRecord]:
    """Schema-validate prompt records and screen prompts for corrupt numerics."""
    out: list[PromptRecord] = []
    for i, rec in enumerate(records):
        try:
            pr = PromptRecord.model_validate(rec)
        except ValidationError as exc:
            raise GuardrailError(f"prompt record {i}: {exc.error_count()} schema errors") from exc
        if _NONFINITE_TOKEN_RE.search(pr.prompt):
            raise GuardrailError(
                f"prompt record {i} ({pr.task}/{pr.sample}): non-finite token in prompt"
            )
        out.append(pr)
    return out


def validate_eval_records(records: list[dict[str, Any]], *, lenient: bool = True) -> list[EvalRecord]:
    """Validate eval archive records.

    Args:
        lenient: keep records with ``error`` set (failed calls are legitimate
            archive content); when ``False`` they raise instead.
    """
    out: list[EvalRecord] = []
    for i, rec in enumerate(records):
        try:
            er = EvalRecord.model_validate(rec)
        except ValidationError as exc:
            raise GuardrailError(f"eval record {i}: {exc.error_count()} schema errors") from exc
        if er.error is not None and er.raw is not None:
            raise GuardrailError(f"eval record {i}: both raw and error set")
        if er.error is not None and not lenient:
            raise GuardrailError(f"eval record {i}: error record not allowed here")
        out.append(er)
    return out


#: Required and optional parameter contracts per run type.
_RUN_CONTRACTS: dict[RunType, tuple[set[str], set[str]]] = {
    RunType.FRONTIER: ({"model"}, {"corpus", "n_per_task", "max_tokens", "workers", "dataset_tag"}),
    RunType.LOCAL: ({"adapter_path", "corpus"}, {"base_model", "dataset_tag", "batch", "device"}),
    RunType.SCORE: (set(), {"archive_dir", "out_csv"}),
    RunType.PAIRED: ({"candidate"}, {"reference", "archive_dir"}),
    RunType.VERIFY: (set(), {"prompts_dir"}),
    RunType.BASELINE: ({"train_corpus"}, {"test_corpus", "feature_mode"}),
    RunType.BRIDGE_DISPATCH: ({"job_type"}, {"params"}),
}


def validate_run_spec(spec: RunSpec) -> RunSpec:
    """Check run params against the per-type contract (types + required keys)."""
    required, optional = _RUN_CONTRACTS[spec.type]
    unknown = set(spec.params) - required - optional
    if unknown:
        raise GuardrailError(
            f"run type {spec.type.value}: unknown params {sorted(unknown)}; "
            f"allowed: required {sorted(required)}, optional {sorted(optional)}"
        )
    missing = {k for k in required if k not in spec.params}
    if missing:
        raise GuardrailError(f"run type {spec.type.value}: missing params {sorted(missing)}")

    type_checks: dict[str, tuple[type, ...]] = {
        "model": (str,),
        "corpus": (str,),
        "reference": (str,),
        "candidate": (str,),
        "train_corpus": (str,),
        "test_corpus": (str,),
        "feature_mode": (str,),
        "archive_dir": (str,),
        "prompts_dir": (str,),
        "out_csv": (str,),
        "dataset_tag": (str,),
        "base_model": (str,),
        "adapter_path": (str,),
        "device": (str,),
        "job_type": (str,),
        "n_per_task": (int,),
        "max_tokens": (int,),
        "workers": (int,),
        "batch": (int,),
    }
    for key, val in spec.params.items():
        expected = type_checks.get(key)
        if expected and not isinstance(val, expected) or isinstance(val, bool) and key in {
            "n_per_task",
            "max_tokens",
            "workers",
            "batch",
        }:
            raise GuardrailError(f"param {key!r}: expected {expected}, got {type(val).__name__}")
    if "n_per_task" in spec.params and int(spec.params["n_per_task"]) <= 0:
        raise GuardrailError("n_per_task must be >= 1")
    return spec


def require_secret(value: str | None, *, name: str) -> str:
    """Return a required credential from an environment-loaded value.

    Refuses empty strings and the literal placeholder used in .env.example.
    The value is never logged or embedded in exceptions beyond its name.
    """
    if not value or not value.strip() or value.strip().upper().startswith("REPLACE_"):
        raise GuardrailError(f"missing credential: {name} (set it in the environment / .env)")
    return value.strip()
