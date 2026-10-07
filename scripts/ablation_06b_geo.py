#!/usr/bin/env python3
"""Geometric ablation: 0.6B-v3 model (raw-only training) evaluated zero-shot
on the geometric test set (MB-40xx).

Completes the 2x2 ablation matrix:
  1.7B trained raw+geo  -> raw: banked | geo: banked
  0.6B-v3 trained raw   -> raw: banked | geo: THIS RUN (never saw geometric prompts)

Local MPS inference, newline-stopped generation, tested parser, archive +
inline scores. ~20-40 min on M2.
"""
import gzip, json, os, random, re, time
import numpy as np
import torch

T0 = time.time()
ROOT = "/Users/subhadipbanerjee/masld-llm"
SEED = 20260929

# --- load base + v3 adapter, merge in memory ---
print("loading Qwen3-0.6B + v3 adapter (MPS)...")
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B", padding_side="left")
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
base = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-0.6B", dtype=torch.float16)
model = PeftModel.from_pretrained(base, f"{ROOT}/checkpoints/qwen3-0.6b-masld-sft")
model = model.merge_and_unload()
model = model.half().to("mps").eval()
print(f"model ready ({time.time()-T0:.0f}s)")

# --- load geometric test set ---
rows = []
with gzip.open(f"{ROOT}/prompts/MB-40xx_geo_test.jsonl.gz", "rt") as f:
    f.readline()
    for line in f:
        rows.append(json.loads(line))
print(f"geometric test prompts: {len(rows)}")

# --- tested parser (same as leaderboard) ---
def parse_answer(text, task):
    raw = (text or "").strip()
    t = raw.lower()
    if task.endswith(("001", "201", "4001")):
        if t.startswith("yes") or "answer: yes" in t or "answer is yes" in t: return "yes"
        if t.startswith("no") or "answer: no" in t or "answer is no" in t: return "no"
        return None
    if task.endswith(("003", "203")):
        if re.search(r"\banswer(?: is|:) a\b", t) or t.startswith("a"): return "A"
        if re.search(r"\banswer(?: is|:) b\b", t) or t.startswith("b"): return "B"
        return None
    if task.endswith(("002", "202", "4002")):
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

# --- generation (newline-stopped, greedy, batched) ---
raws = []
BATCH = 4
i = 0
while i < len(rows):
    batch = rows[i:i+BATCH]
    try:
        enc = tok([r["prompt"] for r in batch], return_tensors="pt",
                  padding=True, truncation=True, max_length=1024).to("mps")
        with torch.no_grad():
            gen = model.generate(**enc, max_new_tokens=30, do_sample=False,
                                 pad_token_id=tok.pad_token_id)
        for j in range(len(batch)):
            text = tok.decode(gen[j][enc["input_ids"].shape[1]:], skip_special_tokens=True)
            raws.append(text.split("\n")[0])
        i += len(batch)
    except Exception as e:
        if BATCH > 1:
            BATCH = max(1, BATCH // 2)
            print(f"  batch error ({str(e)[:50]}) -> batch {BATCH}")
        else:
            raise
    if i % 80 < BATCH:
        print(f"  {i}/{len(rows)} ({time.time()-T0:.0f}s)", flush=True)
print("generation complete")

# --- archive ---
import hashlib
run_path = f"{ROOT}/results/frontier_runs/qwen3-0.6b-masld__MB-40xx.jsonl.gz"
with gzip.open(run_path, "wt") as f:
    for r, raw in zip(rows, raws):
        f.write(json.dumps(dict(task=r["task"], sample=r["sample"], answer=r["answer"],
                                raw=raw, error=None, model_version="qwen3-0.6b-masld-v3-geo-zeroshot",
                                parsed=parse_answer(raw, r["task"]))) + "\n")
print("archived ->", run_path)

# --- inline scores ---
import collections
bt = collections.defaultdict(list)
for r, raw in zip(rows, raws):
    bt[r["task"]].append((parse_answer(raw, r["task"]), r["answer"]))
print("\n=== 0.6B-v3 GEOMETRIC zero-shot (trained raw-only) ===")
results = {}
for t, pairs in sorted(bt.items()):
    n = len(pairs)
    valid = sum(1 for p, g in pairs if p is not None)
    if t in ("MB-4001", "MB-4002"):
        correct = sum(1 for p, g in pairs if p == g)
        results[t] = dict(acc=round(correct/n, 3), validity=round(valid/n, 3))
        emit = collections.Counter(str(p) for p, g in pairs)
        print(f"  {t}: acc={correct/n:.3f} validity={valid/n:.3f} | emits {dict(emit.most_common(3))}")
    else:
        nums = [(p, float(g)) for p, g in pairs if isinstance(p, (int, float))]
        if nums:
            mae = float(np.mean([abs(p-g) for p, g in nums]))
            from scipy.stats import spearmanr
            rho = float(spearmanr([g for p,g in nums],[p for p,g in nums]).statistic)
            results[t] = dict(mae=round(mae,3), rho=round(rho,3), validity=round(valid/n,3))
            print(f"  {t}: mae={mae:.3f} rho={rho:.3f} validity={valid/n:.3f}")
        else:
            results[t] = dict(validity=round(valid/n,3))
            print(f"  {t}: validity={valid/n:.3f} (no parseable)")
json.dump(results, open(f"{ROOT}/results/v3_geo_ablation.json", "w"), indent=1)
print("\nreferences: 1.7B(geo) binary 0.661/multi 0.202/MAE 1.268 | geo-sanity EN 0.679/HGB 0.280/MAE 1.210")
print(f"done in {(time.time()-T0)/60:.1f} min")
