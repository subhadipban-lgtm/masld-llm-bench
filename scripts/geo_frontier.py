#!/usr/bin/env python3
"""Frontier bracket on MB-40xx (geometric, 354-char prompts).
Short prompts should clear the 402 pre-auth walls -> full roster coverage."""
import gzip, json, os, random, re, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

SEED = 20260929
ROOT = "/Users/subhadipbanerjee/masld-llm"
RUNS = f"{ROOT}/results/frontier_runs"
LOG = f"{ROOT}/logs/geo_bracket.log"

def get_key():
    k = os.environ.get("OPENROUTER_API_KEY")
    if k: return k
    p = os.path.expanduser("~/.openclaw/tmp/or_key.txt")
    return open(p).read().strip() if os.path.exists(p) else None

def parse_answer(text, task):
    raw = (text or "").strip()
    t = raw.lower()
    if task.endswith("01"):
        if t.startswith("yes") or "answer: yes" in t or "answer is yes" in t: return "yes"
        if t.startswith("no") or "answer: no" in t or "answer is no" in t: return "no"
        return None
    if task.endswith("02"):
        m = re.search(r"F([0-4])", raw)
        if m: return f"F{m.group(1)}"
        m = re.search(r"f([0-4])", t)
        return f"F{m.group(1)}" if m else None
    m = re.search(r"[Ff]([0-4])\b", raw)
    if m: return f"F{m.group(1)}"
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)", t)
    if m:
        try: return float(m.group(1))
        except ValueError: return None
    return None

def log(msg):
    with open(LOG, "a") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    print(msg, flush=True)

def call(body, key, retries=4):
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    last = None
    for a in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.loads(r.read())
                return d["choices"][0]["message"]["content"], d.get("model"), None
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code == 429:
                ra = e.headers.get("Retry-After")
                time.sleep(min(float(ra) if ra else 20*(a+1), 120)); continue
            time.sleep(5*(a+1))
        except Exception as e:
            last = str(e); time.sleep(5*(a+1))
    return None, None, last

def main():
    key = get_key()
    assert key, "no key"
    rows = []
    with gzip.open(f"{ROOT}/prompts/MB-40xx_geo_test.jsonl.gz", "rt") as f:
        f.readline()
        for line in f:
            rows.append(json.loads(line))
    by_task = {}
    for r in rows:
        by_task.setdefault(r["task"], []).append(r)
    sample = []
    rng = random.Random(SEED)
    for task, items in sorted(by_task.items()):
        rng.shuffle(items)
        sample.extend(items[:300])   # 168 x 3 = 504 total
    log(f"geometric eval set: {len(sample)} prompts (all of them)")

    models = ["deepseek/deepseek-chat", "nvidia/nemotron-3-super-120b-a12b:free",
              "google/gemini-2.5-pro", "qwen/qwen3-235b-a22b",
              "moonshotai/kimi-k3", "minimax/minimax-m3"]
    for model in models:
        out_path = f"{RUNS}/{model.replace('/', '__')}__MB-40xx.jsonl.gz"
        done = set()
        if os.path.exists(out_path):
            with gzip.open(out_path, "rt") as f:
                for line in f:
                    try:
                        r = json.loads(line)
                        if r.get("raw") is not None:
                            done.add(f"{r['task']}:{r['sample']}")
                    except: pass
        todo = [r for r in sample if f"{r['task']}:{r['sample']}" not in done]
        log(f"{model}: {len(todo)} to go")
        if not todo: continue

        def work(r):
            raw, ver, err = call({"model": model,
                "messages": [{"role": "user", "content": r["prompt"]}],
                "temperature": 0.0, "top_p": 1.0, "max_tokens": 200,
                "reasoning": {"enabled": False}}, key)
            return dict(task=r["task"], sample=r["sample"], answer=r["answer"],
                        raw=raw, error=err, model_version=ver,
                        parsed=parse_answer(raw, r["task"]))
        t0 = time.time(); n_ok = 0
        with gzip.open(out_path, "at") as f, ThreadPoolExecutor(max_workers=6) as ex:
            futs = {ex.submit(work, r): r for r in todo}
            for i, fut in enumerate(as_completed(futs)):
                rec = fut.result()
                f.write(json.dumps(rec) + "\n")
                if rec["raw"] is not None: n_ok += 1
                if (i+1) % 25 == 0: f.flush()
                if (i+1) % 100 == 0:
                    log(f"  {model} {i+1}/{len(todo)} ok={n_ok} ({(i+1)/(time.time()-t0)*60:.0f}/min)")
        log(f"{model} DONE: {n_ok}/{len(todo)} ok")

if __name__ == "__main__":
    main()
