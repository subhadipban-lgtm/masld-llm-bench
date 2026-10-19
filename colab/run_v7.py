#!/usr/bin/env python3
"""MASLD-LLM v7 runner: the 9B rung (self-contained Colab script).

v7 = the v6 mixture EXACTLY (same corpora, same sampling, same seed), at
Qwen3-8B with QLoRA r32 a32. The only variable vs v6 is model scale, so
any improvement is attributable to size, not data.

Hardware: A100-40 (Colab Pro+). 4-bit NF4 QLoRA, bs=1 x accum=32 keeps the
effective batch at 32; gradient checkpointing + liger fused-CE on. Hourly
checkpoints to Drive; re-running resumes from the newest checkpoint.

After training: merge -> eval the FROZEN tests (MB-20xx / 85xx / 87xx /
88xx / 86xx) under the identical protocol. Frozen corpora never trained on.

Usage (one Colab cell, A100 runtime):
  !python /content/drive/MyDrive/masld-llm/run_v7.py
"""
import os, subprocess, sys, json, gzip, glob, random, re, collections

def _sh(cmd):
    print(">>>", cmd, flush=True)
    subprocess.run(cmd, shell=True, check=False)

if not os.path.exists('/content/drive/MyDrive'):
    from google.colab import drive
    drive.mount('/content/drive')

MASLD_LLM = '/content/drive/MyDrive/masld-llm'
PROMPTS  = os.path.join(MASLD_LLM, 'prompts')
RESULTS  = os.path.join(MASLD_LLM, 'results')
RUNS_DIR = os.path.join(RESULTS, 'frontier_runs')
CKPT     = os.path.join(MASLD_LLM, 'checkpoints')
for d in (RESULTS, RUNS_DIR, CKPT): os.makedirs(d, exist_ok=True)
for need in ('MB-12xx_staged_train.jsonl.gz', 'MB-88xx_drugseq_train.jsonl.gz'):
    assert os.path.exists(os.path.join(PROMPTS, need)), 'missing corpus: ' + need
print('workspace OK; corpora present (v7)')
assert os.path.exists(os.path.join(MASLD_LLM, 'data', 'ensembl_to_symbol_cache.csv')), 'missing ensembl cache'

# ---- deps (same as v5; torchao must stay absent) ----
_sh("cd /content && (git clone --depth 1 https://github.com/hiyouga/LLaMA-Factory.git 2>/dev/null || true)")
_sh("cd /content/LLaMA-Factory && pip -q install -e '.[torch,metrics]' bitsandbytes peft transformers accelerate liger-kernel")
import importlib
if importlib.util.find_spec('torchao') is not None:
    subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', 'torchao'], check=False)
print('deps ok; torchao absent:', importlib.util.find_spec('torchao') is None)

# ---- corpora -> alpaca ----
def to_alpaca(in_path, out_path):
    rows = []
    with gzip.open(in_path, 'rt') as f:
        first = json.loads(f.readline())
        if '__meta__' not in first: rows.append(first)
        for l in f: rows.append(json.loads(l))
    out = [dict(instruction=r['prompt'], output=str(r['answer'])) for r in rows]
    json.dump(out, open(out_path, 'w'), indent=0)
    print(os.path.basename(out_path), len(out))

for src, dst in [
    ('MB-10xx_liver_train.jsonl.gz', 'sft_liver.json'),
    ('MB-11xx_external_train.jsonl.gz', 'sft_external.json'),
    ('MB-61xx_msigdb_train.jsonl.gz', 'sft_knowledge.json'),
    ('MB-62xx_drugs_train.jsonl.gz', 'sft_drugs.json'),
    ('MB-63xx_drugcentral_affinity_train.jsonl.gz', 'sft_drugs2.json'),
    ('MB-70xx_dge_direction_train.jsonl.gz', 'sft_dge.json'),
    ('MB-8xxx_fujiwara_train.jsonl.gz', 'sft_fujiwara.json'),
    ('MB-30xx_dnam_train.jsonl.gz', 'sft_dnam.json'),
    ('MB-12xx_staged_train.jsonl.gz', 'sft_staged.json'),      # NEW v6
    ('MB-88xx_drugseq_train.jsonl.gz', 'sft_drugseq.json'),    # NEW v6
]:
    to_alpaca(os.path.join(PROMPTS, src), '/content/' + dst)

# ---- v7 mixture: v6 recipe verbatim (same seed, same weights) ----
rs = random.Random(20260929)
def load(p): return json.load(open(p)) if os.path.exists(p) else []

liver, external = load('/content/sft_liver.json'), load('/content/sft_external.json')
fujiwara, knowledge = load('/content/sft_fujiwara.json'), load('/content/sft_knowledge.json')
dge, drugs1 = load('/content/sft_dge.json'), load('/content/sft_drugs.json')
drugs2, dnam = load('/content/sft_drugs2.json'), load('/content/sft_dnam.json')
staged, drugseq = load('/content/sft_staged.json'), load('/content/sft_drugseq.json')

# DRUG-seq corpus uses Ensembl ids; every other corpus (and the frozen tests)
# use gene SYMBOLS -> remap ENSGxxxx= to symbols for transfer consistency.
_ens_cache = os.path.join(MASLD_LLM, 'data', 'ensembl_to_symbol_cache.csv')
if os.path.exists(_ens_cache):
    ens2sym = {}
    for line in open(_ens_cache).read().splitlines()[1:]:
        if ',' in line:
            e, s = line.split(',', 1)
            ens2sym[e.strip()] = s.strip()
    _ens_re = re.compile(r'(ENSG\d{11})(?==)')
    n_mapped = 0
    for ex in drugseq:
        def _sub(m):
            global n_mapped
            sym = ens2sym.get(m.group(1))
            if sym: n_mapped += 1
            return sym if sym else m.group(1)
        ex['instruction'] = _ens_re.sub(_sub, ex['instruction'])
    print(f'drugseq ensembl->symbol tokens mapped: {n_mapped}')

def is_pairwise(ex): return 'Patient A:' in ex['instruction']
liver_single = [e for e in liver if not is_pairwise(e)]
liver_pair   = [e for e in liver if is_pairwise(e)]
ext_single   = [e for e in external if not is_pairwise(e)]
ext_pair     = [e for e in external if is_pairwise(e)]

STAGE_W = {'F0': 2, 'F1': 1, 'F2': 2, 'F3': 2, 'F4': 7}
def task_kind(ex):
    q = ex['instruction']
    if 'Assign the fibrosis stage' in q or 'Which fibrosis stage' in q: return 'multi'
    if 'advanced fibrosis' in q or 'ADVANCED' in q: return 'binary'
    if 'NAFLD Activity Score' in q or 'exact NAS' in q or 'NAFLD activity score' in q: return 'nas'
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
staged_up = upsample_weighted(staged, 4, lambda e: 1)     # uniform x4 (v6)
drugseq_up = list(drugseq) * 4                            # uniform x4 (v6)
single = liver_single_up + ext_single + list(fujiwara)*8 + (list(dnam)*20 if dnam else []) + staged_up + drugseq_up
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
json.dump(mixture, open('/content/sft_multitask_v7.json', 'w'), indent=0)
print(f'single {len(single)} (staged {len(staged_up)}, drugseq {len(drugseq_up)}) | pair {len(pair)} | drugs {len(drugs)} | know {len(know)} | geo {len(geo_up)}')
print('FINAL v7 MIXTURE:', len(mixture))

# ---- train (v5 hyperparameters verbatim) ----
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
ds_entry = json.dumps({'masld_sft_v7': {'file_name': '/content/sft_multitask_v7.json',
                                        'columns': {'prompt': 'instruction', 'response': 'output'}}})
open('/content/LLaMA-Factory/data/dataset_info.json', 'w').write(ds_entry)

import torch as _t
try: _major, _ = _t.cuda.get_device_capability()
except Exception: _major = 0
DTYPE_LINE = 'bf16: true' if _major >= 8 else 'fp16: true'

def latest_ckpt(out_dir):
    cks = [d for d in glob.glob(f'{out_dir}/checkpoint-*') if re.search(r'checkpoint-\d+$', d)]
    return max(cks, key=lambda d: int(d.rsplit('-', 1)[1])) if cks else None

def make_yaml(model, out_dir, epochs, bs, accum, ckpt, liger, resume):
    RESUME_LINE = f'resume_from_checkpoint: {resume}' if resume else ''
    return f'''model_name_or_path: {model}
trust_remote_code: true
stage: sft
do_train: true
finetuning_type: lora
quantization_bit: 4
quantization_method: bnb
double_quantization: true
lora_rank: 32
lora_alpha: 32
lora_dropout: 0.0
dataset: masld_sft_v6
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

def train(model, out_dir, yaml_path, epochs, bs=8, accum=4, ckpt=True, liger=False):
    marker = f'{out_dir}/train_results.json'
    if os.path.exists(marker):
        try:
            if float(json.load(open(marker)).get('epoch', 0)) >= epochs:
                print(f'{out_dir} already trained -> skip'); return
        except Exception: pass
    resume = latest_ckpt(out_dir)
    if resume: print('resuming from', resume)
    open(yaml_path, 'w').write(make_yaml(model, out_dir, epochs, bs, accum, ckpt, liger, resume))
    r = subprocess.run([sys.executable, '-m', 'llamafactory.cli', 'train', yaml_path],
                       env=dict(os.environ, DISABLE_VERSION_CHECK='1'))
    if r.returncode != 0: raise RuntimeError('training failed: ' + yaml_path)

# 8B on A100-40: 4-bit NF4 QLoRA, bs=1 x accum=32 (effective 32), packing
# 4096, gradient checkpointing, liger fused-CE. If liger fights the quantized
# forward on this stack, fall back once to the unfused loss.
try:
    train('Qwen/Qwen3-8B', f'{CKPT}/qwen3-8b-masld-sft-v7', '/content/qwen8b_v7.yaml', 2.0,
          bs=1, accum=32, ckpt=True, liger=True)
except RuntimeError:
    print('liger path failed -> retrying unfused CE (same effective batch)')
    train('Qwen/Qwen3-8B', f'{CKPT}/qwen3-8b-masld-sft-v7', '/content/qwen8b_v7.yaml', 2.0,
          bs=1, accum=32, ckpt=True, liger=False)
print('8B-v7 done')

# ---- eval on the FROZEN C3 tests (trained-on readout) ----
import numpy as np, torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

def parse_v7(text, task):
    raw = (text or '').strip(); t = raw.lower()
    if task in ('MB-2001', 'MB-8602', 'MB-8801', 'MB-1221'):
        if t.startswith('yes') or 'answer: yes' in t or 'answer is yes' in t: return 'yes'
        if t.startswith('no') or 'answer: no' in t or 'answer is no' in t: return 'no'
        return None
    if task == 'MB-2003':
        if re.search(r'\banswer(?: is|:) a\b', t) or t.startswith('a'): return 'A'
        if re.search(r'\banswer(?: is|:) b\b', t) or t.startswith('b'): return 'B'
        return None
    if task in ('MB-2002', 'MB-1202') or task.endswith('002'):
        m = re.search(r'F([0-4])', raw) or re.search(r'f([0-4])', t)
        return f'F{m.group(1)}' if m else None
    if task == 'MB-8501':
        m = re.search(r'\b(stable|progressive)\b', t)
        return m.group(1) if m else None
    if task == 'MB-8601':
        m = re.search(r'\b(low|medium|high)\b', t)
        return m.group(1) if m else None
    if task == 'MB-8701':
        m = re.search(r'(plasma_liver2|souria72|lumos72)', t)
        return m.group(1) if m else None
    m = re.search(r'(-?\d+(?:\.\d+)?)', t)
    if m:
        try: return float(m.group(1))
        except ValueError: return None
    return None

def load_gz(path):
    rows = []
    with gzip.open(path, 'rt') as f:
        first = f.readline()
        if '"__meta__"' not in first:
            try: rows.append(json.loads(first))
            except Exception: pass
        for l in f: rows.append(json.loads(l))
    return rows

def merge_adapter(base_id, adapter_dir, merged_dir):
    b = AutoModelForCausalLM.from_pretrained(base_id, torch_dtype=torch.bfloat16)
    m = PeftModel.from_pretrained(b, adapter_dir).merge_and_unload()
    m.save_pretrained(merged_dir, safe_serialization=True)
    AutoTokenizer.from_pretrained(base_id).save_pretrained(merged_dir)
    return merged_dir

def eval_corpus(merged_dir, corpus, tag, n_per_task=300, max_len=4096):
    path = os.path.join(PROMPTS, corpus)
    if not os.path.exists(path):
        print('MISSING', corpus); return
    tok = AutoTokenizer.from_pretrained(merged_dir, padding_side='left')
    if tok.pad_token is None: tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(merged_dir, torch_dtype=torch.bfloat16, device_map='cuda').eval()
    rows = load_gz(path)
    by_task = {}
    for r in rows: by_task.setdefault(r['task'], []).append(r)
    rng = random.Random(20260929); sample = []
    for t, items in sorted(by_task.items()):
        rng.shuffle(items); sample.extend(items[:n_per_task])
    raws = []; BATCH = 8; i = 0
    while i < len(sample):
        batch = sample[i:i+BATCH]
        try:
            enc = tok([r['prompt'] for r in batch], return_tensors='pt', padding=True,
                      truncation=True, max_length=max_len).to('cuda')
            with torch.no_grad():
                gen = model.generate(**enc, max_new_tokens=24, do_sample=False, pad_token_id=tok.pad_token_id)
            for j in range(len(batch)):
                raws.append(tok.decode(gen[j][enc['input_ids'].shape[1]:], skip_special_tokens=True).split('\n')[0])
            i += len(batch)
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            if BATCH == 1: raise
            BATCH = max(1, BATCH // 2)
    fam = corpus.split('_')[0]
    out = os.path.join(RUNS_DIR, f'{tag}__{fam}.jsonl.gz')
    with gzip.open(out, 'wt') as f:
        for r, raw in zip(sample, raws):
            f.write(json.dumps(dict(task=r['task'], sample=r['sample'], answer=r['answer'], raw=raw,
                                    error=None, model_version=tag, parsed=parse_v7(raw, r['task']))) + '\n')
    print('archived ->', out)
    del model; import gc; gc.collect(); torch.cuda.empty_cache()
    bt = collections.defaultdict(list)
    for r, raw in zip(sample, raws): bt[r['task']].append((parse_v7(raw, r['task']), r['answer']))
    print(f'=== {tag} / {fam} ===')
    for t, pairs in sorted(bt.items()):
        n = len(pairs); valid = sum(1 for p, g in pairs if p is not None)
        gold_num = all(_isfloat(g) for _, g in pairs)
        if gold_num:
            nums = [(float(p), float(g)) for p, g in pairs if isinstance(p, (int, float))]
            mae = float(np.mean([abs(p-g) for p, g in nums])) if nums else None
            print(f'  {t}: mae={mae} validity={valid/n:.3f} n={n}')
        else:
            print(f'  {t}: acc={sum(1 for p,g in pairs if p==g)/n:.3f} validity={valid/n:.3f} n={n}')

def _isfloat(x):
    try: float(x); return True
    except Exception: return False

TESTS = ['MB-20xx_liver_test.jsonl.gz', 'MB-85xx_progression_test.jsonl.gz',
         'MB-87xx_liverplasma_test.jsonl.gz', 'MB-88xx_perturb_test.jsonl.gz',
         'MB-86xx_bloodproxy_test.jsonl.gz']

merged = merge_adapter('Qwen/Qwen3-8B', f'{CKPT}/qwen3-8b-masld-sft-v7', '/content/merged-v7-8b')
for corpus in TESTS:
    eval_corpus(merged, corpus, 'qwen3-8b-masld-v7')

import datetime
json.dump(dict(generated=datetime.datetime.utcnow().isoformat(timespec='seconds') + 'Z',
               recipe='v7 = v6 mixture verbatim at Qwen3-8B QLoRA (size-only contrast)',
               checkpoints=sorted(os.path.basename(p) for p in glob.glob(f'{CKPT}/*v7*')),
               archives=sorted(os.path.basename(p) for p in glob.glob(f'{RUNS_DIR}/*v7*.jsonl.gz'))),
          open(os.path.join(RESULTS, 'v7_run_manifest.json'), 'w'), indent=2)
print('\nV7 COMPLETE. Archives in Drive results/frontier_runs/*v7*')
