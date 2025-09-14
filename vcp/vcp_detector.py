import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Contraction:
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    high_price: float
    low_price: float
    percent_drop: float
    avg_volume: float
    duration_days: int


@dataclass
class VCPSignal:
    symbol: str
    detected: bool
    pivot_price: Optional[float] = None
    contractions: Optional[List[Contraction]] = None
    confidence_score: float = 0.0
    trend_strength: float = 0.0
    volume_dry_up: bool = False
    final_contraction_tightness: Optional[float] = None
    breakout_detected: bool = False
    signal_date: Optional[pd.Timestamp] = None
    notes: List[str] = None


class VCPDetector:
    def __init__(self, min_price=10.0, min_volume=500_000,
                 min_contractions=2, max_contractions=6,
                 max_base_depth=0.40, final_contraction_max=0.10,
                 pivot_window=5, breakout_volume_multiplier=1.5):
        self.min_price = min_price
        self.min_volume = min_volume
        self.min_contractions = min_contractions
        self.max_contractions = max_contractions
        self.max_base_depth = max_base_depth
        self.final_contraction_max = final_contraction_max
        self.pivot_window = pivot_window
        self.breakout_volume_multiplier = breakout_volume_multiplier

    def detect_vcp(self, df: pd.DataFrame, symbol: str = "UNKNOWN") -> VCPSignal:
        signal = VCPSignal(symbol=symbol, detected=False, notes=[])
        if df is None or len(df) < 200:
            signal.notes = (signal.notes or []) + ["Insufficient data"]
            return signal

        # Flatten multiindex columns if present
        try:
            df.columns = [str(c[0]) if isinstance(c, tuple) else str(c) for c in df.columns]
        except Exception:
            pass
        if "Date" not in df.columns:
            df = df.reset_index()
        # Standardize columns robustly
        cols_lower = {c.lower(): c for c in df.columns}
        # If only adj close exists, use it as Close
        if "close" not in cols_lower and "adj close" in cols_lower:
            df["Close"] = df[cols_lower["adj close"]]
        # Ensure title-case keys exist
        for want in ("open", "high", "low", "close", "volume"):
            if want in cols_lower and cols_lower[want] != want.capitalize():
                df.rename(columns={cols_lower[want]: want.capitalize()}, inplace=True)
        # If still missing required columns, bail
        for req in ("Open","High","Low","Close","Volume"):
            if req not in df.columns:
                signal.notes = (signal.notes or []) + [f"Missing column: {req}"]
                return signal

        current_price = float(df["Close"].iloc[-1])
        avg_volume_50d = float(df["Volume"].iloc[-50:].mean())
        if current_price < self.min_price or avg_volume_50d < self.min_volume:
            signal.notes = (signal.notes or []) + ["Failed liquidity filters"]
            return signal

        df["MA50"] = df["Close"].rolling(50).mean()
        df["MA150"] = df["Close"].rolling(150).mean()
        df["MA200"] = df["Close"].rolling(200).mean()
        if not (current_price > df["MA50"].iloc[-1] > df["MA150"].iloc[-1] > df["MA200"].iloc[-1]):
            signal.notes = (signal.notes or []) + ["Failed trend template"]
            return signal
        signal.trend_strength = 1.0

        highs, lows = self._find_swings(df, window=5)
        contractions: List[Contraction] = []
        for hi, lo in zip(highs, lows):
            if lo <= hi:
                continue
            h, l = float(df.iloc[hi]["High"]), float(df.iloc[lo]["Low"])
            pct = (h - l) / max(h, 1e-9)
            if 0.02 < pct < self.max_base_depth:
                contractions.append(
                    Contraction(
                        start_date=pd.to_datetime(df.iloc[hi]["Date"]),
                        end_date=pd.to_datetime(df.iloc[lo]["Date"]),
                        high_price=h, low_price=l, percent_drop=pct,
                        avg_volume=float(df["Volume"].iloc[hi:lo+1].mean()),
                        duration_days=int(lo - hi)
                    )
                )

        if len(contractions) < self.min_contractions:
            signal.notes = (signal.notes or []) + ["Not enough contractions"]
            return signal

        signal.contractions = contractions
        signal.final_contraction_tightness = contractions[-1].percent_drop

        pivot = float(df["High"].iloc[-self.pivot_window:].max())
        signal.pivot_price = pivot
        if current_price > pivot:
            signal.breakout_detected = True

        # naive confidence placeholder
        tight_bonus = max(0.0, 0.12 - signal.final_contraction_tightness) * 200
        signal.confidence_score = float(min(95, 65 + tight_bonus))
        signal.detected = True
        signal.signal_date = pd.to_datetime(df["Date"].iloc[-1])
        signal.notes = (signal.notes or []) + [f"Detected with {len(contractions)} contractions"]
        return signal

    def _find_swings(self, df: pd.DataFrame, window=5):
        highs, lows = [], []
        for i in range(window, len(df) - window):
            win = df.iloc[i-window:i+window+1]
            hi_val = float(df["High"].iloc[i])
            lo_val = float(df["Low"].iloc[i])
            if hi_val == float(win["High"].max()):
                highs.append(i)
            if lo_val == float(win["Low"].min()):
                lows.append(i)
        # align in time (alternating hi→lo sequences)
        highs = [h for h in highs if any(l > h for l in lows)]
        lows_sorted = sorted([l for l in lows if any(h < l for h in highs)])
        highs_sorted = sorted([h for h in highs if any(l > h for l in lows_sorted)])
        return highs_sorted, lows_sorted
