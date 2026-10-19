# Public bulk blood transcriptome cohorts in MASLD with liver-histology labels

**Search and verification report for the MB-86xx frozen blood family — 2026-10-19 (Asia/Bangkok)**

Method preamble: six worker agents swept NCBI GEO (systematic `db=gds` walk, 6 query variants → 79 unique GSE series triaged, 15 SOFT-level spot checks), EBI BioStudies/ArrayExpress (16 queries, 192-entry union, 19 dataset accessions individually resolved), SRA/BioProject-only and alternative-indexing framings (~27 queries: bariatric/T2D indexing, paired super-series, MeSH routes, 2025–2026 recent deposits, non-English cohorts), and the 2015–2026 literature with partial forward-citation trails. A dedicated verification agent then fetched SOFT/BioSample/BioStudies records for all 7 shortlisted near-misses and quoted the exact fields; an adversarial reviewer independently re-swept the highest-risk query gaps (MASLD/MASH nomenclature, PAXgene/Tempus, Europe PMC full-text) and audited 5 sampled rejections plus the anchor superseries. Every verdict below traces to a fetched URL. All endpoint statuses are as of 2026-10-19.

---

## 1. ACCEPTED

**None accepted.**

No public, bulk, blood-derived transcriptome cohort in a MASLD/NAFLD/MASH population with per-sample liver-histology labels at n ≥ 100 was found. The largest open blood+histology deposit remains the already-known **GSE267032** (Bulk White Blood Cells in MAFLD/MASH): verified at GSM level this turn as **exactly 35 samples — 14 healthy controls + 21 histology-graded MAFLD/MASH** (grade distribution: `1_low` = 8, `2_medium` = 6, `3_high` = 7; per-sample fields `disease`, `condition`, `celltype: wbc`, `assaytype: bulk`; label join directly verifiable from GSM characteristics). That is ~3× below the mission's hard floor of n ≥ 100, so it fails criterion 4 and cannot anchor an MB-86xx replacement by itself.

A documented negative is the honest deliverable here: the supporting search coverage is in Section 4, and the strongest near-misses with exact rejection evidence are in Sections 2–3.

---

## 2. REJECTED table

All candidates that surfaced during the sweep with a blood-adjacent profile, plus histology-labeled liver deposits surfaced alongside them (marked, to prevent future re-litigation). The 7 already-known accessions from the program (GSE267032/33, GSE135251, GSE130970, GSE167523, GSE126848, GSE48452) are not repeated here.

| Accession | One-line reason | Criterion failed |
|---|---|---|
| GSE55645 | n=49 blood **lymphocytes**, per-sample `Stage: NASH` (39) / `Simple steatosis` (10) — but `Series_type = Genome variation profiling by genome tiling array`, `Sample_molecule_ch1 = genomic DNA` (aCGH/CNV, GPL9777), not a transcriptome; labels only 2-level | 2 (assay); partially 3 (no F/NAS) |
| GSE117623 | n=137 peripheral blood but **CEC-enriched** fractions (116/137 circulating epithelial cells) + 21 sorted WBC subsets; diagnosis only `HCC patient` (73) / `Chronic liver disease patient` (64); zero NAFLD/NASH/steatosis/fibrosis strings in the entire SOFT family; etiologies unspecified | 1 (cell type), 3 (no histology labels), 5 (etiology) |
| GSE73634 | 48 GSMs = 24 blood + 24 liver, simtuzumab trial NCT01707472 in **HCV and/or HIV** adults; blanket `disease state: advanced liver fibrosis` on every sample, no per-sample stage; blood arm n=24 | 3 (etiology + labels), 4 |
| GSE247467 | Peripheral **neutrophils** n=12 (Advanced_1-4, Mild_1-3, Normal_1-5), MASH vs healthy only, no grade field; "biopsy proven" is group-level design wording; metadata quirk: `Normal_1` carries `disease state: MASH` in GEO characteristics | 3 (no per-sample histology), 4 |
| GSE326605 | Peripheral NK cells, FACS-sorted NTCP±, `Liver fibrosis F4 score` label, n=4 | 2 (sorted subset), 4 |
| GSE325645 | Peripheral blood NK cells, CHB vs CHB-MASLD comparison, n=7 | 3 (no fibrosis labels), 4 |
| GSE185062 | Serum **miRNA** (2,083 miRNAs; 183 NAFLD cases across full spectrum + 10 controls, n=193) — cell-free, non-mRNA | 1 (specimen), 2 (assay) |
| GSE33857 | Serum exosomal miRNA incl. 7 NASH, n=100 | 1 (specimen), 2 (assay) |
| S-BSST1614 (PMID 42173964, Sci Data 2026) | Plasma **cell-free RNA**, 601 mixed-CLD patients (112+489); deposit contains ONLY two count matrices keyed by anonymous `RNA015584...`-style IDs with **zero sample-level metadata** — no phenotype file, no histology, no scores; join impossible from deposit | 1 (specimen), 3, 6 (join) |
| PRJNA1089362 | Thai PBMC RNA-seq n=68 (Chulalongkorn, 2020–2023), open SRA — but complete BioSample attribute set = {isolate, age, biomaterial_provider, collection_date, geo_loc_name, sex (restricted), tissue=PBMC1..68}; **no disease or histology attribute of any kind**; no GEO mirror | 3, 4, 6 |
| PRJNA1305173 | Reported in a 2025 pediatric-PBMC paper lead, but **does not resolve** in NCBI BioProject/SRA/BioSample or ENA (count 0 everywhere) — likely mistyped; paper (PMID 41479518) describes n=30 adolescents, imaging-defined steatosis, no per-sample histology | 3, 4; deposit unverified |
| GSE117623-adjacent: GSE73634-adjacent paired designs | No other paired blood+biopsy human NAFLD deposit exists in GEO (blood+liver super-series relation fields empty for all 74 GSE docsums reviewed) | — |
| GSE267031 | Bulk **liver** needle biopsies, n=18, NAS-stratified — part of the same anchor SuperSeries GSE267195; previously unlisted in the program table | 1 (specimen) |
| GSE240729 | Liver (FFPE) MASLD biomarker study, n=67, per-sample `fibrosisscore: F0–F4` — the "blood-based biomarker panel" is a **protein** panel; transcriptomic deposit is liver | 1 (specimen) |
| GSE249997 | Liver, "early MASLD", n=77, brain-MRI correlation study | 1 (specimen) |
| GSE69039 | Korean obesity PBMC n=18 — no liver histology | 3, 4 |
| GSE180241 | Blood outgrowth endothelial cells cultured from NAFLD patients/controls, n=3+3, 6 GSMs | 1 (cell type), 3, 4 |
| GSE318806 | PBMCs from 3–5 healthy donors for in-vitro MASLD macrophage work; "no clinical information" | 3, 4 |
| GSE342568 | iPSC-derived hepatocyte cultures, 386 samples / 193 participants (Family Study) — no blood transcriptome, no biopsy | 1 (specimen), 3 |
| E-GEOD-54882 | Whole blood DNA **methylation**, no NAFLD attributes (only EBI blood specimen found) | 2 (assay), 3 |

Note on the anchor family: GSE267195 is a 3-part SuperSeries — GSE267031 (bulk liver, n=18, NAS-stratified) + GSE267032 (bulk WBC, n=35) + GSE267033 (scRNA, n=15) = 68 GSMs total. One literature row claims "22 patients liver-RNA-seq" vs the deposited 18 liver GSMs; that discrepancy (possibly a FACS/scRNA subset or undeposited samples) is unresolved — both numbers are stated, neither asserted as final.

---

## 3. Near-misses (would qualify if one specific thing were obtained)

| Cohort | What it has | The one missing thing | What to request / watch |
|---|---|---|---|
| **S-BSST1614 / Zenodo 10.5281/zenodo.19047046** (Ghent "Grand Challenge" hepatology plasma cfRNA, PMID 42173964) | 601 patients, two open count matrices (cohort 1: 12.9 MB; cohort 2: 101 MB), raw reads behind EGA DUA (EGAD50000000775 / EGAS50000000545) | Per-sample metadata: the open deposit ships **no phenotype file at all** (anonymous `RNAxxxxx` columns; no histology, not even age/sex); and it is plasma cfRNA, not blood cells | Contact authors for the sample-sheet (even biochemical scores only would help); per-sample liver histology exists for a subset per the paper. Even then: plasma, mixed-etiology, MASLD fraction unknown — use as secondary family, not MB-86xx blood |
| **GSE55645** | n=49 blood lymphocytes, per-sample histology labels (`Stage: NASH` 39 / `Simple steatosis` 10) joinable within each GSM | Transcriptome assay (it is aCGH on genomic DNA) | Nothing to request — assay mismatch is inherent. Only relevant if the benchmark ever adds a DNA-copy-number arm |
| **GSE73634** | Paired whole blood + liver biopsy, 24 participants, trial tissue available | MASLD etiology (it is HCV/HIV) and per-sample fibrosis stage | Nothing to request for MASLD use; listed to prevent future confusion |
| **GSE185062** | n=193, complete NAFLD histology spectrum (183 cases) | Cellular specimen (it is serum miRNA) | Nothing to request; candidate only if the benchmark ever relaxes to circulating miRNA |
| **PMID 41751802** (Mondal 2026, whole-blood miRNA/ncRNA in African Americans with MASLD) | Whole-blood specimen, MASLD population | Deposit accession (none found; pilot n; ncRNA assay; same group's 2023 data were "on request") | Email corresponding author (T. Mondal) for deposition status |
| **PMID 38281815** (Oh 2024, Clin Mol Hepatol, 134 biopsy-proven MASLD) | Biopsy-proven n=134 | A blood bulk-transcriptome arm (only tissue WGS/WES/RNA-seq under PRJNA725028 is evident; cfRNA mentioned but not evidently deposited) | Check supplement tables / email authors whether blood RNA-seq exists |
| **GRIPonMASH** (PMID 40447415 protocol) | Prospective multicentre MASH biobank with planned blood multiomics + biopsied histology | Nothing yet — cohort still accruing; no deposit | Set a 6–12 month re-sweep reminder; this is the most likely future qualifying source |
| **PMID 40257301 family** (GSE267032/33 anchor study) | 35 bulk WBC + 15 scRNA + 18 bulk liver, all NAS/grade-labeled, join verifiable | Sample size (35 graded WBC) | Watch for a larger follow-up blood cohort from the same group; 10 forward citations checked — none yet |

---

## 4. Search log (all queries run 2026-10-19, Asia/Bangkok)

**Sources checked:** NCBI eutils `db=gds` (GSE+GDS), `db=sra`, `db=bioproject`, `db=biosample`; GEO SOFT via FTP family.soft.gz and CGI per-GSM text views; EBI BioStudies search API + study API + SDRF attachments; ArrayExpress JSON v3 (found retired, HTTP 302 → BioStudies HTML); Europe PMC search + full-text + citations; ENA portal API; PubMed abstracts; open-web search (AutoGLM provider); Zenodo/Figshare via web search.

**GEO systematic walk (worker 1, replacement run):**

| Query (db=gds, all with `Homo sapiens[ORGN]`) | Hits |
|---|---|
| ("whole blood" OR PBMC OR "peripheral blood" OR leukocyte) AND (NAFLD OR NASH OR MASLD OR MASH OR "fatty liver") AND gse[ETYP] — base | 59 |
| base + "hepatic steatosis"/steatosis variants | 64 |
| blood terms AND bariatric AND (liver OR biopsy) | 39 |
| blood terms AND diabetes AND NAFLD-ish | 3 |
| ("whole blood" OR "peripheral blood") AND "liver biopsy" (no ETYP) | 182 |
| base without gse[ETYP] (catch GDS) | 428 |
| **Union after dedupe** | **509 UIDs → 79 unique GSE series, 0 GDS-only** |

15/15 SOFT spot-check budget used (per-GSM brief views); triage: 62 not-blood, 10 ambiguous (all resolved negative on inspection), 4 blood-no-histology, 3 excluded-known. Verdict file: `geo_triage.tsv` (79 rows).

**Adversarial reviewer's gap-closing sweeps (worker 6):**
- `(MASLD OR MASH) AND blood terms AND gse[ETYP]` → 13 hits (4 accessions new to triage: GSE318806, GSE303156, GSE240729, GSE249997 — all rejected, see table)
- "metabolic (dysfunction)-associated" / "steatotic liver" / MAFLD variants → 42 hits, no new blood cohort
- PAXgene/Tempus/whole-blood-RNA + liver biopsy → 3 hits, all unrelated diseases (SLE, scleroderma, arthritis) — query space demonstrably empty in GEO
- Europe PMC full-text: `"whole blood" AND "liver biopsy" AND "RNA-seq" AND (NAFLD OR NASH OR MASLD)` → 136 hits; PBMC/whole-blood + biopsy-proven/fibrosis-stage + transcriptome → 929 hits; `"blood transcriptome" AND (MASLD OR MAFLD OR NAFLD OR NASH)` → 103 hits; top-100 of each walked
- Rejection audit: 5 sampled verdicts re-fetched — all correct
- Anchor recheck: GSE267195 full SOFT → 3-part SuperSeries (18+35+15); GSE267032 GSM-level count confirmed 14+21

**EBI BioStudies/ArrayExpress (worker 2):** 16 search queries (NAFLD blood; NASH blood transcriptome; MASLD blood; non-alcoholic fatty liver expression; fatty liver PBMC; hepatic steatosis microarray; steatohepatitis whole blood; liver biopsy blood gene expression; + 8 supplementary incl. E-MTAB prefix probes) → totalHits 10⁴–10⁶ each (loose-OR), 192-entry union, **19 unique dataset accessions, all individually fetched and triaged**; `type=arrayexpress` param broken (0 hits); AE-native JSON v3 endpoint retired (HTTP 302 empty); dual-deposit check: only E-GEOD-48452 mirrors a known GSE; all other known GSEs 404 at EBI. Triage file: `ae_triage.tsv` (19 rows).

**SRA / BioProject / alternative framings (worker 4):** 14 db=gds esearch variants (bariatric/T2D/metabolic-syndrome indexing; paired super-series; MeSH-strict → 0; MeSH-loose → 27 all murine; MASLD-only → 9; fibrosis-stage + blood → 184 reviewed via 63 unique GSEs); db=sra `(NAFLD OR NASH OR MASLD) AND "whole blood" AND "RNA-Seq"[Strategy]` → 188 (collapses to SRP471237 = GSE247467 + 1 SLE false positive); db=bioproject human NAFLD transcriptome sweep → 223 (49 titles listed, only PRJNA1089362 blood); recent-deposit sweep (sort=pub_date, top 40) → all murine/in-vitro; web searches incl. zenodo/figshare supplementary-matrix probes (noise), review-literature negative-test (blood biomarker field routes through protein/metabolite/miRNA; no ≥100 blood transcriptome cohort enumerated anywhere).

**Literature track (workers 3 + 3b, partially recovered):** 14-paper candidate table (`papers.tsv`) with accessions resolved or marked unresolved; anchor-paper forward-citation check (PMID 40257301: 10 citations, no larger blood follow-up); Sci Data 2026 plasma cohort resolved to S-BSST1614 + Zenodo and verified at file level. **Coverage gap (disclosed):** the systematic forward-citation walks of GSE126848 (Suppli 2019), GSE135251 (Govaere 2020), GSE48452 (Ahrens 2013) source papers did not complete (worker failure); partially mitigated by the reviewer's independent Europe PMC full-text sweeps, but a dedicated citation walk remains worthwhile if the consortium wants belt-and-braces coverage.

**Verification round (worker 5):** 7 shortlisted candidates re-verified by direct deposit fetches with exact field quotes (S-BSST1614 study JSON + count-matrix header range-fetch; GSE55645 full 49-GSM dump; GSE117623 SOFT family grep; GSE73634 SOFT family grep; GSE247467 SOFT; PRJNA1089362 SRA efetch + 3 BioSample efetch; PRJNA1305173 zero-hit check in 4 repositories). Route failures recorded: NCBI FTP family.soft.gz unreachable for GSE55645 (CGI fallback used); BioSample DB does not index PRJNA strings (accession-level efetch used).

**Aggregate: ~120 queries/fetches across 6 workers + reviewer; every GSE surfaced by any route is represented in the triage tables.**

---

## 5. Recommendation

**Do not freeze a blood MB-86xx family from public data today — no qualifying cohort exists publicly (as of 2026-10-19).**

- The single best candidate for a future frozen blood family remains **GSE267032** (bulk WBC, n=35: 14 controls + 21 graded MAFLD/MASH; labels joinable straight from GSM characteristics — the join the GSE126848 trap forbids is trivially safe here). It supports the 3-class severity target (low/medium/high) and binary high-vs-low at n=35, and ordinal regression only with heavy regularization — but it **fails the n ≥ 100 floor by ~3×** and cannot anchor an MB-86xx replacement alone.
- A defensible interim design is a **multi-cohort meta-family**: GSE267032 (bulk WBC) as the anchor + the small blood arms already in the program (GSE267033 scRNA excluded by modality; GSE247467 neutrophils n=12) are not combineable at n ≥ 100 either — so the honest interim position is: no public blood family at target size, full stop.
- **Highest-value acquisition targets, in order:** (1) the S-BSST1614/Zenodo sample-sheet from the Ghent group (601 patients; would immediately become the largest liver-disease blood-derived transcriptome family if the MASLD subset has per-sample histology — note specimen is plasma cfRNA); (2) GRIPonMASH prospective biobank (protocol PMID 40447415) — set a 6–12 month re-sweep; (3) author queries to Mondal (PMID 41751802) and Oh (PMID 38281815) about blood-arm deposits.
- If the consortium can relax one criterion, the relaxation with the best yield is **specimen (accept plasma cfRNA)** — GSE185062 (n=193 histology-spectrum serum miRNA) and S-BSST1614 (n=601, pending metadata) become available. Relaxing **assay to DNA-based** adds only GSE55645 (n=49, 2-level labels) — not worth it.

---

## Residual risks and uncovered scope (disclosed negatives)

1. **Industry-trial and non-English deposits with local sample codes** (the GSE126848 trap pattern) are structurally hard to find by label-join-capable search; the Thai PRJNA1089362 shows such deposits exist. Coverage of this space is best-effort, not exhaustive.
2. **ArrayExpress-native enumeration is impossible** (API retired); an AE-only deposit with minimal text could evade BioStudies relevance ranking (19 dataset accessions surfaced across 16 queries).
3. **Forward-citation walk is partial** (three source-paper citation walks not completed; mitigated by independent Europe PMC full-text sweeps).
4. **Two accession-unresolved papers** (PMID 38496899 PBMC/liver-fibrosis; PMID 41751802) were never chased to deposit level beyond abstract/search.
5. All repository states are snapshots of 2026-10-19; deposits released after this date are not covered. A re-sweep in 6–12 months (GRIPonMASH, Sci Data follow-ups, MASLD-nomenclature deposits) is cheap and recommended.

*Verification artifacts (triage TSVs, per-agent evidence reports with exact SOFT/JSON quotes, search logs) are preserved in the workspace research folder for audit.*
