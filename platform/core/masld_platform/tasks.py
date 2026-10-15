"""Benchmark task registry: task id -> :class:`AnswerType`.

The registry is profile-driven (see :mod:`masld_platform.profile`): the
active profile maps task ids and id-suffix rules to answer-type names, which
resolve to built-ins (``yes_no`` / ``letter`` / ``number``) or custom
categorical types. Gold-answer sniffing remains the last-resort fallback for
genuinely unknown tasks.
"""

from __future__ import annotations

import re

from masld_platform.profile import get_active_profile
from masld_platform.schemas import AnswerType, EvalRecord, PromptRecord

#: Task ids look like ``MB-2001`` / ``QA-0001`` (4-5 digits after a prefix).
_TASK_ID_RE = re.compile(r"^[A-Za-z]+-\d{4,5}$")


def valid_task_id(task_id: str) -> bool:
    return bool(_TASK_ID_RE.match(task_id))


def answer_type_for(task_id: str) -> AnswerType | None:
    """Resolve the answer type of a task id, or ``None`` if unknown.

    Order: explicit profile ``tasks`` entry, then suffix rule on the last two
    digits of the numeric part. Callers fall back to :func:`sniff_answer_type`.
    """
    profile = get_active_profile()
    name = profile.tasks.get(task_id)
    if name is not None:
        return profile.answer_type(name)
    digits = task_id.rsplit("-", 1)[-1] if "-" in task_id else task_id
    if len(digits) >= 2 and digits[-2:] in profile.suffix_rules:
        return profile.answer_type(profile.suffix_rules[digits[-2:]])
    return None


def sniff_answer_type(answer: str | None) -> AnswerType | None:
    """Infer the answer type from a gold answer value (last-resort fallback)."""
    from masld_platform.schemas import BUILTIN_ANSWER_TYPES

    if answer is None:
        return None
    a = answer.strip().lower()
    if a in ("yes", "no"):
        return BUILTIN_ANSWER_TYPES["yes_no"]
    if a in ("a", "b"):
        return BUILTIN_ANSWER_TYPES["letter"]
    try:
        float(a)
        return BUILTIN_ANSWER_TYPES["number"]
    except ValueError:
        pass
    upper = answer.strip().upper()
    for type_name in get_active_profile().answer_types:
        at = get_active_profile().answer_type(type_name)
        if upper in (t.upper() for t in at.tokens):
            return at
    return None


def resolve_task_type(
    task_id: str, records: list[PromptRecord] | list[EvalRecord]
) -> AnswerType:
    """Registry lookup with sniffing fallback; raises if both fail."""
    at = answer_type_for(task_id)
    if at is not None:
        return at
    for r in records:
        if r.task == task_id:
            at = sniff_answer_type(r.answer)
            if at is not None:
                return at
    raise ValueError(f"cannot resolve answer type for {task_id!r}; not in the active profile")
