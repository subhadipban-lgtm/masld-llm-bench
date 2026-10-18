#!/usr/bin/env python3
"""C3a novelty gate for the MB-85xx (progression) and MB-87xx (liver->plasma)
frozen tests — same frozen contract as c3a_gate.py (ANALYSIS_PLAN_C3_addendum
§3): grouped CV by sample, 2000 bootstraps, seed 20260929.

Gate question per family: does ANY model family (logreg / HGB) beat
chance/majority (accuracy) or the median-constant (MAE) with a CI excluding
it, on ANY task?

Expected caveats coded into the report:
- MB-8701 (platform 3-class) measures BATCH separation across three
  quantification tables; a ~1.0 pass is a batch-effect readout, not a
  clinical claim.
- MB-8705 as built (freeze-10) has all-identical golds (saturated log10
  transform) -> median-constant MAE = 0, nothing can beat it; reported as
  DEGENERATE unless the corpus was rebuilt (freeze-11 masked-protein
  target).
"""
import gzip, json, sys
from collections import Counter

import numpy as np

sys.path.insert(0, "/Users/subhadipbanerjee/masld-llm/platform/core")
from masld_platform.features import encode_prompt, vectorise
from masld_platform.answers import gold_value
from masld_platform.tasks import resolve_task_type
from masld_platform.schemas import PromptRecord

PROMPTS = "/Users/subhadipbanerjee/masld-llm/prompts"
SEED = 20260929
N_FOLDS = 5
N_BOOT = 2000

CORPORA = [
    ("MB-85xx", "MB-85xx_progression_test.jsonl.gz", [
        ("MB-8501", "multi", "stable-vs-progressive binary"),
        ("MB-8505", "reg", "ordinal progression 1-2"),
    ]),
    ("MB-87xx", "MB-87xx_liverplasma_test.jsonl.gz", [
        ("MB-8701", "multi", "platform 3-class (batch readout caveat)"),
        ("MB-8705", "reg", "protein level (check degeneracy)"),
    ]),
    ("MB-88xx", "MB-88xx_perturb_test.jsonl.gz", [
        ("MB-8801", "binary", "PHH FFA perturbation yes/no (grouped by donor)"),
    ]),
]


def load(path):
    recs = [json.loads(l) for l in gzip.open(path, "rt").read().splitlines()]
    return [PromptRecord.model_validate(r) for r in recs if "task" in r]


def fit_logreg(Xtr, ytr, Xte):
    from sklearn.linear_model import LogisticRegression
    return LogisticRegression(max_iter=2000, C=1.0).fit(Xtr, ytr).predict(Xte)


def fit_hgb_cls(Xtr, ytr, Xte):
    from sklearn.ensemble import HistGradientBoostingClassifier as M
    return M(random_state=SEED).fit(Xtr, ytr).predict(Xte)


def fit_hgb_reg(Xtr, ytr, Xte):
    from sklearn.ensemble import HistGradientBoostingRegressor as M
    return M(random_state=SEED).fit(Xtr, ytr).predict(Xte)


def grouped_folds(samples, y, stratify=True):
    if stratify:
        from sklearn.model_selection import StratifiedGroupKFold
        sgkf = StratifiedGroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
        return list(sgkf.split(np.zeros(len(y)), y, samples))
    from sklearn.model_selection import GroupKFold
    return list(GroupKFold(n_splits=N_FOLDS).split(np.zeros(len(y)), y, samples))


def bootstrap_ci(y, p, metric, n_boot=N_BOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    n = len(y)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        vals.append(float(np.mean(p[idx] == y[idx])) if metric == "accuracy"
                    else float(np.mean(np.abs(p[idx] - y[idx]))))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def main():
    report, any_win, notes = {}, False, []
    for tag, fname, specs in CORPORA:
        records = load(f"{PROMPTS}/{fname}")
        print(f"=== {tag}: {len(records)} records | "
              f"samples={len(set(r.sample for r in records))} ===")
        for task, kind, label in specs:
            recs = [r for r in records if r.task == task]
            at = resolve_task_type(task, recs)
            X, cols = vectorise([encode_prompt(r.prompt, mode="genes") for r in recs])
            X = np.array(X)
            samples = [r.sample for r in recs]
            if kind == "multi":
                y = np.array([at.tokens.index(str(gold_value(r.answer, at))) for r in recs])
                majority = float(np.bincount(y).max() / len(y))
                chance = 1.0 / len(at.tokens)
            elif kind == "binary":
                y = np.array([1 if gold_value(r.answer, at) == "yes" else 0 for r in recs])
                majority = float(np.bincount(y).max() / len(y))
                chance = 0.5
            else:
                y = np.array([float(gold_value(r.answer, at)) for r in recs])
                majority, chance = None, None
            degenerate = len(set(y.tolist())) == 1
            med = float(np.median(y))
            med_mae = float(np.mean(np.abs(np.full_like(y, med, dtype=float) - y)))
            entry = {"task": task, "n": len(recs), "features": len(cols),
                     "metric": "accuracy" if kind == "multi" else "mae"}
            print(f"  {task} ({label}) n={len(recs)} feats={len(cols)}"
                  + (f" majority={majority:.3f} chance={chance:.3f}"
                     if kind != "reg" else f" median-MAE={med_mae:.3f}"))
            if degenerate:
                print("    DEGENERATE: all golds identical -> unpassable by design")
                entry["degenerate"] = True
                notes.append(f"{task}: degenerate target (all golds {y[0]}); "
                             "rebuild needed (freeze-11)")
                report[task] = entry
                continue
            preds = {m: np.empty_like(y, dtype=float) for m in ("logreg", "hgb")}
            for tr, te in grouped_folds(samples, y, stratify=(kind != "reg")):
                if kind != "reg":
                    preds["logreg"][te] = fit_logreg(X[tr], y[tr], X[te])
                    preds["hgb"][te] = fit_hgb_cls(X[tr], y[tr], X[te])
                else:
                    preds["logreg"][te] = fit_hgb_reg(X[tr], y[tr], X[te])
                    preds["hgb"][te] = fit_hgb_reg(X[tr], y[tr], X[te])
            for m, p in preds.items():
                if kind != "reg":
                    v = float(np.mean(p == y))
                    lo, hi = bootstrap_ci(y, p, "accuracy")
                    beats = lo > max(chance, majority)
                    print(f"    {m:7s} acc={v:.3f} CI[{lo:.3f},{hi:.3f}] "
                          f"beats_chance_or_majority={beats}")
                    entry[m] = {"acc": v, "ci": [lo, hi], "majority": majority,
                                "chance": chance, "beats": bool(beats)}
                else:
                    v = float(np.mean(np.abs(p - y)))
                    lo, hi = bootstrap_ci(y, p, "mae")
                    beats = hi < med_mae
                    print(f"    {m:7s} MAE={v:.3f} CI[{lo:.3f},{hi:.3f}] "
                          f"beats_median={beats} (median-MAE={med_mae:.3f})")
                    entry[m] = {"mae": v, "ci": [lo, hi], "median_mae": med_mae,
                                "beats": bool(beats)}
                any_win = any_win or beats
            report[task] = entry
        print()
    if report.get("MB-8701", {}).get("logreg", {}).get("acc", 0) > 0.95:
        notes.append("MB-8701 near-ceiling = batch/platform separation, NOT clinical signal")
    report["_gate"] = {"any_family_beats_chance_majority_or_median": bool(any_win),
                       "seed": SEED,
                       "protocol": f"StratifiedGroupKFold(n={N_FOLDS}) by sample; {N_BOOT} bootstraps",
                       "notes": notes}
    out = "/Users/subhadipbanerjee/masld-llm/results/c3a_gate_85_87.json"
    json.dump(report, open(out, "w"), indent=2)
    print(f"GATE: {'PASS' if any_win else 'FAIL'} | notes: {notes}")
    print(f"written -> {out}")


if __name__ == "__main__":
    main()
