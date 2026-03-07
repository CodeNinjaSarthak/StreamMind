#!/usr/bin/env bash
set -euo pipefail

SESSION="dev"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  tmux kill-session -t "$SESSION"
  echo "[stop_dev] Session '$SESSION' killed."
else
  echo "[stop_dev] No session '$SESSION' found."
fi
