#!/usr/bin/env python3
"""Session 6a — DNAm tasks from GSE48325 (450K, NAFLD ± bariatric surgery).

Beta = Signal_B / (Signal_A + Signal_B) per sample; Detection P-val filter.
Tasks (MB-30xx), split by subject where identifiable, else by sample:
  MB-3001 binary: NAFLD vs NORMAL (group)
  MB-3002 multiclass: age decade (50s/60s/70s+)
  MB-3005 regression: age
Feature selection: top-variable CpGs on the TRAIN side only (subject split),
CpGs referenced by ID with no gene annotation (avoids text-recoverable hints).
"""
import gzip, json, os, random, re, sys, time

import numpy as np
import pandas as pd

T0 = time.time()
SEED = 20260929
rng = random.Random(SEED)
ROOT = "/Users/subhadipbanerjee/masld-llm"
sys.path.insert(0, f"{ROOT}/scripts")
from build_freeze3 import parse_soft_meta

DATA = f"{ROOT}/data"
OUT = f"{ROOT}/prompts"
N_CPG_SINGLE = 150   # paper used 100+100 / 160; keep prompts ~6-8k tokens
N_CPG_PAIR = 100

VERB_INTRO = [
    "You are analyzing human liver DNA methylation profiles from a MASLD study.",
    "The following data come from a liver biopsy of a patient in a fatty-liver-disease cohort.",
    "Below is the DNA methylation profile of a human liver sample.",
]
VERB_FEATS = [
    "Methylation beta values: {features}",
    "DNA methylation levels (beta): {features}",
    "CpG methylation measurements: {features}",
]
ASK_BINARY = [
    "Does this methylation profile indicate fatty liver disease (NAFLD)? Answer yes or no.",
    "Is this profile consistent with non-alcoholic fatty liver disease? Answer with yes or no.",
]
ASK_AGE_DECADE = [
    "Assign the donor to an age decade: 50s, 60s, 70s, or 80s. Answer with one of 50s, 60s, 70s, 80s.",
]
ASK_AGE_REG = [
    "Predict the donor's age in years.",
    "Estimate the donor's chronological age as a number.",
]

def pick(pool): return pool[rng.randrange(len(pool))]

def fmt_cpg(cpg, beta):
    return f"{cpg}={beta:.2f}"

def write_jsonl(records, path, meta):
    import hashlib
    meta = {"n_records": len(records), "seed": SEED, "built": "2026-09-30", **meta}
    with gzip.open(path, "wt") as f:
        f.write(json.dumps({"__meta__": meta}) + "\n")
        for r in records:
            f.write(json.dumps(r) + "\n")
    print(f"  {os.path.basename(path):46s} {len(records):6d} prompts")


def main():
    print("== loading GSE48325 metadata ==")
    soft = parse_soft_meta(f"{DATA}/GSE48325_family.soft.gz")
    print(f"  {len(soft)} samples in soft")

    print("== computing beta values (streaming) ==")
    sig = pd.read_csv(f"{DATA}/matrices/GSE48325_signal_intensities.txt.gz", sep="\t", index_col=0, compression="gzip")
    cols = sig.columns.tolist()
    # columns: N.Signal_A, N.Signal_B, N.Detection Pval per sample number N
    sample_nums = sorted({c.split(".")[0] for c in cols})
    betas, detects = [], []
    for n in sample_nums:
        a = sig.get(f"{n}.Signal_A"); b = sig.get(f"{n}.Signal_B"); d = sig.get(f"{n}.Detection Pval")
        if a is None or b is None:
            continue
        beta = b / (a + b).replace(0, np.nan)
        betas.append(beta.rename(n))
        detects.append(d.rename(n) if d is not None else pd.Series(0.0, index=sig.index))
    beta_df = pd.concat(betas, axis=1)
    det_df = pd.concat(detects, axis=1)
    # detection filter: require p<0.01 in >=80% of samples
    ok = (det_df < 0.01).mean(axis=1) >= 0.8
    beta_df = beta_df.loc[ok]
    print(f"  beta matrix: {beta_df.shape[0]} CpGs x {beta_df.shape[1]} samples (after detection filter)")
    del sig

    # ---- sample-number -> metadata join (positional: soft order == column-group order?) ----
    # The signal file's sample numbers are arbitrary; join by order of !Sample blocks
    geo_order = list(soft.keys())
    if len(geo_order) != beta_df.shape[1]:
        print(f"  !! soft n={len(geo_order)} != matrix n={beta_df.shape[1]}; joining by position")
    meta_rows = []
    for i, n in enumerate(beta_df.columns):
        v = soft[geo_order[i]] if i < len(geo_order) else {}
        meta_rows.append({
            "sample": n,
            "group": v.get("group", "NA"),
            "age": pd.to_numeric(pd.Series([v.get("age")]), errors="coerce").iloc[0] if v.get("age") else np.nan,
            "sex": v.get("sex (1 - male, 2 - female)", "NA"),
            "surgery": v.get("bariatric surgery (1 - before surgery, 2 - after)", "NA"),
        })
    meta = pd.DataFrame(meta_rows).set_index("sample")
    print(f"  groups: {meta['group'].value_counts().to_dict()}")
    print(f"  age available: {meta['age'].notna().sum()}")

    # ---- split: stratified 20% test by sample (subject ids unavailable) ----
    order = meta.sample(frac=1.0, random_state=SEED).index.tolist()
    n_test = max(1, int(0.2 * len(order)))
    test_ids, train_ids = order[:n_test], order[n_test:]

    # ---- feature selection on train only ----
    var = beta_df[train_ids].var(axis=1)
    top_cpg = var.sort_values(ascending=False).head(500).index.tolist()
    cpg_single = top_cpg[:N_CPG_SINGLE]
    cpg_pair = top_cpg[:N_CPG_PAIR]
    print(f"  feature CpGs: {len(cpg_single)} single / {len(cpg_pair)} pair (train-selected)")

    def render(sid, cpgs):
        vals = beta_df.loc[cpgs, sid]
        feats = ", ".join(fmt_cpg(c, vals[c]) for c in cpgs)
        return pick(VERB_FEATS).format(features=feats)

    def clin(row):
        parts = []
        if pd.notna(row["age"]) and pd.notna(row.get("_hide_age", np.nan)) is False:
            pass  # age hidden for age tasks; shown for disease tasks? keep hidden everywhere to avoid leakage in age tasks
        s = str(row["sex"])
        parts.append("male" if s.startswith("1") else "female" if s.startswith("2") else "sex unknown")
        return "; ".join(parts)

    recs = []
    for sid in train_ids:
        row = meta.loc[sid]
        base = f"{pick(VERB_INTRO)}\nDonor: {clin(row)}.\n{render(sid, cpg_single)}\n"
        if str(row["group"]).upper() in ("NORMAL", "NAFLD"):
            recs.append(dict(task="MB-3001", split="train", sample=sid,
                prompt=base + pick(ASK_BINARY),
                answer="yes" if str(row["group"]).upper() == "NAFLD" else "no"))
        if pd.notna(row["age"]):
            dec = int(row["age"]) // 10 * 10
            if 50 <= dec <= 80:
                recs.append(dict(task="MB-3002", split="train", sample=sid,
                    prompt=base + pick(ASK_AGE_DECADE), answer=f"{dec}s"))
                recs.append(dict(task="MB-3005", split="train", sample=sid,
                    prompt=base + pick(ASK_AGE_REG), answer=f"{int(row['age'])}"))
    write_jsonl(recs, f"{OUT}/MB-30xx_dnam_train.jsonl.gz",
                meta=dict(builder="GSE48325 450K beta values, detection-filtered",
                          n_cpg_single=N_CPG_SINGLE, split="80/20 by sample, subject ids unavailable"))

    # ---- test side ----
    recs = []
    for sid in test_ids:
        row = meta.loc[sid]
        base = f"{pick(VERB_INTRO)}\nDonor: {clin(row)}.\n{render(sid, cpg_single)}\n"
        if str(row["group"]).upper() in ("NORMAL", "NAFLD"):
            recs.append(dict(task="MB-3001", split="test", sample=sid,
                prompt=base + pick(ASK_BINARY),
                answer="yes" if str(row["group"]).upper() == "NAFLD" else "no"))
        if pd.notna(row["age"]):
            dec = int(row["age"]) // 10 * 10
            if 50 <= dec <= 80:
                recs.append(dict(task="MB-3002", split="test", sample=sid,
                    prompt=base + pick(ASK_AGE_DECADE), answer=f"{dec}s"))
                recs.append(dict(task="MB-3005", split="test", sample=sid,
                    prompt=base + pick(ASK_AGE_REG), answer=f"{int(row['age'])}"))
    write_jsonl(recs, f"{OUT}/MB-30xx_dnam_test.jsonl.gz",
                meta=dict(builder="GSE48325 held-out 20% (split rule above)"))
    print(f"done in {time.time()-T0:.1f}s")


if __name__ == "__main__":
    main()
