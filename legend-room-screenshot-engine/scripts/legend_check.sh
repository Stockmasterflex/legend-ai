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
