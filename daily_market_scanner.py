import os
import time
import math
import json
import traceback
from datetime import datetime, timedelta
from typing import List, Dict

import requests
import pandas as pd
from dotenv import load_dotenv
import yfinance as yf

from legend_ai_backend import SessionLocal, Stock, Pattern, ScanRun, ScanFailure, Base
from vcp_ultimate_algorithm import scan_for_vcp, VCPSignal


load_dotenv()


FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
PROVIDER = (os.getenv("VCP_PROVIDER") or "yfinance").lower()
DATA_DIR = os.path.join("data", "price_history")


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)


def unix_ts(dt: datetime) -> int:
    return int(dt.timestamp())


def get_tickers() -> List[str]:
    """Fetch S&P 500 and Nasdaq-100 tickers with multiple fallbacks."""
    tickers: List[str] = []

    # Primary: Wikipedia S&P 500
    try:
        sp500_tables = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
        sp500 = sp500_tables[0]
        if 'Symbol' in sp500.columns:
            sp_symbols = sp500['Symbol'].astype(str).str.replace('.', '-', regex=False).tolist()
            tickers.extend(sp_symbols)
    except Exception as e:
        print(f"SP500 fetch failed (Wikipedia): {e}")

    # Primary: Wikipedia Nasdaq-100
    try:
        ndx_tables = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100")
        ndx = None
        for t in ndx_tables:
            cols = [str(c).lower() for c in t.columns]
            if any('ticker' in c for c in cols) or any('symbol' in c for c in cols):
                ndx = t
                break
        if ndx is not None:
            col = 'Ticker' if 'Ticker' in ndx.columns else ('Symbol' if 'Symbol' in ndx.columns else ndx.columns[0])
            ndx_symbols = ndx[col].astype(str).str.replace('.', '-', regex=False).tolist()
            tickers.extend(ndx_symbols)
    except Exception as e:
        print(f"NDX fetch failed (Wikipedia): {e}")

    # Fallback: DataHub S&P 500 constituents
    if not tickers:
        try:
            sp_alt = pd.read_csv("https://datahub.io/core/s-and-p-500-companies/r/constituents.csv")
            tickers.extend(sp_alt['Symbol'].astype(str).str.replace('.', '-', regex=False).tolist())
        except Exception as e:
            print(f"SP500 fetch failed (DataHub): {e}")

    # Final fallback: curated major tickers
    if not tickers:
        tickers = [
            'AAPL','MSFT','NVDA','AMZN','GOOGL','META','AVGO','TSLA','AMD','NFLX',
            'SMCI','COST','PEP','ADBE','CSCO','CRM','LIN','TXN','QCOM','INTC',
            'JPM','WMT','PG','XOM','UNH','V','MA','HD','MRK','ABBV'
        ]

    uniq = sorted({t.strip().upper() for t in tickers if t and t.strip()})
    return uniq


def _fetch_candles_finnhub(symbol: str, start: datetime, end: datetime) -> List[Dict]:
    params = {
        'symbol': symbol,
        'resolution': 'D',
        'from': unix_ts(start),
        'to': unix_ts(end),
        'token': FINNHUB_API_KEY,
    }
    r = requests.get('https://finnhub.io/api/v1/stock/candle', params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    if data.get('s') != 'ok':
        raise RuntimeError(f"Finnhub returned status {data.get('s')} for {symbol}")
    result: List[Dict] = []
    for i in range(len(data['t'])):
        result.append({
            'date': datetime.utcfromtimestamp(int(data['t'][i])).strftime('%Y-%m-%d'),
            'open': float(data['o'][i]),
            'high': float(data['h'][i]),
            'low': float(data['l'][i]),
            'close': float(data['c'][i]),
            'volume': int(data['v'][i] or 0),
        })
    return result


def _fetch_candles_yf(symbol: str, start: datetime, end: datetime) -> List[Dict]:
    # Use Ticker.history to avoid some known ambiguities in yf.download
    t = yf.Ticker(symbol)
    # yfinance end is exclusive; add 1 day to include end date
    df = t.history(start=start.date(), end=(end + timedelta(days=1)).date(), interval='1d', auto_adjust=False, actions=False)
    if df is None or df.empty:
        raise RuntimeError(f"yfinance returned no data for {symbol}")
    df = df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
    # Ensure required columns exist
    for col in ['open','high','low','close','volume']:
        if col not in df.columns:
            raise RuntimeError(f"yfinance missing column {col} for {symbol}")
    out: List[Dict] = []
    for ts, row in df.iterrows():
        vol_val = row['volume']
        try:
            vol_val = 0 if pd.isna(vol_val) else int(vol_val)
        except Exception:
            vol_val = 0
        out.append({
            'date': ts.strftime('%Y-%m-%d'),
            'open': float(row['open']) if not pd.isna(row['open']) else 0.0,
            'high': float(row['high']) if not pd.isna(row['high']) else 0.0,
            'low': float(row['low']) if not pd.isna(row['low']) else 0.0,
            'close': float(row['close']) if not pd.isna(row['close']) else 0.0,
            'volume': vol_val,
        })
    return out


def fetch_candles(symbol: str, start: datetime, end: datetime) -> List[Dict]:
    if PROVIDER == 'finnhub':
        try:
            return _fetch_candles_finnhub(symbol, start, end)
        except Exception as e:
            print(f"Finnhub failed for {symbol} ({e}); falling back to yfinance")
            return _fetch_candles_yf(symbol, start, end)
    # default yfinance
    return _fetch_candles_yf(symbol, start, end)


def save_history(symbol: str, candles: List[Dict]):
    ensure_dirs()
    path = os.path.join(DATA_DIR, f"{symbol}.json")
    with open(path, 'w') as f:
        json.dump(candles, f)


def data_fetcher(symbol: str) -> pd.DataFrame | None:
    path = os.path.join(DATA_DIR, f"{symbol}.json")
    if not os.path.exists(path):
        return None
    with open(path, 'r') as f:
        rows = json.load(f)
    if not rows:
        return None
    df = pd.DataFrame(rows)
    df = df.rename(columns={
        'date': 'Date', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'
    })
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.set_index('Date')
    return df[['Open', 'High', 'Low', 'Close', 'Volume']].sort_index()


def upsert_stock(session, symbol: str, last_close: float):
    symbol = symbol.upper()
    stock = session.query(Stock).filter(Stock.symbol == symbol).first()
    now = datetime.utcnow()
    if not stock:
        stock = Stock(symbol=symbol, name=symbol, sector='Unknown', industry='Unknown', current_price=last_close,
                      market_cap='', rs_rating=0, created_at=now, updated_at=now)
        session.add(stock)
    else:
        stock.current_price = last_close
        stock.updated_at = now


def run_scan():
    if PROVIDER == 'finnhub' and not FINNHUB_API_KEY:
        raise RuntimeError("FINNHUB_API_KEY not set in environment")

    session = SessionLocal()
    run = ScanRun(started_at=datetime.utcnow(), total_tickers=0, success_count=0, failed_count=0, notes="daily scan")
    session.add(run)
    session.commit()
    session.refresh(run)

    try:
        tickers = get_tickers()
        run.total_tickers = len(tickers)
        session.commit()

        start = datetime.utcnow() - timedelta(days=180)
        end = datetime.utcnow()

        requests_this_minute = 0
        minute_window_start = time.time()

        failures = 0
        successes = 0

        for idx, symbol in enumerate(tickers, start=1):
            try:
                # Rate limiting: keep under 60/min
                now_ts = time.time()
                if now_ts - minute_window_start >= 60:
                    minute_window_start = now_ts
                    requests_this_minute = 0
                if requests_this_minute >= 58:
                    sleep_for = 60 - (now_ts - minute_window_start)
                    if sleep_for > 0:
                        time.sleep(sleep_for)
                    minute_window_start = time.time()
                    requests_this_minute = 0

                candles = fetch_candles(symbol, start, end)
                requests_this_minute += 1

                if not candles:
                    raise RuntimeError("No candles returned")
                save_history(symbol, candles)
                upsert_stock(session, symbol, candles[-1]['close'])
                successes += 1
            except Exception as exc:
                failures += 1
                session.add(ScanFailure(run_id=run.id, symbol=symbol, error_message=str(exc)))
            finally:
                # Gentle spacing between requests
                time.sleep(0.6)

        # Run VCP detection using stored histories with production-quality filters
        symbols = [s.symbol for s in session.query(Stock.symbol).all()]
        signals: List[VCPSignal] = scan_for_vcp(
            symbols, data_fetcher=data_fetcher,
            min_contractions=2,
            max_contractions=6,
            max_base_depth=0.35,
            final_contraction_max=0.10,
            min_price=30.0,
            min_volume=1_000_000,
            check_trend_template=True,
        )

        # Clear and write patterns
        session.query(Pattern).filter(Pattern.pattern_type == "VCP").delete()
        for sig in signals:
            stock = session.query(Stock).filter(Stock.symbol == sig.symbol).first()
            if not stock:
                continue
            confidence = (sig.confidence_score or 0.0) / 100.0
            pivot = sig.pivot_price or (stock.current_price or 0.0) * 1.05
            stop = None
            days = 0
            if sig.contractions:
                last_c = sig.contractions[-1]
                stop = last_c.low_price
                first_date = sig.contractions[0].start_date
                last_date = last_c.end_date or sig.signal_date
                if first_date and last_date:
                    days = max(0, (last_date - first_date).days)
            if stop is None and stock.current_price:
                stop = stock.current_price * 0.92
            session.add(Pattern(
                symbol=sig.symbol,
                pattern_type="VCP",
                confidence=confidence,
                pivot_price=float(pivot),
                stop_loss=float(stop or 0.0),
                days_in_pattern=int(days),
                pattern_data={
                    "symbol": sig.symbol,
                    "confidence_score": sig.confidence_score,
                    "pivot_price": sig.pivot_price,
                },
                detected_at=datetime.utcnow(),
                status="active",
            ))

        run.success_count = successes
        run.failed_count = failures
        run.finished_at = datetime.utcnow()
        session.commit()
        print(f"Scan completed: {successes} succeeded, {failures} failed, patterns: {len(signals)}")
    except Exception as exc:
        run.finished_at = datetime.utcnow()
        run.notes = f"failed: {exc}"
        session.commit()
        traceback.print_exc()
        raise
    finally:
        session.close()


def test_finnhub_connection(sample: List[str] | None = None):
    sample = sample or ['AAPL', 'MSFT', 'NVDA']
    start = datetime.utcnow() - timedelta(days=30)
    end = datetime.utcnow()
    ok = 0
    for sym in sample:
        try:
            candles = fetch_candles(sym, start, end)
            print(f"Test {sym}: {len(candles)} candles")
            ok += 1
        except Exception as e:
            print(f"Test {sym} failed: {e}")
    print(f"Data provider test: {ok}/{len(sample)} succeeded (provider={PROVIDER})")


def run_scan_for_symbols(symbols: List[str]):
    session = SessionLocal()
    run = ScanRun(started_at=datetime.utcnow(), total_tickers=len(symbols), success_count=0, failed_count=0, notes="manual subset scan")
    session.add(run)
    session.commit()
    session.refresh(run)
    try:
        start = datetime.utcnow() - timedelta(days=180)
        end = datetime.utcnow()
        successes = 0
        failures = 0
        for symbol in symbols:
            try:
                candles = fetch_candles(symbol, start, end)
                save_history(symbol, candles)
                upsert_stock(session, symbol, candles[-1]['close'])
                successes += 1
                time.sleep(0.6)
            except Exception as e:
                failures += 1
                session.add(ScanFailure(run_id=run.id, symbol=symbol, error_message=str(e)))
        sigs: List[VCPSignal] = scan_for_vcp(
            symbols,
            data_fetcher=data_fetcher,
            min_contractions=2,
            max_contractions=6,
            max_base_depth=0.35,
            final_contraction_max=0.10,
            min_price=30.0,
            min_volume=1_000_000,
            check_trend_template=True,
        )
        session.query(Pattern).filter(Pattern.pattern_type == "VCP").delete()
        for sig in sigs:
            stock = session.query(Stock).filter(Stock.symbol == sig.symbol).first()
            if not stock:
                continue
            confidence = (sig.confidence_score or 0.0) / 100.0
            pivot = sig.pivot_price or (stock.current_price or 0.0) * 1.05
            stop = (sig.contractions[-1].low_price if sig.contractions else (stock.current_price or 0.0) * 0.92)
            session.add(Pattern(symbol=sig.symbol, pattern_type="VCP", confidence=confidence, pivot_price=float(pivot),
                                stop_loss=float(stop or 0.0), days_in_pattern=0, pattern_data={"symbol": sig.symbol},
                                detected_at=datetime.utcnow(), status="active"))
        run.success_count = successes
        run.failed_count = failures
        run.finished_at = datetime.utcnow()
        session.commit()
        print(f"Subset scan completed: {successes} succeeded, {failures} failed, patterns: {len(sigs)}")
    finally:
        session.close()


if __name__ == "__main__":
    run_scan()

