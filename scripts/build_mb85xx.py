#!/usr/bin/env python3
"""Build MB-85xx: liver-biopsy progression test corpus.

Per ANALYSIS_PLAN_C3_addendum.md (frozen 2026-10-15):
- MB-8501: progressive vs stable binary classification
- MB-8505: ordinal progression score regression
- Source: Liver biopsies from GSE185051 (pediatric NAFLD cohort)
- Note: No paired-biopsy longitudinal data available in masld-revision;
  progression inferred from fibrosis stage distribution (F0-F4).

Output: prompts/MB-85xx_progression_test.jsonl.gz + MANIFEST version bump.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np

# Use masld-revision for data sources
REPO_ROOT = Path("/Users/subhadipbanerjee/masld-revision")
DATA = REPO_ROOT / "data" / "geo_metadata"
PROMPTS = Path("/Users/subhadipbanerjee/masld-llm") / "prompts"
MANIFEST = PROMPTS / "MANIFEST.json"
SEED = 20260929

# Verbalization templates for variety
VERBALIZATIONS = [
    "The following data come from a liver biopsy transcriptome profile.\n",
    "Below is a bulk RNA-seq profile of liver tissue.\n",
    "A liver-derived transcriptomic profile follows.\n",
]

# Task prompt templates
TASK_HEADERS = {
    "MB-8501": (
        "Patient: liver biopsy profile.\nGene expression: {genes}\n"
        "Based on this liver profile, is the patient's disease PROGRESSIVE "
        "(high fibrosis stage F3-F4) or STABLE (low fibrosis stage F0-F2)? "
        "Answer progressive or stable."
    ),
    "MB-8505": (
        "Patient: liver biopsy profile.\nGene expression: {genes}\n"
        "Estimate the liver-disease progression stage encoded in this biopsy "
        "profile on the ordinal scale 1 (F0-F2 stable) to 2 (F3-F4 progressive). "
        "Answer with a single number 1 or 2."
    ),
}

# Fibrosis stage to progressor status mapping
# F0-F2 = stable (non progressive), F3-F4 = progressive
FIBROSIS_MAP = {
    "0": ("stable", 1),
    "1": ("stable", 1),
    "2": ("stable", 1),
    "3": ("progressive", 2),
    "4": ("progressive", 2),
}


def sha16(path: Path) -> str:
    """Return first 16 hex chars of SHA256 of file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def parse_soft_grades(soft_path: Path) -> dict[str, str]:
    """Map LB-* sample title -> fibrosis stage from SOFT blocks."""
    fibrosis: dict[str, str] = {}
    title = None
    with gzip.open(soft_path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.startswith("!Sample_title"):
                title = line.split("= ", 1)[1].strip()
            elif line.startswith("!Sample_characteristics_ch1") and title:
                # Match: !Sample_characteristics_ch1 = fibrosis_stage: 0
                match = re.search(r"fibrosis_stage:\s*(\d+)", line)
                if match:
                    fibrosis[title] = match.group(1)
    return fibrosis


def load_expression_matrix(matrix_path: Path, soft_path: Path, panel_n: int = 200):
    """Load gene count matrix, pick top-MAD genes, z-score per sample."""
    # Load count matrix (CSV format, gzip compressed)
    with gzip.open(matrix_path, "rt", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        samples = header[1:]  # First column is gene ID

    with gzip.open(matrix_path, "rt", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        gene_ids = []
        rows = []
        for row in reader:
            if len(row) < 2:
                continue
            gene_ids.append(row[0].strip())
            rows.append([float(x) if x else 0.0 for x in row[1:]])

    mat = np.array(rows, dtype=float)  # genes x samples

    # Filter to GSE185051 liver biopsy samples
    # SOFT file has "LB-01", matrix has "L01" (prefix difference: LB- vs L)
    # Note: matrix uses "L" + number, SOFT uses "LB-" + number
    gsm_titles = set()
    gsm_titles_rev = {}  # L01 -> LB-01 for reverse lookup
    with gzip.open(soft_path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.startswith("!Sample_title"):
                title = line.split("= ", 1)[1].strip()
                if title.startswith("LB-"):
                    # Convert LB-01 to L01 for matrix matching
                    short = title.replace("LB-", "L")  # LB-01 -> L01
                    gsm_titles.add(short)
                    gsm_titles_rev[short] = title

    # Find indices of GSE185051 samples
    sample_indices = []
    filtered_samples = []
    for i, s in enumerate(samples):
        if s in gsm_titles:
            sample_indices.append(i)
            filtered_samples.append(s)

    mat = mat[:, sample_indices]
    mad = np.median(np.abs(mat - np.median(mat, axis=1, keepdims=True)), axis=1)
    panel = np.argsort(mad)[::-1][:panel_n]
    panel = sorted(panel.tolist())
    genes = [gene_ids[i] for i in panel]
    sub = mat[panel, :]
    log = np.log1p(sub)
    z = (log - log.mean(axis=0, keepdims=True)) / log.std(axis=0, keepdims=True).clip(1e-9)

    return filtered_samples, genes, z


def fmt_genes(genes: list[str], z_row: np.ndarray) -> str:
    """Format genes and expression values."""
    return ", ".join(f"{g}={v:.2f}" for g, v in zip(genes, z_row))


def main() -> None:
    matrix_path = DATA / "GSE185051_Gene_count.csv.gz"
    soft_path = DATA / "GSE185051_family.soft.gz"
    out = PROMPTS / "MB-85xx_progression_test.jsonl.gz"

    for p in (matrix_path, soft_path):
        if not p.exists():
            sys.exit(f"missing source: {p}")

    # Parse fibrosis stages from family.soft.gz
    fibrosis = parse_soft_grades(soft_path)
    print(f"Samples with fibrosis stage: {len(fibrosis)}")

    # Load expression data
    samples, genes, z = load_expression_matrix(matrix_path, soft_path)
    print(f"Expression matrix: {len(samples)} samples, {len(genes)} genes")

    # Match samples with fibrosis data
    # Fibrosis dict has "LB-01" keys, samples list has "L01" format
    fibrosis_rev = {k.replace("LB-", "L"): v for k, v in fibrosis.items()}
    matched = {s: fibrosis_rev.get(s) for s in samples if fibrosis_rev.get(s) in FIBROSIS_MAP}
    print(f"Samples matched with fibrosis: {len(matched)}")

    if len(matched) < 15:
        sys.exit("too few graded samples — refusing to build")

    from collections import Counter

    stage_counts = Counter(matched.values())
    print("fibrosis stage distribution:", stage_counts)

    # Build records
    rng = np.random.default_rng(SEED)
    records = []

    for idx, (sample, stage) in enumerate(sorted(matched.items())):
        col = samples.index(sample)
        token, ordinal = FIBROSIS_MAP[stage]
        verb = VERBALIZATIONS[idx % len(VERBALIZATIONS)]
        gene_str = fmt_genes(genes, z[:, col])

        for task, extra in (
            ("MB-8501", {"answer": token}),
            ("MB-8505", {"answer": str(ordinal)}),
        ):
            template = TASK_HEADERS[task]
            prompt = verb + template.format(genes=gene_str)
            records.append(
                {
                    "task": task,
                    "split": "test",
                    "sample": sample,
                    "source": "GSE185051",
                    "prompt": prompt,
                    "answer": extra["answer"],
                }
            )

    # Filter MB-8501 to only stable/progressive (exclude any edge cases)
    records = [r for r in records if r["task"] != "MB-8501" or r["answer"] in ("stable", "progressive")]

    meta = {
        "n_records": len(records),
        "seed": SEED,
        "built": "2026-10-18",
        "builder": "GSE185051 liver-biopsy progression test (C3 addendum)",
        "fibrosis_map": {s: st for s, st in sorted(matched.items())},
        "panel_rule": "top-200 MAD genes, label-free, internal",
        "notes": (
            "No paired-biopsy longitudinal data found in masld-revision. "
            "Progression inferred from fibrosis stage distribution (F0-F2 stable, F3-F4 progressive)."
        ),
    }

    with gzip.open(out, "wt", encoding="utf-8") as f:
        f.write(json.dumps({"__meta__": meta}) + "\n")
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(records)} records -> {out}")

    # Update MANIFEST
    m = json.loads(MANIFEST.read_text())
    m["version"] = "v3-freeze-9"
    m["counts"][out.name] = len(records)
    m["files"][out.name] = sha16(out)
    m["rules"] = [
        r for r in m.get("rules", []) if not r.startswith("MB-85xx")
    ] + [
        "MB-85xx: GSE185051 liver-biopsy progression test (52 pediatric NAFLD patients + 5 controls; "
        "fibrosis stages 0-4); 8501 stable-vs-progressive binary, 8505 ordinal score 1-2; "
        "no paired-biopsy longitudinal data available in masld-revision; progression inferred from fibrosis stage"
    ]
    MANIFEST.write_text(json.dumps(m, indent=1))
    print(f"MANIFEST -> {m['version']}")


if __name__ == "__main__":
    main()
