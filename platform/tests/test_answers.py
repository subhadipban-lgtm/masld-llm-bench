"""Answer parser tests, including the compact models' degenerate emissions."""

from __future__ import annotations

import pytest

from masld_platform.answers import gold_value, parse_answer
from masld_platform.profile import get_active_profile
from masld_platform.schemas import TaskType

YES_NO = get_active_profile().answer_type("yes_no")
LETTER = get_active_profile().answer_type("letter")
NUMBER = get_active_profile().answer_type("number")
#: The MASLD categorical type (F0–F4) exercises the generic categorical path.
F_STAGE = get_active_profile().answer_type("f_stage")
assert F_STAGE.kind is TaskType.CATEGORICAL


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Yes.", "yes"),
        ("no", "no"),
        ("The answer is: YES", "yes"),
        ("Answer: no, because...", "no"),
        ("I cannot say", None),
        ("", None),
        (None, None),
        # Strict parser: only leading answers or explicit "answer ..." phrasings
        # count — a bare "yes" mid-line does not parse (research behavior).
        ("First line yes\nsecond line no", None),
    ],
)
def test_parse_yes_no(text: str | None, expected: str | None) -> None:
    assert parse_answer(text, YES_NO) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("A", "A"),
        ("b.", "B"),
        ("The answer is A", "A"),
        ("answer: b", "B"),
        ("Profile B shows...", None),
        ("Answer is C", None),
    ],
)
def test_parse_letter(text: str, expected: str | None) -> None:
    assert parse_answer(text, LETTER) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("F2", "F2"),
        ("f4", "F4"),
        ("F1F1F1F1F1", "F1"),  # degenerate cycling emission: first token wins
        ("Stage F3 fibrosis", "F3"),
        ("F5", None),  # out of range
        ("2", None),
    ],
)
def test_parse_f_stage(text: str, expected: str | None) -> None:
    assert parse_answer(text, F_STAGE) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2", 2.0),
        ("3.5", 3.5),
        ("-1.2", -1.2),
        ("about 4 out of 8", 4.0),
        ("0000", 0.0),
        ("1e5", 1.0),  # regex takes the leading integer, not the exponent
        ("none", None),
    ],
)
def test_parse_number(text: str, expected: float | None) -> None:
    assert parse_answer(text, NUMBER) == expected


def test_parse_generic_categorical() -> None:
    """Custom categorical types from another domain parse identically."""
    from masld_platform.profile import load_profile

    prof = load_profile(
        __import__("pathlib").Path(__file__).resolve().parents[1]
        / "profiles"
        / "example-generic.yaml"
    )
    sev = prof.answer_type("severity")
    assert parse_answer("The severity is Moderate.", sev) == "moderate"
    assert parse_answer("severe", sev) == "severe"
    assert parse_answer("unknown", sev) is None


def test_gold_value_normalisation() -> None:
    assert gold_value("yes", YES_NO) == "yes"
    assert gold_value("F2", F_STAGE) == "F2"
    assert gold_value("f2", F_STAGE) == "F2"  # canonicalised to declared casing
    assert gold_value("A", LETTER) == "A"
    assert gold_value("2", NUMBER) == 2.0


@pytest.mark.parametrize(
    ("answer", "at"),
    [
        ("maybe", YES_NO),
        ("F9", F_STAGE),
        ("Q", LETTER),
        ("abc", NUMBER),
    ],
)
def test_gold_value_rejects_corrupt(answer: str, at: object) -> None:
    with pytest.raises(ValueError):
        gold_value(answer, at)  # type: ignore[arg-type]
