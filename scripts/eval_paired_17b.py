#!/usr/bin/env python3
"""C2 paired-alignment eval for the 1.7B model on the frontier's EXACT items.

Same protocol as eval_paired_06b.py (frame = the 929-item frontier frame),
but memory-lean for the larger model: NO adapter merge, batch=1, base fp16
with the LoRA applied on the fly.

Frame source: the existing qwen3-0.6b-masld__MB-20xx_PAIRED.jsonl.gz archive
(929 items = exact frontier frame; overlap with nemotron = 929).

Model: checkpoints/qwen3-1.7b-masld-sft (adapter) on Qwen/Qwen3-1.7B.

Output: results/frontier_runs/qwen3-1.7b-masld__MB-20xx_PAIRED.jsonl.gz
Device: MPS first; set PAIRED_DEVICE=cpu to force the CPU fallback.
"""
import gzip, json, os, re, time, collections
import torch

T0 = time.time()
ROOT = "/Users/subhadipbanerjee/masld-llm"
FRAME = f"{ROOT}/results/frontier_runs/qwen3-0.6b-masld__MB-20xx_PAIRED.jsonl.gz"
TEST = f"{ROOT}/prompts/MB-20xx_liver_test.jsonl.gz"
OUT = f"{ROOT}/results/frontier_runs/qwen3-1.7b-masld__MB-20xx_PAIRED.jsonl.gz"
BASE = "Qwen/Qwen3-1.7B"
ADAPTER = f"{ROOT}/checkpoints/qwen3-1.7b-masld-sft"

def load_jsonl(p, skip_meta=True):
    rows = []
    with gzip.open(p, "rt") as f:
        for i, line in enumerate(f):
            if skip_meta and i == 0 and "__meta__" in line:
                continue
            rows.append(json.loads(line))
    return rows

# 1. frame (task, sample) keys from the 0.6B PAIRED archive = frontier frame
frame_keys = []
seen = set()
for r in load_jsonl(FRAME):
    key = (r["task"], r["sample"])
    if key not in seen:
        seen.add(key)
        frame_keys.append(key)
print(f"frame items: {len(frame_keys)}")
print("  by task:", dict(collections.Counter(t for t, s in frame_keys)))

# 2. index the frozen test by (task, sample)
test = {}
for r in load_jsonl(TEST):
    test[(r["task"], r["sample"])] = r
print(f"frozen test indexed: {len(test)}")

# 3. build the aligned eval set
aligned = [test[k] for k in frame_keys if k in test]
missing = [k for k in frame_keys if k not in test]
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

# 4. load model (memory-lean: no merge, 16-bit, adapter on the fly)
# bf16 = the checkpoint's native dtype (Qwen3-1.7B ships bf16). Same 2-byte
# footprint as fp16; on this 8GB arm64 box the CPU bf16 GEMM path is
# vectorized while the fp16 path degrades to scalar dot products.
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
DEVICE = os.environ.get("PAIRED_DEVICE") or ("mps" if torch.backends.mps.is_available() else "cpu")
_p = torch.ones(8, device=DEVICE) * 2; _p.sum().item(); del _p
print(f"device {DEVICE}; loading 1.7B base+adapter (no merge, bf16)...")
tok = AutoTokenizer.from_pretrained(BASE, padding_side="left")
if tok.pad_token is None: tok.pad_token = tok.eos_token
base = AutoModelForCausalLM.from_pretrained(BASE, dtype=torch.bfloat16)
model = PeftModel.from_pretrained(base, ADAPTER)
model = model.to(torch.bfloat16).to(DEVICE).eval()
print(f"model ready ({time.time()-T0:.0f}s)")

# 5. generate (left-padded micro-batches; auto-halve on failure like 06b)
# batch=1 keeps MPS memory-lean, but on the CPU fallback the ~1.5k-token
# prefill is GEMV-bound (bandwidth) and this arm64 torch build has no fast
# 16-bit path -> >20 s/item (5+ h). Batching amortizes the weight reads;
# batch=4 is what the 0.6B harness itself used. Memory stays ~5 GB.
raws = []
BATCH = int(os.environ.get("PAIRED_BATCH") or (1 if DEVICE == "mps" else 4))
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
            txt = tok.decode(gen[j][enc["input_ids"].shape[1]:],
                             skip_special_tokens=True)
            raws.append(txt.split("\n")[0])
        i += len(b)
    except Exception:
        if BATCH > 1:
            BATCH = max(1, BATCH // 2)
            print(f"  batch error -> BATCH={BATCH}", flush=True)
        else:
            raise
    if len(raws) >= 50 and (len(raws) % 50 < BATCH or len(raws) == len(aligned)):
        print(f"  {len(raws)}/{len(aligned)} ({time.time()-T0:.0f}s)", flush=True)

# 6. archive
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with gzip.open(OUT, "wt") as f:
    for r, raw in zip(aligned, raws):
        f.write(json.dumps(dict(task=r["task"], sample=r["sample"], answer=r["answer"],
                                raw=raw, error=None,
                                model_version="qwen3-1.7b-masld-sft-v4-paired",
                                parsed=parse_answer(raw, r["task"]))) + "\n")

# 7. quick scores
bt = collections.defaultdict(list)
for r, raw in zip(aligned, raws):
    bt[r["task"]].append((parse_answer(raw, r["task"]), r["answer"]))
print("\n=== PAIRED 1.7B scores ===")
for t, pairs in sorted(bt.items()):
    n = len(pairs); valid = sum(1 for p, g in pairs if p is not None)
    if t in ("MB-2001", "MB-2002", "MB-2003"):
        corr = sum(1 for p, g in pairs if p == g)
        print(f"  {t}: acc {corr/n:.3f} val {valid/n:.3f} n={n}")
    else:
        print(f"  {t}: validity {valid/n:.3f} n={n}")
print(f"\narchived -> {OUT} ({(time.time()-T0)/60:.1f} min)")
