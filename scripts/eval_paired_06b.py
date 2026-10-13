#!/usr/bin/env python3
"""C2 paired-alignment eval: run 0.6B-v3 on the frontier bracket's EXACT items.

Why: the compact model's eval draw overlapped the frontier's by only 10/300
on MB-2003 -> the C2 headline was an UNPAIRED comparison (two-proportion only).
Re-running on the same items makes every C2 contrast paired -> McNemar exact /
Wilcoxon signed-rank become available (analysis plan sec.8).

Output: results/frontier_runs/qwen3-0.6b-masld__MB-20xx_PAIRED.jsonl.gz
"""
import gzip, json, os, re, time, collections
import numpy as np
import torch

T0 = time.time()
ROOT = "/Users/subhadipbanerjee/masld-llm"
REF = f"{ROOT}/results/frontier_runs/nvidia__nemotron-3-super-120b-a12b:free__MB-20xx.jsonl.gz"
TEST = f"{ROOT}/prompts/MB-20xx_liver_test.jsonl.gz"
OUT = f"{ROOT}/results/frontier_runs/qwen3-0.6b-masld__MB-20xx_PAIRED.jsonl.gz"

def load_jsonl(p, skip_meta=True):
    rows = []
    with gzip.open(p, "rt") as f:
        for i, line in enumerate(f):
            if skip_meta and i == 0 and "__meta__" in line:
                continue
            rows.append(json.loads(line))
    return rows

# 1. reference item list (task, sample) from the frontier archive
ref_items = []
seen = set()
for r in load_jsonl(REF):
    if r.get("error") is None and r.get("parsed") is not None:
        key = (r["task"], r["sample"])
        if key not in seen:
            seen.add(key)
            ref_items.append(key)
print(f"frontier items: {len(ref_items)}")
print("  by task:", dict(collections.Counter(t for t, s in ref_items)))

# 2. index the frozen test by (task, sample)
test = {}
for r in load_jsonl(TEST):
    test[(r["task"], r["sample"])] = r
print(f"frozen test indexed: {len(test)}")

# 3. build the aligned eval set
aligned = [test[k] for k in ref_items if k in test]
missing = [k for k in ref_items if k not in test]
print(f"aligned eval set: {len(aligned)} (missing {len(missing)})")

def parse_answer(text, task):
    raw = (text or "").strip()
    t = raw.lower()
    if task.endswith("2001"):
        if t.startswith("yes") or "answer: yes" in t or "answer is yes" in t: return "yes"
        if t.startswith("no") or "answer: no" in t or "answer is no" in t: return "no"
        return None
    if task.endswith("2002"):
        m = re.search(r"F([0-4])", raw)
        if m: return f"F{m.group(1)}"
        m = re.search(r"f([0-4])", t)
        return f"F{m.group(1)}" if m else None
    if task.endswith("2003"):
        m = re.match(r"\s*([ABab])\b", raw)
        return m.group(1).upper() if m else None
    # numeric (2005/2006)
    m = re.search(r"(-?\d+(?:\.\d+)?)", t)
    if m:
        try: return float(m.group(1))
        except ValueError: return None
    return None

if os.environ.get("PAIRED_SKIP_MODEL") == "1":
    print("PAIRED_SKIP_MODEL=1 -> item prep only"); raise SystemExit

# 4. load model
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
DEVICE = os.environ.get("PAIRED_DEVICE") or ("mps" if torch.backends.mps.is_available() else "cpu")
_p = torch.ones(8, device=DEVICE) * 2; _p.sum().item(); del _p
print(f"device {DEVICE}; loading 0.6B-v3...")
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B", padding_side="left")
if tok.pad_token is None: tok.pad_token = tok.eos_token
base = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-0.6B", dtype=torch.float16)
model = PeftModel.from_pretrained(base, f"{ROOT}/checkpoints/qwen3-0.6b-masld-sft")
model = model.merge_and_unload()
model = model.half().to(DEVICE).eval()
print(f"model ready ({time.time()-T0:.0f}s)")

# 5. generate
raws = []
BATCH = 4
i = 0
while i < len(aligned):
    b = aligned[i:i+BATCH]
    try:
        enc = tok([r["prompt"] for r in b], return_tensors="pt", padding=True,
                  truncation=True, max_length=4096).to(DEVICE)
        with torch.no_grad():
            gen = model.generate(**enc, max_new_tokens=24, do_sample=False,
                                 pad_token_id=tok.pad_token_id)
        for j in range(len(b)):
            txt = tok.decode(gen[j][enc["input_ids"].shape[1]:], skip_special_tokens=True)
            raws.append(txt.split("\n")[0])
        i += len(b)
    except Exception as e:
        if BATCH > 1:
            BATCH = max(1, BATCH // 2)
        else:
            raise

# 6. archive
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with gzip.open(OUT, "wt") as f:
    for r, raw in zip(aligned, raws):
        f.write(json.dumps(dict(task=r["task"], sample=r["sample"], answer=r["answer"],
                                raw=raw, error=None,
                                model_version="qwen3-0.6b-masld-sft-v3-paired",
                                parsed=parse_answer(raw, r["task"]))) + "\n")

# 7. quick scores
bt = collections.defaultdict(list)
for r, raw in zip(aligned, raws):
    bt[r["task"]].append((parse_answer(raw, r["task"]), r["answer"]))
print("\n=== PAIRED 0.6B-v3 scores ===")
for t, pairs in sorted(bt.items()):
    n = len(pairs); valid = sum(1 for p, g in pairs if p is not None)
    if t in ("MB-2001", "MB-2002", "MB-2003"):
        corr = sum(1 for p, g in pairs if p == g)
        print(f"  {t}: acc {corr/n:.3f} val {valid/n:.3f} n={n}")
    else:
        print(f"  {t}: validity {valid/n:.3f} n={n}")
print(f"\narchived -> {OUT} ({(time.time()-T0)/60:.1f} min)")
