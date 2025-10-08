"""
FastAPI app wrapper for Legend AI API.

This module imports the existing root-level FastAPI app from
`legend_ai_backend.py`, applies standardized observability (JSON logging,
optional Sentry), config-driven CORS, and exposes `/healthz` and `/readyz`.

Keeping this wrapper allows Render to run `uvicorn app.legend_ai_backend:app`
without duplicating business logic.
"""

import os
import uuid
import math
from datetime import datetime
from typing import List, Dict, Any, Tuple

import logging

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, APIRouter, Query, Response, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
import yfinance as yf
import pandas as pd

from .config import allowed_origins, mock_enabled
from .flags import get_flags
from .cache import cache_get, cache_set
from .db_queries import fetch_patterns, get_status
from .data_fetcher import fetch_stock_data

from .observability import setup_json_logging, setup_sentry
from pathlib import Path
from vcp_ultimate_algorithm import VCPDetector


# Import the existing FastAPI application defined at repository root
try:
    from legend_ai_backend import app as base_app  # type: ignore
except Exception as import_exc:  # pragma: no cover - defensive import guard
    # Fallback: create a minimal app if import fails so /healthz still works
    base_app = FastAPI(title="Legend AI API (fallback)")


# Observability
setup_json_logging()
app = setup_sentry(base_app)


# CORS middleware with env-driven allowlist
ALLOWED_ORIGINS = allowed_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz():
    return {"ok": True, "version": "0.1.0"}


# Readiness endpoint using a minimal SQLAlchemy engine if available
try:
    from .db import engine  # type: ignore
    from sqlalchemy import text

    @app.get("/readyz")
    def readyz():
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"ok": True}
except Exception:  # pragma: no cover - readiness degrades gracefully
    @app.get("/readyz")
    def readyz():
        return {"ok": False, "reason": "db engine unavailable"}


# ---------------------------
# API v1 router and middleware
# ---------------------------

class Error(BaseModel):
    code: str
    message: str


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        response = await call_next(request)
        response.headers["x-request-id"] = rid
        return response


try:
    app.add_middleware(RequestIdMiddleware)
except Exception:
    pass


v1 = APIRouter(prefix="/v1", tags=["v1"])

_DETECTOR = VCPDetector(
    min_price=5.0,
    min_volume=200_000,
    min_contractions=2,
    max_contractions=6,
    check_trend_template=False,
)

_PRICE_CACHE: Dict[str, pd.DataFrame] = {}
_SIGNAL_CACHE: Dict[str, Any] = {}
_PROFILE_CACHE: Dict[str, Dict[str, Any]] = {}
_BENCHMARK_CACHE: Dict[str, Tuple[float, datetime]] = {}


def _fetch_price_history(ticker: str, days: int = 365) -> pd.DataFrame | None:
    if ticker in _PRICE_CACHE:
        return _PRICE_CACHE[ticker]

    try:
        df = fetch_stock_data(ticker, days=days)
        if df is not None and not df.empty:
            if "Date" in df.columns:
                df = df.sort_values("Date").reset_index(drop=True)
            _PRICE_CACHE[ticker] = df
            return df
    except Exception as exc:  # pragma: no cover - defensive guard
        logging.warning("price history fetch failed for %s: %s", ticker, exc)
    return None


def _compute_vcp_signal(ticker: str) -> Any:
    if ticker in _SIGNAL_CACHE:
        return _SIGNAL_CACHE[ticker]

    df = _fetch_price_history(ticker, days=365)
    if df is None or len(df) < 80:
        _SIGNAL_CACHE[ticker] = None
        return None

    try:
        detector_df = df.set_index("Date")[['Open', 'High', 'Low', 'Close', 'Volume']]
        signal = _DETECTOR.detect_vcp(detector_df, symbol=ticker)
        _SIGNAL_CACHE[ticker] = signal
        return signal
    except Exception as exc:
        logging.warning("VCP detector failed for %s: %s", ticker, exc)
        _SIGNAL_CACHE[ticker] = None
        return None


def _get_benchmark_return(symbol: str = "SPY", days: int = 180) -> float | None:
    cache_key = f"{symbol}:{days}"
    cached = _BENCHMARK_CACHE.get(cache_key)
    if cached and (datetime.utcnow() - cached[1]).total_seconds() < 3600:
        return cached[0]

    df = _fetch_price_history(symbol, days=days + 5)
    if df is None or df.empty:
        return None
    df_tail = df.tail(days)
    if len(df_tail) < 2:
        return None
    start = float(df_tail['Close'].iloc[0])
    end = float(df_tail['Close'].iloc[-1])
    if start <= 0:
        return None
    ret = (end - start) / start
    _BENCHMARK_CACHE[cache_key] = (ret, datetime.utcnow())
    return ret


def _calculate_rs_rating(stock_return: float | None, benchmark_return: float | None) -> int | None:
    if stock_return is None:
        return None
    if benchmark_return is None:
        score = 50 + stock_return * 120
    else:
        score = 50 + (stock_return - benchmark_return) * 120
    score = max(0, min(100, int(round(score))))
    return score


def _format_market_cap(value: float | None) -> str | None:
    if not value:
        return None
    units = [(1_000_000_000_000, "T"), (1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")]
    for threshold, suffix in units:
        if value >= threshold:
            return f"{value / threshold:.2f}{suffix}"
    return f"{value:.0f}"


def _get_stock_profile(ticker: str) -> Dict[str, Any]:
    if ticker in _PROFILE_CACHE:
        return _PROFILE_CACHE[ticker]

    profile: Dict[str, Any] = {
        "ticker": ticker,
        "name": ticker,
        "sector": None,
        "industry": None,
        "market_cap": None,
        "average_volume": None,
        "market_cap_human": None,
        "rs_rating": None,
        "return_6m": None,
        "volume_multiple": None,
    }

    try:
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.get_info()
        profile["name"] = info.get("shortName") or info.get("longName") or ticker
        profile["sector"] = info.get("sector")
        profile["industry"] = info.get("industry")
        profile["market_cap"] = info.get("marketCap")
        profile["average_volume"] = info.get("averageVolume") or info.get("averageDailyVolume10Day")
        if profile["market_cap"]:
            profile["market_cap_human"] = _format_market_cap(profile["market_cap"])
    except Exception as exc:  # pragma: no cover - yfinance sometimes fails
        logging.debug("yfinance profile lookup failed for %s: %s", ticker, exc)

    df = _fetch_price_history(ticker, days=240)
    if df is not None and not df.empty:
        try:
            profile["current_price"] = float(df['Close'].iloc[-1])
        except Exception:
            profile["current_price"] = None
        window = df.tail(180)
        if len(window) >= 2:
            start = float(window['Close'].iloc[0])
            end = float(window['Close'].iloc[-1])
            if start > 0:
                stock_return = (end - start) / start
                profile["return_6m"] = stock_return
                benchmark_return = _get_benchmark_return("SPY", days=min(180, len(window)))
                profile["rs_rating"] = _calculate_rs_rating(stock_return, benchmark_return)
        if 'Volume' in df.columns and len(df['Volume']) >= 30:
            avg_vol = float(df['Volume'].tail(30).mean())
            profile["average_volume"] = avg_vol
            latest_vol = float(df['Volume'].iloc[-1])
            if avg_vol > 0:
                profile["volume_multiple"] = latest_vol / avg_vol

    _PROFILE_CACHE[ticker] = profile
    return profile


def _normalize_confidence(raw: float | None, signal: Any, meta: Dict[str, Any]) -> float | None:
    if raw is not None:
        value = float(raw)
        if value > 1:
            return value / 100.0
        return value
    if signal and getattr(signal, "confidence_score", None) is not None:
        return float(signal.confidence_score) / 100.0
    score = meta.get("confidence_score")
    if score is not None:
        score = float(score)
        return score / 100.0 if score > 1 else score
    return None


def _enrich_pattern_row(row: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(row)
    ticker = data.get("ticker")
    meta = data.get("meta") or {}

    if not ticker:
        return data

    signal = _compute_vcp_signal(ticker)
    profile = _get_stock_profile(ticker)

    confidence = _normalize_confidence(data.get("confidence"), signal, meta)
    price = float(data.get("price") or profile.get("current_price") or meta.get("current_price") or 0)

    pivot = meta.get("pivot_price") or (signal.pivot_price if signal and signal.pivot_price else None)
    if pivot is None and price:
        pivot = price

    stop_loss = meta.get("stop_loss")
    if stop_loss is None and signal and getattr(signal, "contractions", None):
        last_c = signal.contractions[-1]
        stop_loss = float(getattr(last_c, "low_price", 0) or 0)
    if not stop_loss and pivot:
        stop_loss = float(pivot) * 0.92

    days_in_pattern = meta.get("days_in_pattern")
    if days_in_pattern is None and signal and getattr(signal, "contractions", None):
        first = signal.contractions[0].start_date if signal.contractions else None
        last = signal.contractions[-1].end_date if signal.contractions else None
        if first and last:
            days_in_pattern = max(0, (last - first).days)
    if days_in_pattern is None:
        days_in_pattern = 0

    rs_rating = meta.get("rs_rating") or profile.get("rs_rating")
    trend_strength = meta.get("trend_strength")
    if trend_strength is None and signal and getattr(signal, "trend_strength", None) is not None:
        trend_strength = float(signal.trend_strength)

    volume_multiple = meta.get("volume_multiple") or profile.get("volume_multiple")
    average_volume = meta.get("average_volume") or profile.get("average_volume")

    meta.update({
        "sector": meta.get("sector") or profile.get("sector"),
        "industry": meta.get("industry") or profile.get("industry"),
        "pivot_price": pivot,
        "stop_loss": stop_loss,
        "rs_rating": rs_rating,
        "days_in_pattern": days_in_pattern,
        "market_cap": meta.get("market_cap") or profile.get("market_cap"),
        "market_cap_human": meta.get("market_cap_human") or profile.get("market_cap_human"),
        "volume_multiple": volume_multiple,
        "average_volume": average_volume,
        "trend_strength": trend_strength,
    })

    data.update(
        {
            "confidence": confidence,
            "meta": meta,
            "name": meta.get("name") or profile.get("name") or ticker,
            "sector": meta.get("sector") or profile.get("sector"),
            "industry": meta.get("industry") or profile.get("industry"),
            "pivot_price": pivot,
            "stop_loss": stop_loss,
            "rs_rating": rs_rating,
            "days_in_pattern": days_in_pattern,
            "market_cap": meta.get("market_cap") or profile.get("market_cap"),
            "market_cap_human": meta.get("market_cap_human") or profile.get("market_cap_human"),
            "volume_multiple": volume_multiple,
            "average_volume": average_volume,
            "trend_strength": trend_strength,
        }
    )

    if rs_rating is not None:
        data["rs"] = rs_rating

    if price and meta.get("current_price") is None:
        meta["current_price"] = price

    return data


class PatternItem(BaseModel):
    ticker: str
    pattern: str
    as_of: str
    confidence: float | None = Field(default=None)
    rs: float | None = Field(default=None)
    price: float | None = Field(default=None)
    meta: dict | None = Field(default=None)
    name: str | None = Field(default=None)
    sector: str | None = Field(default=None)
    industry: str | None = Field(default=None)
    pivot_price: float | None = Field(default=None)
    stop_loss: float | None = Field(default=None)
    rs_rating: int | None = Field(default=None)
    days_in_pattern: int | None = Field(default=None)
    market_cap: float | None = Field(default=None)
    market_cap_human: str | None = Field(default=None)
    volume_multiple: float | None = Field(default=None)
    average_volume: float | None = Field(default=None)
    trend_strength: float | None = Field(default=None)


class PaginatedPatterns(BaseModel):
    items: list[PatternItem]
    next: str | None


@v1.get("/patterns/all", response_model=PaginatedPatterns)
def patterns_all_v1(
    response: Response,
    limit: int = Query(100, ge=1, le=500),
    cursor: str | None = None,
):
    """Return latest patterns with cursor pagination.

    Ordered by (as_of DESC, ticker ASC). Cursor encodes last (as_of, ticker).
    """
    response.headers["Cache-Control"] = "public, max-age=30"

    flags = get_flags()
    cache_key = f"v1:patterns:all:{limit}:{cursor or ''}"
    if "cache" in flags:
        cached = cache_get(cache_key)
        if cached:
            return cached

    try:
        from .db import engine  # type: ignore
        items, next_cursor = fetch_patterns(engine, limit=limit, cursor=cursor)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail={"code": "db_error", "message": str(exc)})

    enriched_items = [_enrich_pattern_row(row) for row in items]
    payload = {"items": enriched_items, "next": next_cursor}
    if "cache" in flags:
        cache_set(cache_key, payload, ttl=60)
    return payload


class StatusModel(BaseModel):
    last_scan_time: str | None
    rows_total: int
    patterns_daily_span_days: int | None
    version: str


class MarketSparkPoint(BaseModel):
    time: str
    close: float


class MarketIndexModel(BaseModel):
    symbol: str
    name: str
    last_price: float | None
    change_percent: float | None
    previous_close: float | None
    sparkline: List[MarketSparkPoint]


class MarketOverviewModel(BaseModel):
    indices: List[MarketIndexModel]
    updated_at: str


@v1.get("/meta/status", response_model=StatusModel)
def meta_status_v1() -> StatusModel:
    try:
        from .db import engine  # type: ignore
        status = get_status(engine)
    except Exception:
        # graceful when DB unavailable
        status = {"last_scan_time": None, "rows_total": 0, "patterns_daily_span_days": None, "version": "0.1.0"}
    return StatusModel(**status)


@app.get("/api/market/indices", response_model=MarketOverviewModel)
def market_indices_overview():
    indices_catalog = [
        ("SPY", "S&P 500"),
        ("QQQ", "Nasdaq 100"),
        ("IWM", "Russell 2000"),
        ("DIA", "Dow Jones Industrial"),
        ("VIX", "CBOE Volatility"),
    ]

    indices: List[Dict[str, Any]] = []
    for symbol, display_name in indices_catalog:
        df = _fetch_price_history(symbol, days=120)
        if df is None or df.empty:
            continue

        recent = df.tail(60)
        if recent.empty:
            continue

        try:
            if not pd.api.types.is_datetime64_any_dtype(recent['Date']):
                recent['Date'] = pd.to_datetime(recent['Date'])
            last_close = float(recent['Close'].iloc[-1])
            previous_close = float(recent['Close'].iloc[-2]) if len(recent) > 1 else None
            change_percent = ((last_close - previous_close) / previous_close) if previous_close else 0.0
            sparkline = [
                MarketSparkPoint(time=row['Date'].strftime('%Y-%m-%d'), close=float(row['Close']))
                for _, row in recent.iterrows()
            ]
        except Exception as exc:  # pragma: no cover
            logging.warning("sparkline generation failed for %s: %s", symbol, exc)
            continue

        indices.append(
            {
                "symbol": symbol,
                "name": display_name,
                "last_price": last_close,
                "change_percent": change_percent,
                "previous_close": previous_close,
                "sparkline": sparkline,
            }
        )

    if not indices:
        raise HTTPException(status_code=503, detail="Market overview unavailable")

    return MarketOverviewModel(indices=indices, updated_at=datetime.utcnow().isoformat())


app.include_router(v1)

# Mount static files if public directory exists
public_dir = Path(__file__).parent.parent / "public"
if public_dir.exists():
    app.mount("/static", StaticFiles(directory=str(public_dir)), name="static")


# Serve the test dashboard
@app.get("/test-api.html", response_class=HTMLResponse)
def serve_test_dashboard():
    """Serve the interactive API test dashboard."""
    html_path = Path(__file__).parent.parent / "public" / "test-api.html"
    if html_path.exists():
        return html_path.read_text()
    return "<h1>Dashboard not found. Please check deployment.</h1>"


# Legacy API endpoint (redirect to v1 for backward compatibility)
# Returns data in the format the dashboard expects
@app.get("/api/patterns/all")
def get_all_patterns_legacy(response: Response, limit: int = Query(default=500, ge=1, le=1000)):
    """Legacy endpoint for backward compatibility. Returns dashboard-compatible format.
    
    Calls the v1 endpoint internally and transforms the data to the format the dashboard expects.
    """
    # Call the v1 endpoint
    v1_response = patterns_all_v1(response, limit=min(limit, 500), cursor=None)
    
    # v1 returns {"items": [...], "next": ...}, extract items
    v1_items = v1_response.get("items", []) if isinstance(v1_response, dict) else []
    
    # Transform to dashboard format
    dashboard_format = []
    for item in v1_items:
        ticker = item.get("ticker", "UNKNOWN")
        pattern = item.get("pattern", "VCP")
        confidence = item.get("confidence", 0)
        price = item.get("price") or item.get("pivot_price") or 0
        rs = item.get("rs_rating") or item.get("rs") or 50
        sector = item.get("sector") or item.get("meta", {}).get("sector") or "Unknown"
        industry = item.get("industry") or item.get("meta", {}).get("industry") or sector
        pivot_price = item.get("pivot_price") or price or 0
        stop_loss = item.get("stop_loss") or (pivot_price * 0.92 if pivot_price else None)
        days_in_pattern = item.get("days_in_pattern") or item.get("meta", {}).get("days_in_pattern") or 0
        name = item.get("name") or item.get("meta", {}).get("name") or f"{ticker} Corp"

        normalized_confidence = confidence
        if normalized_confidence and normalized_confidence > 1:
            normalized_confidence = normalized_confidence / 100

        dashboard_item = {
            "symbol": ticker,
            "name": name,
            "sector": sector,
            "industry": industry,
            "pattern_type": pattern,
            "confidence": normalized_confidence or 0,
            "pivot_price": pivot_price,
            "stop_loss": stop_loss,
            "current_price": price or 0,
            "days_in_pattern": int(days_in_pattern),
            "rs_rating": int(rs),
            "trend_strength": item.get("trend_strength"),
            "volume_multiple": item.get("volume_multiple"),
            "average_volume": item.get("average_volume"),
            "market_cap": item.get("market_cap"),
            "market_cap_human": item.get("market_cap_human"),
            "entry": price or 0,
            "target": pivot_price * 1.2 if pivot_price else None,
            "action": "Analyze",
        }
        dashboard_format.append(dashboard_item)
    
    return dashboard_format


# Market environment endpoint (used by dashboard)
@app.get("/api/market/environment")
def get_market_environment():
    """Get current market environment for dashboard."""
    return {
        "current_trend": "Confirmed Uptrend",
        "days_in_trend": 23,
        "distribution_days": 2,
        "follow_through_date": "2025-09-15",
        "market_health_score": 78,
        "breadth_indicators": {
            "advance_decline_line": "Strong",
            "new_highs_vs_lows": "245 vs 23",
            "up_volume_ratio": "68%"
        }
    }


# Portfolio endpoint (used by dashboard)
@app.get("/api/portfolio/positions")
def get_portfolio_positions():
    """Get portfolio positions for dashboard."""
    # Return empty for now - could be extended later
    return []


# Debug endpoint to show exactly what data the frontend should use
@app.get("/admin/frontend-data-sample")
def frontend_data_sample():
    """Return a sample of exactly what the frontend should fetch and how to display it."""
    v1_response = patterns_all_v1(Response(), limit=3, cursor=None)
    
    return {
        "instructions": "The frontend should call /v1/patterns/all and transform like this:",
        "api_url": "https://legend-api.onrender.com/v1/patterns/all",
        "raw_v1_response": v1_response,
        "frontend_code": """
// Correct way to fetch and display patterns:
fetch('https://legend-api.onrender.com/v1/patterns/all?limit=100')
  .then(r => r.json())
  .then(data => {
    const patterns = data.items.map(item => ({
      symbol: item.ticker,
      name: item.ticker + ' Corp',
      pattern_type: item.pattern,
      confidence: item.confidence,
      rs_rating: item.rs || 80,
      current_price: item.price,
      pivot_price: item.price,
      stop_loss: item.price * 0.92,
      target: item.price * 1.20,
      entry: item.price,
      days_in_pattern: 15,
      sector: 'Technology',
      action: 'Analyze'
    }));
    console.log('Patterns ready:', patterns);
    // Now populate your table with patterns array
  });
        """,
        "test_it_now": "Open browser console and paste the code above to see it work!"
    }


# Debug endpoint to list all routes
@app.get("/admin/list-routes")
def list_all_routes():
    """List all registered routes to debug routing issues."""
    routes = []
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            routes.append({
                "path": route.path,
                "methods": list(route.methods) if route.methods else [],
                "name": route.name if hasattr(route, "name") else None
            })
    # Filter to show only patterns-related routes
    patterns_routes = [r for r in routes if 'pattern' in r['path'].lower() or 'api' in r['path'].lower()]
    return {
        "total_routes": len(routes),
        "patterns_related": patterns_routes,
        "all_routes": routes
    }


# Debug endpoint to test data transformation
@app.get("/admin/test-legacy-transform")
def test_legacy_transform():
    """Debug endpoint to test the legacy data transformation and diagnose issues."""
    import traceback as tb
    try:
        from .db import engine  # type: ignore
        from .db_queries import fetch_patterns  # type: ignore
        
        items, _ = fetch_patterns(engine, limit=3, cursor=None)
        
        result = {
            "raw_count": len(items),
            "raw_sample": items[0] if items else None,
            "transformed": [],
            "legacy_call_result": None,
            "legacy_call_error": None
        }
        
        for item in items:
            ticker = item.get("ticker", "UNKNOWN")
            pattern = item.get("pattern", "VCP")
            confidence = item.get("confidence", 0)
            price = item.get("price", 0)
            rs = item.get("rs", 80)
            
            result["transformed"].append({
                "symbol": ticker,
                "pattern_type": pattern,
                "confidence": confidence,
                "price": price,
                "rs_rating": int(rs or 80)
            })
        
        # Now actually CALL the legacy endpoint to see what happens
        try:
            from fastapi.responses import Response
            from fastapi import Query
            legacy_response = get_all_patterns_legacy(Response(), limit=3)
            result["legacy_call_result"] = legacy_response
        except Exception as legacy_err:
            result["legacy_call_error"] = {
                "error": str(legacy_err),
                "type": type(legacy_err).__name__,
                "traceback": tb.format_exc()
            }
        
        return result
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__, "traceback": tb.format_exc()}


# Database initialization endpoint (one-time use, no auth for now)
@app.post("/admin/init-db")
def init_database_endpoint():
    """Initialize database schema by running SQL migrations. Use once after deploy."""
    try:
        from .db import engine  # type: ignore
        from sqlalchemy import text
        
        migrations_dir = Path(__file__).parent.parent / "migrations" / "sql"
        sql_files = sorted(migrations_dir.glob("*.sql"))
        
        results = []
        for sql_file in sql_files:
            with open(sql_file, "r") as f:
                sql = f.read()
            
            # Split and execute
            statements = [s.strip() for s in sql.split(";") if s.strip()]
            with engine.begin() as conn:
                for stmt in statements:
                    if stmt:
                        try:
                            conn.execute(text(stmt))
                            results.append(f"✓ {sql_file.name}")
                        except Exception as e:
                            results.append(f"⚠ {sql_file.name}: {str(e)[:100]}")
        
        return {"ok": True, "results": results}
    except Exception as e:
        logging.error(f"Database init failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Init failed: {str(e)}")


@app.post("/admin/seed-demo")
def seed_demo_data():
    """Seed the database with mock VCP patterns for testing."""
    try:
        from .db import engine  # type: ignore
        from sqlalchemy import text
        from datetime import datetime, timedelta
        
        # Create 3 mock VCP detections
        mock_patterns = [
            {
                "ticker": "NVDA",
                "pattern": "VCP",
                "as_of": datetime.now() - timedelta(days=2),
                "confidence": 85.5,
                "rs": 92.3,
                "price": 495.22,
                "meta": '{"contractions": 3, "base_depth": 0.18, "pivot": 495.22}'
            },
            {
                "ticker": "PLTR",
                "pattern": "VCP",
                "as_of": datetime.now() - timedelta(days=1),
                "confidence": 78.2,
                "rs": 88.5,
                "price": 28.45,
                "meta": '{"contractions": 4, "base_depth": 0.25, "pivot": 28.45}'
            },
            {
                "ticker": "CRWD",
                "pattern": "VCP",
                "as_of": datetime.now(),
                "confidence": 91.0,
                "rs": 95.1,
                "price": 285.67,
                "meta": '{"contractions": 3, "base_depth": 0.15, "pivot": 285.67}'
            }
        ]
        
        with engine.begin() as conn:
            for pattern in mock_patterns:
                conn.execute(
                    text("""
                        INSERT INTO patterns (ticker, pattern, as_of, confidence, rs, price, meta)
                        VALUES (:ticker, :pattern, :as_of, :confidence, :rs, :price, :meta)
                        ON CONFLICT (ticker, pattern, as_of) DO UPDATE
                        SET confidence=EXCLUDED.confidence, rs=EXCLUDED.rs, price=EXCLUDED.price, meta=EXCLUDED.meta
                    """),
                    pattern
                )
        
        return {"ok": True, "seeded": len(mock_patterns), "patterns": [p["ticker"] for p in mock_patterns]}
    except Exception as e:
        logging.error(f"Seed failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Seed failed: {str(e)}")


@app.get("/admin/test-data")
def test_data_fetch(ticker: str = Query(default="AAPL")):
    """Test endpoint to check what data we're getting from yfinance."""
    try:
        import yfinance as yf
        import pandas as pd
        
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")
        
        if df.empty:
            return {"error": "No data returned from yfinance"}
        
        df = df.reset_index()
        
        return {
            "ticker": ticker,
            "rows": len(df),
            "columns": list(df.columns),
            "first_row": df.iloc[0].to_dict() if len(df) > 0 else None,
            "last_row": df.iloc[-1].to_dict() if len(df) > 0 else None,
            "sample_close": float(df['Close'].iloc[-1]) if 'Close' in df.columns else None,
            "sample_volume": float(df['Volume'].iloc[-1]) if 'Volume' in df.columns else None,
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/admin/run-scan")
def run_scan_endpoint(limit: int = Query(default=7, ge=1, le=20)):
    """Trigger a scan for VCP patterns on a limited set of tickers."""
    try:
        import sys
        from pathlib import Path
        from datetime import datetime
        
        # Add parent to path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        
        from vcp_ultimate_algorithm import VCPDetector  # type: ignore
        from .db import engine  # type: ignore
        from .data_fetcher import fetch_stock_data  # type: ignore
        from sqlalchemy import text
        
        # Load universe
        universe_path = Path(__file__).parent.parent / "data" / "universe.csv"
        if universe_path.exists():
            with open(universe_path) as f:
                tickers = [line.strip() for line in f if line.strip()][:limit]
        else:
            tickers = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN"][:limit]
        
        detector = VCPDetector(min_price=10.0, min_volume=500000, min_contractions=2, check_trend_template=False)
        
        results = []
        for ticker in tickers:
            try:
                # Fetch data using multi-source fetcher
                df = fetch_stock_data(ticker, days=365)
                if df is None or len(df) < 60:
                    results.append(f"⊘ {ticker}: insufficient data")
                    continue
                
                # Detect
                signal = detector.detect_vcp(df, ticker)
                
                if signal.detected:
                    # Upsert to database
                    record = {
                        "ticker": ticker,
                        "pattern": "VCP",
                        "as_of": datetime.now(),
                        "confidence": float(signal.confidence_score),
                        "rs": None,
                        "price": float(signal.pivot_price) if signal.pivot_price else None,
                        "meta": text(f"""'{{"contractions": {len(signal.contractions)}}}'::jsonb""")
                    }
                    
                    with engine.begin() as conn:
                        conn.execute(
                            text("""
                                INSERT INTO patterns (ticker, pattern, as_of, confidence, rs, price, meta)
                                VALUES (:ticker, :pattern, :as_of, :confidence, :rs, :price, :meta)
                                ON CONFLICT (ticker, pattern, as_of) DO UPDATE
                                SET confidence=EXCLUDED.confidence, price=EXCLUDED.price, meta=EXCLUDED.meta
                            """),
                            {
                                "ticker": ticker,
                                "pattern": "VCP",
                                "as_of": datetime.now(),
                                "confidence": float(signal.confidence_score),
                                "rs": None,
                                "price": float(signal.pivot_price) if signal.pivot_price else None,
                                "meta": f'{{"contractions": {len(signal.contractions)}}}'
                            }
                        )
                    
                    results.append(f"✓ {ticker}: VCP (conf={signal.confidence_score:.1f}%)")
                else:
                    results.append(f"✗ {ticker}: no VCP")
                    
            except Exception as e:
                results.append(f"⚠ {ticker}: {str(e)[:50]}")
        
        return {"ok": True, "scanned": len(tickers), "results": results}
        
    except Exception as e:
        logging.error(f"Scan failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


# Security headers (optional, no-op if lib missing)
try:
    from secure import Secure  # type: ignore

    secure = Secure()

    @app.middleware("http")
    async def set_secure_headers(request, call_next):
        resp = await call_next(request)
        # FastAPI integration helper
        secure.framework.fastapi(resp)  # type: ignore[attr-defined]
        return resp
except Exception:
    pass


# Boot log
try:
    logging.info("legend-api boot", extra={"module": "legend-api", "port_env": os.getenv("PORT"), "mock": mock_enabled()})
except Exception:
    pass

# Warn if DATABASE_URL missing (non-fatal for /healthz)
try:
    from .config import get_database_url  # lazy import

    try:
        _ = get_database_url()
    except Exception as db_exc:  # pragma: no cover
        logging.error("database url missing or invalid", extra={"error": str(db_exc)})
except Exception:
    pass
