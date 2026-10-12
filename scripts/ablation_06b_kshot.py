#!/usr/bin/env python3
"""Evaluate 0.6B-v3 on the K-shot geometric variants (BDH-CQ paradigm test).

Local MPS, fp16. One archive per variant. Prints the full comparison table.
"""
import gzip, json, os, re, time
import numpy as np
import torch

T0 = time.time()
ROOT = "/Users/subhadipbanerjee/masld-llm"

VARIANTS = [
    ("MB-40xx_geo_kshot2_balanced_test.jsonl.gz", "K=2 balanced"),
    ("MB-40xx_geo_kshot4_balanced_test.jsonl.gz", "K=4 balanced"),
    ("MB-40xx_geo_kshot8_balanced_test.jsonl.gz", "K=8 balanced"),
    ("MB-40xx_geo_kshot4_random_test.jsonl.gz",   "K=4 random"),
]

def parse_answer(text, task):
    raw = (text or "").strip()
    t = raw.lower()
    if task.endswith(("4001", "001")):
        if t.startswith("yes") or "answer: yes" in t or "answer is yes" in t: return "yes"
        if t.startswith("no") or "answer: no" in t or "answer is no" in t: return "no"
        return None
    if task.endswith(("4002", "002")):
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

import os
DEVICE = "mps" if os.environ.get("KSHOT_DEVICE", "mps") == "mps" and torch.backends.mps.is_available() else "cpu"
if DEVICE == "mps":
    # MPS sanity probe: a tiny op with a sync. If the Metal stream is wedged,
    # this hangs -> user should retry with KSHOT_DEVICE=cpu
    _probe = torch.ones(8, device="mps") * 2
    _ = _probe.sum().item()   # forces sync
    del _probe
    print("MPS probe OK")
print(f"loading model (fp16 {DEVICE})...")
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B", padding_side="left")
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
base = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-0.6B", dtype=torch.float16)
model = PeftModel.from_pretrained(base, f"{ROOT}/checkpoints/qwen3-0.6b-masld-sft")
model = model.merge_and_unload()
model = model.half().to(DEVICE).eval()
print(f"model ready on {DEVICE} ({time.time()-T0:.0f}s)")

def load_jsonl(p):
    rows = []
    with gzip.open(p, "rt") as f:
        f.readline()
        for line in f:
            rows.append(json.loads(line))
    return rows

def evaluate(rows, tag):
    raws = []
    BATCH = 4
    i = 0
    while i < len(rows):
        batch = rows[i:i+BATCH]
        try:
            enc = tok([r["prompt"] for r in batch], return_tensors="pt",
                      padding=True, truncation=True, max_length=4096).to(DEVICE)
            with torch.no_grad():
                gen = model.generate(**enc, max_new_tokens=30, do_sample=False,
                                     pad_token_id=tok.pad_token_id)
            for j in range(len(batch)):
                text = tok.decode(gen[j][enc["input_ids"].shape[1]:], skip_special_tokens=True)
                raws.append(text.split("\n")[0])
            i += len(batch)
        except Exception:
            if BATCH > 1:
                BATCH = max(1, BATCH // 2)
            else:
                raise
    import collections
    bt = collections.defaultdict(list)
    for r, raw in zip(rows, raws):
        bt[r["task"]].append((parse_answer(raw, r["task"]), r["answer"]))
    out = {}
    for t, pairs in sorted(bt.items()):
        n = len(pairs)
        valid = sum(1 for p, g in pairs if p is not None)
        if t in ("MB-4001", "MB-4002"):
            correct = sum(1 for p, g in pairs if p == g)
            emit = collections.Counter(str(p) for p, g in pairs)
            out[t] = dict(acc=round(correct/n, 3), validity=round(valid/n, 3),
                          emits=dict(emit.most_common(3)))
        else:
            nums = [(p, float(g)) for p, g in pairs if isinstance(p, (int, float))]
            if nums:
                mae = float(np.mean([abs(p-g) for p, g in nums]))
                from scipy.stats import spearmanr
                rho = float(spearmanr([g for p,g in nums],[p for p,g in nums]).statistic)
                out[t] = dict(mae=round(mae, 3), rho=round(rho, 3), validity=round(valid/n, 3))
            else:
                out[t] = dict(validity=round(valid/n, 3))
    return out, raws

results = {}
for fn, tag in VARIANTS:
    path = f"{ROOT}/prompts/{fn}"
    if not os.path.exists(path):
        print(f"skip {fn} (missing)")
        continue
    rows = load_jsonl(path)
    t0 = time.time()
    scores, raws = evaluate(rows, tag)
    results[tag] = scores
    # archive
    run_name = fn.replace("_test.jsonl.gz", "")
    out_path = f"{ROOT}/results/frontier_runs/qwen3-0.6b-masld__{run_name}.jsonl.gz"
    with gzip.open(out_path, "wt") as f:
        for r, raw in zip(rows, raws):
            f.write(json.dumps(dict(task=r["task"], sample=r["sample"], answer=r["answer"],
                                    raw=raw, error=None,
                                    model_version=f"qwen3-0.6b-v3-{tag.replace(' ', '-')}",
                                    parsed=parse_answer(raw, r["task"]))) + "\n")
    print(f"\n=== {tag} ({time.time()-t0:.0f}s) ===")
    for t, s in scores.items():
        print(f"  {t}: {json.dumps(s)}")

print("\n=== SUMMARY: 0.6B-v3 on geometric prompts ===")
print("%-16s %22s %26s %18s" % ("variant", "binary", "multiclass", "regression"))
print("%-16s %22s %26s %18s" % ("zero-shot", "acc 0.000 val 0.000", "acc 0.220 (all F1)", "MAE 5.024 rho 0.011"))
for tag in ["K=2 balanced", "K=4 balanced", "K=8 balanced", "K=4 random"]:
    if tag not in results: continue
    s = results[tag]
    b = s.get("MB-4001", {})
    m = s.get("MB-4002", {})
    r_ = s.get("MB-4005", {})
    bs = "acc %s val %s" % (b.get('acc','-'), b.get('validity','-'))
    ms = "acc %s emits %s" % (m.get('acc','-'), list(m.get('emits',{}).keys())[:2])
    rs = "MAE %s rho %s" % (r_.get('mae','-'), r_.get('rho','-'))
    print("%-16s %22s %26s %18s" % (tag, bs, ms, rs))
json.dump(results, open(f"{ROOT}/results/kshot_ablation.json", "w"), indent=1)
print(f"\ndone in {(time.time()-T0)/60:.1f} min")
