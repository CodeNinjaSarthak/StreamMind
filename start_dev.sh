#!/usr/bin/env bash
set -euo pipefail

SESSION="dev"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check tmux
if ! command -v tmux &>/dev/null; then
  echo "[start_dev] tmux not found. Install with: brew install tmux"
  exit 1
fi

# Attach if session already running
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "[start_dev] Session '$SESSION' already running — attaching..."
  tmux attach -t "$SESSION"
  exit 0
fi

# Detect venv
VENV=""
for candidate in "$ROOT/venv" "$ROOT/.venv" "$ROOT/backend/venv"; do
  if [ -f "$candidate/bin/activate" ]; then
    VENV="$candidate"
    break
  fi
done

if [ -z "$VENV" ]; then
  echo "[start_dev] No virtualenv found. Checked: venv/, .venv/, backend/venv/"
  echo "  Create one with: python -m venv venv && source venv/bin/activate && pip install -r backend/requirements.txt"
  exit 1
fi

echo "[start_dev] Using venv: $VENV"

NAMES=(
  "Backend (FastAPI)"
  "Classification"
  "Embeddings"
  "Clustering"
  "Answer Generation"
  "YouTube Polling"
  "YouTube Posting"
  "Scheduler"
  "Frontend (Vite)"
)
DIRS=(
  "$ROOT/backend"
  "$ROOT"
  "$ROOT"
  "$ROOT"
  "$ROOT"
  "$ROOT"
  "$ROOT"
  "$ROOT"
  "$ROOT/frontend"
)
CMDS=(
  "PYTHONPATH='$ROOT' uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
  "python workers/classification/worker.py"
  "python workers/embeddings/worker.py"
  "python workers/clustering/worker.py"
  "python workers/answer_generation/worker.py"
  "python workers/youtube_polling/worker.py"
  "python workers/youtube_posting/worker.py"
  "cd workers && python -m scheduler.worker"
  "npm run dev"
)

# Build the shell command for a given pane index.
# Env vars are sourced inside each pane so tmux inheritance is not relied upon.
# '; exec bash' keeps the pane open if the service crashes (useful for debugging).
pane_cmd() {
  local i=$1
  echo "source '${VENV}/bin/activate' && \
{ [ -f '${ROOT}/.env.development' ] && source '${ROOT}/.env.development' || true; } && \
{ [ -f '${ROOT}/backend/.env.development' ] && source '${ROOT}/backend/.env.development' || true; } && \
cd '${DIRS[$i]}' && echo -e '\033[1;34m=== ${NAMES[$i]} ===\033[0m' && ${CMDS[$i]}; exec bash"
}

# Create session with first pane
tmux new-session -d -s "$SESSION" -x "$(tput cols)" -y "$(tput lines)"

# Mouse + clipboard config
tmux set-option -t "$SESSION" mouse on
tmux set-option -t "$SESSION" set-clipboard on
tmux set-window-option -t "$SESSION" mode-keys vi
tmux bind-key -T copy-mode-vi MouseDragEnd1Pane send-keys -X copy-pipe-and-cancel "xclip -in -selection clipboard 2>/dev/null || pbcopy 2>/dev/null || true"
tmux bind-key -T copy-mode-vi Enter send-keys -X copy-pipe-and-cancel "xclip -in -selection clipboard 2>/dev/null || pbcopy 2>/dev/null || true"

tmux send-keys -t "$SESSION:0" "$(pane_cmd 0)" Enter

# Add remaining panes
for i in "${!NAMES[@]}"; do
  [ "$i" -eq 0 ] && continue
  tmux split-window -t "$SESSION:0" "$(pane_cmd "$i")"
  tmux select-layout -t "$SESSION:0" tiled
done

tmux select-layout -t "$SESSION:0" tiled
tmux attach -t "$SESSION"