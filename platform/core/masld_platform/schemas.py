"""Typed schemas for the MASLD-Bench platform.

These mirror the de-facto on-disk record formats of the research repository
exactly, so archives written by the research scripts and by this platform are
interchangeable:

* Prompt corpora (``prompts/*.jsonl.gz``): one ``__meta__`` header line
  followed by ``PromptRecord`` lines (answers are always strings, including
  numeric answers).
* Evaluation archives (``results/frontier_runs/*.jsonl.gz``): ``EvalRecord``
  lines with the 7-field interchange schema
  ``{task, sample, answer, raw, error, model_version, parsed}``.
* Leaderboard rows: the unified column set ending the historical
  ``rho``/``spearman`` drift.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

#: Task ids look like ``MB-2001`` / ``QA-0001`` — an alpha prefix plus 4-5
#: digits; the prefix is domain vocabulary defined by the benchmark profile.
_TASK_ID_RE = re.compile(r"^[A-Za-z]+-\d{4,5}$")


class TaskType(str, Enum):
    """Answer modality *kinds*; domain-specific types are profile-defined.

    ``CATEGORICAL`` is parameterised by an :class:`AnswerType` (allowed tokens
    + extraction pattern) — e.g. the MASLD ``f_stage`` type (F0–F4) is one
    instance, a severity scale (mild/moderate/severe) another.
    """

    YES_NO = "yes_no"
    LETTER = "letter"
    NUMBER = "number"
    CATEGORICAL = "categorical"


class MetricName(str, Enum):
    """Metric families emitted by the scorer."""

    ACCURACY = "accuracy"
    MAE = "mae"


@dataclass(frozen=True)
class AnswerType:
    """A fully resolved answer modality (kind + parameters).

    Built-ins (``yes_no`` / ``letter`` / ``number``) carry no parameters;
    ``CATEGORICAL`` types carry the token set and the extraction regex (one
    capture group yielding the distinguishing part, e.g. ``f([0-4])``).
    Profiles instantiate these; code compares ``kind`` and uses ``tokens``.
    """

    kind: TaskType
    name: str
    pattern: str = ""
    tokens: tuple[str, ...] = ()
    normalize: str = "upper"


#: Built-in answer types available in every profile.
BUILTIN_ANSWER_TYPES: dict[str, AnswerType] = {
    "yes_no": AnswerType(kind=TaskType.YES_NO, name="yes_no"),
    "letter": AnswerType(kind=TaskType.LETTER, name="letter"),
    "number": AnswerType(kind=TaskType.NUMBER, name="number"),
}


class RunType(str, Enum):
    """Kinds of executable runs orchestrated by the platform."""

    FRONTIER = "frontier"
    LOCAL = "local"
    SCORE = "score"
    PAIRED = "paired"
    VERIFY = "verify"
    BASELINE = "baseline"
    BRIDGE_DISPATCH = "bridge_dispatch"


class RunState(str, Enum):
    """Lifecycle of a run; only forward transitions except CANCELLED."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def terminal(self) -> bool:
        return self in (RunState.SUCCEEDED, RunState.FAILED, RunState.CANCELLED)


class MetaHeader(BaseModel):
    """``__meta__`` first line of a prompt corpus or archive file."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    n_records: int = Field(ge=0)
    seed: int
    built: str
    builder: str
    # Research builders add provenance fields (e.g. ``epos_sha``); kept as-is.


class PromptRecord(BaseModel):
    """One benchmark item from a frozen corpus."""

    model_config = ConfigDict(extra="allow")

    task: str
    split: str = "test"
    sample: str
    source: str = ""
    prompt: str
    answer: str

    @field_validator("task")
    @classmethod
    def _valid_task(cls, v: str) -> str:
        if not _TASK_ID_RE.match(v):
            raise ValueError(
                f"malformed task id: {v!r} (expected <alpha-prefix>-<4-5 digits>, e.g. MB-2001)"
            )
        return v

    @field_validator("prompt", "answer", "sample")
    @classmethod
    def _non_empty(cls, v: str, info: Any) -> str:
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} must be a non-empty string")
        return v


class EvalRecord(BaseModel):
    """One model prediction against a benchmark item (universal interchange)."""

    model_config = ConfigDict(extra="allow")

    task: str
    sample: str
    #: Gold answer as stored in the corpus (string, even for numeric tasks).
    answer: str | None = None
    #: Raw model output text; ``None`` marks a failed call (``error`` set).
    raw: str | None = None
    error: str | None = None
    model_version: str | None = None
    #: Parsed prediction: "yes"/"no", "A"/"B", "F0".."F4" or float; ``None``
    #: means unparseable and counts against validity.
    parsed: str | float | None = None


class LeaderboardRow(BaseModel):
    """One scored (model, task) cell with a percentile bootstrap CI."""

    model: str
    task: str
    n: int = Field(ge=0)
    metric: str
    value: float
    ci_lo: float
    ci_hi: float
    validity: float = Field(ge=0.0, le=1.0)
    #: Spearman correlation; regression tasks only.
    rho: float | None = None


class RunSpec(BaseModel):
    """Validated request to execute a run of a given type."""

    type: RunType
    params: dict[str, Any] = Field(default_factory=dict)


class PairedCell(BaseModel):
    """2x2 concordance counts for one (candidate, reference) task comparison."""

    n: int
    both_correct: int
    cand_only: int
    ref_only: int
    neither: int


class PairedResult(BaseModel):
    """Paired comparison of a candidate archive against a reference archive."""

    candidate: str
    reference: str
    task: str
    metric: str
    cand_value: float
    ref_value: float
    cell: PairedCell
    #: Exact McNemar p-value over discordant pairs (cand_only vs ref_only).
    mcnemar_p: float | None = None
    #: Wilcoxon signed-rank p-value over per-item score deltas (regression).
    wilcoxon_p: float | None = None


class VerificationItem(BaseModel):
    """Outcome of one manifest entry check."""

    file: str
    ok: bool
    expected_count: int | None = None
    actual_count: int | None = None
    expected_sha16: str | None = None
    actual_sha16: str | None = None
    detail: str = ""


class VerificationReport(BaseModel):
    """Result of verifying a prompt corpus directory against its manifest."""

    manifest_version: str
    ok: bool
    items: list[VerificationItem] = Field(default_factory=list)
    #: Files on disk the manifest does not know about (informational).
    extras: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
