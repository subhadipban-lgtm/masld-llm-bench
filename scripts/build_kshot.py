#!/usr/bin/env python3
"""K-shot (demonstration-conditioned) variants of MASLD-Bench — the BDH-CQ
paradigm applied without its proprietary architecture.

Hypotheses tested (from BDH-CQ's findings):
  H1 (context binds mappings): do K geometric demonstrations teach the 0.6B
     the yes/no + F-stage formats at inference time? (zero-shot validity was 0.000)
  H2 (demonstration coverage): does stage-BALANCED demonstration selection
     fix the F0/F1 collapse and majority-'no' mimicry?

Design:
  - K in {2, 4, 8} for geometric prompts (354 chars each — fits context)
  - K = 2 for raw prompts (4700 chars each — context limit)
  - Demonstrations drawn from TRAIN patients only (geometric train corpus)
  - Selection strategies: 'balanced' (stages F0-F4 covered evenly) vs 'random'
  - Format: demonstrations first as worked examples, then the query
"""
import gzip, json, os, random, re, sys, time

T0 = time.time()
ROOT = "/Users/subhadipbanerjee/masld-llm"
SEED = 20260929

def load_jsonl(path):
    rows = []
    with gzip.open(path, "rt") as f:
        first = json.loads(f.readline())
        if "__meta__" not in first:
            rows.append(first)
        for line in f:
            rows.append(json.loads(line))
    return rows

# ---- load train (demonstration pool) and test ----
train_geo = load_jsonl(f"{ROOT}/prompts/MB-40xx_geo_train.jsonl.gz")
test_geo = load_jsonl(f"{ROOT}/prompts/MB-40xx_geo_test.jsonl.gz")
print(f"geometric train pool: {len(train_geo)} | test: {len(test_geo)}")

# index train by patient (each patient has 3 tasks: 4001/4002/4005)
by_patient = {}
for r in train_geo:
    by_patient.setdefault(r["sample"], {})[r["task"]] = r
print(f"unique train patients: {len(by_patient)}")

# stage label per patient (from the multiclass answer)
patient_stage = {}
for r in train_geo:
    if r["task"] == "MB-4002":
        patient_stage[r["sample"]] = r["answer"]
from collections import Counter
print(f"train stage distribution: {dict(sorted(Counter(patient_stage.values()).items()))}")

def pick_demonstrations(k, strategy, rng, exclude=None):
    """Return k patient IDs as demonstrations."""
    patients = [p for p in by_patient if patient_stage.get(p) and p != exclude]
    if strategy == "random":
        return rng.sample(patients, min(k, len(patients)))
    # balanced: cover stages F0..F4 as evenly as possible
    by_stage = {}
    for p in patients:
        by_stage.setdefault(patient_stage[p], []).append(p)
    for s in by_stage:
        rng.shuffle(by_stage[s])
    picks = []
    stages = sorted(by_stage.keys())
    while len(picks) < k and any(by_stage[s] for s in stages):
        for s in stages:
            if by_stage[s] and len(picks) < k:
                picks.append(by_stage[s].pop())
    return picks

def strip_question(prompt):
    """Remove the trailing question from a prompt, keep the profile."""
    # geometric prompts end with the question after the manifold line
    lines = prompt.strip().split("\n")
    # question is the last line; profile is everything before it
    return "\n".join(lines[:-1]), lines[-1]

def build_kshot(query_row, demo_patients, rng):
    profile, question = strip_question(query_row["prompt"])
    parts = ["You are given example patients from a liver fibrosis study, each with their structural profile and the correct assessment."]
    for p in demo_patients:
        d = by_patient[p].get(query_row["task"])
        if d is None:
            continue
        d_profile, _ = strip_question(d["prompt"])
        parts.append(f"Example: {d_profile}\nAssessment: {d['answer']}")
    parts.append(f"Now assess this patient.\n{profile}\n{question}")
    return "\n\n".join(parts)

# ---- generate variants ----
OUT = f"{ROOT}/prompts"
variants = {}
rng = random.Random(SEED)

for task_filter, tag in [(None, "all")]:
    # geometric: K=2,4,8 balanced; K=4 random (strategy control)
    for k, strategy in [(2, "balanced"), (4, "balanced"), (8, "balanced"), (4, "random")]:
        recs = []
        # one demo set per test patient (shared across their tasks to save tokens? no — per task, matched task type)
        for r in test_geo:
            demos = pick_demonstrations(k, strategy, rng)
            recs.append(dict(task=r["task"], split="test", sample=r["sample"],
                             source=f"geo-kshot{k}-{strategy}",
                             prompt=build_kshot(r, demos, rng),
                             answer=r["answer"]))
        fn = f"MB-40xx_geo_kshot{k}_{strategy}_test.jsonl.gz"
        with gzip.open(f"{OUT}/{fn}", "wt") as f:
            f.write(json.dumps({"__meta__": dict(n_records=len(recs), k=k, strategy=strategy,
                    builder="BDH-CQ-inspired demonstration conditioning", seed=SEED)}) + "\n")
            for r in recs:
                f.write(json.dumps(r) + "\n")
        avg_len = sum(len(r["prompt"]) for r in recs) / len(recs)
        print(f"  {fn}: {len(recs)} prompts, avg {avg_len:.0f} chars")
        variants[f"geo-k{k}-{strategy}"] = fn

print(f"\ngenerated {len(variants)} few-shot variants in {time.time()-T0:.0f}s")
print("next: run scripts/ablation_06b_kshot.py to evaluate")
