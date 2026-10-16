# Maximum-GPU Colab run — how to fire it (2026-10-16)

## What is ready (staged on the ami Drive)
`My Drive/masld-llm/` now holds everything Colab needs:
- `prompts/` — all 18 frozen corpora (incl. MB-40xx k-shot variants, MB-86xx)
- `checkpoints/qwen3-0.6b-masld-sft` — the 0.6B-v3 adapter (88 MB)
- `colab/05_maxgpu_runall.ipynb` — **the one notebook to run**
- `colab/01..04` — earlier notebooks (kept for reference)
- `scripts/`, `analysis-plan/`, `results/` (writable output dir)

Plus the bridge bus: `My Drive/masld-bridge/{outbox,inbox,done}` with **3 jobs
already queued** (0.6B paired, 1.7B MB-20xx, 1.7B geometric).

## The one action only you can do: sign in to Colab
Colab login lands on a **passkey challenge** ("Verifying it's you… Complete
sign-in using your passkey"). That needs your fingerprint/Face ID on your
device — I cannot complete it. Once you sign in once, the session persists and
unattended scheduled runs work.

## Then: run the notebook (two options)

### Option A — interactive, maximum GPU (recommended first run)
1. Open `My Drive/masld-llm/colab/05_maxgpu_runall.ipynb` in Colab
   (Drive → masld-llm → colab → 05_maxgpu_runall.ipynb → Open with Colab).
2. **Runtime → Change runtime type → GPU** (L4 or A100).
3. **Runtime → Run all**. It runs, in order:
   - installs LLaMA-Factory
   - converts the 8 train corpora
   - builds the v5 mixture (class-balanced + geometric)
   - trains 0.6B-v5 and 1.7B-v5 (skip-if-done, Drive-resumable)
   - merges + evaluates MB-20xx for both → `results/frontier_runs/*v5*`
   - **C3a zero-shot arm** on MB-86xx (the outstanding half of the novelty gate)
   - **k-shot (BDH-CQ) ablation at 1.7B** → `results/kshot_17b.json`
   - writes `results/maxgpu_run_manifest.json`
   Expected: ~10–14 h on L4 for both trainings; evals add ~1 h.

### Option B — unattended (after one interactive run)
1. Same notebook → **Runtime → Change runtime type → GPU**.
2. Click the **Schedule** (clock) icon → run hourly (needs Colab Pro+).
3. Separately, open `My Drive/masld-llm/bridge_worker.ipynb` and schedule it too
   — it drains `masld-bridge/outbox/` (the 3 queued jobs) and writes results to
   `inbox/`; the laptop then ingests them with `cli.py bridge-dispatch`/sync.

## Pull results back
After the notebook finishes, on the laptop:
```
cd ~/masld-llm
# results are on Drive already; copy the new archives locally
rsync -a "$HOME/Library/CloudStorage/GoogleDrive-ami.subhadipbanerjee@gmail.com/My Drive/masld-llm/results/" results/
# then score:
platform/.venv/bin/python platform/cli.py score --archive-dir results/frontier_runs --out-csv results/leaderboard.csv
```

## Notes / honesty
- The **C3a gate already FAILED on the ML arm locally** (n=20, wide CIs). The
  Colab arm adds the LLM zero-shot side, but a bigger blood-proxy cohort is the
  real fix — see the C3 addendum.
- The k-shot run is the **GPU-scale replay** of the 0.6B local ablation; it needs
  1.7B because the BDH-CQ paradigm claim is about in-context demonstration, and
  we want a stronger base to test H1/H2.
