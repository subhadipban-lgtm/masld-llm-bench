# Standalone prompt: hunt a large bulk blood-transcriptome cohort for MASLD staging

Copy everything between the lines into a fresh agent session (one with web access,
`curl`, and Python). Run it to completion and report the final table back.

---

## Mission

Find one or more **public, bulk RNA-seq or microarray cohorts of whole blood / PBMC /
peripheral leukocytes** in MASLD (NAFLD/MASH) that are **large enough to test a
blood-based staging proxy** — target n ≥ 200 cases with liver histology, minimum
acceptable n ≥ 100. This cohort will become a frozen test family (`MB-86xx`
replacement) in the MASLD-LLM benchmark, so the bar is not "usable with effort" but
**"label join is verifiable with zero assumptions."**

## What the current program already has (do not re-report these as new)

| Accession | Modality | n | Why it is not enough |
|---|---|---|---|
| GSE267032 | bulk WBC RNA-seq | ~35 (21 graded) | too small |
| GSE267033 | scRNA WBC (same study) | 15 patients | not bulk; sibling of above |
| GSE135251 | liver biopsy bulk | 216 | liver, not blood |
| GSE130970 | liver biopsy bulk | 78 | liver, not blood |
| GSE167523 | liver bulk | 98 | liver, not blood |
| GSE126848 | liver bulk | 57 | liver; **also label-join BLOCKED** (numeric ids absent from SOFT) |
| GSE48452 | liver bulk | 73 | liver, not blood |

## Non-negotiable acceptance criteria

A candidate is **ACCEPTED** only if all six hold. Mark each explicitly.

1. **Specimen is blood**: whole blood, PBMC, or sorted leukocytes. Liver, adipose,
   stool, and serum *protein* panels do not count. Blood-derived organoids do not
   count.
2. **Bulk or pooled**: standard bulk RNA-seq, microarray, or full-length sequencing.
   Single-cell is out (different assay; no comparable prompt format).
3. **Human adults**, MASLD/NAFLD/MASH population, with **liver-histology labels**:
   fibrosis stage F0–F4, NAS/NAFLD activity score, or steatohepatitis grade.
   Self-reported disease or ICD codes alone are not enough.
4. **n ≥ 100 labeled samples** (≥ 200 strongly preferred). State exact labeled n.
5. **Expression matrix downloadable** without dbGaP/EGA controlled-access
   application (GEO supplementary, ArrayExpress, or SRA fastq that can be
   quantitated — say which).
6. **Label join verifiable from the deposit itself**: sample IDs in the matrix
   must match sample IDs/titles in the metadata/SOFT, or the paper's supplementary
   sample sheet must map them. **Column order is never evidence.**

If any criterion fails, report the candidate as REJECTED with the failing number.
Partial cohorts are still useful if you can say which criterion they miss.

## Search plan (be exhaustive, then verify)

1. **GEO** via NCBI eutils `esearch`/`esummary`, queries combining:
   `("whole blood" OR PBMC OR "peripheral blood" OR leukocyte) AND
   (NAFLD OR NASH OR MASLD OR MASH OR "fatty liver")` filtered to
   `gse[ETYP] AND Homo sapiens[ORGN]`. Sort by sample count; walk every hit.
   Also run the same query on `gds` to catch series records.
2. **ArrayExpress / BioStudies** (`https://www.ebi.ac.uk/biostudies/api/v1/search`)
   with the same terms.
3. **Literature-first**: search PubMed for blood transcriptome + NAFLD/NASH cohorts
   from 2015–2026 (include the big consortia and biobank-derived studies). For each
   candidate paper, find its accession. Papers sometimes deposit under unexpected
   titles, so search the accession back.
4. **Biobanks**: check whether any public processed blood expression + histology
   exists (e.g., GEO uploads from biobank sub-studies). Do not count controlled
   access.
5. **Follow citation trails** from the GEOS already known (GSE267032/33, GSE126848,
   GSE135251) — papers citing them sometimes describe a larger blood arm.

For each promising hit, fetch the SOFT/matrix headers and **verify the join
yourself**. Useful pattern:

```bash
# sample titles + characteristics
curl -s "https://ftp.ncbi.nlm.nih.gov/geo/series/GSExxxnnn/GSExxxxx/soft/GSExxxxx_family.soft.gz" \
  | gzip -dc | grep -E '^!Sample_(title|characteristics|description)'
# matrix header (first line)
curl -s "https://ftp.ncbi.nlm.nih.gov/geo/series/GSExxxnnn/GSExxxxx/suppl/<file>" \
  | gzip -dc | head -1
```

## Known trap that must not repeat

A previous candidate (GSE126848) had a counts matrix keyed by bare numeric patient
ids (e.g. `0869`) while the SOFT had only descriptive titles (`NAFL_1`, `Obese_9`).
Matching them by column order would have silently assigned fake labels. That join
was refused. **Apply the same rule here: if you cannot point to the exact field
that maps matrix columns to labeled samples, the candidate is REJECTED.**

## Deliverable (report back in exactly this shape)

1. **ACCEPTED** (or "none accepted") — accession, study title, specimen, assay,
   platform, labeled n, label type and distribution, download URLs, and the exact
   evidence for the label join (quote the matching field names and a few example
   aligned IDs).
2. **REJECTED table** — accession, one-line reason, which criterion failed.
3. **Near-misses** — cohorts that would qualify if one specific thing were obtained
   (e.g. "needs paper supplement table S2"), with what to request.
4. **Search log** — queries run, sources checked, date. This proves coverage, not
   just a lucky hit.
5. **Recommendation** — the single best candidate for a frozen `MB-86xx` blood
   family, and whether it supports 3-class severity, binary high-vs-low, and
   ordinal regression targets at n ≥ 100.

Keep the report factual. If the honest answer is "no such cohort exists publicly,"
say that and show the searches that support it — a documented negative is a valid
result and is more useful than a shaky join.
