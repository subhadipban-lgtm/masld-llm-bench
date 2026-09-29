# MASLD-Bench Analysis Plan v1 — FROZEN 2026-09-29

This document pre-specifies the evaluation protocol BEFORE any frontier-LLM
API call is made (per the Cell publication plan, W2 gate). Any deviation must
be recorded in RUNLOG.md with justification.

## 1. Frozen evaluation set

- Test items: `prompts/MB-20xx_liver_test.jsonl.gz` (EPos + Gubra, 13,273
  prompts; 843 single-profile + 12,430 pairwise), checksum `3074d7b007465a82`
  (MANIFEST v3-freeze-3). This file is never regenerated.
- Frontier evaluation subsample: first 300 prompts per task, stratified by
  task, sampled with seed 20260929. Pairwise task capped at 300 (not 12,430).

## 2. Primary contrasts (the two the paper claims)

- C2 (compact vs frontier): best MASLD-LLM vs best frontier model on
  equal-domain mean rank over tasks, with prompt-level bootstrap 95% CI
  (10,000 resamples).
- C4 (regime split): ML baseline vs best LLM on fixed-panel tasks (gene
  features constant across prompts within a task) vs variable-feature tasks.

## 3. Metrics per task format

- Binary: accuracy + F1; report response validity separately.
- Multiclass: accuracy (macro-F1 secondary).
- Regression: MAE + Spearman rho.
- Pairwise: concordance (accuracy on A/B).

## 4. Ranking scheme

Equal-domain mean rank: rank models per task, average within domain, then
across domains with equal weight (paper's scheme). Sensitivity check:
all-task flat average (their Table S5 analogue).

## 5. Model roster (frontier bracket, via OpenRouter)

Minimum viable roster (n>=6): deepseek/deepseek-chat, google/gemini-2.5-pro,
openai/gpt-4.1-mini, openai/gpt-4.1, anthropic/claude-sonnet-4.5,
x-ai/grok-4-fast. Extend to 16 when budget allows; every model's responses
are archived to results/frontier_runs/<model>__<file>.jsonl.gz with the model
version string recorded.

## 6. Decoding protocol

Zero-shot, single pass, temperature 0.0, top_p 1.0, max 1500 tokens (the
paper's protocol). No few-shot, no retrieval, no tools.

## 7. Validity handling

Invalid/unparseable answers are counted in the validity rate and scored as
incorrect for headline metrics (invalid-as-error); invalid-excluded accuracy
reported as sensitivity.

## 8. Statistics

- Bootstrap 95% CIs on every per-task metric (prompt-level resampling).
- Post-hoc winner-vs-runner-up: McNemar exact (classification/pairwise) or
  Wilcoxon signed-rank (regression), Holm-corrected across tasks.
- No Friedman critical-difference claim with <10 models; note this explicitly.

## 9. Current ML baselines (already run, session 2)

Kamzolas-only (feature-matched) gene-feature baselines on the frozen test:
binary EN 0.560 / HGB 0.564 vs majority 0.582; multiclass EN 0.231 vs
majority 0.200; regression EN rho 0.250, MAE 2.55 vs median 1.70. These are
weak baselines — the honest starting bracket. Cross-platform feature mapping
(probe->gene symbol) is scheduled for freeze-4 and will re-train these.

## 10. Contamination controls

Named-gene vs masked-gene variant pair (MB-7001 named built; MB-7002 masked
to follow). Report the delta for knowledge tasks.

## 11. What would falsify the headline claims

- C2 fails if the best compact model's CI overlaps frontier's on >=2 domains.
- C4 fails if LLMs beat ML on fixed-panel tasks or lose on variable-feature
  tasks (interaction direction reversed).
- In either case: pivot claim weight to C3 (novel tasks) per the publication
  plan; do not re-run with different prompts.
