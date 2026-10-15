"""Guardrail tests: corrupt inputs must fail loudly, credentials must exist."""

from __future__ import annotations

import pytest

from masld_platform.guardrails import (
    GuardrailError,
    check_min_n,
    require_finite,
    require_secret,
    validate_prompt_records,
    validate_run_spec,
)
from masld_platform.schemas import RunSpec, RunType
from tests.conftest import prompt_record


def test_require_finite_rejects_nan_and_inf() -> None:
    with pytest.raises(GuardrailError):
        require_finite([1.0, float("nan")])
    with pytest.raises(GuardrailError):
        require_finite([float("inf")])
    assert require_finite([1.0, 2.0]) == [1.0, 2.0]


def test_min_n() -> None:
    check_min_n(5, 5)
    with pytest.raises(GuardrailError):
        check_min_n(4, 5)


def test_prompt_validation_rejects_nan_prompt_text() -> None:
    rec = prompt_record("MB-2001", "S1", "yes", prompt="genes: G1=nan, G2=1.0")
    with pytest.raises(GuardrailError, match="non-finite"):
        validate_prompt_records([rec])


def test_prompt_validation_rejects_inf() -> None:
    rec = prompt_record("MB-2001", "S1", "yes", prompt="genes: G1=inf")
    with pytest.raises(GuardrailError):
        validate_prompt_records([rec])


def test_prompt_validation_rejects_schema_errors() -> None:
    bad = prompt_record("MB-2001", "S1", "yes")
    bad["answer"] = ""
    with pytest.raises(GuardrailError):
        validate_prompt_records([bad])


def test_run_spec_contracts() -> None:
    with pytest.raises(GuardrailError):
        validate_run_spec(RunSpec(type=RunType.FRONTIER, params={}))  # missing model
    with pytest.raises(GuardrailError):
        validate_run_spec(RunSpec(type=RunType.FRONTIER, params={"model": "x", "bogus": 1}))
    with pytest.raises(GuardrailError):
        validate_run_spec(RunSpec(type=RunType.FRONTIER, params={"model": "x", "n_per_task": "ten"}))
    with pytest.raises(GuardrailError):
        validate_run_spec(RunSpec(type=RunType.FRONTIER, params={"model": "x", "n_per_task": True}))
    ok = validate_run_spec(RunSpec(type=RunType.FRONTIER, params={"model": "x", "n_per_task": 300}))
    assert ok.params["model"] == "x"


def test_require_secret() -> None:
    with pytest.raises(GuardrailError):
        require_secret(None, name="TEST_KEY")
    with pytest.raises(GuardrailError):
        require_secret("   ", name="TEST_KEY")
    with pytest.raises(GuardrailError):
        require_secret("REPLACE_ME", name="TEST_KEY")
    assert require_secret(" real-key ", name="TEST_KEY") == "real-key"
