"""Benchmark profiles: the domain vocabulary as data.

A profile is a small YAML file that turns the platform into a benchmark for
a specific domain. Everything else — run orchestration, scoring, paired
statistics, leaderboards, the dashboard, the Colab bridge — is domain-free.

```yaml
name: my-benchmark
answer_types:                      # custom types (built-ins need no entry)
  severity:
    kind: categorical
    pattern: '(mild|moderate|severe)'
    tokens: [mild, moderate, severe]
    normalize: lower
tasks:                             # task id -> answer type name
  TASK-001: yes_no
  TASK-002: severity
suffix_rules:                      # fallback keyed on last two digits
  "01": yes_no
```

The active profile is selected via ``MASLD_PROFILE`` (path) and defaults to
the bundled MASLD profile. Profiles validate eagerly: a task referencing an
undefined answer type fails at load, not mid-run.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator

from masld_platform.schemas import AnswerType, BUILTIN_ANSWER_TYPES, TaskType

#: Bundled domain profiles shipped with the platform.
PROFILES_DIR = Path(__file__).resolve().parents[2] / "profiles"
DEFAULT_PROFILE_PATH = PROFILES_DIR / "masld.yaml"

_lock = threading.Lock()
_active: "BenchmarkProfile | None" = None


class AnswerTypeDef(BaseModel):
    """Declarative definition of one custom (categorical) answer type."""

    kind: Literal["categorical"] = "categorical"
    #: Extraction regex over the raw model output; the FIRST match wins and
    #: group 1 (when present) is the distinguishing part matched to a token.
    pattern: str
    #: Allowed answer tokens in canonical casing (also the gold label set).
    tokens: list[str] = Field(min_length=1)
    normalize: Literal["upper", "lower"] = "upper"

    def resolve(self, name: str) -> AnswerType:
        try:
            import re

            re.compile(self.pattern)
        except re.error as exc:  # pragma: no cover - config authoring aid
            raise ValueError(f"answer type {name!r}: invalid pattern {self.pattern!r}") from exc
        if len(set(t.casefold() for t in self.tokens)) != len(self.tokens):
            raise ValueError(f"answer type {name!r}: duplicate tokens (case-insensitive)")
        return AnswerType(
            kind=TaskType.CATEGORICAL,
            name=name,
            pattern=self.pattern,
            tokens=tuple(self.tokens),
            normalize=self.normalize,
        )


class BenchmarkProfile(BaseModel):
    """A loaded benchmark profile (domain vocabulary)."""

    name: str
    version: int = 1
    description: str = ""
    answer_types: dict[str, AnswerTypeDef] = Field(default_factory=dict)
    tasks: dict[str, str] = Field(default_factory=dict)
    suffix_rules: dict[str, str] = Field(default_factory=dict)
    #: Default feature extractor names for baseline runs (see features.py).
    feature_extractors: list[str] = Field(default_factory=lambda: ["genes"])

    @field_validator("tasks")
    @classmethod
    def _tasks_reference_known_types(cls, v: dict[str, str]) -> dict[str, str]:
        # Only structural checks here; full validation happens in resolve()
        # because built-ins are not part of ``answer_types``.
        for task, type_name in v.items():
            if not task or not type_name:
                raise ValueError(f"task entry must be non-empty: {task!r}: {type_name!r}")
        return v

    def answer_type(self, name: str) -> AnswerType:
        """Resolve an answer-type name (built-in or custom) to an AnswerType."""
        if name in BUILTIN_ANSWER_TYPES:
            return BUILTIN_ANSWER_TYPES[name]
        if name in self.answer_types:
            return self.answer_types[name].resolve(name)
        raise ValueError(
            f"profile {self.name!r}: unknown answer type {name!r} "
            f"(defined: {sorted(self.answer_types)}; built-ins: {sorted(BUILTIN_ANSWER_TYPES)})"
        )

    def validate(self) -> "BenchmarkProfile":
        """Eagerly resolve every referenced AND declared type; raise on any error."""
        for name in self.answer_types:  # catches bad patterns / duplicate tokens
            self.answer_type(name)
        for task, type_name in self.tasks.items():
            try:
                self.answer_type(type_name)
            except ValueError as exc:
                raise ValueError(f"task {task}: {exc}") from exc
        for suffix, type_name in self.suffix_rules.items():
            self.answer_type(type_name)  # raises on unknown
        return self

    def summary(self) -> dict[str, object]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "n_tasks": len(self.tasks),
            "answer_types": {
                **dict.fromkeys(BUILTIN_ANSWER_TYPES),
                **{k: v.model_dump() for k, v in self.answer_types.items()},
            },
            "suffix_rules": self.suffix_rules,
        }


def load_profile(path: str | Path) -> BenchmarkProfile:
    """Load and validate a profile YAML file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"benchmark profile not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return BenchmarkProfile.model_validate(data).validate()


def get_active_profile() -> BenchmarkProfile:
    """The process-wide active profile (defaults to the bundled MASLD one).

    Tests and multi-domain deployments call :func:`set_active_profile`.
    """
    global _active
    with _lock:
        if _active is None:
            _active = load_profile(DEFAULT_PROFILE_PATH)
        return _active


def set_active_profile(profile: BenchmarkProfile | str | Path) -> BenchmarkProfile:
    """Set the active profile (object or path); returns it validated."""
    global _active
    profile = profile if isinstance(profile, BenchmarkProfile) else load_profile(profile)
    with _lock:
        _active = profile
    return profile


def reset_active_profile() -> None:
    """Reset to the default (bundled MASLD) profile — test isolation helper."""
    global _active
    with _lock:
        _active = None
