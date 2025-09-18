#!/usr/bin/env bash
set -euo pipefail
: "${LEGEND_API:?missing env}"; : "${LEGEND_SHOTS:?missing env}"
echo "API /healthz …"
curl -s "${LEGEND_API}/healthz" && echo
echo "Signals (NVDA) …"
curl -s "${LEGEND_API}/api/v1/signals?symbol=NVDA" | jq '.signal.score, .signal.label'
echo "Shots (NVDA) …"
curl -s "${LEGEND_SHOTS}/screenshot?symbol=NVDA" | jq
echo "API → chart (NVDA) …"
curl -s "${LEGEND_API}/api/v1/chart?symbol=NVDA" | jq
echo "Weekly scan (WEDGE, timeframe=1wk) …"
curl -s "${LEGEND_API}/api/v1/scan?pattern=wedge&universe=sp500&timeframe=1wk&limit=3" | jq '{count:.count, sample:.results[0]}'
echo "Chart overlay POST (AAPL) …"
curl -sX POST "${LEGEND_API}/api/v1/chart?symbol=AAPL" \
  -H 'content-type: application/json' \
  -d '{"overlays":{"priceLevels":{"entry":170,"stop":164,"targets":[182]},"lines":[{"x1":"2024-04-01","y1":168,"x2":"2024-04-20","y2":166,"dash":true}]}}' | jq '{chart_url, meta}'
