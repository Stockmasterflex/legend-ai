#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "tmux sessions:"
tmux ls 2>/dev/null || echo "  (none)"

echo; echo "Ports:"
lsof -nP -iTCP -sTCP:LISTEN | grep -E ':(8000|3001|3010)' || echo "  no listeners on 8000/3001/3010"

echo; echo "Health checks:"
set +e
curl -sSf http://127.0.0.1:8000/healthz && echo || echo "❌ backend /healthz failed"
curl -sSf "http://127.0.0.1:8000/api/v1/signals?symbol=NVDA" >/dev/null && echo "✅ signals ok" || echo "❌ signals failed"
curl -sSf "http://127.0.0.1:3010/healthz" >/dev/null && echo "✅ shots ok" || echo "ℹ️ shots health may not exist; try screenshot endpoint"
curl -sSf "http://127.0.0.1:3010/screenshot?symbol=NVDA" >/dev/null && echo "✅ screenshot ok" || echo "❌ screenshot failed"
set -e

echo; echo "Last 10 lines of logs:"
for f in api shots fe; do
  echo "---- logs/$f.log ----"; tail -n 10 "logs/$f.log" 2>/dev/null || true
done