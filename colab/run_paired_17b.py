#!/usr/bin/env python3
"""C2 paired-alignment eval for qwen3-1.7b-masld-sft on the frontier frame (GPU).

Self-contained one-cell Colab runner (same protocol as run_maxgpu.py).
Runs the 1.7B adapter on the frontier's EXACT 929-item frame (the same items
as qwen3-0.6b-masld__MB-20xx_PAIRED) and writes the paired archive to
Drive: results/frontier_runs/qwen3-1.7b-masld__MB-20xx_PAIRED.jsonl.gz

Usage (one Colab cell, GPU runtime):
  !python /content/drive/MyDrive/masld-llm/run_paired_17b.py

Inputs staged on Drive:
  prompts/MB-20xx_liver_test.jsonl.gz      (frozen corpus, read-only)
  checkpoints/qwen3-1.7b-masld-sft/        (LoRA adapter on Qwen/Qwen3-1.7B)
The 929 (task, sample) frame keys are embedded below (gzip+base64).
"""
import os, subprocess, sys

if not os.path.exists('/content/drive/MyDrive'):
    from google.colab import drive
    drive.mount('/content/drive')

subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'peft'], check=False)

import base64, collections, gzip, io, json, re, time

SEARCH_ROOTS = ['/content/drive/MyDrive', '/content/drive/Othercomputers/My Mac']

def find_dir(target_name):
    for root in SEARCH_ROOTS:
        direct = os.path.join(root, target_name)
        if os.path.isdir(direct):
            return direct
    return None

MASLD_LLM = find_dir('masld-llm')
assert MASLD_LLM, 'masld-llm not found on Drive'
TEST = os.path.join(MASLD_LLM, 'prompts', 'MB-20xx_liver_test.jsonl.gz')
ADAPTER = os.path.join(MASLD_LLM, 'checkpoints', 'qwen3-1.7b-masld-sft')
OUT = os.path.join(MASLD_LLM, 'results', 'frontier_runs',
                   'qwen3-1.7b-masld__MB-20xx_PAIRED.jsonl.gz')
os.makedirs(os.path.dirname(OUT), exist_ok=True)
print('MASLD_LLM =', MASLD_LLM)
assert os.path.exists(TEST), f'missing corpus: {TEST}'
assert os.path.exists(os.path.join(ADAPTER, 'adapter_model.safetensors')), \
    f'missing adapter: {ADAPTER}'

T0 = time.time()

FRAME_B64 = "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"

keys = json.loads(gzip.decompress(base64.b64decode(FRAME_B64)))
print(f"frame items: {len(keys)}")
print("  by task:", dict(collections.Counter(t for t, _ in keys)))

def load_jsonl(p):
    rows = []
    with gzip.open(p, 'rt') as f:
        for i, line in enumerate(f):
            if i == 0 and '__meta__' in line:
                continue
            rows.append(json.loads(line))
    return rows

test = {}
for r in load_jsonl(TEST):
    test[(r['task'], r['sample'])] = r
print(f"frozen test indexed: {len(test)}")
aligned = [test[tuple(k)] for k in keys if tuple(k) in test]
missing = [k for k in keys if tuple(k) not in test]
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
    m = re.search(r"(-?\d+(?:\.\d+)?)", t)
    if m:
        try: return float(m.group(1))
        except ValueError: return None
    return None

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
assert DEVICE == 'cuda', 'GPU runtime required (Runtime -> Change runtime type -> GPU)'
print(f"device {DEVICE} ({torch.cuda.get_device_name(0)}); loading 1.7B base+adapter (no merge, fp16)...")
tok = AutoTokenizer.from_pretrained('Qwen/Qwen3-1.7B', padding_side='left')
if tok.pad_token is None: tok.pad_token = tok.eos_token
base = AutoModelForCausalLM.from_pretrained('Qwen/Qwen3-1.7B', dtype=torch.float16)
model = PeftModel.from_pretrained(base, ADAPTER)
model = model.half().to(DEVICE).eval()
print(f"model ready ({time.time()-T0:.0f}s)")

# resume sidecar (Drive): one JSON line per finished item
SIDECAR = OUT + '.progress.jsonl'
done_keys = set()
if os.path.exists(SIDECAR):
    with open(SIDECAR) as f:
        for line in f:
            try:
                r = json.loads(line)
                done_keys.add((r['task'], r['sample']))
            except json.JSONDecodeError:
                continue
if done_keys:
    print(f"resuming: {len(done_keys)} items already done")
todo = [r for r in aligned if (r['task'], r['sample']) not in done_keys]

BATCH = 8
raws = {}
sidecar = open(SIDECAR, 'a')
i = 0
while i < len(todo):
    b = todo[i:i+BATCH]
    try:
        enc = tok([r['prompt'] for r in b], return_tensors='pt', padding=True,
                  truncation=True, max_length=4096).to(DEVICE)
        with torch.no_grad():
            gen = model.generate(**enc, max_new_tokens=24, do_sample=False,
                                 pad_token_id=tok.pad_token_id)
        for j, r in enumerate(b):
            txt = tok.decode(gen[j][enc['input_ids'].shape[1]:],
                             skip_special_tokens=True)
            raw = txt.split('\n')[0]
            raws[(r['task'], r['sample'])] = raw
            sidecar.write(json.dumps(dict(task=r['task'], sample=r['sample'],
                                          answer=r['answer'], raw=raw)) + '\n')
        sidecar.flush()
        i += len(b)
    except RuntimeError as e:
        if BATCH > 1 and 'out of memory' in str(e).lower():
            BATCH = max(1, BATCH // 2)
            torch.cuda.empty_cache()
            print(f"  OOM -> BATCH={BATCH}", flush=True)
        else:
            raise
    n_done = len(done_keys) + len(raws)
    if n_done % 40 < BATCH or i >= len(todo):
        print(f"  {n_done}/{len(aligned)} ({time.time()-T0:.0f}s)", flush=True)
sidecar.close()

# merge sidecar history (covers restarts) and write the final archive
with open(SIDECAR) as f:
    for line in f:
        try:
            r = json.loads(line)
            raws.setdefault((r['task'], r['sample']), r['raw'])
        except json.JSONDecodeError:
            continue
with gzip.open(OUT, 'wt') as f:
    for r in aligned:
        raw = raws[(r['task'], r['sample'])]
        f.write(json.dumps(dict(task=r['task'], sample=r['sample'],
                                answer=r['answer'], raw=raw, error=None,
                                model_version='qwen3-1.7b-masld-sft-v4-paired',
                                parsed=parse_answer(raw, r['task']))) + '\n')
os.remove(SIDECAR)

bt = collections.defaultdict(list)
for r in aligned:
    bt[r['task']].append((parse_answer(raws[(r['task'], r['sample'])], r['task']),
                          r['answer']))
print('\n=== PAIRED 1.7B scores ===')
for t, pairs in sorted(bt.items()):
    n = len(pairs); valid = sum(1 for p, g in pairs if p is not None)
    if t in ('MB-2001', 'MB-2002', 'MB-2003'):
        corr = sum(1 for p, g in pairs if p == g)
        print(f'  {t}: acc {corr/n:.3f} val {valid/n:.3f} n={n}')
    else:
        print(f'  {t}: validity {valid/n:.3f} n={n}')
open(OUT + '.DONE', 'w').write(f'{len(aligned)} items, {(time.time()-T0)/60:.1f} min\n')
print(f'\narchived -> {OUT} ({(time.time()-T0)/60:.1f} min)')
