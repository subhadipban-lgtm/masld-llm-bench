# MASLD-Bench Platform

Production-grade platform around the [MASLD-LLM](../README.md) research
program: frozen-corpus management, frontier + local model evaluation,
scoring with paired statistics, a live leaderboard, supervised run
orchestration, and a Google Colab Pro / Drive bridge for GPU work.

The research repository is treated as a **read-only data source** (``prompts/``,
``results/frontier_runs/``, ``checkpoints/``); this platform never mutates it.

## Architecture

```
platform/
├── core/masld_platform/    pure typed engines (no HTTP/UI imports)
│   ├── schemas.py          PromptRecord / EvalRecord / LeaderboardRow / RunSpec
│   ├── tasks.py            task-id -> answer-modality registry
│   ├── io_jsonl.py         gzip JSONL I/O + truncated-archive recovery
│   ├── answers.py          ONE consolidated answer parser
│   ├── features.py         prompt -> feature encoders (genes/clinical/manifold)
│   ├── guardrails.py       NaN/inf/boundary/credential validation
│   ├── metrics.py          accuracy / MAE / Spearman / bootstrap CI
│   ├── leaderboard.py      archive scoring -> unified CSV (rho column)
│   ├── paired.py           McNemar exact + Wilcoxon signed-rank
│   ├── manifest.py         MANIFEST.json integrity verification
│   ├── baselines.py        ElasticNet / HGB baseline suite
│   ├── frontier_runner.py  OpenRouter runner (env-only credentials)
│   ├── local_runner.py     HF/PEFT local eval (lazy heavy imports)
│   └── colab_bridge.py     Drive-folder job protocol (outbox/inbox/done)
├── api/masld_api/          FastAPI service (runs, corpora, leaderboard, bridge)
├── agents/masld_agents/    supervisor loop + task registry + notifications
├── persistence/            SQLAlchemy 2.0 models + hash-chained audit log
├── frontend/               Next.js dashboard (leaderboard / runs / corpora)
├── infra/                  Dockerfiles, docker-compose, Colab bridge notebook
└── tests/                  pytest suite (unit + API end-to-end)
```

## Multi-domain by configuration (benchmark profiles)

The domain vocabulary lives in a YAML **profile** (`profiles/masld.yaml`);
everything else — orchestration, scoring, paired statistics, leaderboard,
dashboard, bridge — is domain-free. To repoint the platform at a different
benchmark:

1. Copy `profiles/example-generic.yaml`, define your answer types (built-ins:
   `yes_no`, `letter`, `number`; plus any `categorical` type with a pattern
   and token set) and your task registry.
2. Point your corpora at a root with `prompts/*.jsonl.gz` in the record
   format `{task, split, sample, source, prompt, answer}` (answers as strings).
3. Activate: `export MASLD_PROFILE=/path/to/profile.yaml` (CLI, API and
   dashboard all pick it up; `masld profile` prints what's live).

Feature encoders for baselines are equally pluggable
(`masld_platform.features.register_extractor`). The MASLD profile reproduces
the frozen research registry exactly — the rescored leaderboard is
byte-identical before and after the genericization.

## What this architecture is suitable for

**Strong fit (designed for):**

| Work type | Why it fits |
|---|---|
| Benchmark / evaluation platforms over frozen corpora | Prompt-in / short-answer-out eval with stratified sampling, resume, validity tracking. |
| Model comparison studies (frontier APIs + local fine-tunes) | One runner contract for OpenRouter and HF/PEFT; unified archives; leaderboards with bootstrap CIs. |
| Paired significance testing | McNemar exact + Wilcoxon on aligned items — the machinery that made the C2 audit possible. |
| Regulated / audited ML workflows | Append-only hash-chained audit log, frozen-data integrity verification (counts + checksums), guardrails that fail loudly on NaN/inf/OOD inputs. |
| Hybrid laptop + remote-GPU automation | File-based Colab/Drive bridge, supervisor with stall detection and bounded retries — no cloud lock-in, no inbound ports. |
| Reproducible research pipelines | Seeded everywhere (sampling, bootstrap), stateless engines, immutable inputs. |

**Adaptable with modest extension:**

- **New answer modalities** — a profile `categorical` type is data; a truly new
  kind (e.g. ranked lists) is one parser + one metric branch.
- **LLM-judged or similarity-scored evals** — add metric families next to
  accuracy/MAE/rho in `metrics.py` + `leaderboard.py`.
- **Non-text features for baselines** — implement the `FeatureExtractor`
  protocol and register it.
- **Multi-benchmark hosting** — profiles are swappable per process; per-request
  profile selection is a small API addition.

**Poor fit (wrong tool):**

- Real-time / streaming inference serving (stateless batch evaluation, not a
  model server; use vLLM/Triton for serving).
- High-QPS transactional backends (SQLite-defaulted, audit-append-heavy by
  design; this is rigor, not throughput).
- Long-form free-text generation evals without adding judge/similarity
  metrics (the metric layer is accuracy/MAE/Spearman today).
- Multimodal (image/audio) benchmarks — records are text prompts end-to-end.
- Distributed multi-node training orchestration (Kubernetes/Ray territory;
  the bridge covers one-laptop-plus-Colab, not clusters).
- Per-user consumer products (no authn/authz, no user model — intentional).

## Quickstart (laptop)

```bash
cd platform
make setup                     # venv + editable install ([api,dev] extras)
cp .env.example .env           # fill in what you need (see table below)
make test                      # full pytest suite
make api                       # http://127.0.0.1:8000 (docs at /docs)
make frontend                  # http://localhost:3000 dashboard
```

CLI (installed as ``masld``, or ``python cli.py``):

```bash
masld verify-manifest                  # prove frozen corpora integrity
masld score                            # rescore all archives -> leaderboard
masld paired-stats CANDIDATE_STEM --reference REF_STEM
masld run-frontier deepseek/deepseek-chat --n-per-task 300
masld run-local ../checkpoints/qwen3-0.6b-masld-sft   # needs [local-model]
masld baseline --feature-mode genes
masld agent                            # supervisor daemon (autopilot)
masld serve                            # same as `make api`
```

## Configuration (env only — never commit secrets)

| Variable | Purpose |
|---|---|
| `MASLD_ROOT` | Research repo root (default: this repo). |
| `OPENROUTER_API_KEY` | Frontier runs. **Required** for `run-frontier`. |
| `DRIVE_SYNC_DIR` | Google Drive for Desktop folder → Colab bridge. |
| `NGROK_AUTHTOKEN` | Optional direct Colab→laptop HTTP tunnel. |
| `HUGGINGFACE_TOKEN` | Optional (Qwen weights are public). |
| `MASLD_DB_URL` | Default SQLite under `platform/data/`; Postgres in compose. |
| `MASLD_DEVICE` | Force `cpu`/`mps`/`cuda` for local eval. |

## Colab Pro / Drive bridge

Colab has no headless start API; the official unattended path is the **Pro+
scheduler** running `infra/colab/bridge_worker.ipynb`. The platform talks to
it through the Drive-synced folder (no API keys):

1. `masld bridge-dispatch eval_local '{"adapter_path": "...", "corpus": "..."}'`
   writes `outbox/<job_id>.json`.
2. The scheduled notebook polls the outbox, runs the job on Colab GPU, writes
   the archive to `inbox/`.
3. `masld agent` (or `masld bridge-sync`) ingests results, scores them,
   audits and notifies.

## Security & quality mandates

* Credentials via environment variables only; no plaintext-file fallbacks;
  secrets are `SecretStr` and never logged.
* Guardrails reject NaN/inf/out-of-distribution inputs, malformed records,
  missing data, and underpowered samples (HTTP 400 with a clear message).
* Core engines are stateless; all state lives in the DB with an append-only,
  hash-chained audit log (`verify_audit_chain` detects tampering).
* Research artifacts are consumed in place and never modified.

## Docker

```bash
make docker   # api + postgres + frontend via infra/docker-compose.yml
```

Local-model (torch) evaluation intentionally stays OUT of the container —
run it on the host (or Colab via the bridge) with `pip install -e '.[local-model]'`.
