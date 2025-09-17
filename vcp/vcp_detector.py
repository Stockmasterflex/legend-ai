import pandas as pd
from dataclasses import dataclass, field
from typing import List, Optional
import logging

log = logging.getLogger("legend.vcp")


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
    contractions: List[Contraction] = field(default_factory=list)
    confidence_score: float = 0.0
    trend_strength: float = 0.0
    volume_dry_up: bool = False
    final_contraction_tightness: Optional[float] = None
    breakout_detected: bool = False
    signal_date: Optional[pd.Timestamp] = None
    notes: List[str] = field(default_factory=list)


class VCPDetector:
    def __init__(self,
                 min_price: float = 10.0,
                 min_volume: int = 500_000,
                 min_contractions: int = 2,
                 max_contractions: int = 6,
                 max_base_depth: float = 0.35,          # loosened from 0.40→0.35 gives more realistic passes
                 final_contraction_max: float = 0.12,    # loosened from 0.10
                 pivot_window: int = 7,
                 breakout_volume_multiplier: float = 1.8,
                 vol_dryup_ratio: float = 0.70,          # was 0.60 (easier to satisfy dry-up)
                 tightening_factor: float = 0.95,        # was strict 0.90 (easier tightening check)
                 min_bars_required: int = 150            # was 200 (lets us run on shorter histories)
                 ):
        self.min_price = float(min_price)
        self.min_volume = int(min_volume)
        self.min_contractions = int(min_contractions)
        self.max_contractions = int(max_contractions)
        self.max_base_depth = float(max_base_depth)
        self.final_contraction_max = float(final_contraction_max)
        self.pivot_window = int(pivot_window)
        self.breakout_volume_multiplier = float(breakout_volume_multiplier)
        self.vol_dryup_ratio = float(vol_dryup_ratio)
        self.tightening_factor = float(tightening_factor)
        self.min_bars_required = int(min_bars_required)

    def detect_vcp(self, df: pd.DataFrame, symbol: str = "UNKNOWN") -> VCPSignal:
        signal = VCPSignal(symbol=symbol, detected=False)
        if df is None or len(df) < self.min_bars_required:
            signal.notes.append(f"Insufficient data: {len(df) if df is not None else 0} &lt; {self.min_bars_required}")
            log.debug("VCP %s rejected: insufficient data len=%s &lt; %s", symbol, len(df) if df is not None else None, self.min_bars_required)
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
            signal.notes.append(f"Failed liquidity filters (price={current_price:.2f}, avg50v={avg_volume_50d:.0f})")
            log.debug("VCP %s rejected: liquidity price=%.2f avg50v=%.0f", symbol, current_price, avg_volume_50d)
            return signal

        df["MA50"] = df["Close"].rolling(50).mean()
        df["MA150"] = df["Close"].rolling(150).mean()
        df["MA200"] = df["Close"].rolling(200).mean()
        # Trend template: stacked MAs and positive slope on MA50
        ma_stack = current_price > df["MA50"].iloc[-1] > df["MA150"].iloc[-1] > df["MA200"].iloc[-1]
        ma50_slope = float(df["MA50"].iloc[-1] - df["MA50"].iloc[-20]) if pd.notnull(df["MA50"].iloc[-20]) else 0.0
        if not (ma_stack and ma50_slope > 0):
            signal.notes.append(f"Failed trend template (stack={ma_stack}, ma50_slope={ma50_slope:.4f})")
            log.debug("VCP %s rejected: trend stack=%s ma50_slope=%.4f", symbol, ma_stack, ma50_slope)
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

        min_needed = max(2, self.min_contractions)  # allow 2 for demo/looser validation
        if len(contractions) < min_needed:
            signal.notes.append(f"Not enough contractions (have={len(contractions)}, need&gt;={min_needed})")
            log.debug("VCP %s rejected: contractions have=%d need>=%d", symbol, len(contractions), min_needed)
            return signal

        # Validate VCP: decreasing contraction depth, tight final area, volume dry-up
        depths = [c.percent_drop for c in contractions]
        decreasing = all(depths[i+1] <= depths[i] * self.tightening_factor for i in range(len(depths)-1))
        if not decreasing:
            signal.notes.append(f"Contractions not tightening (factor={self.tightening_factor:.2f}, depths={ [round(d,4) for d in depths] })")
            log.debug("VCP %s rejected: not tightening factor=%.2f depths=%s", symbol, self.tightening_factor, depths)
            return signal

        signal.contractions = contractions
        signal.final_contraction_tightness = contractions[-1].percent_drop
        if signal.final_contraction_tightness is None or signal.final_contraction_tightness > self.final_contraction_max:
            signal.notes.append(f"Final contraction too wide ({signal.final_contraction_tightness:.2f} &gt; {self.final_contraction_max:.2f})")
            log.debug("VCP %s rejected: final width=%.4f &gt; %.4f", symbol, signal.final_contraction_tightness or -1, self.final_contraction_max)
            return signal

        # Volume dry-up: last 10d < vol_dryup_ratio * 50d
        vol10 = float(df["Volume"].iloc[-10:].mean())
        vol50 = avg_volume_50d
        vol_dry_up = vol10 < self.vol_dryup_ratio * max(vol50, 1e-9)
        signal.volume_dry_up = bool(vol_dry_up)
        if not vol_dry_up:
            signal.notes.append(f"No volume dry-up (vol10={vol10:.0f}, vol50={vol50:.0f}, ratio={self.vol_dryup_ratio:.2f})")
            log.debug("VCP %s rejected: vol dry-up false vol10=%.0f vol50=%.0f ratio=%.2f", symbol, vol10, vol50, self.vol_dryup_ratio)
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

        log.debug("VCP %s detected: contractions=%d final=%.4f dryup=%s score=%.1f",
                  symbol, len(contractions), signal.final_contraction_tightness or -1, vol_dry_up, signal.confidence_score)

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
