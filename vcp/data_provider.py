import os
import time
from typing import Callable
import pandas as pd
import yfinance as yf


_LAST_FETCH_TS: float | None = None


class DataProvider:
    def __init__(self, source: str | None = None):
        self.source = source or os.getenv("VCP_PROVIDER", "yfinance")
        self.min_interval = float(os.getenv("DATA_PROVIDER_MIN_INTERVAL", "0.2"))

    def _retry(self, fn: Callable[[], pd.DataFrame], tries: int = 3, backoff: float = 0.75) -> pd.DataFrame:
        last: Exception | None = None
        for i in range(tries):
            try:
                return fn()
            except Exception as e:
                last = e
                if i < tries - 1:
                    time.sleep(backoff * (2 ** i))
        raise last  # type: ignore[misc]

    def fetch(self, symbol: str, period="18mo", interval="1d") -> pd.DataFrame:
        global _LAST_FETCH_TS
        if self.min_interval > 0:
            now = time.time()
            if _LAST_FETCH_TS is not None:
                delta = now - _LAST_FETCH_TS
                if delta < self.min_interval:
                    time.sleep(self.min_interval - delta)
            _LAST_FETCH_TS = time.time()
        if self.source == "yfinance":
            def _fetch():
                return yf.download(symbol, period=period, interval=interval, auto_adjust=True, progress=False)
            df = self._retry(_fetch)
            df = df.reset_index()
            # Flatten potential multiindex columns
            try:
                df.columns = [str(c[0]) if isinstance(c, tuple) else str(c) for c in df.columns]
            except Exception:
                pass
            # Normalize column names
            cols_lower = {c.lower(): c for c in df.columns}
            if "close" not in cols_lower and "adj close" in cols_lower:
                df["Close"] = df[cols_lower["adj close"]]
            for want in ("date","open","high","low","close","volume"):
                if want in cols_lower and cols_lower[want] != want.capitalize():
                    df.rename(columns={cols_lower[want]: want.capitalize()}, inplace=True)
            # Ensure required columns exist
            needed = {"Date","Open","High","Low","Close","Volume"}
            missing = [c for c in needed if c not in df.columns]
            if missing:
                raise ValueError(f"Missing columns from provider: {missing}")
            return df
        # Stubs for future providers
        if self.source in {"polygon", "tiingo", "norgate"}:
            raise NotImplementedError(f"Provider '{self.source}' not implemented yet")
        raise NotImplementedError("Unsupported provider")
