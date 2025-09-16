import os
import logging
from pathlib import Path
from typing import Optional

import requests
from fastapi import FastAPI, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, date
from typing import List
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("legend.vcp").setLevel(logging.DEBUG)

from .db.database import get_db, engine, Base
from .db.models import Price

app = FastAPI(title="Legend Room API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Defaults: localhost for dev; compose will override with http://shots:3010
SHOTS_BASE_URL = os.getenv("SHOTS_BASE_URL", "http://127.0.0.1:3010")
DEFAULT_SYMBOL = os.getenv("DEFAULT_SYMBOL", "SPY")
LOCAL_PNG = Path(
    os.getenv(
        "LOCAL_PNG",
        str(Path.home() / "Projects/LegendAI/legend-room-screenshot-engine/reports/SMOKE.png"),
    )
)

class ScreenshotRequest(BaseModel):
    symbol: Optional[str] = None

# ---- existing minimal routes kept for compatibility ----
@app.get("/")
def root():
    return {"ok": True, "service": "legend-room-backend"}

@app.get("/analyze")
def analyze(symbol: Optional[str] = Query(None)):
    sym = symbol or DEFAULT_SYMBOL
    return {"symbol": sym, "note": "legacy analyze endpoint"}

# ---- thin wrappers used by smoke/integration ----
def call_shots(symbol: str) -> dict:
    try:
        r = requests.get(f"{SHOTS_BASE_URL}/screenshot", params={"symbol": symbol}, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/health")
def api_health():
    return {"ok": True}

@app.get("/api/screenshot")
def api_screenshot_get(symbol: Optional[str] = Query(None)):
    sym = symbol or DEFAULT_SYMBOL
    data = call_shots(sym)
    return {
        "symbol": sym,
        "engine": data,
        "local_png": str(LOCAL_PNG.resolve()) if LOCAL_PNG.exists() else None,
        "local_png_exists": LOCAL_PNG.exists(),
    }

@app.post("/api/screenshot")
def api_screenshot_post(body: ScreenshotRequest):
    sym = (body.symbol or DEFAULT_SYMBOL) if body else DEFAULT_SYMBOL
    data = call_shots(sym)
    return {
        "symbol": sym,
        "engine": data,
        "local_png": str(LOCAL_PNG.resolve()) if LOCAL_PNG.exists() else None,
        "local_png_exists": LOCAL_PNG.exists(),
    }

# ---- Phase 2: Thin price adapter ----
def ensure_tables():
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass


def fetch_prices_yf(symbol: str, limit: int) -> List[dict]:
    """Fetch recent prices using yfinance. Keep import local to avoid heavy deps at import time.
    Returns list of dicts with keys: date, open, high, low, close, volume, symbol
    """
    import yfinance as yf  # local import

    ticker = yf.Ticker(symbol)
    df = ticker.history(period="6mo")  # ample range
    if df is None or df.empty:
        return []
    rows = []
    for idx, row in df.tail(limit).iterrows():
        d = idx.date() if isinstance(idx, (datetime, date)) else date.fromisoformat(str(idx)[:10])
        rows.append({
            "date": d,
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": int(row.get("Volume", 0)),
            "symbol": symbol.upper(),
        })
    return rows


@app.get("/api/price")
def api_price(symbol: Optional[str] = Query("SPY"), limit: int = Query(100, ge=1, le=1000), db: Session = Depends(get_db)):
    ensure_tables()
    sym = (symbol or "SPY").upper()
    # fetch and persist (naive upsert)
    data = fetch_prices_yf(sym, limit=limit)
    for item in data:
        existing = db.query(Price).filter(Price.symbol == sym, Price.date == item["date"]).first()
        if existing:
            continue
        db.add(Price(symbol=sym, date=item["date"], open=item["open"], high=item["high"], low=item["low"], close=item["close"], volume=item["volume"]))
    db.commit()

    # return last N rows
    rows = (
        db.query(Price)
        .filter(Price.symbol == sym)
        .order_by(Price.date.desc())
        .limit(limit)
        .all()
    )
    out = [
        {
            "symbol": r.symbol,
            "date": r.date.isoformat(),
            "open": r.open,
            "high": r.high,
            "low": r.low,
            "close": r.close,
            "volume": r.volume,
        }
        for r in rows
    ]
    return out
