import os
from datetime import date as _date, timedelta
from pathlib import Path
from typing import Iterable, List

import pandas as pd

from vcp.data_provider import DataProvider

DATA_ROOT = Path("backtest/data/prices")
DATA_ROOT.mkdir(parents=True, exist_ok=True)


def _cache_path(symbol: str, interval: str) -> Path:
    safe_interval = interval.replace("/", "-")
    return DATA_ROOT / f"{symbol}_{safe_interval}.parquet"


MAX_STALE_DAYS = int(os.getenv("DATA_MAX_STALE_DAYS", "2"))


def _is_cache_fresh(symbol: str, interval: str, *, min_rows: int | None = None) -> bool:
    cache = _cache_path(symbol, interval)
    if not cache.exists():
        return False
    try:
        df_cached = pd.read_parquet(cache, columns=["Date"])
        if "Date" not in df_cached.columns or not len(df_cached):
            return False
        if min_rows and len(df_cached) < min_rows:
            return False
        last = pd.to_datetime(df_cached["Date"].iloc[-1]).date()
        if last >= _date.today():
            return True
        if MAX_STALE_DAYS > 0:
            cutoff = _date.today() - timedelta(days=MAX_STALE_DAYS)
            return last >= cutoff
    except Exception:
        return False
    return False


def _write_cache(symbol: str, interval: str, df: pd.DataFrame) -> None:
    cache = _cache_path(symbol, interval)
    cache.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache, index=False)


def prefetch_prices(symbols: Iterable[str], *, period: str, interval: str, min_rows: int | None = None) -> None:
    """Fetch price history for any symbols missing fresh cache in bulk batches."""
    symbols = [s.upper() for s in symbols if s]
    if not symbols:
        return
    to_refresh = [sym for sym in symbols if not _is_cache_fresh(sym, interval, min_rows=min_rows)]
    if not to_refresh:
        return
    provider = DataProvider()
    default_batch = 12
    batch_size = max(1, int(os.getenv("DATA_PREFETCH_BATCH", str(default_batch)) or default_batch))

    def fetch_chunk(chunk: List[str]) -> None:
        if not chunk:
            return
        if len(chunk) == 1:
            sym = chunk[0]
            try:
                df_single = provider.fetch(sym, period=period, interval=interval)
                if "Date" not in df_single.columns:
                    df_single = df_single.reset_index()
                _write_cache(sym, interval, df_single)
            except Exception:
                pass
            return
        try:
            data = provider.fetch_many(chunk, period=period, interval=interval)
        except Exception:
            mid = len(chunk) // 2
            fetch_chunk(chunk[:mid])
            fetch_chunk(chunk[mid:])
            return
        for sym in chunk:
            df = data.get(sym)
            if df is None or df.empty:
                fetch_chunk([sym])
            else:
                _write_cache(sym, interval, df)

    for i in range(0, len(to_refresh), batch_size):
        fetch_chunk(to_refresh[i : i + batch_size])


def load_prices(
    symbol: str,
    period: str = "18mo",
    interval: str = "1d",
    *,
    refresh: bool = False,
    min_rows: int | None = None,
) -> pd.DataFrame:
    """Load prices with simple parquet caching.
    If refresh is True, or cache is stale (last Date < today), refetch and overwrite.
    """
    cache = _cache_path(symbol, interval)
    if cache.exists() and not refresh:
        try:
            df_cached = pd.read_parquet(cache)
            if "Date" in df_cached.columns:
                if min_rows and len(df_cached) < min_rows:
                    raise RuntimeError("cache-too-short")
                last = pd.to_datetime(df_cached["Date"].iloc[-1]).date()
                if last >= _date.today():
                    return df_cached
                if MAX_STALE_DAYS > 0:
                    cutoff = _date.today() - timedelta(days=MAX_STALE_DAYS)
                    if last >= cutoff:
                        return df_cached
        except Exception:
            pass
    df = DataProvider().fetch(symbol, period=period, interval=interval)
    if "Date" not in df.columns:
        df = df.reset_index()
    df.to_parquet(cache, index=False)
    return df


__all__ = ["load_prices"]
