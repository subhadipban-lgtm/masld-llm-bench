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

SEED = 20260929
ROOT = "/Users/subhadipbanerjee/masld-llm"
RUNS = f"{ROOT}/results/frontier_runs"
os.makedirs(RUNS, exist_ok=True)

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

def main():
    if len(sys.argv) < 2:
        sys.exit("usage: session3_frontier.py <openrouter_model_id> [n_per_task]")
    model = sys.argv[1]
    n_per = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    key = get_key()
    if not key:
        sys.exit("no OPENROUTER_API_KEY (env, .or_key, or ~/.openclaw/tmp/or_key.txt)")

    import urllib.request
    rng = random.Random(SEED)

    # load + stratified subsample per task
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
    print(f"model={model} n_per_task={n_per} total={len(sample)}")

    out_path = f"{RUNS}/{model.replace('/', '__')}__MB-20xx.jsonl.gz"
    done = set()
    if os.path.exists(out_path):
        with gzip.open(out_path, "rt") as f:
            for line in f:
                try:
                    done.add(json.loads(line)["sample"])
                except Exception:
                    pass
    print(f"resuming: {len(done)} already archived")

    t0 = time.time()
    with gzip.open(out_path, "at") as f:
        for i, r in enumerate(sample):
            if r["sample"] in done:
                continue
            body = json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": r["prompt"]}],
                "temperature": 0.0, "top_p": 1.0, "max_tokens": 1500,
            }).encode()
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions", data=body,
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json"})
            raw, err = None, None
            for attempt in range(3):
                try:
                    with urllib.request.urlopen(req, timeout=180) as resp:
                        d = json.loads(resp.read())
                        raw = d["choices"][0]["message"]["content"]
                        model_ver = d.get("model", model)
                        break
                except Exception as e:
                    err = str(e); time.sleep(3 * (attempt + 1))
            rec = dict(task=r["task"], sample=r["sample"], answer=r["answer"],
                       raw=raw, error=err, model_version=model_ver if raw else None,
                       parsed=parse_answer(raw, r["task"]))
            f.write(json.dumps(rec) + "\n")
            if (i + 1) % 25 == 0:
                print(f"  {i+1}/{len(sample)} ({time.time()-t0:.0f}s)")
    print(f"archived -> {out_path}")

if __name__ == "__main__":
    main()
