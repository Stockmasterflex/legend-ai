import pandas as pd
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
                 pivot_window=7, breakout_volume_multiplier=1.8):
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
        # Trend template: stacked MAs and positive slope on MA50
        ma_stack = current_price > df["MA50"].iloc[-1] > df["MA150"].iloc[-1] > df["MA200"].iloc[-1]
        ma50_slope = float(df["MA50"].iloc[-1] - df["MA50"].iloc[-20]) if pd.notnull(df["MA50"].iloc[-20]) else 0.0
        if not (ma_stack and ma50_slope > 0):
            signal.notes = (signal.notes or []) + ["Failed trend template"]
            return signal
        signal.trend_strength = 1.0

        highs, lows = self._find_swings(df, window=5)
        contractions: List[Contraction] = []
        # Build contraction legs between swing highs and subsequent swing lows
        for hi, lo in zip(highs, lows):
            if lo <= hi:
                continue
            high_price, low_price = float(df.iloc[hi]["High"]), float(df.iloc[lo]["Low"])
            pct = (high_price - low_price) / max(high_price, 1e-9)
            if 0.02 < pct < self.max_base_depth:
                contractions.append(
                    Contraction(
                        start_date=pd.to_datetime(df.iloc[hi]["Date"]),
                        end_date=pd.to_datetime(df.iloc[lo]["Date"]),
                        high_price=high_price, low_price=low_price, percent_drop=pct,
                        avg_volume=float(df["Volume"].iloc[hi:lo+1].mean()),
                        duration_days=int(lo - hi)
                    )
                )

        if len(contractions) < max(3, self.min_contractions):
            signal.notes = (signal.notes or []) + ["Not enough contractions"]
            return signal

        # Validate VCP: decreasing contraction depth, tight final area, volume dry-up
        depths = [c.percent_drop for c in contractions]
        decreasing = all(depths[i+1] <= depths[i] * 0.9 for i in range(len(depths)-1))
        if not decreasing:
            signal.notes = (signal.notes or []) + ["Contractions not tightening"]
            return signal

        signal.contractions = contractions
        signal.final_contraction_tightness = contractions[-1].percent_drop
        if signal.final_contraction_tightness is None or signal.final_contraction_tightness > self.final_contraction_max:
            signal.notes = (signal.notes or []) + ["Final contraction too wide"]
            return signal

        # Volume dry-up: last 10d < 60% of 50d
        vol10 = float(df["Volume"].iloc[-10:].mean())
        vol50 = avg_volume_50d
        vol_dry_up = vol10 < 0.6 * max(vol50, 1e-9)
        signal.volume_dry_up = bool(vol_dry_up)
        if not vol_dry_up:
            signal.notes = (signal.notes or []) + ["No volume dry-up"]
            return signal

        pivot = float(df["High"].iloc[-self.pivot_window:].max())
        signal.pivot_price = pivot
        # Breakout confirmation (optional)
        if current_price > pivot and float(df["Volume"].iloc[-1]) > self.breakout_volume_multiplier * avg_volume_50d:
            signal.breakout_detected = True

        # Confidence: composite of tightness, number of contractions, trend, volume dry-up
        tight_bonus = max(0.0, 0.12 - float(signal.final_contraction_tightness)) * 200
        count_bonus = min(len(contractions), 5) * 4
        trend_bonus = min(max(ma50_slope, 0.0) * 50, 10)
        vol_bonus = 10 if vol_dry_up else 0
        breakout_bonus = 10 if signal.breakout_detected else 0
        base_score = 55 + tight_bonus + count_bonus + trend_bonus + vol_bonus + breakout_bonus
        signal.confidence_score = float(max(0, min(95, base_score)))
        signal.detected = True
        signal.signal_date = pd.to_datetime(df["Date"].iloc[-1])
        signal.notes = (signal.notes or []) + [
            f"Detected with {len(contractions)} contractions",
            f"final={signal.final_contraction_tightness:.2f}",
            "vol_dry_up" if vol_dry_up else "vol_normal",
        ]
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
        highs = [hi for hi in highs if any(lo > hi for lo in lows)]
        lows_sorted = sorted([lo for lo in lows if any(hi < lo for hi in highs)])
        highs_sorted = sorted([hi for hi in highs if any(lo > hi for lo in lows_sorted)])
        return highs_sorted, lows_sorted
