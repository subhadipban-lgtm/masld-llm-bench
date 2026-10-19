# Subagent 06 — Adversarial Review of the Negative Result (MASLD blood + histology cohorts)

Date: 2026-10-19 (Asia/Bangkok). Role: adversarial reviewer; mission: break the negative ("no new qualifying cohort; the only blood+histology deposits are the 8 already-known accessions"). All facts below are from fetches made this session (eutils db=gds esearch/esummary ×3, GEO SOFT text ×16 accessions incl. full/gsm views, Europe PMC ×3 queries, 1 web search). URLs quoted inline.

## VERDICT

**YES, WITH CAVEATS — the negative stands.** No new qualifying blood cohort was found. Four reporting corrections are required (below): the sweeps missed GSE267031 entirely (a liver subseries of the anchor superseries — does not qualify as blood but must appear in the report), two liver MASLD accessions with per-sample fibrosis labels (GSE240729, GSE249997) are absent from geo_triage.tsv, and one new literature lead (PMID 41751802, whole-blood ncRNA in African Americans with MASLD) must be added to the watchlist. The "bulk WBC arm > 35" trigger did NOT fire: GSE267032 is exactly 35 GSMs (14 Control + 21 graded MAFLD/MASH).

## Attack findings

### Vector 1 — Coverage gaps (new-nomenclature and PAXgene/Tempus query spaces)

**(a) MASLD/MASH + blood terms (db=gds):** `(MASLD OR MASH) AND ("whole blood" OR PBMC OR "peripheral blood" OR leukocyte OR leukocytes OR "blood cells") AND Homo sapiens[Organism] AND gse[ETYP]` → 13 hits. Union with (b) surfaced 4 accessions absent from geo_triage.tsv:
- **GSE318806** "P21+TREM2+-Senescent Macrophages Fuel Inflammaging and MASLD. [Blood]" — SOFT `overall_design`: "Blood from biological male or female human donors were collected and PBMCs were isolated at UCLA's Virology Core. 100 x 10^6 blood cells were collected from **3-5 donors with no clinical information**." n=9 GSMs → fails n, no disease labels. Not a qualifier. (URL: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE318806)
- **GSE303156** circulating exosomal miRNA, T2D ± MASH — 10 GSMs, serum exosomes. Not a qualifier.
- **GSE240729** and **GSE249997** — see corrections; both turned out to be LIVER deposits (below).
- All other hits already in geo_triage.tsv.

**(b) "metabolic (dysfunction)-associated" / "steatotic liver" / MAFLD variants:** → 42 hits; dominated by mouse/in-vitro/HepG2/HSC series already known. New finds were only GSE240729 + GSE249997 (both liver, below). The new-nomenclature space contains **no missed human blood transcriptome cohort**.

**(c) PAXgene/Tempus/whole-blood-RNA + liver biopsy/histology:** → only 3 hits, all unrelated-disease: GSE112087 (SLE blood), GSE134310 (scleroderma PBMC, 229 GSMs/63 participants, systemic sclerosis HSCT trial), GSE186580 (IL-2 Treg, arthritis). **Zero NAFLD/MASLD hits** — this query space is now demonstrably empty in GEO, closing the gap.

**(d) Europe PMC full-text:** 3 queries — `"whole blood" AND "liver biopsy" AND "RNA-seq" AND (NAFLD OR NASH OR MASLD)` (136 hits), PBMC/whole-blood + biopsy-proven/fibrosis-stage + transcriptome terms (929 hits), `"blood transcriptome" AND (MASLD OR MAFLD OR NAFLD OR NASH)` (103 hits); top-100 of each walked. No paper with a missed ≥100-sample blood cohort. **One new lead**: PMID 41751802 (2026) "Transcriptomic Profiling of MicroRNA and Non-Coding RNA from Whole Blood of African Americans with MASLD" (https://pubmed.ncbi.nlm.nih.gov/41751802) — abstract calls it a **pilot study** of miRNAs/ncRNAs (non-coding RNA, not bulk mRNA); same group (T. Mondal) as the papers.tsv Mondal 2023 row whose data were "available upon reasonable request"; no GSE/PRJNA accession surfaced in abstract or search. Non-qualifying (assay = miRNA/ncRNA, pilot n, no evident per-sample histology, no evident deposit) but must be watchlisted.

### Vector 2 — Rejection audit (5 sampled suspicious verdicts)

All 5 spot-checked rejections were CORRECT, none premature:
1. **GSE83898** (was "liver tissue / single-cell"): SOFT brief — 74 GSMs, "FFPE biopsies collected from the livers of well-characterized chronic **HBV** patients (n=74)". Liver + wrong etiology. ✓
2. **GSE134310** (was "unrelated disease"): "Peripheral Blood Gene Expression … Systemic Sclerosis … SCOT trial". PBMC, scleroderma. ✓ (n=229 GSMs — worth a glance only because it is big; disease is not MASLD and no liver histology.)
3. **GSE110041** (was "unrelated"): "In-vitro stimulation of healthy donor blood with IL-3". ✓
4. **GSE180241** (was ambiguous "needs manual check"): "blood outgrowth endothelial cells (BOECs) … cultivated from NAFLD patients and healthy controls (n=3 each)", RNA-seq in triplicate, 6 GSMs. Cultured blood-derived cells, tiny, no histology labels → rejection upheld (was ambivalently triaged; now resolved as not-qualifying). ✓
5. **GSE204963/964/965** (ambiguous): esummary titles confirm all three are siblings of the in-vitro MBOAT7 series ("…MBOAT7 regulates toll like receptor induced outcomes [ATAC-seq]/[Cut&Tag]/[RNA-seq]") — in-vitro, no patient histology. ✓

### Vector 3 — Superseries recheck: GSE267195

SOFT full view (https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE267195&targ=self&form=text&view=full): "This SuperSeries is composed of the SubSeries listed below. RELATION SuperSeries of: **GSE267031**, GSE267032, GSE267033." Total = **68 GSMs**, composition exactly 18 + 35 + 15:
- **GSE267031 "Bulk Liver in MAFLD/MASH"** — 18 GSMs, "Bulk RNA-seq samples were collected from **liver needle biopsies** from MAFLD/MASH patients and histologically stratified by disease stage (**NAS score**)". **This subseries is absent from plan.md's known-excluded list, from subagent_01's triage notes, and from papers.tsv's anchor row.** It is LIVER, not blood — it does not qualify and does not change the blood negative — but the report must include it (see corrections).
- **GSE267032 "Bulk White Blood Cells in MAFLD/MASH"** — 35 GSMs (below). The trigger "if bulk WBC arm > 35" did **not** fire.
- GSE267033 — scRNA-seq peripheral immune cells (known).

### Vector 4 — N-counting of GSE267032 (user belief "~35 (21 graded)")

GSM-level SOFT (targ=gsm): **exactly 35 GSMs** (GSM8258746–GSM8258780). Per-sample characteristics `disease`/`condition` tally: **0_healthy/Control = 14; MAFLD/MASH = 21** (1_low = 8, 2_medium = 6, 3_high = 7). `celltype: wbc`, `assaytype: bulk`. → The user's count is exactly right; **no hidden labeled samples**; the deposit's per-sample labels (disease + low/medium/high) are join-able directly from GSM characteristics.

### Vector 5 — False-negative check on strongest near-misses

- **GSE185062** (full view): serum miRNA only — "2,083 serum miRNAs … 183 NAFLD cases … and 10 population controls", 193 GSMs, relations only BioProject PRJNA767557/SRA SRP339456 — **no blood-cell arm, no sub-series**. Rejection correct. ✓
- **GSE117623** (full view): single series, **no SubSeries relations**; "circulating epithelial cells (CECs) were enriched from peripheral blood from patients with chronic liver disease and hepatocellular carcinoma. Select samples were further flow sorted for WBC subsets." — no MASLD-only subseries, no staging labels. Rejection correct. ✓

## Required corrections to the sweep agents' claims

1. **GSE267031 must be added everywhere** (plan.md known-excluded context, subagent_01 triage, papers.tsv anchor row, final report REJECTED/near-miss table): GSE267195 is a **3-part** superseries (Bulk Liver n=18 + Bulk WBC n=35 + scRNA n=15 = 68), not the 2-part composition implied by all sweep documents. GSE267031 is liver (NAS-stratified needle biopsies) — label it not-blood.
2. **papers.tsv anchor-row inconsistency to reconcile**: row says "22 patients liver-RNA-seq" but the deposited bulk-liver arm GSE267031 has **18 GSMs**. Flag for Round-2 join verification (do not assert either number as final; the 22 may include the scRNA or FACS subset, or 4 samples may be undeposited).
3. **geo_triage.tsv completeness gap (subagent_01)**: add at minimum **GSE240729** (67 GSMs, `tissue: liver (FFPE)`, per-sample `fibrosisscore: F0–F4`, MASLD biomarker study — the "blood-based biomarker panel" is a protein panel; the transcriptomic DEPOSIT is liver; PRJNA1005170; https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE240729) and **GSE249997** (77 GSMs, all `source: liver`, "early MASLD", brain-MRI correlation study, PRJNA1051582). Neither is blood → not qualifiers, but both are histology-labeled liver MASLD transcriptomes that a "liver near-miss/anti-confusion" table should carry.
4. **Watchlist addition**: PMID 41751802 (Mondal 2026, whole-blood miRNA/ncRNA pilot, African Americans with MASLD) — accession-unresolved; pair it with the existing Mondal 2023 row (same group, same "data on request" pattern).

## Residual risks that must be stated in the report

- Europe PMC and db=gds sweeps cover indexed deposits only; industry-trial or non-English/SRA-only blood cohorts with local sample codes remain structurally uncoverable (subagent_04's risk #2/#4 unchanged).
- PMID 41751802's deposit status was checked by abstract/search only, not by contacting authors; if data were deposited under an unlisted accession, it is still non-qualifying today (pilot, ncRNA assay, no evident histology labels).
- ArrayExpress-native API remains dead (per subagent_02); an AE-only deposit would evade the current tooling (low probability given community practice, but state it).
- Esummary-derived n's elsewhere in the triage were spot-checked only for the anchor series; GSE73634-style GSM≈2×participant inflation is known and flagged in subagent_01.

## Bottom line for the report

The negative is robust: the only public blood+histology deposits remain the known 8; GSE267032 offers exactly 35 bulk-WBC samples (21 graded + 14 controls) — the largest verifiable open blood cohort — and the recommendation should pivot on it and/or multi-cohort meta-design, now with GSE267031 (paired liver arm) documented as part of the same deposit family.
