# Review record — MASLD blood cohort search (S4)

## Confidence classification of key findings

**High confidence (≥2 independent agents or direct deposit fetch + reviewer re-check):**
- No public bulk blood (WB/PBMC/leukocyte) transcriptome cohort in MASLD/NAFLD with per-sample liver-histology labels at n ≥ 100 exists as of 2026-10-19. Sources: subagent_01 (79 GSEs walked, 6 query variants, 15 SOFT checks), subagent_02 (19 E-accessions, all triaged), subagent_04 (~27 queries, 6 framings), subagent_06 (independent re-sweep of MASLD/MASH-nomenclature, PAXgene/Tempus, Europe PMC full-text spaces — zero new qualifiers), subagent_05 (field-level verification of 7 near-misses — all confirm exclusion).
- GSE267032 = exactly 35 bulk WBC GSMs: 14 control + 21 graded MAFLD/MASH (1_low=8, 2_medium=6, 3_high=7); labels joinable from per-GSM characteristics (`disease`, `condition`, `celltype: wbc`, `assaytype: bulk`). Verified independently by subagent_06 (Vector 4) and consistent with the user's own count.
- GSE267195 is a 3-part SuperSeries: GSE267031 (bulk liver, n=18, NAS-stratified) + GSE267032 (bulk WBC n=35) + GSE267033 (scRNA n=15). Found by subagent_06; corrects all sweep documents.
- GSE55645 is aCGH/genomic DNA (GPL9777, `Sample_molecule_ch1 = genomic DNA`, `Series_type = Genome variation profiling by genome tiling array`), n=49 blood lymphocytes, Stage labels 39 NASH / 10 simple steatosis; join verifiable per-GSM. Verified by subagent_01 (SOFT) and subagent_05 (full 49-GSM dump).
- S-BSST1614 (plasma cfRNA, PMID 42173964): deposit contains ONLY two count matrices keyed by anonymous `RNA015584...`-style IDs, zero sample-level metadata — label join impossible from deposit; specimen is plasma, not cells. Verified by subagent_05 with direct file range-fetch.
- PRJNA1089362 (Thai PBMC n=68): complete BioSample attribute set = {isolate, age, biomaterial_provider, collection_date, geo_loc_name, sex(restricted), tissue=PBMC1..68, BioSampleModel}; no disease/histology attributes. Verified by subagent_04 (SRA esummary) and subagent_05 (SRA efetch + BioSample efetch).

**Medium confidence (single authoritative source):**
- ArrayExpress-native JSON API retired (HTTP 302 → BioStudies HTML) as of 2026-10-19; BioStudies `type=arrayexpress` filter broken; only EBI mirror of known set is E-GEOD-48452 (subagent_02, with endpoint statuses quoted).
- PRJNA1305173 does not resolve in NCBI BioProject/SRA/BioSample or ENA (count 0 everywhere) — likely mistyped accession in the original paper-lead table (subagent_05). The paper (PMID 41479518) itself is real (fetched round 1), so its deposit must be re-derived from the full text before anyone relies on this row.
- Literature citation-trail coverage is PARTIAL: the literature agent failed twice (round 1 failed before writing; round 1b timed out after research but before writing subagent_03.md). Surviving evidence: papers.tsv (14 rows, incl. anchor-paper 10-citation check "no larger blood follow-up"). Mitigation: subagent_06 independently walked Europe PMC full-text (3 queries: 136 / 929 / 103 hits, top-100 each) with no missed ≥100 blood cohort. Residual gap: systematic forward-citation walks of GSE126848/GSE135251/GSE48452 source papers were not completed.

**Low confidence:**
- PMID 41751802 (Mondal 2026, whole-blood miRNA/ncRNA pilot, African Americans with MASLD): abstract-level only; accession-unresolved. Watchlist item.
- PMID 38496899 (PBMC mitochondrial fusion × liver fibrosis): accession-unresolved, never chased (budget).

**Conflicts and their resolution:**
- papers.tsv anchor row says "22 patients liver-RNA-seq" vs GSE267031 deposit = 18 GSMs. UNRESOLVED discrepancy (may include scRNA/FACS subset or undeposited samples). Report states both numbers with the caveat; does not assert either as final. Flagged by subagent_06 (correction #2).
- GSE247467 metadata quirk: `Normal_1` carries `disease state: MASH` (8 MASH + 4 healthy by characteristics vs 7 MASH + 5 Normal by title) — internal GEO inconsistency, does not affect verdict (subagent_05).
- subagent_04 said BioStudies/AE APIs "failed"; subagent_02 found the BioStudies search API working (only AE-native + type param broken). Resolution: both partially right; recorded precisely in the search log. Adversarial reviewer's coverage attack (Vector 1) was run through the working BioStudies route, closing the gap.

## Required corrections applied to the final report
1. GSE267031 added (liver subseries of anchor superseries).
2. Anchor liver-arm n discrepancy (22 vs 18) stated as unresolved.
3. GSE240729 + GSE249997 added to rejected/anti-confusion entries (liver, histology-labeled).
4. PMID 41751802 added to watchlist.
5. PRJNA1305173 downgraded to "unverified deposit" per subagent_05.
6. Literature-track coverage gap stated explicitly in the search log.

## Verdict
The negative result stands: **"none accepted"** is the honest deliverable. Best available anchor remains GSE267032 (n=35, verifiable join) — below the mission's n ≥ 100 bar.
