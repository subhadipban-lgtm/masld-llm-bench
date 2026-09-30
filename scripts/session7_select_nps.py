#!/usr/bin/env python3
"""Session 7 prep — diversity selection of 5,000 NPs for the first Vina screen.

From the 362,313-compound unified library: random 60k candidate pool (seed),
Morgan fingerprints (2048-bit), greedy max-min diversity selection of 5k.
Output: drug-discovery/screening/top5k.smi + provenance.
"""
import json, random, time

import numpy as np
from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem, Descriptors, Crippen

RDLogger.DisableLog("rdApp.*")
T0 = time.time()
SEED = 20260929
rng = random.Random(SEED)

LIB = "/Users/subhadipbanerjee/masld-llm/drug-discovery/library/unified_np_library.smi"
OUT_DIR = "/Users/subhadipbanerjee/masld-llm/drug-discovery/screening"
import os; os.makedirs(OUT_DIR, exist_ok=True)

N_CAND = 60_000
N_PICK = 5_000

rows = []
with open(LIB) as f:
    f.readline()
    for line in f:
        rows.append(line.rstrip("\n").split("\t"))
print(f"library: {len(rows)}", flush=True)

idx = rng.sample(range(len(rows)), min(N_CAND, len(rows)))
cands = [rows[i] for i in idx]

fps, kept = [], []
for smi, sid, mw, logp, src in cands:
    mol = Chem.MolFromSmiles(smi)
    if mol is None or mol.GetNumAtoms() > 60:
        continue
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
    arr = np.zeros((2048,), dtype=np.int8)
    Chem.DataStructs.ConvertToNumpyArray(fp, arr)
    fps.append(arr.astype(np.int32))
    kept.append((smi, sid, mw, logp, src))
print(f"candidates fingerprinted: {len(kept)} ({time.time()-T0:.0f}s)", flush=True)

X = np.array(fps, dtype=np.int32)          # (n, 2048) 0/1
popcount = X.sum(axis=1)                    # bits per molecule

# greedy max-min Tanimoto diversity (vectorised updates)
sel = [int(np.argmax(popcount))]
inter0 = X @ X[sel[0]]
dmin = 1.0 - inter0 / np.maximum(popcount + popcount[sel[0]] - inter0, 1)
dmin[sel[0]] = -1.0
while len(sel) < N_PICK:
    nxt = int(np.argmax(dmin))
    sel.append(nxt)
    inter = X @ X[nxt]
    d = 1.0 - inter / np.maximum(popcount + popcount[nxt] - inter, 1)
    dmin = np.minimum(dmin, d)
    dmin[nxt] = -1.0
    if len(sel) % 1000 == 0:
        print(f"  picked {len(sel)} ({time.time()-T0:.0f}s)", flush=True)

with open(f"{OUT_DIR}/top5k.smi", "w") as f:
    for i in sel:
        smi, sid, mw, logp, src = kept[i]
        f.write(f"{smi}\t{sid}\t{mw}\t{logp}\t{src}\n")
json.dump({"n_library": len(rows), "n_candidates": len(kept), "n_selected": len(sel),
           "method": "greedy max-min Tanimoto diversity, Morgan r=2 2048-bit, seed 20260929",
           "date": "2026-09-30"},
          open(f"{OUT_DIR}/top5k_provenance.json", "w"), indent=1)
print(f"DONE: {len(sel)} selected -> top5k.smi ({time.time()-T0:.0f}s)")
