# Plan — MASLD blood cohort search (MB-86xx frozen test family candidate)

Task ID dir: .cluster/masld-blood-cohort/
Research run dir: ~/.openclaw-autoclaw/workspace/research/masld-blood-cohort-20261019-1257
Delivery: DELIVERY/ (markdown report; docx skill not available in this environment — documented downgrade)

## Mission (from user file)
Find public bulk RNA-seq/microarray cohorts of whole blood/PBMC/peripheral leukocytes in MASLD/NAFLD with liver-histology labels, n ≥ 100 (≥ 200 preferred), open download, and a label join verifiable from the deposit itself. Deliver: ACCEPTED / REJECTED table / near-misses / search log / recommendation.

## Acceptance criteria (all 6 must hold)
1. Blood specimen (whole blood / PBMC / sorted leukocytes)
2. Bulk or pooled assay
3. Human adults, MASLD/NAFLD/MASH with liver histology labels (F0–F4 / NAS / SH grade)
4. n ≥ 100 labeled samples (≥ 200 preferred)
5. Matrix downloadable without dbGaP/EGA controlled access
6. Label join verifiable from deposit (sample IDs match metadata/SOFT or paper supplement; column order never evidence)

## Known-excluded accessions (do not re-report as new)
GSE267032, GSE267033, GSE135251, GSE130970, GSE167523, GSE126848, GSE48452

## Round 1 — parallel sweeps (4 subagents, same wave)
| # | Label | Role perspective | Output | Review item |
|---|---|---|---|---|
| 01 | GEO database sweep | supplementary material (eutils width sweep + SOFT triage) | subagent_01.md + geo_triage.tsv | Were all gse/gds hits walked? Blood-possible set complete? |
| 02 | ArrayExpress sweep | supplementary material (EBI BioStudies/AE-native accessions) | subagent_02.md + ae_triage.tsv | AE-native E-MTAB candidates checked at sample-table level? |
| 03 | Literature and citation-trail sweep | supplementary material (PubMed 2015–2026 + Europe PMC citation trails from known GSEs) | subagent_03.md + papers.tsv | Accession found for each candidate paper? Follow-up papers of known studies checked? |
| 04 | Alternative-framing sweep | adversarial/supplementary (bariatric/T2D cohorts, paired liver+blood, SRA-fastq-only, non-NAFLD indexing, benchmark signature papers) | subagent_04.md | Which framings could the other 3 miss? |

Dependency graph: 01–04 independent → feed Round 2 shortlist.

## Round 2 — verification + review (after Round 1)
| # | Label | Role | Output |
|---|---|---|---|
| 05 | Join verification agent(s) | numerical-definitions (download SOFT + matrix headers, test sample-ID join for every shortlisted accession, quote exact matching fields) | subagent_05.md (+ per-GSE evidence blocks) |
| 06 | Adversarial reviewer | adversarial review (criterion marks, join evidence, n counting, controlled-access traps) | subagent_06.md → review.md — DONE |

## Delivery item
DELIVERY/masld-blood-cohort-mb86xx-report.md — sections exactly: 1 ACCEPTED, 2 REJECTED table, 3 Near-misses, 4 Search log, 5 Recommendation. cluster_bypass_reason: none (sessions_spawn used).
