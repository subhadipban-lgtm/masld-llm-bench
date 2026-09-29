#!/usr/bin/env python3
"""Session 4 — COCONUT NP library pull with physicochemical filters.

POSTs to coconut.naturalproducts.net/api/search with MW 250-600 + LogP 0-5,
pages through results, writes drug-discovery/library/coconut_filtered.smi
(SMILES + identifier) plus a provenance JSON.
Target: 5,000 compounds for the first Vina screen.
"""
import json, os, time, urllib.request

OUT_DIR = "/Users/subhadipbanerjee/masld-llm/drug-discovery/library"
os.makedirs(OUT_DIR, exist_ok=True)
TARGET = 5000
PAGE = 100
LOG = "/Users/subhadipbanerjee/masld-llm/logs/coconut.log"

def log(msg):
    with open(LOG, "a") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")

def fetch_page(page, retries=3):
    body = json.dumps({"query": {
        "incChiral": {"isContain": False},
        "incFsp3": {"isContain": False},
        "incHeavyAtom": {"isContain": False},
        "incMolWeight": {"contains": False, "min": 250, "max": 600},
        "incLogP": {"contains": False, "min": 0, "max": 5},
        "includes": {"contains": False},
        "nResult": PAGE, "pageIndex": page, "asSynonym": True,
        "queryText": "natural product", "origin": "*"}}).encode()
    req = urllib.request.Request(
        "https://coconut.naturalproducts.net/api/search", data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"})
    for a in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except Exception as e:
            log(f"page {page} attempt {a+1} failed: {e}")
            time.sleep(5 * (a + 1))
    return None

def main():
    seen, rows = set(), []
    page = 1
    while len(rows) < TARGET and page <= 80:
        d = fetch_page(page)
        if not d or "data" not in d or not d["data"].get("data"):
            log(f"page {page}: no data, stopping")
            break
        for item in d["data"]["data"]:
            ident = item.get("identifier")
            smi = item.get("canonical_smiles")
            if ident and smi and ident not in seen:
                seen.add(ident)
                rows.append({"identifier": ident, "smiles": smi,
                             "name": item.get("name"), "mw": item.get("mol_weight"),
                             "logp": item.get("mol_logp")})
        if page % 5 == 0:
            log(f"page {page}: {len(rows)} unique compounds")
        page += 1
        time.sleep(1.0)  # be polite

    with open(f"{OUT_DIR}/coconut_filtered.smi", "w") as f:
        for r in rows:
            f.write(f"{r['smiles']}\t{r['identifier']}\n")
    json.dump({"n_compounds": len(rows), "filters": "MW 250-600, LogP 0-5",
               "source": "COCONUT API /api/search", "date": "2026-09-29",
               "note": "first 5k for Vina screen; full 50-150k pull deferred to Colab"},
              open(f"{OUT_DIR}/coconut_provenance.json", "w"), indent=1)
    log(f"DONE: {len(rows)} compounds -> coconut_filtered.smi")

if __name__ == "__main__":
    main()
