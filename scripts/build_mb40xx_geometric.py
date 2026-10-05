#!/usr/bin/env python3
"""MB-40xx — Geometric-omics prompt family (the geometric compression layer).

Novel task family: instead of raw gene=value lists, each patient is described
by GEOMETRIC features of their transcriptome, computed in a leakage-proof way:
  - train-side co-expression graph -> Louvain modules
  - per-patient module activity scores (mean z of member genes)
  - UMAP patient manifold (train-fitted) -> patient's position + local density
  - k-NN severity-neighbourhood composition in manifold space

Prompts are ~60 tokens (vs ~2000 for raw gene lists) — the "short-LLM" thesis.
Same EPos patients + labels as MB-20xx, so raw-vs-geometry is directly
measurable per patient.

Split discipline: graph, UMAP, scalers fitted on TRAIN (Kamzolas+external)
samples only; test patients are embedded, never used for fitting.
"""
import gzip, json, os, random, sys, time
import numpy as np
import pandas as pd

T0 = time.time()
SEED = 20260929
rng = random.Random(SEED)

ROOT = "/Users/subhadipbanerjee/masld-llm"
sys.path.insert(0, f"{ROOT}/scripts")
from build_mb10xx import (VERBALIZATIONS, pick, write_jsonl, fmt_expr,
                          standardize_sample, harmonise_kamzolas, harmonise_epos,
                          top_genes)

OUT = f"{ROOT}/prompts"
REV = "/Users/subhadipbanerjee/masld-revision"

N_GENES = 2000          # graph-building gene set (train-side top-variance)
N_UMAP_NEIGHBORS = 15

GEO_INTRO = [
    "You are analyzing the geometric structure of a liver transcriptome from a MASLD study.",
    "The following is a structural summary of a patient's liver gene-expression profile in a steatotic liver disease cohort.",
    "Below is a geometry-aware summary of a human liver biopsy transcriptome.",
]
GEO_LINE = [
    "Module activities: {modules}",
    "Co-expression module scores: {modules}",
    "Transcriptome module structure: {modules}",
]
GEO_MANIFOLD = [
    "Manifold position: {manifold}",
    "Patient-manifold embedding: {manifold}",
    "Position on the cohort expression manifold: {manifold}",
]
ASK_BINARY = [
    "Does this geometric profile indicate advanced fibrosis (F3-F4)? Answer yes or no.",
    "Is this structural profile consistent with advanced fibrosis? Answer with yes or no.",
]
ASK_MULTI = [
    "Assign the fibrosis stage of this biopsy: F0, F1, F2, F3, or F4.",
    "Which fibrosis stage best matches this profile? Answer with one of F0, F1, F2, F3, F4.",
]
ASK_REG = [
    "Predict the numeric fibrosis stage (0-4) of this biopsy.",
    "Estimate the exact Kleiner fibrosis stage as a number between 0 and 4.",
]

def main():
    print("== loading cohorts (train: Kamzolas; test: EPos) ==")
    train_df, train_mat = harmonise_kamzolas()
    epos_df, epos_mat = harmonise_epos()
    train_df = train_df[train_df["fibrosis"].notna()]
    epos_df = epos_df[epos_df["fibrosis"].notna()]

    # shared gene space
    shared_genes = sorted(set(train_mat.index) & set(epos_mat.index))
    print(f"shared genes: {len(shared_genes)}")
    train_mat = standardize_sample(train_mat.loc[shared_genes])
    epos_mat = standardize_sample(epos_mat.loc[shared_genes])

    # ---- 1. train-side gene selection ----
    genes = top_genes(train_mat, min(N_GENES, len(shared_genes)))

    # ---- 2. co-expression graph -> Louvain modules (TRAIN ONLY) ----
    print("== building co-expression graph (train-side) ==")
    import networkx as nx
    try:
        import community as community_louvain
    except ImportError:
        import community.community_louvain as community_louvain
    X = train_mat.loc[genes]
    corr = np.corrcoef(X.values)
    G = nx.Graph()
    G.add_nodes_from(genes)
    thr = 0.3
    for i in range(len(genes)):
        for j in range(i + 1, len(genes)):
            if abs(corr[i, j]) >= thr:
                G.add_edge(genes[i], genes[j], weight=float(abs(corr[i, j])))
    partition = community_louvain.best_partition(G, random_state=SEED, weight="weight")
    modules = {}
    for gene, mod in partition.items():
        modules.setdefault(mod, []).append(gene)
    modules = {k: v for k, v in modules.items() if len(v) >= 5}
    mod_names = {k: f"M{k+1}" for k in sorted(modules)}
    print(f"modules: {len(modules)} (sizes {[len(v) for v in modules.values()][:12]}...)")

    # ---- 3. per-patient module activity ----
    def module_activities(mat):
        out = {}
        for mod, gl in modules.items():
            out[mod_names[mod]] = mat.loc[gl].mean(axis=0)
        return pd.DataFrame(out)
    act_train = module_activities(train_mat)
    act_test = module_activities(epos_mat)

    # ---- 4. UMAP manifold fitted on TRAIN activities ----
    print("== fitting UMAP on train module activities ==")
    import umap
    reducer = umap.UMAP(n_neighbors=N_UMAP_NEIGHBORS, min_dist=0.3,
                        random_state=SEED, n_components=2)
    emb_train = reducer.fit_transform(act_train.values)
    emb_test = reducer.transform(act_test.values)

    # local density: mean distance to 5 nearest TRAIN neighbours
    from sklearn.neighbors import NearestNeighbors
    nn = NearestNeighbors(n_neighbors=6).fit(emb_train)
    def local_density(emb):
        d, _ = nn.kneighbors(emb)
        return d[:, 1:].mean(axis=1)  # skip self-ish zero dist
    dens_test = local_density(emb_test)
    dens_train = local_density(emb_train)

    # k-NN severity neighbourhood (train labels only)
    nnsev = NearestNeighbors(n_neighbors=11).fit(emb_train)
    def neigh_severity(emb, train_labels):
        _, idx = nnsev.kneighbors(emb)
        return train_labels[idx].mean(axis=1)
    tr_labels = train_df["fibrosis"].reindex(act_train.index).values
    sev_train = neigh_severity(emb_train, tr_labels)
    sev_test = neigh_severity(emb_test, tr_labels)

    def fmt_act(row):
        parts = []
        for m in sorted(row.index):
            v = row[m]
            lvl = "high" if v > 0.5 else "mid-high" if v > 0.15 else "mid" if v > -0.15 else "mid-low" if v > -0.5 else "low"
            parts.append(f"{m} {lvl}")
        return ", ".join(parts)

    def fmt_manifold(emb, dens, sev):
        x, y = emb
        region = "upper" if y > 0 else "lower"
        dens_lvl = "dense" if dens < np.median(dens_train) else "sparse"
        return (f"({x:.1f}, {y:.1f}) {region} region, {dens_lvl} neighbourhood, "
                f"mean neighbour stage {sev:.1f}")

    def build(df, act, emb, dens, sev, split, prefix):
        recs = []
        for sid in df.index:
            if sid not in act.index:
                continue
            row = df.loc[sid]
            base = (f"{pick(GEO_INTRO)}\n"
                    f"{pick(GEO_LINE).format(modules=fmt_act(act.loc[sid]))}.\n"
                    f"{pick(GEO_MANIFOLD).format(manifold=fmt_manifold(emb[list(act.index).index(sid)], dens[list(act.index).index(sid)], sev[list(act.index).index(sid)]))}.\n")
            recs.append(dict(task=f"{prefix}01", split=split, sample=str(sid), source="geo",
                prompt=base + pick(ASK_BINARY),
                answer="yes" if row["fibrosis" if "fibrosis" in df.columns else "Fibrosis"] >= 3 else "no"))
            recs.append(dict(task=f"{prefix}02", split=split, sample=str(sid), source="geo",
                prompt=base + pick(ASK_MULTI),
                answer=f"F{int(row['fibrosis' if 'fibrosis' in df.columns else 'Fibrosis'])}"))
            recs.append(dict(task=f"{prefix}05", split=split, sample=str(sid), source="geo",
                prompt=base + pick(ASK_REG),
                answer=f"{row['fibrosis' if 'fibrosis' in df.columns else 'Fibrosis']:.0f}"))
        return recs

    train_col = "fibrosis"
    recs_train = []
    # train prompts use Kamzolas labels
    for sid in train_df.index:
        if sid not in act_train.index: continue
        row = train_df.loc[sid]
        i = list(act_train.index).index(sid)
        base = (f"{pick(GEO_INTRO)}\n"
                f"{pick(GEO_LINE).format(modules=fmt_act(act_train.loc[sid]))}.\n"
                f"{pick(GEO_MANIFOLD).format(manifold=fmt_manifold(emb_train[i], dens_train[i], sev_train[i]))}.\n")
        recs_train.append(dict(task="MB-4001", split="train", sample=str(sid), source="geo_train",
            prompt=base + pick(ASK_BINARY), answer="yes" if row["fibrosis"] >= 3 else "no"))
        recs_train.append(dict(task="MB-4002", split="train", sample=str(sid), source="geo_train",
            prompt=base + pick(ASK_MULTI), answer=f"F{int(row['fibrosis'])}"))
        recs_train.append(dict(task="MB-4005", split="train", sample=str(sid), source="geo_train",
            prompt=base + pick(ASK_REG), answer=f"{row['fibrosis']:.0f}"))

    recs_test = []
    for sid in epos_df.index:
        if sid not in act_test.index: continue
        row = epos_df.loc[sid]
        i = list(act_test.index).index(sid)
        base = (f"{pick(GEO_INTRO)}\n"
                f"{pick(GEO_LINE).format(modules=fmt_act(act_test.loc[sid]))}.\n"
                f"{pick(GEO_MANIFOLD).format(manifold=fmt_manifold(emb_test[i], dens_test[i], sev_test[i]))}.\n")
        recs_test.append(dict(task="MB-4001", split="test", sample=str(sid), source="geo_epos",
            prompt=base + pick(ASK_BINARY), answer="yes" if row["fibrosis"] >= 3 else "no"))
        recs_test.append(dict(task="MB-4002", split="test", sample=str(sid), source="geo_epos",
            prompt=base + pick(ASK_MULTI), answer=f"F{int(row['fibrosis'])}"))
        recs_test.append(dict(task="MB-4005", split="test", sample=str(sid), source="geo_epos",
            prompt=base + pick(ASK_REG), answer=f"{row['fibrosis']:.0f}"))

    write_jsonl(recs_train, f"{OUT}/MB-40xx_geo_train.jsonl.gz",
                meta=dict(builder="geometric compression layer v1",
                          n_modules=len(modules), n_genes_graph=len(genes),
                          fit="co-expression graph + UMAP + kNN fitted on Kamzolas train only"))
    write_jsonl(recs_test, f"{OUT}/MB-40xx_geo_test.jsonl.gz",
                meta=dict(builder="geometric compression, EPos embedded (never fitted)"))
    # prompt length comparison
    import statistics
    rawlens, geolens = [], []
    with gzip.open(f"{OUT}/MB-20xx_liver_test.jsonl.gz", "rt") as f:
        f.readline()
        for line in f:
            r = json.loads(line)
            if r["task"] == "MB-2001":
                rawlens.append(len(r["prompt"]))
            if len(rawlens) > 50: break
    geolens = [len(r["prompt"]) for r in recs_test if r["task"] == "MB-4001"]
    print(f"prompt chars: raw {statistics.mean(rawlens):.0f} vs geometric {statistics.mean(geolens):.0f} "
          f"({100*statistics.mean(geolens)/statistics.mean(rawlens):.0f}% compression)")
    print(f"done in {time.time()-T0:.0f}s")


if __name__ == "__main__":
    main()
