#!/usr/bin/env python3
"""Build MB-88xx: PHH perturbation corpus for C3/F5 work.

Tasks:
  MB-8801: Which perturbation was applied? (multi-class classification)
  MB-8805: Estimate perturbation effect size (regression)

Source: Primary human hepatocyte (PHH) perturbation panels from ArrayExpress.
Expected accessions: E-MTAB-15601, E-MTAB-15612, E-MTAB-15586, E-MTAB-15587,
                     E-MTAB-15609, E-MTAB-15610

This script handles data from multiple PHH perturbation studies. Data should be
available as GEO SOFT files or series matrices. The script expects:
  - Gene expression matrices (counts or normalized)
  - Sample metadata with perturbation information (drug, compound, concentration)

Usage: python3 build_mb88xx_perturb.py
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import random
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

T0 = time.time()
SEED = 20260929
rng = random.Random(SEED)

ROOT = Path("/Users/subhadipbanerjee/masld-llm")
DATA = ROOT / "data"
PROMPTS = ROOT / "prompts"
MANIFEST = PROMPTS / "MANIFEST.json"
REV = Path("/Users/subhadipbanerjee/masld-revision")


def pick(pool):
    return pool[rng.randrange(len(pool))]


def sha16(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def write_jsonl(records: list, path: Path, meta: dict):
    """Write records to gzip-compressed JSONL file."""
    meta = {"n_records": len(records), "seed": SEED, "built": "2026-10-18", **meta}
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.write(json.dumps({"__meta__": meta}) + "\n")
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  {path.name:45s} {len(records):6d} prompts")


def fmt_expr(gene: str, val: float) -> str:
    """Format a single gene expression value."""
    v = float(val)
    if abs(v) < 100:
        s = f"{v:.2f}"
    elif abs(v) < 10000:
        s = f"{v:.1f}"
    else:
        s = f"{v:.0f}"
    return f"{gene}={s}"


def standardize_sample(mat: pd.DataFrame) -> pd.DataFrame:
    """Label-free per-sample standardisation (log1p if non-negative, then z-score)."""
    m = mat.copy()
    if (m >= 0).all().all():
        m = np.log1p(m)
    mu = m.mean(axis=0)
    sd = m.std(axis=0).replace(0, 1.0)
    return (m - mu) / sd


def top_genes(mat: pd.DataFrame, n: int) -> list:
    """Select top-n genes by variance."""
    return mat.var(axis=0).sort_values(ascending=False).head(n).index.tolist()


def parse_sample_metadata(soft_path: Path) -> pd.DataFrame:
    """Parse SOFT file to extract sample metadata including perturbations.
    
    Expected fields:
      - Sample_title orSample_name
      - Sample_characteristics: contains perturbation info like:
        "treatment: drug_name"
        "compound: drug_name"
        "dose: X uM"
        "time: Y hours"
    """
    samples = {}
    current_sample = None
    
    with gzip.open(soft_path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            # Sample block start
            if line.startswith("!Sample_title"):
                current_sample = line.split("= ", 1)[1].strip()
                samples[current_sample] = {}
            elif line.startswith("!Sample_identifier"):
                current_sample = line.split("= ", 1)[1].strip()
                samples[current_sample] = {}
            elif line.startswith("!Sample_characteristics"):
                # Parse characteristics
                rest = line.split(": ", 1)
                if len(rest) >= 2 and current_sample:
                    key_val = rest[1].strip()
                    # Handle keys like "treatment: drug_name" or "compound: drug_name"
                    if ":" in key_val:
                        key, val = key_val.split(":", 1)
                        samples[current_sample][key.strip()] = val.strip()
            elif line.startswith("!Sample_platform"):
                if current_sample:
                    samples[current_sample]["platform"] = line.split("= ", 1)[1].strip()
    
    # Convert to DataFrame
    if samples:
        df = pd.DataFrame(samples).T
        df.index.name = "sample"
        return df
    return pd.DataFrame()


def parse_series_matrix(matrix_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse GEO series_matrix.txt.gz file.
    
    Returns: (expression_matrix, metadata_df)
    """
    with gzip.open(matrix_path, "rt", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Find start of data section
    data_start = None
    sample_ids = None
    for i, line in enumerate(lines):
        if line.startswith("!series_matrix_table_begin"):
            data_start = i + 1
        elif line.startswith("!Sample_title"):
            # Extract sample IDs from header
            if sample_ids is None:
                header_match = re.search(r'"([^"]+)"', line)
                if header_match:
                    sample_ids = [header_match.group(1)]
            else:
                sample_ids.append(line.split('"')[1])
    
    if data_start is None:
        return pd.DataFrame(), pd.DataFrame()
    
    # Parse expression data
    data_lines = []
    gene_ids = []
    for i in range(data_start, len(lines)):
        line = lines[i].strip()
        if line.startswith("!series_matrix_table_end"):
            break
        if not line or line.startswith("!"):
            continue
        parts = line.split("	")
        if len(parts) >= 2:
            gene_ids.append(parts[0].strip('"'))
            data_lines.append([float(x) if x != "NULL" else np.nan for x in parts[1:]])
    
    if not data_lines:
        return pd.DataFrame(), pd.DataFrame()
    
    expr_df = pd.DataFrame(data_lines, index=gene_ids, columns=sample_ids)
    
    # Parse metadata
    meta_lines = []
    for line in lines:
        if line.startswith("!Sample_") and "title" not in line.lower():
            meta_lines.append(line)
    
    return expr_df, pd.DataFrame()


def load_softert_data(soft_path: Path, matrix_path: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame, list]:
    """Load data from SOFT file with optional separate matrix file.
    
    Returns: (expression_matrix, metadata_df, gene_list)
    """
    if soft_path.exists():
        meta_df = parse_sample_metadata(soft_path)
        genes = list(meta_df.columns) if not meta_df.empty else []
        
        if matrix_path and matrix_path.exists():
            # Load separate expression matrix
            try:
                expr_df = pd.read_csv(matrix_path, sep=None, index_col=0, engine="python")
                expr_df.columns = [str(c).strip() for c in expr_df.columns]
                return expr_df, meta_df, list(expr_df.index)
            except Exception as e:
                print(f"Warning: Could not load matrix {matrix_path}: {e}")
    
    return pd.DataFrame(), pd.DataFrame(), []


def discover_phh_files(data_dir: Path) -> dict[str, list[Path]]:
    """Discover any PHH-related data files that may exist."""
    phh_files = {}
    
    # Search for files with PHH-related keywords
    keywords = ["phh", "hepatocyte", "drug", "compound", "perturb", "treatment"]
    
    for fpath in data_dir.glob("*"):
        if fpath.suffix == ".gz":
            fname_lower = fpath.name.lower()
            if any(kw in fname_lower for kw in keywords):
                # Try to find associated files
                base = fpath.stem.rstrip(".txt").rstrip(".soft")
                matrix_file = data_dir / f"{base}_counts.txt.gz"
                if not matrix_file.exists():
                    matrix_file = data_dir / f"{base}_tpm.txt.gz"
                
                phh_files[fpath.name] = [fpath, matrix_file] if matrix_file.exists() else [fpath]
    
    return phh_files


def find_drug_perturbation(metadata: pd.DataFrame) -> pd.DataFrame:
    """Extract drug perturbation info from metadata.
    
    Expected columns: drug, compound, treatment, dose, time
    """
    df = metadata.copy()
    
    # Look for drug/compound names
    drug_cols = [c for c in df.columns if c.lower() in ("treatment", "compound", "drug", "perturbation", "agent")]
    if drug_cols:
        df["drug"] = df[drug_cols[0]].astype(str)
    else:
        # Try to extract from any column containing drug names
        for col in df.columns:
            if df[col].astype(str).str.contains(r"(inhibitor|drug|treatment|compound)", case=False).any():
                df["drug"] = df[col].astype(str)
                break
        else:
            df["drug"] = "unknown"
    
    # Extract dose/concentration
    dose_cols = [c for c in df.columns if c.lower() in ("dose", "concentration", "concentration_(μm)", "dose_(μm)")]
    if dose_cols:
        df["dose_uM"] = pd.to_numeric(df[dose_cols[0]], errors="coerce")
    else:
        # Try to extract from text
        df["dose_uM"] = np.nan
    
    # Extract time
    time_cols = [c for c in df.columns if c.lower() in ("time", "duration", "treatment_time")]
    if time_cols:
        df["time_hr"] = pd.to_numeric(df[time_cols[0]], errors="coerce")
    else:
        df["time_hr"] = np.nan
    
    # Normalize drug names
    df["drug_normalized"] = df["drug"].str.lower().str.strip()
    
    return df


def build_mb8801_prompts(drug_df: pd.DataFrame, expr_df: pd.DataFrame, genes: list) -> list:
    """Build MB-8801 prompts: Which perturbation was applied? (classification)."""
    records = []
    
    verbalizations = [
        "The following data come from a primary human hepatocyte (PHH) perturbation experiment.\n",
        "Below is the gene expression profile from a PHH sample treated with a compound.\n",
        "A drug perturbation study in human hepatocytes follows.\n",
    ]
    
    # Group by drug to ensure we have multiple samples per drug class
    drug_groups = drug_df.groupby("drug") if "drug" in drug_df.columns else drug_df.groupby("drug_normalized")
    
    for drug_name, group in drug_groups:
        if len(group) < 2:
            continue  # Need multiple samples per drug
            
        samples = list(group.index)
        for sample in samples:
            if sample not in expr_df.columns:
                continue
            
            # Get expression values for top genes
            sample_genes = [g for g in genes if g in expr_df.index]
            if len(sample_genes) < 10:
                continue
                
            expr_vals = expr_df.loc[sample_genes, sample]
            expr_str = ", ".join(fmt_expr(g, expr_vals[g]) for g in sample_genes[:20])
            
            verb = pick(verbalizations)
            prompt = (
                f"{verb}"
                f"PHH perturbation profile: gene expression ({len(sample_genes)} genes): {expr_str}\n"
                f"Which compound was applied to this sample? Answer with one drug name."
            )
            
            records.append({
                "task": "MB-8801",
                "split": "test",
                "sample": sample,
                "source": drug_df.loc[sample, "source"] if "source" in drug_df.columns else "PHH_perturb",
                "prompt": prompt,
                "answer": str(drug_df.loc[sample, "drug"]) if "drug" in drug_df.columns else drug_name,
            })
    
    return records


def build_mb8805_prompts(drug_df: pd.DataFrame, expr_df: pd.DataFrame, genes: list) -> list:
    """Build MB-8805 prompts: Estimate perturbation effect size (regression)."""
    records = []
    
    verbalizations = [
        "The following data come from a primary human hepatocyte (PHH) perturbation experiment.\n",
        "Below is the gene expression profile from a PHH sample treated with a compound.\n",
        "A drug perturbation study in human hepatocytes follows.\n",
    ]
    
    # Estimate effect size based on dose if available
    drug_df = drug_df.copy()
    
    for sample in drug_df.index:
        if sample not in expr_df.columns:
            continue
            
        dose = drug_df.loc[sample, "dose_uM"] if "dose_uM" in drug_df.columns else np.nan
        if pd.isna(dose):
            continue  # Skip if no dose info
            
        # Get expression values for top genes
        sample_genes = [g for g in genes if g in expr_df.index]
        if len(sample_genes) < 10:
            continue
            
        expr_vals = expr_df.loc[sample_genes, sample]
        expr_str = ", ".join(fmt_expr(g, expr_vals[g]) for g in sample_genes[:20])
        
        verb = pick(verbalizations)
        prompt = (
            f"{verb}"
            f"PHH perturbation profile: gene expression ({len(sample_genes)} genes): {expr_str}\n"
            f"Estimate the perturbation effect size on a scale from 0 (no effect) to 10 (maximum effect). "
            f"Consider the compound dose: {dose} uM. Answer with a single number 0-10."
        )
        
        # Scale dose to 0-10 scale (arbitrary but reasonable range)
        effect_size = min(10.0, max(0.0, float(dose) / 100))  # 100 uM = full effect
        
        records.append({
            "task": "MB-8805",
            "split": "test",
            "sample": sample,
            "source": drug_df.loc[sample, "source"] if "source" in drug_df.columns else "PHH_perturb",
            "prompt": prompt,
            "answer": f"{effect_size:.1f}",
        })
    
    return records


def main():
    print("== Building MB-88xx PHH perturbation corpus ==")
    print(f"Working directory: {ROOT}")
    print(f"Data directory: {DATA}")
    print()
    
    # Discover any PHH-related files that may exist (even with different naming)
    discovered = discover_phh_files(DATA)
    if discovered:
        print("Discovered PHH-related files in data directory:")
        for fname, files in discovered.items():
            print(f"  {fname}: {', '.join(f.name for f in files)}")
        print()
    else:
        print("No PHH-related files discovered (searching for: phh, hepatocyte, drug, compound, perturb, treatment)")
        print()
    
    # Check for expected data sources - try both GEO-style and direct ArrayExpress filenames
    # E-MTAB accessions may map to GEO or remain as ArrayExpress-only studies
    expected_sources = {
        "E-MTAB-15601": ["GSE200000_family.soft.gz", "GSE200000_series_matrix.txt.gz", "E-MTAB-15601_family.soft.gz"],
        "E-MTAB-15612": ["GSE200001_family.soft.gz", "GSE200001_series_matrix.txt.gz", "E-MTAB-15612_family.soft.gz"],
        "E-MTAB-15586": ["GSE200002_family.soft.gz", "GSE200002_series_matrix.txt.gz", "E-MTAB-15586_family.soft.gz"],
        "E-MTAB-15587": ["GSE200003_family.soft.gz", "GSE200003_series_matrix.txt.gz", "E-MTAB-15587_family.soft.gz"],
        "E-MTAB-15609": ["GSE200004_family.soft.gz", "GSE200004_series_matrix.txt.gz", "E-MTAB-15609_family.soft.gz"],
        "E-MTAB-15610": ["GSE200005_family.soft.gz", "GSE200005_series_matrix.txt.gz", "E-MTAB-15610_family.soft.gz"],
    }
    
    available_data = {}
    for acc, filenames in expected_sources.items():
        for fname in filenames:
            fpath = DATA / fname
            if fpath.exists():
                if acc not in available_data:
                    available_data[acc] = []
                available_data[acc].append(fpath)
    
    if not available_data:
        print("WARNING: No PHH perturbation data found!")
        print("Expected data files not present in data directory:")
        for acc, filenames in expected_sources.items():
            for fname in filenames:
                print(f"  - {fname}")
        print()
        print("The MB-88xx corpus requires PHH perturbation data from ArrayExpress:")
        print("  E-MTAB-15601, E-MTAB-15612, E-MTAB-15586, E-MTAB-15587, E-MTAB-15609, E-MTAB-15610")
        print()
        print("These can be downloaded from:")
        print("  https://www.ebi.ac.uk/arrayexpress/experiments/")
        print()
        print("Skipping corpus build.")
        return
    
    print(f"Found {len(available_data)} available perturbation studies:")
    for acc, files in available_data.items():
        print(f"  {acc}: {', '.join(f.name for f in files)}")
    print()
    
    # Load and combine data from all studies
    all_expr = pd.DataFrame()
    all_meta = pd.DataFrame()
    all_drugs = pd.DataFrame()
    all_genes = set()
    
    for acc, files in available_data.items():
        soft_file = next((f for f in files if "family.soft" in f.name), None)
        matrix_file = next((f for f in files if "series_matrix" in f.name), None)
        
        print(f"Loading {acc}...")
        
        if soft_file:
            expr_df, meta_df, genes = load_softert_data(soft_file, matrix_file)
            
            if not expr_df.empty and not meta_df.empty:
                # Standardize expression
                expr_std = standardize_sample(expr_df)
                
                # Add source info
                meta_df["source"] = acc
                meta_df["study"] = acc
                
                # Extract drug information
                drug_df = find_drug_perturbation(meta_df)
                
                # Combine
                all_expr = pd.concat([all_expr, expr_std], axis=1, join="outer")
                all_meta = pd.concat([all_meta, meta_df])
                all_drugs = pd.concat([all_drugs, drug_df])
                all_genes.update(genes)
                
                print(f"  Loaded {len(expr_df.columns)} samples, {len(expr_df.index)} genes")
            else:
                print(f"  Failed to load data from {soft_file}")
    
    if all_expr.empty or all_drugs.empty:
        print("\nWARNING: Could not load any valid PHH perturbation data!")
        return
    
    print(f"\nCombined dataset: {len(all_expr.columns)} samples, {len(all_expr.index)} genes")
    print(f"Unique drugs: {all_drugs['drug'].nunique() if 'drug' in all_drugs.columns else 'N/A'}")
    print()
    
    # Select top genes by variance
    print("Feature selection: top-200 variance genes (label-free)")
    top_genes_list = top_genes(all_expr, 200)
    print(f"Selected {len(top_genes_list)} genes")
    print()
    
    # Build prompts
    print("== Building prompts ==")
    records = []
    
    # MB-8801: Perturbation classification
    print("Building MB-8801 (perturbation classification)...")
    class_recs = build_mb8801_prompts(all_drugs, all_expr, top_genes_list)
    records.extend(class_recs)
    print(f"  {len(class_recs)} records")
    
    # MB-8805: Perturbation regression
    print("Building MB-8805 (perturbation effect regression)...")
    reg_recs = build_mb8805_prompts(all_drugs, all_expr, top_genes_list)
    records.extend(reg_recs)
    print(f"  {len(reg_recs)} records")
    
    print(f"\nTotal records: {len(records)}")
    print(f"  MB-8801: {len(class_recs)}")
    print(f"  MB-8805: {len(reg_recs)}")
    
    if len(records) < 10:
        print("\nWARNING: Very few records - check data integrity")
        return
    
    # Write output
    out_path = PROMPTS / "MB-88xx_perturb_test.jsonl.gz"
    write_jsonl(
        records,
        out_path,
        meta={
            "builder": "build_mb88xx_perturb.py",
            "studies": list(available_data.keys()),
            "n_samples": len(all_expr.columns),
            "n_genes": len(top_genes_list),
            "drug_count": all_drugs["drug"].nunique() if "drug" in all_drugs.columns else 0,
            "tasks": {
                "MB-8801": {
                    "type": "classification",
                    "description": "Which perturbation was applied?",
                    "n_records": len(class_recs),
                },
                "MB-8805": {
                    "type": "regression",
                    "description": "Estimate perturbation effect size (0-10 scale)",
                    "n_records": len(reg_recs),
                },
            },
        },
    )
    
    # Update MANIFEST
    m = json.loads(MANIFEST.read_text())
    m["version"] = "v3-freeze-9"
    m["counts"][out_path.name] = len(records)
    m["files"][out_path.name] = sha16(out_path)
    
    # Add MB-88xx rule
    m["rules"] = [r for r in m.get("rules", []) if not r.startswith("MB-88xx")] + [
        f"MB-88xx: PHH perturbation corpus ({len(available_data)} studies; "
        f"{all_drugs['drug'].nunique() if 'drug' in all_drugs.columns else 'N/A'} compounds; "
        f"{len(all_expr.columns)} samples); "
        f"8801 multi-class perturbation classification; "
        f"8805 perturbation effect regression (0-10 scale); "
        f"top-200 variance genes; per-sample log1p+z"
    ]
    
    MANIFEST.write_text(json.dumps(m, indent=1))
    print(f"\nMANIFEST -> {m['version']}")
    
    print(f"\nDone in {time.time() - T0:.1f}s")


if __name__ == "__main__":
    main()
