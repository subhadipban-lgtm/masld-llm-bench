#!/bin/zsh
cd /Users/subhadipbanerjee/masld-llm/platform
export OPENROUTER_API_KEY=$(cat ~/.openclaw/tmp/or_key.txt | tr -d '\n\r ')
for M in "openai/gpt-4o-mini" "meta-llama/llama-3.3-70b-instruct" "qwen/qwen-2.5-72b-instruct" "openai/gpt-4.1-mini" "amazon/nova-pro-v1"; do
  echo "=== $(date +%T) running $M ==="
  .venv/bin/python cli.py run-frontier "$M" --n-per-task 300 2>&1 | tail -8
  echo "=== $(date +%T) done $M ==="
done
echo "ALL DONE $(date +%T)"
