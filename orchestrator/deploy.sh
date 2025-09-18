#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Deploying Legend AI Services"
echo "==============================="
echo

# Check for required env vars
if [ -z "${RENDER_TOKEN:-}" ]; then
    echo "⚠️  RENDER_TOKEN not set - skipping Render deployments"
else
    if [ -n "${API_SERVICE_ID:-}" ]; then
        echo "Deploying API..."
        curl -X POST -H "Authorization: Bearer $RENDER_TOKEN" \
            "https://api.render.com/v1/services/$API_SERVICE_ID/deploys" \
            > /dev/null 2>&1 && echo "  ✅ API deployment triggered"
    fi

    if [ -n "${SHOTS_SERVICE_ID:-}" ]; then
        echo "Deploying Screenshots..."
        curl -X POST -H "Authorization: Bearer $RENDER_TOKEN" \
            "https://api.render.com/v1/services/$SHOTS_SERVICE_ID/deploys" \
            > /dev/null 2>&1 && echo "  ✅ Screenshots deployment triggered"
    fi
fi

if [ -n "${VERCEL_DEPLOY_HOOK_URL:-}" ]; then
    echo "Deploying Frontend..."
    curl -X POST "$VERCEL_DEPLOY_HOOK_URL" > /dev/null 2>&1 && \
        echo "  ✅ Frontend deployment triggered"
else
    echo "⚠️  VERCEL_DEPLOY_HOOK_URL not set - skipping frontend"
fi

echo
echo "✨ Deployments triggered - check service dashboards for status"
