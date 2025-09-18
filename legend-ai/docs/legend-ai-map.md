# Legend AI – System Map (Curated)

This document summarizes the current architecture of Legend AI as implemented in this repository, distilled from the imported planning docs and aligned with the actual code and services.

Overview
- Frontend (Next.js): kyle-portfolio
  - Path: kyle-portfolio
  - Serves /demo and calls the API via NEXT_PUBLIC_VCP_API_BASE
  - Production: Vercel (vercel.json sets NEXT_PUBLIC_VCP_API_BASE)
- Backend API (FastAPI): legend-api
  - Entry: service_api.py
  - Provides indicators, signals, sentiment, VCP candidates/metrics, runs, and chart URL endpoints
  - Storage: lightweight SQLite for runs metadata; CSV/JSON artifacts under reports
  - Production: Render (render.yaml service: legend-api)
- Screenshot service (Node/Express + Puppeteer): legend-shots
  - Path: legend-room-screenshot-engine
  - Endpoint: GET /screenshot?symbol=TSLA → { chart_url }
  - Currently returns a deterministic dummy image URL; includes a Puppeteer smoke launch
  - Production: Render (render.yaml service: legend-shots)

Data Flow
1) Frontend calls Backend
   - /api/v1/vcp/today → table of candidates (sample fallback when needed)
   - /api/v1/vcp/metrics?start&end → KPI header and charts
   - /api/v1/indicators, /api/v1/signals, /api/v1/sentiment → per-symbol details
   - /api/v1/chart?symbol=NVDA → returns chart_url (backend calls legend-shots)
2) Backend composes data
   - yfinance for prices (with caching via lru_cache in-process)
   - Indicators/Signals computed in-process (indicators/, signals/)
   - Sentiment via NewsAPI if NEWSAPI_KEY; otherwise sample fallback
   - VCP reports via backtest/ module reading artifacts under reports/
3) Screenshot service
   - Stateless GET /screenshot → returns URL to an image for embedding
   - Later: can render TradingView page via Puppeteer and optionally upload to Cloudinary

Environments and URLs
- Local
  - API: http://127.0.0.1:8000
  - Frontend: http://localhost:3000
  - Shots: http://127.0.0.1:3010
- Production
  - API: https://legend-api.onrender.com
  - Frontend: https://legend-ai.vercel.app
  - Shots: https://legend-shots.onrender.com

Key Environment Variables
- Backend (FastAPI)
  - SHOTS_BASE_URL: URL for screenshot service (default https://legend-shots.onrender.com)
  - ALLOWED_ORIGINS, ALLOWED_ORIGIN_REGEX: CORS config
  - LEGEND_MOCK: if true, return sample payloads for resilience
  - NEWSAPI_KEY: optional for live sentiment
  - VCP_*: tuning knobs for VCP detector (see settings.py)
- Frontend (Next.js)
  - NEXT_PUBLIC_VCP_API_BASE: API base URL
  - NEXT_PUBLIC_LEGEND_ROOM_DEMO_PASSWORD: demo gate
- Shots (Node)
  - PORT=3010; DRY_RUN=1 for dummy URL; PUPPETEER_EXECUTABLE_PATH for packaged Chromium (Docker)

Health and Monitoring
- Backend: GET /healthz; GET /metrics (Prometheus)
- Shots: GET /healthz
- Frontend: /demo returns 200 when built

Runbook (Local)
- Start all: make up
  - Shots on 3010, API on 8000, Frontend on 3000
- Stop all: make down
- Test smoke:
  - curl -s http://127.0.0.1:8000/api/v1/chart?symbol=AAPL | jq
  - Open http://localhost:3000/demo

Roadmap Notes (from imports → current)
- Data provider abstraction and alternative feeds (Polygon, Finnhub, etc.): planned; current is yfinance
- n8n ingestion and Sheets/Streamlit flows: not part of this repo; the current system favors in-repo backtest + API + demo
- Production charts: can upgrade legend-shots to real rendered charts and Cloudinary hosting
- Authentication/roles: demo gating only on frontend; no auth enforced at API yet
