#!/usr/bin/env python3
"""MASLD-Bench builder v3 — knowledge/perturbation corpus + Fujiwara clinical train.

Corpora built here (all TRAIN-side; the frozen test remains EPos+Gubra only):
  MB-61xx  MSigDB c2 pathway-membership prompts (masked-member format)
  MB-62xx  drug->gene interaction retrieval prompts (DrugBank-layer)
  MB-70xx  masked direction-of-change from YOUR discovery DGE (11,676 genes)
  MB-8xxx  Fujiwara clinical block (TU+HU+TH train series; KU reserved)

Usage: python3 build_mb6xxx_8xxx.py
"""
import gzip, hashlib, json, os, random, re, time

import numpy as np
import pandas as pd

T0 = time.time()
SEED = 20260929
rng = random.Random(SEED)

REV = "/Users/subhadipbanerjee/masld-revision"
OUT = "/Users/subhadipbanerjee/masld-llm/prompts"
os.makedirs(OUT, exist_ok=True)

# reuse the harmonised prompt machinery from the clinical builder
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_mb10xx import (VERBALIZATIONS, pick, sha16, write_jsonl, fmt_expr,
                          top_genes, clinical_block, render_profile, standardize_sample)


def build_msigdb(n_sets=3000):
    msig = json.load(open(f"{REV}/data/msigdb/c2.all.v2023.2.Hs.json"))
    recs = []
    all_genes = list({g for v in msig.values()
                      for g in (v.get("geneSymbols") or [])})
    print(f"  msigdb c2: {len(msig)} sets, union {len(all_genes)} genes")
    for setname, v in list(msig.items())[:n_sets]:
        members = v.get("geneSymbols") or []
        if len(members) < 8:
            continue
        hidden = rng.choice(members)
        shown = rng.sample([m for m in members if m != hidden], min(12, len(members) - 1))
        decoy = rng.choice(all_genes)
        while decoy in members:
            decoy = rng.choice(all_genes)
        options = [hidden, decoy]
        rng.shuffle(options)
        recs.append(dict(
            task="MB-6101", split="train", source="msigdb_c2",
            prompt=(f"The gene set {setname} contains the following members: "
                    f"{', '.join(shown)}, and others.\n"
                    f"Which additional gene also belongs to {setname}: "
                    f"{options[0]} or {options[1]}? Answer with one gene symbol."),
            answer=hidden,
        ))
    return recs


def build_drugs(n_prompts=30000):
    inter = pd.read_csv(f"{REV}/data/drug_data/interactions.tsv", sep="\t")
    genes = pd.read_csv(f"{REV}/data/drug_data/genes.tsv", sep="\t")
    print("  interactions columns:", list(inter.columns)[:8])
    gene_col = "gene_name" if "gene_name" in inter.columns else inter.columns[1]
    drug_col = "drug_name" if "drug_name" in inter.columns else inter.columns[0]
    gene_pool = genes.iloc[:, 0].astype(str).tolist()
    known = set(inter[gene_col].astype(str))
    pool = [g for g in gene_pool if g not in known][:5000] or gene_pool[:5000]
    take = inter.dropna(subset=[gene_col, drug_col]).sample(n=min(n_prompts, len(inter)), random_state=SEED)
    recs = []
    for _, row in take.iterrows():
        gene = str(row[gene_col]); drug = str(row[drug_col])
        decoy = rng.choice(pool)
        options = [gene, decoy]
        rng.shuffle(options)
        recs.append(dict(
            task="MB-6201", split="train", source="drugbank_layer",
            prompt=(f"Which gene is a known interaction target of the drug {drug}: "
                    f"{options[0]} or {options[1]}? Answer with one gene symbol."),
            answer=gene,
        ))
    return recs


def build_dge():
    t1 = pd.read_csv(f"{REV}/results/decisive_test/t1_ranked_logFC.csv")
    recs = []
    for _, row in t1.iterrows():
        gene, lf = str(row["GeneSymbol"]), float(row["logFC"])
        if not gene or np.isnan(lf) or abs(lf) < 0.05:
            continue
        recs.append(dict(
            task="MB-7001", split="train", source="discovery_dge_t1",
            prompt=(f"The gene {gene} is measured in human liver biopsies of MASLD patients "
                    f"compared to healthy liver tissue. Does expression of {gene} increase or "
                    f"decrease in MASLD? Answer with increase or decrease."),
            answer="increase" if lf > 0 else "decrease",
        ))
    return recs


def build_fujiwara():
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
    emat = standardize_sample(emat[[c for c in fuji.index if c in emat.columns]])

    train = fuji[fuji["series"].isin(["TU", "HU", "TH"]) & fuji["fibrosis"].notna()]
    print(f"  Fujiwara: {len(fuji)} joined, {len(train)} staged train (TU+HU+TH); KU held for internal test")
    genes_single = top_genes(emat, 200)
    recs = []
    for sid, row in train.iterrows():
        base = (
            f"{pick(VERBALIZATIONS['instr_intro'])}\n"
            f"Patient: {clinical_block(row['age'], row['sex'])}.\n"
            f"{render_profile(sid, genes_single, emat)}\n"
        )
        recs.append(dict(task="MB-8001", split="train", sample=sid, source="fujiwara",
                         prompt=base + pick(VERBALIZATIONS["ask_fib_binary"]),
                         answer="yes" if row["fibrosis"] >= 3 else "no"))
        recs.append(dict(task="MB-8002", split="train", sample=sid, source="fujiwara",
                         prompt=base + pick(VERBALIZATIONS["ask_fib_multiclass"]),
                         answer=f"F{int(row['fibrosis'])}"))
        recs.append(dict(task="MB-8005", split="train", sample=sid, source="fujiwara",
                         prompt=base + pick(VERBALIZATIONS["ask_fib_regression"]),
                         answer=f"{row['fibrosis']:.0f}"))
        if pd.notna(row["nas"]):
            recs.append(dict(task="MB-8006", split="train", sample=sid, source="fujiwara",
                             prompt=base + pick(VERBALIZATIONS["ask_nas_regression"]),
                             answer=f"{row['nas']:.0f}"))
    return recs, train


def main():
    print("== MB-61xx MSigDB ==")
    msig_recs = build_msigdb()
    write_jsonl(msig_recs, f"{OUT}/MB-61xx_msigdb_train.jsonl.gz",
                meta=dict(builder="msigdb c2", sha=sha16(f"{REV}/data/msigdb/c2.all.v2023.2.Hs.json")))

    print("== MB-62xx drug layer ==")
    drug_recs = build_drugs()
    write_jsonl(drug_recs, f"{OUT}/MB-62xx_drugs_train.jsonl.gz",
                meta=dict(builder="drugbank interactions", sha=sha16(f"{REV}/data/drug_data/interactions.tsv")))

    print("== MB-70xx DGE direction ==")
    dge_recs = build_dge()
    write_jsonl(dge_recs, f"{OUT}/MB-70xx_dge_direction_train.jsonl.gz",
                meta=dict(builder="t1_ranked_logFC", sha=sha16(f"{REV}/results/decisive_test/t1_ranked_logFC.csv")))

    print("== MB-8xxx Fujiwara clinical train ==")
    fuji_recs, fuji_train = build_fujiwara()
    write_jsonl(fuji_recs, f"{OUT}/MB-8xxx_fujiwara_train.jsonl.gz",
                meta=dict(builder="fujiwara TU+HU+TH", sha=sha16(f"{REV}/data/expression_matrix.csv"),
                          train_n=len(fuji_train)))
    print(f"done in {time.time()-T0:.1f}s")


if __name__ == "__main__":
    main()
