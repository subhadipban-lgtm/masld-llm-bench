#!/usr/bin/env python3
"""Score archived frontier runs -> results/leaderboard.csv (per ANALYSIS_PLAN_v1).

Usage: python3 score_frontier.py
Reads results/frontier_runs/*.jsonl.gz, computes per-task metrics with
bootstrap 95% CIs, and appends rows to results/leaderboard.csv.
"""
import glob, gzip, json, os, random, sys

import numpy as np
import pandas as pd

ROOT = "/Users/subhadipbanerjee/masld-llm"
RUNS = f"{ROOT}/results/frontier_runs"
OUT = f"{ROOT}/results/leaderboard.csv"
SEED = 20260929

def bootstrap_ci(vals, n=10000):
    rng = np.random.default_rng(SEED)
    vals = np.asarray(vals, dtype=float)
    if len(vals) == 0:
        return (None, None)
    idx = rng.integers(0, len(vals), size=(n, len(vals)))
    means = vals[idx].mean(axis=1)
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))

def score_run(path):
    rows = []
    with gzip.open(path, "rt") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    if not rows:
        return []
    df = pd.DataFrame(rows)
    out = []
    for task, g in df.groupby("task"):
        valid = g["parsed"].notna() if "parsed" in g else pd.Series(False, index=g.index)
        n = len(g)
        validity = float(valid.mean())
        ans = g["answer"].astype(str)
        par = g["parsed"].astype(str)
        if ans.iloc[0] in ("A", "B") or ans.iloc[0] in ("yes", "no"):
            correct = (par == ans).astype(float)  # invalid-as-error
            acc = float(correct.mean())
            lo, hi = bootstrap_ci(correct)
            out.append(dict(task=task, n=n, metric="accuracy", value=acc,
                            ci_lo=lo, ci_hi=hi, validity=validity))
        elif ans.iloc[0].startswith("F"):
            correct = (par == ans).astype(float)
            acc = float(correct.mean())
            lo, hi = bootstrap_ci(correct)
            out.append(dict(task=task, n=n, metric="accuracy", value=acc,
                            ci_lo=lo, ci_hi=hi, validity=validity))
        else:
            num = pd.to_numeric(g["parsed"], errors="coerce")
            ref = pd.to_numeric(g["answer"], errors="coerce")
            ok = num.notna()
            if ok.sum() == 0:
                out.append(dict(task=task, n=n, metric="mae", value=None,
                                ci_lo=None, ci_hi=None, validity=validity))
                continue
            from scipy.stats import spearmanr
            mae = float(np.abs(num[ok] - ref[ok]).mean())
            errs = np.abs(num[ok] - ref[ok]).values
            lo, hi = bootstrap_ci(errs)
            rho = float(spearmanr(ref[ok], num[ok]).statistic) if len(set(ref[ok])) > 1 else None
            out.append(dict(task=task, n=n, metric="mae", value=mae,
                            ci_lo=lo, ci_hi=hi, validity=validity, spearman=rho))
    model = os.path.basename(path).split("__")[0]
    for r in out:
        r["model"] = model
    return out

def main():
    all_rows = []
    for path in sorted(glob.glob(f"{RUNS}/*.jsonl.gz")):
        all_rows += score_run(path)
    if not all_rows:
        print("no runs found; execute session3_frontier.py first (needs OPENROUTER_API_KEY)")
        return
    df = pd.DataFrame(all_rows)[["model", "task", "n", "metric", "value", "ci_lo", "ci_hi",
                                  "validity", "spearman"] if "spearman" in all_rows[0]
                                else ["model", "task", "n", "metric", "value", "ci_lo", "ci_hi", "validity"]]
    df.to_csv(OUT, index=False)
    print(df.to_string(index=False))
    print(f"\n-> {OUT}")

if __name__ == "__main__":
    main()
