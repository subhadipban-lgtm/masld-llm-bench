# Subagent 04 — Adversarial / Alternative-Framing Sweep (MASLD blood + histology cohorts)

Date: 2026-10-19 (Asia/Bangkok). Role: find cohorts the other sweeps would structurally miss; stress-test the premise. No visibility into other agents' outputs. All facts below come from fetches made this session (logs in `.openclaw/tmp/sa04/`).

## Conclusion

**Zero new qualifying candidates.** After 14 distinct eutils db=gds framings, 3 db=sra, 2 db=bioproject sweeps, Europe PMC, BioStudies/ArrayExpress (API failed, see Gaps), and 8 web searches, **no public bulk whole-blood/PBMC/peripheral-leukocyte transcriptome cohort of n ≥ 100 in NAFLD/MASLD with per-sample liver-histology labels was found beyond the already-known/excluded accessions**. The sweep instead produced a well-defined set of NEAR-MISSES (each failing exactly one criterion) and indirect negative-test evidence that such cohorts are genuinely scarce, not merely under-indexed. Two SRA/BioProject-only deposits are flagged as unverifiable rather than disqualified.

## Evidence

### Near-misses (fail exactly one criterion each; NOT new qualifying candidates)

1. **GSE247467 / SRP471237 — MASH circulating neutrophils, n=12** (verified via SOFT `acc.cgi?acc=GSE247467&targ=gsm&form=text&view=brief` and SRA esummary, 2026-10-19)
   - What I saw: `!Sample_source_name_ch1 = Peripheral blood`; `cell type: Neutrophil`; `disease state: MASH`; sample titles `Advanced_1..4`, `Mild_1..`, `Normal_..`. Submitter "Golden Lab, Medicine, USC". All 25 sampled SRA runs (30468197–30468208…) belong to SRP471237.
   - Fails: n=12 ≪ 100; purified neutrophils (not bulk WB/PBMC); no fibrosis-stage/NAS attribute — only coarse Mild/Advanced/Normal. URL: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE247467

2. **GSE185062 — serum miRNA across full NAFLD spectrum, n=193** (esummary db=gds, 2026-10-19)
   - What I saw: "profiled 2,083 serum miRNAs in a discovery cohort (183 NAFLD cases representing the complete NAFLD spectrum and 10 population controls)", HTG EdgeSeq, n=193.
   - Fails: serum cell-free miRNA, not blood-cell transcriptome. Would be the largest histology-labeled "liquid biopsy" if the team ever relaxes modality. URL: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE185062

3. **GSE49541 — liver biopsy, n=72, fibrosis F0-1 vs F3-4** (SOFT fetched 2026-10-19)
   - What I saw: 72 samples, `tissue: liver`, `Stage: advanced (fibrosis stage 3-4)` / `mild (fibrosis stage 0-1)`, GPL570. Found via web_search because the site surfaced it; it is liver, not blood — listed here so nobody re-litigates it. URL: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE49541

4. **GSE185051 — pediatric multiethnic NAFLD liver transcriptome** (SOFT checked 2026-10-19): `Sample_source_name_ch1 = liver` throughout; hepatic, not blood.

5. **PRJNA1089362 / SRP497495 — PBMC RNA-seq, MASLD (+HCC), n=68 runs, Chulalongkorn University, Thailand** (db=sra esearch+esummary, 2026-10-19)
   - What I saw: 68 public RNA-seq experiments (Illumina HiSeq X, paired), study name "Homo sapiens Transcriptome from PBMC in patient with MASLD and HCC"; sample names opaque (`FF66-146-LFL10671_L1`), Biosample accessions only (SAMN40537228…); **no fibrosis/NAS/histology attributes anywhere in SRA metadata**; no GEO mirror found.
   - Status: flag as *unverifiable join* — open fastq, but label join cannot be confirmed from the deposit without the authors' codebook. URL: https://www.ncbi.nlm.nih.gov/bioproject/PRJNA1089362

6. **PRJNA1305173 — pediatric PBMC RNA-seq, NAFLD n=16 vs control n=14** (PMC12754493 fetched 2026-10-19; Zeber-Lubecka et al., World J Hepatol 2025)
   - What I saw: adolescent cohort (median age 15), PBMC transcriptome, NAFLD diagnosis by CAP/ALT/"and/or histological examination"; Data availability: BioProject PRJNA1305173. Deposited n=30 total; no per-sample fibrosis/NAS labels evidenced in the paper text fetched. Fails: n ≪ 100, histology labels not per-sample.

7. **E-MTAB-6863** (via web_search, omicsdi): "RNA-seq of hepatic biopsies … different aetiologies (HCV, FLD) and fibrosis stages" — liver tissue; noted to prevent confusion with a blood arm.

### Premise stress-test (negative-test evidence)

- **Structure of the field**: every human blood-adjacent NAFLD transcriptomics study surfaced in ~30 queries is either (a) n ≤ 30 PBMC/qPCR papers (e.g., PMC12754493; "Noninvasive diagnostic criteria… PBMC cytokine/chemokine genes", scienceopen), (b) cell-sorted small cohorts (neutrophils n=12, NK cells n=4–7, monocyte-derived macrophages), or (c) serum/plasma miRNA. None enumerates a ≥100-sample bulk blood cohort with histology.
- **Review literature** (Europe PMC, 58 hits scanned; Miller 2011 systematic review of non-invasive markers, PMID 21382157; Gîlcă-Blanariu 2023 MDPI Metabolites 13:1115; Huang 2025 J Hepatol metabolome-derived score): blood biomarker development in MASLD routes through proteins/metabolites/miRNAs; none cites a public blood transcriptome cohort with histology, and multiple papers explicitly note "single-cohort" / "no external validation" limitations — consistent with the resource not existing publicly.
- **Indexing pollution**: db=gds `liver AND ("whole blood" OR PBMC…) AND (NAFLD…)` returns 219 hits, of which the top 40 esummarized were overwhelmingly **mouse** NAFLD studies or liver/serum — the word NAFLD in mouse summaries drowns human blood cohorts. MeSH-route (`"Non-alcoholic Fatty Liver Disease"[MeSH] AND leukocytes/blood cells`) returns **0**; a looser MeSH route returns 27, all murine/liver. This is why the premise is hard to satisfy by naive GEO search and why the excluded known accessions may genuinely be nearly the whole universe.
- **Counterpoint (against non-existence)**: EBI ArrayExpress/BioStudies API calls failed from this environment (below), so EBI-only deposits and non-English-labeled studies (Thai PRJNA1089362 was found only via BioProject author-institution-blind search) remain a live residual risk. Absence of evidence across my framings ≠ proof of absence.

### Alternative framings tested (per mission)

- Bariatric/T2D/metabolic-syndrome-indexed: 4+1+6 db=gds hits — none human blood+histology (GSE69039 Korean obesity PBMC n=18 has **no liver histology**; GSE9157 adipose).
- SuperSeries with blood+liver arms: esummary `relation/relationtype` fields were **empty for all 74 GSE docsums reviewed**; no hidden blood arm surfaced.
- SRA-only deposits: 188 SRA hits collapse to SRP471237 (+ an SLE study SRP136102, false positive); 223 human NAFLD BioProjects scanned — 49 titles listed, all cell-line/organoid/iPSC/liver except PRJNA1089362.
- 2025–2026 recent deposits (sort=pub_date, top 40): all murine/in-vitro.
- Microarray-era/MeSH: 0 direct MeSH hits; GSE33857 (serum exosomal miRNA incl. 7 NASH) and GSE48452 (excluded) are the era's relevant deposits.

## Analysis — productive vs dead-end framings

**Productive**: (1) db=bioproject organism+datatype filtered sweep — surfaced the only new near-miss (PRJNA1089362) that GEO- and web-centric sweeps structurally miss; (2) db=sra `"whole blood" AND "RNA-Seq"[Strategy]` — definitively mapped the SRA-only space (one study); (3) SOFT `targ=gsm` verification — repeatedly killed false leads (GSE49541 liver; GSE246221 mouse; GSE89632 liver) in one call each; (4) Europe PMC full-text — found the two PBMC papers GEO indexing misses.

**Dead ends**: (1) web_search with CJK characters (query mangled by provider → semiconductor noise); (2) zenodo/figshare supplementary-data search (generic noise; no processed matrices surfaced); (3) "SuperSeries subseries" web search (GSE = Government Sponsored Enterprise noise); (4) BioStudies/AE REST API (endpoint errors, below); (5) MeSH-strict queries (0 hits — GEO free-text doesn't honor MeSH the way PubMed does).

## Gaps and risks

1. **ArrayExpress/BioStudies unverified**: `ebi.ac.uk/biostudies/api/v1/studies/search` → `{"errorMessage":"Study not found"}`; `arrayexpress/json/v3/experiments` → non-JSON (HTML/blocked). Any AE-only deposit (e.g., a European biobank arm) is uncovered. E-MTAB-6863 (liver) is the only AE hit seen, via web.
2. **Non-English metadata**: the Thailand deposit shows non-English/locally-coded deposits exist; Korean/Chinese/japanese-labeled SRA-only deposits with local sample codes would evade every label-join check I ran.
3. **Biosample attributes**: I verified SRA experiment-level attributes for flagged deposits; BioSample-level attributes were not exhaustively parsed for all 68 PRJNA1089362 runs (budget) — a manual BioBrowse pass could still rescue or kill it.
4. **Positive-space risk**: figshare/GitHub-hosted processed matrices from industry trials (e.g., pharma MASH biopsy cohorts with adjunct blood draws) would have no accession and are findable only by paper-adjacent search; my two web attempts there were noisy, not exhaustive.
5. All esearch counts are live indexes; a deposit retracted/embargoed today could change results.

## Suggested final-report placement

- **"Premise stress-test"** section: the negative-test synthesis (blood-biomarker literature uses protein/metabolite/miRNA modalities; every bulk-blood hit is ≤30 samples or cell-sorted; indexing pollution explanation).
- **"Watchlist / fails-one-criterion"** table: GSE247467, GSE185062, PRJNA1089362, PRJNA1305173, GSE49541/GSE185051/E-MTAB-6863 (as anti-confusion entries).
- **"Residual risks / next probes"**: manual AE/BioStudies browse once API access works; BioSample attribute parse of PRJNA1089362; contact-author route for Thai cohort codebook.

## SEARCH LOG (all 2026-10-19; eutils retmax 25–40; raw logs in workspace `.openclaw/tmp/sa04/`)

**eutils db=gds esearch** (each = 1 query):
1. `("bariatric" OR "severe obesity" OR "morbid obesity") AND ("whole blood" OR PBMC) AND (biopsy OR histology OR fibrosis OR steatosis)` → 4
2. `"type 2 diabetes" AND ("whole blood" OR PBMC) AND (NAFLD OR NASH OR "fatty liver" OR "liver biopsy")` → 1
3. `("metabolic syndrome" OR "insulin resistance") AND ("whole blood" OR PBMC) AND (NAFLD…fibrosis)` → 6
4. `"liver biopsy" AND ("whole blood" OR PBMC) AND (steatosis OR "fatty liver" OR NAFLD OR NASH)` → 0
5. `liver AND ("whole blood" OR PBMC OR "peripheral blood") AND (NAFLD OR NASH OR steatosis OR "fatty liver")` → 219
6. `"Non-alcoholic Fatty Liver Disease"[MeSH] AND ("leukocytes"[MeSH] OR "blood cells"[MeSH])` → 0
7. `"Non-alcoholic Fatty Liver Disease" AND (leukocytes OR "blood cells")` → 27
8. `"hepatic steatosis" AND "peripheral blood"` → 3
9. `NAFLD OR NASH OR "non-alcoholic fatty liver"` (sort=pub_date) → 7650
10. `NASH AND PBMC` → 3
11. `MASLD AND ("whole blood" OR PBMC OR "peripheral blood")` → 9
12. `"liver histology" AND ("whole blood" OR PBMC OR "peripheral blood")` → 1 (GSE216064, AIH)
13. `"fibrosis stage" AND ("whole blood" OR PBMC OR "peripheral blood") AND ("fatty liver" OR NAFLD OR NASH OR steatosis OR obesity)` → 184 (overlap w/ GSE185062 cluster)
14. `(NAFLD OR NASH OR "fatty liver") AND (PBMC OR "peripheral blood mononuclear" OR leukocytes) AND "homo sapiens"[Organism]` → 104 (63 unique GSEs, all reviewed)

**eutils db=sra**: 15. `(NAFLD OR NASH OR MASLD) AND "whole blood" AND "RNA-Seq"[Strategy]` → 188 (25 esummarized → SRP471237; SRP136102 SLE). 16. `(NAFLD OR NASH) AND PBMC AND (biopsy OR histology OR fibrosis) AND "RNA-Seq"[Strategy]` → 0. 17. `PRJNA1089362` → 68 runs (3 esummarized + count).

**eutils db=bioproject**: 18. `(NAFLD/NASH/MASLD/"fatty liver") AND ("whole blood" OR PBMC OR leukocytes) AND (biopsy OR histology OR fibrosis)` → 4 (mouse ICAM-1; mouse hepatic-leukocyte protocol; Wilson liver+blood methylation; mouse β-cryptoxanthin). 19. `(NAFLD OR NASH OR MASLD OR "non-alcoholic fatty liver") AND "Homo sapiens"[Organism] AND "Transcriptome or Gene expression"[Data Type]` → 223 (50 esummarized + filtered).

**SOFT/API fetches**: GSE49541 (series+GSM), GSE246221 (series), GSE247467 (GSM), GSE185051 (GSM), GSE89632 (series+GSM), esummary db=gds batches (74 + 23 UIDs), esummary db=sra (29 UIDs), esummary db=bioproject (4 + 50 UIDs), BioStudies search ×3 (failed), ArrayExpress JSON ×2 (failed), Europe PMC ×4 (58 hits; 15 hits; 25 hits; 1 abstract).

**web_search** (autoglm provider): 20. `whole blood transcriptome NAFLD "fibrosis stage" GEO GSE dataset liver biopsy` (10; → GSE49541, GSE185051, GSE246221). 21. zenodo/figshare supplementary matrix (9; noise). 22. systematic review blood biomarkers NAFLD (9; reviews, no cohort enumerations). 23. CJK/Korean cohort query (8; provider noise — dead end). 24. negative-test "no public…lack of cohorts" (9; generic single-cohort limitations). 25. `PRJNA/ERP whole blood RNA-seq fibrosis fastq` (9; E-MTAB-6863, GSE202379 — both liver). 26. PBMC + NAS/activity score GSE (9; PMC12754493, GSE89632). 27. SuperSeries subseries query (10; noise).

**Totals**: 19 eutils esearch queries + ~15 API/SOFT fetches + 8 web searches ≥ 12 distinct searches ✔; all six mission angles attempted ✔.

**Tool failures recorded**: BioStudies API (`Study not found`), ArrayExpress JSON endpoint (non-JSON response ×2), one esummary JSON shape error (re-run with raw dump), web CJK query mangling.
