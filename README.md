# MASLD-LLM

Open benchmark + fine-tuned compact language models for metabolic
dysfunction-associated steatotic liver disease (MASLD), following the
LongevityBench recipe (Zhavoronkov et al., *Cell* 189:5980–5994, 2026).

Program status: **active build** (started 2026-09-29). See
docs/MASLD-LLM_cell_publication_plan.html for the Cell-submission strategy
and RUNLOG.md for the build log.

## Layout

```
masld-llm/
├── README.md                  this file
├── RUNLOG.md                  dated build log (what was built, bugs fixed, next steps)
├── analysis-plan/             pre-specified statistics plan (freeze before frontier bracket)
├── prompts/                   FROZEN prompt corpora (gzip JSONL) + MANIFEST.json
├── scripts/                   reproducible builders (python)
├── colab/                     notebooks 01–03 for Google Colab Pro/Pro+
├── data/
│   └── external_v3/           tier-1 external cohort downloads (GEO SOFT, 460 MB)
├── results/                   baseline + evaluation outputs (baselines.json, leaderboards)
├── logs/                      download / build logs
└── docs/
    ├── MASLD-LLM_roadmap.html             full replication roadmap (v3)
    ├── MASLD-LLM_cell_publication_plan.html  claims / figures / timeline
    ├── external_cohorts_v3.csv            62-accession acquisition manifest
    └── assets/                            figures (pipeline diagram, submission plan)
```

## Current frozen state (2026-09-29)

| Corpus | File | Prompts |
|---|---|---|
| Train clinical (Kamzolas SANYAL+UCAM) | prompts/MB-10xx_liver_train.jsonl.gz | 3,928 |
| **Frozen test (EPos+Gubra — never trained on)** | prompts/MB-20xx_liver_test.jsonl.gz | 13,273 |
| MSigDB pathway membership | prompts/MB-61xx_msigdb_train.jsonl.gz | 2,701 |
| Drug→gene retrieval | prompts/MB-62xx_drugs_train.jsonl.gz | 30,000 |
| DGE direction (named-gene variant) | prompts/MB-70xx_dge_direction_train.jsonl.gz | 8,088 |
| Fujiwara clinical train (TU+HU+TH) | prompts/MB-8xxx_fujiwara_train.jsonl.gz | 204 |
| **Total** | | **58,194** |

Integrity: prompts/MANIFEST.json records per-file counts + SHA-256 (first 16
hex chars) and the split rules. **The test side was frozen before any new
training data entered the program — do not regenerate it.**

## Reproducing the freeze

```bash
cd /Users/subhadipbanerjee/masld-llm
python3 scripts/build_mb10xx.py        # clinical core: train + frozen test
python3 scripts/build_mb6xxx_8xxx.py   # knowledge + Fujiwara corpora
```

Requirements: Python >= 3.9, numpy, pandas (any recent versions). On the M2
laptop, each script runs in well under a minute. Source data paths point at
~/masld-revision (data provenance in its DATA_MANIFEST.md).

## Colab (heavy stages)

1. colab/01_MASLD_Bench_prompt_construction.ipynb — upload Drive tiers, build remaining corpora
2. colab/02_baselines_and_frontier_eval.ipynb — ML baselines + OpenRouter frontier bracket
3. colab/03_finetune_masld_llm.ipynb — LoRA/QLoRA ladder (0.6B -> 9B) + vLLM eval

## Ground rules (enforced by MANIFEST)

- Test = EPos + Gubra only, frozen forever; Fujiwara KU reserved as internal test.
- Features selected on the train side only (over the train/test shared gene space).
- Pairwise prompts intra-cohort only.
- Per-sample label-free standardisation (log1p if non-negative, then z-score)
  applied to every expression matrix before prompting.
- Any builder change bumps the manifest version; all evaluation runs must then
  be rebuilt.
