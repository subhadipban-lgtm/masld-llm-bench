#!/bin/zsh
# watcher: notify when k-shot ablation completes or dies
while true; do
  if ! pgrep -f ablation_06b_kshot > /dev/null; then
    osascript -e 'display notification "k-shot ablation finished or died - check logs/kshot_ablation.log" with title "MASLD-LLM"'
    exit 0
  fi
  sleep 300
done
