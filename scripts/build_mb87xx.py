#!/usr/bin/env python3
"""Build MB-87xx: liver→plasma protein quantification corpus for C3/F5 work.

Tasks:
  MB-8701: Which plasma protein panel was used? (multi-class classification)
  MB-8705: Estimate plasma protein level (regression)

Source: MSV000094959 plasma protein quantification
- Plasma_liver2_Report_Protein_Quant_Pivot.xls
- Souria72_Plasma_DirectDIA_Protein_Quant_Pivot.xls
- Lumos72_Biognosys_Protein_Quant_Pivot.xls
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
DATA = ROOT / "data"
PROMPTS = ROOT / "prompts"
MANIFEST = PROMPTS / "MANIFEST.json"


def pick(pool):
    return pool[rng.randrange(len(pool))]


def sha16(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def fmt_expr(gene: str, val: float) -> str:
    """Format a single protein expression value."""
    v = float(val)
    if abs(v) < 100:
        s = f"{v:.2f}"
    elif abs(v) < 10000:
        s = f"{v:.1f}"
    else:
        s = f"{v:.0f}"
    return f"{gene}={s}"


def load_excel_matrix(excel_path: Path) -> tuple[pd.DataFrame, list]:
    """Load protein quantification matrix from Excel pivot table.
    
    Returns: (expression_matrix, protein_list)
    """
    # Read as tab-separated text (files are .xls but actually text)
    df = pd.read_csv(excel_path, sep="	", header=0)
    
    # First column is protein IDs (semicolon-separated), use first as index
    proteins = []
    for p in df.iloc[:, 0].astype(str).tolist():
        first = p.split(";")[0].strip()
        if first and first != "nan":
            proteins.append(first)
    
    expr_df = df.iloc[:, 1:].copy()
    expr_df.columns = [str(c).strip() for c in expr_df.columns]
    expr_df.index = proteins
    
    return expr_df, proteins


def top_proteins(mat: pd.DataFrame, n: int) -> list:
    """Select top-n proteins by variance."""
    return mat.var(axis=1).sort_values(ascending=False).head(n).index.tolist()


def build_mb8701_prompts(plasma_df: pd.DataFrame, expr_df: pd.DataFrame, top_proteins: list) -> list:
    """Build MB-8701 prompts: Which plasma protein panel was used? (classification)."""
    records = []
    
    verbalizations = [
        "The following data come from a plasma proteome profiling experiment.\n",
        "Below is the protein quantification profile from a plasma sample.\n",
        "A plasma proteomics study follows.\n",
    ]
    
    # Group by study to ensure we have multiple samples per platform
    for study, group in plasma_df.groupby("study"):
        if len(group) < 2:
            continue  # Need multiple samples per platform
            
        samples = list(group.index)
        for sample in samples:
            if sample not in expr_df.columns:
                continue
            
            # Get expression values for top proteins
            valid_proteins = [p for p in top_proteins if p in expr_df.index]
            sample_proteins = valid_proteins[:30]
            if len(sample_proteins) < 10:
                continue
                
            try:
                expr_vals = expr_df.loc[sample_proteins, sample]
                expr_str = ", ".join(fmt_expr(p, expr_vals[p]) for p in sample_proteins[:30])
            except Exception as e:
                print(f"  Skipping sample {sample}: {e}")
                continue
            
            verb = pick(verbalizations)
            platform = study.replace("_Report_Protein_Quant_Pivot", "").replace("_Plasma_DirectDIA_Protein_Quant_Pivot", "").replace("_Biognosys_Protein_Quant_Pivot", "")
            
            prompt = (
                f"{verb}"
                f"Plasma proteome profile: protein levels ({len(sample_proteins)} proteins): {expr_str}\n"
                f"Which plasma protein quantification platform was used? "
                f"Answer with one of: Plasma_liver2, Souria72, Lumos72."
            )
            
            records.append({
                "task": "MB-8701",
                "split": "test",
                "sample": sample,
                "source": "MSV000094959",
                "prompt": prompt,
                "answer": platform,
            })
    
    return records


def build_mb8705_prompts(plasma_df: pd.DataFrame, expr_df: pd.DataFrame, top_proteins: list) -> list:
    """Build MB-8705 prompts: Estimate plasma protein level (regression)."""
    records = []
    
    verbalizations = [
        "The following data come from a plasma proteome profiling experiment.\n",
        "Below is the protein quantification profile from a plasma sample.\n",
        "A plasma proteomics study follows.\n",
    ]
    
    for sample in plasma_df.index:
        if sample not in expr_df.columns:
            continue
        
        # Get expression values for top proteins
        valid_proteins = [p for p in top_proteins if p in expr_df.index]
        sample_proteins = valid_proteins[:30]
        if len(sample_proteins) < 10:
            continue
        
        try:
            expr_vals = expr_df.loc[sample_proteins, sample]
            mean_level = float(expr_vals.mean())
            expr_str = ", ".join(fmt_expr(p, expr_vals[p]) for p in sample_proteins[:30])
        except Exception as e:
            print(f"  Skipping sample {sample}: {e}")
            continue
        
        # Scale mean level to 0-10 range
        if mean_level > 0:
            severity = min(10.0, max(0.0, np.log10(mean_level + 1) * 3))
        else:
            severity = 0.0
        
        verb = pick(verbalizations)
        prompt = (
            f"{verb}"
            f"Plasma proteome profile: protein levels ({len(sample_proteins)} proteins): {expr_str}\n"
            f"Estimate the overall plasma protein abundance level on a scale from 0 (low) to 10 (high). "
            f"Answer with a single number 0-10."
        )
        
        records.append({
            "task": "MB-8705",
            "split": "test",
            "sample": sample,
            "source": "MSV000094959",
            "prompt": prompt,
            "answer": f"{severity:.1f}",
        })
    
    return records


def discover_plasma_files(data_dir: Path) -> dict[str, Path]:
    """Discover plasma protein quantification files."""
    plasma_files = {}
    
    keywords = ["plasma", "protein", "pivot", "quant"]
    
    for fpath in data_dir.glob("*.xls*"):
        fname_lower = fpath.name.lower()
        if any(kw in fname_lower for kw in keywords):
            if "report" in fname_lower or "directdia" in fname_lower or "biognosys" in fname_lower:
                plasma_files[fpath.stem] = fpath
    
    return plasma_files


def main():
    print("== Building MB-87xx liver→plasma corpus ==")
    print(f"Working directory: {ROOT}")
    print(f"Data directory: {DATA}")
    print()
    
    plasma_files = discover_plasma_files(DATA / "msv000094959")
    
    if not plasma_files:
        print("WARNING: No plasma protein quant files found!")
        print("Skipping corpus build.")
        return
    
    print(f"Found {len(plasma_files)} plasma protein quantification files:")
    for name, fpath in plasma_files.items():
        print(f"  {name}: {fpath.name}")
    print()
    
    # Load and combine data
    all_expr = pd.DataFrame()
    all_meta = pd.DataFrame()
    
    for name, fpath in plasma_files.items():
        print(f"Loading {name}...")
        expr_df, proteins = load_excel_matrix(fpath)
        
        if not expr_df.empty:
            meta_df = pd.DataFrame(index=expr_df.columns)
            meta_df["study"] = name
            meta_df["source_file"] = fpath.name
            
            if all_expr.empty:
                all_expr = expr_df
                all_meta = meta_df
            else:
                all_expr = pd.concat([all_expr, expr_df], axis=1, join="outer")
                all_meta = pd.concat([all_meta, meta_df])
            
            print(f"  Loaded {len(expr_df.columns)} samples, {len(proteins)} proteins")
    
    if all_expr.empty:
        print("\nWARNING: Could not load any plasma protein data!")
        return
    
    print(f"\nCombined dataset: {len(all_expr.columns)} samples, {len(all_expr.index)} proteins")
    print(f"Studies: {all_meta['study'].nunique()}")
    print()
    
    # Select top proteins by variance
    print("Feature selection: top-200 variance proteins (label-free)")
    top_proteins_list = top_proteins(all_expr, 200)
    print(f"Selected {len(top_proteins_list)} proteins")
    print()
    
    # Build prompts
    print("== Building prompts ==")
    records = []
    
    print("Building MB-8701 (plasma platform classification)...")
    class_recs = build_mb8701_prompts(all_meta, all_expr, top_proteins_list)
    records.extend(class_recs)
    print(f"  {len(class_recs)} records")
    
    print("Building MB-8705 (plasma protein level regression)...")
    reg_recs = build_mb8705_prompts(all_meta, all_expr, top_proteins_list)
    records.extend(reg_recs)
    print(f"  {len(reg_recs)} records")
    
    print(f"\nTotal records: {len(records)}")
    print(f"  MB-8701: {len(class_recs)}")
    print(f"  MB-8705: {len(reg_recs)}")
    
    if len(records) < 10:
        print("\nWARNING: Very few records - check data integrity")
        return
    
    # Write output
    out_path = PROMPTS / "MB-87xx_liverplasma_test.jsonl.gz"
    meta = {
        "n_records": len(records),
        "seed": SEED,
        "built": "2026-10-17",
        "builder": "MSV000094959 liver→plasma corpus (C3/F5 work)",
        "studies": list(plasma_files.keys()),
        "n_samples": len(all_expr.columns),
        "n_proteins": len(top_proteins_list),
        "tasks": {
            "MB-8701": {
                "type": "classification",
                "description": "Which plasma protein panel was used?",
                "n_records": len(class_recs),
                "classes": ["Plasma_liver2", "Souria72", "Lumos72"],
            },
            "MB-8705": {
                "type": "regression",
                "description": "Estimate plasma protein level (0-10 scale)",
                "n_records": len(reg_recs),
            },
        },
    }
    
    with gzip.open(out_path, "wt", encoding="utf-8") as f:
        f.write(json.dumps({"__meta__": meta}) + "\n")
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nwrote {len(records)} records -> {out_path}")
    
    # Update MANIFEST
    m = json.loads(MANIFEST.read_text())
    m["version"] = "v3-freeze-10"
    m["counts"][out_path.name] = len(records)
    m["files"][out_path.name] = sha16(out_path)
    
    m["rules"] = [r for r in m.get("rules", []) if not r.startswith("MB-87xx")] + [
        f"MB-87xx: MSV000094959 liver→plasma corpus ({len(plasma_files)} studies; "
        f"{len(top_proteins_list)} proteins; {len(all_expr.columns)} samples); "
        f"8701 plasma platform classification (3 classes); "
        f"8705 plasma protein level regression (0-10 scale); "
        f"top-200 variance proteins"
    ]
    
    MANIFEST.write_text(json.dumps(m, indent=1))
    print(f"\nMANIFEST -> {m['version']}")
    print("\nDone.")


if __name__ == "__main__":
    main()
