#!/usr/bin/env python3
"""Session 7 prep — 3D conformers for the top-5k NP set (Vina input).

ETKDGv3 + MMFF94 minimisation, single best conformer per ligand,
written as multi-SDF: drug-discovery/screening/top5k_3d.sdf
"""
import os, time

from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem

RDLogger.DisableLog("rdApp.*")
T0 = time.time()
IN = "/Users/subhadipbanerjee/masld-llm/drug-discovery/screening/top5k.smi"
OUT = "/Users/subhadipbanerjee/masld-llm/drug-discovery/screening/top5k_3d.sdf"

writer = Chem.SDWriter(OUT)
n_ok, n_fail = 0, 0
with open(IN) as f:
    for line in f:
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 2:
            continue
        smi, sid = parts[0], parts[1]
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            n_fail += 1
            continue
        try:
            mol = Chem.AddHs(mol)
            ps = AllChem.ETKDGv3()
            ps.randomSeed = 20260929
            conf = AllChem.EmbedMolecule(mol, ps)
            if conf != 0:
                n_fail += 1
                continue
            if AllChem.MMFFHasAllMoleculeParams(mol):
                AllChem.MMFFOptimizeMolecule(mol, maxIters=500)
            mol.SetProp("_Name", sid)
            writer.write(mol)
            n_ok += 1
        except Exception:
            n_fail += 1
        if (n_ok + n_fail) % 500 == 0:
            print(f"  {n_ok} ok / {n_fail} failed ({time.time()-T0:.0f}s)", flush=True)
writer.close()
print(f"DONE: {n_ok} conformers written, {n_fail} failed ({time.time()-T0:.0f}s)")
