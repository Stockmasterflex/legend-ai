#!/usr/bin/env bash
set -euo pipefail
for s in api shots fe; do
  if tmux has-session -t "$s" 2>/dev/null; then
    tmux kill-session -t "$s"
    echo "⏹  stopped $s"
  fi
done