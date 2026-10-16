#!/bin/zsh
# MASLD-LLM autopilot — watches for 1.7B training/eval artifacts and acts.
# Installed as a LaunchAgent: runs every 10 minutes, no terminal needed.
#
# What it does:
#   1. Detects training completion (train_results.json with >= 2 epochs)
#      -> notifies via macOS notification
#   2. Detects finished eval files (qwen3-1.7b-masld__*.jsonl.gz)
#      -> runs the scorer, appends to RUNLOG, notifies with scores
#   3. Detects trainer stalls (log unchanged for > 45 min mid-training)
#      -> notifies (you reconnect Colab; training auto-resumes)
# State lives in ~/.openclaw/tmp/masld_autopilot_state.json - idempotent.

VENV=/Users/subhadipbanerjee/masld-llm/platform/.venv/bin/python
ROOT=/Users/subhadipbanerjee/masld-llm
STATE=$HOME/.openclaw/tmp/masld_autopilot_state.json
LOG=$ROOT/logs/autopilot.log

mkdir -p $HOME/.openclaw/tmp
echo "[$(date +%F\ %T)] autopilot tick" >> $LOG

$VENV <<'EOF' >> $ROOT/logs/autopilot.log 2>&1
import json, os, subprocess, time
from datetime import datetime

ROOT = "/Users/subhadipbanerjee/masld-llm"
STATE = os.path.expanduser("~/.openclaw/tmp/masld_autopilot_state.json")

def notify(title, msg):
    script = f'display notification "{msg}" with title "{title}"'
    subprocess.run(["osascript", "-e", script], capture_output=True)

def load_state():
    try:
        return json.load(open(STATE))
    except Exception:
        return {}

def save_state(s):
    json.dump(s, open(STATE, "w"), indent=1)

s = load_state()

# --- 1. training completion ---
tr = f"{ROOT}/checkpoints/qwen3-1.7b-masld-sft/train_results.json"
if os.path.exists(tr) and not s.get("train_done_17b"):
    try:
        res = json.load(open(tr))
        if float(res.get("epoch", 0)) >= 2.0:
            notify("MASLD-LLM 1.7B", f"Training complete: {res.get('train_loss', '?')} loss, {res.get('epoch')} epochs. Run cell 20 (merge+eval) in Colab.")
            s["train_done_17b"] = True
            save_state(s)
    except Exception:
        pass

# --- 2. eval files landed ---
for run_name, key in [("qwen3-1.7b-masld__MB-20xx.jsonl.gz", "eval_raw_17b"),
                      ("qwen3-1.7b-masld__MB-40xx.jsonl.gz", "eval_geo_17b")]:
    p = f"{ROOT}/results/frontier_runs/{run_name}"
    if os.path.exists(p):
        mtime = os.path.getmtime(p)
        if not s.get(key) or s[key] < mtime:
            # new/updated eval file -> score it
            r = subprocess.run(["/Users/subhadipbanerjee/masld-llm/platform/.venv/bin/python",
                                f"{ROOT}/scripts/score_frontier.py"],
                               capture_output=True, text=True, cwd=ROOT)
            ok = r.returncode == 0
            with open(f"{ROOT}/RUNLOG.md", "a") as f:
                f.write(f"\n### autopilot {datetime.now().isoformat(timespec='minutes')}\n")
                f.write(f"- detected {run_name} -> scored {'OK' if ok else 'FAILED'}\n")
            notify("MASLD-LLM eval scored", f"{run_name} {'scored; see leaderboard.csv' if ok else 'scoring failed - check logs'}")
            s[key] = mtime
            save_state(s)

# --- 3. trainer stall detection ---
tl = f"{ROOT}/checkpoints/qwen3-1.7b-masld-sft/trainer_log.jsonl"
if os.path.exists(tl):
    age = time.time() - os.path.getmtime(tl)
    log_done = os.path.exists(f"{ROOT}/checkpoints/qwen3-1.7b-masld-sft/train_results.json")
    if age > 2700 and not log_done and not s.get("stall_notified", 0) or \
       (age > 2700 and not log_done and time.time() - s.get("stall_notified", 0) > 14400):
        notify("MASLD-LLM training stalled?", f"Trainer log unchanged for {age/60:.0f} min. Check Colab; reconnect if needed (auto-resumes).")
        s["stall_notified"] = time.time()
        save_state(s)
print("autopilot: pass complete")
EOF
