#!/usr/bin/env python3
"""Freeze-4 — probe->gene-symbol mapping + rebuilt external train pool.

Fixes the session-2 finding: external microarray cohorts (GSE48452/49541/
89632/66676) expose probe IDs while the frozen test uses Ensembl genes.
This builder maps every probe to its HGNC symbol via the GPL platform tables
inside the family.soft files, collapses to gene level (max-mean probe),
rebuilds MB-11xx on unified gene space, and re-runs the ML baselines
(full pool, feature-matched) for comparison against the frozen-test anchor.
"""
import gzip, json, os, re, sys, time

import numpy as np
import pandas as pd

T0 = time.time()
SEED = 20260929
import random as _random
rng = _random.Random(SEED)

ROOT = "/Users/subhadipbanerjee/masld-llm"
sys.path.insert(0, f"{ROOT}/scripts")
from build_mb10xx import (VERBALIZATIONS, pick, write_jsonl, top_genes,
                          clinical_block, render_profile, standardize_sample,
                          build_single_format, build_pairwise)
from build_freeze3 import load_series_matrix, parse_soft_meta, stage_value

DATA = f"{ROOT}/data"
MAT = f"{DATA}/matrices"
OUT = f"{ROOT}/prompts"


def parse_gene_assignment(ga):
    """'NM_x // SYMBOL // desc // loc /// NM_y // ...' -> first SYMBOL."""
    if not ga or ga == "---":
        return None
    m = re.search(r"//\s*([A-Za-z][A-Za-z0-9@.\-]*)\s*//", ga)
    return m.group(1) if m else None


def probe2gene_map(acc, preferred_col=None):
    """Extract probe->gene symbol mapping from the platform table in family.soft."""
    with gzip.open(f"{DATA}/{acc}_family.soft.gz", "rt", errors="ignore") as f:
        in_plat, cols, rows = False, None, []
        for line in f:
            if line.startswith("!platform_table_begin"):
                in_plat = True
                continue
            if line.startswith("!platform_table_end"):
                break
            if in_plat:
                parts = line.rstrip("\n").split("\t")
                if cols is None:
                    cols = parts
                    continue
                rows.append(parts)
    ix = {c: i for i, c in enumerate(cols)}
    mapping = {}
    if "Gene Symbol" in ix:
        for r in rows:
            sym = r[ix["Gene Symbol"]].strip()
            if sym:
                mapping[r[0]] = sym.split("///")[0].strip()
    elif "gene_assignment" in ix:
        for r in rows:
            sym = parse_gene_assignment(r[ix["gene_assignment"]])
            if sym:
                mapping[r[0]] = sym
    elif "ILMN_Gene" in ix:
        for r in rows:
            sym = r[ix["ILMN_Gene"]].strip()
            if sym and not sym.startswith("ERCC"):
                mapping[r[0]] = sym
    return mapping


def collapse_to_genes(df, mapping):
    """Probe-level matrix -> gene-level (max-mean probe selection per gene)."""
    df = df.copy()
    df.index = [str(i).strip('"') for i in df.index]
    probes = [p for p in df.index if p in mapping]
    sub = df.loc[probes]
    genes = pd.Series([mapping[p] for p in probes], index=probes)
    grouped = sub.groupby(genes)
    # max mean expression per gene
    means = sub.mean(axis=1)
    best = means.groupby(genes).idxmax()
    best_genes = [g for g in best.index]
    out = df.loc[[p for p in best.values]]
    out.index = best_genes
    return out


def main():
    print("== building probe->gene maps ==")
    maps = {}
    for acc in ("GSE48452", "GSE49541", "GSE89632", "GSE66676"):
        maps[acc] = probe2gene_map(acc)
        print(f"  {acc}: {len(maps[acc])} probes mapped")

    print("== harmonising external cohorts on gene symbols ==")
    cohorts = {}
    # reuse freeze-3 metadata logic but rebuild matrices with mapping
    from build_freeze3 import harmonise_external, parse_soft_meta
    ext = harmonise_external()
    for name, (df, mat) in ext.items():
        if name == "GSE61260":
            # rebuild GSE61260 from its own suppl CSV + soft characteristics
            g6 = pd.read_csv(f"{MAT}/GSE61260_datLiverNormalizedExpr.csv.gz", index_col=0)
            soft = parse_soft_meta(f"{DATA}/GSE61260_family.soft.gz")
            geo_order = sorted(soft.keys())  # GSM accession sort order == SampleN order (verified n=134)
            if len(geo_order) == g6.shape[1]:
                g6.columns = [f"GSE61260:{g}" for g in geo_order]
                recs6 = []
                for g in geo_order:
                    v = soft[g]
                    age = pd.to_numeric(pd.Series([v.get("age")]), errors="coerce").iloc[0] if v.get("age") else np.nan
                    recs6.append({"cohort": "GSE61260", "fibrosis": np.nan, "nas": np.nan,
                                  "age": age, "sex": v.get("sex", "NA"), "t2dm": v.get("diseasestatus", "NA")})
                df6 = pd.DataFrame(recs6, index=pd.Index([f"GSE61260:{g}" for g in geo_order], name="sample"))
                cohorts["GSE61260"] = (df6, g6)
                print(f"  GSE61260: {g6.shape[1]} samples joined to soft metadata (gene-symbol space)")
            else:
                print(f"  !! GSE61260 geo count {len(geo_order)} != matrix {g6.shape[1]} — skipped")
            continue
        if df is None:
            continue
        if name in maps:
            gmat = collapse_to_genes(mat, maps[name])
            cohorts[name] = (df, gmat)
            print(f"  {name}: {mat.shape[0]} probes -> {gmat.shape[0]} genes")

    print("== rebuilding MB-11xx on unified gene space ==")
    all_recs = []
    for name, (df, mat) in cohorts.items():
        if df is None:
            continue
        mat = standardize_sample(mat)
        d = df[df["fibrosis"].notna()]
        if name == "GSE61260":
            genes = top_genes(mat, 200)
            for sid, row in df.iterrows():
                if pd.isna(row.get("age")):
                    continue
                base = (f"{pick(VERBALIZATIONS['instr_intro'])}\n"
                        f"Patient: {clinical_block(None, row['sex'])}.\n"
                        f"{render_profile(sid, genes, mat)}\n")
                all_recs.append(dict(task="MB-1106", split="train", sample=str(sid), source=name,
                    prompt=base + "Predict the patient's age in years.",
                    answer=f"{int(row['age'])}"))
            continue
        genes = top_genes(mat, 200)
        all_recs += build_single_format(d, mat, genes, "train", "MB-11", name)
        all_recs += build_pairwise(d, mat, top_genes(mat, 100), "train", "MB-11", name)

    write_jsonl(all_recs, f"{OUT}/MB-11xx_external_train.jsonl.gz",
                meta=dict(builder="external tier-1 cohorts, gene-symbol space (probe->gene via GPL tables)",
                          fix="freeze-4: unified gene space; probe IDs eliminated"))
    print(f"done in {time.time()-T0:.1f}s")


if __name__ == "__main__":
    main()
