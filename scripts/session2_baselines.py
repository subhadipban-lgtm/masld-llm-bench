#!/usr/bin/env python3
"""Session 2 — ML baselines on the FROZEN test (EPos + Gubra).

Trains fibrosis 'clocks' on the exact features each prompt exposes,
evaluates on the identical frozen test items — the paper's paired-comparison
rule. Produces results/baselines.json.

Models: ElasticNet (linear) + HistGradientBoosting (nonlinear) per format:
  binary (F3-F4), multiclass (F0-F4), regression (stage 0-4)
plus a majority-class reference and a clinical-only variant (no genes).
"""
import gzip, json, os, re, sys, time

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import ElasticNetCV, LogisticRegression

T0 = time.time()
ROOT = "/Users/subhadipbanerjee/masld-llm"
PROMPTS = f"{ROOT}/prompts"
RESULTS = f"{ROOT}/results"
os.makedirs(RESULTS, exist_ok=True)

SEED = 20260929

# scikit-learn in the venv?
try:
    import sklearn
    print("sklearn", sklearn.__version__)
except ImportError:
    sys.exit("sklearn missing")


def load_jsonl(path):
    with gzip.open(path, "rt") as f:
        first = json.loads(f.readline())
        rows = [json.loads(l) for l in f] if "__meta__" in first else [first] + [json.loads(l) for l in f]
    return rows


FEAT_RE = re.compile(r"([A-Za-z0-9_.\-]+)=(-?[0-9]+\.?[0-9]*)")

def parse_features(prompt):
    return {m.group(1): float(m.group(2)) for m in FEAT_RE.finditer(prompt)}


def parse_clinical(prompt):
    """age/sex/diabetes from the 'Patient:' line."""
    m = re.search(r"Patient:\s*([^\n]+)\.", prompt)
    if not m:
        return {}
    block = m.group(1)
    out = {}
    if "age " in block:
        am = re.search(r"age (\d+)", block)
        if am: out["age"] = float(am.group(1))
    out["is_female"] = 1.0 if "female" in block else 0.0
    out["t2dm"] = 1.0 if "type-2 diabetes" in block and "no type-2" not in block else 0.0
    return out


def build_xy(rows, feature_mode="genes"):
    X, y_binary, y_multi, y_reg = [], [], [], []
    for r in rows:
        feats = parse_features(r["prompt"])
        clin = parse_clinical(r["prompt"])
        if feature_mode == "genes":
            X.append(feats)
        else:
            X.append(clin)
        ans = r["answer"]
        if ans in ("yes", "no"):
            y_binary.append(1 if ans == "yes" else 0)
            y_multi.append(None); y_reg.append(None)
        elif ans in ("A", "B"):
            y_binary.append(None); y_multi.append(None); y_reg.append(None)
        elif ans.startswith("F"):
            y_binary.append(None); y_multi.append(ans); y_reg.append(None)
        else:
            try:
                v = float(ans)
                y_binary.append(None); y_multi.append(None); y_reg.append(v)
            except ValueError:
                y_binary.append(None); y_multi.append(None); y_reg.append(None)
    return X, y_binary, y_multi, y_reg


def vectorise(X_dicts):
    allf = sorted({k for d in X_dicts for k in d})
    ix = {f: i for i, f in enumerate(allf)}
    M = np.zeros((len(X_dicts), len(allf)))
    for r, d in enumerate(X_dicts):
        for k, v in d.items():
            M[r, ix[k]] = v
    return M, allf


def main():
    print("== loading frozen test ==")
    test_rows = [r for r in load_jsonl(f"{PROMPTS}/MB-20xx_liver_test.jsonl.gz")]
    print(f"  {len(test_rows)} test prompts")
    print("== loading train pool (Kamzolas + external) ==")
    train_rows = load_jsonl(f"{PROMPTS}/MB-10xx_liver_train.jsonl.gz")
    train_rows += load_jsonl(f"{PROMPTS}/MB-11xx_external_train.jsonl.gz")
    # keep only single-profile tasks with gene features and usable answers
    def usable(r):
        return r["task"] in ("MB-1001","MB-1002","MB-1005","MB-1006","MB-11001","MB-11002","MB-11005","MB-11006")
    train_rows = [r for r in train_rows if usable(r)]
    test_rows = [r for r in test_rows if r["task"] in ("MB-2001","MB-2002","MB-2005","MB-2006")]
    print(f"  train {len(train_rows)} | test {len(test_rows)} single-profile prompts")

    results = {"meta": {"date": "2026-09-29", "seed": SEED,
                        "rule": "trained on prompt-exposed features only; evaluated on identical frozen items"}}

    for feature_mode in ("genes", "clinical"):
        Xtr_d, ytr_b, ytr_m, ytr_r = build_xy(train_rows, feature_mode)
        Xte_d, yte_b, yte_m, yte_r = build_xy(test_rows, feature_mode)
        # NOTE: feature spaces differ per cohort (probe IDs vs Ensembl) — build on union, zero-fill
        Xtr, feats = vectorise(Xtr_d)
        ix = {f: i for i, f in enumerate(feats)}
        Xte = np.zeros((len(Xte_d), len(feats)))
        for r, d in enumerate(Xte_d):
            for k, v in d.items():
                if k in ix: Xte[r, ix[k]] = v

        tag = "gene_features" if feature_mode == "genes" else "clinical_only"
        results[tag] = {}

        # ---- binary: advanced fibrosis ----
        tr_mask = np.array([y is not None for y in ytr_b]); te_mask = np.array([y is not None for y in yte_b])
        if tr_mask.sum() > 10 and te_mask.sum() > 0:
            ytr = np.array([y for y in ytr_b if y is not None]); yte = np.array([y for y in yte_b if y is not None])
            # majority reference
            maj = pd.Series(ytr).value_counts().index[0]
            maj_acc = float((yte == maj).mean())
            # elastic-net logistic
            lr = LogisticRegression(max_iter=2000, C=1.0).fit(Xtr[tr_mask], ytr)
            lr_acc = float(lr.score(Xte[te_mask], yte))
            # HGB
            hgb = HistGradientBoostingClassifier(random_state=SEED).fit(Xtr[tr_mask], ytr)
            hgb_acc = float(hgb.score(Xte[te_mask], yte))
            results[tag]["binary_advanced_fibrosis"] = {
                "n_train": int(tr_mask.sum()), "n_test": int(te_mask.sum()),
                "majority_acc": maj_acc, "elasticnet_logreg_acc": lr_acc, "hgb_acc": hgb_acc}
            print(f"  [{tag}] binary: maj={maj_acc:.3f} EN={lr_acc:.3f} HGB={hgb_acc:.3f} (n_test={te_mask.sum()})")

        # ---- multiclass F0-F4 ----
        tr_mask = np.array([y is not None for y in ytr_m]); te_mask = np.array([y is not None for y in yte_m])
        if tr_mask.sum() > 10 and te_mask.sum() > 0:
            ytr = np.array([y for y in ytr_m if y is not None]); yte = np.array([y for y in yte_m if y is not None])
            maj = pd.Series(ytr).value_counts().index[0]
            maj_acc = float((yte == maj).mean())
            lr = LogisticRegression(max_iter=2000, C=1.0).fit(Xtr[tr_mask], ytr)
            lr_acc = float(lr.score(Xte[te_mask], yte))
            hgb = HistGradientBoostingClassifier(random_state=SEED).fit(Xtr[tr_mask], ytr)
            hgb_acc = float(hgb.score(Xte[te_mask], yte))
            results[tag]["multiclass_F0_F4"] = {
                "n_train": int(tr_mask.sum()), "n_test": int(te_mask.sum()),
                "majority_acc": maj_acc, "elasticnet_logreg_acc": lr_acc, "hgb_acc": hgb_acc}
            print(f"  [{tag}] multiclass: maj={maj_acc:.3f} EN={lr_acc:.3f} HGB={hgb_acc:.3f} (n_test={te_mask.sum()})")

        # ---- regression 0-4 ----
        tr_mask = np.array([y is not None for y in ytr_r]); te_mask = np.array([y is not None for y in yte_r])
        if tr_mask.sum() > 10 and te_mask.sum() > 0:
            ytr = np.array([y for y in ytr_r if y is not None]); yte = np.array([y for y in yte_r if y is not None])
            from sklearn.metrics import mean_absolute_error
            from scipy.stats import spearmanr
            base_mae = mean_absolute_error(yte, np.full_like(yte, np.median(ytr)))
            en = ElasticNetCV(l1_ratio=[.1,.5,.9], cv=5, random_state=SEED).fit(Xtr[tr_mask], ytr)
            pred = en.predict(Xte[te_mask])
            en_mae = float(mean_absolute_error(yte, pred))
            en_rho = float(spearmanr(yte, pred).statistic) if len(set(yte)) > 1 else None
            hgb = HistGradientBoostingRegressor(random_state=SEED).fit(Xtr[tr_mask], ytr)
            pred2 = hgb.predict(Xte[te_mask])
            hgb_mae = float(mean_absolute_error(yte, pred2))
            hgb_rho = float(spearmanr(yte, pred2).statistic) if len(set(yte)) > 1 else None
            results[tag]["regression_stage_0_4"] = {
                "n_train": int(tr_mask.sum()), "n_test": int(te_mask.sum()),
                "median_mae": float(base_mae), "elasticnet_mae": en_mae, "elasticnet_spearman": en_rho,
                "hgb_mae": hgb_mae, "hgb_spearman": hgb_rho}
            print(f"  [{tag}] regression: med={base_mae:.3f} EN={en_mae:.3f}(rho={en_rho:.3f}) HGB={hgb_mae:.3f}(rho={hgb_rho:.3f})")

    json.dump(results, open(f"{RESULTS}/baselines.json", "w"), indent=1)
    print(f"== wrote {RESULTS}/baselines.json in {time.time()-T0:.1f}s ==")


if __name__ == "__main__":
    main()
