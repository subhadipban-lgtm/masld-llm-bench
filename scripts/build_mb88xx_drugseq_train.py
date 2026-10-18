#!/usr/bin/env python3
"""Build MB-88xx DRUG-seq TRAIN corpus (E-MTAB-15601, HepG2, 40 compounds).

TRAIN-side perturbation resource for the C3 transfer claim: train the
compact models on compound-perturbation QA in HepG2, then test transfer on
the FROZEN PHH test (MB-8801, GSE247407 — never trained on).

Design:
- Tasks: MB-8811 'which compound' multi-class (40 compounds, subsample
  12 samples each for prompt budget), MB-8812 treated-vs-DMSO yes/no
  (12/compound + all 32 DMSO).
- Panel: top-200 MAD genes (Ensembl -> keep ids as-is; the matrix uses
  Ensembl), label-free; per-sample log1p + z (program rule).
- No dose/time encoding in v1 tasks (dose-gradient tasks need the design
  table; defer).

Source on Drive (disk policy): masld-llm/data/emtab15601/.
Output: prompts/MB-88xx_drugseq_train.jsonl.gz + MANIFEST v3-freeze-13.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20260929
rng = random.Random(SEED)

ROOT = Path("/Users/subhadipbanerjee/masld-llm")
DRIVE_DATA = Path("/Users/subhadipbanerjee/ami.subhadipbanerjee@gmail.com - Google Drive"
                  "/My Drive/masld-llm/data/emtab15601")
LOCAL_DATA = ROOT / "data" / "emtab15601"
PROMPTS = ROOT / "prompts"
MANIFEST = PROMPTS / "MANIFEST.json"

PER_COMPOUND = 12
PANEL_N = 200

VERBALIZATIONS = [
    "The following data come from a DRUG-seq compound screen in HepG2 hepatoma cells.\n",
    "Below is a bulk RNA-seq profile of HepG2 cells treated with a compound.\n",
    "A compound-perturbation transcriptome from a HepG2 DRUG-seq screen follows.\n",
]
T_8811 = (
    "HepG2 compound-screen profile.\nGene expression (counts, log1p+z): {genes}\n"
    "Which compound was applied to these cells? Answer with one of: {options}."
)
T_8812 = (
    "HepG2 compound-screen profile.\nGene expression (counts, log1p+z): {genes}\n"
    "Were these cells treated with a compound (any drug), rather than the "
    "DMSO vehicle control? Answer yes or no."
)


def sha16(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def main() -> None:
    data_dir = DRIVE_DATA if DRIVE_DATA.is_dir() else LOCAL_DATA
    meta = pd.read_csv(data_dir / "processed_metadata.csv")
    counts = pd.read_csv(data_dir / "raw_counts.csv", index_col=0)
    print(f"metadata {meta.shape} | counts {counts.shape}")

    # join: metadata Sample ID must match counts columns
    cols = [c for c in counts.columns if c in set(meta["Sample ID"])]
    print(f"counts columns matching metadata: {len(cols)}/{counts.shape[1]}")
    if len(cols) < 1000:
        sys.exit("sample join failed — inspect column naming")

    sub = counts[cols]
    vals = sub.astype(float)
    mad = (vals.sub(vals.median(axis=1), axis=0)).abs().median(axis=1)
    panel = mad.sort_values(ascending=False).head(PANEL_N).index.tolist()
    log = np.log1p(vals.loc[panel].clip(lower=0))
    z = (log - log.mean(axis=0)) / log.std(axis=0).clip(1e-9)

    comp_of = dict(zip(meta["Sample ID"], meta["Compound"]))
    by_compound: dict[str, list[str]] = {}
    for s in cols:
        by_compound.setdefault(comp_of[s], []).append(s)
    compounds = sorted(c for c in by_compound if c != "DMSO")
    print(f"{len(compounds)} compounds + DMSO x{len(by_compound.get('DMSO', []))}")

    records = []
    order = 0
    options = ", ".join(compounds)
    for comp in compounds:
        chosen = sorted(rng.sample(by_compound[comp], min(PER_COMPOUND, len(by_compound[comp]))))
        for s in chosen:
            genes = ", ".join(f"{g}={z.loc[g, s]:.2f}" for g in panel)
            verb = VERBALIZATIONS[order % len(VERBALIZATIONS)]
            records.append({
                "task": "MB-8811", "split": "train", "sample": s,
                "source": "E-MTAB-15601",
                "prompt": verb + T_8811.format(genes=genes, options=options),
                "answer": comp,
            })
            records.append({
                "task": "MB-8812", "split": "train", "sample": s,
                "source": "E-MTAB-15601",
                "prompt": verb + T_8812.format(genes=genes),
                "answer": "yes",
            })
            order += 1
    for s in sorted(by_compound.get("DMSO", [])):
        genes = ", ".join(f"{g}={z.loc[g, s]:.2f}" for g in panel)
        verb = VERBALIZATIONS[order % len(VERBALIZATIONS)]
        records.append({
            "task": "MB-8812", "split": "train", "sample": s,
            "source": "E-MTAB-15601",
            "prompt": verb + T_8812.format(genes=genes),
            "answer": "no",
        })
        order += 1

    n_11 = sum(1 for r in records if r["task"] == "MB-8811")
    n_12 = sum(1 for r in records if r["task"] == "MB-8812")
    out = PROMPTS / "MB-88xx_drugseq_train.jsonl.gz"
    meta_out = {
        "n_records": len(records), "seed": SEED, "built": "2026-10-18",
        "builder": "E-MTAB-15601 DRUG-seq HepG2 compound TRAIN corpus (C3 transfer)",
        "design": f"top-{PANEL_N} MAD genes, per-sample log1p+z; {len(compounds)} "
                  f"compounds x {PER_COMPOUND} subsample for 8811/8812-yes; "
                  "all DMSO for 8812-no; frozen PHH MB-8801 is the transfer test",
    }
    with gzip.open(out, "wt", encoding="utf-8") as f:
        f.write(json.dumps({"__meta__": meta_out}) + "\n")
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(records)} records (8811: {n_11}, 8812: {n_12}) -> {out}")

    m = json.loads(MANIFEST.read_text())
    m["version"] = "v3-freeze-13"
    m["counts"][out.name] = len(records)
    m["files"][out.name] = sha16(out)
    m["rules"] = [r for r in m.get("rules", []) if "MB-88xx DRUG-seq" not in r] + [
        "MB-88xx DRUG-seq TRAIN (freeze-13): E-MTAB-15601 HepG2, 40 compounds + "
        "DMSO (1196 samples); MB-8811 compound 40-class (subsample 12/compound), "
        "MB-8812 treated-vs-DMSO yes/no; top-200 MAD genes; per-sample log1p+z; "
        "TRAIN-side only — transfer test = frozen MB-8801 (GSE247407 PHH FFA)"
    ]
    MANIFEST.write_text(json.dumps(m, indent=1))
    print(f"MANIFEST -> {m['version']}")


if __name__ == "__main__":
    main()
