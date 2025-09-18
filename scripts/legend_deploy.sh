#!/usr/bin/env bash
set -euo pipefail

: "${RENDER_TOKEN:?missing RENDER_TOKEN}"
: "${API_SERVICE_ID:?missing API_SERVICE_ID}"
: "${VERCEL_DEPLOY_HOOK_URL:?missing VERCEL_DEPLOY_HOOK_URL}"

echo "=== Render: deploy legend-api (${API_SERVICE_ID}) ==="
curl -fsS -X POST "https://api.render.com/v1/services/${API_SERVICE_ID}/deploys" \
  -H "Authorization: Bearer ${RENDER_TOKEN}" >/dev/null && echo "✅ Render (API) deploy triggered"

if [[ "${1:-}" == "shots" ]]; then
  : "${SHOTS_SERVICE_ID:?missing SHOTS_SERVICE_ID}"
  echo "=== Render: deploy legend-shots (${SHOTS_SERVICE_ID}) ==="
  curl -fsS -X POST "https://api.render.com/v1/services/${SHOTS_SERVICE_ID}/deploys" \
    -H "Authorization: Bearer ${RENDER_TOKEN}" >/dev/null && echo "✅ Render (shots) deploy triggered"
fi

echo "=== Vercel: trigger Deploy Hook ==="
curl -fsS -X POST "${VERCEL_DEPLOY_HOOK_URL}" >/dev/null && echo "✅ Vercel deploy hook sent"
