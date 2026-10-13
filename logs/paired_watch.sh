#!/bin/zsh
while true; do
  if ! pgrep -f eval_paired_06b > /dev/null; then
    osascript -e 'display notification "paired 0.6B eval finished - see logs/paired_eval.log" with title "MASLD-LLM"'
    exit 0
  fi
  sleep 120
done
