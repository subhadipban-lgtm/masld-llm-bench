"""Unified answer parser, keyed by :class:`AnswerType`.

Consolidates the five divergent per-script parsers of the research
repository into one deterministic, profile-driven implementation:

* ``yes_no``: leading answer or explicit "answer: yes"/"answer is yes" phrasing.
* ``letter``: pairwise A/B with optional phrasing; a bare leading letter only
  (never fires on words like "answer").
* ``number``: first numeric token, decimals and negatives allowed.
* ``categorical`` (e.g. the MASLD ``f_stage`` F0–F4 type): first regex match;
  the capture group maps onto the declared token set — which also handles the
  compact models' degenerate ``"F1F1F1..."`` emissions by design.

Frontier outputs are prose with the verdict often at the end, so the full
text is scanned (ordered: explicit phrasing, leading token, first match).
Local-model generation is newline-stopped upstream
(:mod:`masld_platform.local_runner`), so the same parser serves both.

Unparseable output returns ``None`` and counts against validity, never
silently coerced.
"""

from __future__ import annotations

import re

from masld_platform.schemas import AnswerType, TaskType

_YES_NO_PATTERNS = re.compile(r"answer(?:\s+is)?[:\s]\s*\**\s*(yes|no)\b")
#: Verdict after an explicit answer lead-in, tolerating markdown/quotes/newlines
#: and an optional "Patient"/"Option" word ("**Final answer:**"> **A**").
_LETTER_PATTERN = re.compile(
    r"answer(?:\s+is)?\s*[:\-]?\s*[*\s>\"'`]*(?:patient|option|choice)?\s*"
    r"[*_\s>\"'`]*([ab])\b",
    re.IGNORECASE,
)
#: Bare leading letter only — must not fire on words like "answer".
_LETTER_START = re.compile(r"^\s*(?:[*_`#>\-\s]+)?([ABab])\b")
_NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")
#: Leading markdown emphasis/bullets/quotes before a first-token answer.
_LEAD_MARKUP = re.compile(r"^[\s*_`#>\"'(\[]+")
#: "The answer is:" / "Answer:" may be followed by markup and newlines.
_ANSWER_LEAD = re.compile(r"^\s*(?:the\s+)?answer(?:\s+is)?\s*[:\-]?\s*", re.IGNORECASE)


def _clean(text: str) -> str:
    """Strip leading markdown decoration so a verdict at position 0 is seen.

    Surface-form normalisation only: it never changes which verdict the model
    stated, and it applies identically to every archive.
    """
    t = _LEAD_MARKUP.sub("", text.strip())
    return t


def parse_yes_no(text: str) -> str | None:
    t = _clean(text)
    low = t.lower()
    if low.startswith(("yes", "no")):
        return "yes" if low.startswith("yes") else "no"
    # "The answer is:\n\n**Yes**" — skip the lead-in and re-check position 0.
    stripped = _ANSWER_LEAD.sub("", t)
    low2 = _clean(stripped).lower()
    if low2.startswith(("yes", "no")):
        return "yes" if low2.startswith("yes") else "no"
    m = _YES_NO_PATTERNS.search(low)
    return m.group(1) if m else None


def parse_letter(text: str) -> str | None:
    t = _clean(text)
    if (m := _LETTER_START.match(t)):
        return m.group(1).upper()
    stripped = _ANSWER_LEAD.sub("", t)
    if (m := _LETTER_START.match(_clean(stripped))):
        return m.group(1).upper()
    m = _LETTER_PATTERN.search(t)
    return m.group(1).upper() if m else None


def parse_number(text: str) -> float | None:
    m = _NUMBER_PATTERN.search(_clean(text))
    if not m:
        return None
    try:
        v = float(m.group(0))
    except ValueError:  # pragma: no cover - regex guarantees parseable
        return None
    if v != v or v in (float("inf"), float("-inf")):  # NaN/inf guard
        return None
    return v


def parse_categorical(text: str, at: AnswerType) -> str | None:
    """First pattern match mapped onto the declared token set."""
    m = re.search(at.pattern, text, re.IGNORECASE)
    if not m:
        return None
    captured = (m.group(1) if m.groups() else m.group(0)).strip()
    if not captured:
        return None
    norm = captured.upper() if at.normalize == "upper" else captured.lower()
    canonical = [t.upper() if at.normalize == "upper" else t.lower() for t in at.tokens]
    if norm in canonical:  # the capture IS the token (e.g. "moderate")
        return at.tokens[canonical.index(norm)]
    # The capture is the distinguishing part (e.g. "2" for token "F2"):
    # accept only a unique suffix/prefix match to stay deterministic.
    matches = [i for i, c in enumerate(canonical) if c.endswith(norm) or c.startswith(norm)]
    return at.tokens[matches[0]] if len(matches) == 1 else None


def parse_answer(text: str | None, at: AnswerType) -> str | float | None:
    """Parse a raw model output into the canonical prediction for a task type."""
    if not text or not text.strip():
        return None
    t = text.strip()
    if at.kind is TaskType.YES_NO:
        return parse_yes_no(t)
    if at.kind is TaskType.LETTER:
        return parse_letter(t)
    if at.kind is TaskType.NUMBER:
        return parse_number(t)
    if at.kind is TaskType.CATEGORICAL:
        return parse_categorical(t, at)
    raise ValueError(f"unknown answer kind: {at.kind}")  # pragma: no cover


def gold_value(answer: str, at: AnswerType) -> str | float:
    """Normalise a gold answer string to its comparable value.

    Classification golds stay strings in canonical token casing; numeric
    golds become floats. Raises on inconsistent golds — a corrupted corpus
    must fail loudly, not score silently wrong (e.g. out-of-range F5+ labels
    for the MASLD ``f_stage`` type).
    """
    a = answer.strip()
    if at.kind is TaskType.NUMBER:
        try:
            return float(a)
        except ValueError as exc:
            raise ValueError(f"numeric task gold not parseable: {answer!r}") from exc
    if at.kind is TaskType.CATEGORICAL:
        norm = a.upper() if at.normalize == "upper" else a.lower()
        canonical = [t.upper() if at.normalize == "upper" else t.lower() for t in at.tokens]
        if norm not in canonical:
            raise ValueError(
                f"categorical task gold not in tokens {list(at.tokens)}: {answer!r}"
            )
        return at.tokens[canonical.index(norm)]
    if at.kind is TaskType.YES_NO:
        if a.lower() not in ("yes", "no"):
            raise ValueError(f"yes/no task gold malformed: {answer!r}")
        return a.lower()
    if at.kind is TaskType.LETTER:
        if a.upper() not in ("A", "B"):
            raise ValueError(f"letter task gold malformed: {answer!r}")
        return a.upper()
    raise ValueError(f"unknown answer kind: {at.kind}")  # pragma: no cover
