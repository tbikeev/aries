#!/usr/bin/env bash
# Start Aries (Tauri dev) from the repo root. Logs: /tmp/aries-make-run.log
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
SESSION=aries-make-run
if command -v tmux >/dev/null 2>&1; then
  if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "Session '$SESSION' already running. Attach with:"
    echo "  tmux attach -t $SESSION"
    exit 0
  fi
  tmux new-session -d -s "$SESSION" -c "$ROOT" -- "${SHELL:-bash}" -lc "make run 2>&1 | tee /tmp/aries-make-run.log"
  echo "Started Aries in tmux session '$SESSION'."
  echo "  tmux attach -t $SESSION    # live log"
  echo "  tail -f /tmp/aries-make-run.log"
else
  echo "tmux not found; running make run in foreground."
  exec make run
fi
