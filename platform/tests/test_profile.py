"""Benchmark profile tests: loading, validation, domain switching."""

from __future__ import annotations

from pathlib import Path

import pytest

from masld_platform.profile import (
    DEFAULT_PROFILE_PATH,
    PROFILES_DIR,
    get_active_profile,
    load_profile,
    reset_active_profile,
    set_active_profile,
)
from masld_platform.schemas import TaskType
from masld_platform.tasks import answer_type_for, sniff_answer_type

GENERIC = PROFILES_DIR / "example-generic.yaml"


def test_default_profile_is_masld() -> None:
    reset_active_profile()
    prof = get_active_profile()
    assert prof.name == "masld"
    assert DEFAULT_PROFILE_PATH.name == "masld.yaml"
    assert answer_type_for("MB-2002").name == "f_stage"


def test_generic_profile_loads_and_resolves() -> None:
    prof = load_profile(GENERIC)
    assert prof.name == "example-generic"
    assert prof.answer_type("severity").kind is TaskType.CATEGORICAL
    assert prof.answer_type("severity").tokens == ("mild", "moderate", "severe")


def test_profile_switch_changes_registry() -> None:
    try:
        set_active_profile(GENERIC)
        assert answer_type_for("QA-0002").name == "severity"
        assert answer_type_for("QA-0001").kind is TaskType.YES_NO
        assert sniff_answer_type("MODERATE").name == "severity"
        # Explicit MASLD tasks are gone; only the generic suffix rules remain
        # (MB-2002 still matches suffix "02" -> severity; "07" has no rule).
        assert answer_type_for("MB-2002").name == "severity"
        assert answer_type_for("MB-12307") is None
    finally:
        reset_active_profile()


def test_invalid_profile_rejects_unknown_type(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("name: bad\ntasks:\n  T-0001: nope\n")
    with pytest.raises(ValueError, match="unknown answer type"):
        load_profile(bad)


def test_invalid_profile_rejects_duplicate_tokens(tmp_path: Path) -> None:
    bad = tmp_path / "bad2.yaml"
    bad.write_text(
        "name: bad2\n"
        "answer_types:\n"
        "  sev:\n"
        "    kind: categorical\n"
        "    pattern: '(a|A)'\n"
        "    tokens: [a, A]\n"
    )
    with pytest.raises(ValueError, match="duplicate tokens"):
        load_profile(bad)


def test_cohort_task_prefix_validation_is_generic() -> None:
    from masld_platform.guardrails import GuardrailError, validate_prompt_records

    ok = validate_prompt_records(
        [{"task": "QA-0001", "sample": "S1", "prompt": "p?", "answer": "yes"}]
    )
    assert ok[0].task == "QA-0001"
    with pytest.raises(GuardrailError):
        validate_prompt_records(
            [{"task": "2001", "sample": "S1", "prompt": "p?", "answer": "yes"}]
        )


def test_feature_extractor_registry() -> None:
    from masld_platform.features import encode_prompt, get_extractor, register_extractor

    class UpperCount:
        name = "uppercount"

        def encode(self, prompt: str) -> dict[str, float]:
            return {"n_upper": float(sum(1 for c in prompt if c.isupper()))}

    register_extractor(UpperCount())
    assert get_extractor("uppercount").encode("ABc") == {"n_upper": 2.0}
    assert encode_prompt("ABc", mode="uppercount") == {"n_upper": 2.0}
    assert encode_prompt("Patient: female; G1=1.0", mode="genes+uppercount") == {
        "G1": 1.0,
        "n_upper": 2.0,  # 'P' (Patient) + 'G' (G1)
    }
    with pytest.raises(ValueError, match="unknown feature extractor"):
        encode_prompt("x", mode="nope")
