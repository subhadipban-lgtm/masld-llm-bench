#!/usr/bin/env python3
"""Generate manuscript figures F2/F3/F5 from committed artifacts.

F2  leaderboard overview: models x MB-20xx tasks (accuracy + MAE panels)
F3  paired C2 forest: MB-2005 MAE with bootstrap CIs vs all references
F5  C3 matrix: novel families x methods, with majority/constant baselines

Reads: results/leaderboard.csv, results/c2_significance.csv, gates (hard
numbers from results/c3a_gate*.json mirrored here for plotting).
Writes: docs/assets/fig2_leaderboard.png, fig3_paired_forest.png,
        fig5_c3_matrix.png
"""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
LB = ROOT / "results" / "leaderboard.csv"
OUT = ROOT / "docs" / "assets"
OUT.mkdir(parents=True, exist_ok=True)

rows = list(csv.DictReader(open(LB)))

def cell(model, task):
    for r in rows:
        if r["model"] == model and r["task"] == task:
            return (float(r["value"]), float(r["ci_lo"]), float(r["ci_hi"]))
    return None

# ---------------- F2: leaderboard overview ----------------
TASKS_ACC = ["MB-2001", "MB-2002", "MB-2003"]
TASKS_MAE = ["MB-2005", "MB-2006"]
FRONTIER = ["amazon", "deepseek", "google", "meta-llama", "nvidia",
            "openai", "qwen"]  # leaderboard groups by family prefix
COMPACT = [
    ("qwen3-0.6b-masld", "0.6B-v3"), ("qwen3-0.6b-masld-v5", "0.6B-v5"),
    ("qwen3-0.6b-masld-v6", "0.6B-v6"),
    ("qwen3-1.7b-masld", "1.7B-v3"), ("qwen3-1.7b-masld-v5", "1.7B-v5"),
    ("qwen3-1.7b-masld-v6", "1.7B-v6"),
]
# dedupe frontier families -> one row per (family, task) best archive entry:
# leaderboard uses model names like 'openai' twice (4.1-mini & 4o-mini) — take best.
def frontier_best(task, metric_min):
    best = {}
    for r in rows:
        m = r["model"]
        if m.startswith("qwen3-") or m in ("majority",):
            continue
        key = m
        val = float(r["value"])
        if r["task"] != task:
            continue
        if key not in best:
            best[key] = (val, float(r["ci_lo"]), float(r["ci_hi"]), m)
        else:
            cur = best[key][0]
            if (val < cur) if metric_min else (val > cur):
                best[key] = (val, float(r["ci_lo"]), float(r["ci_hi"]), m)
    return best

fig, axes = plt.subplots(1, 2, figsize=(13, 6.2), gridspec_kw={"width_ratios": [3, 2]})
ax = axes[0]
labels, xs = [], []
for i, t in enumerate(TASKS_ACC):
    fb = frontier_best(t, metric_min=False)
    for fam, (v, lo, hi, m) in sorted(fb.items()):
        ax.errorbar(i + np.random.default_rng(4 + i).uniform(-0.18, 0.18, 1)[0] * 0,
                    v, yerr=[[v - lo], [hi - v]], fmt="o", color="#9ecae1",
                    ecolor="#9ecae1", alpha=.85, capsize=2)
        labels.append((fam, i, v)) if False else None
for j, (mod, name) in enumerate(COMPACT):
    for i, t in enumerate(TASKS_ACC):
        c = cell(mod, t)
        if c:
            ax.errorbar(i + (j - 2.5) * 0.045, c[0], yerr=[[c[0] - c[1]], [c[2] - c[0]]],
                        fmt="s", color=plt.cm.viridis((j + 1) / 7), capsize=2, ms=5)
maj = {"MB-2001": 0.6607, "MB-2002": 0.262, "MB-2003": 0.5}
for i, t in enumerate(TASKS_ACC):
    ax.hlines(maj[t], i - 0.3, i + 0.3, color="crimson", ls="--", lw=1.2)
ax.set_xticks(range(3)); ax.set_xticklabels(["binary\n(MB-2001)", "multiclass\n(MB-2002)", "pairwise\n(MB-2003)"])
ax.set_ylabel("accuracy (bootstrapped 95% CI)")
ax.set_title("A  MB-20xx classification — frontier (○, family-best) vs compact (■)")
ax.text(0.99, 0.02, "dashed = majority", transform=ax.transAxes, ha="right",
        color="crimson", fontsize=8)

ax = axes[1]
for j, t in enumerate(TASKS_MAE):
    fb = frontier_best(t, metric_min=True)
    for fam, (v, lo, hi, m) in fb.items():
        ax.errorbar(j - 0.15, v, yerr=[[v - lo], [hi - v]], fmt="o",
                    color="#9ecae1", capsize=2)
for j, (mod, name) in enumerate(COMPACT):
    for i, t in enumerate(TASKS_MAE):
        c = cell(mod, t)
        if c and c[0] < 20:  # clip digit-loop artifacts (noted in text)
            ax.errorbar(i + (j - 2.5) * 0.09, c[0], yerr=[[max(c[0] - c[1], 0)], [c[2] - c[0]]],
                        fmt="s", color=plt.cm.viridis((j + 1) / 7), capsize=2, ms=5)
ax.hlines(1.76, -0.3, 1.3, color="green", ls=":", lw=1.5)
ax.text(1.28, 1.76, "ML EN", color="green", fontsize=8, va="center")
ax.set_xticks(range(2)); ax.set_xticklabels(["fibrosis MAE\n(MB-2005)", "NAS MAE\n(MB-2006)"])
ax.set_yscale("log"); ax.set_ylabel("MAE (log; lower better)")
ax.set_title("B  regression — compact beats frontier on MB-2005")
fig.suptitle("F2 · MASLD-Bench frozen-test leaderboard (9 frontier refs, 6 compact variants)", y=1.0)
fig.tight_layout()
fig.savefig(OUT / "fig2_leaderboard.png", dpi=200, bbox_inches="tight")
plt.close(fig)

# ---------------- F3: paired C2 forest, MB-2005 ----------------
fig, ax = plt.subplots(figsize=(8.5, 6))
entries = []
for r in csv.DictReader(open(ROOT / "results" / "c2_significance.csv")):
    if r["candidate"] == "qwen3-1.7b-masld" and r["task"] == "MB-2005":
        entries.append((f"{r['reference']} (p={float(r['wilcoxon_p']):.1e})", float(r["ref_value"]), "ref"))
for mod, name in [("qwen3-1.7b-masld-v5", "1.7B-v5"), ("qwen3-1.7b-masld-v6", "1.7B-v6")]:
    c = cell(mod, "MB-2005")
    if c:
        entries.append((name, c[0], "cand"))
entries.sort(key=lambda e: e[1])
ys = np.arange(len(entries))
fb50 = frontier_best("MB-2005", metric_min=True)
for y, (label, v_c2, kind) in zip(ys, entries):
    if kind == "cand":
        m = "v5" if "v5" in label else "v6"
        c = cell(f"qwen3-1.7b-masld-{m}", "MB-2005")
        v, color = c[0], "#08519c"
    else:
        fam = label.split(" ")[0]
        c = fb50.get(fam)
        v, color = c[0], "#9ecae1"
    ax.errorbar(v, y, xerr=[[max(v - c[1], 0)], [max(c[2] - v, 0)]],
                fmt="o" if kind == "ref" else "s", color=color, capsize=3, ms=6)
ax.hlines(1.76, *ax.get_xlim(), color="green", ls=":", lw=1.5)
ax.text(ax.get_xlim()[1], 1.76, " ML EN", color="green", fontsize=8, va="bottom", ha="right")
ax.set_yticks(ys); ax.set_yticklabels([e[0] for e in entries], fontsize=9)
ax.set_xlabel("MB-2005 fibrosis-stage MAE on the frozen EPos test (lower = better)")
ax.set_title("F3 · Paired C2: 1.7B compact vs frontier references\n(wilcoxon p from the 929-item paired frame)")
fig.tight_layout()
fig.savefig(OUT / "fig3_paired_forest.png", dpi=200, bbox_inches="tight")
plt.close(fig)

# ---------------- F5: C3 matrix ----------------
gates = json.load(open(ROOT / "results" / "c3a_gate_85_87.json"))
g86 = json.load(open(ROOT / "results" / "c3a_gate.json"))
PANELS = [
    ("MB-8501\nprogression", "acc", 0.904,
     {"logreg": gates["MB-8501"]["logreg"]["acc"],
      "0.6B-v5": None, "1.7B-v5": 0.173, "0.6B-v6": 0.269, "1.7B-v6": 0.846}),
    ("MB-8505\nordinal", "mae", 0.096,
     {"logreg": gates["MB-8505"]["logreg"]["mae"],
      "0.6B-v5": None, "1.7B-v5": None, "0.6B-v6": None, "1.7B-v6": None}),
    ("MB-8601\nblood 3-class", "acc", 0.35,
     {"logreg": g86["MB-8601"]["logreg"]["acc"],
      "0.6B-v5": 0.35, "1.7B-v5": 0.25, "0.6B-v6": 0.40, "1.7B-v6": 0.30}),
    ("MB-8602\nblood binary", "acc", 0.50,
     {"logreg": g86["MB-8602"]["logreg"]["acc"],
      "0.6B-v5": 0.50, "1.7B-v5": 0.50, "0.6B-v6": 0.571, "1.7B-v6": 0.429}),
    ("MB-8701\nplatform", "acc", 0.350,
     {"logreg": 1.000, "0.6B-v5": 0.320, "1.7B-v5": 0.257, "0.6B-v6": 0.0, "1.7B-v6": 0.398}),
    ("MB-8705\nmasked protein", "mae", 0.818,
     {"logreg": 0.814, "0.6B-v5": None, "1.7B-v5": 1.151, "0.6B-v6": None, "1.7B-v6": None}),
    ("MB-8801\nPHH FFA", "acc", 0.500,
     {"logreg": 0.833, "0.6B-v5": 0.500, "1.7B-v5": 0.433, "0.6B-v6": 0.533, "1.7B-v6": 0.500}),
]
fig, axes = plt.subplots(1, len(PANELS), figsize=(16, 3.6))
for ax, (title, kind, baseline, series) in zip(axes, PANELS):
    names = [n for n, v in series.items() if v is not None]
    vals = [series[n] for n in names]
    colors = ["#74c47d" if n == "logreg" else "#9ecae1" for n in names]
    ax.bar(range(len(names)), vals, color=colors)
    ax.axhline(baseline, color="crimson", ls="--", lw=1.2)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels([n.replace("logreg", "logreg\n(classical)") for n in names],
                       rotation=45, ha="right", fontsize=7.5)
    ax.set_title(title, fontsize=9)
    lo, hi = (0, max(max(vals + [baseline]) * 1.15, 0.01)) if kind == "acc" else (0, max(vals + [baseline]) * 1.15)
    ax.set_ylim(lo, hi)
    if kind == "mae":
        ax.text(0.02, 0.92, "MAE: lower=better\ndashed=constant", transform=ax.transAxes,
                fontsize=6.5, color="crimson")
fig.suptitle("F5 · C3 novel families: classical gate vs compact LLMs (zero-shot v5 / trained-on v6); dashed = majority/constant baseline",
             y=1.04, fontsize=10)
fig.tight_layout()
fig.savefig(OUT / "fig5_c3_matrix.png", dpi=200, bbox_inches="tight")
plt.close(fig)

print("wrote fig2/fig3/fig5 to", OUT)
