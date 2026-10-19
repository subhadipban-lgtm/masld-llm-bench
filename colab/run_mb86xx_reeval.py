#!/usr/bin/env python3
"""MB-86xx freeze-16 re-evaluation (self-contained Colab script).

Re-runs the four quarantined MB-86xx cells on the CORRECTED corpus
(MANIFEST v3-freeze-16: 21 patients, 8/6/7 grades, 57 records):

  qwen3-0.6b-masld-v5-zeroshot   (base 0.6B + v5 adapter)
  qwen3-0.6b-masld-v6            (base 0.6B + v6 adapter)
  qwen3-1.7b-masld-v5-zeroshot   (base 1.7B + v5 adapter)
  qwen3-1.7b-masld-v6            (base 1.7B + v6 adapter)

The freeze-8 archives scored the mislabeled corpus (header off-by-one in
build_mb86xx.py) and are quarantined; nothing here reads them.

Protocol identical to the platform local_runner: greedy, max_new_tokens=24,
left padding, continuation-only decode, first-line answer, OOM batch-halving.

Safety: verifies MANIFEST version + corpus SHA against Drive BEFORE any
model load — aborts if Drive still holds the pre-correction corpus.

Usage (one Colab cell, any GPU runtime; T4 is plenty — 228 generations):
  !python /content/drive/MyDrive/masld-llm/run_mb86xx_reeval.py
"""
import gc
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
import time

def _sh(cmd):
    print('>>>', cmd, flush=True)
    subprocess.run(cmd, shell=True, check=False)

if not os.path.exists('/content/drive/MyDrive'):
    from google.colab import drive
    drive.mount('/content/drive')

MASLD = '/content/drive/MyDrive/masld-llm'
PROMPTS = os.path.join(MASLD, 'prompts')
RUNS = os.path.join(MASLD, 'results', 'frontier_runs')
CKPT = os.path.join(MASLD, 'checkpoints')
CORPUS = 'MB-86xx_bloodproxy_test.jsonl.gz'
SEED = 20260929

# ---- deps: torchao must go before peft (hosted runtimes ship 0.10) ----
_sh('pip -q install peft transformers accelerate')
import importlib
if importlib.util.find_spec('torchao') is not None:
    subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', 'torchao'], check=False)
print('torchao absent:', importlib.util.find_spec('torchao') is None)

# ---- freeze gate: the Drive corpus must BE the corrected freeze-16 one ----
def sha16(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()[:16]

manifest = json.load(open(os.path.join(PROMPTS, 'MANIFEST.json')))
corpus_path = os.path.join(PROMPTS, CORPUS)
expect_ver = 'v3-freeze-16'
actual_sha = sha16(corpus_path)
assert manifest['version'] == expect_ver, (
    f'Drive MANIFEST is {manifest["version"]}, expected {expect_ver} — '
    'the corrected corpus is not on Drive yet; aborting before wasted GPU time')
assert manifest['files'].get(CORPUS) == actual_sha, (
    f'corpus SHA mismatch: manifest {manifest["files"].get(CORPUS)} vs file '
    f'{actual_sha} — Drive copy is stale; aborting')
assert manifest['counts'].get(CORPUS) == 57, (
    f'expected 57 records (21 patients), manifest says {manifest["counts"].get(CORPUS)}')
print(f'freeze gate OK: {expect_ver}, sha16={actual_sha}, 57 records')

# ---- corpus ----
records = []
with gzip.open(corpus_path, 'rt', encoding='utf-8') as f:
    for line in f:
        r = json.loads(line)
        if '__meta__' in r:
            continue
        records.append(r)
assert len(records) == 57, f'expected 57 records, got {len(records)}'
from collections import Counter
print('tasks:', dict(Counter(r['task'] for r in records)),
      '| patients:', len({r['sample'] for r in records}))

# ---- harness ----
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

MAX_NEW_TOKENS = 24
MAX_LENGTH = 4096

def probe_adapter(d):
    """Drive-FUSE can serve an empty listing for a real dir; force-read it."""
    if not os.path.isdir(d):
        raise SystemExit(f'adapter dir missing: {d}')
    entries = os.listdir(d)
    for attempt in range(3):
        if 'adapter_config.json' in entries:
            json.load(open(os.path.join(d, 'adapter_config.json')))
            print(f'adapter OK: {d} ({len(entries)} entries)')
            return
        print(f'  FUSE listing thin ({len(entries)} entries), retry {attempt + 1}/3...')
        time.sleep(4)
        entries = os.listdir(d)
    raise SystemExit(f'adapter_config.json not readable in {d} (Drive FUSE)')

def parse(text, task):
    raw = (text or '').strip()
    t = raw.lower()
    if task == 'MB-8602':
        if t.startswith('yes') or 'answer: yes' in t or 'answer is yes' in t: return 'yes'
        if t.startswith('no') or 'answer: no' in t or 'answer is no' in t: return 'no'
        return None
    if task == 'MB-8601':
        m = re.search(r'\b(low|medium|high)\b', t)
        return m.group(1) if m else None
    m = re.search(r'(-?\d+(?:\.\d+)?)', t)
    try:
        return float(m.group(1)) if m else None
    except ValueError:
        return None

def evaluate(model, tok, recs, batch=8):
    out, i, t0 = [], 0, time.time()
    while i < len(recs):
        chunk = recs[i:i + batch]
        try:
            enc = tok([r['prompt'] for r in chunk], padding=True, truncation=True,
                      max_length=MAX_LENGTH, return_tensors='pt').to('cuda')
            with torch.no_grad():
                gen = model.generate(**enc, max_new_tokens=MAX_NEW_TOKENS,
                                     do_sample=False, pad_token_id=tok.pad_token_id)
            for j, r in enumerate(chunk):
                text = tok.decode(gen[j][enc['input_ids'].shape[1]:],
                                  skip_special_tokens=True)
                out.append(dict(task=r['task'], sample=r['sample'], answer=r['answer'],
                                raw=text.split('\n')[0].strip(), error=None,
                                model_version=None, parsed=None))
            i += len(chunk)
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            if batch == 1:
                raise
            batch = max(batch // 2, 1)
            print(f'  OOM -> batch {batch}', flush=True)
    print(f'  {len(out)} items in {time.time() - t0:.0f}s', flush=True)
    return out

def summarize(recs, tag):
    by = {}
    for r in recs:
        by.setdefault(r['task'], []).append((parse(r['raw'], r['task']), r['answer']))
    print(f'=== {tag} ===')
    for t, pairs in sorted(by.items()):
        n = len(pairs)
        valid = sum(1 for p, _ in pairs if p is not None)
        gold_num = all(_isfloat(g) for _, g in pairs)
        if gold_num:
            nums = [(float(p), float(g)) for p, g in pairs if isinstance(p, (int, float))]
            mae = sum(abs(p - g) for p, g in nums) / len(nums) if nums else float('nan')
            print(f'  {t}: MAE={mae:.3f} validity={valid / n:.2f} n={n}')
        else:
            print(f'  {t}: acc={sum(1 for p, g in pairs if p == g) / n:.3f} '
                  f'validity={valid / n:.2f} n={n}')

def _isfloat(x):
    try:
        float(x)
        return True
    except (TypeError, ValueError):
        return False

CONFIGS = [
    ('Qwen/Qwen3-0.6B', 'qwen3-0.6b-masld-sft-v5', 'qwen3-0.6b-masld-v5-zeroshot'),
    ('Qwen/Qwen3-0.6B', 'qwen3-0.6b-masld-sft-v6', 'qwen3-0.6b-masld-v6'),
    ('Qwen/Qwen3-1.7B', 'qwen3-1.7b-masld-sft-v5', 'qwen3-1.7b-masld-v5-zeroshot'),
    ('Qwen/Qwen3-1.7B', 'qwen3-1.7b-masld-sft-v6', 'qwen3-1.7b-masld-v6'),
]

for base_id, adapter_name, tag in CONFIGS:
    out_path = os.path.join(RUNS, f'{tag}__MB-86xx.jsonl.gz')
    adapter_dir = os.path.join(CKPT, adapter_name)
    probe_adapter(adapter_dir)
    tok = AutoTokenizer.from_pretrained(base_id, padding_side='left')
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        base_id, torch_dtype=torch.bfloat16, device_map='cuda').eval()
    model = PeftModel.from_pretrained(model, adapter_dir).eval()
    recs = evaluate(model, tok, records, batch=8)
    for r in recs:
        r['model_version'] = tag
        r['parsed'] = parse(r['raw'], r['task'])
    with gzip.open(out_path, 'wt', encoding='utf-8') as f:
        f.write(json.dumps({'__meta__': {
            'n_records': len(recs), 'seed': SEED,
            'built': time.strftime('%Y-%m-%d'),
            'builder': 'colab/run_mb86xx_reeval.py (freeze-16 corrected corpus)',
            'model_version': tag,
            'protocol': 'greedy, max_new_tokens=24, newline-stopped',
        }}) + '\n')
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print('archived ->', out_path)
    summarize(recs, tag)
    del model
    gc.collect()
    torch.cuda.empty_cache()

print('\nMB-86xx FREEZE-16 RE-EVAL COMPLETE — 4 archives in Drive results/frontier_runs/')
