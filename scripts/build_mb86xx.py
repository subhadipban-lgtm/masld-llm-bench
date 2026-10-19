#!/usr/bin/env python3
"""Build MB-86xx: blood-proxy severity test corpus (GSE267032 WBC RNA-seq).

Per ANALYSIS_PLAN_C3_addendum.md (frozen 2026-10-15):
- NEW frozen test, built once, never trained on (mirrors the MB-20xx
  discipline: freeze precedes any use).
- 21 MAFLD/MASH patients with 3-level severity (1_low/2_medium/3_high);
  controls have no expression in the deposit and are excluded.
- Tasks: 8601 severity 3-class | 8602 binary low-vs-high | 8605 ordinal
  severity regression (1-3).
- Gene panel: top-200 by MAD across patients (label-free selection, internal
  to this frozen cohort; 200 matches the liver train panel size).
- Per-sample label-free standardisation: log1p (TPM, non-negative) then
  z-score — the program-wide rule.

Output: prompts/MB-86xx_bloodproxy_test.jsonl.gz + MANIFEST v3-freeze-16.

Renumbered to freeze-16 (2026-10-19): the freeze-8 corpus carried a
header off-by-one that paired every item with the preceding patient's
expression. Rebuilt from re-fetched GEO sources; 21 gradable patients.
"""

from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PROMPTS = ROOT / "prompts"
MANIFEST = PROMPTS / "MANIFEST.json"
SEED = 20260929

VERBALIZATIONS = [
    "The following data come from a peripheral white-blood-cell transcriptome profile.\n",
    "Below is a bulk RNA-seq profile of peripheral white blood cells.\n",
    "A blood-derived transcriptomic profile follows.\n",
]
TASK_HEADERS = {
    "MB-8601": (
        "Patient: blood-derived profile.\nGene expression (WBC): {genes}\n"
        "Which liver-disease severity grade does this blood profile indicate: "
        "low, medium, or high? Answer with one of low, medium, high."
    ),
    "MB-8602": (
        "Patient: blood-derived profile.\nGene expression (WBC): {genes}\n"
        "Based on this blood profile, is the patient's liver-disease severity "
        "HIGH (rather than low)? Answer yes or no."
    ),
    "MB-8605": (
        "Patient: blood-derived profile.\nGene expression (WBC): {genes}\n"
        "Estimate the liver-disease severity grade encoded in this blood "
        "profile on the ordinal scale 1 (low) to 3 (high). Answer with a "
        "single number 1, 2, or 3."
    ),
}
GRADE_TOKENS = {"1_low": ("low", 1), "2_medium": ("medium", 2), "3_high": ("high", 3)}


def sha16(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def parse_soft_grades(soft_path: Path) -> dict[str, str]:
    """Map Blood_patient_N -> severity grade from per-sample SOFT blocks."""
    grades: dict[str, str] = {}
    title = None
    with gzip.open(soft_path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.startswith("!Sample_title"):
                title = line.split("= ", 1)[1].strip()
            elif line.startswith("!Sample_characteristics") and title:
                val = line.split(": ", 1)[-1].strip()
                if val in GRADE_TOKENS:
                    grades[title] = val
    return grades


def load_tpm(tpm_path: Path, panel_n: int = 200):
    """Load TPM matrix, pick top-MAD genes, z-score per sample.

    GSE267032's header lists ONLY the 35 sample names (all quoted) and has no
    gene-ID column label, while each data row carries 36 fields (gene id +
    35 values). The original implementation did ``header[1:]``, which dropped
    Blood_patient_1 and paired every remaining label with the PRECEDING
    sample's column — a silent off-by-one that mislabeled all 20 items.
    Detect the header shape explicitly and fail loudly if it is ambiguous.
    """
    with gzip.open(tpm_path, "rt", encoding="utf-8") as f:
        header = f.readline().split()
        names = [h.strip('"') for h in header]
        gene_ids: list[str] = []
        rows: list[list[float]] = []
        for line in f:
            parts = line.rstrip("\n").split(" ")
            if len(parts) < 2:
                continue
            gene_ids.append(parts[0].strip('"'))
            rows.append([float(x) for x in parts[1:]])
    mat = np.array(rows, dtype=float)  # genes x samples

    n_val_cols = mat.shape[1]
    looks_like_gene_label = names[0].upper().startswith(("ENSG", "GENE"))
    if len(names) == n_val_cols and not looks_like_gene_label:
        samples = names                      # header has no gene-id column
    elif len(names) == n_val_cols + 1:
        samples = names[1:]                  # header includes a gene-id column
    else:
        raise SystemExit(
            f"header/matrix mismatch: {len(names)} names vs {n_val_cols} value "
            f"columns in {tpm_path} — refusing to guess the sample mapping"
        )
    if not all(s.startswith(("Blood_patient", "Blood_control")) for s in samples):
        raise SystemExit(f"unexpected sample names in header: {samples[:5]}")

    ok = [i for i, p in enumerate(samples) if p.startswith("Blood_patient")]
    mat = mat[:, ok]
    patients = [samples[i] for i in ok]
    mad = np.median(np.abs(mat - np.median(mat, axis=1, keepdims=True)), axis=1)
    panel = np.argsort(mad)[::-1][:panel_n]
    panel = sorted(panel.tolist())
    genes = [gene_ids[i] for i in panel]
    sub = mat[panel, :]
    log = np.log1p(sub)
    z = (log - log.mean(axis=0, keepdims=True)) / log.std(axis=0, keepdims=True).clip(1e-9)
    return patients, genes, z


def fmt_genes(genes: list[str], z_row: np.ndarray) -> str:
    return ", ".join(f"{g}={v:.2f}" for g, v in zip(genes, z_row))


def main() -> None:
    soft = DATA / "GSE267032_family.soft.gz"
    tpm = DATA / "GSE267032_tpm_RNASeq_WBC_bulk.txt.gz"
    out = PROMPTS / "MB-86xx_bloodproxy_test.jsonl.gz"
    for p in (soft, tpm):
        if not p.exists():
            sys.exit(f"missing source: {p}")

    grades = parse_soft_grades(soft)
    patients, genes, z = load_tpm(tpm)
    matched = {p: grades[p] for p in patients if p in grades}
    print(f"patients in matrix: {len(patients)}; with severity grade: {len(matched)}")
    if len(matched) < 15:
        sys.exit("too few graded patients — refusing to build")
    from collections import Counter

    print("grade distribution:", Counter(matched.values()))

    rng = np.random.default_rng(SEED)
    records = []
    for idx, (patient, grade) in enumerate(sorted(matched.items())):
        col = patients.index(patient)
        token, ordinal = GRADE_TOKENS[grade]
        verb = VERBALIZATIONS[idx % len(VERBALIZATIONS)]
        gene_str = fmt_genes(genes, z[:, col])
        hi = "yes" if grade == "3_high" else "no"
        for task, extra in (
            ("MB-8601", {"answer": token}),
            ("MB-8602", {"answer": hi}),
            ("MB-8605", {"answer": str(ordinal)}),
        ):
            template = TASK_HEADERS[task]
            prompt = verb + template.format(genes=gene_str)
            records.append(
                {
                    "task": task,
                    "split": "test",
                    "sample": patient,
                    "source": "GSE267032",
                    "prompt": prompt,
                    "answer": extra["answer"],
                }
            )
    # low-vs-high binary uses only those two classes (medium excluded).
    records = [r for r in records if r["task"] != "MB-8602" or r["answer"] in ("yes", "no")]
    records = [r for r in records if not (r["task"] == "MB-8602" and _is_medium(r, grades))]
    meta = {
        "n_records": len(records),
        "seed": SEED,
        "built": "2026-10-15",
        "builder": "GSE267032 WBC blood-proxy frozen test (C3 addendum)",
        "grades": {p: g for p, g in sorted(matched.items())},
        "panel_rule": "top-200 MAD genes, label-free, internal",
    }
    with gzip.open(out, "wt", encoding="utf-8") as f:
        f.write(json.dumps({"__meta__": meta}) + "\n")
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(records)} records -> {out}")

    m = json.loads(MANIFEST.read_text())
    m["version"] = "v3-freeze-16"
    m["counts"][out.name] = len(records)
    m["files"][out.name] = sha16(out)
    m["rules"] = [
        r for r in m.get("rules", [])
        if not r.startswith("MB-86xx")
    ] + [
        "MB-86xx: GSE267032 WBC blood-proxy frozen test (21 patients, grades "
        "1_low/2_medium/3_high; controls excluded — no expression deposited); "
        "rebuilt 2026-10-19 (freeze-16) after the freeze-8 header off-by-one; "
        "8601 3-class, 8602 low-vs-high binary, 8605 ordinal 1-3; panel = "
        "top-200 MAD genes internal to this frozen corpus; per-sample log1p+z"
    ]
    MANIFEST.write_text(json.dumps(m, indent=1))
    print(f"MANIFEST -> {m['version']}")


def _is_medium(rec: dict, grades: dict[str, str]) -> bool:
    return grades.get(rec["sample"]) == "2_medium"


if __name__ == "__main__":
    main()
