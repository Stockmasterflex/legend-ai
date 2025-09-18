import os
import threading
import time
from typing import Callable, Dict, Iterable
import pandas as pd
import yfinance as yf


_LAST_FETCH_TS: float | None = None
_FETCH_LOCK = threading.Lock()


class DataProvider:
    def __init__(self, source: str | None = None):
        self.source = source or os.getenv("VCP_PROVIDER", "yfinance")
        # Allow higher concurrency by default; rely on retry/backoff when providers throttle.
        default_interval = "0.0" if os.getenv("LEGEND_ENV", "").lower() == "production" else "0.05"
        self.min_interval = float(os.getenv("DATA_PROVIDER_MIN_INTERVAL", default_interval))

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

    def _wait_for_slot(self) -> None:
        if self.min_interval <= 0:
            return
        global _LAST_FETCH_TS
        now = time.time()
        if _LAST_FETCH_TS is not None:
            delta = now - _LAST_FETCH_TS
            if delta < self.min_interval:
                time.sleep(self.min_interval - delta)
        _LAST_FETCH_TS = time.time()

    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.reset_index()
        try:
            df.columns = [str(c[0]) if isinstance(c, tuple) else str(c) for c in df.columns]
        except Exception:
            pass
        cols_lower = {c.lower(): c for c in df.columns}
        if "close" not in cols_lower and "adj close" in cols_lower:
            df["Close"] = df[cols_lower["adj close"]]
        for want in ("date", "open", "high", "low", "close", "volume"):
            if want in cols_lower and cols_lower[want] != want.capitalize():
                df.rename(columns={cols_lower[want]: want.capitalize()}, inplace=True)
        needed = {"Date", "Open", "High", "Low", "Close", "Volume"}
        missing = [c for c in needed if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns from provider: {missing}")
        return df

    def fetch(self, symbol: str, period="18mo", interval="1d") -> pd.DataFrame:
        if self.source == "yfinance":
            with _FETCH_LOCK:
                self._wait_for_slot()

                def _fetch():
                    return yf.download(symbol, period=period, interval=interval, auto_adjust=True, progress=False, threads=False)

                df = self._retry(_fetch)
            return self._normalize(df)
        # Stubs for future providers
        if self.source in {"polygon", "tiingo", "norgate"}:
            raise NotImplementedError(f"Provider '{self.source}' not implemented yet")
        raise NotImplementedError("Unsupported provider")

    def fetch_many(self, symbols: Iterable[str], period="18mo", interval="1d") -> Dict[str, pd.DataFrame]:
        symbols = [s.upper() for s in symbols if s]
        if not symbols:
            return {}
        if self.source != "yfinance":
            raise NotImplementedError("fetch_many currently only supports yfinance")

        joined = " ".join(symbols)

        def _download() -> pd.DataFrame:
            return yf.download(joined, period=period, interval=interval, auto_adjust=True, progress=False, threads=False, group_by="ticker")

        with _FETCH_LOCK:
            self._wait_for_slot()
            raw = self._retry(_download)

        out: Dict[str, pd.DataFrame] = {}
        if isinstance(raw.columns, pd.MultiIndex):
            for sym in symbols:
                if sym in raw.columns.levels[0]:
                    frame = raw[sym].dropna(how="all")
                elif (sym,) in raw.columns:
                    frame = raw[(sym,)].dropna(how="all")
                else:
                    continue
                try:
                    out[sym] = self._normalize(frame)
                except Exception:
                    continue
        else:
            # yfinance collapses to single symbol without MultiIndex
            try:
                out[symbols[0]] = self._normalize(raw.dropna(how="all"))
            except Exception:
                pass
        return out
