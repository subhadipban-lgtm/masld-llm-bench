"""Classical ML baselines over prompt features (ElasticNet / HGB).

Port of the research session-2 logic, modernised: encodes prompts via
:mod:`masld_platform.features`, trains the same model family set
(LogisticRegression-EN, HistGradientBoosting, ElasticNetCV) and reports the
same reference baselines (majority class, median prediction).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from masld_platform.answers import gold_value
from masld_platform.features import encode_prompt, vectorise
from masld_platform.io_jsonl import load_jsonl
from masld_platform.schemas import AnswerType, PromptRecord, TaskType
from masld_platform.tasks import resolve_task_type


@dataclass
class TaskTargets:
    """Derived target views of a record set (one per task family head)."""

    task: str
    answer_type: AnswerType
    n: int


def build_xy(
    records: list[PromptRecord],
    *,
    tasks: list[str],
    feature_mode: str = "genes",
) -> dict[str, dict[str, Any]]:
    """Group records by task into ``{features, binary_y, multi_y, reg_y}`` sets.

    * yes/no answers -> ``binary_y`` (0/1)
    * categorical answers -> ``multi_y`` (index into the type's token set)
    * numeric answers -> ``reg_y`` (float)
    * letter (pairwise) answers -> excluded (no single-profile target)
    """
    out: dict[str, dict[str, Any]] = {}
    by_task: dict[str, list[PromptRecord]] = {}
    for r in records:
        if r.task in tasks:
            by_task.setdefault(r.task, []).append(r)
    for task, group in by_task.items():
        at = resolve_task_type(task, group)
        feats = [encode_prompt(r.prompt, mode=feature_mode) for r in group]
        binary_y: list[int] = []
        multi_y: list[int] = []
        reg_y: list[float] = []
        for r in group:
            g = gold_value(r.answer, at)
            if at.kind is TaskType.YES_NO:
                binary_y.append(1 if g == "yes" else 0)
            elif at.kind is TaskType.CATEGORICAL:
                multi_y.append(at.tokens.index(str(g)))
            elif at.kind is TaskType.NUMBER:
                reg_y.append(float(g))
        out[task] = {
            "features": feats,
            "answer_type": at,
            "binary_y": binary_y,
            "multi_y": multi_y,
            "reg_y": reg_y,
            "n": len(group),
        }
    return out


def fit_baselines(
    train_path: str,
    test_path: str,
    *,
    train_tasks: list[str] | None = None,
    test_tasks: list[str] | None = None,
    feature_mode: str = "genes",
) -> dict[str, Any]:
    """Train and evaluate the baseline suite; returns a JSON-safe report.

    Training uses the shared feature space (union of train+test keys, zero
    fill) mirroring the research protocol so cross-platform feature mismatch
    is visible rather than hidden.
    """
    train_raw, _ = load_jsonl(train_path)
    test_raw, _ = load_jsonl(test_path)
    train = [PromptRecord.model_validate(r) for r in train_raw]
    test = [PromptRecord.model_validate(r) for r in test_raw]

    train_tasks = train_tasks or _default_tasks(train, position=1)
    test_tasks = test_tasks or _default_tasks(test, position=2)
    tr = build_xy(train, tasks=train_tasks, feature_mode=feature_mode)
    te = build_xy(test, tasks=test_tasks, feature_mode=feature_mode)

    report: dict[str, Any] = {"meta": {"feature_mode": feature_mode, "tasks": sorted(te)}, "tasks": {}}
    for task in sorted(te):
        if task not in tr:
            report["tasks"][task] = {"error": "no matching train task"}
            continue
        tr_set, te_set = tr[task], te[task]
        at = te_set["answer_type"]
        X_all, cols = vectorise(tr_set["features"] + te_set["features"])
        X_tr = np.array(X_all[: len(tr_set["features"])])
        X_te = np.array(X_all[len(tr_set["features"]) :])
        entry: dict[str, Any] = {"n_train": len(tr_set["features"]), "n_test": len(te_set["features"]), "n_features": len(cols)}

        if at.kind is TaskType.YES_NO and tr_set["binary_y"] and te_set["binary_y"]:
            y_tr = np.array(tr_set["binary_y"])
            y_te = np.array(te_set["binary_y"])
            maj = float(np.bincount(y_tr).argmax())
            entry["majority_acc"] = _acc(np.full_like(y_te, maj), y_te)
            entry["elasticnet_logreg_acc"] = _acc(_fit_logreg(X_tr, y_tr, X_te), y_te)
            entry["hgb_acc"] = _acc(_fit_hgb_clf(X_tr, y_tr, X_te), y_te)
        elif at.kind is TaskType.CATEGORICAL and tr_set["multi_y"] and te_set["multi_y"]:
            y_tr = np.array(tr_set["multi_y"])
            y_te = np.array(te_set["multi_y"])
            maj = int(np.bincount(y_tr).argmax())
            entry["majority_acc"] = _acc(np.full_like(y_te, maj), y_te)
            entry["elasticnet_logreg_acc"] = _acc(_fit_logreg(X_tr, y_tr, X_te), y_te)
            entry["hgb_acc"] = _acc(_fit_hgb_clf(X_tr, y_tr, X_te), y_te)
        elif at.kind is TaskType.NUMBER and tr_set["reg_y"] and te_set["reg_y"]:
            y_tr = np.array(tr_set["reg_y"], dtype=float)
            y_te = np.array(te_set["reg_y"], dtype=float)
            entry["median_mae"] = float(np.mean(abs(np.full_like(y_te, np.median(y_tr)) - y_te)))
            en_pred = _fit_en(X_tr, y_tr, X_te)
            entry["elasticnet_mae"] = float(np.mean(abs(en_pred - y_te)))
            entry["elasticnet_rho"] = _safe_rho(en_pred, y_te)
            hgb_pred = _fit_hgb_reg(X_tr, y_tr, X_te)
            entry["hgb_mae"] = float(np.mean(abs(hgb_pred - y_te)))
            entry["hgb_rho"] = _safe_rho(hgb_pred, y_te)
        else:
            entry["error"] = f"unsupported pairing for answer type {at.name}"
        report["tasks"][task] = entry
    return report


def _default_tasks(records: list[PromptRecord], *, position: int) -> list[str]:
    """Clinical family heads for a corpus: MB-<pos>001..006 present in data."""
    prefix = {r.task[: 2 + position] for r in records}
    heads = ["001", "002", "005", "006"]
    out: list[str] = []
    for p in sorted(prefix):
        for h in heads:
            t = f"{p}{h}"
            if any(r.task == t for r in records):
                out.append(t)
    return out


def _acc(pred: np.ndarray, gold: np.ndarray) -> float:
    return float(np.mean(pred == gold))


def _fit_logreg(X_tr: np.ndarray, y_tr: np.ndarray, X_te: np.ndarray) -> np.ndarray:
    from sklearn.linear_model import LogisticRegression

    clf = LogisticRegression(max_iter=2000, C=1.0)
    clf.fit(X_tr, y_tr)
    return clf.predict(X_te)


def _fit_hgb_clf(X_tr: np.ndarray, y_tr: np.ndarray, X_te: np.ndarray) -> np.ndarray:
    from sklearn.ensemble import HistGradientBoostingClassifier

    clf = HistGradientBoostingClassifier(random_state=0)
    clf.fit(X_tr, y_tr)
    return clf.predict(X_te)


def _fit_en(X_tr: np.ndarray, y_tr: np.ndarray, X_te: np.ndarray) -> np.ndarray:
    from sklearn.linear_model import ElasticNetCV

    reg = ElasticNetCV(l1_ratio=[0.1, 0.5, 0.9], cv=5, random_state=0)
    reg.fit(X_tr, y_tr)
    return reg.predict(X_te)


def _fit_hgb_reg(X_tr: np.ndarray, y_tr: np.ndarray, X_te: np.ndarray) -> np.ndarray:
    from sklearn.ensemble import HistGradientBoostingRegressor

    reg = HistGradientBoostingRegressor(random_state=0)
    reg.fit(X_tr, y_tr)
    return reg.predict(X_te)


def _safe_rho(pred: np.ndarray, gold: np.ndarray) -> float | None:
    if np.std(pred) == 0 or np.std(gold) == 0:
        return None
    from scipy.stats import spearmanr

    r = spearmanr(pred, gold).statistic
    return None if r is None or np.isnan(r) else float(r)
