#!/usr/bin/env bash
set -euo pipefail

cd ~/Projects/LegendAI
source ~/.legend-ai/env.sh 2>/dev/null || true

REQUIRED=(LEGEND_API LEGEND_SHOTS API_SERVICE_ID SHOTS_SERVICE_ID RENDER_TOKEN VERCEL_DEPLOY_HOOK_URL)
MISS=(); for v in "${REQUIRED[@]}"; do [ -z "${!v:-}" ] && MISS+=("$v"); done
if [ "${#MISS[@]}" -gt 0 ]; then echo "❌ Missing: ${MISS[*]} (add to ~/.legend-ai/env.sh)"; exit 1; fi

# 1) Trigger deploys
echo "➡️  Render: shots";  curl -fsS -X POST "https://api.render.com/v1/services/${SHOTS_SERVICE_ID}/deploys" -H "Authorization: Bearer ${RENDER_TOKEN}" >/dev/null && echo "   ✅"
echo "➡️  Render: api";    curl -fsS -X POST "https://api.render.com/v1/services/${API_SERVICE_ID}/deploys"   -H "Authorization: Bearer ${RENDER_TOKEN}" >/dev/null && echo "   ✅"
echo "➡️  Vercel: FE";     curl -fsS -X POST "${VERCEL_DEPLOY_HOOK_URL}" >/dev/null && echo "   ✅"

# 2) Poll health
poll(){ local n="$1" u="$2"; echo "⏳ $n"; for i in {1..40}; do curl -fsS "$u" >/dev/null && echo "   ✅ $n" && return 0; sleep 5; done; echo "   ⚠️ $n not ready"; }
poll "API /healthz"   "$LEGEND_API/healthz"
poll "Shots /healthz" "$LEGEND_SHOTS/healthz"

# 3) Sanity quick-enable (local + reminder)
if [ -n "${NEXT_PUBLIC_SANITY_PROJECT_ID:-}" ] && [ -n "${NEXT_PUBLIC_SANITY_DATASET:-}" ]; then
  echo "✅ Sanity env present: $NEXT_PUBLIC_SANITY_PROJECT_ID / $NEXT_PUBLIC_SANITY_DATASET"
else
  echo "ℹ️ To enable blog now:"
  echo "   cd kyle-portfolio"
  echo "   npx sanity@latest init   # get projectId + dataset (e.g., production)"
  echo "   echo 'NEXT_PUBLIC_SANITY_PROJECT_ID=xxxx' >> .env.local"
  echo "   echo 'NEXT_PUBLIC_SANITY_DATASET=production' >> .env.local"
  echo "   # In Vercel project env, add the same + SANITY_REVALIDATE_SECRET, then redeploy."
fi

# 4) Smokes
echo "🔎 Chart";  curl -fsS "$LEGEND_API/api/v1/chart?symbol=NVDA" | jq '{chart_url,meta}'
echo "🔎 Scan";   curl -fsS "$LEGEND_API/api/v1/scan?universe=nasdaq100&pattern=VCP&limit=5" | jq
echo "🔎 Blog";   FRONT="${LEGEND_FRONTEND:-https://legend-ai.vercel.app}"; curl -s -o /dev/null -w "blog %{http_code}\n" "$FRONT/blog"