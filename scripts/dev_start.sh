#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p logs

# Ensure env
[ -f .envrc ] || echo 'source ~/.legend-ai/env.sh' > .envrc
direnv allow >/dev/null 2>&1 || true
# shellcheck disable=SC1090
source ~/.legend-ai/env.sh 2>/dev/null || true

# --- Backend (uvicorn) on 8000 ---
if ! tmux has-session -t api 2>/dev/null; then
  tmux new-session -d -s api 'SHOTS_BASE_URL=${SHOTS_BASE_URL:-http://127.0.0.1:3010} python -m uvicorn service_api:app --host 0.0.0.0 --port 8000 --reload >> logs/api.log 2>&1'
  echo "▶️  api started (tmux session: api, log: logs/api.log)"
else
  echo "ℹ️  api already running"
fi

# --- Shots service on 3010 ---
if ! tmux has-session -t shots 2>/dev/null; then
  tmux new-session -d -s shots 'DRY_RUN=${DRY_RUN:-1} PUPPETEER_EXECUTABLE_PATH=${PUPPETEER_EXECUTABLE_PATH:-/usr/bin/chromium} node legend-room-screenshot-engine/server.js >> logs/shots.log 2>&1'
  echo "▶️  shots started (tmux session: shots, log: logs/shots.log)"
else
  echo "ℹ️  shots already running"
fi

# --- Frontend dev on 3001 (avoid prod 3000 conflicts) ---
if ! tmux has-session -t fe 2>/dev/null; then
  tmux new-session -d -s fe 'cd kyle-portfolio && npm install --silent && npm run dev -- -p 3001 >> ../logs/fe.log 2>&1'
  echo "▶️  fe started (tmux session: fe, log: logs/fe.log)"
else
  echo "ℹ️  fe already running"
fi