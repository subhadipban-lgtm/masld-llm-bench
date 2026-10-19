#!/usr/bin/env python3
"""Targeted frontier re-pass: re-ask low-validity (model, task) cells with a
larger output budget, then rewrite only those records in the archive.

Why: the first pass capped output at 200 tokens. Verbose models (Claude,
Gemini, Nova, Llama) reason for longer and get truncated before stating a
verdict, so their validity collapses to ~0 on pairwise/numeric tasks. That is
a harness artifact, not a model result. This pass re-asks exactly those cells
with `--max-tokens` and keeps every other record untouched.

Usage:
  python scripts/frontier_repass.py <model> <task,task,...> [max_tokens]
"""
from __future__ import annotations

import gzip
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "results", "frontier_runs")
PROMPTS = os.path.join(ROOT, "prompts")
SEED = 20260929
WORKERS = 8


def get_key() -> str | None:
    k = os.environ.get("OPENROUTER_API_KEY")
    if k:
        return k.strip()
    for p in (os.path.join(ROOT, ".or_key"), os.path.expanduser("~/.openclaw/tmp/or_key.txt")):
        if os.path.exists(p):
            return open(p).read().strip()
    return None


def call(model: str, prompt: str, key: str, max_tokens: int, retries: int = 4):
    import urllib.error
    import urllib.request

    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0, "top_p": 1.0, "max_tokens": max_tokens,
        "reasoning": {"enabled": False},
    }).encode()
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions", data=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.loads(r.read())
            msg = d["choices"][0]["message"].get("content")
            return (msg or ""), d.get("model"), None
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            time.sleep(20 * (attempt + 1) if e.code == 429 else 5 * (attempt + 1))
        except Exception as e:  # noqa: BLE001
            last = str(e)
            time.sleep(5 * (attempt + 1))
    return None, None, last


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    model, tasks = sys.argv[1], set(sys.argv[2].split(","))
    max_tokens = int(sys.argv[3]) if len(sys.argv) > 3 else 900
    key = get_key()
    if not key:
        sys.exit("no OPENROUTER_API_KEY")

    stem = model.replace("/", "__")
    path = os.path.join(RUNS, f"{stem}__MB-20xx.jsonl.gz")
    if not os.path.exists(path):
        sys.exit(f"no archive: {path}")

    with gzip.open(path, "rt") as f:
        records = [json.loads(l) for l in f]
    # Only re-ask what the first pass could not parse: records that already
    # produced a verdict stay untouched (never re-buy a valid answer).
    redo_idx = [
        i for i, r in enumerate(records)
        if r["task"] in tasks and (r.get("parsed") is None or not (r.get("raw") or "").strip())
    ]
    redo = [records[i] for i in redo_idx]
    print(f"{stem}: rewriting {len(redo)} unparsed records across {sorted(tasks)}", flush=True)

    # Prompts come from the frozen corpus, keyed by (task, sample).
    prompts: dict[tuple[str, str], str] = {}
    with gzip.open(os.path.join(PROMPTS, "MB-20xx_liver_test.jsonl.gz"), "rt") as f:
        for line in f:
            r = json.loads(line)
            if "task" in r:
                prompts[(r["task"], r["sample"])] = r["prompt"]

    def work(rec: dict) -> dict:
        p = prompts[(rec["task"], rec["sample"])]
        raw, ver, err = call(model, p, key, max_tokens)
        return dict(rec, raw=raw, error=err, model_version=ver or rec.get("model_version"),
                    parsed=None, _repass=True, _max_tokens=max_tokens)

    done = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(work, r): r for r in redo}
        for i, fut in enumerate(as_completed(futs)):
            done.append(fut.result())
            if (i + 1) % 25 == 0:
                print(f"  {i+1}/{len(redo)} ({time.time()-t0:.0f}s)", flush=True)

    # Splice the re-asked records back into their original positions.
    out = list(records)
    for i, rec in zip(redo_idx, done):
        out[i] = rec
    tmp = path + ".tmp"
    with gzip.open(tmp, "wt") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, path)
    empty = sum(1 for r in done if not (r.get("raw") or "").strip())
    errs = sum(1 for r in done if r.get("error"))
    print(f"rewrote {path}: {len(out)} records, re-pass empty={empty} errors={errs}")


if __name__ == "__main__":
    main()
