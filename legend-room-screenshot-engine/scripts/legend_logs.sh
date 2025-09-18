#!/usr/bin/env bash
set -euo pipefail
: "${RENDER_TOKEN:?missing RENDER_TOKEN}"

TARGET="${1:-api}" # api|shots
case "$TARGET" in
  api)   : "${API_SERVICE_ID:?missing API_SERVICE_ID}";   SID="$API_SERVICE_ID" ;;
  shots) : "${SHOTS_SERVICE_ID:?missing SHOTS_SERVICE_ID}"; SID="$SHOTS_SERVICE_ID" ;;
  *) echo "Usage: $0 [api|shots]"; exit 1 ;;
esac

curl -fsS "https://api.render.com/v1/services/${SID}/logs?limit=200" \
  -H "Authorization: Bearer ${RENDER_TOKEN}" | jq -r '.logs[]?.message' | tail -100
