"""MASLD-Bench platform core engines.

Pure, fully typed computational modules decoupled from HTTP, UI and
persistence concerns. The research repository (``MASLD_ROOT``) is treated as
a read-only data source: frozen prompt corpora, evaluation archives and
model checkpoints are consumed in place and never mutated here.
"""

from masld_platform.schemas import (
    EvalRecord,
    LeaderboardRow,
    MetaHeader,
    PromptRecord,
    RunSpec,
    RunState,
    RunType,
    TaskType,
)

__all__ = [
    "EvalRecord",
    "LeaderboardRow",
    "MetaHeader",
    "PromptRecord",
    "RunSpec",
    "RunState",
    "RunType",
    "TaskType",
]

__version__ = "0.1.0"
