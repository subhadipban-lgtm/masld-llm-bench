# Subagent 01 — Systematic GEO width walk (bulk blood transcriptomes in MASLD/NAFLD with liver-histology labels)

Date: 2026-10-19 | Agent: geo-sweep-v2 (replacement, width walk of NCBI GEO db=gds)

## Conclusion

**No new qualifying cohort found.** The union of 6 query variants (509 unique GEO UIDs → **79 unique GSE accessions** after dedupe, 0 GDS-only records) contains **zero bulk whole-blood/PBMC/peripheral-leukocyte transcriptome cohorts in MASLD/NAFLD with per-sample liver-histology labels (F0–F4 / NAS / Brunt / Kleiner) at n ≥ 100**. The 8 known-excluded series (GSE267032/33/195, GSE135251, GSE130970, GSE167523, GSE126848, GSE48452) remain the only deposits matching the mission profile; 3 of them surfaced in this sweep and were marked excluded-known.

Closest near-misses (all fail ≥1 hard criterion):
1. **GSE55645** — n=49 **blood lymphocytes** with `Stage: NASH` / `Stage: Simple steatosis` + NAFLD-vs-Control channel labels. Best blood+histology-label match in GEO, **but assay is a genome-variation (SNP/CNV) array, not a transcriptome** — fails "bulk transcriptome" unless the project relaxes assay type. Labels verifiable from GSM characteristics.
2. **GSE117623** — n=137 peripheral blood (circulating epithelial cells + sorted B/T/NK/mono/granulocyte fractions), chronic liver disease + HCC; diagnosis field is only `Chronic liver disease patient` / `Hepatocellcular carcinoma patient` — **no MASLD focus, no fibrosis/NAS staging**.
3. **GSE73634** — 48 GSMs / 24 participants, source `paired blood biopsy`, `disease state: advanced liver fibrosis` (simtuzumab trial) — whole blood + biopsy pairing exists, **but etiology is HCV/HIV, not MASLD**, and stage labels are not in GSM characteristics (series/paper level only).
4. **GSE326605** — peripheral NK cells with `disease state: Liver fibrosis F4 score` — has an F4 label but n=4 and FACS-sorted subset.
5. GSE247467 (known near-miss, peripheral neutrophils MASH, n=12), GSE325645 (PBMC NK, CHB vs CHB-MASLD, n=7), GSE179886 (PBMC, n=2), GSE228087 (PBMC→macrophage differentiation, 5 donors), GSE185062/GSE33857 (serum/exosomal miRNA) — all confirm the "small-n blood subsets / non-cellular" pattern.

## Evidence

### Search log (esearch db=gds, retmax=300, Homo sapiens; 2026-10-19)

| Query | Terms | Hits |
|---|---|---|
| q1 (base, tested) | blood terms ∧ (NAFLD∨NASH∨MASLD∨MASH∨"fatty liver") ∧ gse[ETYP] | 59 |
| q2 (variant a) | q1 ∧ +"hepatic steatosis"∨steatosis | 64 |
| q3 (variant b) | blood terms ∧ bariatric ∧ (liver∨biopsy) | 39 |
| q4 (variant c) | blood terms ∧ diabetes ∧ NAFLD-ish | 3 |
| q5 (variant d) | ("whole blood"∨"peripheral blood") ∧ "liver biopsy" ∧ human (no ETYP) | 182 |
| q6 (variant e) | variant a without gse[ETYP] (catch GDS) | 428 |
| Union | 509 UIDs → esummary (3 batched calls) | **79 unique GSE, 0 GDS-only** |

SOFT-fetch budget: 15/15 used (GSM brief view, `targ=gsm&form=text&view=brief`), all decisive.

### Post-SOFT per-candidate notes (exact characteristic fields)

- **GSE55645** (49 GSMs): `!Sample_source_name_ch1 = NAFLD` / `ch2 = Control`; `!Sample_characteristics_ch1 = Stage: NASH` / `Stage: Simple steatosis`; `blood: lymphocytes`; gender+age present. gdstype "Genome variation profiling" → CNV/SNP array. Verdict: ambiguous (assay mismatch).
- **GSE117623** (137 GSMs): source `Peripheral blood`; cell types B/Cytotoxic T/Helper T/Monocytes/NK/Granulocytes/Circulating epithelial cells; `diagnosis: Chronic liver disease patient | Hepatocellcular carcinoma patient`. **No fibrosis/NAS/steatosis field** (grep for fibros|brunt|nas|stage|steat|etiolog|hbv|hcv over characteristics returned empty). Verdict: blood-no-histology.
- **GSE73634** (48 GSMs): source `paired blood biopsy PRE treatment pair and rep N`; `disease state: advanced liver fibrosis`; 24 participants; simtuzumab in HIV/HCV. Verdict: ambiguous (wrong etiology, staging not per-sample).
- **GSE326605** (4 GSMs): `cell type: Peripheral NK cells`, `disease state: Liver fibrosis F4 score`, `tissue: Blood`, FACS NTCP±. Verdict: ambiguous (tiny, sorted subset).
- **GSE247467** (12 GSMs): `tissue: Peripheral blood`, `cell type: Neutrophil`, `disease state: MASH | healthy`. No grade field. Verdict: blood-no-histology (known near-miss confirmed).
- **GSE325645** (7 GSMs): `tissue: peripheral blood`, NK, `disease state: CHB | CHB-MASLD`. Verdict: blood-no-histology.
- **GSE179886** (2 GSMs): `PBMC`, FLV vs Healthy only. Verdict: blood-no-histology.
- **GSE204962** (12): `monocyte-derived macrophages`, MBOAT7 siRNA vs scramble — in vitro. **GSE228087** (16): `blood (PBMC)` → M-CSF/LPS/IL4/IL13 differentiation, 5 donor ids — in vitro. **GSE160200** (20): M2-like macrophages + HoxLDL/MoxLDL — in vitro. **GSE235079** (3): `tissue: liver`, CD45 cells. **GSE151353** (8): `liver biopsy sample`, sASH. **GSE169446** (2): pooled sorted DCs. **GSE270488** (18): tissue liver×16 vs pbmc×2. **GSE33857** (100): serum Exosome miRNA. All verdict: not-blood.

### Triage distribution (79 rows, geo_triage.tsv)
not-blood 62 | ambiguous 10 | blood-no-histology 4 | excluded-known 3. No row reached "blood-histology-candidate".

## Analysis

- The base query is already near-saturated: q1's 59 hits are a near-subset of the wider variants; widening to steatosis terms (+5), bariatric (+), no-ETYP (q5/q6) surfaced mostly GDS-adjacent/super-series noise, and esummary dedupe collapsed everything to 79 real series — none new and qualifying.
- GEO's MASLD blood transcriptome space is dominated by: (i) liver-tissue single-cell/bulk series matching on "blood" only via summary text, (ii) in-vitro monocyte/macrophage experiments from few donors, (iii) circulating miRNA (non-cellular), (iv) small sorted-subset studies (NK/neutrophil/DC, n≤12). This mirrors the ArrayExpress agent's empty result — the negative is now cross-platform.
- The only per-sample histology-labeled blood deposit found (GSE55645) is a CNV array — if the consortium's inclusion criteria can stretch to "blood-derived DNA assay with histology labels", it is the sole n≥30 option; otherwise GEO has nothing beyond the known 8.

## Gaps and risks

- 7 rows remain verdict=ambiguous by rule fallback: GSE204963/204964/204965 (MBOAT7 SuperSeries siblings of the in-vitro GSE204962), GSE180241 (sibling of GSE179886 n=2 PBMC), GSE300514 (IL-4 scaffold biomaterials — likely mouse), plus two siblings already covered. All low-priority; none expected to qualify.
- Esummary samplecount was used for n; a few series (e.g. GSE73634) count GSMs ≈ 2× participants (PRE/POST pairs) — flagged in notes.
- esearch retmax=300 caps q5/q6 (182/428 hits) — q6's tail beyond 300 was not walked; risk is low (q6 hits are GDS-heavy dupes of q1/q2) but a full pagination pass would cost ~2 extra calls.
- Join verification (label join from deposit files) not performed here — next-round task per mission. GSE55645's labels are inside GSM characteristics, so a join should be trivial if the assay criterion is relaxed.

## Suggested final-report placement

- "Systematic sweep" section: GEO width walk negative result — 6 queries, 79 series triaged, 0 new qualifiers; cross-confirms ArrayExpress emptiness.
- Conditional-candidates table: GSE55645 (relax-assay option), GSE117623 (n≥100 blood but no staging/MASLD), GSE73634 (blood+biopsy pairing, HCV/HIV etiology), GSE326605 (F4 label, n=4).
- Strengthens the pivot recommendation toward the known 8 deposits (esp. GSE267032 bulk WBC MAFLD/MASH) and/or multi-cohort meta-design.

Files: `geo_triage.tsv` (79 rows, incremental-safe, header included), this report. Copies placed in `research/masld-blood-cohort-20261019-1257/`.
