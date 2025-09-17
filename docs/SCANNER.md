# LegendAI Scanner & Charts

The scanner surfaces high-probability technical patterns across curated universes and renders annotated charts via the screenshot service. This note covers the universe lists, pattern detectors, backend API, and overlay-aware chart generation so you can extend or debug the workflow quickly.

## Universes

Universe constituents live in `data/universe/`:

- `sp500.txt` – Official S&P 500 membership (one ticker per line, upper-case, `.` normalised to `-`).
- `nasdaq100.txt` – NASDAQ-100 membership with the same formatting rules.

`service_universe.get_universe(name)` loads and normalises these files. Set `EXPAND_NASDAQ=1` to opt into a larger list in the future (if `nasdaq100_full.txt` is added). Results are cached in-process, so repeated scans are cheap.

## Pattern detectors

Detectors live in `signals/patterns.py` and expose a consistent signature:

```python
patterns.detect(
    pattern: Literal["vcp","cup_handle","hns","flag","wedge","double"],
    df,
    symbol,
    timeframe="1d",
)
```

Each detector returns a dictionary:

```python
{
  "pattern": "cup_handle",
  "score": 88.5,
  "entry": 101.25,
  "stop": 96.8,
  "targets": [112.5, 118.0],
  "key_levels": {"entry": 101.25, "stop": 96.8, "targets": [112.5, 118.0]},
  "overlays": {
    "priceLevels": {"entry": 101.25, "stop": 96.8, "targets": [...]},
    "lines": [...],
    "boxes": [...],
    "labels": [...],
    "arrows": [...],
    "zones": [...]
  },
  "meta": {
    "evidence": ["depth 0.16", "handle depth 0.03"],
    "atr14": 2.1
  }
}
```

Scores are heuristic but scaled to 0–100 so downstream ranking is straightforward. Overlays describe the pattern geometry and get passed straight to the chart renderer.

A few implementation notes:

- **VCP** reuses the existing `VCPDetector`, adds risk-based targets, and serialises contraction legs into overlays.
- **Cup & Handle / Flag / Wedge / Double** use price window heuristics that tolerate noisy data while still highlighting the breakout levels you care about.
- **Head & Shoulders / Double Tops & Bottoms** annotate neckline measurements and symmetry so the frontend can surface evidence.
- Every detector returns an `evidence` list and `atr14` so the scanner can filter on liquidity/risk, and guards against missing columns/NaNs so bad symbols are skipped instead of aborting the run.

## Scan API

The FastAPI endpoint `/api/v1/scan` powers the UI and any automation. Parameters:

- `pattern`: `vcp | cup_handle | hns | flag | wedge | double`
- `universe`: `sp500 | nasdaq100`
- `timeframe`: `1d | 1wk | 60m` (defaults to `1d`)
- `min_price`: optional 30-day average close filter
- `min_volume`: optional 30-day average volume filter
- `max_atr_ratio`: optional ATR/entry ratio ceiling (e.g., `0.08`)
- `limit`: optional, defaults to 100 returned rows

Example:

```bash
curl "http://localhost:8000/api/v1/scan?pattern=vcp&universe=sp500&limit=50"
```

Response shape:

```json
{
  "pattern": "vcp",
  "universe": "sp500",
  "count": 8,
  "results": [
    {
      "symbol": "AAPL",
      "score": 91.2,
      "entry": 197.5,
      "stop": 189.2,
      "targets": [214.1, 231.0],
      "key_levels": {"entry": 197.5, "stop": 189.2, "targets": [214.1, 231.0]},
      "avg_price": 198.3,
      "avg_volume": 42100000,
      "atr14": 4.2,
      "overlays": {"priceLevels": {...}, "lines": [...], ...},
      "meta": {"evidence": ["3 tightening contractions", "volume dry-up confirmed"]},
      "chart_url": "https://legend-shots.../reports/AAPL-...png",
      "chart_meta": {
        "source": "https://legend-shots.onrender.com",
        "overlay_applied": true,
        "duration_ms": 1480,
        "overlay_counts": {"lines": 4, "labels": 2}
      }
    }
  ]
}
```

Internally the scanner:

1. Loads the requested universe via `service_universe`.
2. Fetches prices through the cached `backtest.ingestion.load_prices` pipeline (yfinance under the hood).
3. Runs the chosen detector on the requested timeframe (daily/weekly/60m) and filters out symbols that fail the price/volume/ATR checks.
4. Calls the chart proxy so the payload already contains a `chart_url` plus render metadata.
5. Stores each symbol+timeframe in Redis (if configured) or an in-process LRU cache for a few minutes to keep repeated scans responsive.

`/api/v1/scan/pattern` remains for backwards compatibility; it now delegates to the same logic.

## Chart overlays

`/api/v1/chart` accepts GET or POST. When overlays are provided they are forwarded to `legend-room-screenshot-engine` using a POST body:

```json
{
"overlays": {
  "priceLevels": {"entry": 101.2, "stop": 96.5, "targets": [112.0]},
  "lines": [
    {"x1": "2024-01-10", "y1": 110.5, "x2": "2024-02-08", "y2": 102.3, "dash": true}
  ],
  "boxes": [...],
  "labels": [...],
  "arrows": [...],
  "zones": [...]
}
}
```

The screenshot service injects these overlays into the TradingView template before capturing the image. If Chromium or Puppeteer fail the API falls back to `https://dummyimage.com/1200x628/...` so the UI never blocks on chart generation, and the response includes `meta.fallback=true` so callers can surface the degraded state.

Example call returning chart metadata:

```bash
curl -sX POST "${LEGEND_API}/api/v1/chart?symbol=NVDA" \
  -H 'content-type: application/json' \
  -d '{"overlays":{"priceLevels":{"entry":120,"stop":114,"targets":[132]},"lines":[{"x1":"2024-04-01","y1":118,"x2":"2024-05-01","y2":115,"dash":true}],"zones":[{"x1":"2024-05-10","x2":"2024-05-25","y1":118,"y2":122,"color":"#1e88e5","opacity":0.18}]}}' | jq
```

To experiment locally:

```bash
# Generate test data
python -m pytest tests/test_patterns.py -q

# Hit the scan API
uvicorn service_api:app --reload
curl "http://127.0.0.1:8000/api/v1/scan?pattern=flag&universe=nasdaq100&limit=20"

# Render a chart with overlays
curl -X POST "http://127.0.0.1:8000/api/v1/chart?symbol=AAPL" \
  -H "Content-Type: application/json" \
  -d '{"overlays": {"priceLevels": {"entry": 197, "stop": 190, "targets": [210]}, "lines": []}}'
```

## Frontend quickstart

The demo page (`kyle-portfolio/app/demo/page.tsx`) now includes Universe, Pattern, Timeframe, and liquidity filter inputs with an inline results table. Clicking a row fetches (or reuses) the generated chart and expands it in place. Remote sparklines stay behind `NEXT_PUBLIC_USE_REMOTE_SPARKLINE=1` to avoid unnecessary Yahoo Finance calls by default.

## Performance tips

- Enable Redis caching (`REDIS_URL`) for the fastest repeated scans; otherwise the in-process LRU keeps symbols warm for ~4 minutes.
- Tune `SCAN_WORKERS`, `SCAN_CHART_CONCURRENCY`, `SCAN_MIN_PRICE`, `SCAN_MIN_VOLUME`, and `SCAN_MAX_ATR_RATIO` to match your hardware.
- Weekly (`timeframe=1wk`) sweeps are useful for quick breadth checks; `timeframe=60m` provides intraday structure if your provider supports it.
- The shots service logs render duration and overlay counts—keep overlays succinct for quicker renders and fewer fallbacks.

That’s everything you need to wire new patterns, universes, or presentation tweaks end-to-end.
