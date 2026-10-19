# Brief — MASLD blood cohort verification report (MB-86xx)

- **Title**: Public bulk blood transcriptome cohorts in MASLD with liver-histology labels — search and verification report for the MB-86xx frozen blood family
- **Audience**: MASLD-LLM benchmark maintainers deciding whether a public cohort can replace MB-86xx
- **Purpose**: Documented search + field-level verification of candidate cohorts against 6 non-negotiable acceptance criteria; the honest answer is a documented negative
- **Executive summary**: 8 worker agents swept GEO (79 GSEs, 6 query variants + 4 reviewer spaces), ArrayExpress/BioStudies (16 queries, 19 dataset accessions), SRA/BioProject/biobank framings (~27 queries), and the 2015–2026 literature with partial citation trails. Zero new qualifying cohorts. Field-level verification of 7 near-misses (SOFT/BioSample/BioStudies fetches) confirmed every exclusion. Best anchor remains GSE267032 (n=35 bulk WBC, join verifiable) — fails the n ≥ 100 floor by ~3×. Recommendation: do not freeze a blood MB-86xx from public data today; pursue S-BSST1614 phenotype table and GRIPonMASH; re-sweep in 6–12 months.
- **Structure**: 5 numbered sections exactly as the mission requires (ACCEPTED / REJECTED table / Near-misses / Search log / Recommendation) + method preamble + residual risks
- **Key findings (source-backed)**: negative result cross-confirmed by ≥2 independent agents on GEO and EBI sides; GSE267032 n-count verified at GSM level (14 control + 21 graded); GSE55645 is aCGH not transcriptome; S-BSST1614 deposit has zero sample metadata (join impossible); PRJNA1089362 BioSample attributes carry no disease fields
- **Risks/assumptions**: forward-citation walk partial (literature agent failed twice); ArrayExpress-native API retired (residual AE-only deposits structurally uncovered); non-English/local-code SRA deposits can evade label-join checks; all endpoint statuses as of 2026-10-19
- **Format**: markdown (docx skill unavailable in this environment — documented downgrade; mission shape is content-structural)
- **Tone**: factual, no speculation; every verdict traceable to a fetched URL
