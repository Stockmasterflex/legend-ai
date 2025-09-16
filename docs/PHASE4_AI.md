# Phase 4: Optional Sentiment (Headlines + FinBERT)

- If `NEWSAPI_KEY` present, fetch latest 5 headlines via NewsAPI (48h).
- If FinBERT available, classify sentiment; otherwise return neutral.

API:
- GET `/api/v1/sentiment?symbol=TSLA` → `{ sentiment: { label, score, confidence, headlines[] }, is_sample }`

Run:
```
uvicorn service_api:app --host 0.0.0.0 --port 8000
python jobs/run_sentiment.py
curl -s http://127.0.0.1:8000/api/v1/sentiment?symbol=NVDA | jq
```
