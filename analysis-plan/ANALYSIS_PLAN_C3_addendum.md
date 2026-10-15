# MASLD-Bench Analysis Plan — C3 Addendum — FROZEN 2026-10-15

Dated addendum to ANALYSIS_PLAN_v1.md (frozen 2026-09-29). The v1 frozen
test set (MB-20xx, EPos-only) is UNCHANGED and remains the only evaluation
surface for C1/C2/C4 claims. This addendum pre-specifies the C3 novel-task
contrasts BEFORE any C3 corpus is built or evaluated, per the program's
freeze discipline. C2 paired outcome (2026-10-15: pairwise does not survive
McNemar pairing; one significant win on MB-2005 MAE) already triggered the
pre-planned claim-weight pivot to C3/C4 — this addendum is that pivot's
statistical contract.

## 1. New task families (all TRAIN-side or NEW-frozen-test; EPoS untouched)

| Family | Source | Split | Tasks |
|---|---|---|---|
| MB-86xx blood-proxy | GSE267032 (WBC, 21 patients) | new frozen test (built once, never trained on) | 8601 severity 3-class (low/med/high), 8602 binary low-vs-high, 8605 ordinal score regression |
| MB-96xx axis-reasoning | existing train corpora (Kamzolas/external pool) | train-side only (eval via cross-val on train or held-out slice of TRAIN cohorts, never EPoS) | 9601 ferroptosis-stress binary, 9602 senescence-burden class, 9605 FSS-vs-stage regression |
| MB-97xx perturbation transfer | GSE262457 / GSE273523 (mouse, old-vs-young ± Fer1; Smo-KO) | train-side | 9701 direction-of-change, 9702 reversion prediction |
| MB-98xx Duke cohort | GSE213623-derived counts (if present) or GSE167523 | TRAIN-side augmentation | staging tasks; ALSO feeds geometry rebuild (Track D, n→~765) |

## 2. Mechanistic score definitions (FROZEN before computation)

- **FSS (ferroptosis stress score)**: 9 FerrDb V2 genes per Du et al. Nat
  Aging 2024 — FTH1, GPX4, CHAC1, HSPB1, NFE2L2, PTGS2, SLC40A1, TF, TFRC —
  z-scored per sample, summed with literature directions encoded ONLY for
  reporting (ACSL4/SLC7A11/PTGS2/FSP1 up; GPX4/GCH1 down); the TASK uses the
  neutral module activity, not the directed score, to avoid baking the
  hypothesis into the label.
- **AGING (senescence burden)**: CDKN1A, CDKN2A, GLB1, MKI67 (inverse),
  IL6, CCL2, CXCL8, SERPINE1.
- **IRON**: TF, TFRC, FTH1, FTL, SLC40A1, HAMP.
- All scores: per-sample label-free standardisation first (log1p if
  non-negative, then z-score) — the program-wide rule.

## 3. Pre-specified contrasts

- **C3a (novelty)**: on MB-86xx (new frozen test), do compact models or ML
  baselines beat chance/majority? Gate: ANY model family with CI excluding
  chance on ANY 86xx task → C3 claim lives; else fallback framing.
- **C3b (axis grounding)**: do FSS/AGING module activities predict severity
  better than size-matched random gene panels of the same dimension?
  Permutation null: 1000 random panels, same n genes, same pipeline. This is
  the falsifiable test of "the axis carries signal", not just "genes carry
  signal".
- **C3c (transfer)**: MB-97xx — can models predict Fer1 reversion direction
  above 50%? Any honest model is expected near chance unless it read the
  papers; contamination therefore EXPECTED for frontier models and must be
  reported as such, not hidden.
- **C2 paired (already executed)**: recorded verdict stands — 1 significant
  win (MB-2005), 2 losses, 2 ties vs nemotron; C2 claim weight reduced.

## 4. Statistics

- Same metrics/validity/ranking as v1 §3-§8 (accuracy/MAE + bootstrap CIs,
  McNemar where paired). New: permutation nulls for C3b (1000 resamples,
  seed 20260929); one-sided tests ONLY where direction was pre-specified
  (FSS↑ with stage per Du et al.).
- Multiple testing: Holm across the 3 contrast families per model class.
- Power honesty: MB-86xx n=21 → wide CIs are expected; report exact CIs, no
  post-hoc pooling.

## 5. Contamination controls

- MB-97xx mouse-perturbation items are literature-derived: frontier models
  may have memorised Du et al. Any above-chance frontier performance on
  97xx is REPORTED AS POSSIBLE CONTAMINATION (matches v1 §10 philosophy).
- MB-86xx (GSE267032, public Apr 2025): same treatment as other post-2024
  public cohorts — note in limitations.
- Duke cohort (GSE213623) is train-side; no test contamination possible.

## 6. What would falsify the C3 claims

- C3a fails on all 86xx tasks for every model → no novelty claim; paper
  falls back to benchmark+landscape framing.
- C3b permutation null covers the FSS/AGING effect → axis framing drops to
  discussion, not results.
- C3c: everything (including frontier) at chance → perturbation family
  becomes a negative-result supplement table (consistent with program
  culture of banking honest nulls).

## 7. Order of operations (locked)

1. Freeze this addendum (done at commit).
2. Build MB-86xx (one shot, manifest bump, checksums) — THEN it is frozen.
3. MB-96xx/97xx builders on train side; Duke/167523 counts for Track D.
4. Baselines → compact eval → (only if C3a clears) frontier bracket.
