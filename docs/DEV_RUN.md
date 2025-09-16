# Local Dev: Legend Room Demo

Terminal A (API)
```
uvicorn service_api:app --host 0.0.0.0 --port 8000
```

Terminal B (Charts)
```
PORT=3010 DRY_RUN=1 node legend-room-screenshot-engine/screenshotEngine.js
```

Terminal C (Frontend)
```
cd legend-ai
NEXT_PUBLIC_VCP_API_BASE=http://127.0.0.1:8000 npm run dev
```

Environment (recommended)
```
NEXT_PUBLIC_VCP_API_BASE=http://127.0.0.1:8000
SHOTS_BASE_URL=http://127.0.0.1:3010
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,https://legend-ai.vercel.app
# Optional for sentiment
# NEWSAPI_KEY=your_newsapi_key
```

Smoke tests
```
curl -s http://127.0.0.1:8000/healthz
curl -s http://127.0.0.1:8000/api/latest_run | jq '.is_sample, .metrics, .analysis[0].signal.label'
curl -s http://127.0.0.1:8000/api/v1/indicators?symbol=NVDA | jq '.symbol, .is_sample'
curl -s http://127.0.0.1:8000/api/v1/signals?symbol=NVDA | jq '.signal.score, .signal.label, .is_sample'
curl -s "http://127.0.0.1:8000/api/v1/sentiment?symbol=NVDA" | jq '.sentiment.label, .is_sample'
curl -s "http://127.0.0.1:8000/api/v1/chart?symbol=NVDA" | jq
```
