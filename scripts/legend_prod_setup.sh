#!/usr/bin/env bash
set -euo pipefail

# ================================
# 🚀 LEGEND AI — A→D PROD SETUP RUN
#  A) Finalize Sanity (env + webhook check)
#  B) Shots real screenshots
#  C) Optional: Giscus comments vars
#  D) Deploy + end-to-end smoke tests
# ================================

PROJECT_DIR="${HOME}/Projects/LegendAI"
FRONT_DEFAULT="https://legend-ai.vercel.app"

# -------- 0) Enter repo + env --------
cd "$PROJECT_DIR"
source ~/.legend-ai/env.sh 2>/dev/null || true

FRONT="${LEGEND_FRONTEND:-$FRONT_DEFAULT}"

REQUIRED=(LEGEND_API LEGEND_SHOTS API_SERVICE_ID SHOTS_SERVICE_ID RENDER_TOKEN VERCEL_DEPLOY_HOOK_URL)
MISSING=()
for v in "${REQUIRED[@]}"; do
  if [ -z "${!v:-}" ]; then MISSING+=("$v"); fi
done
if [ "${#MISSING[@]}" -gt 0 ]; then
  echo "❌ Missing required env(s): ${MISSING[*]}"
  echo "   Add them to ~/.legend-ai/env.sh and re-run."
  exit 1
fi

# Optional-but-recommended (blog live)
SANITY_OK=1
if [ -z "${NEXT_PUBLIC_SANITY_PROJECT_ID:-}" ] || [ -z "${NEXT_PUBLIC_SANITY_DATASET:-}" ]; then
  SANITY_OK=0
  echo "ℹ️ Sanity envs not set: NEXT_PUBLIC_SANITY_PROJECT_ID/NEXT_PUBLIC_SANITY_DATASET"
  echo "   Blog will render empty until these are set in Vercel and (optionally) .env.local"
fi
if [ -z "${SANITY_REVALIDATE_SECRET:-}" ]; then
  echo "ℹ️ SANITY_REVALIDATE_SECRET not set — /api/revalidate should be secured once Codex lands the patch."
fi

# -------- 1) Sanity quick checks (non-destructive) --------
if [ "$SANITY_OK" -eq 1 ]; then
  echo "✅ Sanity envs present: project=${NEXT_PUBLIC_SANITY_PROJECT_ID}, dataset=${NEXT_PUBLIC_SANITY_DATASET}"
  echo "   Remember to add a Sanity webhook → ${FRONT}/api/revalidate?secret=***"
else
  echo "⚠️ Skipping Sanity provisioning checks due to missing envs."
fi

# -------- 2) Ensure real screenshots in prod (env-based) --------
# These flags must be set on the Render 'legend-shots' service.
echo "ℹ️ Shots should run with: DRY_RUN=0 and a valid PUPPETEER_EXECUTABLE_PATH."
echo "   If you already set them in Render, great — we'll just redeploy."

# Trigger Render deploys (shots first, then API)
echo "➡️  Trigger Render deploy: shots"
curl -fsS -X POST "https://api.render.com/v1/services/${SHOTS_SERVICE_ID}/deploys" \
  -H "Authorization: Bearer ${RENDER_TOKEN}" >/dev/null && echo "   ✅ shots deploy triggered"

echo "➡️  Trigger Render deploy: API"
curl -fsS -X POST "https://api.render.com/v1/services/${API_SERVICE_ID}/deploys" \
  -H "Authorization: Bearer ${RENDER_TOKEN}" >/dev/null && echo "   ✅ api deploy triggered"

# Trigger Vercel deploy (frontend)
echo "➡️  Trigger Vercel deploy hook"
curl -fsS -X POST "${VERCEL_DEPLOY_HOOK_URL}" >/dev/null && echo "   ✅ vercel build triggered"

# -------- 3) Poll health (bounded retries) --------
poll() {
  local name="$1" url="$2" tries="${3:-30}" delay="${4:-5}"
  echo "⏳ Waiting for ${name} …"
  for ((i=1;i<=tries;i++)); do
    if curl -fsS "$url" >/dev/null; then
      echo "   ✅ ${name} is up"
      return 0
    fi
    sleep "$delay"
  done
  echo "   ❌ ${name} did not pass health within time"
  return 1
}

# API /healthz
poll "API /healthz" "${LEGEND_API}/healthz" 40 5 || true

# Shots smoke (use endpoint that always exists in your service)
echo "⏳ Probing shots screenshot…"
if curl -fsS "${LEGEND_SHOTS}/screenshot?symbol=NVDA" | jq '{ok, url, note}' ; then
  echo "   ✅ shots returned a payload (ok/url/note shown above)"
else
  echo "   ❌ shots screenshot probe failed (check Render env & logs)"
fi

# -------- 4) FE availability --------
echo "⏳ Checking FE pages…"
if curl -fsS "${FRONT}/" >/dev/null; then echo "   ✅ FE home reachable"; else echo "   ❌ FE home failed"; fi
if curl -fsS "${FRONT}/demo" >/dev/null; then echo "   ✅ FE demo reachable"; else echo "   ❌ FE demo failed"; fi
if curl -fsS "${FRONT}/blog" >/dev/null; then echo "   ✅ FE blog reachable"; else echo "   ❌ FE blog failed (expected empty until Sanity ready)"; fi

# -------- 5) Golden-path smoke --------
echo "🔎 API scan sample (first row)…"
curl -fsS "${LEGEND_API}/api/v1/scan?universe=nasdaq100&patterns=VCP,CupHandle&limit=3" | jq '.[0]' || echo "   ❌ scan returned error or empty"

echo "🔎 API chart (NVDA)…"
curl -fsS "${LEGEND_API}/api/v1/chart?symbol=NVDA" | jq '{url, overlays}' || echo "   ❌ chart failed"

# Optional revalidate ping (will be secured after Codex patch)
if [ -n "${SANITY_REVALIDATE_SECRET:-}" ]; then
  echo "↻ Pinging revalidate route…"
  curl -fsS -X POST "${FRONT}/api/revalidate?secret=${SANITY_REVALIDATE_SECRET}" \
    -H 'Content-Type: application/json' -d '{"slug":"test"}' | jq || true
fi

# -------- 6) Show quick logs if available --------
echo "🪵 Recent logs (API):"
./scripts/legend_logs.sh api || true
echo "🪵 Recent logs (shots):"
./scripts/legend_logs.sh shots || true

# -------- 7) Summary --------
echo ""
echo "========================================"
echo "   ✅ A→D run finished"
echo "   • API:      ${LEGEND_API}"
echo "   • Shots:    ${LEGEND_SHOTS}"
echo "   • Frontend: ${FRONT}"
if [ "$SANITY_OK" -eq 1 ]; then
  echo "   • Blog:     Sanity envs present — publish a post in /studio and confirm"
else
  echo "   • Blog:     Set NEXT_PUBLIC_SANITY_* (Vercel + .env.local), add webhook, then publish"
fi
echo "========================================"