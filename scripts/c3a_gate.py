#!/usr/bin/env python3
"""C3a novelty gate (frozen contract: analysis-plan/ANALYSIS_PLAN_C3_addendum.md §3).

MB-86xx blood-proxy is a NEW frozen test with NO train corpus, so the honest
protocol is grouped cross-validation by patient (never split a patient across
folds). Gate: does ANY model family beat chance/majority with a CI that
excludes it, on ANY 86xx task?  Seed 20260929 (program seed).
"""
import gzip, json, sys
from collections import defaultdict
import numpy as np

sys.path.insert(0, "/Users/subhadipbanerjee/masld-llm/platform/core")
from masld_platform.features import encode_prompt, vectorise
from masld_platform.answers import gold_value
from masld_platform.tasks import resolve_task_type
from masld_platform.schemas import PromptRecord, TaskType

CORPUS = "/Users/subhadipbanerjee/masld-llm/prompts/MB-86xx_bloodproxy_test.jsonl.gz"
SEED = 20260929
N_FOLDS = 5
N_BOOT = 2000

def load():
    recs = [json.loads(l) for l in gzip.open(CORPUS, "rt").read().splitlines()]
    return [PromptRecord.model_validate(r) for r in recs if "task" in r]

def fit_logreg(Xtr, ytr, Xte):
    from sklearn.linear_model import LogisticRegression
    return LogisticRegression(max_iter=2000, C=1.0).fit(Xtr, ytr).predict(Xte)

def fit_hgb(Xtr, ytr, Xte, classification=True):
    if classification:
        from sklearn.ensemble import HistGradientBoostingClassifier as M
    else:
        from sklearn.ensemble import HistGradientBoostingRegressor as M
    return M(random_state=SEED).fit(Xtr, ytr).predict(Xte)

def stratified_group_folds(records, y):
    """Return list of (train_idx, test_idx), grouped by patient (stratified-ish)."""
    from sklearn.model_selection import StratifiedGroupKFold
    groups = [r.sample for r in records]
    sgkf = StratifiedGroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    return list(sgkf.split(np.zeros(len(records)), y, groups))

def cv_task(records, task, kind):
    recs = [r for r in records if r.task == task]
    at = resolve_task_type(task, recs)
    feats = [encode_prompt(r.prompt, mode="genes") for r in recs]
    X_all, cols = vectorise(feats)
    X_all = np.array(X_all)
    if kind == "binary":
        y = np.array([1 if gold_value(r.answer, at) == "yes" else 0 for r in recs])
        metric = "accuracy"
    elif kind == "multi":
        y = np.array([at.tokens.index(str(gold_value(r.answer, at))) for r in recs])
        metric = "accuracy"
    else:
        y = np.array([float(gold_value(r.answer, at)) for r in recs]); metric = "mae"

    folds = stratified_group_folds(recs, y)
    models = {"logreg": [], "hgb": []}
    for tr, te in folds:
        if kind == "reg":
            models["logreg"].append((te, fit_hgb(X_all[tr], y[tr], X_all[te], classification=False)))
            models["hgb"].append((te, fit_hgb(X_all[tr], y[tr], X_all[te], classification=False)))
        else:
            models["logreg"].append((te, fit_logreg(X_all[tr], y[tr], X_all[te])))
            models["hgb"].append((te, fit_hgb(X_all[tr], y[tr], X_all[te], classification=True)))
    return recs, y, models, metric, at

def bootstrap_ci(y_true, y_pred, metric, n_boot=N_BOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    n = len(y_true)
    def score(yt, yp):
        if metric == "accuracy": return float(np.mean(yp == yt))
        return float(np.mean(np.abs(yp - yt)))
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        vals.append(score(y_true[idx], y_pred[idx]))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))

def main():
    records = load()
    print(f"MB-86xx: {len(records)} records; "
          f"patients={len(set(r.sample for r in records))}\n")
    specs = [("MB-8601", "multi", "severity 3-class"),
             ("MB-8602", "binary", "low-vs-high binary"),
             ("MB-8605", "reg", "ordinal score regression")]
    report = {}
    any_win = False
    for task, kind, label in specs:
        recs, y, models, metric, at = cv_task(records, task, kind)
        print(f"=== {task} ({label})  n={len(recs)}  metric={metric} ===")
        majority = float(np.bincount(y).max()/len(y)) if kind != "reg" else None
        med = float(np.median(y))
        entry = {"task": task, "n": len(recs), "metric": metric}
        if kind != "reg":
            print(f"  majority baseline acc = {majority:.3f}")
        else:
            print(f"  median baseline MAE   = {np.mean(np.abs(np.full_like(y, med, dtype=float)-y)):.3f}")
        for name, preds in models.items():
            y_pred = np.empty_like(y, dtype=float)
            for te, p in preds:
                y_pred[te] = p
            if metric == "accuracy":
                acc = float(np.mean(y_pred == y)); lo, hi = bootstrap_ci(y, y_pred, "accuracy")
                print(f"  {name:7s} acc={acc:.3f}  95%CI[{lo:.3f},{hi:.3f}]  (chance={1/ (len(at.tokens) if kind=='multi' else 2):.3f})")
                chance = 1.0 / (len(at.tokens) if kind == "multi" else 2)
                beats_chance = lo > chance
                beats_majority = lo > majority
                print(f"           chance={chance:.3f}  beats_chance={beats_chance}  beats_majority={beats_majority}")
                beats = beats_chance or beats_majority
                entry[name] = {"acc": acc, "ci": [lo, hi], "chance": chance,
                               "beats_chance": bool(beats_chance), "beats_majority": bool(beats_majority)}
            else:
                mae = float(np.mean(np.abs(y_pred - y))); lo, hi = bootstrap_ci(y, y_pred, "mae")
                print(f"  {name:7s} MAE={mae:.3f}  95%CI[{lo:.3f},{hi:.3f}]  (median MAE={np.mean(np.abs(np.full_like(y, med, dtype=float)-y)):.3f})")
                med_mae = float(np.mean(np.abs(np.full_like(y, med, dtype=float) - y)))
                beats = hi < med_mae
                n_at_chance = 1.0/((len(at.tokens)-1))**0.5 if at.tokens else 0.0
                print(f"           beats_median={beats} (median MAE={med_mae:.3f})")
                entry[name] = {"mae": mae, "ci": [lo, hi], "median_mae": med_mae, "beats_median": bool(beats)}
            any_win = any_win or beats
        print()
        report[task] = entry
    report["_gate"] = {"any_family_beats_chance_or_majority": bool(any_win),
                       "seed": SEED, "protocol": f"StratifiedGroupKFold(n={N_FOLDS}) by patient; {N_BOOT} bootstraps"}
    out = "/Users/subhadipbanerjee/masld-llm/results/c3a_gate.json"
    json.dump(report, open(out, "w"), indent=2)
    print(f"GATE: {'PASS - C3 claim lives' if any_win else 'FAIL - no family beats chance/majority'}")
    print(f"written -> {out}")

if __name__ == "__main__":
    main()
