# Deploy Checks

Assume $API points to your deployed service_api base.

Health
```
curl -s $API/healthz
```

Sample fallback
```
curl -s $API/api/latest_run | jq '.is_sample, .metrics'
```

Indicators/Signals/Sentiment
```
curl -s "$API/api/v1/indicators?symbol=NVDA" | jq '.symbol, .is_sample'
curl -s "$API/api/v1/signals?symbol=NVDA" | jq '.signal.score, .signal.label, .is_sample'
curl -s "$API/api/v1/sentiment?symbol=NVDA" | jq '.sentiment.label, .is_sample'
```

Charts
```
curl -s "$API/api/v1/chart?symbol=NVDA" | jq
```

Env vars
- NEXT_PUBLIC_VCP_API_BASE: frontend → backend base URL
- SHOTS_BASE_URL: backend → screenshot engine base URL
- ALLOWED_ORIGINS / ALLOWED_ORIGIN_REGEX: CORS
- Optional: NEWSAPI_KEY for sentiment
