#!/usr/bin/env bash
set -euo pipefail

cd "${HOME}/Projects/LegendAI"
source ~/.legend-ai/env.sh 2>/dev/null || true

REQ=(API_SERVICE_ID SHOTS_SERVICE_ID RENDER_TOKEN VERCEL_DEPLOY_HOOK_URL LEGEND_API LEGEND_SHOTS)
MISS=(); for v in "${REQ[@]}"; do [[ -z "${!v:-}" ]] && MISS+=("$v"); done
if (( ${#MISS[@]} )); then echo "❌ Missing: ${MISS[*]} (add to ~/.legend-ai/env.sh)"; exit 1; fi

echo "➡️ Deploy SHOTS"
curl -fsS -X POST "https://api.render.com/v1/services/${SHOTS_SERVICE_ID}/deploys" \
  -H "Authorization: Bearer ${RENDER_TOKEN}" >/dev/null && echo "   ✓ shots deploy triggered"

echo "➡️ Deploy API"
curl -fsS -X POST "https://api.render.com/v1/services/${API_SERVICE_ID}/deploys" \
  -H "Authorization: Bearer ${RENDER_TOKEN}" >/dev/null && echo "   ✓ api deploy triggered"

echo "➡️ Trigger Vercel"
curl -fsS -X POST "${VERCEL_DEPLOY_HOOK_URL}" >/dev/null && echo "   ✓ vercel hook sent"

# Poll helpers
poll() { name="$1"; url="$2"; n=40; d=5; echo "⏳ $name"; for((i=1;i<=n;i++));do curl -fsS "$url" >/dev/null && { echo "   ✓ up"; return 0; }; sleep $d; done; echo "   ⚠️ not up"; return 1; }

poll "API /healthz"   "$LEGEND_API/healthz"   || true
poll "SHOTS /healthz" "$LEGEND_SHOTS/healthz" || true

echo "🔎 Health summaries:"
curl -fsS "$LEGEND_API/healthz"   | jq
curl -fsS "$LEGEND_SHOTS/healthz" | jq

echo "🔎 Chart NVDA"
curl -fsS "$LEGEND_API/api/v1/chart?symbol=NVDA" | jq '{chart_url, meta}'

echo "🔎 Scan VCP (OK if empty)"
curl -fsS "$LEGEND_API/api/v1/scan?universe=nasdaq100&pattern=VCP&limit=10" | jq '.count, .results[0]'

echo "✅ Warp Tab 2 done."