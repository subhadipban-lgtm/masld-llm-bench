#!/usr/bin/env python3
"""Extend MB-12xx with GSE130970 (freeze-15); GSE126848 documented blocked.

GSE130970: 78 liver biopsies (6 normal + 72 NAFLD), SOFT carries per-sample
fibrosis stage (F0=25/F1=28/F2=9/F3=14/F4=2) + steatosis grade; counts are
entrez-id keyed with titles matching SOFT exactly ('440349.1.X_1').
Entrez->symbol via Drive data/entrez_to_symbol_cache.csv (19,585 ids,
NCBI eutils, fetched 2026-10-19).

GSE126848 (57 liver, healthy/NAFLD/NASH/obese) NOT built: the counts file
keys samples by numeric patient ids absent from the SOFT (no per-sample
numeric characteristic); order-matching would gamble labels — the exact
failure mode the Gubra correction (freeze-6) taught us to refuse. Needs
the paper's sample sheet.

Tasks (train-side, prefix 121x): MB-1211 advanced-fibrosis binary,
MB-1212 F0-F4 multiclass, MB-1215 fibrosis 0-4 regression.
Existing MB-12xx records carried verbatim.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
from collections import Counter
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
CORPUS = PROMPTS / "MB-12xx_staged_train.jsonl.gz"
MANIFEST = PROMPTS / "MANIFEST.json"

VERBS = [
    "The following data come from a human liver biopsy transcriptome study.\n",
    "Below is a bulk RNA-seq profile of human liver tissue.\n",
    "A liver-derived transcriptomic profile follows.\n",
]


def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def parse_soft_staging(path):
    out, cur = {}, None
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.startswith("!Sample_title"):
                if cur and "fib" in cur:
                    out[cur["title"]] = cur
                cur = {"title": line.split("= ", 1)[1].strip()}
            elif cur is not None and line.startswith("!Sample_characteristics_ch1"):
                m = re.search(r"fibrosis stage:\s*(\d+)", line)
                if m:
                    cur["fib"] = int(m.group(1))
    if cur and "fib" in cur:
        out[cur["title"]] = cur
    return out


def main():
    staging = parse_soft_staging(REV / "GSE130970_family.soft.gz")
    print(f"130970 staged samples: {len(staging)}")

    ens2sym = {}
    with open(DATA / "ensembl_to_symbol_cache.csv") as f:
        for line in f.read().splitlines()[1:]:
            if "," in line:
                e, s = line.split(",", 1)
                ens2sym[e.strip()] = s.strip()
    ent2sym = {}
    with open(DATA / "entrez_to_symbol_cache.csv") as f:
        for line in f.read().splitlines()[1:]:
            if "," in line:
                e, s = line.split(",", 1)
                ent2sym[e.strip()] = s.strip()

    counts = pd.read_csv(REV / "GSE130970_counts_entrez.csv.gz", index_col=0, sep=",")
    counts.index = [str(i) for i in counts.index]
    counts = counts.loc[[i for i in counts.index if i in ent2sym]]
    counts.index = [ent2sym[i] for i in counts.index]
    counts = counts.groupby(counts.index).sum()
    cols = [c for c in counts.columns if c in staging]
    print(f"130970 matrix: {counts.shape[0]} symbol-genes x {len(cols)}/{counts.shape[1]} staged columns")
    if len(cols) < 70:
        sys.exit("join failed")

    vals = counts[cols].astype(float)
    mad = (vals.sub(vals.median(axis=1), axis=0)).abs().median(axis=1)
    panel = mad.sort_values(ascending=False).head(PANEL_N).index.tolist()
    log = np.log1p(vals.loc[panel].clip(lower=0))
    z = (log - log.mean(axis=0)) / log.std(axis=0).clip(1e-9)

    records = []
    for i, c in enumerate(sorted(cols)):
        fib = staging[c]["fib"]
        genes = ", ".join(f"{g}={z.loc[g, c]:.2f}" for g in panel)
        verb = VERBS[i % len(VERBS)]
        base = verb + f"Liver biopsy profile.\nGene expression (counts, log1p+z): {genes}\n"
        records.append({"task": "MB-1211", "split": "train", "sample": c, "source": "GSE130970",
                        "prompt": base + "Is fibrosis ADVANCED (stage F3-F4) rather than early (F0-F2)? Answer yes or no.",
                        "answer": "yes" if fib >= 3 else "no"})
        records.append({"task": "MB-1212", "split": "train", "sample": c, "source": "GSE130970",
                        "prompt": base + "Which fibrosis stage does this profile indicate? Answer with one of F0, F1, F2, F3, F4.",
                        "answer": f"F{fib}"})
        records.append({"task": "MB-1215", "split": "train", "sample": c, "source": "GSE130970",
                        "prompt": base + "Estimate the fibrosis stage on the ordinal scale 0-4. Answer with a single number 0-4.",
                        "answer": str(fib)})
    print("130970 fibrosis dist:", Counter(staging[c]["fib"] for c in cols))

    with gzip.open(CORPUS, "rt", encoding="utf-8") as f:
        lines = f.read().splitlines()
    meta = json.loads(lines[0])["__meta__"]
    keep = [json.loads(l) for l in lines[1:]]
    n_old = len(keep)
    keep = [r for r in keep if r.get("source") != "GSE130970"]  # idempotent re-run
    records = keep + records
    meta.update({"n_records": len(records), "built": "2026-10-19",
                 "revision": "freeze-15: + GSE130970 (78 biopsies, F0=25/F1=28/F2=9/F3=14/"
                             "F4=2; entrez->symbol via eutils cache); GSE126848 BLOCKED "
                             "(counts keyed by numeric patient ids absent from SOFT; "
                             "order-matching refused — needs paper sample sheet)"})
    with gzip.open(CORPUS, "wt", encoding="utf-8") as f:
        f.write(json.dumps({"__meta__": meta}) + "\n")
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"corpus: {n_old} -> {len(records)} records")

    m = json.loads(MANIFEST.read_text())
    m["version"] = "v3-freeze-15"
    m["counts"][CORPUS.name] = len(records)
    m["files"][CORPUS.name] = sha16(CORPUS)
    m["rules"] = [r for r in m.get("rules", [])
                  if not r.startswith("MB-12xx")] + [
        "MB-12xx: staged-liver TRAIN pool (freeze-15): GSE135251 216 F0-F4+NAS "
        "(1201/1202/1205/1206), GSE167523 98 NAFL/NASH (1221), GSE130970 78 "
        "biopsies F0-F4 (1211/1212/1215; entrez->symbol via eutils); "
        "GSE126848 BLOCKED (sample-key join unverifiable); top-200 MAD panels; "
        "per-sample log1p+z; TRAIN-side only"
    ]
    MANIFEST.write_text(json.dumps(m, indent=1))
    print(f"MANIFEST -> {m['version']}")


if __name__ == "__main__":
    main()
