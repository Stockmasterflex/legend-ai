# Legend AI — Codex Context & Ops

This repo is wired to secrets loaded via `direnv` from `~/.legend-ai/env.sh`.

## Primary Endpoints
- API  : $LEGEND_API/healthz
- Shots: $LEGEND_SHOTS/healthz
- FE   : $LEGEND_FRONTEND

Common API routes:
- GET $LEGEND_API/api/v1/signals?symbol=NVDA
- GET $LEGEND_API/api/v1/chart?symbol=NVDA

## Deploy
- Backend (Render): POST https://api.render.com/v1/services/$API_SERVICE_ID/deploys  (Auth: Bearer $RENDER_TOKEN)
- Frontend (Vercel): POST $VERCEL_DEPLOY_HOOK_URL
- Shots (Render): POST https://api.render.com/v1/services/$SHOTS_SERVICE_ID/deploys  (Auth: Bearer $RENDER_TOKEN)

## Quick Commands
- Health:    ./scripts/legend_check.sh
- Deploy:    ./scripts/legend_deploy.sh
- Logs:      ./scripts/legend_logs.sh [api|shots]

## ENV (loaded by direnv)
- Vercel: $VERCEL_DEPLOY_HOOK_URL, $VERCEL_TOKEN
- Render: $RENDER_TOKEN, $API_SERVICE_ID, $SHOTS_SERVICE_ID
- Backend: $SERVICE_DATABASE_URL, $REDIS_URL, $ALLOWED_ORIGINS, $ALLOWED_ORIGIN_REGEX, $VCP_PROVIDER, $NEWSAPI_KEY
- Shots: $CLOUDINARY_URL ($CLOUDINARY_API_KEY/$CLOUDINARY_API_SECRET/$CLOUDINARY_CLOUD_NAME), $PUPPETEER_EXECUTABLE_PATH, $DRY_RUN

## Rules for Codex
- Do not print secrets.
- Use env vars in code/config.
- Keep API contracts stable.
