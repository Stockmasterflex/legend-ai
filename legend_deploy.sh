#!/usr/bin/env bash
set -euo pipefail

: "${RENDER_TOKEN:?missing}"
: "${VERCEL_TOKEN:?missing}"
: "${VERCEL_DEPLOY_HOOK_URL:?missing}"
: "${API_SERVICE_ID:?missing}"

LEGEND_API="https://legend-api.onrender.com"
LEGEND_FRONTEND="https://legend-ai.vercel.app"

hdr_auth=(-H "Authorization: Bearer ${RENDER_TOKEN}" -H "Content-Type: application/json")

find_service_id () {
  local name="$1"
  curl -fsS "https://api.render.com/v1/services" -H "Authorization: Bearer ${RENDER_TOKEN}" \
  | jq -r --arg n "$name" '
      map(select((.name|ascii_downcase|contains($n)) or
                 (.serviceDetails.slug|tostring|ascii_downcase|contains($n))))[0].id // empty'
}

redeploy_render () {
  local sid="$1" label="$2"
  echo "🚀 Redeploying ${label} (${sid}) with cache clear…"
  local resp deploy_id status
  resp="$(curl -fsS -X POST "https://api.render.com/v1/services/${sid}/deploys" "${hdr_auth[@]}" -d '{"clearCache": true}')"
  deploy_id="$(jq -r '.id // empty' <<<"$resp")"
  [[ -n "$deploy_id" ]] || { echo "❌ could not trigger ${label} deploy: $resp"; exit 1; }

  echo "⏳ Waiting for ${label} to go live (deploy: $deploy_id)…"
  for i in {1..60}; do
    sleep 10
    status="$(curl -fsS "https://api.render.com/v1/services/${sid}/deploys/${deploy_id}" -H "Authorization: Bearer ${RENDER_TOKEN}" | jq -r '.status')"
    echo "  [$i/60] ${label}: $status"
    [[ "$status" == "live" ]] && { echo "✅ ${label} live"; return; }
    [[ "$status" == "build_failed" || "$status" == "deploy_failed" ]] && { echo "❌ ${label} failed"; exit 1; }
  done
  echo "❌ ${label} timeout"; exit 1
}

echo "🔎 Finding legend-shots service on Render…"
SHOTS_SERVICE_ID="$(find_service_id shots || true)"
if [[ -z "${SHOTS_SERVICE_ID:-}" ]]; then
  SHOTS_SERVICE_ID="$(find_service_id legend-room-screenshot-engine || true)"
fi
if [[ -z "${SHOTS_SERVICE_ID:-}" ]]; then
  echo "❌ Could not auto-find the legend-shots service. Export SHOTS_SERVICE_ID and re-run."
  exit 1
fi
echo "🆔 legend-shots service id: ${SHOTS_SERVICE_ID}"

echo "=== 1) Render: redeploy legend-shots ==="
redeploy_render "$SHOTS_SERVICE_ID" "legend-shots"

echo "=== 2) Render: redeploy legend-api ==="
redeploy_render "$API_SERVICE_ID" "legend-api"

echo "=== 3) Vercel: trigger Deploy Hook & poll to READY ==="
curl -fsS -X POST "$VERCEL_DEPLOY_HOOK_URL" >/dev/null
ready=0
for i in {1..30}; do
  sleep 10
  state="$(curl -fsS -H "Authorization: Bearer ${VERCEL_TOKEN}" "https://api.vercel.com/v6/deployments?app=legend-ai&limit=1" | jq -r '.deployments[0].state // .state // "unknown"')"
  echo "  [$i/30] Vercel state: $state"
  [[ "$state" == "READY" ]] && { ready=1; break; }
  [[ "$state" == "ERROR" ]] && { echo "❌ Vercel ERROR"; exit 1; }
done
[[ $ready -eq 1 ]] || { echo "❌ Vercel timeout"; exit 1; }
echo "✅ Vercel READY"

echo "=== 4) Health checks ==="
printf "API /healthz … "
if curl -fsS "$LEGEND_API/healthz" | grep -qiE 'ok|healthy'; then echo "✅"; else echo "⚠️"; fi

printf "legend-shots /healthz … "
if curl -fsS "https://legend-shots.onrender.com/healthz" | grep -qiE 'ok|true'; then echo "✅"; else echo "⚠️"; fi

echo -n "Chart API (AAPL) … "
chart_json="$(curl -fsS "$LEGEND_API/api/v1/chart?symbol=AAPL" || true)"
if echo "$chart_json" | jq -e 'has("chart_url") and (.chart_url|type=="string" and length>0)' >/dev/null 2>&1; then
  chart_url="$(jq -r '.chart_url' <<<"$chart_json")"
  echo "✅ $chart_url"
else
  echo "❌"
  echo "— Full response from API:"
  echo "$chart_json" | jq . || echo "$chart_json"

  echo; echo "=== legend-shots recent logs (last 100 lines) ==="
  curl -fsS "https://api.render.com/v1/services/${SHOTS_SERVICE_ID}/logs?limit=200" -H "Authorization: Bearer ${RENDER_TOKEN}" \
  | jq -r '.logs[]?.message' 2>/dev/null | tail -100 || echo "(no logs API / insufficient permissions)"
fi

printf "Frontend … "
code="$(curl -s -o /dev/null -w "%{http_code}" "$LEGEND_FRONTEND")"
[[ "$code" == "200" ]] && echo "✅" || echo "⚠️ ($code)"

echo
echo "🎉 Done. Open: $LEGEND_FRONTEND/demo → click “Chart ▾”."
