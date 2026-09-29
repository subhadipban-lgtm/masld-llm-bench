#!/usr/bin/env python3
"""MASLD-Bench builder v3 — first freeze.

Builds the clinical-core prompt corpus from on-disk cohorts:
  TRAIN  : Kamzolas SANYAL+UCAM (batch-corrected counts, n=136)
  TEST   : EPos (n=157) + Gubra (n=38 usable)  — frozen forever
  (Fujiwara + external_v3 cohorts join the TRAIN pool in the next freeze;
   they are deliberately excluded from this first freeze so the test side
   is locked before any new cohort enters training.)

Tasks (four formats, rotating verbalizations):
  MB-1001/2001 fibrosis binary (advanced F3-F4?)
  MB-1002/2002 fibrosis multiclass (F0-F4)
  MB-1003/2003 fibrosis pairwise (intra-cohort)
  MB-1005/2005 fibrosis regression (0-4)
  MB-1006/2006 NAS regression (0-8)

Usage: python3 build_mb10xx.py
"""
import gzip, hashlib, itertools, json, os, random, re, sys, time

import numpy as np
import pandas as pd

T0 = time.time()
SEED = 20260929
rng = random.Random(SEED)

REV = "/Users/subhadipbanerjee/masld-revision"
OUT = "/Users/subhadipbanerjee/masld-llm/prompts"
os.makedirs(OUT, exist_ok=True)

N_SINGLE, N_PAIR = 200, 100
TRAIN_COHORTS = ("SANYAL", "UCAM")

VERBALIZATIONS = {
    "instr_intro": [
        "You are analyzing human liver biopsy transcriptomics from a MASLD study.",
        "The following data come from a liver biopsy of a patient in a metabolic dysfunction-associated steatotic liver disease cohort.",
        "Below is the expressed gene profile of a human liver sample from a steatotic liver disease study.",
    ],
    "gene_line": [
        "Expression (normalised counts): {features}",
        "Gene expression measurements: {features}",
        "Transcript levels (counts): {features}",
    ],
    "ask_fib_binary": [
        "Does this profile indicate advanced fibrosis (F3-F4)? Answer yes or no.",
        "Is this biopsy consistent with advanced fibrosis? Answer with yes or no.",
    ],
    "ask_fib_multiclass": [
        "Assign the fibrosis stage of this biopsy: F0, F1, F2, F3, or F4.",
        "Which fibrosis stage best matches this profile? Answer with one of F0, F1, F2, F3, F4.",
    ],
    "ask_fib_regression": [
        "Predict the numeric fibrosis stage (0-4) of this biopsy.",
        "Estimate the exact Kleiner fibrosis stage as a number between 0 and 4.",
    ],
    "ask_nas_regression": [
        "Predict the NAFLD Activity Score (0-8) of this biopsy.",
        "Estimate the exact NAS as a number between 0 and 8.",
    ],
    "ask_pairwise": [
        "Which patient has the more advanced fibrosis stage? Answer with A or B.",
        "Which of the two patients shows more advanced fibrosis? Answer A or B.",
    ],
}


def pick(pool):
    return pool[rng.randrange(len(pool))]


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def write_jsonl(records, path, meta):
    meta = {"n_records": len(records), "seed": SEED, "built": "2026-09-29", **meta}
    with gzip.open(path, "wt") as f:
        f.write(json.dumps({"__meta__": meta}) + "\n")
        for r in records:
            f.write(json.dumps(r) + "\n")
    print(f"  {os.path.basename(path):42s} {len(records):6d} prompts")


def fmt_expr(gene, val):
    v = float(val)
    s = f"{v:.2f}" if abs(v) < 100 else f"{v:.1f}" if abs(v) < 10000 else f"{v:.0f}"
    return f"{gene}={s}"


def standardize_sample(mat):
    """Label-free per-sample harmonisation across differently processed matrices.

    log1p when the matrix is non-negative (raw counts), then per-sample z-score
    across genes. Makes Kamzolas (batch-corrected log), EPos (raw counts) and
    Gubra (normalised) comparable without touching labels or cross-sample info.
    """
    m = mat.copy()
    if (m >= 0).all().all():
        m = np.log1p(m)
    mu = m.mean(axis=0)
    sd = m.std(axis=0).replace(0, 1.0)
    return (m - mu) / sd


def top_genes(mat, n):
    return mat.var(axis=1).sort_values(ascending=False).head(n).index.tolist()


def clinical_block(age=None, sex=None, t2dm=None):
    parts = []
    if age is not None and pd.notna(age):
        parts.append(f"age {int(age)}")
    if sex is not None and pd.notna(sex):
        parts.append("female" if str(sex).lower().startswith("f") else "male")
    if t2dm is not None and pd.notna(t2dm):
        parts.append(
            "type-2 diabetes" if str(t2dm).lower() in ("yes", "1", "true") else "no type-2 diabetes"
        )
    return "; ".join(parts)


def render_profile(sample, genes, mat):
    vals = mat.loc[genes, sample]
    feats = ", ".join(fmt_expr(g, vals[g]) for g in genes)
    return pick(VERBALIZATIONS["gene_line"]).format(features=feats)


def build_single_format(df, mat, genes, split, prefix, source):
    out = []
    for sid, row in df.iterrows():
        if pd.isna(row["fibrosis"]):
            continue
        base = (
            f"{pick(VERBALIZATIONS['instr_intro'])}\n"
            f"Patient: {clinical_block(row.get('age'), row.get('sex'), row.get('t2dm'))}.\n"
            f"{render_profile(sid, genes, mat)}\n"
        )
        out.append(dict(task=f"{prefix}001", split=split, sample=str(sid), source=source,
                        prompt=base + pick(VERBALIZATIONS["ask_fib_binary"]),
                        answer="yes" if row["fibrosis"] >= 3 else "no"))
        out.append(dict(task=f"{prefix}002", split=split, sample=str(sid), source=source,
                        prompt=base + pick(VERBALIZATIONS["ask_fib_multiclass"]),
                        answer=f"F{int(row['fibrosis'])}"))
        out.append(dict(task=f"{prefix}005", split=split, sample=str(sid), source=source,
                        prompt=base + pick(VERBALIZATIONS["ask_fib_regression"]),
                        answer=f"{row['fibrosis']:.0f}"))
        if pd.notna(row.get("nas")):
            out.append(dict(task=f"{prefix}006", split=split, sample=str(sid), source=source,
                            prompt=base + pick(VERBALIZATIONS["ask_nas_regression"]),
                            answer=f"{row['nas']:.0f}"))
    return out


def build_pairwise(df, mat, genes, split, prefix, source):
    out = []
    for cohort, grp in df.groupby("cohort"):
        sids = [s for s in grp.index if pd.notna(grp.loc[s, "fibrosis"])]
        for a, b in itertools.combinations(sids, 2):
            fa, fb = grp.loc[a, "fibrosis"], grp.loc[b, "fibrosis"]
            if fa == fb:
                continue
            out.append(dict(
                task=f"{prefix}003", split=split, cohort=str(cohort), sample=f"{a}|{b}",
                source=source,
                prompt=(
                    f"{pick(VERBALIZATIONS['instr_intro'])}\n"
                    f"Patient A: {clinical_block(grp.loc[a,'age'], grp.loc[a,'sex'], grp.loc[a,'t2dm'])}.\n"
                    f"{render_profile(a, genes, mat)}\n\n"
                    f"Patient B: {clinical_block(grp.loc[b,'age'], grp.loc[b,'sex'], grp.loc[b,'t2dm'])}.\n"
                    f"{render_profile(b, genes, mat)}\n\n"
                    f"{pick(VERBALIZATIONS['ask_pairwise'])}"
                ),
                answer="A" if fa > fb else "B",
            ))
    return out


def harmonise_kamzolas():
    counts = pd.read_csv(f"{REV}/data/kamzolas/batch_corrected_counts_(dataset+gender).csv", index_col=0)
    meta = pd.read_csv(f"{REV}/data/kamzolas/metadata.csv", index_col=0)
    counts.columns = [str(c).strip() for c in counts.columns]
    meta.index = meta["Sample name"].astype(str).str.strip()   # join key = 'Sample N'
    shared = [s for s in meta.index if s in counts.columns]
    counts, meta = counts[shared], meta.loc[shared]
    df = pd.DataFrame({
        "cohort": meta["Dataset"].astype(str),
        "fibrosis": pd.to_numeric(meta["Fibrosis"], errors="coerce"),
        "nas": pd.to_numeric(meta["NAS"], errors="coerce"),
        "age": pd.to_numeric(meta["Age"], errors="coerce"),
        "sex": meta["Sex"].astype(str),
        "t2dm": meta["T2DM"].astype(str),
    }, index=pd.Index(shared, name="sample"))
    return df, counts


def harmonise_epos():
    import zipfile
    with zipfile.ZipFile(f"{REV}/data/kamzolas/EPoS_dataset/EPoS_counts.tsv.zip") as z:
        with z.open(z.namelist()[0]) as f:
            counts = pd.read_csv(f, sep="\t", index_col=0)
    counts.columns = [str(c).strip().strip('"') for c in counts.columns]
    meta = pd.read_csv(f"{REV}/data/kamzolas/EPoS_dataset/epos_metadata.csv")
    meta = meta.set_index("GEO_ID")
    shared = [s for s in meta.index.astype(str) if s in counts.columns]
    counts, meta = counts[shared], meta.loc[shared]
    df = pd.DataFrame({
        "cohort": "EPOS",
        "fibrosis": pd.to_numeric(meta["Fibrosis.stage"], errors="coerce"),
        "nas": pd.to_numeric(meta["NAFLD.Activity.Score..NAS..Kleiner"], errors="coerce"),
        "age": np.nan,
        "sex": "NA",
        "t2dm": "NA",
    }, index=pd.Index(shared, name="sample"))
    return df, counts


def harmonise_gubra():
    counts = pd.read_csv(f"{REV}/data/kamzolas/Gubra_dataset/Normalised_Counts_GUBRA.txt", sep="\t", index_col=0)
    counts.columns = [str(c).strip().strip('"') for c in counts.columns]
    meta = pd.read_csv(f"{REV}/data/kamzolas/Gubra_dataset/GSE126848_meta.txt", sep=",", index_col=0)
    # characteristics fields are embedded per sample; extract disease + gender from characteristics columns
    def find_char(row, key):
        for v in row:
            s = str(v)
            if s.startswith(key + ":"):
                return s.split(":", 1)[1].strip()
        return None
    ch = meta.filter(like="characteristics_ch1")
    disease = ch.apply(lambda r: find_char(r, "disease"), axis=1)
    gender = ch.apply(lambda r: find_char(r, "gender"), axis=1)
    # Gubra staging is encoded in the title: 'NAFL_1' .. 'NAFL_38' (suffix = fibrosis stage)
    fib = meta["title"].astype(str).str.extract(r"(\d)$", expand=False)
    fib = pd.to_numeric(fib, errors="coerce")
    shared = [s for s in meta.index.astype(str) if s in counts.columns]
    counts, meta2 = counts[shared], meta.loc[shared]
    df = pd.DataFrame({
        "cohort": "GUBRA",
        "fibrosis": fib.loc[shared],
        "nas": np.nan,
        "age": np.nan,
        "sex": gender.loc[shared],
        "t2dm": "NA",
    }, index=pd.Index([str(s) for s in shared], name="sample"))
    return df, counts


def main():
    print("== harmonising cohorts ==")
    train_df, train_mat = harmonise_kamzolas()
    print(f"  kamzolas train pool: {len(train_df)} samples, {train_mat.shape[0]} genes")
    epos_df, epos_mat = harmonise_epos()
    print(f"  EPos test pool: {len(epos_df)} samples, {epos_mat.shape[0]} genes")
    gubra_df, gubra_mat = harmonise_gubra()
    print(f"  Gubra test pool: {len(gubra_df)} samples ({int(gubra_df['fibrosis'].notna().sum())} staged), {gubra_mat.shape[0]} genes")

    # scale harmonisation: per-sample z-scores so differently-processed matrices are comparable
    train_mat, epos_mat, gubra_mat = (standardize_sample(m) for m in (train_mat, epos_mat, gubra_mat))
    print("  per-sample standardisation applied (log1p where non-negative, then z-score)")

    train_df = train_df[train_df["cohort"].isin(TRAIN_COHORTS)]
    train_df = train_df[train_df["fibrosis"].notna()]
    print(f"  -> train (SANYAL+UCAM, staged): {len(train_df)}")
    print(f"  train fibrosis distribution: {train_df['fibrosis'].value_counts().sort_index().to_dict()}")

    print("== feature selection (train-side top variance, restricted to shared gene space) ==")
    # all matrices must carry the prompt genes; select top-variance among the train∩test intersection
    shared_genes = sorted(set(train_mat.index) & set(epos_mat.index) & set(gubra_mat.index))
    print(f"  gene space: train={len(train_mat.index)} epos={len(epos_mat.index)} gubra={len(gubra_mat.index)} -> shared={len(shared_genes)}")
    tr_shared = train_mat.loc[shared_genes]
    genes_single = top_genes(tr_shared, N_SINGLE)
    genes_pair = top_genes(tr_shared, N_PAIR)
    print(f"  single={len(genes_single)} pair={len(genes_pair)} (train-side selection over shared space — no test labels touched)")

    print("== building TRAIN prompts ==")
    rec = build_single_format(train_df, train_mat, genes_single, "train", "MB-1", "kamzolas")
    rec += build_pairwise(train_df, train_mat, genes_pair, "train", "MB-1", "kamzolas")
    write_jsonl(rec, f"{OUT}/MB-10xx_liver_train.jsonl.gz",
                meta=dict(builder="kamzolas SANYAL+UCAM", genes_single=N_SINGLE, genes_pair=N_PAIR,
                          counts_sha=sha16(f"{REV}/data/kamzolas/batch_corrected_counts_(dataset+gender).csv")))

    print("== building TEST prompts (frozen) ==")
    rec = []
    for df, mat, name in ((epos_df, epos_mat, "EPOS"), (gubra_df, gubra_mat, "GUBRA")):
        d = df[df["fibrosis"].notna()]
        rec += build_single_format(d, mat, [g for g in genes_single if g in mat.index], "test", "MB-2", name)
        rec += build_pairwise(d, mat, [g for g in genes_pair if g in mat.index], "test", "MB-2", name)
    write_jsonl(rec, f"{OUT}/MB-20xx_liver_test.jsonl.gz",
                meta=dict(builder="EPos+Gubra frozen test", genes_from_train=True,
                          epos_sha=sha16(f"{REV}/data/kamzolas/EPoS_dataset/EPoS_counts.tsv.zip"),
                          gubra_sha=sha16(f"{REV}/data/kamzolas/Gubra_dataset/Normalised_Counts_GUBRA.txt")))

    print("== manifest ==")
    manifest = dict(
        version="v3-freeze-1", created="2026-09-29", seed=SEED,
        recipe="Zhavoronkov et al. Cell 189:5980-5994 (2026), LongevityBench",
        rules=[
            "test = EPos + Gubra, frozen forever; no external_v3 or Fujiwara data in this freeze",
            "features selected on train side only (over train/test shared gene space)",
            "pairwise prompts intra-cohort only",
            "per-sample label-free standardisation (log1p if non-negative, then z-score) applied to every matrix before prompting",
        ],
        files={f: sha16(os.path.join(OUT, f)) for f in sorted(os.listdir(OUT)) if f.endswith(".jsonl.gz")},
    )
    json.dump(manifest, open(f"{OUT}/MANIFEST.json", "w"), indent=1)
    print(json.dumps({k: manifest[k] for k in ("version", "rules")}, indent=1))
    print(f"done in {time.time()-T0:.1f}s")


if __name__ == "__main__":
    main()
