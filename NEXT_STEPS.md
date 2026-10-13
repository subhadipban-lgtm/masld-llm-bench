# MASLD-LLM · How to go ahead — triage & path (2026-10-13)

Written after a full state audit. Short version: the program has more than
enough for C1/C2/C4; the paper-critical gap is **C3 (novel tasks, F5)** and
one **credibility fix** (the compact-model eval draw barely overlaps the
frontier's, so the headline C2 test is currently unpaired).

## 0. Live blockers found in the audit

| # | Finding | Impact | Fix |
|---|---|---|---|
| B1 | `~/masld-revision` (source omics for Kamzolas/EPoS/Fujiwara) is **not on disk** | Cannot rebuild frozen corpora or the geometric layer from scratch | Locate/restore the dir (author's revision workspace), or re-pull from GEO |
| B2 | Compact eval draw ∩ frontier draw = **10/300** on MB-2003 | C2 headline is **unpaired**; cannot run McNemar | `scripts/eval_paired_06b.py` re-runs 0.6B-v3 on the frontier's exact 929 items -> paired |
| B3 | MPS (Apple GPU) **deadlocks** at `.to("mps")` weight transfer | All local fp16 inference falls back to CPU (slow, but works) | Reboot restores MPS; or keep CPU fallback (`PAIRED_DEVICE=cpu`) |
| B4 | Frontier bracket only 4 usable models (deepseek, nemotron full; gemini, qwen partial) | C2 needs >=6 for a real bracket; analysis plan says no Friedman <10 | Top up OpenRouter (~$10-20) or add free-tagged models |
| B5 | Vina not installed; no docking tooling | Drug arm screen not runnable | `brew install vina` or Colab; or defer drug arm |
| B6 | GSE267032 / MSV000094959 (F5 blood-proxy/plasma sources) not downloaded | C3 F5 unbuildable until data lands | Download on Colab/laptop |

## 1. What is actually done and defensible (no more work needed)

- **C1 infrastructure**: 100k+ prompts frozen + checksummed, MANIFEST v3-freeze-7,
  test frozen before any new train data (the reviewer anchor). 17 corpora.
- **W2 baselines**: ML baselines + 4-model frontier bracket + leaderboard with
  bootstrap CIs.
- **W3 ladder**: 0.6B-v3 (LoRA) and 1.7B evaluated, honest verdicts.
- **Ablations** (5 legs): geometry v1 fail / v2 win, geometry stability +/-0.15,
  raw-vs-geometry zero-shot matrix, 1.7B geometry collapse, k-shot BDH-CQ.
  Every leg is committed with a runlog entry.

## 2. The paper-critical gap: C3 / F5 (novel tasks) — the Cell headline

The publication plan says C3 is the *headline novelty over LongevityBench*.
F5 = four panels, one per novel family:
1. progression from paired biopsies
2. blood-proxy severity (GSE267032)
3. liver->plasma bridging (MSV000094959)
4. drug-perturbation transfer (PHH panels)

**None of these corpora are built and only some source data is on disk.**
Without C3 the paper is "benchmark + evaluation landscape" (weaker journal).
-> **This is the highest-priority build.**

## 3. Recommended sequencing

### Track A — local, no credentials (start now)
- A1 **(running)** paired 0.6B eval -> makes C2 a real paired test.
- A2 Write the C2 paired-scoring script (McNemar/Wilcoxon vs frontier), feed the
  paired archive -> significance table.
- A3 Draft the results section + regenerate F2/F3 from existing leaderboards.

### Track B — needs data (C3 build; the paper's reason to exist)
- B1 Acquire F5 sources: GSE267032 (blood-proxy), MSV000094959 (plasma),
  paired-biopsy progression data, PHH perturbation panels (E-MTAB series).
- B2 Build MB-85xx (progression), MB-86xx (blood-proxy), MB-87xx (liver->plasma),
  MB-88xx (perturbation transfer) with train/test discipline + manifest.
- B3 ML baselines + compact-model eval on the new families (the C3 test).
- B4 Freeze an analysis-plan v2 (or dated addendum) for the C3 contrasts.

### Track C — needs credentials/compute
- C1 Top up OpenRouter -> complete the frontier bracket to >=6 models.
- C2 If C3 baselines clear: consider the 9B two-stage QLoRA (Colab Pro+).
- C3 (optional) Vina screen for the drug arm + MB-95xx tasks.

### Track D — the one laptop-quality fix if B1 is restored
- D1 Rebuild the geometric layer with the external cohorts in the train-side
  graph (n 135 -> ~466) -> re-test the +/-0.15 stability. Directly strengthens C4.

## 4. Go/no-go gates (from the publication plan)

- C2 gate: best compact vs frontier, paired, Holms-corrected. If the paired CI
  overlaps frontier on >=2 domains -> pivot claim weight to C3/C4 (planned fallback).
- C3 gate: compact models + ML must beat chance on the novel tasks. If not ->
  fallback framing.
- 9B gate: only spend Pro+ if 1.7B is within CI of frontier on >=1 domain.

## 5. Immediate decision needed from the human

1. **`~/masld-revision`**: where is it? (or can we re-pull the source cohorts?)
2. **C3 data pull**: can I download GSE267032 / MSV000094959 / the PHH panels now
   (on this laptop, if there's room), or do you want that on Colab?
3. **OpenRouter top-up (~$10-20)**: yes/no — decides whether the frontier bracket
   grows to 6+.
4. **Scope call**: do we lean into C3 (new data, higher ceiling, more work) or
   consolidate the existing material into a submission now (lower ceiling, faster)?
