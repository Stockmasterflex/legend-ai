#!/usr/bin/env bash
# Legend AI: Deploy and Verify Fix (with Vercel Deploy Hook)
# Expects RENDER_TOKEN, VERCEL_TOKEN to be set in the environment.
# Optional: VERCEL_DEPLOY_HOOK_URL, VERCEL_TEAM_ID

set -euo pipefail

echo "🚀 Legend AI: Deploy and Verify Fix"
echo "=================================="

# Require tokens from environment (do not print them)
: "${RENDER_TOKEN:?RENDER_TOKEN is not set in the environment}"
: "${VERCEL_TOKEN:?VERCEL_TOKEN is not set in the environment}"

# Service and project IDs (discovered via APIs)
SERVICE_ID="srv-d33kus6mcj7s73afodng"
PROJECT_ID="prj_OVUp69Fr1bmHENNsmxh80kwMkqc1"
TEAM_ID="${VERCEL_TEAM_ID:-team_ECQfsPVlEgANIrtznNs33qTh}"

LEGEND_API="https://legend-api.onrender.com"
LEGEND_FRONTEND="https://legend-ai.vercel.app"

echo "📋 Using:"
echo "  Render Service: $SERVICE_ID"
echo "  Vercel Project: $PROJECT_ID"
echo "  Team: $TEAM_ID"
echo ""

echo "🔧 Step 1: Redeploy Render backend"
echo "=================================="

response=$(curl -sS -X POST \
  "https://api.render.com/v1/services/${SERVICE_ID}/deploys" \
  -H "Authorization: Bearer ${RENDER_TOKEN}" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  --data '{}')

if command -v jq >/dev/null 2>&1; then
  deploy_id=$(echo "$response" | jq -r 'select(. != null) | .id // empty')
else
  deploy_id=$(echo "$response" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4 || true)
fi

if [ -z "${deploy_id:-}" ]; then
    echo "❌ Failed to trigger Render deploy"
    echo "Response: $response"
    exit 1
fi

echo "✅ Deploy triggered! ID: $deploy_id"
echo "⏳ Waiting for Render deployment..."

# Wait for deployment (max 10 minutes)
for i in {1..60}; do
    sleep 10
    status=$(curl -sS -H "Authorization: Bearer ${RENDER_TOKEN}" \
      "https://api.render.com/v1/services/${SERVICE_ID}/deploys/${deploy_id}")

    if command -v jq >/dev/null 2>&1; then
      status_val=$(echo "$status" | jq -r '.status // empty')
    else
      status_val=$(echo "$status" | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || true)
    fi

    echo "[$i/60] Status: ${status_val:-unknown}"

    if [ "${status_val:-}" = "live" ]; then
        echo "🎉 Render deployment successful!"
        break
    elif [ "${status_val:-}" = "build_failed" ] || [ "${status_val:-}" = "deploy_failed" ]; then
        echo "❌ Render deployment failed"
        exit 1
    fi

    if [ "$i" -eq 60 ]; then
        echo "⌛ Timed out waiting for Render deployment"
        exit 1
    fi

done

echo ""
echo "🌐 Step 2: Redeploy Vercel frontend"
echo "==================================="

if [ -n "${VERCEL_DEPLOY_HOOK_URL:-}" ]; then
  echo "Triggering Vercel deploy via Deploy Hook..."
  hook_resp=$(curl -sS -X POST "$VERCEL_DEPLOY_HOOK_URL" \
    -H "Accept: application/json" \
    -H "Content-Type: application/json" \
    --data '{}' || true)

  # Determine timestamp (ms) to look for new deployments after the hook
  if command -v jq >/dev/null 2>&1; then
    hook_ts=$(echo "$hook_resp" | jq -r '.job.createdAt // empty')
  else
    hook_ts=$(echo "$hook_resp" | grep -o '"createdAt":[0-9]\+' | head -1 | cut -d':' -f2)
  fi
  # Fallback: current time in ms if hook response didn't contain createdAt
  if [ -z "${hook_ts:-}" ]; then
    hook_ts=$(($(date +%s)*1000))
  fi

  echo "⏳ Waiting for Vercel deployment..."
  # Wait for up to 5 minutes
  for i in {1..30}; do
    dep_json=$(curl -sS -H "Authorization: Bearer ${VERCEL_TOKEN}" \
      "https://api.vercel.com/v6/deployments?projectId=${PROJECT_ID}&teamId=${TEAM_ID}&limit=5")

    if command -v jq >/dev/null 2>&1; then
      vercel_id=$(echo "$dep_json" | jq -r --argjson ts "$hook_ts" \
        '.deployments | map(select(.created > $ts)) | sort_by(.created) | last | .uid // empty')
      state=$(echo "$dep_json" | jq -r --arg uid "$vercel_id" \
        '.deployments[] | select(.uid==$uid) | .state // empty')
    else
      vercel_id=$(echo "$dep_json" | grep -o '"uid":"[^"]*"' | head -1 | cut -d'"' -f4 || true)
      state=$(echo "$dep_json" | grep -o '"state":"[^"]*"' | head -1 | cut -d'"' -f4 || true)
    fi

    if [ -n "${vercel_id:-}" ]; then
      echo "[$i/30] State: ${state:-unknown} id: $vercel_id"
      if [ "${state:-}" = "READY" ]; then
        echo "🎉 Vercel deployment successful!"
        break
      elif [ "${state:-}" = "ERROR" ]; then
        echo "❌ Vercel deployment failed"
        exit 1
      fi
    else
      echo "[$i/30] Waiting for deployment..."
    fi

    if [ "$i" -eq 30 ]; then
      echo "⌛ Timed out waiting for Vercel deployment"
      exit 1
    fi

    sleep 10
  done
else
  echo "ℹ️  VERCEL_DEPLOY_HOOK_URL not set; skipping Vercel deploy. Set it to enable automatic redeploy."
fi

echo ""
echo "🔍 Step 3: Testing everything"
echo "============================="

echo "Testing API health..."
health_response=$(curl -sS "${LEGEND_API}/healthz" || echo "failed")
if echo "$health_response" | grep -qE "healthy|ok|\"ok\":true"; then
    echo "✅ API health check passed"
else
    echo "⚠️  API health check failed: $health_response"
fi

echo ""
echo "Testing chart generation..."
chart_response=$(curl -sS "${LEGEND_API}/api/v1/chart?symbol=AAPL" || echo "failed")
if echo "$chart_response" | grep -q "chart_url"; then
    chart_url=$(echo "$chart_response" | grep -o '"chart_url":"[^"]*"' | cut -d'"' -f4)
    echo "✅ Chart API working! URL: $chart_url"
else
    echo "ℹ️  Chart API response did not include chart_url. Raw (truncated):"
    echo "$chart_response" | sed -n '1,5p'
fi

echo ""
echo "Testing frontend..."
frontend_status=$(curl -sS -o /dev/null -w "%{http_code}" "$LEGEND_FRONTEND" || echo "000")
if [ "$frontend_status" = "200" ]; then
    echo "✅ Frontend is live!"
else
    echo "⚠️  Frontend status: $frontend_status"
fi

echo ""
echo "🎯 Summary"
echo "=========="
echo "✅ Backend redeployed"
echo "✅ Frontend redeployed (if hook set)"
echo "🔗 Test your charts at: $LEGEND_FRONTEND/demo"
echo ""
echo "Done! 🚀"
