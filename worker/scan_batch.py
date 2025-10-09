"""
Runs batch scans over a symbol universe and upserts results into Timescale.
Idempotent by (ticker, pattern, as_of).
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd
import yfinance as yf

# Add parent directory to path so we can import the detector
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlalchemy as sa

from vcp_ultimate_algorithm import VCPDetector
from worker.utils import load_universe, upsert_patterns

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


PG_URL = os.getenv("DATABASE_URL")
if not PG_URL:
    raise SystemExit("DATABASE_URL required")

engine = sa.create_engine(PG_URL, future=True, pool_pre_ping=True)


def fetch_price_data(ticker: str, period: str = "1y") -> pd.DataFrame:
    """Fetch historical price data from yfinance."""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df.empty:
            return None
        # Reset index to make Date a column, keep uppercase for VCP detector
        df = df.reset_index()
        return df
    except Exception as e:
        logging.error(f"Error fetching {ticker}: {e}")
        return None


def run_one(ticker: str) -> List[Dict]:
    """Run VCP detection on a single ticker and return pattern records."""
    try:
        df = fetch_price_data(ticker)
        if df is None or len(df) < 50:
            return []

        detector = VCPDetector(
            min_price=10.0, min_volume=500000, min_contractions=2, check_trend_template=True
        )

        signal = detector.detect_vcp(df, ticker)

        if not signal.detected:
            return []

        # Convert signal to database record
        record = {
            "ticker": ticker,
            "pattern": "VCP",
            "as_of": datetime.now(),
            "confidence": float(signal.confidence_score),
            "rs": None,  # TODO: calculate RS if available
            "price": float(signal.pivot_price) if signal.pivot_price else None,
            "meta": {
                "contractions": len(signal.contractions),
                "base_depth": (
                    float(signal.base_depth_percent) if signal.base_depth_percent else None
                ),
                "notes": signal.notes or [],
            },
        }

        logging.info(f"✓ {ticker}: VCP detected (confidence={signal.confidence_score:.1f}%)")
        return [record]

    except Exception as e:
        logging.error(f"Error processing {ticker}: {e}")
        return []


def main() -> None:
    """Main scan batch function."""
    tickers = load_universe()
    logging.info(f"Starting scan for {len(tickers)} tickers...")

    total_patterns = 0
    for ticker in tickers:
        rows = run_one(ticker)
        if rows:
            upsert_patterns(engine, rows)
            total_patterns += len(rows)

    logging.info(f"Scan complete. Found {total_patterns} patterns.")


if __name__ == "__main__":
    main()
