import pandas as pd
from pathlib import Path
from vcp.data_provider import DataProvider

DATA_ROOT = Path("backtest/data/prices")
DATA_ROOT.mkdir(parents=True, exist_ok=True)


def load_prices(symbol: str, period="18mo", interval="1d") -> pd.DataFrame:
    cache = DATA_ROOT / f"{symbol}.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    df = DataProvider().fetch(symbol, period=period, interval=interval)
    if "Date" not in df.columns:
        df = df.reset_index()
    df.to_parquet(cache, index=False)
    return df

