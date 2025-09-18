#!/usr/bin/env bash
set -euo pipefail

: "${RENDER_TOKEN:?missing}"
: "${VERCEL_TOKEN:?missing}"
: "${VERCEL_DEPLOY_HOOK_URL:?missing}"
: "${API_SERVICE_ID:?missing}"

LEGEND_API="https://legend-api.onrender.com"
LEGEND_FRONTEND="https://legend-ai.vercel.app"

hdr_auth=(-H "Authorization: Bearer ${RENDER_TOKEN}" -H "Content-Type: application/json" -H "Accept: application/json")

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

step () { echo; echo "=== $* ==="; }
ok () { echo "✅ $*"; }
warn () { echo "⚠️  $*"; }

step "0) Resolve legend-shots service id"
SHOTS_SERVICE_ID="${SHOTS_SERVICE_ID:-}"
if [[ -z "${SHOTS_SERVICE_ID:-}" ]]; then
  echo "🔎 Finding legend-shots service on Render…"
  SHOTS_SERVICE_ID="$(find_service_id shots || true)"
  if [[ -z "${SHOTS_SERVICE_ID:-}" ]]; then
    SHOTS_SERVICE_ID="$(find_service_id legend-room-screenshot-engine || true)"
  fi
fi
if [[ -z "${SHOTS_SERVICE_ID:-}" ]]; then
  echo "❌ Could not auto-find the legend-shots service. Name it with 'shots' or 'screenshot' in Render, or export SHOTS_SERVICE_ID=… and re-run."
  exit 1
fi
ok "legend-shots service id: ${SHOTS_SERVICE_ID}"

step "1) Render: redeploy legend-shots"
redeploy_render "$SHOTS_SERVICE_ID" "legend-shots"

step "2) Render: redeploy legend-api"
redeploy_render "$API_SERVICE_ID" "legend-api"

step "3) Vercel: trigger Deploy Hook & poll to READY"
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
ok "Vercel READY"

step "4) Health checks"
printf "API /healthz … "
if curl -fsS "$LEGEND_API/healthz" | grep -qiE 'ok|healthy'; then ok; else warn; fi

printf "legend-shots /healthz … "
if curl -fsS "https://legend-shots.onrender.com/healthz" | grep -qiE 'ok|true'; then ok; else warn; fi

step "5) Live scanner and chart tests"
# Pattern scan – 2 cases
printf "Scan VCP on S&P 500 … "
scan1="$(curl -fsS "$LEGEND_API/api/v1/scan/pattern?pattern=VCP&universe=sp500&limit=50" || true)"
rows1="$(jq -r '(.rows|length) // 0' <<<"$scan1" 2>/dev/null || echo 0)"
echo "$rows1 rows"

printf "Scan CUP on NASDAQ-100 … "
scan2="$(curl -fsS "$LEGEND_API/api/v1/scan/pattern?pattern=CUP&universe=nasdaq100&limit=50" || true)"
rows2="$(jq -r '(.rows|length) // 0' <<<"$scan2" 2>/dev/null || echo 0)"
echo "$rows2 rows"

# Chart with overlays
printf "Chart overlays (AAPL) … "
chart_json="$(curl -fsS "$LEGEND_API/api/v1/chart?symbol=AAPL&pivot=210&entry=211&stop=202&target=235&pattern=VCP" || true)"
url="$(jq -r '.chart_url // empty' <<<"$chart_json" 2>/dev/null || true)"
if [[ -n "$url" ]]; then
  code="$(curl -s -o /dev/null -w "%{http_code}" "$url")"
  if [[ "$code" == "200" ]]; then ok; else warn "($code)"; fi
else
  warn "no chart_url"
fi

step "6) Frontend /demo check"
code="$(curl -s -o /dev/null -w "%{http_code}" "$LEGEND_FRONTEND/demo")"
[[ "$code" == "200" ]] && ok || warn "($code)"

echo
ok "Deployment + checks complete"
