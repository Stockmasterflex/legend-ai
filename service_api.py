from fastapi import FastAPI, Depends, Query, Request
from typing import Dict, Any, Optional
from pathlib import Path
import pandas as pd
from vcp.vcp_detector import VCPDetector
from settings import load_vcp_settings, is_mock_enabled
from backtest.run_backtest import scan_once
from backtest.ingestion import load_prices
from backtest.simulate import summarize_range, REPORT_ROOT
from service_db import Base as RunsBase, engine as runs_engine, get_db as get_runs_db, BacktestRun
from sqlalchemy.orm import Session
import os
import time
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.cors import CORSMiddleware
from uuid import uuid4
from pythonjsonlogger import jsonlogger
import logging
import requests
from functools import lru_cache
from fastapi import APIRouter
from datetime import datetime, date
from typing import List

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

SHOTS_BASE_URL = os.getenv("SHOTS_BASE_URL", "http://127.0.0.1:3010")

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
    try:
        from indicators.ta import compute_all_indicators
        from signals.core import score_from_indicators
        df = yf_history_cached(symbol.upper(), period="6mo")
        if df.empty:
            raise RuntimeError("no_data")
        ind = compute_all_indicators(df)
        sig = score_from_indicators(ind, df)
        return {"symbol": symbol.upper(), "signal": sig, "is_sample": False}
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
    RunsBase.metadata.create_all(bind=runs_engine)
    try:
        from jobs import enqueue_backtest  # lazy import to avoid hard dependency
        return enqueue_backtest(start, end, universe, provider, detector_version)
    except Exception:
        return {"status": "disabled", "message": "Background worker unavailable on this instance."}


@app.get("/api/v1/runs/{run_id}")
def run_detail(run_id: int, db: Session = Depends(get_runs_db)) -> Dict[str, Any]:
    RunsBase.metadata.create_all(bind=runs_engine)
    run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()
    if not run:
        return {"status": "not_found", "run_id": run_id}
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
    return {"run": run.to_dict(), "artifacts": art, "days": days}


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

@lru_cache(maxsize=2048)
def get_sector_safe(symbol: Optional[str]) -> Optional[str]:
    if not symbol:
        return None
    try:
        import yfinance as yf
        info = yf.Ticker(symbol).info
        return info.get("sector")
    except Exception:
        return None


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
    cdfs = []
    odfs = []
    for p in sorted(cand_dir.glob("*.csv")):
        df = pd.read_csv(p)
        if len(df):
            df["date"] = p.stem
            cdfs.append(df)
    for p in sorted(out_dir.glob("*_outcomes.csv")):
        df = pd.read_csv(p)
        if len(df):
            df["date_detected"] = p.stem.replace("_outcomes", "")
            odfs.append(df)
    cands = pd.concat(cdfs, ignore_index=True) if cdfs else pd.DataFrame(columns=["date","symbol","confidence","pivot","price","notes"]) 
    outs = pd.concat(odfs, ignore_index=True) if odfs else pd.DataFrame(columns=["date_detected","symbol","trigger_date","triggered","success","exit_date","max_runup_30d","max_drawdown_30d","r_multiple"]) 

    # Optional sector filter (best-effort)
    if sector and len(cands):
        cands["sector"] = cands["symbol"].map(lambda s: get_sector_safe(s))
        cands = cands[cands["sector"].fillna("") == sector]

    # Pattern distribution (currently only VCP; ignore non-VCP requests)
    if pattern and pattern.upper() != "VCP":
        cands = cands.iloc[0:0]
        outs = outs.iloc[0:0]
    total = int(len(cands))
    success = int(outs["success"].sum()) if len(outs) else 0
    triggered = int(len(outs))
    dist = [{
        "name": "VCP",
        "count": total,
        "successRate": round((success / max(triggered,1)) * 100, 1) if triggered else 0.0,
        "avgConfidence": round(float(cands["confidence"].mean()), 1) if len(cands) else 0.0,
        "color": "#10B981",
    }]

    # Recent candidates (last day available)
    recent_day = cands["date"].max() if len(cands) else None
    recent = []
    if recent_day:
        last_df = cands[cands["date"] == recent_day].copy()
        for _, r in last_df.iterrows():
            recent.append({
                "symbol": r["symbol"],
                "price": float(r.get("price", 0)),
                "pivot": float(r.get("pivot", 0)) if pd.notnull(r.get("pivot")) else None,
                "confidence": float(r.get("confidence", 0)),
                "sector": get_sector_safe(str(r.get("symbol"))),
                "pattern": "VCP",
                "detected": str(r.get("date")),
            })

    # Performance timeline (daily aggregates)
    timeline = []
    if len(cands):
        by_day = cands.groupby("date").size().to_dict()
        success_by_day = outs.groupby("date_detected")["success"].sum().to_dict() if len(outs) and "success" in outs.columns else {}
        triggers_by_day = outs.groupby("date_detected").size().to_dict() if len(outs) else {}
        if len(outs) and "r_multiple" in outs.columns:
            avg_r_by_day = outs.groupby("date_detected")["r_multiple"].mean().to_dict()
        else:
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

    return {
        "pattern_distribution": dist,
        "recent_candidates": recent,
        "performance_timeline": timeline[-30:],
        "kpis": {
            "active_patterns": len(recent),
            "success_rate": dist[0]["successRate"] if dist else 0.0,
            "avg_confidence": dist[0]["avgConfidence"] if dist else 0.0,
            "market_coverage": int(cands["symbol"].nunique()) if len(cands) else 0,
        }
    }


@app.get("/api/v1/chart")
def chart_proxy(symbol: str = Query("SPY"), pivot: Optional[float] = Query(None)) -> Dict[str, Any]:
    base = os.getenv("SHOTS_BASE_URL", "http://127.0.0.1:3010")
    try:
        params: Dict[str, Any] = {"symbol": symbol}
        if pivot is not None:
            params["pivot"] = pivot
        r = requests.get(f"{base}/screenshot", params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e), "symbol": symbol}
