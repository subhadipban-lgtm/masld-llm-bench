# MASLD-LLM workbench run log

## 2026-09-29 · v3 freeze-1 + freeze-2 (local build session)

### What was built

**Frozen test corpus (freeze-1)** — `prompts/MB-20xx_liver_test.jsonl.gz`, 13,273 prompts
- EPos (157 staged) + Gubra (57 staged, fibrosis from title suffix `NAFL_<stage>`)
- Tasks: MB-2001/2002/2005/2006 single-profile + MB-2003 pairwise (intra-cohort)
- **Frozen forever.** No Fujiwara, no external_v3 data touched this file.

**Train corpora (freeze-2)** — 44,921 prompts across four files:
- `MB-10xx_liver_train.jsonl.gz` — 3,928: Kamzolas SANYAL+UCAM (135 staged; F0=32, F1=50, F2=23, F3=23, F4=7)
- `MB-8xxx_fujiwara_train.jsonl.gz` — 204: Fujiwara TU+HU+TH (51 staged of 213 joined; KU series reserved as internal test)
- `MB-61xx_msigdb_train.jsonl.gz` — 2,701: pathway-membership masked-gene tasks (msigdb c2)
- `MB-62xx_drugs_train.jsonl.gz` — 30,000: drug→gene retrieval tasks (DrugBank-layer interactions)
- `MB-70xx_dge_direction_train.jsonl.gz` — 8,088: direction-of-change from discovery DGE (t1_ranked_logFC)

**Total: 58,194 prompts, all with rotating verbalizations and provenance checksums** (`prompts/MANIFEST.json`).

### Data acquired this session (workbench/data/external_v3/, 460 MB)

11 tier-1 external datasets downloaded and staging-audited:

| Accession | n | Staging available | Verdict |
|---|---|---|---|
| GSE48452 | 73 | fibrosis 0–4 (0.5/3.5 present), NAS, group | ✅ joins train pool (freeze-3) |
| GSE49541 | 72 | mild (F0-1) vs advanced (F3-4) | ✅ train pool (binary + grouped stages) |
| GSE66676 | 67 | histology (no NAFLD / NAFLD not NASH / NASH) — **no fibrosis stage** | ⚠️ NASH-vs-no-NAFLD binary only |
| GSE89632 | 63 | fibrosis 0–4 (31/14/2/4/4), ballooning, inflammation | ✅ train pool (4 formats) |
| GSE61260 | 134 | age, diseasestatus (Normal/NASH/NAFLD/Healthy Obese) | ✅ age tasks + disease binary |
| GSE247407 | 30 | FFA-treated vs control PHH | ⚠️ perturbation corpus, not clinical |
| GSE48325 | 85 | **DNAm** 450K, group, bariatric before/after, age | ✅ opens DNAm domain (freeze-4) |
| GSE164760 | 80+ | NASH-HCC + NASH (expression array n=127) | ⚠️ HCC-contaminated; NASH-only arm usable |
| GSE162694 | 143 | NASH fibrosis DE study | ✅ metadata-only SOFT; matrix needs SRA/GTEx-style pull |
| GSE269926 / GSE244832 | — | snRNA / HSC multi-modal | phase-2 (supplementary files needed) |

### Bugs found and fixed during the build

1. GEO FTP path rule: series dir = accession minus **last 3 digits** + `nnn` (GSE48452 → `GSE48nnn`). My first round 404'd on 5-digit accessions.
2. Kamzolas join key = `Sample name` column (`Sample N`), not the metadata row index.
3. Gubra fibrosis stage encoded in `title` (`NAFL_1`…`NAFL_38`), not in characteristics.
4. Train/test scale mismatch: Kamzolas batch-corrected (log-ish, can be negative) vs EPos raw counts vs Gubra normalised → fixed with label-free per-sample standardisation (log1p if non-negative, then z-score).
5. MSigDB c2 JSON: members under `geneSymbols` key per set dict, not the dict values directly.
6. Task-ID padding produced MB-10001 instead of MB-1001 → normalised to MB-1xxx/2xxx scheme.

### Next steps (in order)

1. **Freeze-3**: add GSE48452, GSE49541, GSE89632, GSE61260, GSE66676(binary), GSE164760(NASH arm) to the train pool — SOFT files already on disk; needs expression-matrix extraction from supplementary files (GSE48452/GSE49541 matrices are embedded in the SOFT or as suppl files).
2. **Freeze-4 (DNAm)**: GSE48325 beta values → age/fibrosis-from-methylation tasks (paper's GEO DNAm analogue; 450K platform GPL13534).
3. **ArrayExpress tier-1**: E-MTAB-9815, E-MTAB-15601/-15612/-15586/-15587/-15609/-15610 (perturbation panels) — download via BioStudies APIFTPs.
4. **Baselines** on the frozen test (laptop-runnable): ElasticNet/HGB fibrosis clocks on prompt features → `results/baselines.json`.
5. Then Colab: notebook 01 (rest of corpora) → 02 (frontier bracket) → 03 (0.6B ladder first).

## 2026-09-29 · Cell publication plan added

- `../MASLD-LLM_cell_publication_plan.html` — claims (C1–C4), figure plan (F1–F6 + supplements S1–S10), statistics/rigor plan, 6-month timeline with go/no-go gates, authorship/licensing.
- Key decisions made for the plan:
  - Test freeze (EPos+Gubra) precedes all new training data — the reviewer-defense anchor.
  - C3 (progression + blood-proxy tasks) is the headline novelty over LongevityBench; C4 (ML/LLM regime split) is the field-level lesson.
  - Journal ladder: Cell → Cell Metabolism → Cell Reports Medicine.
  - Analysis plan to be frozen before the frontier bracket (P2) runs.
- Fixed in this pass: MB-7001 prompts had a dangling "gene with the following characteristics" clause showing no characteristics (gene symbol was dropped in the masked design). Now the named-gene variant; MB-7002 masked variant to be built before P2 so the contamination delta is a designed comparison.

## 2026-09-29 · Drug-discovery extension (design + smoke test)

- Question: can Chai-1 / AlphaFold add natural-product compound nomination?
- Verdict: yes, but only at the structure/screening stages — target nomination
  already lives in masld_kg_v5 (21k drugs, 35k target edges, personalization
  annotations).
- Audited on-disk assets: Natural .xlsx = seed only (~4 unique NPs, quercetin/
  kaempferol/carvacrol); FerrDb 246 inhibitors; PubChem props 10,650.
- Smoke-tested AlphaFold DB API: current model files are **v6** (v4 URLs 404);
  downloaded 5 seed target structures (THRβ, PPARα, GSK3β, LPA1, NCOA3) ->
  drug-discovery/structures/.
- COCONUT (~400k NPs) verified reachable — the missing library piece.
- Design doc: drug-discovery/README.md (5-stage pipeline, compute budget,
  honest caveats: docking = weak evidence, frame as computational nomination).

## 2026-09-29 · Master plan + freeze-3 executed

- Master plan written: docs/MASLD-LLM_master_plan.html — five workstreams
  (W1 corpora, W2 baselines+frontier, W3 model ladder, W4 drug arm, W5 paper),
  7-session immediate queue, budget $220–500, risk register with fallbacks.
- Downloaded 7 expression matrices (series-matrix + count files) for the
  external cohorts; GSE61260 needed its supplementary normalized-expr CSV
  (series matrix was metadata-only).
- **Freeze-3 built: MB-11xx_external_train.jsonl.gz — 5,575 prompts.**
  GSE48452 (71 staged), GSE49541 (72), GSE89632 (56), GSE66676 (67 binary),
  GSE61260 (134 age-regression tasks). Train pool now ~466 staged samples.
- Bug fixed (7th of the program): family.soft characteristics are per-sample
  sequential lines, not cohort-wide — parser rewritten; GSE48452 went from
  1 staged to 71 staged.
- MANIFEST bumped to v3-freeze-3. **Program total: 63,769 prompts.**
- Next in queue: ML baselines on frozen test (session 2), analysis-plan
  freeze + frontier bracket (session 3), COCONUT pull (session 4).
