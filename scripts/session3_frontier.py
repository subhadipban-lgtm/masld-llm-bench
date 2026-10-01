#!/usr/bin/env python3
"""Session 3 — frontier bracket runner.

Evaluates frontier LLMs via OpenRouter on the frozen test subsample,
per ANALYSIS_PLAN_v1.md: 300 prompts/task stratified, seed 20260929,
zero-shot greedy single-pass, max 1500 tokens.

Usage:
  OPENROUTER_API_KEY=sk-... python3 session3_frontier.py <openrouter_model_id> [n_per_task]

The key is read from the environment or a .openclaw/tmp/or_key.txt file.
Responses are archived to results/frontier_runs/ with the model version string.
"""
import gzip, json, os, random, re, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed

SEED = 20260929
ROOT = "/Users/subhadipbanerjee/masld-llm"
RUNS = f"{ROOT}/results/frontier_runs"
os.makedirs(RUNS, exist_ok=True)
WORKERS = 6

def get_key():
    k = os.environ.get("OPENROUTER_API_KEY")
    if k:
        return k
    for p in (f"{ROOT}/.or_key", os.path.expanduser("~/.openclaw/tmp/or_key.txt")):
        if os.path.exists(p):
            return open(p).read().strip()
    return None

def parse_answer(text, task):
    t = (text or "").strip().lower()
    if task.endswith(("001", "201")):
        if t.startswith("yes") or "answer: yes" in t or "answer is yes" in t: return "yes"
        if t.startswith("no") or "answer: no" in t or "answer is no" in t: return "no"
        return None
    if task.endswith(("003", "203")):
        if re.search(r"\banswer(?: is|:) a\b", t) or t.startswith("a"): return "A"
        if re.search(r"\banswer(?: is|:) b\b", t) or t.startswith("b"): return "B"
        return None
    m = re.search(r"\bf([0-4])\b", t)
    if m: return f"F{m.group(1)}"
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)", t)
    if m:
        try: return float(m.group(1))
        except ValueError: return None
    return None

def call_openrouter(body_dict, key, retries=4):
    import urllib.request, urllib.error
    body = json.dumps(body_dict).encode()
    last_err = None
    for attempt in range(retries):
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions", data=body,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=240) as resp:
                d = json.loads(resp.read())
                return d["choices"][0]["message"]["content"], d.get("model"), None
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}"
            if e.code == 429:
                ra = e.headers.get("Retry-After")
                wait = float(ra) if ra else 20 * (attempt + 1)
                time.sleep(min(wait, 120))
                continue
            time.sleep(5 * (attempt + 1))
        except Exception as e:
            last_err = str(e)
            time.sleep(5 * (attempt + 1))
    return None, None, last_err


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: session3_frontier.py <openrouter_model_id> [n_per_task]")
    model = sys.argv[1]
    n_per = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    key = get_key()
    if not key:
        sys.exit("no OPENROUTER_API_KEY (env, .or_key, or ~/.openclaw/tmp/or_key.txt)")

    rng = random.Random(SEED)
    rows = []
    with gzip.open(f"{ROOT}/prompts/MB-20xx_liver_test.jsonl.gz", "rt") as f:
        f.readline()
        for line in f:
            rows.append(json.loads(line))
    by_task = {}
    for r in rows:
        by_task.setdefault(r["task"], []).append(r)
    sample = []
    for task, items in sorted(by_task.items()):
        rng.shuffle(items)
        sample.extend(items[:n_per])
    print(f"model={model} n_per_task={n_per} total={len(sample)}", flush=True)

    out_path = f"{RUNS}/{model.replace('/', '__')}__MB-20xx.jsonl.gz"
    done = set()
    if os.path.exists(out_path):
        with gzip.open(out_path, "rt") as f:
            for line in f:
                try:
                    done.add(json.loads(line)["sample"])
                except Exception:
                    pass
    todo = [r for r in sample if r["sample"] not in done]
    print(f"resuming: {len(done)} archived, {len(todo)} to go", flush=True)

    def work(r):
        raw, ver, err = call_openrouter({
            "model": model,
            "messages": [{"role": "user", "content": r["prompt"]}],
            "temperature": 0.0, "top_p": 1.0,
            "max_tokens": 200,
            "reasoning": {"enabled": False},   # reasoning models burn the budget on <think>; disable for direct answers
        }, key)
        return dict(task=r["task"], sample=r["sample"], answer=r["answer"],
                    raw=raw, error=err, model_version=ver,
                    parsed=parse_answer(raw, r["task"]))

    t0 = time.time()
    n_ok = 0
    with gzip.open(out_path, "at") as f, ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(work, r): r for r in todo}
        for i, fut in enumerate(as_completed(futures)):
            rec = fut.result()
            f.write(json.dumps(rec) + "\n")
            if rec["raw"] is not None:
                n_ok += 1
            if (i + 1) % 25 == 0:
                f.flush()
            if (i + 1) % 50 == 0:
                rate = (i + 1) / (time.time() - t0) * 60
                print(f"  {i+1}/{len(todo)} ok={n_ok} ({rate:.0f}/min, {time.time()-t0:.0f}s)", flush=True)
    print(f"archived -> {out_path}", flush=True)


if __name__ == "__main__":
    main()
