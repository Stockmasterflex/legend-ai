import pandas as pd
from pathlib import Path
from vcp.data_provider import DataProvider
from datetime import date as _date

DATA_ROOT = Path("backtest/data/prices")
DATA_ROOT.mkdir(parents=True, exist_ok=True)


def load_prices(symbol: str, period: str = "18mo", interval: str = "1d", refresh: bool = False) -> pd.DataFrame:
    """Load prices with simple parquet caching.
    If refresh is True, or cache is stale (last Date < today), refetch and overwrite.
    """
    cache = DATA_ROOT / f"{symbol}.parquet"
    if cache.exists() and not refresh:
        try:
            df_cached = pd.read_parquet(cache)
            # If cache is for prior day, refetch to get latest bar
            if "Date" in df_cached.columns:
                last = pd.to_datetime(df_cached["Date"].iloc[-1]).date()
                if last >= _date.today():
                    return df_cached
        except Exception:
            pass
    df = DataProvider().fetch(symbol, period=period, interval=interval)
    if "Date" not in df.columns:
        df = df.reset_index()
    df.to_parquet(cache, index=False)
    return df

