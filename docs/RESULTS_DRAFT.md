# MASLD-Bench Results Draft (v1, 2026-10-19)

Manuscript results-section skeleton. Every number is traceable to
`results/leaderboard.csv` (138 rows), `results/c2_significance.{csv,md}`
(paired McNemar/Wilcoxon, 9 frontier references), `results/c3a_gate*.json`
(grouped-CV classical gates), `results/kshot_17b.json`, and the RUNLOG.
Claims C1–C4 follow the frozen publication plan; the C2 fallback and C3
fallback were pre-specified and are the ones invoked — no post-hoc
claim-shifting.

---

## Overview paragraph (draft)

We introduce MASLD-Bench, a multi-domain omics benchmark for metabolic
dysfunction-associated steatotic liver disease comprising 15 frozen
prompt corpora (~110k items; MANIFEST v3-freeze-14): clinical liver
transcriptomics with histological endpoints, external staged cohorts
(including a newly-staged 216-biopsy cohort, GSE135251), DNAm, a
geometric-manifold compression layer, knowledge corpora (pathways,
drug–target), and four novel C3 task families (progression, blood-proxy
severity, liver→plasma proteomics, perturbation transfer). We evaluated
nine frontier API models, two classical ML families, and six compact
fine-tuned variants (Qwen3-0.6B/1.7B × v3/v5/v6 recipes) under a single
pre-registered decoding and scoring protocol. Three findings structure
the results: (i) frontier models cannot solve fixed-panel liver-omics
tasks beyond class priors; (ii) compact models trained on the benchmark
domains win the regression tasks outright but inherit the priors
elsewhere; and (iii) neither zero-shot nor trained-on exposure transfers
omics signal to held-out domains — while a logistic regression on the
identical prompts reads the strongest novel task at 0.833. Representation
format, not scale or training, is the binding constraint.

---

## C1 — Benchmark contribution (infrastructure)

- 15 frozen corpora, SHA-256 manifest, test-before-train freeze
  discipline; EPos-only frozen test after the Gubra label correction
  (freeze-6); every later corpus (85xx/86xx/87xx/88xx/12xx) frozen
  before its first evaluation.
- Novel domains added in this program: progression proxy (GSE185051,
  n=52), blood-proxy severity (GSE267032, n=20), liver→plasma masked-
  protein + platform (MSV000094959, n=206–216), PHH FFA perturbation
  (GSE247407, n=30, donor-grouped), DRUG-seq 40-compound train pool
  (E-MTAB-15601, n=1,196), staged train pool (GSE135251 n=216 + GSE167523
  n=98).
- Table S1: corpus manifest (from prompts/MANIFEST.json).

## C2 — Compact vs frontier (paired)

Pre-specified gate: paired CI separation on ≥2 domains; the fallback
(pivot claim weight to C3/C4) was invoked because the gate was NOT met.

Paired results (McNemar exact / Wilcoxon; n=929 identical items):
- MB-2005 fibrosis MAE is the one significant family of WINS:
  1.7B-v5 1.389 vs nemotron 2.024 (p=8.7e-12), deepseek 1.778
  (p=1.9e-6), gpt-4.1-mini 1.804 (p=8.3e-8); 1.7B-v6 improves to
  1.226 — better than every frontier model (best: meta-llama 1.529)
  and the ML ElasticNet (1.76). Caveat (pre-registered): driven by
  mean-anchored prediction; rho remains ≤0.12.
- MB-2001/2002/2003: ties or losses after pairing. The celebrated
  zero-shot pairwise 0.593 did not survive pairing (0.469, p=0.615) —
  reported as draw-luck in the supplement, not hidden.
- Full table: results/c2_significance.md (39 paired comparisons per
  candidate; 1.7B-v5: 27W/0L/12T vs the 9-reference bracket, driven by
  weak references; vs the strongest reference per task the picture is
  the one above).

## C3 — Novel task families (the honest ledger)

Classical gates (grouped CV, 2000 bootstraps, seed 20260929):

| Family | Task | logreg | majority | verdict |
|---|---|---|---|---|
| Progression (85xx) | 8501 / 8505 | 0.904= / MAE 0.20 | 0.904 / 0.10 | no signal (5/52 progressive) — negative control |
| Blood-proxy (86xx) | 8601/02/05 | 0.45 / 0.57 / 0.73 | 0.35/0.50/0.70 | underpowered (n=20), CIs span chance |
| Plasma (87xx) | 8701 | 1.000 | 0.350 | trivial BATCH separation (not clinical) |
| Plasma (87xx) | 8705 v2 | MAE 0.814 | 0.818 | no classical win (encoder target-blind caveat) |
| **Perturbation (88xx)** | **8801** | **0.833 [0.700,0.967]** | 0.500 | **genuine signal, donor-leakage blocked** |

LLM ledger on the same frozen tests:
- Zero-shot (v5): both sizes collapse to constants (1.7B all-"no"
  0.433; 0.6B all-"yes" 0.500 on 8801).
- **Trained-on (v6, this program's controlled experiment)**: after
  training on 40 compounds × ~8k HepG2 DRUG-seq prompts (+staged-liver
  pool), MB-8801 = 0.500 (1.7B) / 0.533 [0.367,0.700] (0.6B) — still at
  majority. Cross-model perturbation transfer does not occur at
  0.6–1.7B scale.
- k-shot ablation (BDH-CQ): demonstrations recover answer FORMAT
  (validity 0→0.77 at K=2) but not signal (all-K ≤ majority).

**C3 conclusion (per the frozen fallback):** the contribution is the
task families themselves plus a complete negative-control matrix —
no LLM evidence of omics signal transfer at compact scale.

## C4 — Representation-format regime split (the field-level lesson)

The convergent negative: across 6 compact variants, 3 training regimes,
5 test families, and K-shot conditioning, compact LLMs read omics
prompts at class-prior level wherever a linear baseline exceeds chance —
and the one novel task with strong classical signal (8801: 0.833) shows
LLM 0.500 both zero-shot AND trained-on. Conversely, on domains where
prompt text encodes the answer structurally (platform id: 0.398>v5
0.257; masked-value formats: validity 1.0), trained models learn
immediately. Structural readability, not statistical signal, is what
SFT conveys. Classical ML and LLMs occupy disjoint regimes on
fixed-panel omics — mirroring and extending the LongevityBench
observation into trained-on and cross-model transfer settings.

## Negative results & warts (all pre-committed in RUNLOG)

1. 0.6B-v6 degraded (empty plasma emissions, 2002 0.190 vs v5 0.202;
   MB-2006 digit-loop in 1.7B-v6, MAE 6.1e5) — mixture dilution bites
   the small model.
2. MB-8501's apparent v6 gain (0.846) is the stable PRIOR (majority
   0.904 still higher).
3. 8705 freeze-10 was degenerate (all golds saturated); rebuilt as
   masked-protein z (freeze-11) with the per-protein-z correction
   (per-sample z makes the answer arithmetic).
4. Gubra fake-label correction (freeze-6) and the unpaired-pairwise
   draw-luck correction are reported, not buried.

## Figure plan (from existing artifacts)

- F2: leaderboard heat/dot plot — models × MB-20xx tasks (leaderboard.csv).
- F3: paired C2 forest — MB-2005 MAE w/ CIs vs 9 references
  (c2_significance.csv).
- F5: C3 matrix — 5 families × {logreg, majority, 0.6B-v5/zs, 1.7B-v5/zs,
  0.6B-v6, 1.7B-v6} (leaderboard.csv + gates).
- S-kshot: demonstration-conditioning table (kshot_17b.json).
- S-geometry: raw-vs-geometry 2×2 + k-shot variants (v3_geo_ablation,
  MB-40xx rows).

## Limitations (draft)

Frozen test families are small (20–216 items); CIs are correspondingly
wide and several gates are underpowered by construction (pre-registered
as such). The progression family is a cross-sectional stage proxy, not
true paired-biopsy progression. The plasma platform task measures batch
separation. Frontier coverage is 9 references with partial archives for
two. The transfer experiment trains on a different cell type (HepG2)
than the test (primary hepatocytes) — negative transfer is specific to
that (biologically meaningful) axis, not to identical-domain learning,
which the format-learning results (8701, validity metrics) show does
occur.
