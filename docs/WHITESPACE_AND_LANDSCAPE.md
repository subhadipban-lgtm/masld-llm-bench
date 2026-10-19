# MASLD-LLM: whitespace & competitive landscape (2026-10-19)

Purpose: decide whether the 9B run (v7, Qwen3-8B QLoRA on A100) adds
publishable value before spending the compute. All claims traced to sources
listed at the end; internal numbers from results/leaderboard.csv (freeze-16,
12-reference bracket) and the RUNLOG.

---

## 1. Competitive landscape (as of October 2026)

### The anchor competitor — LongevityBench (Cell, 2026; Zhavoronkov/Insilico)

The field-defining work. 17 tasks across ~6 biodata domains: NHANES clinical
survival, GTEx transcriptomic aging, TCGA cancer survival (RNA-seq), GEO
DNAm aging, Olink proteomics, SynergyAge genetics, OpenGenes text. 15–18
frontier systems evaluated (o3 best mean rank 4.65; Gemini 3 Pro first on
6/17). Headline: a released ~9B fine-tuned "Longevity-LLM" beat every
frontier system on aging/omics tasks at ~20x cheaper inference, and Insilico
open-sourced the toolkit as a Cell cover study.

What they do NOT have (verified against the bioRxiv full text):
- **No disease-specific tasks** — only cancer survival (TCGA) approaches
  disease, with progression-free survival as the endpoint.
- **No histology endpoints anywhere** — no biopsy-graded fibrosis, no NAS,
  no steatohepatitis grading. Their endpoints are death, age, lifespan,
  survival time.
- **No paired significance testing** — evaluation is mean-rank across
  tasks; no McNemar/Wilcoxon on identical items, no CI-separated head-to-heads.
- **No training-exposure negatives** — the SFT-success story is not stress-
  tested with held-out-domain transfer failures.
- **No label-join integrity discipline** — nothing comparable to SHA
  manifests, test-before-train freezes, or documented label corrections.

### The only MASLD x LLM work — "Fibro-GPT" (Njei et al., 2026)

GPT-4/GPT-3.5 predicting advanced fibrosis in MASLD, AUROC 0.91/0.90.
Critically: **inputs are seven routine lab values** (age, BMI, AST, ALT,
platelets, eGFR, HbA1c) rendered as text — **no transcriptomics of any
kind**. Fibrosis labels are a FIB-4/NFS+VCTE *surrogate*, not histology;
n=162; thresholds selected on the same cohort that produced the reported
metrics. No fine-tuning, no benchmark suite, one binary task.

This is complementary, not competing: it shows LLMs read clinical lab
tables well — exactly LongevityBench's NHANES finding — while leaving the
omics-in-prompt question in MASLD completely open. Our MB-2001 asks the same
clinical question but with biopsy-proven labels and expression input.

### Adjacent ecosystems (different paradigm, must be cited, not beaten)

- **Single-cell foundation models** (scGPT, scFoundation, UCE, Transcriptformer)
  and their benchmarks (OpenProblems, SCMBench Nat Commun 2026, the
  perturbation-analysis benchmark arXiv:2410.13956, BAISBench). Encoder-style
  models doing integration/perturbation tasks — not instruction-following
  LLMs reading expression prompts. In our framing these are the *classical
  ML* competitor class, and our logreg/HGB baselines already proxy that
  regime honestly.
- **OmicsBench (arXiv:2610.21074, this month)** — 97 chained multi-turn tasks
  for bioinformatics *agents*. Orthogonal: agent workflow evaluation, not
  omics-in-prompt inference. Signals how fast the space is moving.
- **LLM-eval methodology** (paired-test discipline: Ivanova; FAQ/alphaXiv) —
  general-purpose statistical rigor arguments nobody has applied to an omics
  benchmark. Our paired-stats section rides this literature.

### What is already crowded (do not claim)

General multi-domain omics benchmarking (LongevityBench owns it);
single-cell FM benchmarking; clinical-lab-value LLM prediction (Fibro-GPT);
bioinformatics agents (OmicsBench); general medical QA.

---

## 2. Whitespace map — what only MASLD-Bench has

| # | Whitespace | Evidence it is open | Our artifact |
|---|---|---|---|
| W1 | Disease-specific LLM benchmark with **biopsy-proven histology endpoints** (F0-F4, NAS) | LongevityBench: zero histology tasks; Fibro-GPT: no omics, surrogate labels | MB-20xx/12xx (GSE48452/135251/130970/167523, EPos-only) |
| W2 | **Cross-tissue/perturbation transfer families** (progression, blood-proxy, liver->plasma, PHH FFA) | No equivalent task exists in any benchmark | MB-85xx/86xx/87xx/88xx |
| W3 | **Paired significance discipline** on omics LLM claims (McNemar exact / Wilcoxon, identical items, 929-item frame) | LongevityBench is mean-rank only; the eval-methodology literature has no omics application | results/c2_significance.csv; and the demonstration that our own pairwise "win" evaporated under pairing + a fair bracket |
| W4 | **Controlled training-exposure negative** (trained-on-C3 still fails held-out perturbation) | Their SFT headline has no stress test like this | v6 experiment: 0.500 at majority while logreg reads 0.833 |
| W5 | **Regime split on identical prompts** (LLM vs classical ML on the same strings) | Nobody reports the logreg-0.833-vs-majority contrast on identical items | C4 + MB-8801 gate |
| W6 | **Label-integrity discipline as a contribution** (SHA manifests, test-before-train, documented refusals and self-caught corrections) | Absent from every competitor | MANIFEST v3-freeze-16; GSE126848 refusal; freeze-8 off-by-one catch + quarantine |

The defensible one-sentence positioning: **the disease-specific,
histology-grounded replication+extension of LongevityBench, with the
statistical rigor and honest negatives their mean-rank design cannot
express.**

Timing risk: W1/W2 are visibly unclaimed but the space is hot (OmicsBench
appeared this month; SCMBench in Nat Commun 2026). The window for "first
disease-specific omics-LLM benchmark with histology endpoints" is open now
and will not stay open indefinitely.

---

## 3. Does the 9B run add value?

### The reviewer question it answers

LongevityBench's headline IS "a ~9B fine-tune beats frontier." Our current
C2 reads: compact (0.6-1.7B) wins regression decisively (MB-2005 MAE 1.226
vs 1.529 best-of-12; MB-2006 2.162 vs 3.814), ties binary (0.667 vs 0.661),
**loses pairwise to claude-sonnet-4.5 (0.610 vs 0.593)**. Without a 9B-class
run, the most predictable reviewer objection is: *"you did not test the
scale at which their result appeared."* That objection hits both remaining
claims:

- C2: "compact matches frontier" is untested at the scale class where the
  anchor paper found the effect.
- C4: "format dominates over scale" rests on a 13x untested gap (1.7B -> 8B).

### Value by outcome

| v7 outcome | What it does to the paper | Value |
|---|---|---|
| 8B transfers (perturbation > majority, or beats frontier broadly) | Replicates their core finding in a disease-specific domain -> replication+extension story complete; strongest version; Cell-tier argument strengthens materially | Highest |
| 8B fails (still majority; logreg still 0.833) | C4 at its strongest: even ~13x scale with in-domain SFT cannot read the format. Boundary condition they never mapped. QLoRA confound must be worded honestly ("QLoRA-8B", not "8B") | High |
| Mixed (regression improves; transfer still null) — the expected one | C2 deepens on regression; C4 stands elsewhere; story refined, not changed | Medium-high |

No plausible outcome damages the paper: W1/W3/W4/W5/W6 are outcome-
independent, and the bracket is already complete. The run only resolves the
one open variable.

### Cost and alternatives

~65-100 compute units (one Pro+ month at $49.99, or spread across existing
Pro quota), 6-10 wall-clock hours, resume-safe. Cheaper substitutes do not
answer the objection: Qwen3-4B leaves the gap half-crossed and a reviewer
can still say the anchor effect lived at ~9B. Additional frontier spend is
now worthless (12 references already exceed what the argument needs — the
anchor used 15-18 across far more tasks). New cohorts are blocked on public
data availability (documented negative), not on compute.

### Honest limits to state in the manuscript

1. QLoRA (4-bit NF4) vs their full-precision LoRA: on a positive result this
   evaporates (a win under a *harder* budget is still a win); on a negative
   it must be acknowledged. Mitigation: cite QLoRA-vs-LoRA parity evidence
   (e.g., FinLoRA-style studies) and note our 0.6/1.7B runs used full LoRA
   and behaved identically.
2. One family of models (Qwen3) — same limitation class as the anchor.
3. n of the novel families is small (blood 21, perturbation 30 cultures) —
   the C3a gates were pre-registered precisely to keep this honest.

### Verdict

**Run it.** It is the highest-leverage remaining compute in the program:
it closes the #1 predictable reviewer objection, completes the
0.6B -> 1.7B -> 8B scale axis against a 12-reference frontier bracket, and
every outcome maps to a publishable claim. Everything else that would
strengthen the paper is either done (bracket, paired stats, corrections) or
blocked on external data availability (blood cohort), not on GPU hours.

---

## 4. Post-v7 publication ladder (unchanged by this analysis)

- Now (with v7 either way): Cell Metabolism / Cell Reports Medicine tier —
  disease-specific benchmark, histology-grounded, paired-stats discipline,
  scale axis complete, honest negatives + documented integrity corrections.
- Cell-tier resubmission additionally needs: a large novel cohort
  (GRIPonMASH release, S-BSST1614 phenotype table, or an author-deposited
  n>=200 blood cohort — the search brief names the exact asks) and possibly
  a full-precision 8B confirmation run if v7-QLoRA is positive-but-thin.

---

## Sources

- LongevityBench Cell full text: https://www.cell.com/cell/fulltext/S0092-8674(26)00999-2
- LongevityBench bioRxiv full text (task/model/method detail): https://www.biorxiv.org/content/10.64898/2026.01.12.698650v1
- Insilico toolkit release (9B claim, cost): https://www.prnewswire.com/news-releases/insilico-medicine-opens-ai-longevity-discovery-toolkit-to-researchers-worldwide-in-cell-cover-study-302882275.html ; https://longevitybenchmarks.org
- Fibro-GPT (Njei 2026): https://pmc.ncbi.nlm.nih.gov/articles/PMC12955738
- SCMBench (Nat Commun 2026): https://www.nature.com/articles/s41467-026-72570-x
- Perturbation-analysis FM benchmark: https://arxiv.org/html/2410.13956v1
- OmicsBench agents (Oct 2026): https://arxiv.org/html/2610.21074v1
- BAISBench: https://academic.oup.com/bioinformatics/article/42/Supplement_1/btag227/8726318
- OpenProblems FM benchmark: https://openproblems.bio/benchmarks/foundation_models
- LLM-eval paired-statistics methodology: https://desirivanova.com/post/llm-stats-evals ; https://www.alphaxiv.org/abs/2601.20251
- AI in liver-disease omics review (context): https://pmc.ncbi.nlm.nih.gov/articles/PMC11874365
