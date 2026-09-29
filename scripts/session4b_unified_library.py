#!/usr/bin/env python3
"""Unified NP library builder — merges all on-disk NP/drug resources.

Sources (audited 2026-09-29):
  COCONUT 2.0 (09-2024 Zenodo dump)   -> coconut_filtered.smi (327,916; already built)
  COCONUT lite 09-2026 (summit_poc)   -> 738,828 rows, NEWER dump — replaces 09-2024 as base
  NPAtlas 2024-09 TSV                 -> 36,454 curated NPs w/ origin + refs (3,492 not in COCONUT by IK)
  NP-MRD smiles shards (7 x ~47k)     -> 150,927 unique SMILES
  CMNPD (marine, summit_poc)          -> 31,561 marine NPs (125 verified not in COCONUT)

Output: drug-discovery/library/unified_np_library.smi (SMILES \t source_id \t MW \t LogP)
with dedup by InChIKey, RDKit filters (MW 250-600, Crippen LogP 0-5).
"""
import csv, glob, gzip, io, json, time, zipfile

from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors, Crippen

RDLogger.DisableLog("rdApp.*")
T0 = time.time()
OUT = "/Users/subhadipbanerjee/masld-llm/drug-discovery/library"

def passes(mol):
    mw = Descriptors.MolWt(mol)
    if not (250 <= mw <= 600):
        return None
    logp = Crippen.MolLogP(mol)
    if not (0 <= logp <= 5):
        return None
    return mw, logp

seen_ik = set()
kept = []
stats = {}

def add(smi, source_id, source_name):
    try:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            return
        ik = Chem.MolToInchiKey(mol)
        if not ik or ik in seen_ik:
            return
        r = passes(mol)
        if r is None:
            return
        seen_ik.add(ik)
        kept.append((Chem.MolToSmiles(mol), source_id, f"{r[0]:.1f}", f"{r[1]:.2f}", source_name))
    except Exception:
        return

# ---- 1. COCONUT lite 09-2026 (newest base) ----
n = 0
z = zipfile.ZipFile("/Users/subhadipbanerjee/Downloads/summit_poc/coconut_csv_lite-09-2026.zip")
with z.open("coconut_csv_lite-09-2026.csv") as f:
    reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"))
    for row in reader:
        n += 1
        add(row.get("canonical_smiles", ""), row.get("identifier", ""), "coconut_2026")
stats["coconut_2026_scanned"] = n
print(f"coconut 2026: scanned {n}, kept so far {len(kept)} ({time.time()-T0:.0f}s)", flush=True)

# ---- 2. NPAtlas ----
n = 0
with open("/Users/subhadipbanerjee/NPAtlas/NPAtlas_download_2024_09.tsv", errors="ignore") as f:
    reader = csv.DictReader(f, delimiter="\t")
    for row in reader:
        n += 1
        add(row.get("compound_smiles", ""), row.get("npaid", ""), "npatlas")
stats["npatlas_scanned"] = n
print(f"npatlas: scanned {n}, kept {len(kept)} ({time.time()-T0:.0f}s)", flush=True)

# ---- 3. NP-MRD shards ----
n = 0
for fp in sorted(glob.glob("/Users/subhadipbanerjee/NP-MRD/smiles_*.csv.gz")):
    with gzip.open(fp, "rt", errors="ignore") as f:
        f.readline()
        for line in f:
            n += 1
            parts = line.rstrip("\n").split(",")
            if len(parts) >= 3:
                add(parts[2].strip('"'), parts[1].strip('"'), "npmrd")
stats["npmrd_scanned"] = n
print(f"npmrd: scanned {n}, kept {len(kept)} ({time.time()-T0:.0f}s)", flush=True)

# ---- 4. CMNPD ----
n = 0
with open("/Users/subhadipbanerjee/Downloads/summit_poc/external_test/cmnpd_table.csv", errors="ignore") as f:
    reader = csv.DictReader(f)
    for row in reader:
        n += 1
        add(row.get("cm_smiles", ""), row.get("cmnpd_id", ""), "cmnpd")
stats["cmnpd_scanned"] = n
print(f"cmnpd: scanned {n}, kept {len(kept)} ({time.time()-T0:.0f}s)", flush=True)

with open(f"{OUT}/unified_np_library.smi", "w") as f:
    f.write("# smiles\tsource_id\tMW\tLogP\tsource\n")
    for smi, sid, mw, logp, src in kept:
        f.write(f"{smi}\t{sid}\t{mw}\t{logp}\t{src}\n")

from collections import Counter
by_src = Counter(k[4] for k in kept)
stats["n_kept"] = len(kept)
stats["by_source"] = dict(by_src)
stats["filters"] = "RDKit MW 250-600, LogP(crippen) 0-5, dedup by InChIKey"
stats["date"] = "2026-09-29"
json.dump(stats, open(f"{OUT}/unified_library_provenance.json", "w"), indent=1)
print("DONE:", json.dumps(stats, indent=1))
