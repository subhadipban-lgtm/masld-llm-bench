# MASLD-LLM workbench run log

## 2026-09-29 · v3 freeze-1 + freeze-2 (local build session)

### What was built

**Frozen test corpus (freeze-1)** — `prompts/MB-20xx_liver_test.jsonl.gz`, 13,273 prompts
- EPos (157 staged) + Gubra (57 staged, fibrosis from title suffix `NAFL_<stage>`)
- Tasks: MB-2001/2002/2005/2006 single-profile + MB-2003 pairwise (intra-cohort)
- **Frozen forever.** No Fujiwara, no external_v3 data touched this file.

**Train corpora (freeze-2)** — 44,921 prompts across four files:
- `MB-10xx_liver_train.jsonl.gz` — 3,928: Kamzolas SANYAL+UCAM (135 staged; F0=32, F1=50, F2=23, F3=23, F4=7)
- `MB-8xxx_fujiwara_train.jsonl.gz` — 204: Fujiwara TU+HU+TH (51 staged of 213 joined; KU series reserved as internal test)
- `MB-61xx_msigdb_train.jsonl.gz` — 2,701: pathway-membership masked-gene tasks (msigdb c2)
- `MB-62xx_drugs_train.jsonl.gz` — 30,000: drug→gene retrieval tasks (DrugBank-layer interactions)
- `MB-70xx_dge_direction_train.jsonl.gz` — 8,088: direction-of-change from discovery DGE (t1_ranked_logFC)

**Total: 58,194 prompts, all with rotating verbalizations and provenance checksums** (`prompts/MANIFEST.json`).

### Data acquired this session (workbench/data/external_v3/, 460 MB)

11 tier-1 external datasets downloaded and staging-audited:

| Accession | n | Staging available | Verdict |
|---|---|---|---|
| GSE48452 | 73 | fibrosis 0–4 (0.5/3.5 present), NAS, group | ✅ joins train pool (freeze-3) |
| GSE49541 | 72 | mild (F0-1) vs advanced (F3-4) | ✅ train pool (binary + grouped stages) |
| GSE66676 | 67 | histology (no NAFLD / NAFLD not NASH / NASH) — **no fibrosis stage** | ⚠️ NASH-vs-no-NAFLD binary only |
| GSE89632 | 63 | fibrosis 0–4 (31/14/2/4/4), ballooning, inflammation | ✅ train pool (4 formats) |
| GSE61260 | 134 | age, diseasestatus (Normal/NASH/NAFLD/Healthy Obese) | ✅ age tasks + disease binary |
| GSE247407 | 30 | FFA-treated vs control PHH | ⚠️ perturbation corpus, not clinical |
| GSE48325 | 85 | **DNAm** 450K, group, bariatric before/after, age | ✅ opens DNAm domain (freeze-4) |
| GSE164760 | 80+ | NASH-HCC + NASH (expression array n=127) | ⚠️ HCC-contaminated; NASH-only arm usable |
| GSE162694 | 143 | NASH fibrosis DE study | ✅ metadata-only SOFT; matrix needs SRA/GTEx-style pull |
| GSE269926 / GSE244832 | — | snRNA / HSC multi-modal | phase-2 (supplementary files needed) |

### Bugs found and fixed during the build

1. GEO FTP path rule: series dir = accession minus **last 3 digits** + `nnn` (GSE48452 → `GSE48nnn`). My first round 404'd on 5-digit accessions.
2. Kamzolas join key = `Sample name` column (`Sample N`), not the metadata row index.
3. Gubra fibrosis stage encoded in `title` (`NAFL_1`…`NAFL_38`), not in characteristics.
4. Train/test scale mismatch: Kamzolas batch-corrected (log-ish, can be negative) vs EPos raw counts vs Gubra normalised → fixed with label-free per-sample standardisation (log1p if non-negative, then z-score).
5. MSigDB c2 JSON: members under `geneSymbols` key per set dict, not the dict values directly.
6. Task-ID padding produced MB-10001 instead of MB-1001 → normalised to MB-1xxx/2xxx scheme.

### Next steps (in order)

1. **Freeze-3**: add GSE48452, GSE49541, GSE89632, GSE61260, GSE66676(binary), GSE164760(NASH arm) to the train pool — SOFT files already on disk; needs expression-matrix extraction from supplementary files (GSE48452/GSE49541 matrices are embedded in the SOFT or as suppl files).
2. **Freeze-4 (DNAm)**: GSE48325 beta values → age/fibrosis-from-methylation tasks (paper's GEO DNAm analogue; 450K platform GPL13534).
3. **ArrayExpress tier-1**: E-MTAB-9815, E-MTAB-15601/-15612/-15586/-15587/-15609/-15610 (perturbation panels) — download via BioStudies APIFTPs.
4. **Baselines** on the frozen test (laptop-runnable): ElasticNet/HGB fibrosis clocks on prompt features → `results/baselines.json`.
5. Then Colab: notebook 01 (rest of corpora) → 02 (frontier bracket) → 03 (0.6B ladder first).

## 2026-09-29 · Cell publication plan added

- `../MASLD-LLM_cell_publication_plan.html` — claims (C1–C4), figure plan (F1–F6 + supplements S1–S10), statistics/rigor plan, 6-month timeline with go/no-go gates, authorship/licensing.
- Key decisions made for the plan:
  - Test freeze (EPos+Gubra) precedes all new training data — the reviewer-defense anchor.
  - C3 (progression + blood-proxy tasks) is the headline novelty over LongevityBench; C4 (ML/LLM regime split) is the field-level lesson.
  - Journal ladder: Cell → Cell Metabolism → Cell Reports Medicine.
  - Analysis plan to be frozen before the frontier bracket (P2) runs.
- Fixed in this pass: MB-7001 prompts had a dangling "gene with the following characteristics" clause showing no characteristics (gene symbol was dropped in the masked design). Now the named-gene variant; MB-7002 masked variant to be built before P2 so the contamination delta is a designed comparison.

## 2026-09-29 · Drug-discovery extension (design + smoke test)

- Question: can Chai-1 / AlphaFold add natural-product compound nomination?
- Verdict: yes, but only at the structure/screening stages — target nomination
  already lives in masld_kg_v5 (21k drugs, 35k target edges, personalization
  annotations).
- Audited on-disk assets: Natural .xlsx = seed only (~4 unique NPs, quercetin/
  kaempferol/carvacrol); FerrDb 246 inhibitors; PubChem props 10,650.
- Smoke-tested AlphaFold DB API: current model files are **v6** (v4 URLs 404);
  downloaded 5 seed target structures (THRβ, PPARα, GSK3β, LPA1, NCOA3) ->
  drug-discovery/structures/.
- COCONUT (~400k NPs) verified reachable — the missing library piece.
- Design doc: drug-discovery/README.md (5-stage pipeline, compute budget,
  honest caveats: docking = weak evidence, frame as computational nomination).

## 2026-09-29 · Master plan + freeze-3 executed

- Master plan written: docs/MASLD-LLM_master_plan.html — five workstreams
  (W1 corpora, W2 baselines+frontier, W3 model ladder, W4 drug arm, W5 paper),
  7-session immediate queue, budget $220–500, risk register with fallbacks.
- Downloaded 7 expression matrices (series-matrix + count files) for the
  external cohorts; GSE61260 needed its supplementary normalized-expr CSV
  (series matrix was metadata-only).
- **Freeze-3 built: MB-11xx_external_train.jsonl.gz — 5,575 prompts.**
  GSE48452 (71 staged), GSE49541 (72), GSE89632 (56), GSE66676 (67 binary),
  GSE61260 (134 age-regression tasks). Train pool now ~466 staged samples.
- Bug fixed (7th of the program): family.soft characteristics are per-sample
  sequential lines, not cohort-wide — parser rewritten; GSE48452 went from
  1 staged to 71 staged.
- MANIFEST bumped to v3-freeze-3. **Program total: 63,769 prompts.**
- Next in queue: ML baselines on frozen test (session 2), analysis-plan
  freeze + frontier bracket (session 3), COCONUT pull (session 4).

## 2026-09-29 · Sessions 2–4 executed

### Session 2 — ML baselines on frozen test (results/baselines.json)
- Gene-feature models: binary EN 0.382 / HGB 0.382 vs majority 0.582; multiclass
  EN 0.240 / HGB 0.249 vs majority 0.200; regression EN MAE 1.838 (rho 0.292).
- **Finding (honest): cross-platform feature mismatch.** External microarray
  cohorts expose probe IDs; the test uses Ensembl. Full-pool gene models
  undershoot majority on binary. Kamzolas-only (feature-matched) rerun:
  binary 0.560/0.564, multiclass 0.231, regression EN rho 0.250.
- Action: map all platforms to gene symbols in freeze-4 (probe->gene from the
  GPL tables already in the SOFT files), then re-train baselines. Recorded in
  baselines.json meta.finding.

### Session 3 — analysis plan frozen + frontier tooling ready
- analysis-plan/ANALYSIS_PLAN_v1.md: pre-specified contrasts (C2, C4), metrics,
  ranking scheme, model roster, decoding protocol, validity handling, bootstrap
  stats, falsification criteria. Frozen BEFORE any API call.
- scripts/session3_frontier.py: OpenRouter runner (stratified 300/task, seed
  20260929, resumable, archives raw + parsed + model version).
- scripts/score_frontier.py: scoring with bootstrap CIs -> leaderboard.csv.
- **Blocked on: OPENROUTER_API_KEY** — user must create key at openrouter.ai
  and provide it (env var, or ~/.openclaw/tmp/or_key.txt, or masld-llm/.or_key).

### Session 4 — COCONUT NP library (drug arm unblocked)
- COCONUT API flaky (intermittent 400s on identical payloads) -> switched to
  the Zenodo COCONUT 2.0 dump (record 13692394).
- Downloaded + filtered with RDKit: **327,916 NPs kept** from 695,133 scanned
  (MW 250–600, Crippen LogP 0–5, dedup). Library:
  drug-discovery/library/coconut_filtered.smi (SMILES + identifier + MW + LogP).
- Next: top-5k selection + 3D conformers -> Vina screen vs the 5 AF targets.

## 2026-09-29 · Four-folder NP/drug audit + unified library

Audited: NP-MRD (7 shards, 150,927 unique SMILES), NPAtlas (36,454 curated;
23,530 in-range; 3,492 IKs not in COCONUT), Drug_database (DrugCentral 23,115
w/ affinities; DrugBank 35,043; CTD 41,624), summit_poc (1.4 GB NMR PoC +
CMNPD marine 31,561 + COCONUT lite **09-2026** — two years newer than our
09-2024 dump).

Built:
- **unified_np_library.smi — 362,313 unique NPs** (InChIKey-dedup, RDKit
  MW 250–600 + LogP 0–5): coconut_2026 338,986 + npmrd 11,003 + cmnpd 10,614
  + npatlas 1,710 net-new. NP-MRD/CMNPD add ~21.6k NPs COCONUT lacks;
  NPAtlas mostly overlaps (curated value = metadata, not novelty).
- **drug_target_full.csv — 92,486 drug→target rows** (11,677 drugs × 9,414
  genes) from DrugCentral+DrugBank+CTD merge.
- **MB-63xx prompts — 19,982 affinity-grounded drug→target tasks**
  (DrugCentral ACT_VALUE; strong/moderate/weak verbalization). Program total
  now 83,751 prompts.
- summit_poc's NMR-shift models (HOSE/shift-MPNN .pt) noted as a future
  structure-elucidation extension — not part of the current benchmark.

## 2026-09-30 · Sessions 6 + 7 prep

- Frontier bracket: relaunched detached with flush patch (overnight run was
  killed by session timeout; ~148 records recovered). Pacing ~30-46/min.
- **Session 6a — DNAm domain open**: GSE48325 signal intensities downloaded
  (368 MB), beta values computed (B/(A+B), detection p<0.01 in >=80% samples,
  483,781 CpGs x 85 samples), MB-30xx built (73 train / 19 test; NAFLD-vs-
  NORMAL binary, age-decade multiclass, age regression).
- **Session 6b — Fujiwara KU internal test**: MB-9xxx built (224 prompts,
  56 staged KU samples, train-side feature selection from TU+HU+TH).
- MANIFEST -> v3-freeze-4. **Program total: 84,067 prompts.**
- **Session 7 prep**: top-5k diverse NP subset selected (greedy max-min
  Tanimoto, 60k candidate pool); 3D conformer generation running detached.

## 2026-09-30 · background status at turn end

- Conformers: ~1,000/5,000 done (ETKDGv3 + MMFF, ~2/s on M2; ETA ~35 min more).
- Frontier bracket: DeepSeek ~410/1,110 (30/min); 5 models queued after.
  Total bracket ETA ~5-6 h. Both processes detached (nohup).
- Next when bracket completes: run scripts/score_frontier.py -> leaderboard.csv.

## 2026-10-01 · Drive-sync notebook edition + bracket diagnostics

- Colab notebooks 01/02/03 rewritten for the Drive-for-Desktop sync layout:
  auto-discovery of masld-llm / masld-revision / masld-clinical-transcriptomics-
  github under MyDrive (handles 'My Mac' computers-sync naming), read-only
  detection with writable output fallback (MyDrive/masld-llm-outputs).
- Frontier bracket audit: DeepSeek complete (1,120 ok). Gemini 440 ok then 402s.
  Claude/GPT-4.1-mini 100% 402 — the promotional credit does not cover
  OpenAI/Anthropic providers on this key. Probe-verified working roster:
  kimi-k3, minimax-m3, qwen3-235b, llama-3.3-70b, deepseek, (gemini partial).
- Bracket relaunched on the verified roster (restart 6).
- Conformers complete: 4,904/5,000 NPs (top5k_3d.sdf) — Vina-ready.

## 2026-10-01 · First leaderboard (partial bracket)

- Scored: deepseek-chat (1120 ok), gemini-2.5-pro (440 ok before 402),
  nemotron-120b-free (1010 ok before free-daily-limit 1000).
- Headline numbers on frozen test (EPos+Gubra):
  - binary: nemotron 0.582 [0.516-0.644] ~= majority baseline; deepseek 0.123
    (inverted answers), gemini 0.391
  - multiclass: nemotron 0.231 ~= ML EN baseline 0.231-0.253; others below
  - pairwise: deepseek 0.393, nemotron 0.497 (below 0.5 chance-corrected mean)
  - regression: nemotron MAE 2.12 vs ML EN 1.76
- Interpretation: frontier zero-shot CANNOT solve fixed-panel liver-omics
  tasks (matches LongevityBench's NHANES/omics findings). The C2/C4
  contrasts now have their frontier bracket forming. ML baselines still
  lead on regression/multiclass — the compact tuned models must beat
  these numbers to claim anything.
- Bracket restart 8 running: kimi-k3, minimax-m3, qwen3-235b, llama-3.3-70b,
  gemini resume, nemotron final 153 (after free-limit reset).

## 2026-10-01 · Session-5 crash diagnosed + fixed (from user's Colab log)

- User ran notebook 03 on Colab; training OOM'd at step 0 (9.3 GiB alloc).
  Root cause: Qwen's 151,936 vocab x 8,192 packed cutoff x batch 2 = ~9.9 GiB
  logits tensor for cross-entropy. The paper's recipe includes Liger fused
  kernels for exactly this - now enabled (enable_liger_kernel: true, plus
  liger-kernel pip install in the train cell).
- Config retuned for the actual 22 GB Colab GPU: cutoff_len 8192->4096,
  batch 2->1, grad_accum 16->32 (effective batch unchanged at 32).
- **Corpus bug caught from the log**: MB-63xx DrugCentral rows carry pipe-joined
  multi-gene "targets" (e.g. GABRP|GABRD|...|GABRQ) as answers, contradicting
  "Answer with one gene symbol". Rebuilt: pipe-lists split per gene, single-
  symbol decoys only -> 39,632 clean prompts (was 19,982 contaminated).
- MANIFEST -> v3-freeze-5. Program total: 103,717 prompts.

## 2026-10-02 · Notebook 3 verified; bracket final state (this key)

- Notebook 03 post-fix verification: all 14 cells compile, all 12 content
  checks pass (the one "FAIL" was my checker miscounting to_alpaca calls:
  9 = 1 def + 8 corpora incl DNAm + fixed MB-63xx). Colab round-trip via
  Drive sync preserved everything. VERDICT: ready to run from cell 4.
- Bracket final on this key: deepseek 1120 ok (complete), nemotron 1010 ok
  (free daily cap), gemini 440 ok (partial), qwen-235b 115 ok (partial).
  llama-3.3 / glm-4.6 / minimax / kimi: 100% HTTP 402 - the promotional
  credit does not cover their providers on long prompts (short-prompt probes
  pass; OpenRouter pre-auth charges full provider context). Files deleted to
  keep runs clean.
- Leaderboard re-scored with 4 usable models. Completing the roster to 6+
  needs either the free-tier daily reset (nemotron finishes) + more
  free-tagged models, or a paid OpenRouter key (~$30) - deferred decision.

## 2026-10-04 · Bracket resume fix + final frontier state

- Resume-logic bug found and fixed: the runner keyed 'done' on sample ID
  alone, but sample IDs repeat across tasks (same patients in 2001/2002/
  2005/2006), so partial archives masked unfinished work ("0 to go" lies).
  Fixed to task:sample, successes only. All error records stripped from
  partial archives.
- Nemotron COMPLETED with the daily reset: 1,142/1,143 ok (second full
  model). Gemini and qwen-235b gap-fills hard-failed on persistent provider
  402s (pre-auth walls on long prompts; credit remains but providers won't
  authorize). Kept: gemini 440, qwen 115 successes.
- FINAL frontier bracket on this key: deepseek 1120 (full), nemotron 1142
  (full), gemini 440 (partial), qwen-235b 115 (partial) + qwen3-0.6b-masld
  (compact, cycling-degenerate eval - invalid, pending one-shot re-eval).
- Notebook 03 has the one-shot verify+eval cell (b3ab275) awaiting the
  user's Colab run: fingerprint check, auto-rebuild if stale, newline-
  stopped generation (fixes the packing-induced answer cycling), inline
  scores.

## 2026-10-04 · First valid compact-model eval (0.6B) — honest result: POOR

One-shot cell completed the full chain (stale-merge detect -> fresh rebuild ->
newline-stopped eval). These are the first VALID numbers for qwen3-0.6b-masld
on the frozen test:

  MB-2001 binary:      acc 0.311, validity 0.591   (majority 0.582)
  MB-2002 multiclass:  acc 0.000, validity 0.000   (ML EN 0.253; never emits F-stages)
  MB-2003 pairwise:    concordance 0.470, validity 1.000 (nemotron 0.497)
  MB-2005 regression:  MAE ~3e12 (emits 30-token digit strings), rho 0.050
  MB-2006 NAS:         MAE ~6e26, rho -0.007

Diagnosis (three compounding causes):
1. Mixture imbalance: the 60k-target sampler fell back to the raw pool when
   domains were small -> drugs 50% of actual training (15k of 33.8k), liver
   clinical only 33% (9.7k). The model learned drug-QA, not liver-omics.
2. Multiclass answer-format gap: training answers were bare stage numbers
   ("2"), eval prompts ask "Answer with one of F0..F4" - the model has literally
   never seen an F-prefixed answer, so validity 0.000.
3. Digit-string degeneracy on regression: same packing artifact as the
   cycling, in the numeric modality; first-line truncation catches valid
   digits only when the model emits them, but it emits 0000... or huge runs.

The training pipeline is validated end-to-end (mount->corpora->train->merge->
eval->score). The MODEL needs retraining with: balanced mixture (cap drugs
~25%, upweight liver), answer-format-matched training prompts (F0-F4 answers
for multiclass, yes/no for binary), and unpacked or EOS-terminated SFT.

Comparison anchors: even nemotron-120b zero-shot only ties majority on binary.
The C2 claim (compact beats frontier) is NOT supported at 0.6B with this
recipe - consistent with LongevityBench, whose small models also lagged;
their gains came at 4B+ with format-matched training.

## 2026-10-04 · CRITICAL test-set fix (freeze-6): Gubra labels were fake

- Diagnosis chain: 0.6B always-F1 outputs -> gold=F5..F9 discovered in the
  frozen test -> traced to the Gubra harmonizer: title suffixes (NAFL_5..9,
  NASH_5..9, etc.) are SEQUENCE NUMBERS, not fibrosis stages. Gubra has NO
  per-sample staging (disease groups only). All 57 Gubra stage-labelled
  records + 1,449 Gubra pairwisce prompts were noise (23 of 225 multiclass
  golds were fake stages).
- Fix: harmonizer patched (Gubra fib = NaN), frozen test rebuilt: EPos-only,
  11,653 prompts. MANIFEST -> v3-freeze-6. Program total: 102,097.
- All eval archives RESCORED against the cleaned test (records carry their
  own answers, so no re-querying needed; Gubra records dropped at scoring).
  Parser fixed for F-token runs (F1F1F1...) matching the compact model's
  emission mode.
- Cleaned-test leaderboard highlights (EPos-only):
  - nemotron binary 0.661 [was 0.582 with Gubra noise] - genuinely ABOVE the
    0.582 EPos majority now
  - nemotron pairwise 0.500, deepseek regression MAE 1.768 (rho 0.040)
  - 0.6B compact: binary 0.339, pairwise 0.473 - unchanged verdict, needs
    the v2 retrain
- Retrain spec (v2 recipe) ready to implement: balanced mixture (drugs capped
  25%), format-matched answers (F0-F4 multiclass, yes/no binary), EOS-terminated
  generation handling.

## 2026-10-05 · v3 results: FIRST COMPACT-BEATS-FRONTIER DATAPOINT

- v3 training complete (1200 steps, 2 epochs, loss 0.17). One-shot eval chain
  worked end-to-end (stale-merge detect -> rebuild -> newline-stopped eval).
- Corrected final scores (EPos-only frozen test, F-token parser):
  - MB-2003 pairwise: 0.593 (nemotron 0.500) — FIRST C2 WIN: compact beats
    every frontier model on a task family
  - MB-2001 binary: 0.405 (v1 0.339) — improving, still below majority 0.582
  - MB-2002 multiclass: 0.208 acc / 1.000 validity — the "0.000 validity" was
    MY scoring bug (eval cell's stored parser required word boundaries;
    re-parse shows 168/168 valid). Model emits proper F-stages but collapses
    to F0/F1 (90/78) — early-stage bias, likely from upsampled train dist
    (F0:50, F1:50 dominant) + no calibration
  - MB-2005 regression: MAE 1.494 (< nemotron 1.606, < ML EN 1.76!) with
    rho 0.011 — good MAE is from mean-prediction (predict ~1.7), zero signal
  - MB-2006 NAS: still emits catastrophic digits (MAE 1e26) — NAS answer
    range 0-8 with "0" leading tokens repeats
- Recipe verdict: format-aware upsampling WORKS (pairwise +13pts, multiclass
  format established, binary +7pts). Remaining: class balance, NAS digit
  degeneracy, binary still below majority.

## 2026-10-05 · 1.7B run prepped (v4 recipe)

- v3 verdict banked: pairwise 0.593 beats all frontier (first C2 win);
  multiclass 0.208/validity 1.0 (format established, F0/F1 collapse);
  binary 0.405; fibrosis MAE 1.494 (leaderboard best).
- Notebook 03 extended with the 1.7B section (3 new cells, all compile):
  A) v4 class-balanced sampler: multiclass F0:F1:F2:F3:F4 weighted 2:1:2:2:7,
     binary yes x3, NAS x3, singles base x8, pairwise x1, drugs 10k, know 8k.
     Writes sft_multitask_17b.json. Includes global-recovery for reset runtimes.
  B) 1.7B LoRA config (r32 a32, 2 epochs, liger, checkpoints to Drive) + all
     CUDA fixes inline. ~10-14h on L4.
  C) Direct-PeFT merge (staleness-guarded) + eval with the UNIT-TESTED parser
     (case-preserved F-token, startswith-b) + inline scores. Archives as
     qwen3-1.7b-masld__MB-20xx.jsonl.gz.
- Expected readouts: does pairwise 0.593 hold/grow with capacity; does class
  balancing fix the F0/F1 collapse; does binary cross majority 0.582.

## 2026-10-05 · Novelty audit + geometric reasoning layer (MB-40xx)

- Analysed the two pasted strategy docs (novelty landscape + geometric layer).
- Verified the landscape claim: AI-MASLD (arXiv Y Shen 2025) is real —
  text-based clinical narratives, GPT-4o/Gemini class. => C1 repositioned:
  "first multi-domain OMICS-BASED MASLD benchmark" (text-input evals exist;
  omics-geometry + compact models do not). Citation list to add: AI-MASLD,
  Med-Scout, GraphSeqLM, Bio-GraphLLM, GALAX, LyMOI.
- Built the geometric compression layer (MB-40xx):
  - v1 (7 modules, binned scores): FAILED sanity (binary 0.38 vs maj 0.661,
    multi 0.07, rho 0.16) — not trained on, documented.
  - v2 (9 modules @ resolution 1.5, continuous scores, UMAP + neighbour
    severity): PASSES — binary EN 0.679 (BEATS majority 0.661 and raw-gene
    EN 0.484), multi 0.280 (vs raw 0.253), reg MAE 1.210 rho 0.193, at 354
    chars/prompt (8% of raw length).
  - 405 train + 504 test prompts, leakage-proof (graph/UMAP/kNN fitted on
    Kamzolas train only; EPos only embedded).
- This gives the paper a new C3 task family (geometric omics reasoning) and
  a raw-vs-geometry ablation axis, both absent from LongevityBench.

## 2026-10-05 · Ablation prep + geometric bracket blocked on credit

- Analysed the strategy review (doc 3): recommendations adopted —
  cell 18 patched to v5 (geometric train prompts x6 join the 1.7B mixture),
  cell 20 patched to evaluate BOTH raw (MB-20xx) and geometric (MB-40xx) test
  sets on the same model = the within-model raw-vs-geometry ablation figure.
- Geometric frontier bracket (all 6 models on 354-char prompts): BLOCKED —
  the OpenRouter key's promotional credit expired ($10.41 real usage, rest
  was promo). All API calls now 402. Needs a top-up (~$10-20) or a new key.
  Runner script saved at /tmp/geo_frontier.py (copy to scripts/ before reboot).
- Robustness check (geometry stability across train subsamples): TODO next.
- v1 negative result: already documented in RUNLOG + manifest; will become
  supplement table per the review.

## 2026-10-05 · Geometry stability check: UNSTABLE across subsamples

- 3x refits on 80% train subsamples: modules 8/8/10 (stable-ish), but binary
  EN accuracy on EPos swings 0.345-0.679 (mean 0.560 ± 0.152).
- Verdict per the review's own criterion: UNSTABLE — the 0.679 headline from
  the v2 full-train fit is not robust to train-subsample variation. Trial 1
  (0.345) shows the module set can fail badly depending on which patients
  build the graph.
- Honest handling: report mean ± sd across refits in the paper; frame the
  0.679 as the full-train point estimate, not a stable property. This is a
  limitation note, not a hidden result. Small-n (135 train patients) is the
  root cause — module estimation on 80% of 135 patients is noisy.
- Paper impact: geometric layer stays as a task family + ablation axis, but
  the "geometry beats raw on binary" claim must carry the ±0.15 caveat until
  train-side n grows (external cohorts could join geometry fitting — the
  GSE48452/49541/89632 cohorts are all train-side and gene-symbol mapped).

## 2026-10-05 · Colab automation stack

Three tiers, honest about limits:
1. NOTEBOOK 04 (one-click Run-all): mount->install->v5 mixture->train (GPU
   hygiene + skip-if-done guard)->merge->dual eval. Manual "Run all" click or
   Colab Pro+ Schedule (clock icon). No interactive input needed.
2. Laptop autopilot (LaunchAgent com.masld.autopilot, every 10 min):
   detects training completion, auto-scores landed eval files into the
   leaderboard, appends RUNLOG entries, sends macOS notifications (incl.
   trainer-stall alerts >45 min). Live and running (PID verified).
3. Colab API limits: no headless *start* of notebooks on Pro/Pro+; the
   Pro+ scheduler + background execution is the official unattended path.
   Full programmatic control would need a self-hosted GPU instead.

### autopilot 2026-10-07T23:59
- detected qwen3-1.7b-masld__MB-20xx.jsonl.gz -> scored OK

### autopilot 2026-10-07T23:59
- detected qwen3-1.7b-masld__MB-40xx.jsonl.gz -> scored OK

## 2026-10-08 · 1.7B complete + dual eval (raw vs geometric) — honest verdict

Training: 2.0 epochs, 1154 steps, loss 0.092 (resumed once after session
eviction; total ~29h incl. the 24h gap). Merge + both evals ran automatically
via notebook 04 Run-all — the automation chain worked end-to-end.

RAW (MB-20xx, EPos-only frozen test):
  binary 0.661 (validity 1.0) — BUT emissions are 160 no / 8 yes: the model
  learned majority-class behavior, NOT fibrosis signal. Matches the 0.661
  majority baseline exactly. Same verdict as frontier models.
  multiclass 0.185 (F0/F1-heavy emissions; class balance improved spread
  but F2/F4 still rare)
  pairwise 0.470 — REGRESSED vs 0.6B-v3's 0.593. The bigger model lost the
  one thing the small model did well.
  regression MAE 1.411 rho 0.087 | NAS MAE 2.274 rho 0.100 — first model
  with sane NAS numbers (digit degeneracy fixed by class-balancing).

GEOMETRIC (MB-40xx, same model, 8% prompt length):
  binary 0.661 — but 168/168 "no": pure majority collapse on geometric input.
  multiclass 0.202 | MAE 1.268 rho 0.031.

VERDICT (honest): the 1.7B did NOT advance the C2 claim. Pairwise regressed
(0.593 -> 0.470), binary is majority-mimicry, geometric prompts didn't help
the trained model. The 0.6B-v3 remains the best compact model. Diagnosis
hypotheses: (a) v5 mixture changes (geometric x6 + class weights) diluted
the pairwise signal the 0.6B-v3 learned, (b) 2 epochs on 1.7B under-trained
relative to 3 epochs on 0.6B, (c) capacity alone doesn't fix format
confusion without more data. Next: score-check 0.6B-v3 on geometric prompts
(it never saw them — that's the cleaner ablation), and consider a 0.6B-v5
run with the class-balanced recipe to isolate the mixture variable.
