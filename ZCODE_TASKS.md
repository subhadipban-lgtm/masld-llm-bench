# ZCODE TASK PROMPT — MASLD-LLM (2026-10-16)

Paste the block below into zcode IDE as a single agent task.

---

## Role
You are the coding agent for the MASLD-LLM repo at `~/masld-llm` (git, no remote).
Work carefully: inspect before editing, keep backups, never clobber whole files.
The project owner codes alongside you; make small, verifiable commits.

## Repo state (as of 2026-10-16 12:06)
- HEAD = `85a7503` ("B4 RESOLVED: bracket top-up complete ... leaderboard rescored").
- Platform: FastAPI + Typer + Next.js under `platform/`. Test suite: **79/79 pytest green**.
  Run it with: `platform/.venv/bin/python -m pytest -q` (from `platform/`).
- Frontier bracket is COMPLETE: 9 model families, 72 leaderboard rows.
  `results/leaderboard.csv` is rescored. `results/frontier_runs/` holds all archives.
- Paired C2 archive exists: `results/frontier_runs/qwen3-0.6b-masld__MB-20xx_PAIRED.jsonl.gz`
  (929 items = exact frontier frame; overlap with nemotron = 929).
- Platform already has paired statistics: `platform/core/masld_platform/paired.py`
  (`paired_compare(candidate, reference)` → McNemar exact + Wilcoxon per task).
  CLI: `platform/.venv/bin/python platform/cli.py paired-stats <candidate_stem> --reference <ref_stem>`.
- Known problem: `results/frontier_runs/google__gemini-2.5-pro__MB-20xx.jsonl.gz` is TRUNCATED
  (gzip EOF after 590 lines).

## MISSION
Close the C2 credibility gap: turn the single unpaired comparison into a **full paired
significance table** across every frontier reference, extend it to the 1.7B model, repair the
one corrupt archive, and commit. This is the highest-value local work — it needs no credentials.

## Tasks (do in order)

### T1 — C2 paired significance table
Write `scripts/c2_significance.py` that:
1. Loads every frontier reference archive matching `results/frontier_runs/*__MB-20xx.jsonl.gz`,
   EXCLUDING the candidate (`*_PAIRED*`) and the local `qwen3-*` archives.
2. For each reference, calls the EXISTING `masld_platform.paired.paired_compare(candidate, reference)`.
   Do NOT reimplement statistics.
3. Emits one row per (reference_model, task):
   `reference,task,metric,n,cand_value,ref_value,both_correct,cand_only,ref_only,neither,mcnemar_p,wilcoxon_p,verdict`
   - verdict: `WIN` if candidate better and (mcnemar_p<0.05 for accuracy / wilcoxon_p<0.05 for MAE);
     `LOSS` if reference better and p<0.05; else `TIE`.
   - For MAE, "better" = lower value.
4. Writes `results/c2_significance.csv` AND `results/c2_significance.md` (markdown table).
Run it with `platform/.venv/bin/python scripts/c2_significance.py`.

### T2 — 1.7B paired evaluation (local, memory-lean)
Re-run the candidate eval on the frontier's exact frame for the 1.7B model:
- Model: `checkpoints/qwen3-1.7b-masld-sft` (adapter; base `Qwen/Qwen3-1.7B`).
- Reuse the existing memory-lean eval harness `scripts/eval_paired_06b.py` (no merge, batch=1,
  base fp16 + on-the-fly LoRA).
- Output: `results/frontier_runs/qwen3-1.7b-masld__MB-20xx_PAIRED.jsonl.gz`.
- Try MPS first; fall back to CPU via `PAIRED_DEVICE=cpu` if MPS deadlocks.
- Then add it as a second candidate block in T1's table (parameterize the candidate).

### T3 — Repair the corrupted gemini archive
`results/frontier_runs/google__gemini-2.5-pro__MB-20xx.jsonl.gz` is truncated (gzip EOF, 590 lines).
- Preferred (a): re-pull if `~/.openclaw/tmp/or_key.txt` (OpenRouter key) is present and funded:
  `platform/.venv/bin/python platform/cli.py run-frontier google/gemini-2.5-pro --n-per-task 300`
- Fallback (b): move it to `results/frontier_runs/_quarantine/` and ensure it is excluded from scoring.
- Re-run scoring either way: `platform/.venv/bin/python platform/cli.py score --archive-dir results/frontier_runs --out-csv results/leaderboard.csv`

### T4 — Commit
`git add -A && git commit -m "C2 paired significance table across all frontier refs; 1.7B paired; gemini archive repaired/quarantined"`

## Acceptance criteria
- `platform/.venv/bin/python -m pytest -q` still green (79/79 or more).
- `results/c2_significance.csv` has one row per (reference × task); 5 tasks per reference.
- `results/leaderboard.csv` gemini row is freshly scored OR cleanly absent (quarantined).
- All new/edited scripts run cleanly from a fresh shell.

## Discipline (non-negotiable)
- Do NOT regenerate or modify any frozen corpus under `prompts/`. Test corpora are frozen.
- Keep a dated `.bak-YYYYMMDD` before editing any existing platform/script file.
- Report negative results honestly — several rows WILL be `LOSS`. Do not tune to hide them.
- Commit small and often with descriptive messages.

---

## Optional follow-ons (only if GPU/Colab path is available)

### OPT-B — Colab GPU run (needs one human "Permit" click)
Notebook staged at `My Drive/Colab Notebooks/MASLD_maxgpu_runall.ipynb` (ami Drive).
Cell 1 mounts Drive (one consent click), Cell 2 runs
`/content/drive/MyDrive/masld-llm/run_maxgpu.py` (trains 0.6B-v5 + 1.7B-v5, merges, evaluates
MB-20xx, geometric MB-40xx ablation, C3a zero-shot arm on MB-86xx, 1.7B k-shot BDH-CQ ablation),
Cell 3 verifies outputs landed in `My Drive/masld-llm/results/`.

### OPT-C — C3 / F5 build (the Cell-paper headline gap)
1. Acquire F5 sources: GSE267032 (blood-proxy, on disk), MSV000094959 (liver→plasma, NOT yet),
   paired-biopsy progression data, PHH perturbation panels.
2. Build MB-85xx (progression), MB-87xx (liver→plasma), MB-88xx (perturbation transfer) with
   train/test discipline + manifest v3-freeze-9.
3. Baselines + compact eval on the new families.
