#!/usr/bin/env python3
"""Session 6b — Fujiwara KU series as internal test (MB-9xxx).

KU (n=56) was held out of MB-8xxx training; this builds its test prompts
with identical builders/verbalizations so KU joins EPos+Gubra as an
internal-validation cohort (cohort-shift robustness check).
"""
import gzip, json, os, re, sys, time

import numpy as np
import pandas as pd

T0 = time.time()
SEED = 20260930
rng = None
import random as _random
rng = _random.Random(SEED)
ROOT = "/Users/subhadipbanerjee/masld-llm"
sys.path.insert(0, f"{ROOT}/scripts")
from build_mb10xx import (VERBALIZATIONS, pick, write_jsonl, top_genes,
                          clinical_block, render_profile, standardize_sample)

REV = "/Users/subhadipbanerjee/masld-revision"
OUT = f"{ROOT}/prompts"


def main():
    fmeta = pd.read_csv(f"{REV}/data/metadata_with_ferroptosis_scores.csv", index_col=0)

    def parse_char(s, key):
        m = re.search(key + r"\s*:\s*(.+)$", str(s))
        return m.group(1).strip() if m else None

    fuji = pd.DataFrame({
        "sample": fmeta["title"],
        "series": fmeta["title"].str[:2],
        "age": pd.to_numeric(fmeta["characteristics_ch1.1"].map(lambda s: parse_char(s, "age")), errors="coerce"),
        "sex": fmeta["characteristics_ch1.2"].map(lambda s: parse_char(s, "Sex")),
        "fibrosis": pd.to_numeric(fmeta["characteristics_ch1.3"].map(lambda s: parse_char(s, "fibrosis stage")), errors="coerce"),
        "nas": pd.to_numeric(fmeta["characteristics_ch1.4"].map(lambda s: parse_char(s, "nafld activity score")), errors="coerce"),
    })
    emat = pd.read_csv(f"{REV}/data/expression_matrix.csv", index_col=0)
    emat.columns = [str(c).split(".", 1)[1] if "." in str(c) else str(c) for c in emat.columns]
    fuji = fuji[fuji["sample"].isin(emat.columns)].set_index("sample")

    ku = fuji[fuji["series"] == "KU"].copy()
    ku_staged = ku[ku["fibrosis"].notna()]
    print(f"KU: {len(ku)} samples, {len(ku_staged)} staged")

    # feature genes: TRAIN-side selection (TU+HU+TH), same as MB-8xxx
    train = fuji[fuji["series"].isin(["TU", "HU", "TH"])]
    emat_t = standardize_sample(emat[[c for c in train.index if c in emat.columns]])
    genes_single = top_genes(emat_t, 200)

    emat_ku = standardize_sample(emat[[c for c in ku_staged.index if c in emat.columns]])
    recs = []
    for sid, row in ku_staged.iterrows():
        base = (f"{pick(VERBALIZATIONS['instr_intro'])}\n"
                f"Patient: {clinical_block(row['age'], row['sex'])}.\n"
                f"{render_profile(sid, genes_single, emat_ku)}\n")
        recs.append(dict(task="MB-9001", split="test", sample=sid, source="fujiwara_KU",
            prompt=base + pick(VERBALIZATIONS["ask_fib_binary"]),
            answer="yes" if row["fibrosis"] >= 3 else "no"))
        recs.append(dict(task="MB-9002", split="test", sample=sid, source="fujiwara_KU",
            prompt=base + pick(VERBALIZATIONS["ask_fib_multiclass"]),
            answer=f"F{int(row['fibrosis'])}"))
        recs.append(dict(task="MB-9005", split="test", sample=sid, source="fujiwara_KU",
            prompt=base + pick(VERBALIZATIONS["ask_fib_regression"]),
            answer=f"{row['fibrosis']:.0f}"))
        if pd.notna(row["nas"]):
            recs.append(dict(task="MB-9006", split="test", sample=sid, source="fujiwara_KU",
                prompt=base + pick(VERBALIZATIONS["ask_nas_regression"]),
                answer=f"{row['nas']:.0f}"))
    write_jsonl(recs, f"{OUT}/MB-9xxx_fujiwara_KU_test.jsonl.gz",
                meta=dict(builder="Fujiwara KU internal test (cohort-shift check)",
                          train_side="TU+HU+TH (MB-8xxx)", n_ku_staged=len(ku_staged)))
    print(f"done in {time.time()-T0:.1f}s")


if __name__ == "__main__":
    main()
