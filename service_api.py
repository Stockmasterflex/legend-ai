import asyncio
import hashlib
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
import threading
from datetime import datetime, date
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import httpx
import pandas as pd
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pythonjsonlogger import jsonlogger
from sqlalchemy.orm import Session
from starlette.middleware.cors import CORSMiddleware

from backtest.ingestion import load_prices, prefetch_prices
from backtest.run_backtest import scan_once
from backtest.simulate import REPORT_ROOT, summarize_range

from service_db import BacktestRun, Base as RunsBase, engine as runs_engine, get_db as get_runs_db
from service_universe import UniverseName, get_universe
from settings import is_mock_enabled, load_vcp_settings
from signals.patterns import PatternName, PatternResult, detect as detect_pattern
from vcp.vcp_detector import VCPDetector
try:
    from legend_room_backend.paper_trade import record as record_paper_trade  # type: ignore
except Exception:  # pragma: no cover - optional dependency fallback
    def record_paper_trade(*args, **kwargs):  # type: ignore
        """Fallback stub for paper trade recording when backend module is unavailable."""
        return {"status": "stub", "message": "Paper trade recording not yet implemented", "args": args, "kwargs": kwargs}

try:
    import redis
except ImportError:  # pragma: no cover - optional dependency
    redis = None  # type: ignore[assignment]

app = FastAPI(title="Legend AI — VCP API", version="0.1.0")

# CORS: allow localhost, vercel previews, and configured origins
base_allowed = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://legend-ai.vercel.app",
]
allowed_env = os.getenv("ALLOWED_ORIGINS", "")
allowed = list({*base_allowed, *[o.strip() for o in allowed_env.split(",") if o.strip()]})
origin_regex = os.getenv("ALLOWED_ORIGIN_REGEX", r"https://.*\.vercel\.app")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed,
    allow_origin_regex=origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JSON logging
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(message)s %(request_id)s")
handler.setFormatter(formatter)
logger = logging.getLogger("legend_api")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(handler)
logging.getLogger("legend.vcp").setLevel(logging.DEBUG)
logging.getLogger("legend.indicators").setLevel(logging.INFO)
logging.getLogger("legend.signals").setLevel(logging.INFO)
logging.getLogger("legend.sentiment").setLevel(logging.INFO)


@app.middleware("http")
async def add_request_id_logging(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    start = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - start) * 1000)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request",
        extra={
            "request_id": request_id,
            "path": str(request.url.path),
            "method": request.method,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response

# Prometheus
REQUESTS = Counter("legend_requests_total", "HTTP requests", ["path", "method", "status"])
LATENCY = Histogram("legend_request_latency_ms", "Latency", buckets=(5, 10, 25, 50, 100, 250, 500, 1000, 2000))
CHART_REQUESTS = Counter("legend_chart_requests_total", "Chart proxy requests", ["fallback"])
CHART_LATENCY = Histogram(
    "legend_chart_latency_ms",
    "Latency for shots rendering",
    buckets=(50, 100, 250, 500, 750, 1000, 1500, 2000, 3000, 5000),
)

@app.get("/metrics")
def metrics(request: Request):
    return app.response_class(generate_latest(), media_type=CONTENT_TYPE_LATEST)
# --- Demo/fallback routes ---
demo_router = APIRouter()

LEGEND_MOCK = is_mock_enabled()
SAMPLE_RUN = {
    "run_id": "SAMPLE-2025-09-15",
    "universe": ["AAPL","NVDA","MSFT","META","GOOGL"],
    "metrics": {"hit_rate": 0.62, "precision_at_10": 0.70, "precision_at_25": 0.66, "coverage": 125, "median_runup": 0.047},
    "patterns": [
        {"ticker":"AAPL","pattern":"VCP","score":92,"atr":2.1,"r_breakout":2.8},
        {"ticker":"NVDA","pattern":"Flag","score":88,"atr":15.3,"r_breakout":3.5},
        {"ticker":"MSFT","pattern":"VCP","score":85,"atr":6.7,"r_breakout":2.2}
    ],
    "created_at": "2025-09-15T12:00:00Z",
    "is_sample": True,
}


def _sample_scan_payload(pattern: PatternName, universe: str, limit: Optional[int] = None) -> Dict[str, Any]:
    rows = []

    def _maybe_float(value: Any) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    for item in SAMPLE_RUN.get("patterns", []):
        symbol = item.get("ticker") or item.get("symbol")
        if not symbol:
            continue
        score = _maybe_float(item.get("score")) or 75.0
        entry = _maybe_float(item.get("r_breakout"))
        atr = _maybe_float(item.get("atr"))
        stop = entry - atr if entry is not None and atr is not None else None
        target = entry + (atr * 2) if entry is not None and atr is not None else None
        key_levels = {
            "entry": entry,
            "stop": stop,
            "targets": [target] if target is not None else [],
        }
        rows.append({
            "symbol": symbol,
            "score": score,
            "entry": entry,
            "stop": stop,
            "targets": key_levels["targets"],
            "pattern": pattern,
            "overlays": {"priceLevels": key_levels},
            "chart_url": DUMMY_CHART_URL_TMPL.format(symbol=symbol),
            "avg_price": entry,
            "avg_volume": None,
            "atr14": atr,
            "key_levels": key_levels,
            "meta": {"evidence": ["sample payload"], "is_sample": True},
            "chart_meta": {"fallback": True, "overlay_applied": False, "source": "dummy", "dry_run": True},
        })

    if limit is not None:
        rows = rows[: max(1, min(limit, len(rows)))]

    return {
        "pattern": pattern,
        "universe": universe,
        "count": len(rows),
        "results": rows,
        "is_sample": True,
    }

@demo_router.get("/health")
def demo_health():
    from datetime import datetime, timezone
    return {"ok": True, "service": "legend-api", "ts": datetime.now(timezone.utc).isoformat()}

@demo_router.get("/sample_run")
def sample_run():
    return SAMPLE_RUN

@demo_router.get("/latest_run")
def latest_run():
    # Always available sample/latest response
    out = dict(SAMPLE_RUN)
    out["is_sample"] = True
    try:
        # Attach indicators/signals/sentiment for first few tickers
        from indicators.ta import compute_all_indicators
        from signals.core import score_from_indicators
        from sentiment.core import fetch_headlines_and_sentiment
        enrich = []
        for p in out.get("patterns", [])[:3]:
            sym = p.get("ticker") or p.get("symbol")
            df = yf_history_cached((sym or "SPY"), period="6mo")
            if df is None or df.empty:
                continue
            ind = compute_all_indicators(df)
            sig = score_from_indicators(ind, df)
            sen = fetch_headlines_and_sentiment(sym) if os.getenv("NEWSAPI_KEY") else {"label":"neutral","is_sample":True}
            enrich.append({"symbol": sym, "indicators": ind, "signal": sig, "sentiment": sen})
        out["analysis"] = enrich
    except Exception:
        pass
    return out

@demo_router.post("/create_run")
def create_run_demo(payload: dict):
    from datetime import datetime
    if LEGEND_MOCK:
        return {"run_id": f"MOCK-{datetime.now().strftime('%Y%m%d-%H%M%S')}", "status": "submitted", "estimated_completion": "2-3 minutes", "is_mock": True}
    return {"run_id": f"RUN-{datetime.now().strftime('%Y%m%d-%H%M%S')}", "status": "submitted"}

app.include_router(demo_router, prefix="/api", tags=["demo"])


@app.on_event("startup")
async def _startup_warm_caches() -> None:
    _warm_cache_background()

SHOTS_BASE_URL = os.getenv("SHOTS_BASE_URL", "https://legend-shots.onrender.com")
DUMMY_CHART_URL_TMPL = "https://dummyimage.com/1200x628/0b1221/9be7ff.png&text={symbol}+Chart"

DEFAULT_SCAN_PERIOD = os.getenv("SCAN_DEFAULT_PERIOD", "18mo")
_cpu_guess = os.cpu_count() or 4
DEFAULT_SCAN_WORKERS = int(os.getenv("SCAN_WORKERS", str(max(4, min(8, _cpu_guess)))))
DEFAULT_CHART_CONCURRENCY = int(os.getenv("SCAN_CHART_CONCURRENCY", "4"))
SYMBOL_SCAN_LIMIT = int(os.getenv("SCAN_SYMBOL_LIMIT", "0"))
SCAN_CACHE_TTL = int(os.getenv("SCAN_CACHE_TTL", "240"))
MIN_PRICE_DEFAULT = float(os.getenv("SCAN_MIN_PRICE", "5"))
MIN_VOLUME_DEFAULT = float(os.getenv("SCAN_MIN_VOLUME", "500000"))
MAX_ATR_RATIO_DEFAULT = float(os.getenv("SCAN_MAX_ATR_RATIO", "0.08"))
# Hard server-side minimums (enforced regardless of client request)
MIN_PRICE_HARD = float(os.getenv("SCAN_MIN_PRICE_HARD", "20"))
MIN_VOLUME_HARD = float(os.getenv("SCAN_MIN_VOLUME_HARD", "750000"))
# Max distance from 52-week high (e.g., 0.25 means within 25%)
MAX_DIST_52W_HIGH = float(os.getenv("SCAN_MAX_DIST_52W_HIGH", "0.25"))
SCAN_52W_BAND = float(os.getenv("SCAN_52W_BAND", str(MAX_DIST_52W_HIGH)))
# Alerting
ALERT_QUALITY_THRESHOLD = float(os.getenv("ALERT_PATTERN_QUALITY_THRESHOLD", "0.20"))
ALERT_MIN_SAMPLES = int(os.getenv("ALERT_MIN_SAMPLES", "25"))
ALERT_SLACK_WEBHOOK = os.getenv("SLACK_ALERT_WEBHOOK", "").strip()

SCAN_SAMPLE_ENABLE = os.getenv("SCAN_SAMPLE_ENABLE", "0").strip() in {"1", "true", "TRUE", "yes", "on"}
_BOOL_TRUE = {"1", "true", "TRUE", "yes", "on"}
SCAN_REDIS_RESPONSE_CACHE_ENABLED = os.getenv("SCAN_REDIS_CACHE", "0").strip() in _BOOL_TRUE
SCAN_RESPONSE_CACHE_TTL = int(os.getenv("SCAN_RESPONSE_CACHE_TTL", str(SCAN_CACHE_TTL)))
SCAN_RATE_LIMIT = max(0, int(os.getenv("SCAN_RATE_LIMIT", "60") or 0))
SCAN_RATE_WINDOW = max(1, int(os.getenv("SCAN_RATE_WINDOW", "60") or 1))
CHART_RATE_LIMIT = max(0, int(os.getenv("CHART_RATE_LIMIT", "120") or 0))
CHART_RATE_WINDOW = max(1, int(os.getenv("CHART_RATE_WINDOW", "60") or 1))
SCAN_PREFETCH_CHARTS = os.getenv("SCAN_PREFETCH_CHARTS", "0").strip() in {"1", "true", "TRUE", "yes", "on"}
SCAN_PREFETCH_TTL = int(os.getenv("SCAN_PREFETCH_TTL", str(900)))


class PaperTradeRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=16)
    entry: float = Field(..., gt=0)
    stop: float = Field(..., gt=0)
    confidence: float = Field(..., ge=0, le=100)
    notes: Optional[str] = Field(None, max_length=1000)
    meta: Optional[Dict[str, Any]] = None


_timeframe_defaults = {
    "1d": {"period": os.getenv("SCAN_PERIOD_1D", "18mo"), "interval": "1d", "fetch_interval": "1d", "min_bars": 180},
    "1wk": {
        "period": os.getenv("SCAN_PERIOD_1W", "3y"),
        "interval": "1wk",
        "fetch_interval": os.getenv("SCAN_FETCH_INTERVAL_1W", "1d"),
        "resample": "1W",
        "min_bars": 120,
    },
    "60m": {
        "period": os.getenv("SCAN_PERIOD_60M", "30d"),
        "interval": "60m",
        "fetch_interval": "60m",
        "min_bars": 160,
    },
}


def _warm_cache_background() -> None:
    def _run() -> None:
        combos = [
            ("sp500", "1d"),
            ("nasdaq100", "1d"),
            ("sp500", "1wk"),
            ("nasdaq100", "1wk"),
            ("sp500", "60m"),
        ]
        for universe, timeframe in combos:
            try:
                cfg = _resolve_timeframe_config(timeframe)
                fetch_interval = cfg.get("fetch_interval", cfg.get("interval", "1d"))
                min_rows = int(cfg.get("min_bars", 120))
                resample_factor = 5 if cfg.get("resample") and fetch_interval == "1d" else 1
                fetch_min_rows = max(min_rows * resample_factor, min_rows)
                symbols = _bounded_symbols(get_universe(universe))
                if timeframe == "1wk":
                    cap = int(os.getenv("SCAN_SYMBOL_LIMIT_1W", "100"))
                    symbols = symbols[:cap]
                elif timeframe == "60m":
                    cap = int(os.getenv("SCAN_SYMBOL_LIMIT_60M", "12"))
                    symbols = symbols[:cap]
                prefetch_prices(
                    symbols,
                    period=cfg.get("period", DEFAULT_SCAN_PERIOD),
                    interval=fetch_interval,
                    min_rows=fetch_min_rows,
                )
            except Exception as exc:
                logger.debug("warm cache failed", extra={"universe": universe, "timeframe": timeframe, "error": str(exc)})

    threading.Thread(target=_run, daemon=True).start()

_redis_client = None
if os.getenv("REDIS_URL") and redis is not None:  # pragma: no branch - simple init
    try:
        _redis_client = redis.Redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)
    except Exception as exc:  # pragma: no cover - redis optional
        logger.warning("redis init failed", extra={"error": str(exc)})
        _redis_client = None

_local_scan_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_cache_lock = threading.Lock()
_rate_limiter_counters: Dict[str, Tuple[int, float]] = {}
_rate_limiter_lock = threading.Lock()
_prefetch_lock = threading.Lock()
_prefetch_state: Dict[Tuple[str, str], float] = {}

_PATTERN_ALIASES: Dict[str, PatternName] = {
    "vcp": "vcp",
    "cup_handle": "cup_handle",
    "cup-handle": "cup_handle",
    "cup": "cup_handle",
    "cuphandle": "cup_handle",
    "hns": "hns",
    "head_and_shoulders": "hns",
    "head-shoulders": "hns",
    "headshoulders": "hns",
    "flag": "flag",
    "pennant": "flag",
    "flag_pennant": "flag",
    "wedge": "wedge",
    "double": "double",
    "double_top": "double",
    "double_bottom": "double",
}


def _canonical_pattern(name: str) -> PatternName:
    key = (name or "").strip().lower().replace(" ", "_").replace("-", "_")
    if key not in _PATTERN_ALIASES:
        raise HTTPException(status_code=400, detail=f"Unsupported pattern '{name}'")
    return _PATTERN_ALIASES[key]


def _canonical_universe(name: str) -> UniverseName:
    key = (name or "").strip().lower()
    if key not in {"sp500", "nasdaq100"}:
        raise HTTPException(status_code=400, detail=f"Unsupported universe '{name}'")
    return key  # type: ignore[return-value]


def _cache_key(pattern: PatternName, symbol: str, timeframe: str, min_price: float, min_volume: float) -> str:
    return f"scan:{pattern}:{timeframe}:{symbol.upper()}:{int(min_price)}:{int(min_volume)}"


def _cache_get(key: str) -> Optional[Dict[str, Any]]:
    if _redis_client is not None:
        try:
            payload = _redis_client.get(key)
            if payload:
                return json.loads(payload)
        except Exception as exc:  # pragma: no cover - redis optional
            logger.debug("scan cache redis get failed", extra={"error": str(exc)})
    else:
        with _cache_lock:
            cached = _local_scan_cache.get(key)
        if cached:
            expires_at, data = cached
            if expires_at > time.time():
                return json.loads(json.dumps(data))
            with _cache_lock:
                _local_scan_cache.pop(key, None)
    return None


def _cache_set(key: str, value: Dict[str, Any]) -> None:
    expires_at = time.time() + SCAN_CACHE_TTL
    if _redis_client is not None:
        try:
            _redis_client.setex(key, SCAN_CACHE_TTL, json.dumps(value))
            return
        except Exception as exc:  # pragma: no cover - redis optional
            logger.debug("scan cache redis set failed", extra={"error": str(exc)})
    with _cache_lock:
        _local_scan_cache[key] = (expires_at, json.loads(json.dumps(value)))


def _rate_limit_check(key: str, limit: int, window: int) -> Tuple[bool, int]:
    if limit <= 0 or window <= 0:
        return False, 0
    now = time.time()
    with _rate_limiter_lock:
        count, reset_at = _rate_limiter_counters.get(key, (0, now + window))
        if now >= reset_at:
            count = 0
            reset_at = now + window
        if count >= limit:
            retry_after = max(1, int(reset_at - now))
            return True, retry_after
        _rate_limiter_counters[key] = (count + 1, reset_at)
        retry_after = max(1, int(reset_at - now))
        return False, retry_after


def _response_cache_key(prefix: str, payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def _response_cache_get(key: str) -> Optional[Dict[str, Any]]:
    if not (SCAN_REDIS_RESPONSE_CACHE_ENABLED and _redis_client and SCAN_RESPONSE_CACHE_TTL > 0):
        return None
    try:
        cached = _redis_client.get(key)
        if cached:
            return json.loads(cached)
    except Exception as exc:
        logger.debug("response cache get failed", extra={"key": key, "error": str(exc)})
    return None


def _response_cache_set(key: str, value: Dict[str, Any]) -> None:
    if not (SCAN_REDIS_RESPONSE_CACHE_ENABLED and _redis_client and SCAN_RESPONSE_CACHE_TTL > 0):
        return
    try:
        _redis_client.setex(key, SCAN_RESPONSE_CACHE_TTL, json.dumps(value))
    except Exception as exc:
        logger.debug("response cache set failed", extra={"key": key, "error": str(exc)})


def _resolve_timeframe_config(timeframe: str) -> Dict[str, Any]:
    tf = timeframe.lower()
    if tf not in _timeframe_defaults:
        raise HTTPException(status_code=400, detail=f"Unsupported timeframe '{timeframe}'")
    return _timeframe_defaults[tf]


def _resample_ohlc(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    if not len(df) or "Date" not in df.columns:
        return df
    try:
        temp = df.copy()
        temp["Date"] = pd.to_datetime(temp["Date"], errors="coerce")
        temp = temp.dropna(subset=["Date"]).set_index("Date")
        ohlc_dict = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
        resampled = temp.resample(rule).apply(ohlc_dict).dropna()
        resampled = resampled.reset_index()
        return resampled
    except Exception:
        return df


def _scan_symbol(
    pattern: PatternName,
    symbol: str,
    *,
    timeframe: str,
    min_price: float,
    min_volume: float,
    max_atr_ratio: float,
) -> Optional[Dict[str, Any]]:
    cache_key = _cache_key(pattern, symbol, timeframe, min_price, min_volume)
    cached = _cache_get(cache_key)
    if cached is not None:
        atr_cached = cached.get("atr14")
        if max_atr_ratio and atr_cached and cached.get("entry"):
            if atr_cached / max(float(cached["entry"]), 1e-6) > max_atr_ratio:
                return None
        return json.loads(json.dumps(cached))
    cfg = _resolve_timeframe_config(timeframe)
    fetch_interval = cfg.get("fetch_interval", cfg.get("interval", "1d"))
    min_rows = int(cfg.get("min_bars", 120))
    resample_factor = 5 if cfg.get("resample") and fetch_interval == "1d" else 1
    fetch_min_rows = max(min_rows * resample_factor, min_rows)
    try:
        df = load_prices(
            symbol,
            period=cfg.get("period", DEFAULT_SCAN_PERIOD),
            interval=fetch_interval,
            refresh=False,
            min_rows=fetch_min_rows,
        )
    except Exception as exc:
        logger.debug("scan load failed", extra={"symbol": symbol, "pattern": pattern, "error": str(exc)})
        return None
    if df is None or len(df) < fetch_min_rows:
        return None
    if cfg.get("resample"):
        df = _resample_ohlc(df, cfg["resample"])
        if df is None or len(df) < min_rows:
            return None
    try:
        prices = df["Close"].astype(float)
        highs = df.get("High").astype(float) if "High" in df.columns else prices
        last_close = float(prices.iloc[-1])
        avg_price = float(prices.tail(30).mean()) if len(prices) >= 30 else float(prices.mean())
    except Exception:
        avg_price, last_close, highs = 0.0, 0.0, None
    # Enforce server-side minimums
    min_price = max(min_price, MIN_PRICE_HARD)
    if avg_price < min_price:
        return None
    # 52-week high proximity filter (best-effort if enough history)
    try:
        window = min(len(df), 252)
        if highs is not None and window >= 60:  # need a reasonable window
            high_52w = float(highs.tail(window).max())
            if high_52w > 0:
                if last_close < (1.0 - SCAN_52W_BAND) * high_52w:
                    return None
    except Exception:
        pass
    try:
        volumes = df.get("Volume")
        avg_volume = float(volumes.tail(30).mean()) if volumes is not None and len(volumes) >= 30 else float(volumes.mean()) if volumes is not None else 0.0
    except Exception:
        avg_volume = 0.0
    min_volume = max(min_volume, MIN_VOLUME_HARD)
    if avg_volume < min_volume:
        return None
    try:
        outcome = detect_pattern(pattern, df, symbol, timeframe=timeframe)
    except Exception as exc:
        logger.debug("pattern detect failed", extra={"symbol": symbol, "pattern": pattern, "error": str(exc)})
        return None
    if not outcome:
        return None
    score = float(outcome.get("score", 0.0))
    entry = outcome.get("entry")
    stop = outcome.get("stop")
    targets = outcome.get("targets") or []
    overlays = outcome.get("overlays")
    if entry is None or stop is None or not targets:
        return None
    try:
        entry_val = float(entry)
        stop_val = float(stop)
        targets_val = [float(t) for t in targets][:3]
    except Exception:
        return None
    atr_val = None
    for key in ("atr14", "atr"):
        if key in outcome and outcome[key] is not None:
            atr_val = float(outcome[key])
            break
    if atr_val and entry_val:
        atr_ratio = atr_val / max(entry_val, 1e-6)
        if max_atr_ratio and atr_ratio > max_atr_ratio:
            return None
    key_levels = outcome.get("key_levels") if isinstance(outcome.get("key_levels"), dict) else None
    confidence = None
    try:
        confidence = float(outcome.get("confidence"))
    except Exception:
        confidence = None
    if confidence is None:
        confidence = max(0.0, min(100.0, float(score)))

    row = {
        "symbol": symbol,
        "score": round(score, 2),
        "confidence": round(float(confidence), 1),
        "entry": entry_val,
        "stop": stop_val,
        "targets": targets_val,
        "pattern": pattern,
        "overlays": overlays,
        "meta": {k: v for k, v in outcome.items() if k not in {"score", "entry", "stop", "targets", "overlays", "pattern", "key_levels"}},
        "avg_price": avg_price,
        "avg_volume": avg_volume,
    }
    if key_levels:
        row["key_levels"] = key_levels
    if atr_val is not None:
        row["atr14"] = round(float(atr_val), 4)
    sector = get_sector_safe(symbol)
    if sector:
        row["sector"] = sector
        row.setdefault("meta", {})["sector"] = sector
    _cache_set(cache_key, row)
    return json.loads(json.dumps(row))


def _bounded_symbols(symbols: List[str]) -> List[str]:
    if SYMBOL_SCAN_LIMIT > 0:
        return symbols[: SYMBOL_SCAN_LIMIT]
    return symbols


async def _attach_chart_urls(pattern: PatternName, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    semaphore = asyncio.Semaphore(max(1, DEFAULT_CHART_CONCURRENCY))
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        async def worker(row: Dict[str, Any]) -> None:
            params = {"symbol": row["symbol"], "pattern": pattern}
            overlays = row.get("overlays") if isinstance(row.get("overlays"), dict) else None
            price_levels = overlays.get("priceLevels") if overlays else None
            if isinstance(price_levels, dict):
                for key in ("entry", "stop"):
                    val = price_levels.get(key)
                    if val is not None:
                        params[key] = str(val)
                targets = price_levels.get("targets")
                if isinstance(targets, list) and targets:
                    params["target"] = str(targets[0])

            async with semaphore:
                row["chart_url"] = await _fetch_chart_url(row["symbol"], params=params, overlays=overlays, client=client)

        await asyncio.gather(*(worker(r) for r in rows))


async def _fetch_chart_url(
    symbol: str,
    params: Optional[Dict[str, Any]] = None,
    overlays: Optional[Dict[str, Any]] = None,
    client: Optional[httpx.AsyncClient] = None,
    *,
    include_meta: bool = False,
) -> Any:
    params = params or {"symbol": symbol}
    url = f"{SHOTS_BASE_URL.rstrip('/')}/screenshot"
    own_client = client is None
    session = client or httpx.AsyncClient(timeout=httpx.Timeout(60.0))
    overlay_applied = bool(overlays)
    meta: Dict[str, Any] = {
        "source": SHOTS_BASE_URL,
        "overlay_applied": overlay_applied,
        "fallback": False,
    }
    start_ts = time.time()
    try:
        if overlays:
            response = await session.post(url, params=params, json={"overlays": overlays})
        else:
            response = await session.get(url, params=params)
        if response.status_code == 200:
            try:
                data = response.json()
            except Exception:
                data = {}
            chart_url = data.get("chart_url") or data.get("url")
            if isinstance(chart_url, str) and chart_url:
                meta["fallback"] = bool(data.get("dry_run") or data.get("error"))
                if "dry_run" in data:
                    meta["dry_run"] = bool(data.get("dry_run"))
                if data.get("error"):
                    meta["error"] = str(data.get("error"))
                if data.get("overlay_counts"):
                    meta.setdefault("overlay_counts", data.get("overlay_counts"))
                duration_ms = (time.time() - start_ts) * 1000.0
                meta["duration_ms"] = round(duration_ms, 2)
                CHART_LATENCY.observe(duration_ms)
                CHART_REQUESTS.labels(fallback=str(meta["fallback"]).lower()).inc()
                if include_meta:
                    return chart_url, meta
                return chart_url
            meta["error"] = f"invalid response from shots status={response.status_code}"
        else:
            meta["error"] = f"shots status {response.status_code}"
    except Exception as exc:
        logger.debug("chart proxy error", extra={"symbol": symbol, "error": str(exc)})
        meta["error"] = str(exc)
    finally:
        if own_client:
            await session.aclose()
    dummy = DUMMY_CHART_URL_TMPL.format(symbol=symbol.upper())
    meta.update({
        "source": "dummy",
        "fallback": True,
        "overlay_applied": overlay_applied,
        "dry_run": meta.get("dry_run", False),
    })
    duration_ms = (time.time() - start_ts) * 1000.0
    meta["duration_ms"] = round(duration_ms, 2)
    CHART_LATENCY.observe(duration_ms)
    CHART_REQUESTS.labels(fallback="true").inc()
    if include_meta:
        return dummy, meta
    return dummy


async def _run_pattern_scan(
    pattern: PatternName,
    universe: UniverseName,
    limit: int,
    *,
    timeframe: str,
    min_price: float,
    min_volume: float,
    max_atr_ratio: float,
) -> Dict[str, Any]:
    symbols = _bounded_symbols(get_universe(universe))
    if timeframe == "1d":
        cap = int(os.getenv("SCAN_SYMBOL_LIMIT_1D", "350"))
        if cap > 0:
            symbols = symbols[:cap]
    if timeframe == "1wk":
        cap = int(os.getenv("SCAN_SYMBOL_LIMIT_1W", "80"))
        symbols = symbols[:cap]
    elif timeframe == "60m":
        cap = int(os.getenv("SCAN_SYMBOL_LIMIT_60M", "6"))
        symbols = symbols[:cap]
    workers = max(2, min(DEFAULT_SCAN_WORKERS, len(symbols)))
    results: List[Dict[str, Any]] = []
    if not symbols:
        return {"pattern": pattern, "universe": universe, "count": 0, "results": []}
    cfg = _resolve_timeframe_config(timeframe)
    fetch_interval = cfg.get("fetch_interval", cfg.get("interval", "1d"))
    min_rows = int(cfg.get("min_bars", 120))
    resample_factor = 5 if cfg.get("resample") and fetch_interval == "1d" else 1
    fetch_min_rows = max(min_rows * resample_factor, min_rows)
    prefetch_key = (universe, f"{timeframe}:{fetch_interval}")
    should_prefetch = True
    with _prefetch_lock:
        last = _prefetch_state.get(prefetch_key)
        if last and (time.time() - last) < SCAN_PREFETCH_TTL:
            should_prefetch = False
        else:
            _prefetch_state[prefetch_key] = time.time()
    if should_prefetch:
        try:
            prefetch_prices(
                symbols,
                period=cfg.get("period", DEFAULT_SCAN_PERIOD),
                interval=fetch_interval,
                min_rows=fetch_min_rows,
            )
        except Exception:
            logger.debug("prefetch failed", extra={"pattern": pattern, "timeframe": timeframe})
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                _scan_symbol,
                pattern,
                sym,
                timeframe=timeframe,
                min_price=min_price,
                min_volume=min_volume,
                max_atr_ratio=max_atr_ratio,
            )
            for sym in symbols
        ]
        for future in futures:
            try:
                row = future.result()
            except Exception as exc:
                logger.debug("scan worker crashed", extra={"pattern": pattern, "error": str(exc)})
                continue
            if row:
                results.append(row)
    results = [r for r in results if r.get("score")]
    results.sort(key=lambda r: r.get("score", 0.0), reverse=True)
    count = len(results)
    trimmed = results[:limit]
    if SCAN_PREFETCH_CHARTS and trimmed:
        await _attach_chart_urls(pattern, trimmed)
    else:
        for row in trimmed:
            row.setdefault("chart_url", None)
    for row in trimmed:
        row["targets"] = [round(float(t), 4) for t in row.get("targets", [])]
        row["score"] = round(float(row.get("score", 0.0)), 2)
        row["entry"] = round(float(row.get("entry", 0.0)), 4)
        row["stop"] = round(float(row.get("stop", 0.0)), 4)
    return {
        "pattern": pattern,
        "universe": universe,
        "count": count,
        "results": trimmed,
    }

# -------- Utilities: fetch OHLCV via yfinance (cached) --------
@lru_cache(maxsize=256)
def yf_history_cached(symbol: str, period: str = "6mo"):
    import yfinance as yf
    t = yf.Ticker(symbol)
    df = t.history(period=period, auto_adjust=False)
    if df is None or df.empty:
        return pd.DataFrame()
    df.index.name = "Date"
    df.reset_index(inplace=True)
    return df

# -------- Indicators/Signals/Sentiment endpoints (Phase 3/4) --------
@app.get("/api/v1/indicators")
def api_indicators(symbol: str = Query(...), period: str = Query("6mo")) -> Dict[str, Any]:
    try:
        from indicators.ta import compute_all_indicators
        df = yf_history_cached(symbol.upper(), period=period)
        if df.empty:
            raise RuntimeError("no_data")
        out = compute_all_indicators(df)
        return {"symbol": symbol.upper(), "period": period, "indicators": out, "is_sample": False}
    except Exception:
        # sample payload
        return {
            "symbol": symbol.upper(),
            "period": period,
            "indicators": {
                "ema21": None, "ema50": None, "ema200": None, "rsi14": 50.0,
                "macd": {"macd": 0.0, "signal": 0.0, "hist": 0.0},
                "bb": {"mid": None, "upper": None, "lower": None, "width": 0.12},
                "atr14": None, "stoch": {"k": 50.0, "d": 50.0}, "vol_sma50": None, "bb_width": 0.12,
            },
            "is_sample": True,
        }

@app.get("/api/v1/signals")
def api_signals(symbol: str = Query(...)) -> Dict[str, Any]:
    # Paper trading validation gate
    if os.getenv("PAPER_TRADING_REQUIRED", "false").strip().lower() in {"1", "true", "yes", "on"}:
        if os.getenv("PAPER_TRADING_VALIDATED", "false").strip().lower() not in {"1", "true", "yes", "on"}:
            raise HTTPException(status_code=503, detail="Paper trading validation required before live signals. Set PAPER_TRADING_VALIDATED=true to bypass.")
    try:
        from indicators.ta import compute_all_indicators
        from signals.core import score_from_indicators
        df = yf_history_cached(symbol.upper(), period="6mo")
        if df.empty:
            raise RuntimeError("no_data")
        ind = compute_all_indicators(df)
        sig = score_from_indicators(ind, df)
        # Normalize score to 0-100 range for consistency
        try:
            sval = float(sig.get("score", 0))
            sig["confidence"] = max(0.0, min(100.0, float(sval)))
        except Exception:
            pass
        return {"symbol": symbol.upper(), "signal": sig, "is_sample": False}
    except HTTPException:
        raise
    except Exception:
        return {
            "symbol": symbol.upper(),
            "signal": {
                "score": 65,
                "reasons": ["sample: tight BB", "sample: RSI>50"],
                "ema21": None, "ema50": None, "ema200": None,
                "rsi": 52.0, "macd": {"macd": 0.1, "signal": 0.05, "hist": 0.05},
                "bbwidth": 0.12,
                "badges": [],
            },
            "is_sample": True,
        }

@app.get("/api/v1/sentiment")
def api_sentiment(symbol: str = Query(...)) -> Dict[str, Any]:
    try:
        from sentiment.core import fetch_headlines_and_sentiment
        data = fetch_headlines_and_sentiment(symbol.upper(), limit=5)
        return {"symbol": symbol.upper(), "sentiment": data, "is_sample": data.get("is_sample", False)}
    except Exception:
        return {
            "symbol": symbol.upper(),
            "sentiment": {"label": "neutral", "score": 0.0, "confidence": 0.5, "headlines": [], "is_sample": True},
            "is_sample": True,
        }


@app.get("/scan/{symbol}")
def scan_symbol(symbol: str) -> Dict[str, Any]:
    df = load_prices(symbol)
    vcp_cfg = load_vcp_settings()
    det = VCPDetector(
        min_contractions=max(2, vcp_cfg.min_tighten_steps),
        max_base_depth=vcp_cfg.max_base_depth,
        final_contraction_max=vcp_cfg.max_final_range,
        pivot_window=vcp_cfg.pivot_window,
        breakout_volume_multiplier=vcp_cfg.breakout_volx,
    )
    sig = det.detect_vcp(df, symbol)
    d = sig.__dict__.copy()
    # Make dataclasses JSON-safe
    d["contractions"] = [c.__dict__ for c in (sig.contractions or [])]
    if d.get("signal_date") is not None:
        d["signal_date"] = str(d["signal_date"])
    return d


@app.get("/api/v1/vcp/today")
def vcp_today(label: Optional[str] = Query(None)):
    from datetime import date as _date
    day = label or _date.today().isoformat()
    try:
        # If mock mode, return sample immediately
        if LEGEND_MOCK:
            sample_rows = [
                {"symbol": p.get("ticker"), "confidence": p.get("score", 80), "pivot": None, "price": None, "notes": p.get("pattern", "VCP")}
                for p in SAMPLE_RUN.get("patterns", [])
            ]
            return {"day": day, "report": "sample", "rows": sample_rows, "is_sample": True}
        csv_path = scan_once(day)
        rows = pd.read_csv(csv_path).to_dict(orient="records")
        return {"day": day, "report": str(csv_path), "rows": rows}
    except Exception:
        # Always provide a usable sample
        sample_rows = [
            {"symbol": p.get("ticker"), "confidence": p.get("score", 80), "pivot": None, "price": None, "notes": p.get("pattern", "VCP")}
            for p in SAMPLE_RUN.get("patterns", [])
        ]
        return {"day": day, "report": "sample", "rows": sample_rows, "is_sample": True}


@app.get("/api/v1/vcp/metrics")
def vcp_metrics(start: Optional[str] = Query(None), end: Optional[str] = Query(None), run_id: Optional[int] = Query(None), db: Session = Depends(get_runs_db)):
    try:
        # If run_id is provided, load that run and use its dates
        if run_id is not None:
            RunsBase.metadata.create_all(bind=runs_engine)
            run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()
            if run is None:
                return {"status": "not_found", "message": "run not found", "run_id": run_id}
            start = run.start.isoformat()
            end = run.end.isoformat()
        if not start or not end:
            return {"status": "error", "message": "start and end are required unless run_id is provided"}
        summary = summarize_range(start, end)
        status = "ok"
        if summary.get("num_triggers", 0) == 0 and summary.get("num_candidates", 0) == 0:
            status = "no_data"
        return {**summary, "start": start, "end": end, "status": status}
    except Exception as e:
        return {"status": "error", "message": str(e), "start": start, "end": end}


@app.get("/healthz")
def healthz():
    return {"ok": True, "version": app.version}


# -------- Runs persistence APIs --------

@app.get("/api/v1/runs")
def list_runs(limit: int = Query(50, ge=1, le=500), status: Optional[str] = Query(None), provider: Optional[str] = Query(None), universe: Optional[str] = Query(None), db: Session = Depends(get_runs_db)) -> Dict[str, Any]:
    try:
        RunsBase.metadata.create_all(bind=runs_engine)
        q = db.query(BacktestRun).order_by(BacktestRun.created_at.desc())
        if status:
            q = q.filter(BacktestRun.status == status)
        if provider:
            q = q.filter(BacktestRun.provider == provider)
        if universe:
            q = q.filter(BacktestRun.universe == universe)
        rows = q.limit(limit).all()
        return {"runs": [r.to_dict() for r in rows]}
    except Exception:
        # Always-on sample when DB is unavailable
        now_iso = datetime.utcnow().isoformat() + "Z"
        sample_run = {
            "id": 0,
            "status": "complete",
            "provider": provider or "yfinance",
            "universe": universe or "simple",
            "start": (date.today().replace(day=1)).isoformat(),
            "end": date.today().isoformat(),
            "created_at": now_iso,
            "artifacts_root": str(REPORT_ROOT),
            "is_sample": True,
        }
        return {"runs": [sample_run], "is_sample": True}


@app.post("/api/v1/runs", status_code=202)
def create_run(start: str, end: str, universe: str = Query("simple"), provider: str = Query("yfinance"), detector_version: str = Query("v1"), request: Request = None) -> Dict[str, Any]:
    # lightweight rate limit on write endpoint
    try:
        from rate_limit import SimpleRateLimiter
        rl = SimpleRateLimiter()
        ip = request.client.host if request and request.client else "unknown"
        if not rl.allow(f"create_run:{ip}"):
            return {"status": "rate_limited"}
    except Exception:
        pass
    try:
        RunsBase.metadata.create_all(bind=runs_engine)
        from jobs import enqueue_backtest  # lazy import to avoid hard dependency
        return enqueue_backtest(start, end, universe, provider, detector_version)
    except Exception:
        # Return a mock submission so the UI proceeds
        return {
            "status": "submitted",
            "run_id": f"MOCK-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            "message": "Background worker unavailable; mock run created.",
            "is_sample": True,
        }


@app.get("/api/v1/runs/{run_id}")
def run_detail(run_id: int, db: Session = Depends(get_runs_db)) -> Dict[str, Any]:
    try:
        RunsBase.metadata.create_all(bind=runs_engine)
        run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()
        if not run:
            raise RuntimeError("not_found")
        # Compute artifact links index
        art = {}
        root = (run.artifacts_root or str(REPORT_ROOT)).rstrip("/")
        art["summary"] = f"{root}/summary/summary_{run.start}_{run.end}.json"
        art["daily_candidates_dir"] = f"{root}/daily_candidates"
        art["outcomes_dir"] = f"{root}/outcomes"
        # Build days index
        try:
            days = [p.stem for p in sorted((Path(root) / "daily_candidates").glob("*.csv"))]
        except Exception:
            days = []
        if not days:
            today = date.today()
            days = [(today.replace(day=max(1, today.day - i))).isoformat() for i in range(5)][::-1]
        return {"run": run.to_dict(), "artifacts": art, "days": days}
    except Exception:
        # Sample detail when DB/filesystem are unavailable
        root = str(REPORT_ROOT).rstrip("/")
        art = {
            "summary": f"{root}/summary/summary_{date.today().replace(day=1)}_{date.today()}.json",
            "daily_candidates_dir": f"{root}/daily_candidates",
            "outcomes_dir": f"{root}/outcomes",
        }
        try:
            days = [p.stem for p in sorted((Path(root) / "daily_candidates").glob("*.csv"))]
        except Exception:
            days = [date.today().isoformat()]
        sample = {
            "id": run_id,
            "status": "complete",
            "provider": "yfinance",
            "universe": "simple",
            "start": (date.today().replace(day=1)).isoformat(),
            "end": date.today().isoformat(),
            "created_at": datetime.utcnow().isoformat() + "Z",
            "artifacts_root": root,
            "is_sample": True,
        }
        return {"run": sample, "artifacts": art, "days": days, "is_sample": True}


@app.get("/api/v1/vcp/candidates")
def candidates_by_date(
    day: Optional[str] = Query(None),
    run_id: Optional[int] = Query(None),
    pattern: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    db: Session = Depends(get_runs_db),
) -> Dict[str, Any]:
    """Return candidates for an exact detection day; if day omitted, return index of available days.
    If run_id provided, use its artifacts_root; otherwise fallback to default reports root.
    """
    root = REPORT_ROOT
    if run_id is not None:
        run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()
        if run and run.artifacts_root:
            root = Path(run.artifacts_root)
    cand_dir = root / "daily_candidates"
    if not day:
        days = [p.stem for p in sorted(cand_dir.glob("*.csv"))]
        return {"days": days}
    p = cand_dir / f"{day}.csv"
    if not p.exists():
        # Provide sample rows so the demo always shows content
        sample_rows = [
            {"symbol": ptn.get("ticker"), "confidence": ptn.get("score", 80), "pivot": None, "price": None, "notes": ptn.get("pattern", "VCP")}
            for ptn in SAMPLE_RUN.get("patterns", [])
        ]
        return {"day": day, "rows": sample_rows, "is_sample": True}
    df = pd.read_csv(p)
    # enrich with sector if requested for filtering
    if sector:
        df["sector"] = df["symbol"].map(lambda s: get_sector_safe(s))
        df = df[df["sector"].fillna("") == sector]
    rows = df.to_dict(orient="records")
    # attach sector when possible
    for r in rows:
        if "sector" not in r or r["sector"] is None:
            r["sector"] = get_sector_safe(r.get("symbol"))
    # simple pattern filter (currently only VCP is implemented)
    if pattern and pattern.upper() != "VCP":
        rows = []
    return {"day": day, "rows": rows}


# ---- Analytics endpoints ----

_sector_cache_lock = threading.Lock()
_sector_cache_loaded = False
_sector_cache: Dict[str, str] = {}
_sector_cache_path = Path(__file__).resolve().parent / "data" / "universe" / "sectors.json"


def _ensure_sector_cache() -> None:
    global _sector_cache_loaded
    if _sector_cache_loaded:
        return
    with _sector_cache_lock:
        if _sector_cache_loaded:
            return
        if _sector_cache_path.exists():
            try:
                data = json.loads(_sector_cache_path.read_text())
                if isinstance(data, dict):
                    _sector_cache.update({k.upper(): str(v) for k, v in data.items() if isinstance(k, str) and isinstance(v, str)})
            except Exception:
                pass
        _sector_cache_loaded = True


def _save_sector_cache() -> None:
    try:
        _sector_cache_path.parent.mkdir(parents=True, exist_ok=True)
        _sector_cache_path.write_text(json.dumps(_sector_cache, indent=2, sort_keys=True))
    except Exception:
        pass


@lru_cache(maxsize=2048)
def get_sector_safe(symbol: Optional[str]) -> Optional[str]:
    if not symbol:
        return None
    sym = symbol.upper()
    _ensure_sector_cache()
    cached = _sector_cache.get(sym)
    if cached:
        return cached
    try:
        import yfinance as yf
        info = yf.Ticker(sym).info
        sector = info.get("sector") if isinstance(info, dict) else None
    except Exception:
        sector = None
    if sector:
        with _sector_cache_lock:
            _sector_cache[sym] = str(sector)
            _save_sector_cache()
    return sector


def _artifacts_root_for_run(run_id: int, db: Session) -> Path:
    run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()
    if run and run.artifacts_root:
        return Path(run.artifacts_root)
    return REPORT_ROOT


@app.get("/api/v1/analytics/overview")
def analytics_overview(
    run_id: int = Query(...),
    pattern: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    db: Session = Depends(get_runs_db),
) -> Dict[str, Any]:
    root = _artifacts_root_for_run(run_id, db)
    cand_dir = root / "daily_candidates"
    out_dir = root / "outcomes"
    # Load all candidates/outcomes for the run window
    cdfs: List[pd.DataFrame] = []
    odfs: List[pd.DataFrame] = []
    try:
        for p in sorted(cand_dir.glob("*.csv")):
            try:
                df = pd.read_csv(p)
                if len(df):
                    df["date"] = p.stem
                    cdfs.append(df)
            except Exception:
                logger.warning("analytics candidates load failed", extra={"file": str(p)})
        for p in sorted(out_dir.glob("*_outcomes.csv")):
            try:
                df = pd.read_csv(p)
                if len(df):
                    df["date_detected"] = p.stem.replace("_outcomes", "")
                    odfs.append(df)
            except Exception:
                logger.warning("analytics outcomes load failed", extra={"file": str(p)})
    except Exception:
        # Directory listing failed; treat as empty
        pass

    cands = pd.concat(cdfs, ignore_index=True) if cdfs else pd.DataFrame(columns=["date", "symbol", "confidence", "pivot", "price", "notes"])
    outs = pd.concat(odfs, ignore_index=True) if odfs else pd.DataFrame(columns=["date_detected", "symbol", "trigger_date", "triggered", "success", "exit_date", "max_runup_30d", "max_drawdown_30d", "r_multiple"])

    # Optional sector filter (best-effort)
    if sector and len(cands) and "symbol" in cands.columns:
        try:
            cands["sector"] = cands["symbol"].map(lambda s: get_sector_safe(s))
            cands = cands[cands["sector"].fillna("") == sector]
        except Exception:
            logger.warning("analytics sector filter failed", extra={"sector": sector})

    # Pattern distribution (currently only VCP; ignore non-VCP requests)
    if pattern and pattern.upper() != "VCP":
        cands = cands.iloc[0:0]
        outs = outs.iloc[0:0]
    total = int(len(cands))

    confidence_series = pd.to_numeric(cands["confidence"], errors="coerce") if "confidence" in cands.columns else pd.Series(dtype=float)
    avg_confidence = float(confidence_series.mean()) if not confidence_series.empty else 0.0

    success_series = pd.to_numeric(outs["success"], errors="coerce") if "success" in outs.columns else pd.Series(dtype=float)
    success = int(success_series.sum()) if not success_series.empty else 0
    triggered = int(len(outs))

    dist = [{
        "name": "VCP",
        "count": total,
        "successRate": round((success / max(triggered, 1)) * 100, 1) if triggered else 0.0,
        "avgConfidence": round(avg_confidence, 1) if avg_confidence else 0.0,
        "color": "#10B981",
    }]

    # Recent candidates (last day available)
    recent_day = cands["date"].max() if len(cands) and "date" in cands.columns else None
    recent: List[Dict[str, Any]] = []
    if recent_day:
        try:
            last_df = cands[cands["date"] == recent_day].copy()
            for _, r in last_df.iterrows():
                def _num(val: Any) -> Optional[float]:
                    try:
                        return float(val)
                    except (TypeError, ValueError):
                        return None

                recent.append({
                    "symbol": r.get("symbol"),
                    "price": _num(r.get("price")) or 0.0,
                    "pivot": _num(r.get("pivot")),
                    "confidence": _num(r.get("confidence")) or 0.0,
                    "sector": get_sector_safe(str(r.get("symbol"))),
                    "pattern": "VCP",
                    "detected": str(r.get("date")),
                })
        except Exception:
            recent = []

    # Performance timeline (daily aggregates)
    timeline: List[Dict[str, Any]] = []
    if len(cands) and "date" in cands.columns:
        try:
            by_day = cands.groupby("date").size().to_dict()
        except Exception:
            by_day = {}
        success_by_day: Dict[str, float] = {}
        if not success_series.empty and "date_detected" in outs.columns:
            try:
                success_by_day = (
                    outs.assign(success=pd.to_numeric(outs["success"], errors="coerce").fillna(0))
                    .groupby("date_detected")["success"]
                    .sum()
                    .to_dict()
                )
            except Exception:
                success_by_day = {}
        triggers_by_day: Dict[str, int] = {}
        if len(outs) and "date_detected" in outs.columns:
            try:
                triggers_by_day = outs.groupby("date_detected").size().to_dict()
            except Exception:
                triggers_by_day = {}
        avg_r_by_day: Dict[str, float] = {}
        if len(outs) and "r_multiple" in outs.columns and "date_detected" in outs.columns:
            try:
                avg_r_by_day = (
                    outs.assign(r_multiple=pd.to_numeric(outs["r_multiple"], errors="coerce"))
                    .groupby("date_detected")["r_multiple"]
                    .mean()
                    .dropna()
                    .to_dict()
                )
            except Exception:
                avg_r_by_day = {}
        for d in sorted(set(cands["date"].tolist())):
            tl = {
                "period": d,
                "totalScans": int(by_day.get(d, 0)),
                "patternsDetected": int(by_day.get(d, 0)),
                "hitRate": round((success_by_day.get(d, 0) / max(triggers_by_day.get(d, 0), 1)) * 100, 1) if triggers_by_day.get(d) else 0.0,
                "avgReturn": round(float(avg_r_by_day.get(d, 0.0)) * 100, 1) if d in avg_r_by_day else 0.0,
            }
            timeline.append(tl)

    # Data status
    data_status = "empty"
    if len(cands) or len(outs):
        data_status = "ok" if (len(cands) and len(outs)) else "partial"

    # Compute v2 KPIs while preserving existing keys for FE
    avg_r = 0.0
    if len(outs) and "r_multiple" in outs.columns:
        try:
            avg_r = float(pd.to_numeric(outs["r_multiple"], errors="coerce").dropna().mean() or 0.0)
        except Exception:
            avg_r = 0.0
    win_rate = (success / max(triggered, 1)) if triggered else 0.0
    trades = triggered

    return {
        "pattern_distribution": dist,
        "recent_candidates": recent,
        "performance_timeline": timeline[-30:],
        "kpis": {
            "active_patterns": len(recent),
            "success_rate": dist[0]["successRate"] if dist else 0.0,
            "avg_confidence": dist[0]["avgConfidence"] if dist else 0.0,
            "market_coverage": int(cands["symbol"].nunique()) if len(cands) and "symbol" in cands.columns else 0,
            # New stable fields for analytics consumers
            "win_rate": round(float(win_rate), 4),
            "avg_r": round(float(avg_r), 4),
            "trades": int(trades),
        },
        "data_status": data_status,
    }


@app.get("/api/v1/scan")
async def scan_v1(
    request: Request,
    pattern: str = Query(..., description="vcp|cup_handle|hns|flag|wedge|double"),
    universe: str = Query("sp500", description="sp500|nasdaq100"),
    limit: int = Query(100, ge=1, le=200),
    timeframe: str = Query("1d", description="1d|1wk|60m"),
    min_price: Optional[float] = Query(None, ge=0),
    min_volume: Optional[float] = Query(None, ge=0),
    max_atr_ratio: Optional[float] = Query(None, ge=0.0, le=1.0),
    sample: bool = Query(False, description="Return a sample payload instead of scanning"),
) -> Dict[str, Any]:
    client_host = request.client.host if request.client else "unknown"
    limited, retry_after = _rate_limit_check(f"scan:{client_host}", SCAN_RATE_LIMIT, SCAN_RATE_WINDOW)
    if limited:
        raise HTTPException(status_code=429, detail="Scan rate limit exceeded", headers={"Retry-After": str(retry_after)})

    canon_pattern = _canonical_pattern(pattern)
    canon_universe = _canonical_universe(universe)
    if sample:
        if SCAN_SAMPLE_ENABLE:
            return _sample_scan_payload(canon_pattern, canon_universe, limit)
        else:
            # Feature disabled; return empty payload with hint
            return {"pattern": canon_pattern, "universe": canon_universe, "count": 0, "results": [], "is_sample": False}
    # Enforce hard minimums server-side regardless of client request
    min_price_value = max(min_price if min_price is not None else MIN_PRICE_DEFAULT, MIN_PRICE_HARD)
    min_volume_value = max(min_volume if min_volume is not None else MIN_VOLUME_DEFAULT, MIN_VOLUME_HARD)
    max_atr_value = max_atr_ratio if max_atr_ratio is not None else MAX_ATR_RATIO_DEFAULT

    cache_key = None
    if SCAN_REDIS_RESPONSE_CACHE_ENABLED and not sample:
        cache_key = _response_cache_key(
            "scan-response",
            {
                "pattern": canon_pattern,
                "universe": canon_universe,
                "limit": limit,
                "timeframe": timeframe,
                "min_price": min_price_value,
                "min_volume": min_volume_value,
                "max_atr": max_atr_value,
            },
        )
        cached = _response_cache_get(cache_key)
        if cached is not None:
            return cached

    payload = await _run_pattern_scan(
        canon_pattern,
        canon_universe,
        limit,
        timeframe=timeframe,
        min_price=min_price_value,
        min_volume=min_volume_value,
        max_atr_ratio=max_atr_value,
    )

    # Alert if quality drops below threshold (fraction of results with score>=80)
    try:
        rows = payload.get("results", [])
        n = len(rows)
        if ALERT_SLACK_WEBHOOK and n >= ALERT_MIN_SAMPLES:
            good = sum(1 for r in rows if float(r.get("score", 0.0)) >= 80.0)
            frac = good / max(n, 1)
            if frac < ALERT_QUALITY_THRESHOLD:
                import requests as _rq
                msg = {
                    "text": f"Pattern quality alert: {canon_pattern.upper()} {frac:.1%} >=80 (n={n}) in {canon_universe}/{timeframe}"}
                try:
                    _rq.post(ALERT_SLACK_WEBHOOK, json=msg, timeout=5)
                except Exception:
                    pass
    except Exception:
        pass

    if cache_key:
        _response_cache_set(cache_key, payload)
    return payload


@app.get("/api/v1/scan/pattern")
async def scan_pattern(
    pattern: str = Query(..., description="VCP|CUP|HNS|FLAG|WEDGE|DOUBLE"),
    universe: str = Query("sp500", description="sp500|nasdaq100"),
    limit: int = Query(200, ge=1, le=2000),
    timeframe: str = Query("1d", description="1d|1wk|60m"),
) -> Dict[str, Any]:
    canon_pattern = _canonical_pattern(pattern)
    canon_universe = _canonical_universe(universe)
    payload = await _run_pattern_scan(
        canon_pattern,
        canon_universe,
        limit,
        timeframe=timeframe,
        min_price=MIN_PRICE_DEFAULT,
        min_volume=MIN_VOLUME_DEFAULT,
        max_atr_ratio=MAX_ATR_RATIO_DEFAULT,
    )
    rows = [
        {
            "symbol": row["symbol"],
            "confidence": row.get("score", 0.0),
            "entry": row.get("entry"),
            "stop": row.get("stop"),
            "target": (row.get("targets") or [None])[0],
            "pattern": canon_pattern.upper(),
            "chart_url": row.get("chart_url"),
            "key_levels": row.get("key_levels"),
            "avg_price": row.get("avg_price"),
            "avg_volume": row.get("avg_volume"),
            "atr14": row.get("atr14"),
        }
        for row in payload["results"]
    ]
    return {"pattern": canon_pattern.upper(), "universe": canon_universe, "rows": rows}


@app.post("/api/v1/paper_trade")
def paper_trade_endpoint(payload: PaperTradeRequest) -> Dict[str, Any]:
    try:
        entry = record_paper_trade(payload.dict(exclude_none=True))
        return {"ok": True, "trade": entry}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("paper trade record failed", extra={"error": str(exc)})
        # Always return stubbed success so FE doesn't break when optional backend is unavailable
        return {"ok": True, "trade": {"status": "stub", "error": str(exc)}}


@app.api_route("/api/v1/chart", methods=["GET", "POST"])
async def chart(
    request: Request,
    symbol: str = Query(..., min_length=1),
    pivot: Optional[str] = None,
    entry: Optional[str] = None,
    stop: Optional[str] = None,
    target: Optional[str] = None,
    pattern: Optional[str] = None,
) -> Dict[str, Any]:
    client_host = request.client.host if request.client else "unknown"
    limited, retry_after = _rate_limit_check(f"chart:{client_host}", CHART_RATE_LIMIT, CHART_RATE_WINDOW)
    if limited:
        raise HTTPException(status_code=429, detail="Chart rate limit exceeded", headers={"Retry-After": str(retry_after)})

    params = {"symbol": symbol}
    for key, value in (("pivot", pivot), ("entry", entry), ("stop", stop), ("target", target), ("pattern", pattern)):
        if value is not None and str(value).strip():
            params[key] = str(value)

    overlays: Optional[Dict[str, Any]] = None
    if request.method == "POST":
        try:
            payload = await request.json()
            if isinstance(payload, dict):
                overlays = payload.get("overlays")
        except Exception:
            overlays = None
    else:
        overlays_param = request.query_params.get("overlays")
        if overlays_param:
            try:
                overlays = json.loads(overlays_param)
            except Exception:
                overlays = None

    chart_url, meta = await _fetch_chart_url(symbol, params=params, overlays=overlays, include_meta=True)
    if overlays:
        meta["overlay_counts"] = {
            "lines": len(overlays.get("lines", []) or []),
            "boxes": len(overlays.get("boxes", []) or []),
            "labels": len(overlays.get("labels", []) or []),
            "arrows": len(overlays.get("arrows", []) or []),
            "zones": len(overlays.get("zones", []) or []),
        }
    return {"chart_url": chart_url, "meta": meta}
