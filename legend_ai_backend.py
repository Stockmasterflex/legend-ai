# Legend AI Backend - FastAPI Implementation

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import List, Optional

import numpy as np
import pandas as pd
import redis
from fastapi import Depends, FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from vcp_ultimate_algorithm import VCPSignal, scan_for_vcp

# Initialize FastAPI app
app = FastAPI(title="Legend AI Backend", version="1.0.0")

# CORS middleware for frontend integration
# CORS middleware for frontend integration
allowed_origins = os.getenv("ALLOWED_ORIGINS")
if allowed_origins:
    allowed_origins = allowed_origins.split(",")
else:
    allowed_origins = ["*"]
allowed_origin_regex = os.getenv("ALLOWED_ORIGIN_REGEX")
cors_args = {
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"]
}
if allowed_origin_regex:
    cors_args["allow_origin_regex"] = allowed_origin_regex
else:
    cors_args["allow_origins"] = allowed_origins
app.add_middleware(CORSMiddleware, **cors_args)

# Database setup
DATABASE_URL = os.getenv("SERVICE_DATABASE_URL", os.getenv("DATABASE_URL", "sqlite:///./legendai.db"))
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class InMemoryCache:
    '''Simple in-memory fallback cache when Redis is unavailable.'''

    def __init__(self):
        self._store = {}

    def get(self, key: str):
        entry = self._store.get(key)
        if not entry:
            return None
        value, expires_at = entry
        if expires_at and expires_at < datetime.utcnow():
            del self._store[key]
            return None
        return value

    def setex(self, key: str, seconds: int, value):
        expiry = datetime.utcnow() + timedelta(seconds=seconds) if seconds else None
        self._store[key] = (value, expiry)

    def delete(self, key: str):
        self._store.pop(key, None)


def create_cache_client():
    redis_url = os.getenv("REDIS_URL")
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_db = int(os.getenv("REDIS_DB", "0"))

    try:
        if redis_url:
            client = redis.from_url(redis_url)
        else:
            client = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
        client.ping()
        return client
    except Exception as exc:
        print(f"Redis unavailable ({exc}); falling back to in-memory cache.")
        return InMemoryCache()


# Redis setup for caching
redis_client = create_cache_client()

# Database Models
class Stock(Base):
    __tablename__ = "stocks"

    symbol = Column(String(10), primary_key=True)
    name = Column(String(255))
    sector = Column(String(100))
    industry = Column(String(100))
    market_cap = Column(String(20))
    current_price = Column(Float)
    rs_rating = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Pattern(Base):
    __tablename__ = "patterns"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), index=True)
    pattern_type = Column(String(50))
    confidence = Column(Float)
    pivot_price = Column(Float)
    stop_loss = Column(Float)
    days_in_pattern = Column(Integer)
    pattern_data = Column(JSON)
    detected_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="active")

class Portfolio(Base):
    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10))
    pattern_type = Column(String(50))
    entry_date = Column(DateTime)
    entry_price = Column(Float)
    position_size = Column(Integer)
    stop_loss = Column(Float)
    target_price = Column(Float)
    status = Column(String(20), default="open")

# Scan tracking models
class ScanRun(Base):
    __tablename__ = "scan_runs"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    total_tickers = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    notes = Column(String(500), default="")

class ScanFailure(Base):
    __tablename__ = "scan_failures"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, index=True)
    symbol = Column(String(10), index=True)
    error_message = Column(String(500))
    occurred_at = Column(DateTime, default=datetime.utcnow)

# Auto-create tables
Base.metadata.create_all(bind=engine)

# Pydantic Models
class PatternResponse(BaseModel):
    symbol: str
    name: str
    sector: str
    pattern_type: str
    confidence: float
    pivot_price: float
    stop_loss: float
    current_price: float
    days_in_pattern: int
    rs_rating: int

class MarketEnvironment(BaseModel):
    current_trend: str
    days_in_trend: int
    distribution_days: int
    follow_through_date: str
    market_health_score: int
    breadth_indicators: dict

class PortfolioPosition(BaseModel):
    symbol: str
    pattern_type: str
    entry_price: float
    current_price: float
    position_size: int
    unrealized_pnl: float
    pnl_percent: float
    days_held: int

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pattern Detection Algorithms
class PatternDetector:

    @staticmethod
    def detect_vcp_pattern(price_data: List[dict], volume_data: List[int]) -> Optional[dict]:
        '''Detect Volatility Contraction Pattern based on Minervini criteria'''

        if len(price_data) < 50:
            return None

        # Calculate price volatility over rolling windows
        volatilities = []
        for i in range(10, len(price_data) - 10):
            window = price_data[i-10:i+10]
            highs = [d['high'] for d in window]
            lows = [d['low'] for d in window]
            volatility = (max(highs) - min(lows)) / min(lows)
            volatilities.append(volatility)

        # Look for decreasing volatility pattern
        contractions = []
        for i in range(1, len(volatilities)):
            if volatilities[i] < volatilities[i-1] * 0.8:  # 20% contraction
                contractions.append(i)

        if len(contractions) >= 3:
            confidence = min(0.95, 0.6 + len(contractions) * 0.08)
            pivot_price = price_data[-1]['close'] * 1.05

            return {
                'pattern_type': 'VCP',
                'confidence': confidence,
                'contractions': len(contractions),
                'pivot_price': pivot_price,
                'stop_loss': price_data[-1]['close'] * 0.92
            }

        return None

    @staticmethod
    def detect_cup_handle_pattern(price_data: List[dict]) -> Optional[dict]:
        '''Detect Cup & Handle pattern based on O'Neil specifications'''

        if len(price_data) < 60:  # Need at least 12 weeks of data
            return None

        closes = [d['close'] for d in price_data]

        # Find potential cup formation (U-shaped)
        mid_point = len(closes) // 2
        left_peak = max(closes[:20])
        right_peak = max(closes[-20:])
        cup_low = min(closes[10:mid_point+10])

        # Cup criteria
        cup_depth = (left_peak - cup_low) / left_peak
        peak_symmetry = abs(left_peak - right_peak) / left_peak

        if 0.15 <= cup_depth <= 0.35 and peak_symmetry <= 0.03:
            # Look for handle formation
            handle_start = len(closes) - 15
            handle_high = max(closes[handle_start:])
            handle_low = min(closes[handle_start:])
            handle_depth = (handle_high - handle_low) / handle_high

            if handle_depth <= cup_depth * 0.5:  # Handle should be shallow
                confidence = 0.6 + (1 - peak_symmetry) * 0.25

                return {
                    'pattern_type': 'Cup & Handle',
                    'confidence': min(0.95, confidence),
                    'cup_depth': cup_depth * 100,
                    'handle_depth': handle_depth * 100,
                    'pivot_price': right_peak * 1.02
                }

        return None

# API Endpoints

def _patterns_from_db(db: Session) -> List[PatternResponse]:
    patterns = db.query(Pattern).filter(Pattern.status == "active").all()
    if not patterns:
        return []
    # Fetch stocks in one go
    symbols = list({p.symbol for p in patterns})
    stocks = db.query(Stock).filter(Stock.symbol.in_(symbols)).all()
    stock_map = {s.symbol: s for s in stocks}

    results: List[PatternResponse] = []
    for p in patterns:
        s = stock_map.get(p.symbol)
        if not s:
            # Build minimal response if stock metadata missing
            results.append(PatternResponse(
                symbol=p.symbol,
                name=p.symbol,
                sector="Unknown",
                pattern_type=p.pattern_type or "VCP",
                confidence=float(p.confidence or 0.0),
                pivot_price=float(p.pivot_price or 0.0),
                stop_loss=float(p.stop_loss or 0.0),
                current_price=0.0,
                days_in_pattern=int(p.days_in_pattern or 0),
                rs_rating=0,
            ))
            continue

        results.append(PatternResponse(
            symbol=p.symbol,
            name=s.name or p.symbol,
            sector=s.sector or "Unknown",
            pattern_type=p.pattern_type or "VCP",
            confidence=float(p.confidence or 0.0),
            pivot_price=float(p.pivot_price or (s.current_price or 0.0)),
            stop_loss=float(p.stop_loss or ((s.current_price or 0.0) * 0.92)),
            current_price=float(s.current_price or 0.0),
            days_in_pattern=int(p.days_in_pattern or 0),
            rs_rating=int(s.rs_rating or 0),
        ))
    return results

@app.get("/api/patterns/all", response_model=List[PatternResponse])
async def get_all_patterns(db: Session = Depends(get_db)):
    '''Return latest cached VCP detections from the database.'''
    cached = redis_client.get("patterns:all") if redis_client else None
    if cached:
        if isinstance(cached, bytes):
            cached = cached.decode("utf-8")
        cached_list = json.loads(cached)
        return [PatternResponse(**item) for item in cached_list]

    pattern_responses = _patterns_from_db(db)
    if redis_client:
        redis_client.setex("patterns:all", 300, json.dumps([p.dict() for p in pattern_responses]))
    return pattern_responses

@app.get("/api/patterns/vcp", response_model=List[PatternResponse])
async def get_vcp_patterns(db: Session = Depends(get_db)):
    '''Return latest cached VCP detections from the database.'''
    return _patterns_from_db(db)

@app.get("/api/market/environment", response_model=MarketEnvironment)
async def get_market_environment():
    '''Get current market environment analysis'''

    # This would normally analyze market breadth, distribution days, etc.
    return MarketEnvironment(
        current_trend="Confirmed Uptrend",
        days_in_trend=23,
        distribution_days=2,
        follow_through_date="2024-08-15",
        market_health_score=78,
        breadth_indicators={
            "advance_decline_line": "Strong",
            "new_highs_vs_lows": "245 vs 23",
            "up_volume_ratio": "68%"
        }
    )

@app.get("/api/stocks/{symbol}/analysis")
async def get_stock_analysis(symbol: str, db: Session = Depends(get_db)):
    '''Get detailed analysis for a specific stock'''

    # Get stock data
    stock = db.query(Stock).filter(Stock.symbol == symbol).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    # Get pattern data
    patterns = db.query(Pattern).filter(
        Pattern.symbol == symbol,
        Pattern.status == "active"
    ).all()

    # Calculate Minervini Trend Template score (simplified)
    trend_template_score = calculate_trend_template_score(symbol)

    return {
        "stock_info": stock.__dict__,
        "patterns": [p.__dict__ for p in patterns],
        "trend_template_score": trend_template_score,
        "technical_indicators": get_technical_indicators(symbol)
    }

@app.get("/api/portfolio/positions", response_model=List[PortfolioPosition])
async def get_portfolio_positions(db: Session = Depends(get_db)):
    '''Get all active portfolio positions'''

    positions = db.query(Portfolio).filter(Portfolio.status == "open").all()

    position_responses = []
    for pos in positions:
        # Get current price
        stock = db.query(Stock).filter(Stock.symbol == pos.symbol).first()
        current_price = stock.current_price if stock else pos.entry_price

        # Calculate P&L
        unrealized_pnl = (current_price - pos.entry_price) * pos.position_size
        pnl_percent = (current_price - pos.entry_price) / pos.entry_price * 100
        days_held = (datetime.now() - pos.entry_date).days

        response = PortfolioPosition(
            symbol=pos.symbol,
            pattern_type=pos.pattern_type,
            entry_price=pos.entry_price,
            current_price=current_price,
            position_size=pos.position_size,
            unrealized_pnl=unrealized_pnl,
            pnl_percent=pnl_percent,
            days_held=days_held
        )
        position_responses.append(response)

    return position_responses

@app.websocket("/ws/market-data")
async def market_data_websocket(websocket: WebSocket):
    '''WebSocket endpoint for real-time market data'''
    await websocket.accept()

    try:
        while True:
            # Simulate real-time price updates
            market_update = {
                "timestamp": datetime.now().isoformat(),
                "updates": generate_price_updates()
            }

            await websocket.send_json(market_update)
            await asyncio.sleep(1)  # Update every second

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()

# Helper Functions
def calculate_trend_template_score(symbol: str) -> int:
    '''Calculate Minervini Trend Template 8-point checklist score'''
    score = 0

    # This is a simplified version - would need real price data
    # 1. Current price above 21-day MA
    # 2. 21-day MA above 50-day MA  
    # 3. 50-day MA above 150-day MA
    # 4. 150-day MA above 200-day MA
    # 5. 200-day MA trending up for 1 month
    # 6. Current price at least 30% above 52-week low
    # 7. Current price within 25% of 52-week high
    # 8. RS Rating above 70

    # Simulate scoring
    import random
    score = random.randint(5, 8)

    return score

def get_technical_indicators(symbol: str) -> dict:
    '''Get technical indicators for a stock'''
    return {
        "sma_21": 145.30,
        "sma_50": 142.80,
        "sma_150": 138.90,
        "sma_200": 135.20,
        "volume_avg_50": 2500000,
        "rsi": 58.5,
        "macd": 0.85
    }

def generate_price_updates() -> List[dict]:
    '''Generate simulated real-time price updates'''
    symbols = ["AAPL", "NVDA", "TSLA", "MSFT", "GOOGL"]
    updates = []

    for symbol in symbols:
        # Simulate price movement
        price_change = np.random.normal(0, 0.5)  # Mean=0, StdDev=0.5%

        updates.append({
            "symbol": symbol,
            "price_change": price_change,
            "volume_surge": np.random.choice([True, False], p=[0.1, 0.9])
        })

    return updates

def fetch_price_data_for_vcp(symbol: str) -> Optional[pd.DataFrame]:
    '''Convert stored price history into the DataFrame format expected by the VCP detector.'''
    price_records = get_stock_price_data(symbol)
    if not price_records:
        return None

    df = pd.DataFrame(price_records)
    if df.empty:
        return None

    column_map = {
        'date': 'Date',
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'volume': 'Volume'
    }
    df = df.rename(columns=column_map)

    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
    else:
        df.index = pd.to_datetime(df.index)

    required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    if not all(col in df.columns for col in required_columns):
        return None

    return df[required_columns].sort_index()

def convert_vcp_signal_to_pattern_response(signal: VCPSignal, stock: Stock) -> PatternResponse:
    '''Translate a VCPSignal into the PatternResponse schema expected by the frontend.'''
    confidence = (signal.confidence_score or 0.0) / 100.0

    pivot_price = signal.pivot_price
    if not pivot_price and stock.current_price:
        pivot_price = stock.current_price * 1.05

    stop_loss = None
    days_in_pattern = 0

    if signal.contractions:
        last_contraction = signal.contractions[-1]
        stop_loss = last_contraction.low_price

        first_date = signal.contractions[0].start_date
        last_date = last_contraction.end_date or signal.signal_date
        if first_date is not None and last_date is not None:
            days_in_pattern = max(0, (last_date - first_date).days)
        else:
            days_in_pattern = sum(max(c.duration_days or 0, 0) for c in signal.contractions)

    if stop_loss is None and stock.current_price:
        stop_loss = stock.current_price * 0.92

    current_price = stock.current_price if stock.current_price is not None else (pivot_price or 0.0)

    return PatternResponse(
        symbol=signal.symbol,
        name=stock.name or signal.symbol,
        sector=stock.sector or "Unknown",
        pattern_type="VCP",
        confidence=confidence,
        pivot_price=float(round(pivot_price, 2)) if pivot_price else float(round(current_price * 1.05, 2)),
        stop_loss=float(round(stop_loss, 2)) if stop_loss else float(round(current_price * 0.92, 2)),
        current_price=float(round(current_price, 2)),
        days_in_pattern=int(days_in_pattern),
        rs_rating=stock.rs_rating or 0
    )

def detect_vcp_patterns_from_stocks(stocks: List[Stock]) -> List[PatternResponse]:
    '''Run the full VCP detector against a prepared stock universe.'''
    if not stocks:
        return []

    symbol_to_stock = {stock.symbol: stock for stock in stocks if stock.symbol}
    symbols = list(symbol_to_stock.keys())
    if not symbols:
        return []

    signals = scan_for_vcp(
        symbols,
        data_fetcher=fetch_price_data_for_vcp,
        min_price=10.0,
        min_volume=500_000,
        min_contractions=2,
        max_contractions=6,
        max_base_depth=0.35,
        final_contraction_max=0.10
    )

    pattern_responses: List[PatternResponse] = []
    for signal in signals:
        stock = symbol_to_stock.get(signal.symbol)
        if not stock:
            continue
        pattern_responses.append(convert_vcp_signal_to_pattern_response(signal, stock))

    return pattern_responses

# New scan endpoints

@app.get("/api/scans/latest")
async def get_latest_scan(db: Session = Depends(get_db)):
    run = db.query(ScanRun).order_by(ScanRun.started_at.desc()).first()
    if not run:
        return {
            "last_scan_started_at": None,
            "last_scan_finished_at": None,
            "total_tickers": 0,
            "success_count": 0,
            "failed_count": 0,
        }
    return {
        "last_scan_started_at": run.started_at.isoformat() if run.started_at else None,
        "last_scan_finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "total_tickers": run.total_tickers or 0,
        "success_count": run.success_count or 0,
        "failed_count": run.failed_count or 0,
    }

@app.get("/api/scans/results", response_model=List[PatternResponse])
async def get_scan_results(db: Session = Depends(get_db)):
    patterns = _patterns_from_db(db)
    # Sort by confidence desc
    return sorted(patterns, key=lambda p: p.confidence, reverse=True)

@app.get("/api/scans/stats")
async def get_scan_stats(db: Session = Depends(get_db)):
    patterns = _patterns_from_db(db)
    total = len(patterns)
    by_sector = {}
    for p in patterns:
        by_sector[p.sector] = by_sector.get(p.sector, 0) + 1
    return {"total": total, "by_sector": by_sector}

# Background Tasks
async def pattern_detection_task():
    '''Background task to continuously detect new patterns'''
    while True:
        try:
            db = SessionLocal()

            stocks = db.query(Stock).all()
            vcp_patterns = detect_vcp_patterns_from_stocks(stocks)

            db.query(Pattern).filter(Pattern.pattern_type == "VCP").delete()
            for pattern in vcp_patterns:
                db.add(
                    Pattern(
                        symbol=pattern.symbol,
                        pattern_type="VCP",
                        confidence=pattern.confidence,
                        pivot_price=pattern.pivot_price,
                        stop_loss=pattern.stop_loss,
                        days_in_pattern=pattern.days_in_pattern,
                        pattern_data=pattern.dict()
                    )
                )

            db.commit()

            # Clear cache so next request pulls fresh detections
            if redis_client:
                redis_client.delete("patterns:all")

        except Exception as e:
            print(f"Pattern detection error: {e}")
        finally:
            db.close()

        # Run every 5 minutes
        await asyncio.sleep(300)

def get_stock_price_data(symbol: str) -> List[dict]:
    '''Fetch stock price data from seeded files if available, else generate mock data.'''
    # Try reading seeded data
    try:
        import json as _json
        import os
        file_path = os.path.join('data', 'price_history', f'{symbol}.json')
        if os.path.exists(file_path):
            with open(file_path) as f:
                loaded = _json.load(f)
                if isinstance(loaded, list) and loaded:
                    return loaded
    except Exception as e:
        print(f"Failed reading seeded price data for {symbol}: {e}")

    # Fallback to mock generation
    dates = pd.date_range(end=datetime.now(), periods=252, freq='D')

    data = []
    base_price = np.random.uniform(50, 200)

    for i, date in enumerate(dates):
        price_change = np.random.normal(0, 0.02)
        base_price *= (1 + price_change)

        high = base_price * (1 + abs(np.random.normal(0, 0.01)))
        low = base_price * (1 - abs(np.random.normal(0, 0.01)))

        data.append({
            'date': date.strftime('%Y-%m-%d'),
            'open': base_price,
            'high': high,
            'low': low,
            'close': base_price,
            'volume': np.random.randint(500000, 5000000)
        })

    return data

def get_stock_volume_data(symbol: str) -> List[int]:
    '''Fetch stock volume data (mock implementation)'''
    return [np.random.randint(500000, 5000000) for _ in range(252)]

if __name__ == "__main__":
    import uvicorn

    # Start background tasks
    asyncio.create_task(pattern_detection_task())

    # Run the application
    uvicorn.run(app, host="0.0.0.0", port=8000)
