# subagent_05 — numerical-definitions VERIFICATION (7 near-miss items)
Date: 2026-10-19 | Verifier: numerical-definitions agent | Method: direct curl fetches only (no re-search)
Note on budget: NCBI FTP/CGI stalls forced several retries; tool-call budget slightly exceeded (~26 calls). All 7 items nonetheless resolved; failures are recorded explicitly.

---

## 1. Sci Data 2026 plasma cell-free RNA cohort (PMID 42173964 / BioStudies S-BSST1614)
**CLAIM**: plasma cfRNA, open processed counts, no per-sample histology, MASLD only a subset → near-miss, exclude.

**FETCHED**:
- https://www.ebi.ac.uk/biostudies/api/v1/studies/S-BSST1614 (full JSON, 2861 bytes)
- https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:42173964%20AND%20SRC:MED&resultType=core&format=json
- Range-fetch (0-1500 bytes) of https://www.ebi.ac.uk/biostudies/files/S-BSST1614/htseq_cohort1.txt

**EXACT QUOTES**:
- BioStudies Study Title: `"Overcoming the main current diagnostic challenges in hepatology"`
- BioStudies Description: `"RNAseq data from plasma samples corresponding to a Grand Challenge Project aiming to find biomarkers for liver disease, including NAFLD, NASH, Cirrhosis and Hepatocelullarcarcinoma."` (sic)
- Files in deposit (complete list): `"htseq_cohort1.txt" (12,964,901 bytes, "Cohort_1_Raw_CountMatrix")`, `"htseq_cohort2.txt" (101,133,609 bytes, "Cohort_2_Raw_CountMatrix")`; subsections = 4 authors + 1 organisation (Ghent University). **Zero sample-level subsections/attributes exist in the submission.**
- EuropePMC title: `"Plasma cell-free transcriptome profiling in blood plasma from chronic liver disease patients."`, Scientific Data 2026, doi 10.1038/s41597-026-07470-2
- Abstract: `"we generated a high-throughput extracellular RNA sequencing dataset from blood plasma samples collected from patients at various stages of liver disease. Samples were obtained from two independent cohorts of 112 (cohort 1) and 489 (cohort 2) patients, and profiled using total RNA sequencing, resulting in 112 and 820 extracellular transcriptomic profiles for cohort 1 and 2, respectively."`
- Counts matrix header (cohort1): `ensembl_gene_id RNA015584 RNA015585 RNA015586 RNA015587 ...` → columns keyed by anonymous RNAxxxxx IDs with **no phenotype/metadata file in the deposit to map them**.

**VERDICT: confirms-claim (correctly excluded).** Specimen = blood plasma (extracellular/cfRNA, NOT blood cells). Total patients = 601 (112+489). No per-sample liver histology fields anywhere in the deposit (no fibrosis stage/NAS, no biochemical scores either — the deposit contains only two count matrices). NAFLD/NASH is one indication inside a mixed CLD cohort. Sample IDs are anonymous RNAxxxxx; the label join is not verifiable from the deposit alone. Not a plausible blood-cell candidate.

---

## 2. GSE55645 (n=49 blood lymphocytes, aCGH)
**CLAIM**: n=49 blood lymphocytes, Stage NASH/Simple steatosis, SNP/CNV array NOT transcriptome.

**FETCHED**:
- https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE55645&targ=self&form=text&view=brief
- https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE55645&targ=gsm&form=text&view=brief (full 49-GSM dump, 203,637 bytes)
- (family.soft.gz from NCBI FTP was unreachable/corrupt on 3 attempts — CGI text route used instead; recorded as a route failure, not a data failure)

**EXACT QUOTES**:
- `!Series_title = Genome wide analysis of copy number variation in NAFLD spectrum`
- `!Series_type = Genome variation profiling by genome tiling array`
- `!Series_overall_design = Genomic DNA was extracted from blood obtained from patients with NAFLD and submitted for genome-wide analysis using aCGH`
- Per-GSM (49/49): `!Sample_type = genomic`, `!Sample_molecule_ch1 = genomic DNA`, `!Sample_platform_id = GPL9777`, `!Sample_characteristics_ch1 = blood: lymphocytes`
- Stage inventory (49 GSMs): `39 × !Sample_characteristics_ch1 = Stage: NASH` and `10 × !Sample_characteristics_ch1 = Stage: Simple steatosis`
- Title examples: `!Sample_title = Simple steatosis [0599_SEN_252185017026_S01_CGH_107_Sep09_1_1]`, `!Sample_title = NASH [0599_SEN_252185017026_S01_CGH_107_Sep09_1_2]`

**VERDICT: confirms-claim.** Assay is genomic aCGH (GPL9777), not transcriptome; n=49; specimen blood lymphocytes. **If the assay criterion were relaxed, the label join IS verifiable**: each GSM block carries the Stage characteristic, and titles repeat the same stage label keyed to the same array ID within the same GSM. Caveat: labels are only 2-level (NASH vs simple steatosis) — no fibrosis stage F0-F4, no NAS.

---

## 3. GSE117623 (n=137 peripheral blood, CLD+HCC, no staging)
**CLAIM**: n=137 peripheral blood, CLD+HCC, no staging.

**FETCHED**:
- https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE117623&targ=gsm&form=text&view=brief (head 150)
- https://ftp.ncbi.nlm.nih.gov/geo/series/GSE117nnn/GSE117623/soft/GSE117623_family.soft.gz (full inventory greps)

**EXACT QUOTES**:
- `!Series_title = The Liquid Liver Biopsy: Detection of Circulating Epithelial Cells in Liver Disease`
- `!Series_summary = Using a microfluidic device, circulating epithelial cells (CECs) were enriched from peripheral blood from patients with chronlic liver disease and hepatocellular carcinoma. Select samples were further flow sorted for WBC subsets. CEC and WBC subsets transcriptomes were sequenced.` (sic)
- Sample count: 137. All 137: `!Sample_characteristics_ch1 = tissue: Peripheral blood`
- Cell types: `116 × cell type: Circulating epithelial cells`; plus WBC subsets: NK cells 4, Monocytes 4, Helper T cells 4, Granulocytes 3, Cytotoxic T cells 3, B cells 3
- Diagnosis (only two values): `73 × diagnosis: Hepatocellcular carcinoma patient` (sic), `64 × diagnosis: Chronic liver disease patient`
- grep -icE "nafld|nash|steato|fibros" across whole SOFT family = **0**

**VERDICT: confirms-claim.** No fibrosis/NAS/steatosis field anywhere; no NAFLD etiology mention (etiologies unspecified). Specimen is CEC-enriched fractions (+ 21 flow-sorted WBC subset runs), not bulk blood cells. Excluded on cell type, label absence, and etiology grounds.

---

## 4. GSE73634 (paired blood+biopsy, simtuzumab HCV/HIV trial)
**CLAIM**: paired blood+biopsy, HCV/HIV simtuzumab trial, staging not per-sample.

**FETCHED**:
- https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE73634&targ=gsm&form=text&view=brief (head 120)
- https://ftp.ncbi.nlm.nih.gov/geo/series/GSE73nnn/GSE73634/soft/GSE73634_family.soft.gz (full inventory)

**EXACT QUOTES**:
- 48 samples total; characteristics inventory: `48 × disease state: advanced liver fibrosis` (blanket value on every sample, blood and liver alike), `24 × tissue: blood`, `24 × tissue: liver`, `24 × treatment: simtuzumab`, `24 × treatment: none`, `24 × time point: pre-treatment`, `24 × time point: post-treatment`, `participant: 1..12`
- `!Sample_treatment_protocol_ch1 = Study participants received 700 mg of simtuzumab (Gilead Sciences, Inc., CA) intravenously over 30 minutes every 2 weeks for 22 weeks (12 infusions).`
- `!Sample_growth_protocol_ch1 = This phase 2a, open-label, single center exploratory study assessed the safety, tolerability and potential efficacy of simtuzumab in HCV- and/or HIV-infected adults (NCT01707472).`
- grep -icE "nafld|nash|steato" = **0**

**VERDICT: confirms-claim.** Etiology HCV and/or HIV; "advanced liver fibrosis" is a single blanket disease-state value, not a per-sample fibrosis stage (no F-scores anywhere). Blood arm n=24 (<100). Correctly excluded.

---

## 5. GSE247467 (neutrophils n=12, MASH vs healthy)
**CLAIM**: neutrophils n=12, MASH vs healthy, no grade field.

**FETCHED**:
- https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE247467&targ=gsm&form=text&view=brief (head 80)
- https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE247467&targ=self&form=text&view=brief
- https://ftp.ncbi.nlm.nih.gov/geo/series/GSE247nnn/GSE247467/soft/GSE247467_family.soft.gz

**EXACT QUOTES**:
- Titles (12): `Advanced_1..4, Mild_1..3, Normal_1..5`
- Per-GSM: `!Sample_characteristics_ch1 = tissue: Peripheral blood`, `!Sample_characteristics_ch1 = cell type: Neutrophil`, `!Sample_characteristics_ch1 = disease state: MASH` (8 samples) / `disease state: healthy` (4 samples)
- Metadata quirk: `Normal_1` carries `disease state: MASH` in GEO metadata (8 MASH + 4 healthy vs 7 MASH + 5 Normal by title) — a per-sample inconsistency worth flagging, though irrelevant to the verdict.
- `!Series_overall_design = Using negative selection, we isolated peripheral neutrophils from subjects with biopsy proven mild and sever MASH and control individuals.` (sic) — biopsy-proven status is group-level wording only; no per-sample fibrosis stage or NAS characteristic exists.

**VERDICT: confirms-claim.** Cell type neutrophil, n=12, no fibrosis/NAS grade field, n far below 100. Correctly excluded.

---

## 6. PRJNA1089362 (Thai PBMC MASLD n=68)
**CLAIM**: PBMC MASLD n=68, no histology attributes in SRA/BioSample metadata.

**FETCHED**:
- https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=bioproject&term=PRJNA1089362&retmode=json → count 1 (project exists; esummary title empty, organism "Homo sapiens")
- https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=biosample&term=PRJNA1089362 → **count 0** (both plain and `[Bioproject]` qualifier — BioSample DB does not index this bioproject string; route failure recorded)
- https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=sra&term=PRJNA1089362 → count **68**, all RNA-Seq
- https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=sra&id=<8 UIDs> (XML)
- https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=biosample&id=SAMN40537230,SAMN40537229,SAMN40537228&retmode=xml

**EXACT QUOTES** (complete attribute set observed across 8 SRA samples + 3 BioSamples):
- `isolate = missing`; `age = missing`; `biomaterial_provider = Center of Excellence in Hepatitis and Liver Cancer, Faculty of Medicine, Chulalongkorn`; `collection_date = 2020/2023`; `geo_loc_name = Thailand: Bangkok`; `sex = restricted access`; `tissue = PBMC8` / `PBMC9` / `PBMC10` / ... / `PBMC68`; `BioSampleModel = Human`
- BioSample Title: `Human sample from Homo sapiens` (SAMN40537230)
- The `tissue=PBMC<n>` numbering runs up to PBMC68, consistent with n=68 PBMC specimens.

**VERDICT: confirms-claim → kill.** Specimen confirmed PBMC (Thailand, 2020-2023). The complete attribute-name set is {isolate, age, biomaterial_provider, collection_date, geo_loc_name, sex, tissue, BioSampleModel} — **no fibrosis/NAS/histology/telemetry attribute of any kind**, and even sex is access-restricted. A BioSample-level pass does NOT rescue it: labels are not joinable from the deposit.

---

## 7. PRJNA1305173 (claimed pediatric PBMC n=30, imaging-defined)
**CLAIM**: pediatric PBMC n=30, imaging-defined, no per-sample histology.

**FETCHED** (all returned empty):
- https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=bioproject&term=PRJNA1305173&retmode=json → `count: 0`
- https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=sra&term=PRJNA1305173 → `count: 0`
- https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=biosample&term=PRJNA1305173 → count 0
- https://www.ebi.ac.uk/ena/portal/api/search?query=study_accession%3DPRJNA1305173&result=read_run&... → header row only, zero runs

**EXACT QUOTES**: NCBI esearch warning: `"No items found."`; ENA returned only the TSV header `run_accession study_accession sample_accession library_strategy scientific_name` with no data rows.

**VERDICT: unverifiable.** The accession PRJNA1305173 does not exist in NCBI BioProject/SRA/BioSample or ENA. The claim (pediatric PBMC n=30, imaging-defined) cannot be confirmed or refuted from any deposit fetch — likely a mistyped accession carried in the earlier table. Recommend re-deriving the correct accession from the source publication before the report finalizes; as-is, it stays rejected/nonqualifying by default.

---

## OVERALL
**None of the 7 should be upgraded to a qualifying candidate.** Every fetch supports the exclusion verdicts: (1) S-BSST1614 is plasma cell-free RNA from a mixed-CLD cohort whose deposit contains only two count matrices keyed by anonymous RNAxxxxx IDs with no per-sample metadata at all — no histology, not blood cells, no joinable labels; (2) GSE55645 is genomic aCGH (GPL9777, "Genome variation profiling by genome tiling array"), not transcriptome — its per-sample Stage labels (39 NASH / 10 Simple steatosis) are joinable, so it is a legitimate relaxed-assay footnote but not a transcriptome cohort; (3) GSE117623 is CEC-enriched CLD/HCC blood with zero NAFLD/fibrosis/staging fields; (4) GSE73634 is a 24-subject HCV/HIV simtuzumab trial with a blanket "advanced liver fibrosis" state and no per-sample stage; (5) GSE247467 is n=12 neutrophils with group-level "biopsy proven" wording only (plus a Normal_1 metadata mislabel worth footnoting); (6) PRJNA1089362 is genuinely Thai PBMC n=68 but carries zero staging attributes and access-restricted covariates; (7) PRJNA1305173 could not be found in any repository and must be treated as an unverifiable/mistyped accession. The negative search result stands.
