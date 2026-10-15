"""End-to-end API tests: lifespan, corpora, run execution, leaderboard, audit."""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from masld_api.app import create_app
from tests.conftest import (
    eval_record,
    make_settings,
    prompt_record,
    write_archive,
    write_corpus,
)


@pytest.fixture()
def client(repo: dict[str, Any], tmp_path: Any) -> Any:
    settings = make_settings(repo, tmp_path)
    # One scored archive + one manifest-registered corpus in the fake root.
    write_archive(
        repo["archives"],
        "model-a__MB-20xx",
        [eval_record("MB-2001", f"S{i}", g, r) for i, (g, r) in enumerate(zip(["yes", "no"], ["yes", "no"]))],
    )
    write_archive(
        repo["archives"],
        "model-b__MB-20xx",
        [eval_record("MB-2001", "S1", "yes", "no"), eval_record("MB-2001", "S2", "no", "no")],
    )
    write_corpus(
        repo["prompts"],
        "MB-20xx_liver_test.jsonl.gz",
        [prompt_record("MB-2001", "S1", "yes"), prompt_record("MB-2001", "S2", "no")],
        with_manifest=True,
    )
    with TestClient(create_app(settings)) as c:
        yield c


def _wait_run(client: TestClient, run_id: str, timeout_s: float = 30.0) -> dict[str, Any]:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        body = client.get(f"/runs/{run_id}").json()
        if body["state"] in ("succeeded", "failed", "cancelled"):
            return body
        time.sleep(0.1)
    raise AssertionError(f"run {run_id} did not settle: {body}")


def test_health(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").status_code == 200


def test_corpora_list_and_verify(client: TestClient) -> None:
    body = client.get("/corpora").json()
    names = [c["name"] for c in body["corpora"]]
    assert "MB-20xx_liver_test.jsonl.gz" in names
    v = client.get("/corpora/MB-20xx_liver_test.jsonl.gz/verify").json()
    assert v["ok"] is True
    assert v["count"]["actual"] == 2


def test_corpora_verify_detects_tampering(client: TestClient, repo: dict[str, Any]) -> None:
    # Overwrite the corpus without updating the manifest.
    from tests.conftest import write_corpus

    write_corpus(repo["prompts"], "MB-20xx_liver_test.jsonl.gz", [prompt_record("MB-2001", "S1", "yes")])
    v = client.get("/corpora/MB-20xx_liver_test.jsonl.gz/verify").json()
    assert v["ok"] is False


def test_run_validation_rejects_bad_params(client: TestClient) -> None:
    resp = client.post("/runs", json={"type": "frontier", "params": {}})
    assert resp.status_code == 400
    resp = client.post("/runs", json={"type": "frontier", "params": {"model": 42}})
    assert resp.status_code == 400


def test_score_run_end_to_end(client: TestClient) -> None:
    resp = client.post("/runs", json={"type": "score", "params": {}})
    assert resp.status_code == 202
    run_id = resp.json()["id"]
    body = _wait_run(client, run_id)
    assert body["state"] == "succeeded", body
    log = client.get(f"/runs/{run_id}/log").json()["log"]
    assert any("rows" in line for line in log)

    lb = client.get("/leaderboard").json()
    assert lb["n_rows"] >= 2
    models = {r["model"] for r in lb["rows"]}
    assert {"model-a", "model-b"} <= models


def test_paired_endpoint(client: TestClient) -> None:
    resp = client.get(
        "/leaderboard/paired",
        params={"candidate": "model-a__MB-20xx", "reference": "model-b__MB-20xx"},
    )
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert results[0]["candidate"] == "model-a"
    assert results[0]["cell"]["both_correct"] == 1


def test_paired_endpoint_404(client: TestClient) -> None:
    assert client.get("/leaderboard/paired", params={"candidate": "nope", "reference": "model-b__MB-20xx"}).status_code == 404


def test_cancel_terminal_run_conflict(client: TestClient) -> None:
    run_id = client.post("/runs", json={"type": "score", "params": {}}).json()["id"]
    body = _wait_run(client, run_id)
    assert body["state"] == "succeeded"
    assert client.delete(f"/runs/{run_id}").status_code == 409


def test_bridge_disabled_without_drive(client: TestClient) -> None:
    assert client.get("/bridge/jobs").status_code == 503


def test_verify_run_type(client: TestClient) -> None:
    run_id = client.post("/runs", json={"type": "verify", "params": {}}).json()["id"]
    body = _wait_run(client, run_id)
    assert body["state"] == "succeeded"
