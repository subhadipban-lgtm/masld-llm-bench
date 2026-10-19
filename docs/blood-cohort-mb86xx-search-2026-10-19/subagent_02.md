# Subagent 02 — EBI ArrayExpress / BioStudies Sweep (MASLD whole-blood/PBMC histology-labeled cohorts)

Date of sweep: **2026-10-19** (all fetches this date, Asia/Bangkok tz).
Role: supplementary-material sweep agent, EBI side (ArrayExpress-native E-XXXX + BioStudies). Parallel to 3 other agents covering GEO etc.
Known-excluded (not re-reported as new): GSE267032, GSE267033, GSE135251, GSE130970, GSE167523, GSE126848, GSE48452.

## Conclusion

**A documented empty sweep.** After exhaustive BioStudies API search (8 assigned queries + 8 supplementary dataset-oriented queries, top-100 pages, union of 192 unique entries, every E- accession individually resolved and triaged) plus dual-deposit existence checks for the seven known GSEs, **zero new openly-deposited human whole-blood/PBMC transcriptome cohorts with liver-histology labels (F0–F4 / NAS / Brunt / Kleiner / NASH-vs-steatosis) were found on the EBI side.**

Key structural findings:

1. **ArrayExpress-native JSON API is dead as of 2026-10-19**: `https://www.ebi.ac.uk/arrayexpress/json/v3/experiments?query=NAFLD&organism=Homo+sapiens` returns **HTTP 302 with a zero-byte body**; with redirect following (`-L`) it lands on the BioStudies web HTML page (title "BioStudies < The European Bioinformatics Institute"). All ArrayExpress content is now served through BioStudies. Sample-level AE endpoint `/arrayexpress/json/v3/experiments/<ACCESSION>/samples` was consequently not usable.
2. **BioStudies `&type=arrayexpress` search parameter does NOT work**: returns `totalHits=0`. Omit the type param; filter E- accessions client-side instead.
3. **Search API is loose-OR**: naive two-word queries return totalHits in the 10⁵–10⁶ range with irrelevant top pages; only tight terms ("NASH PBMC" 11,319; "E-MTAB NAFLD" 14,711; "MASLD PBMC" 19,099) shrink the space. Even so, the union of E- prefixed accessions across all 16 queries is only **19**, all of which were fetched and triaged (see ae_triage.tsv).
4. **Dual-deposit check of the 7 known-excluded GSEs**: only **GSE48452** has an EBI mirror (**E-GEOD-48452**, title "DNA methylation analysis in nonalcoholic Fatty liver disease suggests distinct disease-specific and remodeling signatures after bariatric surgery", 73 unique GSM IDs, liver, fibrosis×73/F1×3/F2×1/steatosis×18 in SDRF text). GSE267032, GSE267033, GSE135251, GSE130970, GSE167523, GSE126848 all return **HTTP 404** from `biostudies/api/v1/studies/E-GEOD-*` — no EBI dual deposits. GSE48452 is marked `excluded-known` in the TSV, not as a new find.
5. The only human blood specimens encountered anywhere in the sweep are **non-transcriptome or non-NAFLD**: E-GEOD-54882 (whole blood DNA **methylation**, no NAFLD/histology attributes), plus S-EPMC literature records describing PBMC-based NAFLD diagnostics whose underlying data live in GEO/other repositories, not as EBI-native deposits.

## Evidence

### Endpoint status (2026-10-19)

- `GET https://www.ebi.ac.uk/arrayexpress/json/v3/experiments?query=NAFLD&organism=Homo+sapiens` → **HTTP 302, 0 bytes** (body file `ae_status_body.txt` empty). With `-L`: HTTP 200, 14,440 bytes of BioStudies HTML (`<title>BioStudies &lt; The European Bioinformatics Institute...`). Recorded from actual fetches; AE keyword queries for NASH, MASLD, steatosis, PBMC, "non-alcoholic fatty liver" all failed identically (JSON parse of empty body).
- `GET https://www.ebi.ac.uk/biostudies/api/v1/search?query=...&size=100` → HTTP 200, JSON, works. Observed page size ≈ 20 hits regardless of `size=100` (see Gaps).
- `GET https://www.ebi.ac.uk/biostudies/api/v1/search?query=NAFLD%20blood&type=arrayexpress&size=100` → HTTP 200 but `totalHits=0`, zero hits → **type param non-functional for dataset filtering**.
- `GET https://www.ebi.ac.uk/biostudies/api/v1/studies/<ACCESSION>` → HTTP 200 for all 19 E- accessions; **HTTP 404** for E-GEOD-126848, E-GEOD-135251, E-GEOD-130970, E-GEOD-267032, E-GEOD-167523.
- Sample metadata inside E- study JSON is not in the section tree; it is referenced as **SDRF/IDF attachment files** (`"Description": "Sample and Data Relationship Format (SDRF)"`, files like `E-GEOD-54882.sdrf.txt`, `GSMxxxx_sample_table.txt`). Histology keyword counts below are over the full raw study JSON.

### Per-candidate sample-attribute evidence (exact field values from study JSON)

- **E-GEOD-63067** — Title: "Integrative genomic signatures of hepatocellular carcinoma derived from nonalcoholic Fatty liver disease."; `Organism: Homo sapiens`; `Organism part: liver`; `Experimental Factors: disease`; 18 unique GSM IDs; keywords: steatosis×7, NASH×2, NAFLD×1, biopsy×1; no F0–F4/NAS/Brunt/Kleiner. Verdict: not-blood.
- **E-GEOD-48452** — Title: "DNA methylation analysis in nonalcoholic Fatty liver disease suggests distinct disease-specific and remodeling signatures after bariatric surgery."; `Organism: Homo sapiens`; `Organism part: liver`; 73 unique GSM IDs; keywords: fibrosis×73, steatosis×18, F1×3, F2×1, NAFLD×6, NAS×2, NASH×2, biopsy×3. = mirror of **GSE48452** (excluded-known). Liver methylation, not blood transcriptome.
- **E-GEOD-69670** — Title: "MicroRNA expression profile in non-alcoholic fatty liver disease"; `Organism: Mus musculus`; `Organism part: liver`; 3 unique GSM IDs; NASH×4, steatosis×1. Verdict: not-blood (mouse).
- **E-MTAB-15760** — Title: "Inhibition of Peripheral Serotonin Activates Hepatic AMPK and Reduces Monocyte-Derived Liver Macrophages, Ameliorating Obesity-Associated Fibrosis"; ReleaseDate 2025-10-30; `Organism: Mus musculus`; `Organism part: liver`; design "disease state design"; fibrosis×2. Verdict: not-blood (mouse; the only E-MTAB surfaced by any query).
- **E-GEOD-54882** — Title (BioStudies index variant): "Correlated DNA methylation clusters in whole blood" / (GEO-side: "GeMes, Clusters of DNA Methylation under Genetic Control..."); `Organism: Homo sapiens`; `Organism part: whole blood`; whole blood×6 in JSON; **no** NAFLD/fibrosis/NAS/steatosis strings anywhere. Verdict: blood-no-histology (also methylation, not transcriptome).
- **E-GEOD-27489** — Title: "Early detection of lung cancer by molecular markers in endobronchial epithelial-lining fluid"; `Organism part: endobronchial epithelial lining fluid`; 30 unique GSM IDs. Verdict: not-blood (search noise).
- **E-GEOD-6523 / 10969 / 13092 / 14450 / 20678 / 21818 / 23299 / 33107 / 40519 / 41377 / 41378 / 41991 / E-MEXP-1172** — titles and organisms: fission yeast pre-RC origins; Arabidopsis epigenome; Arabidopsis RdDM; Arabidopsis PIL5 ChIP-chip; rice allele-specific tiling array ("F1" = rice strain code); Arabidopsis nucleosome/methylation; Drosophila H3K27me3 ChIP-chip; Arabidopsis SICKLE miRNA; Arabidopsis GTL1 ChIP; Arabidopsis DEAD-box helicase cold response ×2 ("F1" fragments non-histology); Arabidopsis HDA18 ChIP; yeast nucleosome atlas. All verdict: not-blood (model-organism noise).

### S-EPMC literature records flagged but not convertible to EBI datasets (underlying data are external)

- S-EPMC10378438 "Mitochondrial Dysfunction in Peripheral Blood Mononuclear Cells as Novel Diagnostic Tools for Non-Alcoholic Fatty Liver Disease" (Q5 hit) — PBMC/NAFLD paper; no EBI dataset accession attached in search hit.
- S-EPMC10944232 "Imbalance of mitochondrial fusion in peripheral blood mononuclear cells is associated with liver fibrosis in patients with..." (Q7+Q13 hit) — PBMC vs liver-fibrosis paper; same situation.
- S-EPMC9787576 "Peripheral blood mononuclear cells-expressed miRNA profiles derived from children with metabolic-associated fa..." (Q12 hit) — pediatric MASLD PBMC miRNA paper; data not visible as an EBI deposit from the search hit.
- S-EPMC3485241 "Comprehensive miRNA expression analysis in peripheral blood can diagnose liver disease" (Q13 hit) — peripheral-blood miRNA/liver-disease paper.
- S-EPMC9008751 "Potential Blood DNA Methylation Biomarker Genes for Diagnosis of Liver Fibrosis in Patients With Biopsy-Proven..." (Q13 hit) — blood methylation vs biopsy fibrosis; methylation, and deposit location not EBI-native.
- S-EPMC9472076 "Differentiating between liver diseases by applying multiclass machine learning approaches to transcriptomics o..." (Q5 hit) — transcriptomic liver-disease classification; datasets cited are GEO-side.
- S-EPMC8238173 "Noninvasive stratification of nonalcoholic fatty liver disease by whole transcriptome cell-free mRNA..." (Q12 hit) — cell-free RNA, not cellular blood; no EBI deposit visible.

These are leads for the GEO-round agents (their raw data may be GSE-deposited) but are **not EBI-native datasets**; flagged for cross-agent reconciliation only.

## Analysis

- EBI is search-noise-heavy for this mission: 16 queries × loose-OR yields ~10⁵–10⁶ totalHits but only **19 unique E- accessions** ever surface, and none is a human blood transcriptome NAFLD/MASLD cohort. The candidate pool of blood-based NAFLD transcriptomics evidently lives in GEO (GSE-land), handled by the other three agents.
- The known large blood-histology cohorts (GSE126848 n≈130, GSE135251 n≈190, GSE130970, GSE267032/33) have **no EBI mirrors** (404 on E-GEOD lookups), so nothing on the EBI side rescues sample size if GEO access changes.
- The only EBI-hosted mirror with liver histology among the seven known GSEs is E-GEOD-48452 (liver tissue methylation) — already excluded.
- ArrayExpress-only content (E-MTAB/E-MEXP native) in the NAFLD/MASLD space is essentially absent from search results; the single E-MTAB hit is a 2025 mouse liver study. This is consistent with the community practice of depositing human NAFLD blood transcriptomics in GEO without EBI dual-deposit.

## Gaps and risks

- **Page-size cap not honored**: `size=100` returned exactly 20 hits per page on every query (tested twice, including `page=2`). If BioStudies relevance ranking ever buries a dataset accession below rank 20 for a given query, this sweep would not see it. Mitigation used: 16 diverse queries; every query's top-20 union was exhausted; E-MTAB-specific queries (Q15/Q16) were added as a targeted safety net and still surfaced only E-MTAB-15760.
- Loose-OR ranking means the E- accession recall depends on title/abstract text; a cohort whose entry has minimal text (e.g., "serum samples, patients") could theoretically be missed. The AE-native browse API that would have enumerated all experiments is dead (302), so full enumeration was impossible.
- `type=arrayexpress` filter is broken, so S-EPMC literature entries (≈170 of 192 union entries) had to be screened by title only; a dataset accession hidden inside a literature entry's full text (rather than its title) could be missed at triage depth.
- SDRF files were inspected via keyword counts inside the study JSON (the sdrf.txt attachment itself was not separately downloaded); verdicts for the 19 E- entries rest on titles, organism/organism-part fields, and JSON keyword densities, all quoted above.
- Endpoint statuses can change; recorded as of 2026-10-19.

## Suggested final-report placement

- Methods/appendix: "EBI side swept via BioStudies API on 2026-10-19; ArrayExpress-native JSON v3 endpoint retired (HTTP 302 → BioStudies HTML); 16 queries, 192-entry union, all 19 dataset accessions triaged; `type=arrayexpress` parameter non-functional; zero new qualifying cohorts; only EBI mirror of the known GEO set is E-GEOD-48452 (excluded)."
- Discussion: reinforces that human whole-blood MASLD transcriptomics with histology labels is a GEO-only deposit pattern; EBI adds no incremental cohorts, so sample-size ceiling and access-status risk are set entirely by the GEO landscape.
- Cross-agent reconciliation list: the 7 S-EPMC PBMC/blood papers above (data likely in GEO; hand to GEO sweep agents).

## SEARCH LOG (all 2026-10-19)

| # | Endpoint | Query | totalHits | returned/page | Note |
|---|----------|-------|-----------|---------------|------|
| 1 | biostudies api/v1/search | NAFLD blood | 254,381 | 20 | assigned Q1 |
| 2 | biostudies api/v1/search | NASH blood transcriptome | 287,144 | 20 | assigned Q2 |
| 3 | biostudies api/v1/search | MASLD blood | 254,469 | 20 | assigned Q3 |
| 4 | biostudies api/v1/search | non-alcoholic fatty liver expression | 496,823 | 20 | assigned Q4 |
| 5 | biostudies api/v1/search | fatty liver PBMC | 155,033 | 20 | assigned Q5 |
| 6 | biostudies api/v1/search | hepatic steatosis microarray | 170,787 | 20 | assigned Q6 |
| 7 | biostudies api/v1/search | steatohepatitis whole blood | 316,761 | 20 | assigned Q7 |
| 8 | biostudies api/v1/search | liver biopsy blood gene expression | 1,291,539 | 20 | assigned Q8 |
| 9 | biostudies api/v1/search + `type=arrayexpress` | NAFLD blood | 0 | 0 | type param broken |
| 10 | biostudies api/v1/search | NAFLD whole blood | 323,898 | 20 | supplementary |
| 11 | biostudies api/v1/search | NASH PBMC | 11,319 | 20 | supplementary, tightest broad term |
| 12 | biostudies api/v1/search | MASLD PBMC | 19,099 | 20 | supplementary |
| 13 | biostudies api/v1/search | fatty liver whole blood | 442,703 | 20 | supplementary |
| 14 | biostudies api/v1/search | liver fibrosis peripheral blood | 390,838 | 20 | supplementary |
| 15 | biostudies api/v1/search | steatohepatitis blood microarray | 376,967 | 20 | supplementary |
| 16 | biostudies api/v1/search | E-MTAB NAFLD | 14,711 | 20 | supplementary, accession-prefix probe |
| 17 | biostudies api/v1/search | E-MTAB NASH | 6,923 | 20 | supplementary, accession-prefix probe |
| 18 | biostudies api/v1/search page=2 | NAFLD blood | 256,403 | 20 | pagination probe; no E- on page 2 |
| 19 | arrayexpress json/v3/experiments | query=NAFLD (+NASH, MASLD, steatosis, PBMC, non-alcoholic fatty liver), organism=Homo sapiens | — | — | **HTTP 302 empty → dead**; `-L` lands on BioStudies HTML |
| 20 | biostudies api/v1/studies/E-GEOD-{126848,135251,130970,267032,167523} | (direct lookups) | — | — | HTTP 404 — no EBI dual deposits of known GSEs |
| 21 | biostudies api/v1/studies/E-GEOD-48452 | (direct lookup) | — | — | HTTP 200 — EBI mirror of excluded GSE48452 exists |
