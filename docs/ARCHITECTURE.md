# Legend AI System Architecture

## Overview

Legend AI is a pattern detection and decision-support system for traders, identifying high-probability Volatility Contraction Patterns (VCP) in stock data. The system follows the methodologies of Mark Minervini and William O'Neil.

## System Components

### 1. Backend API (FastAPI)

**Location**: `/app/legend_ai_backend.py`

The API serves as the central hub for all data operations and pattern detection.

#### Key Endpoints

- **Health & Status**
  - `GET /healthz` - Simple health check
  - `GET /readyz` - Database connectivity check
  - `GET /v1/meta/status` - Scan statistics and freshness

- **Pattern Data (v1)**
  - `GET /v1/patterns/all` - Paginated patterns with cursor
  - Query params: `limit` (1-500), `cursor` (base64 encoded)
  - Returns: `{items: [...], next: cursor|null}`

- **Legacy Endpoints**
  - `GET /api/patterns/all` - Backward-compatible endpoint
  - `GET /api/patterns/vcp` - VCP-specific patterns
  - `GET /api/market/environment` - Market status
  - `GET /api/market/indices` - Market overview (SPY, QQQ, etc.)
  - `GET /api/portfolio/positions` - Portfolio tracking

- **Admin/Debug**
  - `POST /admin/init-db` - Initialize database schema
  - `POST /admin/seed-demo` - Seed sample patterns
  - `POST /admin/run-scan` - Trigger manual scan
  - `GET /admin/test-data` - Test yfinance connection
  - `GET /admin/list-routes` - List all API routes

#### Architecture Decisions

1. **Dual Import Pattern**: The app wraps the root-level FastAPI app for backward compatibility while adding observability
2. **Caching Strategy**: Three-tier cache (in-memory → pattern cache → database)
3. **Enrichment Pattern**: Patterns enriched on-demand with yfinance data

### 2. Pattern Detector

**Location**: `/vcp_ultimate_algorithm.py`

Core VCP detection algorithm implementing Minervini's 8-point trend template.

#### Detection Parameters (Production Defaults)

```python
VCPDetector(
    min_price=30.0,              # Filter penny stocks
    min_volume=1_000_000,        # Ensure liquidity
    min_contractions=2,          # Minimum contractions
    max_contractions=6,          # Maximum contractions
    max_base_depth=0.35,         # 35% maximum base depth
    final_contraction_max=0.10,  # 10% final contraction
    check_trend_template=True    # Apply Minervini filter
)
```

#### Detection Flow

1. **Data Validation** - Check OHLCV data quality
2. **Trend Template** (optional) - 8-point Minervini filter
3. **Swing Point Detection** - Find local highs/lows
4. **Contraction Identification** - Match swing points to contractions
5. **Pattern Validation** - Verify VCP criteria
6. **Confidence Scoring** - Calculate 0-100 confidence score

#### Confidence Score Components

- Trend strength (0-30 points)
- Number of contractions (0-20 points)
- Volume dry-up (0-20 points)
- Volatility compression (0-15 points)
- Final contraction tightness (0-15 points)

### 3. Data Fetcher

**Location**: `/app/data_fetcher.py`

Multi-source price data fetcher with fallback chain.

#### Fallback Chain

1. **Finnhub** (primary, if API key present)
   - Requires `FINNHUB_API_KEY` environment variable
   - Daily candles via REST API

2. **yfinance** (fallback)
   - Free, no API key required
   - Uses `Ticker.history()` for reliable results

3. **Mock Data** (dev/testing)
   - Deterministic random walk based on symbol hash
   - Used when all other sources fail

### 4. Database Layer

**Location**: `/app/db.py`, `/app/db_queries.py`

#### Schema (Normalized)

**Table: `patterns`**
```sql
CREATE TABLE patterns (
    ticker TEXT NOT NULL,
    pattern TEXT NOT NULL,
    as_of TIMESTAMPTZ NOT NULL,
    confidence FLOAT,
    rs FLOAT,
    price NUMERIC,
    meta JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (ticker, pattern, as_of)
);
```

**Table: `stocks`** (legacy, from root app)
- Stores stock metadata (sector, industry, market cap)
- Updated during scans

**Table: `portfolio`** (future use)
- Track paper/real positions

**Table: `scan_runs`** (future use)
- Track scan history and performance

#### Database Compatibility

- **Development**: SQLite (`sqlite:///./legendai.db`)
  - Meta stored as TEXT (JSON string)
  - Timestamps as TIMESTAMP

- **Production**: PostgreSQL/TimescaleDB
  - Meta stored as JSONB (native)
  - Timestamps as TIMESTAMPTZ

The `db_queries.py` module handles both formats transparently.

### 5. Daily Scanner

**Location**: `/daily_market_scanner.py`

Scheduled job that runs daily to scan the market for VCP patterns.

#### Scan Flow

1. **Fetch Universe** - S&P 500 + Nasdaq-100 from Wikipedia
2. **Rate Limiting** - Max 58 requests/minute
3. **Fetch Candles** - 180 days of history per symbol
4. **Cache Data** - Store in `/data/price_history/`
5. **Run Detection** - Scan all symbols for VCPs
6. **Upsert Patterns** - Save to database

#### Configuration

- **Schedule**: 6:00 AM ET (10:00 UTC)
- **Retry Logic**: Individual symbol failures logged to `scan_failures` table
- **Data Provider**: Configurable via `VCP_PROVIDER` env var

### 6. Frontend Dashboard

**Location**: `/index.html`, `/app.js`, `/style.css`

React-free vanilla JavaScript dashboard with modern UI.

#### Key Features

- **Pattern Table** - Sortable, filterable results
- **Advanced Filters** - RS rating, confidence, sector, market cap, price, volume
- **Market Overview** - Indices with sparklines (SPY, QQQ, IWM, DIA, VIX)
- **Sector Performance** - Aggregate metrics by sector
- **Data Freshness** - Real-time indicator (green <6h, yellow <24h, red >24h)
- **Load More** - Cursor-based pagination

#### Data Flow

1. **Initial Load**: Fetch first 100 patterns from `/v1/patterns/all`
2. **Enrichment**: API enriches with yfinance data (sector, RS rating, etc.)
3. **Filtering**: Client-side filtering for instant feedback
4. **Pagination**: Load more via cursor when scrolling

## Deployment Architecture

### Production Stack

```
┌─────────────────┐
│  Vercel (CDN)   │  - Static dashboard hosting
│  legend-ai.     │  - Edge-optimized delivery
│  vercel.app     │  - HTTPS automatic
└────────┬────────┘
         │ CORS
         ▼
┌─────────────────┐
│  Render         │  - FastAPI backend
│  legend-api.    │  - Docker container
│  onrender.com   │  - Health checks
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Database       │  - SQLite (embedded)
│  legendai.db    │  - OR PostgreSQL (cloud)
└─────────────────┘
```

### Environment Variables

**Required**:
- `DATABASE_URL` - Database connection string

**Optional**:
- `FINNHUB_API_KEY` - Finnhub API key for data
- `REDIS_URL` - Redis for caching (falls back to in-memory)
- `SENTRY_DSN` - Error tracking
- `ALLOWED_ORIGINS` - CORS allowlist (comma-separated)
- `ALLOWED_ORIGIN_REGEX` - CORS regex pattern

### Cron Job

Configured in `render.yaml`:
```yaml
cronJobs:
  - name: daily-market-scanner
    schedule: "0 10 * * *"  # 6 AM ET
    command: "python daily_market_scanner.py"
```

## Data Flow

### Scan → Display Pipeline

```
1. Cron Trigger (6 AM ET)
   ↓
2. Fetch S&P 500 + NDX tickers
   ↓
3. For each ticker:
   - Fetch 180d candles (Finnhub/yfinance)
   - Cache to /data/price_history/{TICKER}.json
   - Run VCP detector
   ↓
4. Save detected patterns to database
   ↓
5. Dashboard polls /v1/patterns/all
   ↓
6. API enriches with live data (yfinance)
   ↓
7. Dashboard displays results
```

## Testing Strategy

### Test Coverage

Current: 5 tests
- API status endpoint test
- VCP detector true positive test
- VCP detector false positive test
- Health check test
- Readyz smoke test

### Test Structure

```
tests/
├── api/               # API endpoint tests
├── detectors/         # Pattern detector tests
├── fixtures/          # Test data
│   ├── true_vcp.json  # Known VCPs for validation
│   └── false_vcp.json # Known non-VCPs
└── test_*.py          # Individual test modules
```

### Running Tests

```bash
pytest tests/ -v                    # All tests
pytest tests/detectors/ -v          # Detector tests only
pytest -m slow                      # Integration tests
```

## Configuration

### Scanner Parameters

Adjust in:
- `/vcp_ultimate_algorithm.py` - Detector defaults
- `/app/legend_ai_backend.py` - API detector instance
- `/daily_market_scanner.py` - Scanner detector instance

### Dashboard Filters

Adjust in:
- `/app.js` - JavaScript defaults (setDefaultFilters)
- `/index.html` - HTML default values

## Performance Considerations

### Bottlenecks

1. **Pattern Enrichment** - yfinance calls per pattern (cached)
2. **Volume Dry-up Check** - Volume calculation across contractions
3. **RS Rating Calculation** - SPY benchmark fetch + comparison

### Optimization Strategies

- **Caching**: Three-tier (in-memory → pattern → database)
- **Lazy Enrichment**: Enrich only displayed patterns
- **Batch Fetching**: Group yfinance calls when possible
- **Index Strategy**: Database indexes on `as_of DESC`, `ticker`

## Security

### Current State

- No authentication required
- CORS restricted to Vercel domains
- Read-only API (except admin endpoints)
- Admin endpoints unprotected (should add auth)

### Recommended Improvements

1. Add API key authentication for admin endpoints
2. Implement rate limiting (e.g., slowapi)
3. Add request signing for sensitive operations
4. Enable database backups for PostgreSQL

## Monitoring & Observability

### Current

- JSON logging to stdout
- Sentry integration (if DSN provided)
- Health/readiness probes

### Metrics to Track

- Scan success/failure rates
- Pattern detection count per scan
- API response times (p50, p95, p99)
- Data freshness (hours since last scan)
- False positive rate (manual review)

## Future Enhancements

### Near-term

1. Pattern lifecycle tracking (breakout/failure)
2. Portfolio management with P&L
3. Additional patterns (Cup & Handle, Flat Base)
4. Mobile-responsive design

### Long-term

1. User authentication & saved watchlists
2. Real-time alerting (email/SMS)
3. Backtesting framework
4. ML-based confidence scoring
5. TradingView integration

## Troubleshooting

### Common Issues

**Problem**: Patterns not updating
- Check: Render cron job logs
- Verify: `DATABASE_URL` correct
- Test: `POST /admin/run-scan` manually

**Problem**: Empty patterns table
- Check: `GET /v1/meta/status` shows `rows_total: 0`
- Fix: Run `POST /admin/seed-demo` or wait for cron

**Problem**: Slow API responses
- Check: Pattern count (>1000 may need pagination)
- Verify: Redis connected (check logs for "fallback to in-memory")
- Profile: `/admin/test-legacy-transform` endpoint

**Problem**: Dashboard shows stale data
- Check: Data freshness indicator in header
- Verify: Cron job last run time
- Fix: Manual trigger via dashboard "Run Scan" button

## References

- [VCP Pattern Specification](specs/patterns/vcp.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Testing Guide](TESTING.md)

