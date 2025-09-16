# Phase 3: Technical Indicators & Signals

Indicators (computed in `indicators/ta.py`):
- EMA(21/50/200), RSI(14), MACD(12,26,9), Bollinger(20,2), ATR(14), Stochastic(14,3), VolSMA(50), BB width, simple swing support/resistance.

Signals (in `signals/core.py`):
- Multi-indicator score (0–100) with tunables via env:
  - SIGNAL_VOLX (default 1.5), SIGNAL_MIN_RSI (45), SIGNAL_MAX_BBWIDTH (0.25)
- Reasons and badges (e.g., “volume-confirmed MACD”).

API (read-only, cached fetch):
- GET `/api/v1/indicators?symbol=TSLA`
- GET `/api/v1/signals?symbol=TSLA`

Validation:
```
uvicorn service_api:app --host 0.0.0.0 --port 8000
python jobs/run_analysis.py
curl -s http://127.0.0.1:8000/api/v1/signals?symbol=NVDA | jq
```
