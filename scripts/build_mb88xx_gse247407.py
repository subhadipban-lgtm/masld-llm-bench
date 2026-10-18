#!/usr/bin/env python3
"""Build MB-88xx: PHH FFA-perturbation test corpus (GSE247407).

Per ANALYSIS_PLAN_C3_addendum (MB-88xx perturbation family): GSE247407 is
30 primary-human-hepatocyte cultures — 5 donor preparations x 3 replicates
x {Control, FFA-treated} (F95P = second prep of donor F95). SOFT gives
sequential per-sample blocks (individual / treatment); matrix columns are
<individual><C|F><rep>.

Tasks:
  MB-8801 (yes/no): was this culture treated with free fatty acids?

Design notes:
- sample = DONOR prep id (F95, M95, H20, H961, F95P): 6 records share a
  sample so the gate's grouped CV blocks donor leakage by construction.
- Panel: top-200 MAD genes (label-free, counts, gene_name symbols);
  per-sample log1p + z (program-wide rule).
- Multi-compound extension (HepG2 DRUG-seq, E-MTAB-15601 etc.) identified
  2026-10-18 as the future MB-8801+ multi-class source; NOT pulled yet.

Source data on Drive (disk-offload policy): masld-llm/data/.
Output: prompts/MB-88xx_perturb_test.jsonl.gz + MANIFEST v3-freeze-12.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20260929

ROOT = Path("/Users/subhadipbanerjee/masld-llm")
DRIVE_DATA = Path("/Users/subhadipbanerjee/ami.subhadipbanerjee@gmail.com - Google Drive"
                  "/My Drive/masld-llm/data")
LOCAL_DATA = ROOT / "data"
PROMPTS = ROOT / "prompts"
MANIFEST = PROMPTS / "MANIFEST.json"

VERBALIZATIONS = [
    "The following data come from a primary human hepatocyte (PHH) culture experiment.\n",
    "Below is a bulk RNA-seq profile of cultured primary human hepatocytes.\n",
    "A primary hepatocyte culture transcriptome follows.\n",
]
PROMPT_TEMPLATE = (
    "PHH culture profile.\nGene expression (counts, log1p+z): {genes}\n"
    "Was this hepatocyte culture treated with free fatty acids (FFA) to "
    "induce steatosis? Answer yes or no."
)


def sha16(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def parse_soft(soft_path: Path) -> list[dict]:
    """Sequential per-sample blocks -> [{individual, treatment, rep, title}]."""
    out, cur = [], {}
    title = None
    with gzip.open(soft_path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.startswith("!Sample_title"):
                if cur:
                    out.append(cur)
                title = line.split("= ", 1)[1].strip()
                cur = {"title": title}
            elif line.startswith("!Sample_characteristics_ch1") and cur:
                val = line.split(": ", 1)[-1].strip()
                key = line.split(": ", 1)[0].split("ch1 =")[-1].strip()
                if key in ("individual", "treatment"):
                    cur[key] = val
                m = re.search(r"rep(\d+)", title or "")
                if m and "rep" not in cur:
                    cur["rep"] = m.group(1)
    if cur:
        out.append(cur)
    return [s for s in out if "individual" in s and "treatment" in s]


def main() -> None:
    data_dir = DRIVE_DATA if DRIVE_DATA.is_dir() else LOCAL_DATA
    soft = data_dir / "GSE247407_family.soft.gz"
    counts = data_dir / "GSE247407_gene_count.txt.gz"
    for p in (soft, counts):
        if not p.exists():
            sys.exit(f"missing source: {p}")

    samples = parse_soft(soft)
    print(f"SOFT samples: {len(samples)} | "
          f"treatments={sorted(set(s['treatment'] for s in samples))}")

    # matrix: gene_id x sample cols + gene_name annotation column
    mat = pd.read_csv(counts, sep="\t", index_col=0)
    gene_names = mat["gene_name"].astype(str)
    expr = mat.drop(columns=[c for c in ("gene_name", "gene_chr", "gene_start",
                                         "gene_end", "gene_strand", "gene_length",
                                         "gene_biotype", "gene_description",
                                         "tf_family") if c in mat.columns])
    expr = expr.loc[:, ~expr.columns.str.startswith("gene_")]
    print(f"matrix: {expr.shape[0]} genes x {expr.shape[1]} cultures")

    # map SOFT blocks -> matrix columns <individual><C|F><rep>
    col_of = {}
    for s in samples:
        cond = "C" if s["treatment"].lower().startswith("control") else "F"
        col = f"{s['individual']}{cond}{s.get('rep', '')}"
        if col in expr.columns:
            col_of[col] = s
        else:
            m = [c for c in expr.columns if c.startswith(s["individual"]) and cond in c
                 and c.endswith(str(s.get("rep", "")))]
            if len(m) == 1:
                col_of[m[0]] = s
    print(f"matched {len(col_of)}/{len(samples)} SOFT blocks to matrix columns")
    if len(col_of) < len(samples):
        print("unmatched columns:", sorted(set(expr.columns) - set(col_of)))
        sys.exit("sample mapping incomplete — refusing to build")

    # top-200 MAD genes (label-free), per-sample log1p+z
    vals = expr.astype(float)
    mad = (vals.sub(vals.median(axis=1), axis=0)).abs().median(axis=1)
    panel = mad.sort_values(ascending=False).head(200).index
    sub = vals.loc[panel]
    log = np.log1p(sub.clip(lower=0))
    z = (log - log.mean(axis=0)) / log.std(axis=0).clip(1e-9)

    records = []
    for idx, (col, s) in enumerate(sorted(col_of.items())):
        genes = ", ".join(f"{gene_names[g]}={z.loc[g, col]:.2f}" for g in panel)
        verb = VERBALIZATIONS[idx % len(VERBALIZATIONS)]
        treated = not s["treatment"].lower().startswith("control")
        records.append({
            "task": "MB-8801",
            "split": "test",
            "sample": s["individual"],  # donor prep = CV group (leakage block)
            "source": "GSE247407",
            "prompt": verb + PROMPT_TEMPLATE.format(genes=genes),
            "answer": "yes" if treated else "no",
        })
    n_yes = sum(1 for r in records if r["answer"] == "yes")
    print(f"records: {len(records)} ({n_yes} FFA / {len(records)-n_yes} control), "
          f"groups={len(set(r['sample'] for r in records))}")

    out = PROMPTS / "MB-88xx_perturb_test.jsonl.gz"
    meta = {
        "n_records": len(records), "seed": SEED, "built": "2026-10-18",
        "builder": "GSE247407 PHH FFA perturbation test (C3 addendum MB-88xx)",
        "design": "sample=donor prep (5 groups x 6 cultures) so grouped CV "
                  "blocks donor leakage; panel top-200 MAD genes; per-sample "
                  "log1p+z; multi-compound extension = HepG2 DRUG-seq "
                  "(E-MTAB-15601, identified not pulled)",
    }
    with gzip.open(out, "wt", encoding="utf-8") as f:
        f.write(json.dumps({"__meta__": meta}) + "\n")
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(records)} records -> {out}")

    m = json.loads(MANIFEST.read_text())
    m["version"] = "v3-freeze-12"
    m["counts"][out.name] = len(records)
    m["files"][out.name] = sha16(out)
    m["rules"] = [r for r in m.get("rules", []) if not r.startswith("MB-88xx")] + [
        "MB-88xx: GSE247407 PHH FFA perturbation test (30 cultures = 5 donor "
        "preps x 3 reps x control/FFA; F95P = second F95 prep); 8801 FFA "
        "yes/no; sample=donor prep so grouped CV blocks donor leakage; panel "
        "top-200 MAD genes (symbols); per-sample log1p+z; multi-compound "
        "extension identified: HepG2 DRUG-seq E-MTAB-15601 (not pulled)"
    ]
    MANIFEST.write_text(json.dumps(m, indent=1))
    print(f"MANIFEST -> {m['version']}")


if __name__ == "__main__":
    main()
