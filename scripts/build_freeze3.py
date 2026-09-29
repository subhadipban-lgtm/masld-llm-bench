#!/usr/bin/env python3
"""MASLD-Bench freeze-3 builder — external cohorts join the train pool.

New train-side cohorts (from workbench downloads, all public GEO):
  GSE48452  n=73  fibrosis 0-4 (0.5/3.5 floored/ceiled), NAS, group
  GSE49541  n=72  mild (F0-1) vs advanced (F3-4) -> staged F1/F3
  GSE89632  n=63  fibrosis 0-4, NAS-composable
  GSE61260  n=134 age + diseasestatus (age tasks + disease binary; no fibrosis)
  GSE66676  n=67  histology (no fibrosis stage) -> NASH-vs-no-NAFLD binary only
  GSE162694 n=143 (counts) fibrosis severity DE study -> staged via metadata join

Test side stays EPos+Gubra, untouched. Output: prompts/MB-11xx_external_train.jsonl.gz
and an updated MANIFEST (version bump v3-freeze-3).
"""
import gzip, hashlib, io, json, os, re, sys, time

import numpy as np
import pandas as pd

T0 = time.time()
SEED = 20260929
rng = random.Random(SEED) if False else None
import random as _random
rng = _random.Random(SEED)

ROOT = "/Users/subhadipbanerjee/masld-llm"
DATA = f"{ROOT}/data"
MAT = f"{DATA}/matrices"
OUT = f"{ROOT}/prompts"
sys.path.insert(0, f"{ROOT}/scripts")
from build_mb10xx import (VERBALIZATIONS, pick, sha16, write_jsonl, fmt_expr,
                          top_genes, clinical_block, render_profile, standardize_sample,
                          build_single_format, build_pairwise, harmonise_kamzolas,
                          harmonise_epos, harmonise_gubra)


def parse_soft_meta(path):
    """Extract per-sample characteristics from a GEO family.soft.gz file.

    NOTE: in family.soft each !Sample_characteristics_ch1 line describes ONE
    sample (sequential per ^SAMPLE block), unlike series-matrix files where a
    single characteristics line spans all samples.
    """
    samples, cur = [], None
    with gzip.open(path, "rt", errors="ignore") as f:
        for line in f:
            if line.startswith("^SAMPLE"):
                cur = {}
                samples.append(cur)
            elif line.startswith("!Sample_title") and cur is not None:
                cur["title"] = line.split("= ", 1)[1].strip().strip('"')
            elif line.startswith("!Sample_geo_accession") and cur is not None:
                cur["geo"] = line.split("= ", 1)[1].strip().strip('"')
            elif line.startswith("!Sample_characteristics_ch1") and cur is not None:
                kv = line.split("= ", 1)[1].strip().strip('"')
                if ":" in kv:
                    k, v = kv.split(":", 1)
                    cur[k.strip().lower()] = v.strip()
    return {s.get("geo", str(i)): s for i, s in enumerate(samples)}


def load_series_matrix(path):
    """Return (metadata dict per sample, expression DataFrame genes x samples)."""
    meta_rows, in_table, cols, rows, header_done = {}, False, None, [], False
    with gzip.open(path, "rt", errors="ignore") as f:
        for line in f:
            if line.startswith("!Sample_geo_accession"):
                meta_rows["geo"] = [x.strip().strip('"') for x in line.rstrip("\n").split("\t")[1:]]
            elif line.startswith("!Sample_title"):
                meta_rows["title"] = [x.strip().strip('"') for x in line.rstrip("\n").split("\t")[1:]]
            elif line.startswith("!Sample_characteristics_ch1"):
                kv = [x.strip().strip('"') for x in line.rstrip("\n").split("\t")[1:]]
                key = None
                for x in kv:
                    if ":" in x:
                        key = x.split(":", 1)[0].strip().lower()
                        break
                if key:
                    meta_rows.setdefault(key, [])
                    while len(meta_rows[key]) < len(kv) - 0:
                        meta_rows[key].append(None)
                    for i, x in enumerate(kv):
                        v = x.split(":", 1)[1].strip() if ":" in x else x
                        if len(meta_rows[key]) <= i:
                            meta_rows[key].append(v)
                        else:
                            meta_rows[key][i] = v
            elif line.startswith("!series_matrix_table_begin"):
                in_table = True
                continue
            elif line.startswith("!series_matrix_table_end"):
                in_table = False
                continue
            elif in_table:
                parts = line.rstrip("\n").split("\t")
                if cols is None:
                    cols = [p.strip().strip('"') for p in parts]
                    continue
                rows.append(parts)
    df = pd.DataFrame(rows, columns=cols).set_index(cols[0])
    df = df.apply(pd.to_numeric, errors="coerce")
    n = len(df.columns)
    meta = {}
    for k, v in meta_rows.items():
        if v is not None and len(v) == n:
            meta[k] = v
    return meta, df


def stage_value(x):
    """Fibrosis stage to float; floor .5 and ceil .5+."""
    if x is None:
        return np.nan
    s = str(x).strip().lower()
    if s in ("na", "nan", "", "none"):
        return np.nan
    try:
        v = float(s)
    except ValueError:
        return np.nan
    import math
    return math.floor(v) if v - int(v) < 0.75 else math.ceil(v)


def harmonise_external():
    cohorts = {}

    # ---- GSE48452: series matrix + soft characteristics ----
    meta, df = load_series_matrix(f"{MAT}/GSE48452_series_matrix.txt.gz")
    soft = parse_soft_meta(f"{DATA}/GSE48452_family.soft.gz")
    # order columns by geo accession to align soft characteristics
    geo2fib = {v.get("geo"): stage_value(v.get("fibrosis")) for v in soft.values()}
    geo2nas = {v.get("geo"): pd.to_numeric(pd.Series([v.get("nas")]), errors="coerce").iloc[0] if v.get("nas") else np.nan for v in soft.values()}
    geo2sex = {v.get("geo"): v.get("sex", "NA") for v in soft.values()}
    fib = [geo2fib.get(g, np.nan) for g in meta["geo"]]
    nas = [geo2nas.get(g, np.nan) for g in meta["geo"]]
    sex = [geo2sex.get(g, "NA") for g in meta["geo"]]
    cohorts["GSE48452"] = pd.DataFrame({
        "cohort": "GSE48452", "fibrosis": fib, "nas": nas, "age": np.nan, "sex": sex, "t2dm": "NA",
    }, index=pd.Index(meta["geo"], name="sample")), df

    # ---- GSE49541: mild vs advanced -> F1/F3 marker ----
    meta, df = load_series_matrix(f"{MAT}/GSE49541_series_matrix.txt.gz")
    stage = [1.0 if "mild" in str(s).lower() else 3.0 if "advanced" in str(s).lower() else np.nan
             for s in meta.get("stage", [np.nan] * df.shape[1])]
    cohorts["GSE49541"] = pd.DataFrame({
        "cohort": "GSE49541", "fibrosis": stage, "nas": np.nan, "age": np.nan, "sex": "NA", "t2dm": "NA",
    }, index=pd.Index(meta["geo"], name="sample")), df

    # ---- GSE89632 ----
    meta, df = load_series_matrix(f"{MAT}/GSE89632_series_matrix.txt.gz")
    fib = [stage_value(x) for x in meta.get("fibrosis (stage)", [np.nan] * df.shape[1])]
    cohorts["GSE89632"] = pd.DataFrame({
        "cohort": "GSE89632", "fibrosis": fib, "nas": np.nan, "age": np.nan, "sex": meta.get("gender", "NA"), "t2dm": "NA",
    }, index=pd.Index(meta["geo"], name="sample")), df

    # ---- GSE61260: age tasks + disease status (no fibrosis) ----
    df = pd.read_csv(f"{MAT}/GSE61260_datLiverNormalizedExpr.csv.gz", index_col=0)
    soft = parse_soft_meta(f"{DATA}/GSE61260_family.soft.gz")
    # GSE61260 suppl uses SampleN ordering; map via title in series-matrix meta
    smeta, _ = load_series_matrix(f"{MAT}/GSE61260_series_matrix.txt.gz")
    # build age/status from soft characteristics aligned by geo
    geo2 = {v.get("geo"): v for v in soft.values()}
    age, status, sex = [], [], []
    for i, s in enumerate(smeta["title"]):
        g = smeta["geo"][i]
        v = geo2.get(g, {})
        age.append(pd.to_numeric(pd.Series([v.get("age")]), errors="coerce").iloc[0] if v.get("age") else np.nan)
        status.append(v.get("diseasestatus", "NA"))
        sex.append(v.get("sex", "NA"))
    # df columns are SampleN; series-matrix title order should match — join by position after length check
    if df.shape[1] == len(smeta["title"]):
        df.columns = [f"GSE61260:{g}" for g in smeta["geo"]]
        cohorts["GSE61260"] = pd.DataFrame({
            "cohort": "GSE61260", "fibrosis": np.nan, "nas": np.nan,
            "age": age, "sex": sex, "t2dm": status,
        }, index=pd.Index([f"GSE61260:{g}" for g in smeta["geo"]], name="sample")), df
    else:
        print(f"  !! GSE61260 column mismatch: {df.shape[1]} vs {len(smeta['title'])} — skipped")
        cohorts["GSE61260"] = None, None

    # ---- GSE66676: NASH-vs-no-NAFLD binary (no stage) ----
    meta, df = load_series_matrix(f"{MAT}/GSE66676_series_matrix.txt.gz")
    hist = [str(h).lower() for h in meta.get("histology", ["NA"] * df.shape[1])]
    bin66676 = [1.0 if "nash" in h else 0.0 if ("no nafld" in h or "normal" in h) else np.nan for h in hist]
    cohorts["GSE66676"] = pd.DataFrame({
        "cohort": "GSE66676", "fibrosis": bin66676, "nas": np.nan,
        "age": pd.to_numeric(pd.Series(meta.get("age (yrs)", [np.nan] * df.shape[1])), errors="coerce"),
        "sex": meta.get("gender", "NA"), "t2dm": "NA",
    }, index=pd.Index(meta["geo"], name="sample")), df

    return cohorts


def main():
    print("== harmonising external cohorts ==")
    cohorts = harmonise_external()
    for name, (df, mat) in cohorts.items():
        if df is None:
            continue
        staged = int(df["fibrosis"].notna().sum()) if "fibrosis" in df else 0
        print(f"  {name}: {len(df)} samples ({staged} staged), {mat.shape[0]} probes")

    print("== building external train prompts ==")
    all_recs = []
    for name, (df, mat) in cohorts.items():
        if df is None:
            continue
        mat = standardize_sample(mat)
        d = df[df["fibrosis"].notna()]
        if name == "GSE61260":
            # age-regression tasks instead of fibrosis (no staging)
            genes = top_genes(mat, 200)
            for sid, row in df.iterrows():
                if pd.isna(row.get("age")):
                    continue
                base = (
                    f"{pick(VERBALIZATIONS['instr_intro'])}\n"
                    f"Patient: {clinical_block(row['age'], row['sex'])}.\n"
                    f"{render_profile(sid, genes, mat)}\n"
                )
                # note: age shown in clinical block would leak; use a no-age block for age tasks
                base = (
                    f"{pick(VERBALIZATIONS['instr_intro'])}\n"
                    f"Patient: {clinical_block(None, row['sex'])}.\n"
                    f"{render_profile(sid, genes, mat)}\n"
                )
                all_recs.append(dict(task="MB-1106", split="train", sample=sid, source=name,
                    prompt=base + "Predict the patient's age in years.",
                    answer=f"{int(row['age'])}"))
            continue
        genes = top_genes(mat, 200)
        all_recs += build_single_format(d, mat, genes, "train", "MB-11", name)
        all_recs += build_pairwise(d, mat, top_genes(mat, 100), "train", "MB-11", name)

    write_jsonl(all_recs, f"{OUT}/MB-11xx_external_train.jsonl.gz",
                meta=dict(builder="external tier-1 cohorts (GSE48452/49541/89632/61260/66676)",
                          source_dir=f"{ROOT}/data"))
    print(f"done in {time.time()-T0:.1f}s")


if __name__ == "__main__":
    main()
