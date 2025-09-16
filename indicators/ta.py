import logging
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np

log = logging.getLogger("legend.indicators")

def sma(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(n, min_periods=max(1, n // 2)).mean()

def ema(series: pd.Series, n: int) -> pd.Series:
    return series.ewm(span=n, adjust=False, min_periods=max(1, n // 2)).mean()

def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.rolling(n, min_periods=n).mean()
    avg_loss = loss.rolling(n, min_periods=n).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(50.0)

def macd(close: pd.Series, fast: int = 12, slow: int = 26, sig: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal = macd_line.ewm(span=sig, adjust=False).mean()
    hist = macd_line - signal
    return macd_line, signal, hist

def bollinger(close: pd.Series, n: int = 20, k: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    mid = sma(close, n)
    std = close.rolling(n, min_periods=max(1, n // 2)).std()
    upper = mid + k * std
    lower = mid - k * std
    width = (upper - lower) / mid.replace(0, np.nan)
    return mid, upper, lower, width

def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    close = df["Close"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()

def stoch(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
    low_min = df["Low"].rolling(window=k_period, min_periods=k_period).min()
    high_max = df["High"].rolling(window=k_period, min_periods=k_period).max()
    k = (df["Close"] - low_min) / (high_max - low_min).replace(0, np.nan) * 100
    d = k.rolling(window=d_period, min_periods=d_period).mean()
    return k.fillna(50.0), d.fillna(50.0)

def support_resistance_swings(df: pd.DataFrame, window: int = 5) -> Dict[str, Any]:
    highs, lows = [], []
    for i in range(window, len(df) - window):
        w = df.iloc[i-window:i+window+1]
        if df["High"].iloc[i] == w["High"].max():
            highs.append(float(df["High"].iloc[i]))
        if df["Low"].iloc[i] == w["Low"].min():
            lows.append(float(df["Low"].iloc[i]))
    return {
        "resistance": max(highs[-5:], default=None),
        "support": min(lows[-5:], default=None),
    }

def compute_all_indicators(df: pd.DataFrame) -> Dict[str, Any]:
    d = df.copy()
    if "Date" not in d.columns:
        d = d.reset_index()
    for col in ("Open","High","Low","Close","Volume"):
        if col not in d.columns:
            raise ValueError("missing columns")
    close = d["Close"].astype(float)
    volume = d["Volume"].astype(float)
    ema21 = ema(close, 21).iloc[-1] if len(close) else None
    ema50 = ema(close, 50).iloc[-1] if len(close) else None
    ema200 = ema(close, 200).iloc[-1] if len(close) else None
    rsi14 = rsi(close, 14).iloc[-1] if len(close) else 50.0
    m, s, h = macd(close)
    macd_last = {"macd": float(m.iloc[-1]) if len(m) else 0.0, "signal": float(s.iloc[-1]) if len(s) else 0.0, "hist": float(h.iloc[-1]) if len(h) else 0.0}
    bb_mid, bb_up, bb_lo, bb_w = bollinger(close, 20, 2.0)
    bb = {
        "mid": float(bb_mid.iloc[-1]) if len(bb_mid) else None,
        "upper": float(bb_up.iloc[-1]) if len(bb_up) else None,
        "lower": float(bb_lo.iloc[-1]) if len(bb_lo) else None,
        "width": float(bb_w.iloc[-1]) if len(bb_w) else None,
    }
    atr14 = float(atr(d, 14).iloc[-1]) if len(d) else None
    k, dd = stoch(d, 14, 3)
    st = {"k": float(k.iloc[-1]) if len(k) else 50.0, "d": float(dd.iloc[-1]) if len(dd) else 50.0}
    vol_sma50 = float(sma(volume, 50).iloc[-1]) if len(volume) else None
    sr = support_resistance_swings(d, 5)
    return {
        "ema21": ema21, "ema50": ema50, "ema200": ema200,
        "rsi14": float(rsi14) if rsi14 is not None else None,
        "macd": macd_last,
        "bb": bb, "bb_width": bb["width"],
        "atr14": atr14, "stoch": st, "vol_sma50": vol_sma50,
        "support": sr.get("support"), "resistance": sr.get("resistance"),
    }

