# Legend AI – Codebase Overview (Executable Spec)

This document defines the primary modules, their responsibilities, API contracts, and environment variables so new contributors can get productive quickly.

Modules and Responsibilities
- service_api.py (FastAPI app)
  - CORS, logging, metrics, and all HTTP endpoints
  - Endpoints
    - GET /healthz → { ok, version }
    - GET /metrics → Prometheus metrics
    - GET /api/v1/indicators?symbol=NVDA&period=6mo → { symbol, indicators, is_sample }
    - GET /api/v1/signals?symbol=NVDA → { symbol, signal, is_sample }
    - GET /api/v1/sentiment?symbol=NVDA → { symbol, sentiment, is_sample }
    - GET /api/v1/chart?symbol=AAPL → { chart_url }
    - GET /scan/{symbol} → VCP detector output
    - GET /api/v1/vcp/today → candidates rows
    - GET /api/v1/vcp/metrics?start=YYYY-MM-DD&end=YYYY-MM-DD → summary KPIs
    - GET /api/v1/runs → recent runs
    - POST /api/v1/runs → submit background run (mock fallback)
    - GET /api/v1/runs/{run_id} → run detail, artifacts index
    - GET /api/v1/vcp/candidates?day=YYYY-MM-DD → rows for a day
    - GET /api/v1/analytics/overview?run_id=1 → dashboard aggregates
- backtest/
  - run_backtest.py: scan_once(day), typical backtest runs
  - ingestion.py, simulate.py: produce reports under reports/
- indicators/
  - ta.py: compute_all_indicators(df)
- signals/
  - core.py: score_from_indicators(indicators, df)
- sentiment/
  - core.py: fetch_headlines_and_sentiment(symbol) (uses NEWSAPI_KEY if set)
- service_db.py
  - SQLAlchemy models and session for BacktestRun metadata (SQLite default)
- settings.py
  - VCPSettings dataclass and LEGEND_MOCK flag
- legend-room-screenshot-engine/
  - server.js: GET /screenshot → { chart_url }
  - chromium.js: launchBrowser using @sparticuz/chromium + puppeteer-core

Environment Variables
- Backend
  - SHOTS_BASE_URL: URL for screenshot service (default https://legend-shots.onrender.com)
  - ALLOWED_ORIGINS, ALLOWED_ORIGIN_REGEX: CORS
  - LEGEND_MOCK: 1 to enable resilient sample payloads
  - NEWSAPI_KEY: optional for live sentiment
  - VCP_* tuning: VCP_MIN_DRYUP, VCP_MAX_BASE_DEPTH, VCP_MIN_TIGHTEN_STEPS, VCP_MAX_FINAL_RANGE, VCP_PIVOT_WINDOW, VCP_BREAKOUT_VOLX
- Frontend
  - NEXT_PUBLIC_VCP_API_BASE, NEXT_PUBLIC_LEGEND_ROOM_DEMO_PASSWORD
- Shots
  - PORT, DRY_RUN, PUPPETEER_EXECUTABLE_PATH

Contracts (selected)
- /api/v1/chart
  - Request: GET with query symbol=string, optional pivot
  - Response: 200 { chart_url: string }
  - Behavior: Attempts SHOTS_BASE_URL/screenshot; fallback to deterministic dummy image URL
- /api/v1/vcp/today
  - Request: GET day label optional (defaults to today)
  - Response: 200 { day, rows: [{ symbol, confidence, pivot?, price?, notes? }], is_sample? }
  - Behavior: If LEGEND_MOCK=1 or failure, returns sample rows; otherwise reads generated CSV from scan_once

Local Dev
- make up → starts shots (3010), API (8000), frontend (3000)
- make down → stops processes and kills ports

Testing and Health
- curl -s http://127.0.0.1:8000/healthz | jq
- curl -s "http://127.0.0.1:8000/api/v1/chart?symbol=AAPL" | jq
- Open http://localhost:3000/demo

Roadmap Fit vs Imported Docs
- Data provider abstraction: Can be layered atop existing yfinance-based endpoints later
- n8n/Google Sheets flows: currently out-of-scope of this repo; consider separate repo or integrations
- Charts: upgrade legend-shots to render TradingView template and optionally upload to Cloudinary for persistent URLs
