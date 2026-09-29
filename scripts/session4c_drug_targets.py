#!/usr/bin/env python3
"""Drug-target knowledge corpus builder — DrugCentral + DrugBank + CTD.

Enriches the KG's drug-target layer with affinity-labelled training data:
  MB-63xx: affinity-grounded drug->target tasks (DrugCentral ACT_VALUE)
  merged target table for the KG: drug-discovery/targets/drug_target_full.csv

Sources (audited): DrugCentral 23,115 rows (2,587 drugs x 2,500 genes, with
ACT_VALUE affinities); DrugBank extract 35,043 rows (14,592 drugs x 4,699
genes w/ InChIKey); CTD 41,624 rows (3,298 chemicals x 2,948 genes).
"""
import json, os, time
import pandas as pd

T0 = time.time()
import warnings
warnings.filterwarnings("ignore")
ROOT = "/Users/subhadipbanerjee/masld-llm"
OUT = f"{ROOT}/prompts"
TGT = f"{ROOT}/drug-discovery/targets"
os.makedirs(TGT, exist_ok=True)
SEED = 20260929
import random
rng = random.Random(SEED)

def write_jsonl(records, path, meta):
    import gzip, hashlib
    meta = {"n_records": len(records), "seed": SEED, "built": "2026-09-29", **meta}
    with gzip.open(path, "wt") as f:
        f.write(json.dumps({"__meta__": meta}) + "\n")
        for r in records:
            f.write(json.dumps(r) + "\n")
    print(f"  {os.path.basename(path):46s} {len(records):6d} prompts")

dc = pd.read_excel("/Users/subhadipbanerjee/Drug_database/DrugCentral.xlsx", sheet_name="DrugCentral")
db = pd.read_excel("/Users/subhadipbanerjee/Drug_database/DB.xlsx", sheet_name="DB")
ctd = pd.read_excel("/Users/subhadipbanerjee/Drug_database/CTD.xlsx", sheet_name="CTD")

# unified target table
dc_u = dc[["DRUG_NAME", "GENE", "ACT_VALUE"]].dropna(subset=["GENE"]).copy()
dc_u.columns = ["drug", "gene", "act_value"]
dc_u["source"] = "drugcentral"
db_u = db[["name", "HGNC"]].dropna().copy()
db_u.columns = ["drug", "gene"]
db_u["act_value"] = None
db_u["source"] = "drugbank"
ctd_u = ctd[["ChemicalName", "GeneSymbol"]].dropna().copy()
ctd_u.columns = ["drug", "gene"]
ctd_u["act_value"] = None
ctd_u["source"] = "ctd"
full = pd.concat([dc_u, db_u, ctd_u], ignore_index=True)
full.to_csv(f"{TGT}/drug_target_full.csv", index=False)
print(f"unified drug-target table: {full.shape} ({full['drug'].nunique()} drugs x {full['gene'].nunique()} genes)")

# affinity-grounded prompts from DrugCentral (ACT_VALUE = -log affinity, higher = stronger)
aff = dc.dropna(subset=["GENE", "ACT_VALUE"])
aff = aff[aff["ACT_VALUE"].apply(lambda x: isinstance(x, (int, float)) and 3 <= float(x) <= 12)]
print(f"affinity-labelled pairs: {len(aff)}")
gene_pool = sorted(set(dc["GENE"].dropna()))
recs = []
for _, row in aff.iterrows():
    gene = str(row["GENE"])
    decoy = rng.choice(gene_pool)
    while decoy == gene:
        decoy = rng.choice(gene_pool)
    options = [gene, decoy]
    rng.shuffle(options)
    strength = "strong" if float(row["ACT_VALUE"]) >= 7 else "moderate" if float(row["ACT_VALUE"]) >= 5 else "weak"
    recs.append(dict(
        task="MB-6301", split="train", source="drugcentral_affinity",
        prompt=(f"The drug {row['DRUG_NAME']} binds one of the following protein targets with "
                f"{strength} affinity (pActivity {float(row['ACT_VALUE']):.1f}): "
                f"{options[0]} or {options[1]}? Answer with one gene symbol."),
        answer=gene,
    ))
write_jsonl(recs, f"{OUT}/MB-63xx_drugcentral_affinity_train.jsonl.gz",
            meta=dict(builder="DrugCentral ACT_VALUE affinity tasks",
                      n_affinity_pairs=len(aff)))
print(f"done in {time.time()-T0:.1f}s")
