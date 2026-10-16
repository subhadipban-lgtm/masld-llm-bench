#!/usr/bin/env python3
"""MASLD-LLM maximum-GPU runner (self-contained).
Auto-generated from colab/05_maxgpu_runall.ipynb.
Run inside Colab after: Runtime -> Change runtime type -> GPU.
Usage (one Colab cell):
  !python /content/drive/MyDrive/masld-llm/run_maxgpu.py
"""
import os, subprocess, sys
def _sh(cmd):
    print(">>>", cmd, flush=True)
    subprocess.run(cmd, shell=True, check=False)

if not os.path.exists('/content/drive/MyDrive'):
    from google.colab import drive
    drive.mount('/content/drive')
import os, glob, json, gzip, time, subprocess, sys

SEARCH_ROOTS = ['/content/drive/Othercomputers/My Mac', '/content/drive/MyDrive']

def find_dir(target_name, search_roots=None, depth=6):
    if search_roots is None: search_roots = SEARCH_ROOTS
    matches = []
    for root in search_roots:
        direct = os.path.join(root, target_name)
        if os.path.isdir(direct): matches.append(direct)
    if matches: return matches
    def walk(path, d):
        if d > depth: return
        try:
            for entry in os.scandir(path):
                if entry.is_dir(follow_symlinks=False):
                    if entry.name == target_name: matches.append(entry.path)
                    walk(entry.path, d + 1)
        except (PermissionError, OSError): pass
    for root in search_roots:
        if os.path.exists(root): walk(root, 0)
    return matches

cands = find_dir('masld-llm')
MASLD_LLM = min(cands, key=len) if cands else None
assert MASLD_LLM, 'masld-llm not found under Othercomputers/My Mac or MyDrive'
PROMPTS  = os.path.join(MASLD_LLM, 'prompts')
RESULTS  = os.path.join(MASLD_LLM, 'results')
RUNS_DIR = os.path.join(RESULTS, 'frontier_runs')
CKPT     = os.path.join(MASLD_LLM, 'checkpoints')
for d in (RESULTS, RUNS_DIR, CKPT): os.makedirs(d, exist_ok=True)
print('MASLD_LLM =', MASLD_LLM)
print('corpora   =', sorted(f for f in os.listdir(PROMPTS) if f.endswith('.jsonl.gz')))
assert os.access(RESULTS, os.W_OK), 'Drive results/ not writable'


# ---- cell boundary ----

_sh("cd /content && (git clone --depth 1 https://github.com/hiyouga/LLaMA-Factory.git 2>/dev/null || echo 'already cloned')")
_sh("cd /content/LLaMA-Factory && pip -q install -e '.[torch,metrics]' bitsandbytes peft transformers accelerate liger-kernel")
# torchao must be ABSENT (peft LoRA dispatch breaks on torchao-quantized linears)
import importlib, subprocess, sys
if importlib.util.find_spec('torchao') is not None:
    subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', 'torchao'], check=False)
print('deps ok; torchao absent:', importlib.util.find_spec('torchao') is None)


# ---- cell boundary ----

def to_alpaca(in_path, out_path):
    if not os.path.exists(in_path):
        print('MISSING corpus:', os.path.basename(in_path), '->', os.path.basename(out_path)); return
    rows = []
    with gzip.open(in_path, 'rt') as f:
        first = json.loads(f.readline())
        if '__meta__' not in first: rows.append(first)
        for l in f: rows.append(json.loads(l))
    out = [dict(instruction=r['prompt'], output=str(r['answer'])) for r in rows]
    json.dump(out, open(out_path, 'w'), indent=0)
    print(os.path.basename(out_path), len(out))

to_alpaca(f'{PROMPTS}/MB-10xx_liver_train.jsonl.gz',      '/content/sft_liver.json')
to_alpaca(f'{PROMPTS}/MB-11xx_external_train.jsonl.gz',   '/content/sft_external.json')
to_alpaca(f'{PROMPTS}/MB-61xx_msigdb_train.jsonl.gz',     '/content/sft_knowledge.json')
to_alpaca(f'{PROMPTS}/MB-62xx_drugs_train.jsonl.gz',      '/content/sft_drugs.json')
to_alpaca(f'{PROMPTS}/MB-63xx_drugcentral_affinity_train.jsonl.gz', '/content/sft_drugs2.json')
to_alpaca(f'{PROMPTS}/MB-70xx_dge_direction_train.jsonl.gz', '/content/sft_dge.json')
to_alpaca(f'{PROMPTS}/MB-8xxx_fujiwara_train.jsonl.gz',   '/content/sft_fujiwara.json')
to_alpaca(f'{PROMPTS}/MB-30xx_dnam_train.jsonl.gz',       '/content/sft_dnam.json')


# ---- cell boundary ----

import random
rs = random.Random(20260929)
def load(p): return json.load(open(p)) if os.path.exists(p) else []

liver = load('/content/sft_liver.json'); external = load('/content/sft_external.json')
fujiwara = load('/content/sft_fujiwara.json'); knowledge = load('/content/sft_knowledge.json')
dge = load('/content/sft_dge.json'); drugs1 = load('/content/sft_drugs.json')
drugs2 = load('/content/sft_drugs2.json'); dnam = load('/content/sft_dnam.json')

def is_pairwise(ex): return 'Patient A:' in ex['instruction']
liver_single = [e for e in liver if not is_pairwise(e)]
liver_pair   = [e for e in liver if is_pairwise(e)]
ext_single   = [e for e in external if not is_pairwise(e)]
ext_pair     = [e for e in external if is_pairwise(e)]

STAGE_W = {'F0': 2, 'F1': 1, 'F2': 2, 'F3': 2, 'F4': 7}
def task_kind(ex):
    q = ex['instruction']
    if 'Assign the fibrosis stage' in q or 'Which fibrosis stage' in q: return 'multi'
    if 'advanced fibrosis' in q: return 'binary'
    if 'NAFLD Activity Score' in q or 'exact NAS' in q: return 'nas'
    if 'age in years' in q or 'chronological age' in q: return 'age'
    return 'fibreg'
def liver_weight(ex):
    k = task_kind(ex)
    if k == 'multi':  return STAGE_W.get(str(ex['output']).strip(), 1)
    if k == 'binary': return 3 if str(ex['output']).strip().lower() == 'yes' else 1
    if k == 'nas':    return 3
    return 1
def upsample_weighted(rows, base, wfn):
    out = []
    for e in rows: out += [e] * max(1, int(base * wfn(e)))
    return out

liver_single_up = upsample_weighted(liver_single, 8, liver_weight)
fujiwara_up = list(fujiwara) * 8
dnam_up = list(dnam) * 20 if dnam else []
single = liver_single_up + ext_single + fujiwara_up + dnam_up
pair   = liver_pair + ext_pair
drugs  = rs.sample(drugs1 + drugs2, 10000)
know   = rs.sample(knowledge + dge, 8000)

geo = []
gp = os.path.join(PROMPTS, 'MB-40xx_geo_train.jsonl.gz')
if os.path.exists(gp):
    with gzip.open(gp, 'rt') as f:
        f.readline()
        for l in f:
            r = json.loads(l); geo.append(dict(instruction=r['prompt'], output=str(r['answer'])))
geo_up = geo * 6 if geo else []

mixture = single + pair + drugs + know + geo_up
rs.shuffle(mixture)
json.dump(mixture, open('/content/sft_multitask_v5.json', 'w'), indent=0)
print(f'single {len(single)} | pair {len(pair)} | drugs {len(drugs)} | know {len(know)} | geo {len(geo_up)}')
print('FINAL v5 MIXTURE:', len(mixture))


# ---- cell boundary ----

import subprocess, sys, os, json
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
try:
    import torch, gc; gc.collect(); torch.cuda.empty_cache()
    free, total = torch.cuda.mem_get_info(); print(f'GPU free {free/1e9:.1f}/{total/1e9:.1f} GiB')
except Exception as e: print('(no torch)', e)

ds_entry = json.dumps({'masld_sft_v5': {'file_name': '/content/sft_multitask_v5.json',
                                        'columns': {'prompt': 'instruction', 'response': 'output'}}})
open('/content/LLaMA-Factory/data/dataset_info.json', 'w').write(ds_entry)

# T4 (compute capability 7.5) has no native bf16 -> fp16; Ampere+ keeps bf16
import torch as _t
try:
    _major, _minor = _t.cuda.get_device_capability()
except Exception:
    _major = 0
DTYPE_LINE = 'bf16: true' if _major >= 8 else 'fp16: true'
print('train dtype:', DTYPE_LINE)

def latest_ckpt(out_dir):
    import glob as _g, re as _re
    cks = [d for d in _g.glob(f'{out_dir}/checkpoint-*')
           if _re.search(r'checkpoint-\d+$', d)]
    return max(cks, key=lambda d: int(d.rsplit('-', 1)[1])) if cks else None

def make_yaml(model, out_dir, epochs, bs=4, accum=8, ckpt=True, liger=True, resume=None):
    RESUME_LINE = f'resume_from_checkpoint: {resume}' if resume else ''
    return f'''model_name_or_path: {model}
trust_remote_code: true
stage: sft
do_train: true
finetuning_type: lora
lora_rank: 32
lora_alpha: 32
lora_dropout: 0.0
dataset: masld_sft_v5
dataset_dir: /content/LLaMA-Factory/data
template: qwen
cutoff_len: 4096
packing: true
neat_packing: true
max_samples: 100000
overwrite_cache: true
preprocessing_num_workers: 16
output_dir: {out_dir}
logging_steps: 10
save_steps: 0.05
save_total_limit: 2
plot_loss: true
{RESUME_LINE}
per_device_train_batch_size: {bs}
gradient_accumulation_steps: {accum}
dataloader_num_workers: 4
learning_rate: 1.0e-4
num_train_epochs: {epochs}
lr_scheduler_type: cosine
warmup_ratio: 0.1
weight_decay: 0.01
{DTYPE_LINE}
gradient_checkpointing: {ckpt}
enable_liger_kernel: {liger}
'''

CKPT_06B = f'{CKPT}/qwen3-0.6b-masld-sft-v5'
def train(model, out_dir, yaml_path, epochs, done_epochs, bs=4, accum=8, ckpt=True, liger=True):
    import json as _j
    marker = f'{out_dir}/train_results.json'
    if os.path.exists(marker):
        try:
            if float(_j.load(open(marker)).get('epoch', 0)) >= done_epochs:
                print(f'{out_dir} already trained -> skip'); return
        except Exception: pass
    resume = latest_ckpt(out_dir)
    if resume: print('resuming from', resume)
    open(yaml_path, 'w').write(make_yaml(model, out_dir, epochs, bs, accum, ckpt, liger, resume))
    r = subprocess.run([sys.executable, '-m', 'llamafactory.cli', 'train', yaml_path],
                       env=dict(os.environ, DISABLE_VERSION_CHECK='1'))
    if r.returncode != 0: raise RuntimeError('training failed: ' + yaml_path)

train('Qwen/Qwen3-0.6B', CKPT_06B, '/content/qwen06b_v5.yaml', 2.0, 2.0, bs=8, accum=4, ckpt=False, liger=False)
print('0.6B-v5 done')


# ---- cell boundary ----

CKPT_17B = f'{CKPT}/qwen3-1.7b-masld-sft-v5'
train('Qwen/Qwen3-1.7B', CKPT_17B, '/content/qwen17b_v5.yaml', 2.0, 2.0, bs=8, accum=4, ckpt=True, liger=False)
print('1.7B-v5 done')


# ---- cell boundary ----

import glob, gzip, json, random, re, shutil, collections
import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

def parse_answer(text, task):
    raw = (text or '').strip(); t = raw.lower()
    if task.endswith(('001', '201')):
        if t.startswith('yes') or 'answer: yes' in t or 'answer is yes' in t: return 'yes'
        if t.startswith('no') or 'answer: no' in t or 'answer is no' in t: return 'no'
        return None
    if task.endswith(('003', '203')):
        if re.search(r'\banswer(?: is|:) a\b', t) or t.startswith('a'): return 'A'
        if re.search(r'\banswer(?: is|:) b\b', t) or t.startswith('b'): return 'B'
        return None
    if task.endswith(('002', '202')):
        m = re.search(r'F([0-4])', raw)
        if m: return f'F{m.group(1)}'
        m = re.search(r'f([0-4])', t); return f'F{m.group(1)}' if m else None
    m = re.search(r'[Ff]([0-4])\b', raw)
    if m: return f'F{m.group(1)}'
    m = re.search(r'([0-9]+(?:\.[0-9]+)?)', t)
    if m:
        try: return float(m.group(1))
        except ValueError: return None
    return None

def load_gz(path):
    rows = []
    with gzip.open(path, 'rt') as f:
        f.readline()
        for l in f: rows.append(json.loads(l))
    return rows

def merge_adapter(base_id, adapter_dir, merged_dir):
    fresh = os.path.exists(os.path.join(merged_dir, 'config.json'))
    if fresh:
        try: fresh = os.path.getmtime(os.path.join(merged_dir, 'config.json')) > os.path.getmtime(os.path.join(adapter_dir, 'adapter_model.safetensors'))
        except OSError: fresh = False
    if not fresh:
        print('merging', adapter_dir)
        b = AutoModelForCausalLM.from_pretrained(base_id, torch_dtype=torch.bfloat16)
        m = PeftModel.from_pretrained(b, adapter_dir).merge_and_unload()
        m.save_pretrained(merged_dir, safe_serialization=True)
        AutoTokenizer.from_pretrained(base_id).save_pretrained(merged_dir)
    else: print('fresh merge:', merged_dir)
    return merged_dir

def eval_corpus(merged_dir, corpus_path, tag, n_per_task=300, max_len=4096):
    tok = AutoTokenizer.from_pretrained(merged_dir, padding_side='left')
    if tok.pad_token is None: tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(merged_dir, torch_dtype=torch.bfloat16, device_map='cuda').eval()
    rows = load_gz(corpus_path)
    by_task = {}
    for r in rows: by_task.setdefault(r['task'], []).append(r)
    rng = random.Random(20260929); sample = []
    for t, items in sorted(by_task.items()):
        rng.shuffle(items); sample.extend(items[:n_per_task])
    raws = []; BATCH = 8; i = 0
    while i < len(sample):
        batch = sample[i:i+BATCH]
        try:
            enc = tok([r['prompt'] for r in batch], return_tensors='pt', padding=True, truncation=True, max_length=max_len).to('cuda')
            with torch.no_grad():
                gen = model.generate(**enc, max_new_tokens=30, do_sample=False, pad_token_id=tok.pad_token_id)
            for j in range(len(batch)):
                raws.append(tok.decode(gen[j][enc['input_ids'].shape[1]:], skip_special_tokens=True).split('\n')[0])
            i += len(batch)
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            if BATCH == 1: raise
            BATCH = max(1, BATCH // 2)
    out = os.path.join(RUNS_DIR, f'{tag}__{os.path.basename(corpus_path).split("_")[0]}.jsonl.gz')
    with gzip.open(out, 'wt') as f:
        for r, raw in zip(sample, raws):
            f.write(json.dumps(dict(task=r['task'], sample=r['sample'], answer=r['answer'], raw=raw,
                                    error=None, model_version=tag, parsed=parse_answer(raw, r['task']))) + '\n')
    print('archived ->', out)
    del model; torch.cuda.empty_cache()
    bt = collections.defaultdict(list)
    for r, raw in zip(sample, raws): bt[r['task']].append((parse_answer(raw, r['task']), r['answer']))
    print(f'=== {tag} ===')
    for t, pairs in sorted(bt.items()):
        n = len(pairs); valid = sum(1 for p, g in pairs if p is not None)
        if t in ('MB-2001','MB-2002','MB-2003'):
            print(f'  {t}: acc={sum(1 for p,g in pairs if p==g)/n:.3f} validity={valid/n:.3f}')
        else:
            nums = [(p, float(g)) for p, g in pairs if isinstance(p, (int, float))]
            if nums:
                from scipy.stats import spearmanr
                print(f'  {t}: mae={np.mean([abs(p-g) for p,g in nums]):.3f} rho={spearmanr([g for p,g in nums],[p for p,g in nums]).statistic:.3f} validity={valid/n:.3f}')
            else: print(f'  {t}: no parse validity={valid/n:.3f}')
    return out

MERGED_06B_V5 = merge_adapter('Qwen/Qwen3-0.6B', CKPT_06B, '/content/qwen3-0.6b-masld-merged-v5')
eval_corpus(MERGED_06B_V5, f'{PROMPTS}/MB-20xx_liver_test.jsonl.gz', 'qwen3-0.6b-masld-v5')


# ---- cell boundary ----

MERGED_17B_V5 = merge_adapter('Qwen/Qwen3-1.7B', CKPT_17B, '/content/qwen3-1.7b-masld-merged-v5')
eval_corpus(MERGED_17B_V5, f'{PROMPTS}/MB-20xx_liver_test.jsonl.gz', 'qwen3-1.7b-masld-v5')


# ---- cell boundary ----

eval_corpus(MERGED_17B_V5, f'{PROMPTS}/MB-40xx_geo_test.jsonl.gz', 'qwen3-1.7b-masld-v5-geo', max_len=1024)


# ---- cell boundary ----

# Zero-shot: no training data exists for these tasks. This is the LLM arm of the
# C3a novelty gate (the ML arm already ran locally and FAILED at n=20).
ck = f'{PROMPTS}/MB-86xx_bloodproxy_test.jsonl.gz'
if os.path.exists(ck):
    eval_corpus(MERGED_17B_V5, ck, 'qwen3-1.7b-masld-v5-zeroshot')
    eval_corpus(MERGED_06B_V5, ck, 'qwen3-0.6b-masld-v5-zeroshot')
else:
    print('(MB-86xx not present on Drive)')


# ---- cell boundary ----

# H1: format transfer (does K-shot recover answer VALIDITY?)
# H2: balanced demonstration coverage fixes class collapse?
# Variants already frozen on Drive: kshot{2,4,8}_balanced + kshot4_random on MB-40xx.
import glob, json
kshot_files = sorted(glob.glob(f'{PROMPTS}/MB-40xx_geo_kshot*_test.jsonl.gz'))
print('k-shot variants:', [os.path.basename(p) for p in kshot_files])
kshot_results = {}
tok = AutoTokenizer.from_pretrained(MERGED_17B_V5, padding_side='left')
if tok.pad_token is None: tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(MERGED_17B_V5, torch_dtype=torch.bfloat16, device_map='cuda').eval()
for path in kshot_files:
    tag = os.path.basename(path).replace('_test.jsonl.gz', '')
    rows = load_gz(path)
    by_task = {}
    for r in rows: by_task.setdefault(r['task'], []).append(r)
    raws = []; BATCH = 8; i = 0
    while i < len(rows):
        batch = rows[i:i+BATCH]
        try:
            enc = tok([r['prompt'] for r in batch], return_tensors='pt', padding=True, truncation=True, max_length=2048).to('cuda')
            with torch.no_grad():
                gen = model.generate(**enc, max_new_tokens=30, do_sample=False, pad_token_id=tok.pad_token_id)
            for j in range(len(batch)):
                raws.append(tok.decode(gen[j][enc['input_ids'].shape[1]:], skip_special_tokens=True).split('\n')[0])
            i += len(batch)
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            if BATCH == 1: raise
            BATCH = max(1, BATCH // 2)
    bt = collections.defaultdict(list)
    for r, raw in zip(rows, raws): bt[r['task']].append((parse_answer(raw, r['task']), r['answer']))
    res = {}
    for t, pairs in sorted(bt.items()):
        n = len(pairs); valid = sum(1 for p, g in pairs if p is not None)
        if t in ('MB-4001','MB-4002'):
            res[t] = dict(acc=sum(1 for p,g in pairs if p==g)/n, validity=valid/n, n=n)
        else:
            nums = [(p, float(g)) for p, g in pairs if isinstance(p, (int, float))]
            res[t] = dict(mae=float(np.mean([abs(p-g) for p,g in nums])) if nums else None,
                          validity=valid/n, n=n)
    kshot_results[tag] = res
    print(tag, json.dumps(res))
out = os.path.join(RESULTS, 'kshot_17b.json')
json.dump(kshot_results, open(out, 'w'), indent=2)
print('k-shot results ->', out)
del model; torch.cuda.empty_cache()


# ---- cell boundary ----

import datetime
manifest = dict(
    generated=datetime.datetime.utcnow().isoformat(timespec='seconds') + 'Z',
    notebook='05_maxgpu_runall',
    gpu=str(subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'], capture_output=True, text=True).stdout.strip()),
    checkpoints=[p for p in glob.glob(f'{CKPT}/*v5*')],
    archives=sorted(os.path.basename(p) for p in glob.glob(f'{RUNS_DIR}/*v5*.jsonl.gz')),
    kshot=os.path.join(RESULTS, 'kshot_17b.json'),
)
json.dump(manifest, open(os.path.join(RESULTS, 'maxgpu_run_manifest.json'), 'w'), indent=2)
print(json.dumps(manifest, indent=2))
print('\nALL STAGES COMPLETE. Pull results/frontier_runs/*v5* + results/kshot_17b.json locally to score.')


# ---- cell boundary ----
