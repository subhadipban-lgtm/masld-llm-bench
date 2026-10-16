#!/bin/zsh
# Waits for the bracket run to finish, then scores + commits + notifies.
cd /Users/subhadipbanerjee/masld-llm/platform
while pgrep -f bracket_run.sh >/dev/null; do sleep 120; done
echo "[$(date +%T)] bracket finished; scoring" >> /Users/subhadipbanerjee/masld-llm/logs/bracket_finish.log
.venv/bin/python cli.py score --archive-dir /Users/subhadipbanerjee/masld-llm/results/frontier_runs \
  --out-csv /Users/subhadipbanerjee/masld-llm/results/leaderboard.csv >> /Users/subhadipbanerjee/masld-llm/logs/bracket_finish.log 2>&1
cd /Users/subhadipbanerjee/masld-llm
git add -A && git commit -q -m "bracket top-up: +4 frontier models (gpt-4o-mini, llama-3.3-70b, qwen-2.5-72b, gpt-4.1-mini, nova-pro); B4 resolved (7 full-coverage models); leaderboard rescored" >> logs/bracket_finish.log 2>&1
osascript -e 'display notification "Frontier bracket complete; leaderboard rescored" with title "MASLD-LLM"'
echo "[$(date +%T)] done" >> /Users/subhadipbanerjee/masld-llm/logs/bracket_finish.log
