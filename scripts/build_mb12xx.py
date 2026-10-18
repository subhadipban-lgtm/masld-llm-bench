#!/usr/bin/env python3
"""Build MB-12xx: staged-liver TRAIN pool extension (freeze-14).

Per the Antwerp catalog 'Take' decisions + 2026-10-18 acquisition:
- GSE135251 (Govaere): 216 biopsies, per-sample fibrosis stage F0-F3 +
  NAS score; per-sample counts in RAW.tar (Ensembl) -> symbols via the
  archived ensembl_to_symbol_cache. Tasks MB-1201/1202/1205/1206.
- GSE167523 (Kozumi): 98 biopsies, NAFL/NASH binary from the phenotype
  xlsx (51/47; no fibrosis staging — resolved 2026-10-18). Task MB-1221.
- GSE130970 DEFERRED: entrez-id counts need a symbol map + title join
  (next session).

All TRAIN-side (frozen tests untouched). Panel: top-200 MAD genes per
cohort (label-free); per-sample log1p + z (program rule).
Output: prompts/MB-12xx_staged_train.jsonl.gz + MANIFEST v3-freeze-14.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
import tarfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20260929
PANEL_N = 200

AMI = Path("/Users/subhadipbanerjee/ami.subhadipbanerjee@gmail.com - Google Drive/My Drive")
DATA = AMI / "masld-llm" / "data"
REV = AMI / "masld-llm-archive" / "masld-revision-local-2026-10-18" / "data" / "geo_metadata"
ROOT = Path("/Users/subhadipbanerjee/masld-llm")
PROMPTS = ROOT / "prompts"
MANIFEST = PROMPTS / "MANIFEST.json"

VERBS = [
    "The following data come from a human liver biopsy transcriptome study.\n",
    "Below is a bulk RNA-seq profile of human liver tissue.\n",
    "A liver-derived transcriptomic profile follows.\n",
]


def sha16(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def fmt_genes(genes, z_col):
    return ", ".join(f"{g}={v:.2f}" for g, v in zip(genes, z_col))


def panel_z(mat: pd.DataFrame):
    """mat: genes x samples counts -> top-MAD panel genes, per-sample log1p+z."""
    vals = mat.astype(float)
    mad = (vals.sub(vals.median(axis=1), axis=0)).abs().median(axis=1)
    panel = mad.sort_values(ascending=False).head(PANEL_N).index.tolist()
    log = np.log1p(vals.loc[panel].clip(lower=0))
    z = (log - log.mean(axis=0)) / log.std(axis=0).clip(1e-9)
    return panel, z


def parse_soft_labels(soft_path: Path):
    """GSE135251 SOFT -> {GSM: {'title', 'fib', 'nas'}} sequential blocks."""
    out, cur = {}, None
    with gzip.open(soft_path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.startswith("!Sample_geo_accession"):
                if cur and cur.get("gsm"):
                    out[cur["gsm"]] = cur
                cur = {"gsm": line.split("= ", 1)[1].strip()}
            elif cur is None:
                continue
            elif line.startswith("!Sample_title"):
                cur["title"] = line.split("= ", 1)[1].strip()
            elif line.startswith("!Sample_characteristics_ch1"):
                m = re.search(r"fibrosis stage:\s*(\d+)", line)
                if m:
                    cur["fib"] = int(m.group(1))
                m = re.search(r"nas score:\s*(\d+)", line)
                if m:
                    cur["nas"] = int(m.group(1))
    if cur and cur.get("gsm"):
        out[cur["gsm"]] = cur
    return out


def build_135251(records: list):
    labels = parse_soft_labels(DATA / "GSE135251_family.soft.gz")
    staged = {g: v for g, v in labels.items() if "fib" in v}
    print(f"135251: {len(labels)} SOFT samples, {len(staged)} with fibrosis stage")

    ens2sym = {}
    with open(REV / "ensembl_to_symbol_cache.csv") as f:
        for row in f.read().splitlines()[1:]:
            if "," in row:
                e, s = row.split(",", 1)
                ens2sym[e.strip()] = s.strip()

    tar = tarfile.open(DATA / "GSE135251_RAW.tar", "r")
    cols = {}
    for m in tar.getmembers():
        gsm = m.name.split("_")[0]
        if gsm not in staged:
            continue
        text = gzip.decompress(tar.extractfile(m).read()).decode()
        counts = {}
        for line in text.splitlines():
            parts = line.split()
            if len(parts) == 2:
                g, c = parts
                sym = ens2sym.get(g.split(".")[0])
                if sym:
                    counts[sym] = counts.get(sym, 0) + int(c)
        cols[gsm] = counts
    print(f"135251: parsed {len(cols)} sample count vectors, symbols mapped")

    genes = sorted(set().union(*[set(c) for c in cols.values()]))
    mat = pd.DataFrame(0.0, index=genes, columns=list(cols))
    for gsm, c in cols.items():
        for g, v in c.items():
            mat.loc[g, gsm] = v
    panel, z = panel_z(mat)

    f_order = sorted(staged)
    for i, gsm in enumerate(sorted(cols)):
        v = staged[gsm]
        genes_str = fmt_genes(panel, z[gsm].values)
        verb = VERBS[i % len(VERBS)]
        base = verb + f"Liver biopsy profile.\nGene expression (counts, log1p+z): {genes_str}\n"
        records.append({"task": "MB-1201", "split": "train", "sample": gsm,
                        "source": "GSE135251",
                        "prompt": base + "Is fibrosis ADVANCED (stage F2-F3) rather than early (F0-F1)? Answer yes or no.",
                        "answer": "yes" if v["fib"] >= 2 else "no"})
        records.append({"task": "MB-1202", "split": "train", "sample": gsm,
                        "source": "GSE135251",
                        "prompt": base + "Which fibrosis stage does this profile indicate? Answer with one of F0, F1, F2, F3, F4.",
                        "answer": f"F{v['fib']}"})
        records.append({"task": "MB-1205", "split": "train", "sample": gsm,
                        "source": "GSE135251",
                        "prompt": base + "Estimate the fibrosis stage on the ordinal scale 0-4. Answer with a single number 0-4.",
                        "answer": str(v["fib"])})
        if "nas" in v:
            records.append({"task": "MB-1206", "split": "train", "sample": gsm,
                            "source": "GSE135251",
                            "prompt": base + "Estimate the NAFLD activity score (NAS, 0-8). Answer with a single number 0-8.",
                            "answer": str(v["nas"])})
    from collections import Counter
    print("135251 fibrosis dist:", Counter(staged[g]["fib"] for g in cols))
    return len(cols)


def build_167523(records: list):
    mat = pd.read_csv(DATA / "GSE167523_Raw_gene_counts_matrix.txt.gz",
                      sep="\t", index_col=0)
    mat = mat[~mat.index.astype(str).str.startswith("__")]
    phen = pd.read_excel(DATA / "GSE167523_Sample_phenotype_correspondence.xlsx")
    label_of = {f"NAFLD{int(r['Sample ID']):02d}": str(r["NAFL/NASH"]).strip()
                for _, r in phen.iterrows()}
    panel, z = panel_z(mat)
    n = 0
    from collections import Counter
    used = Counter()
    for i, col in enumerate([c for c in mat.columns if c in label_of]):
        lab = label_of[col]
        used[lab] += 1
        genes_str = fmt_genes(panel, z[col].values)
        verb = VERBS[i % len(VERBS)]
        records.append({"task": "MB-1221", "split": "train", "sample": col,
                        "source": "GSE167523",
                        "prompt": verb + f"Liver biopsy profile.\nGene expression (counts, log1p+z): {genes_str}\n"
                        "Does this profile indicate NASH (rather than non-alcoholic fatty liver, NAFL)? Answer yes or no.",
                        "answer": "yes" if lab.upper() == "NASH" else "no"})
        n += 1
    print(f"167523: {n} samples | labels {dict(used)}")
    return n


def main():
    records = []
    n1 = build_135251(records)
    n2 = build_167523(records)
    out = PROMPTS / "MB-12xx_staged_train.jsonl.gz"
    meta = {"n_records": len(records), "seed": SEED, "built": "2026-10-18",
            "builder": "staged-liver train pool extension (Antwerp Take set)",
            "cohorts": {"GSE135251": n1, "GSE167523": n2},
            "deferred": "GSE130970 (entrez->symbol map + title join pending)"}
    with gzip.open(out, "wt", encoding="utf-8") as f:
        f.write(json.dumps({"__meta__": meta}) + "\n")
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    from collections import Counter
    print(f"wrote {len(records)} records | tasks {dict(Counter(r['task'] for r in records))}")

    m = json.loads(MANIFEST.read_text())
    m["version"] = "v3-freeze-14"
    m["counts"][out.name] = len(records)
    m["files"][out.name] = sha16(out)
    m["rules"] = [r for r in m.get("rules", []) if not r.startswith("MB-12xx")] + [
        "MB-12xx: staged-liver TRAIN pool extension (freeze-14, Antwerp 'Take' "
        "set): GSE135251 216 biopsies F0-F3 + NAS (1201 advanced binary, 1202 "
        "F0-F3 multiclass, 1205 fibrosis 0-3 reg, 1206 NAS reg; Ensembl->symbol "
        "via archived cache) + GSE167523 98 NAFL/NASH binary (1221); GSE130970 "
        "deferred (entrez mapping); top-200 MAD panels per cohort; per-sample "
        "log1p+z; TRAIN-side only — frozen tests untouched"
    ]
    MANIFEST.write_text(json.dumps(m, indent=1))
    print(f"MANIFEST -> {m['version']}")


if __name__ == "__main__":
    main()
