#!/usr/bin/env python3
"""Protocol arms for MASLD-Bench (2026-10-19): RAG / reasoning / architecture / tool.

Four arms, one harness. Each arm is a SEPARATE protocol row — frozen user
prompts stay byte-identical; any added context rides in a system message,
and added compute rides in request parameters. Archives land in
results/frontier_runs/ as `{vendor}__{model}-{arm}__{corpus}.jsonl.gz`.

Arms
----
kg        Graph-RAG: retrieve Reactome pathways / GO-ish processes / MASLD
          associations for the profile's genes from the heterogeneous KG
          (kg_edges.tsv), inject as a system message. Tests whether graph
          grounding rescues omics reading (the #1 objection to C4).
reason    Test-time reasoning ON (models where our main bracket disabled
          it). Tests whether thinking overcomes the format barrier.
mercury   Diffusion-LM architecture arm (Inception Mercury). Tests whether
          C4 is autoregressive-transformer-specific.
tool      Tool-use orchestration on MB-8801: the model may call a
          logreg_predict tool (donor-grouped OOF classical predictions)
          before answering. Tests "LLM conducts the models that read omics".

Usage: python scripts/arms.py <arm> [--tasks MB-2001,MB-2003] [--model id]
Resume-safe: re-running skips already-archived successful calls.
"""
from __future__ import annotations

import argparse
import collections
import csv
import gzip
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "results", "frontier_runs")
PROMPTS = os.path.join(ROOT, "prompts")
KG = ("/Users/subhadipbanerjee/ami.subhadipbanerjee@gmail.com - Google Drive"
      "/My Drive/kg_edges.tsv")
ENS = os.path.join(ROOT, "data", "ensembl_to_symbol_cache.csv")
SEED = 20260929
WORKERS = 8


def key() -> str:
    k = os.environ.get("OPENROUTER_API_KEY")
    return k.strip() if k else open(os.path.expanduser("~/.openclaw/tmp/or_key.txt")).read().strip()


def balance() -> float:
    req = urllib.request.Request("https://openrouter.ai/api/v1/credits",
                                 headers={"Authorization": f"Bearer {key()}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())["data"]
    return round(d["total_credits"] - d["total_usage"], 2)


def call(model, messages, max_tokens=200, reasoning=None, tools=None, retries=4):
    body = {"model": model, "messages": messages, "temperature": 0.0,
            "max_tokens": max_tokens}
    if reasoning:
        body["reasoning"] = reasoning
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    data = json.dumps(body).encode()
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions", data=data,
            headers={"Authorization": f"Bearer {key()}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=420) as r:
                d = json.loads(r.read())
            msg = d["choices"][0]["message"]
            return msg.get("content"), msg.get("tool_calls"), d.get("model"), None
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read()[:150]}"
            time.sleep(20 * (attempt + 1) if e.code == 429 else 5 * (attempt + 1))
        except Exception as e:  # noqa: BLE001
            last = str(e)
            time.sleep(5 * (attempt + 1))
    return None, None, None, last


def load_corpus(name):
    rows = [json.loads(l) for l in gzip.open(os.path.join(PROMPTS, name), "rt")
            if "__meta__" not in l]
    by = collections.defaultdict(list)
    for r in rows:
        by[r["task"]].append(r)
    return by


def sample(by, tasks, n_per=300):
    import random
    rng = random.Random(SEED)
    out = []
    for t in sorted(tasks):
        items = list(by[t]); rng.shuffle(items); out.extend(items[:n_per])
    return out


def run_arm(model, tag, corpus_name, tasks, build_messages, max_tokens=200,
            reasoning=None, n_per=300):
    by = load_corpus(corpus_name)
    items = sample(by, tasks, n_per)
    out_path = os.path.join(RUNS, f"{tag}__{corpus_name.replace('_test.jsonl.gz','')}.jsonl.gz")
    print(f"{tag}: {len(items)} items over {sorted(tasks)} -> {os.path.basename(out_path)}", flush=True)

    done = set()
    if os.path.exists(out_path):
        for line in gzip.open(out_path, "rt"):
            try:
                rec = json.loads(line)
                if rec.get("raw") is not None:
                    done.add(f"{rec['task']}:{rec['sample']}")
            except Exception:
                pass
    todo = [r for r in items if f"{r['task']}:{r['sample']}" not in done]
    print(f"resuming: {len(done)} archived, {len(todo)} to go | balance {balance()}", flush=True)

    def work(r):
        msgs = build_messages(r)
        raw, _tc, ver, err = call(model, msgs, max_tokens=max_tokens, reasoning=reasoning)
        return dict(task=r["task"], sample=r["sample"], answer=r["answer"],
                    raw=raw, error=err, model_version=ver, parsed=None)

    results, t0 = [], time.time()
    with gzip.open(out_path, "at") as f, ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(work, r): r for r in todo}
        for i, fut in enumerate(as_completed(futs)):
            rec = fut.result(); results.append(rec)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if (i + 1) % 25 == 0:
                f.flush()
                print(f"  {i+1}/{len(todo)} ({time.time()-t0:.0f}s) bal {balance()}", flush=True)
    ok = sum(1 for r in results if r["raw"] is not None)
    print(f"done: {ok}/{len(todo)} ok in {(time.time()-t0)/60:.1f} min | balance {balance()}", flush=True)


# ---------------- Arm: graph-RAG ----------------
_ens_cache = None
def ens2sym():
    global _ens_cache
    if _ens_cache is None:
        _ens_cache = {}
        for line in open(ENS).read().splitlines()[1:]:
            if "," in line:
                e, s = line.split(",", 1)
                _ens_cache[e.strip()] = s.strip()
    return _ens_cache

_kg_terms = None
def kg_terms():
    """term -> set(gene symbols) from Reactome part_of + involved_in edges."""
    global _kg_terms
    if _kg_terms is None:
        t0 = time.time()
        _kg_terms = collections.defaultdict(set)
        with open(KG) as f:
            for row in csv.DictReader(f, delimiter="\t"):
                if row["edge_type"] in ("part_of", "involved_in"):
                    _kg_terms[row["target"]].add(row["source"])
        print(f"KG index: {len(_kg_terms)} terms ({time.time()-t0:.0f}s)", flush=True)
    return _kg_terms

def kg_context(prompt, top_k=6, min_overlap=3):
    e2s = ens2sym()
    zs = dict(re.findall(r"(ENSG\d{11})=(-?\d+\.\d+)", prompt))
    sym_z = {e2s[e]: v for e, v in zs.items() if e in e2s}
    terms = kg_terms()
    hits = []
    for name, members in terms.items():
        ov = members & sym_z.keys()
        if len(ov) >= min_overlap:
            hits.append((len(ov), name, ov))
    hits.sort(reverse=True)
    lines = ["Relevant pathway knowledge retrieved for this gene profile "
             "(Reactome/biological-process graph, by member overlap):"]
    for n, name, ov in hits[:top_k]:
        pairs = ", ".join(f"{g}={sym_z[g]}" for g in sorted(ov)[:10])
        lines.append(f"- {name} ({n} of the profile's genes): {pairs}")
    if len(lines) == 1:
        lines.append("(no pathway reached the overlap threshold for this profile)")
    return "\n".join(lines), len(hits)


# ---------------- Arm: tool orchestration (MB-8801) ----------------
def oof_logreg(corpus_name="MB-88xx_perturb_test.jsonl.gz"):
    """Donor-grouped out-of-fold logreg predictions on the frozen corpus."""
    sys.path.insert(0, os.path.join(ROOT, "platform", "core"))
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedGroupKFold
    from masld_platform.features import encode_prompt, vectorise
    rows = [json.loads(l) for l in gzip.open(os.path.join(PROMPTS, corpus_name), "rt")
            if "__meta__" not in l]
    rows = [r for r in rows if r["task"] == "MB-8801"]
    X, _ = vectorise([encode_prompt(r["prompt"], mode="genes") for r in rows])
    X = np.array(X)
    y = np.array([r["answer"] for r in rows])
    # groups = the sample id itself, exactly the frozen C3a-gate protocol
    # (scripts/c3a_gate_85_87.py: grouped_folds(samples, y)) that produced
    # the published 0.833 — do not improvise a different grouping here.
    groups = np.array([r["sample"] for r in rows])
    # NOTE: sample ids repeat across replicates (e.g. 'F95' x7) — key by
    # record position, never by sample, or later folds silently overwrite.
    pred = np.empty(len(rows), dtype=object)
    for tr, te in StratifiedGroupKFold(5, shuffle=True, random_state=SEED).split(X, y, groups):
        m = LogisticRegression(max_iter=2000, C=1.0).fit(X[tr], y[tr])
        for i, p in zip(te, m.predict(X[te])):
            pred[i] = str(p)
    acc = float(np.mean([pred[i] == rows[i]["answer"] for i in range(len(rows))]))
    return list(pred), acc


# ---------------- mains ----------------
def arm_kg(model, tasks, max_tokens=900):
    def build(r):
        ctx, _ = kg_context(r["prompt"])
        return [{"role": "system", "content": ctx},
                {"role": "user", "content": r["prompt"]}]
    # warm the index once so workers don't race on it
    kg_context(load_corpus("MB-20xx_liver_test.jsonl.gz")["MB-2001"][0]["prompt"])
    # The injected KG context elicits longer reasoning-before-verdict than
    # the bare prompt; 200 tokens truncates mid-analysis (same artifact the
    # main bracket needed a re-pass for). 900 clears it for all models.
    tag = model.replace("/", "__") + "-kg"
    run_arm(model, tag, "MB-20xx_liver_test.jsonl.gz", tasks, build, max_tokens=max_tokens)

def arm_reason(model, tasks):
    def build(r):
        return [{"role": "user", "content": r["prompt"]}]
    tag = model.replace("/", "__") + "-reason"
    run_arm(model, tag, "MB-20xx_liver_test.jsonl.gz", tasks, build,
            max_tokens=6000, reasoning={"effort": "low"})

def arm_mercury(model):
    def build(r):
        return [{"role": "user", "content": r["prompt"]}]
    tag = model.replace("/", "__")
    # Mercury burns ~2.5k completion tokens on internal diffusion iterations
    # ("reasoning_tokens") before any visible content; 4k clears it with margin.
    run_arm(model, tag, "MB-20xx_liver_test.jsonl.gz",
            ["MB-2001", "MB-2002", "MB-2003", "MB-2005", "MB-2006"], build, max_tokens=4000)

def arm_tool(model):
    pred, tool_acc = oof_logreg()
    print(f"tool OOF logreg accuracy on MB-8801: {tool_acc:.3f}", flush=True)
    tools = [{"type": "function", "function": {
        "name": "logreg_predict",
        "description": "Run a donor-grouped cross-validated logistic regression "
                       "on this exact gene-expression profile and return its "
                       "FFA-treatment prediction (yes/no).",
        "parameters": {"type": "object", "properties": {}, "required": []}}}]
    def build(r):
        return [{"role": "system", "content":
                 "You may call logreg_predict() to obtain a classical-model "
                 "prediction for this profile before answering."},
                {"role": "user", "content": r["prompt"]}]

    by = load_corpus("MB-88xx_perturb_test.jsonl.gz")
    items = [r for r in by["MB-8801"]]
    tag = model.replace("/", "__") + "-tool"
    out_path = os.path.join(RUNS, f"{tag}__MB-88xx.jsonl.gz")
    results, t0 = [], time.time()
    with gzip.open(out_path, "wt") as f:
        for i, r in enumerate(items):
            tool_lookup = pred[i]
            msgs = build(r)
            raw, tc, ver, err = call(model, msgs, max_tokens=300, tools=tools)
            used_tool, tool_out = False, None
            if tc:
                used_tool = True
                tool_out = tool_lookup
                msgs = msgs + [{"role": "assistant", "content": None,
                                "tool_calls": [tc[0] | {"id": "call1"}]},
                               {"role": "tool", "tool_call_id": "call1",
                                "content": json.dumps({"prediction": tool_out})}]
                raw, _t2, ver, err = call(model, msgs, max_tokens=300)
            rec = dict(task=r["task"], sample=r["sample"], answer=r["answer"],
                       raw=raw, error=err, model_version=ver, parsed=None,
                       used_tool=used_tool, tool_prediction=tool_out,
                       tool_ground_truth=tool_lookup if used_tool else None)
            results.append(rec)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"  {i+1}/{len(items)} tool={used_tool} tool_pred={tool_out} "
                  f"raw={str(raw)[:40]!r}", flush=True)
    ok = [r for r in results if r["raw"]]
    agree = sum(1 for r in ok if r["raw"].strip().lower().startswith(str(r["tool_ground_truth"] or '').lower()))
    acc = sum(1 for r in ok if r["raw"] and r["raw"].strip().lower().startswith(str(r["answer"]).lower()))
    print(f"tool arm: called={sum(1 for r in results if r['used_tool'])}/{len(results)} "
          f"| final agrees-with-tool {agree}/{len(ok)} | final acc {acc}/{len(ok)} "
          f"({(time.time()-t0)/60:.1f} min) bal {balance()}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arm", choices=["kg", "reason", "mercury", "tool"])
    ap.add_argument("--model", default=None)
    ap.add_argument("--tasks", default="MB-2001,MB-2003")
    ap.add_argument("--kg-tokens", type=int, default=900)
    a = ap.parse_args()
    tasks = a.tasks.split(",")
    if a.arm == "kg":
        arm_kg(a.model or "openai/gpt-4.1-mini", tasks, a.kg_tokens)
    elif a.arm == "reason":
        arm_reason(a.model or "x-ai/grok-4.7", tasks)
    elif a.arm == "mercury":
        arm_mercury(a.model or "inception/mercury-2.5")
    elif a.arm == "tool":
        arm_tool(a.model or "openai/gpt-4.1-mini")


if __name__ == "__main__":
    main()
