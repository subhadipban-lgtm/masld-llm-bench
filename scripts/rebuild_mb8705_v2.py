#!/usr/bin/env python3
"""Rebuild MB-8705 (freeze-11): masked-protein regression replaces the
degenerate mean-level target (all freeze-10 golds saturated to '10.0').

Design (fixes two freeze-10 flaws):
1. Target: one held-out protein's per-sample z-score, predicted from the
   other 29 proteins of the same sample -> within-sample co-abundance task
   with real variance (z-scale MAE, SD units).
2. Standardisation: per-PROTEIN log1p + z across samples within each study
   (label-free). Per-SAMPLE z (the program-wide rule) would make the masked
   value arithmetically determined (panel z sums to 0) — a hidden-answer
   puzzle, not a prediction task; the deviation from the per-sample rule is
   deliberate and documented in the manifest rule.

MB-8701 records are carried over BYTE-IDENTICAL from the freeze-10 corpus
(their archive is already scored; log1p+z would only obscure the batch
signature the task measures anyway).

Mask choice is deterministic: per study, proteins ranked by variance; each
sample masks one of the top-5, rotating by sample order (seeded shuffle).

Source data lives on Drive after the 2026-10-18 disk offload
(ami: masld-llm/data/msv000094959/), with a local-data/ fallback.
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
                  "/My Drive/masld-llm/data/msv000094959")
LOCAL_DATA = ROOT / "data" / "msv000094959"
PROMPTS = ROOT / "prompts"
CORPUS = PROMPTS / "MB-87xx_liverplasma_test.jsonl.gz"
MANIFEST = PROMPTS / "MANIFEST.json"

STUDIES = {
    "Plasma_liver2": "Plasma_liver2_Report_Protein_Quant_Pivot.xls",
    "Souria72": "Souria72_Plasma_DirectDIA_Protein_Quant_Pivot.xls",
    "Lumos72": "Lumos72_Biognosys_Protein_Quant_Pivot.xls",
}
PANEL_N = 30
MASK_POOL = 5

VERBALIZATIONS = [
    "The following data come from a plasma proteome profiling experiment.\n",
    "Below is the protein quantification profile from a plasma sample.\n",
    "A plasma proteomics study follows.\n",
]

PROMPT_TEMPLATE = (
    "Plasma proteome profile ({n} proteins, log1p+z standardised): {genes}\n"
    "From the co-abundance pattern above, estimate the standardised level "
    "(z-score) of protein {masked}. Answer with a single number "
    "(typical range -3 to 3)."
)


def sha16(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def load_study(data_dir: Path, fname: str) -> pd.DataFrame:
    """Proteins x samples matrix; first accession of semicolon groups."""
    df = pd.read_csv(data_dir / fname, sep="\t", header=0)
    proteins = [p.split(";")[0].strip() for p in df.iloc[:, 0].astype(str)]
    expr = df.iloc[:, 1:].copy()
    expr.index = proteins
    expr.columns = [str(c).strip() for c in expr.columns]
    return expr


def build_8705(data_dir: Path) -> list[dict]:
    records = []
    order = 0
    for study, fname in STUDIES.items():
        expr = load_study(data_dir, fname)
        # rank proteins by variance within the study (label-free)
        top = expr.var(axis=1).sort_values(ascending=False).head(200).index.tolist()
        panel = top[:PANEL_N]
        sub = expr.loc[panel]
        # per-PROTEIN log1p + z across samples within the study (label-free).
        # NOT per-sample z: the panel would sum-constrain and the masked
        # value would be exact arithmetic (see docstring).
        log = np.log1p(sub.clip(lower=0))
        z = (log.sub(log.mean(axis=1), axis=0)).div(log.std(axis=1).clip(1e-9), axis=0)
        # deterministic mask rotation over the top-5 variance proteins
        mask_pool = panel[:MASK_POOL]
        samples = sorted(sub.columns)
        for s_i, sample in enumerate(samples):
            masked = mask_pool[s_i % MASK_POOL]
            shown = [p for p in panel if p != masked]
            genes = ", ".join(f"{p}={z.loc[p, sample]:.2f}" for p in shown)
            verb = VERBALIZATIONS[order % len(VERBALIZATIONS)]
            records.append({
                "task": "MB-8705",
                "split": "test",
                "sample": sample,
                "source": "MSV000094959",
                "prompt": verb + PROMPT_TEMPLATE.format(
                    n=len(shown), genes=genes, masked=masked),
                "answer": f"{z.loc[masked, sample]:.2f}",
            })
            order += 1
        print(f"  {study}: {len(samples)} masked-protein records "
              f"(mask rotates over {mask_pool})")
    return records


def main() -> None:
    data_dir = DRIVE_DATA if DRIVE_DATA.is_dir() else LOCAL_DATA
    if not data_dir.is_dir():
        sys.exit(f"no source data dir: tried {DRIVE_DATA} and {LOCAL_DATA}")

    # carry over 8701 verbatim
    with gzip.open(CORPUS, "rt", encoding="utf-8") as f:
        lines = f.read().splitlines()
    old_meta = json.loads(lines[0])["__meta__"]
    keep = [json.loads(l) for l in lines[1:] if json.loads(l).get("task") == "MB-8701"]
    print(f"carrying over {len(keep)} MB-8701 records verbatim")

    print("building MB-8705 v2 (masked-protein z regression):")
    recs8705 = build_8705(data_dir)
    golds = [float(r["answer"]) for r in recs8705]
    print(f"  target z: mean {np.mean(golds):+.2f}, sd {np.std(golds):.2f}, "
          f"range [{min(golds):+.2f}, {max(golds):+.2f}] (degenerate if sd=0)")

    records = keep + recs8705
    meta = dict(old_meta)
    meta.update({
        "n_records": len(records),
        "built": "2026-10-18",
        "revision": "freeze-11: MB-8705 rebuilt as masked-protein z regression "
                    "(freeze-10 target saturated: all golds '10.0'); per-protein "
                    "log1p+z within study (per-sample z would make the masked "
                    "value arithmetic); MB-8701 records carried verbatim",
    })
    with gzip.open(CORPUS, "wt", encoding="utf-8") as f:
        f.write(json.dumps({"__meta__": meta}) + "\n")
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(records)} records -> {CORPUS}")

    m = json.loads(MANIFEST.read_text())
    m["version"] = "v3-freeze-11"
    m["counts"][CORPUS.name] = len(records)
    m["files"][CORPUS.name] = sha16(CORPUS)
    m["rules"] = [r for r in m.get("rules", []) if not r.startswith("MB-87xx")] + [
        "MB-87xx: MSV000094959 liver->plasma corpus (freeze-11); 8701 platform "
        "3-class carried verbatim from freeze-10 (batch readout caveat); 8705 = "
        "masked-protein z-score regression (top-30 variance proteins per study, "
        "per-PROTEIN log1p+z within study — per-sample z would make the masked "
        "value arithmetic; mask rotates over top-5); freeze-10 8705 was "
        "degenerate (all golds saturated to 10.0) and is superseded"
    ]
    MANIFEST.write_text(json.dumps(m, indent=1))
    print(f"MANIFEST -> {m['version']}")


if __name__ == "__main__":
    main()
