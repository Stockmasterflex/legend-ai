from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, List, Literal, Optional, Tuple

import numpy as np
import pandas as pd

from vcp.vcp_detector import VCPDetector


def _compute_atr(df: pd.DataFrame, period: int = 14) -> Optional[float]:
    if len(df) < period + 1:
        return None
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    close = df["Close"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(period).mean().iloc[-1]
    if pd.isna(atr):
        return None
    return float(atr)

PatternName = Literal["vcp", "cup_handle", "hns", "flag", "wedge", "double"]
PatternResult = Dict[str, Any]

_VCP_DETECTOR = VCPDetector()


def _prepare_df(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    if df is None or len(df) == 0:
        return None
    out = df.copy()
    if not isinstance(out, pd.DataFrame):
        out = pd.DataFrame(out)
    if "Date" not in out.columns:
        out = out.reset_index()
    if "index" in out.columns and "Date" not in out.columns:
        out = out.rename(columns={"index": "Date"})
    rename: Dict[str, str] = {}
    for col in list(out.columns):
        lower = str(col).lower()
        if lower in {"open", "high", "low", "close", "volume"} and col != lower.capitalize():
            rename[col] = lower.capitalize()
    if rename:
        out = out.rename(columns=rename)
    if "Adj Close" in out.columns and "Close" not in out.columns:
        out["Close"] = out["Adj Close"]
    required = {"Open", "High", "Low", "Close"}
    if not required.issubset(out.columns):
        return None
    if "Volume" not in out.columns:
        out["Volume"] = 0.0
    out = out.dropna(subset=["Close"]).copy()
    out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
    out = out.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    return out


def _round(value: Optional[float], ndigits: int = 4) -> Optional[float]:
    if value is None:
        return None
    try:
        if not math.isfinite(value):
            return None
    except TypeError:
        return None
    return round(float(value), ndigits)


def _to_iso(value: Any) -> str:
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, datetime):
        return value.date().isoformat()
    return str(value)


def _price_levels(entry: Optional[float], stop: Optional[float], targets: Iterable[float]) -> Dict[str, Any]:
    return {
        "entry": _round(entry, 4) if entry is not None else None,
        "stop": _round(stop, 4) if stop is not None else None,
        "targets": [_round(t, 4) for t in targets if t is not None],
    }


def _base_overlay(entry: Optional[float], stop: Optional[float], targets: Iterable[float]) -> Dict[str, Any]:
    return {
        "lines": [],
        "boxes": [],
        "labels": [],
        "priceLevels": _price_levels(entry, stop, targets),
    }


def _result(
    pattern: str,
    score: float,
    entry: Optional[float],
    stop: Optional[float],
    targets: Iterable[float],
    overlays: Dict[str, Any],
    extra: Optional[Dict[str, Any]] = None,
    evidence: Optional[List[str]] = None,
) -> Optional[PatternResult]:
    entry_val = _round(entry, 4) if entry is not None else None
    stop_val = _round(stop, 4) if stop is not None else None
    targets_list: List[float] = []
    for t in targets:
        tv = _round(t, 4) if t is not None else None
        if tv is not None and tv > 0:
            targets_list.append(tv)
    if entry_val is None or stop_val is None or entry_val <= 0 or stop_val <= 0 or not targets_list:
        return None
    out: PatternResult = {
        "pattern": pattern,
        "score": float(round(max(0.0, min(100.0, score)), 2)),
        "entry": entry_val,
        "stop": stop_val,
        "targets": targets_list,
        "overlays": overlays,
        "key_levels": {
            "entry": entry_val,
            "stop": stop_val,
            "targets": targets_list,
        },
    }
    if evidence:
        out["evidence"] = evidence
    if extra:
        out.update(extra)
    return out


def _risk_targets(entry: float, stop: float, multipliers: Tuple[float, ...] = (2.0, 3.0)) -> List[float]:
    risk = entry - stop
    if risk <= 0:
        return []
    return [entry + risk * m for m in multipliers]


def detect_vcp(df: pd.DataFrame, symbol: str = "", timeframe: str = "1d") -> Optional[PatternResult]:
    data = _prepare_df(df)
    if data is None or len(data) < 150:
        return None
    atr = _compute_atr(data)
    avg_volume_50d = float(data["Volume"].tail(50).mean()) if "Volume" in data.columns else 0.0
    signal = _VCP_DETECTOR.detect_vcp(data, symbol or "VCP")
    if not getattr(signal, "detected", False) or not signal.pivot_price:
        return None
    entry = float(signal.pivot_price)
    lows: List[float] = []
    if signal.contractions:
        lows.extend([float(c.low_price) for c in signal.contractions if c.low_price])
    if not lows:
        lows.extend(data["Low"].tail(15).astype(float).tolist())
    handle_low = float(signal.contractions[-1].low_price) if signal.contractions else None
    stop_candidates = [val for val in ([handle_low] + lows) if val is not None]
    stop = min(stop_candidates) if stop_candidates else None
    if stop is None or entry <= stop:
        stop = float(data["Low"].tail(15).min())
    max_risk_stop = entry * 0.92
    stop = max(stop, max_risk_stop)
    stop = min(stop, entry * 0.99)
    if entry <= 0 or stop <= 0 or entry <= stop:
        return None
    stop = round(stop, 2)
    entry = round(entry, 2)

    cup_high = max(float(c.high_price) for c in signal.contractions) if signal.contractions else float(data["High"].tail(60).max())
    cup_low = min(float(c.low_price) for c in signal.contractions) if signal.contractions else float(data["Low"].tail(60).min())
    cup_depth_pct = (cup_high - cup_low) / max(cup_high, 1e-6)
    cup_depth_value = max(entry - cup_low, 0.0)

    risk = max(entry - stop, 0.01)
    target_cup = round(entry + cup_depth_value * 0.618, 2)
    resistance_candidates = [float(h) for h in data["High"].tail(180).astype(float) if h > entry]
    resistance_target = round(min(resistance_candidates) if resistance_candidates else entry * 1.08, 2)
    conservative_target = round(entry + risk * 1.5, 2)
    targets = sorted({t for t in [target_cup, resistance_target, conservative_target] if t > entry})
    overlays = _base_overlay(entry, stop, targets)
    for contraction in signal.contractions:
        overlays["lines"].append(
            {
                "x1": _to_iso(contraction.start_date),
                "y1": _round(contraction.high_price, 4),
                "x2": _to_iso(contraction.end_date),
                "y2": _round(contraction.low_price, 4),
                "color": "#9be7ff",
                "dash": True,
                "width": 1,
            }
        )
    overlays["labels"].append(
        {
            "text": "Pivot",
            "x": _to_iso(data["Date"].iloc[-1]),
            "y": _round(entry, 4),
        }
    )
    overlays["labels"].append(
        {
            "text": "Stop",
            "x": _to_iso(data["Date"].iloc[-1]),
            "y": _round(stop, 4),
        }
    )
    tight = signal.final_contraction_tightness or 0.12
    base = 68.0
    base += min(18.0, max(0.0, (len(signal.contractions) - 2) * 5.0))
    base += max(0.0, (0.12 - tight) / 0.12 * 12.0)
    if signal.volume_dry_up:
        base += 6.0
    slope = float(data["Close"].iloc[-1] / data["Close"].iloc[-50] - 1.0) if len(data) > 50 else 0.0
    base += max(0.0, min(6.0, slope * 40.0))
    if atr:
        risk_ratio = atr / max(entry, 1e-6)
        base -= max(0.0, min(8.0, risk_ratio * 120.0))
    score = max(0.0, min(99.0, base))
    evidence = []
    if signal.contractions:
        evidence.append(f"{len(signal.contractions)} tightening contractions")
    if signal.volume_dry_up:
        evidence.append("volume dry-up confirmed")
    evidence.append(f"MA slope last 50d: {slope:.2%}")
    evidence.append(f"Cup depth: {cup_depth_pct:.2%}")
    handle_volume = float(getattr(signal.contractions[-1], 'avg_volume', 0.0) or 0.0) if signal.contractions else 0.0
    if avg_volume_50d:
        evidence.append(f"Handle volume vs 50d: {handle_volume / max(avg_volume_50d, 1e-6):.2%}")
    extra = {
        "pivot": _round(entry, 4),
        "notes": signal.notes,
        "contractions": [
            {
                "start": _to_iso(c.start_date),
                "end": _to_iso(c.end_date),
                "drop": round(float(c.percent_drop or 0.0), 4),
            }
            for c in signal.contractions
        ],
        "atr14": _round(atr, 4) if atr else None,
        "cup_depth_pct": round(cup_depth_pct, 4),
        "targets_breakdown": {
            "cup_depth": target_cup,
            "resistance": resistance_target,
            "rr_1_5": conservative_target,
        },
        "stop_display": f"${stop:,.2f}",
    }
    return _result("vcp", score, entry, stop, targets, overlays, extra, evidence)


def detect_cup_handle(df: pd.DataFrame, symbol: str = "", timeframe: str = "1d") -> Optional[PatternResult]:
    data = _prepare_df(df)
    if data is None or len(data) < 160:
        return None
    atr = _compute_atr(data)
    window = data.tail(200).reset_index(drop=True)
    close = window["Close"].astype(float)
    if close.isna().any():
        close = close.fillna(method="ffill").fillna(method="bfill")
    values = close.to_numpy(dtype=float)
    if len(values) < 160:
        return None
    smooth = pd.Series(values).rolling(5, min_periods=1, center=True).mean().to_numpy()
    trough_idx = int(np.argmin(smooth))
    if trough_idx < 20 or trough_idx > len(smooth) - 30:
        return None
    left_peak_idx = int(np.argmax(smooth[:trough_idx]))
    right_peak_idx = int(np.argmax(smooth[trough_idx:]) + trough_idx)
    if right_peak_idx <= trough_idx or left_peak_idx >= trough_idx:
        return None
    pivot = float(min(smooth[left_peak_idx], smooth[right_peak_idx]))
    bottom = float(smooth[trough_idx])
    if pivot <= 0:
        return None
    depth = (pivot - bottom) / pivot
    if depth < 0.12 or depth > 0.55:
        return None
    handle_window = smooth[-20:]
    handle_high = float(handle_window.max())
    handle_low = float(handle_window.min())
    handle_depth = (handle_high - handle_low) / handle_high if handle_high else 0.0
    if handle_depth > 0.08:
        return None
    entry = pivot * 1.005
    pivot_recent = float(window["High"].iloc[-20:].max())
    entry = max(entry, pivot_recent)
    stop = handle_low * 0.99
    if entry <= stop or entry <= 0 or stop <= 0:
        return None
    measured = pivot - bottom
    targets = [entry + measured * 0.5, entry + measured]
    overlays = _base_overlay(entry, stop, targets)
    overlays["lines"].append(
        {
            "x1": _to_iso(window["Date"].iloc[left_peak_idx]),
            "y1": _round(smooth[left_peak_idx], 4),
            "x2": _to_iso(window["Date"].iloc[trough_idx]),
            "y2": _round(bottom, 4),
            "color": "#9be7ff",
            "dash": True,
        }
    )
    overlays["lines"].append(
        {
            "x1": _to_iso(window["Date"].iloc[trough_idx]),
            "y1": _round(bottom, 4),
            "x2": _to_iso(window["Date"].iloc[right_peak_idx]),
            "y2": _round(smooth[right_peak_idx], 4),
            "color": "#9be7ff",
            "dash": True,
        }
    )
    overlays["labels"].append(
        {
            "text": "Handle",
            "x": _to_iso(window["Date"].iloc[-5]),
            "y": _round(handle_high, 4),
        }
    )
    symmetry = 1.0 - abs((trough_idx - left_peak_idx) - (right_peak_idx - trough_idx)) / max(trough_idx, len(smooth) - trough_idx, 1)
    score = 65.0 + depth * 20.0 + max(0.0, symmetry * 10.0) - handle_depth * 30.0
    if atr:
        score -= min(10.0, max(0.0, (atr / max(entry, 1e-6)) * 120.0))
    score = max(0.0, min(95.0, score))
    extra = {
        "depth": round(depth, 4),
        "handle_depth": round(handle_depth, 4),
        "atr14": _round(atr, 4) if atr else None,
    }
    evidence = [
        f"depth {depth:.2%}",
        f"handle depth {handle_depth:.2%}",
        f"symmetry {symmetry:.2f}",
    ]
    return _result("cup_handle", score, entry, stop, targets, overlays, extra, evidence)


def detect_head_shoulders(df: pd.DataFrame, symbol: str = "", timeframe: str = "1d") -> Optional[PatternResult]:
    data = _prepare_df(df)
    if data is None or len(data) < 180:
        return None
    atr = _compute_atr(data)
    window = data.tail(220).reset_index(drop=True)
    close = window["Close"].astype(float)
    if len(close) < 160:
        return None
    arr = close.to_numpy()
    order = np.argsort(arr)[::-1]
    head_idx = int(order[0])
    left_candidates = [idx for idx in order[1:] if idx < head_idx]
    right_candidates = [idx for idx in order[1:] if idx > head_idx]
    if not left_candidates or not right_candidates:
        return None
    left_idx = max(left_candidates)
    right_idx = min(right_candidates)
    left_val = float(arr[left_idx])
    right_val = float(arr[right_idx])
    head_val = float(arr[head_idx])
    if head_val <= 0:
        return None
    if abs(left_val - right_val) / head_val > 0.08:
        return None
    if head_val < max(left_val, right_val) * 1.03:
        return None
    neck_left = float(window["Low"].iloc[min(left_idx, head_idx): max(left_idx, head_idx) + 1].min())
    neck_right = float(window["Low"].iloc[min(head_idx, right_idx): max(head_idx, right_idx) + 1].min())
    neckline = (neck_left + neck_right) / 2.0
    entry = neckline * 0.995
    stop = max(left_val, right_val) * 1.02
    if neckline <= 0 or entry <= 0 or stop <= 0:
        return None
    measured = head_val - neckline
    targets = [entry - measured * 0.5, entry - measured]
    overlays = _base_overlay(entry, stop, targets)
    overlays["lines"].append(
        {
            "x1": _to_iso(window["Date"].iloc[left_idx]),
            "y1": _round(left_val, 4),
            "x2": _to_iso(window["Date"].iloc[head_idx]),
            "y2": _round(head_val, 4),
            "color": "#ff8a65",
            "dash": True,
        }
    )
    overlays["lines"].append(
        {
            "x1": _to_iso(window["Date"].iloc[head_idx]),
            "y1": _round(head_val, 4),
            "x2": _to_iso(window["Date"].iloc[right_idx]),
            "y2": _round(right_val, 4),
            "color": "#ff8a65",
            "dash": True,
        }
    )
    overlays["lines"].append(
        {
            "x1": _to_iso(window["Date"].iloc[left_idx]),
            "y1": _round(neckline, 4),
            "x2": _to_iso(window["Date"].iloc[right_idx]),
            "y2": _round(neckline, 4),
            "color": "#ef5350",
            "width": 2,
        }
    )
    overlays["labels"].append(
        {
            "text": "Head",
            "x": _to_iso(window["Date"].iloc[head_idx]),
            "y": _round(head_val, 4),
        }
    )
    symmetry = 1.0 - abs((head_idx - left_idx) - (right_idx - head_idx)) / max(head_idx, len(arr) - head_idx, 1)
    score = 60.0 + min(15.0, max(0.0, measured / neckline * 35.0)) + max(0.0, symmetry * 10.0)
    if atr:
        risk_ratio = atr / max(entry, 1e-6)
        score -= min(12.0, max(0.0, risk_ratio * 140.0))
    score = max(0.0, min(92.0, score))
    extra = {
        "structure": "double-top" if targets[0] < entry else "bearish",
        "atr14": _round(atr, 4) if atr else None,
    }
    evidence = [
        f"head vs shoulders diff {head_val - max(left_val, right_val):.2f}",
        f"neckline {neckline:.2f}",
        f"symmetry {symmetry:.2f}",
    ]
    return _result("hns", score, entry, stop, targets, overlays, extra, evidence)


def detect_flag_pennant(df: pd.DataFrame, symbol: str = "", timeframe: str = "1d") -> Optional[PatternResult]:
    data = _prepare_df(df)
    if data is None or len(data) < 120:
        return None
    atr = _compute_atr(data)
    window = data.tail(140).reset_index(drop=True)
    close = window["Close"].astype(float)
    high = window["High"].astype(float)
    low = window["Low"].astype(float)
    if len(close) < 90:
        return None
    pole_start = max(0, len(close) - 80)
    pole_mid = max(0, len(close) - 50)
    pole_gain = (close.iloc[pole_mid] - close.iloc[pole_start]) / close.iloc[pole_start]
    if pole_gain < 0.18:
        return None
    consolidation_high = high.iloc[-30:]
    consolidation_low = low.iloc[-30:]
    band = (consolidation_high.max() - consolidation_low.min()) / max(consolidation_low.mean(), 1e-6)
    if band > 0.18:
        return None
    x = np.arange(30, dtype=float)
    slope_high = np.polyfit(x, consolidation_high.to_numpy(), 1)[0]
    slope_low = np.polyfit(x, consolidation_low.to_numpy(), 1)[0]
    entry = float(consolidation_high.max()) * 1.002
    stop = float(consolidation_low.min()) * 0.995
    if entry <= stop:
        return None
    pole_height = float(close.iloc[pole_mid] - close.iloc[pole_start])
    targets = [entry + pole_height * 0.75, entry + pole_height * 1.2]
    overlays = _base_overlay(entry, stop, targets)
    overlays["boxes"].append(
        {
            "x1": _to_iso(window["Date"].iloc[-30]),
            "y1": _round(consolidation_high.max(), 4),
            "x2": _to_iso(window["Date"].iloc[-1]),
            "y2": _round(consolidation_low.min(), 4),
            "color": "#1e88e5",
            "opacity": 0.15,
        }
    )
    overlays["labels"].append(
        {
            "text": "Flag",
            "x": _to_iso(window["Date"].iloc[-15]),
            "y": _round(consolidation_high.mean(), 4),
        }
    )
    score = 62.0 + pole_gain * 80.0 + max(0.0, (0.18 - band) * 100.0) - abs(slope_high - slope_low) * 5.0
    if atr:
        score -= min(8.0, max(0.0, (atr / max(entry, 1e-6)) * 100.0))
    score = max(0.0, min(94.0, score))
    extra = {
        "pole_gain": round(pole_gain, 4),
        "atr14": _round(atr, 4) if atr else None,
    }
    evidence = [
        f"pole gain {pole_gain:.2%}",
        f"consolidation band {band:.2%}",
    ]
    return _result("flag", score, entry, stop, targets, overlays, extra, evidence)


def detect_wedge(df: pd.DataFrame, symbol: str = "", timeframe: str = "1d") -> Optional[PatternResult]:
    data = _prepare_df(df)
    if data is None or len(data) < 150:
        return None
    atr = _compute_atr(data)
    window = data.tail(180).reset_index(drop=True)
    high = window["High"].astype(float)
    low = window["Low"].astype(float)
    if len(high) < 100:
        return None
    segment_high = high.iloc[-90:]
    segment_low = low.iloc[-90:]
    x = np.arange(len(segment_high), dtype=float)
    slope_high, intercept_high = np.polyfit(x, segment_high.to_numpy(), 1)
    slope_low, intercept_low = np.polyfit(x, segment_low.to_numpy(), 1)
    spread_start = segment_high.iloc[0] - segment_low.iloc[0]
    spread_end = segment_high.iloc[-1] - segment_low.iloc[-1]
    narrowing = spread_end < spread_start * 0.85
    if not narrowing:
        return None
    if slope_high > 0 and slope_low > 0:
        pattern_type = "rising"
        entry = float(segment_low.iloc[-1]) * 0.995
        stop = float(segment_high.iloc[-1]) * 1.01
        measured = spread_start
        targets = [entry - measured * 0.6, entry - measured]
    elif slope_high < 0 and slope_low < 0:
        pattern_type = "falling"
        entry = float(segment_high.iloc[-1]) * 1.005
        stop = float(segment_low.iloc[-1]) * 0.99
        measured = spread_start
        targets = [entry + measured * 0.6, entry + measured]
    else:
        return None
    if entry <= 0 or stop <= 0:
        return None
    overlays = _base_overlay(entry, stop, targets)
    overlays["lines"].append(
        {
            "x1": _to_iso(window["Date"].iloc[-90]),
            "y1": _round(segment_high.iloc[0], 4),
            "x2": _to_iso(window["Date"].iloc[-1]),
            "y2": _round(segment_high.iloc[-1], 4),
            "color": "#ab47bc",
            "dash": True,
        }
    )
    overlays["lines"].append(
        {
            "x1": _to_iso(window["Date"].iloc[-90]),
            "y1": _round(segment_low.iloc[0], 4),
            "x2": _to_iso(window["Date"].iloc[-1]),
            "y2": _round(segment_low.iloc[-1], 4),
            "color": "#ab47bc",
            "dash": True,
        }
    )
    overlays["labels"].append(
        {
            "text": f"{pattern_type.title()} wedge",
            "x": _to_iso(window["Date"].iloc[-10]),
            "y": _round((segment_high.iloc[-1] + segment_low.iloc[-1]) / 2.0, 4),
        }
    )
    slope_gap = abs(slope_high - slope_low)
    score = 58.0 + max(0.0, (spread_start - spread_end) / max(spread_start, 1e-6) * 40.0) - slope_gap * 5.0
    score += 8.0 if pattern_type == "falling" else 0.0
    if atr:
        score -= min(10.0, max(0.0, (atr / max(entry, 1e-6)) * 120.0))
    score = max(0.0, min(90.0, score))
    extra = {
        "direction": pattern_type,
        "atr14": _round(atr, 4) if atr else None,
    }
    evidence = [
        f"spread compression {(spread_end / max(spread_start, 1e-6)):.2f}",
        f"slope gap {slope_gap:.4f}",
    ]
    return _result("wedge", score, entry, stop, targets, overlays, extra, evidence)


def detect_double_top_bottom(df: pd.DataFrame, symbol: str = "", timeframe: str = "1d") -> Optional[PatternResult]:
    data = _prepare_df(df)
    if data is None or len(data) < 140:
        return None
    atr = _compute_atr(data)
    window = data.tail(200).reset_index(drop=True)
    close = window["Close"].astype(float)
    if len(close) < 120:
        return None
    arr = close.to_numpy()
    # Double top
    max_idx = int(np.argmax(arr))
    alt = arr.copy()
    alt[max(0, max_idx - 5): min(len(arr), max_idx + 6)] = arr.min()
    second_idx = int(np.argmax(alt))
    if abs(arr[second_idx] - arr[max_idx]) / arr[max_idx] <= 0.025 and abs(max_idx - second_idx) > 5:
        left, right = sorted([max_idx, second_idx])
        neckline = float(window["Low"].iloc[left:right + 1].min())
        entry = neckline * 0.995
        stop = float(max(arr[max_idx], arr[second_idx]) * 1.02)
        measured = max(arr[max_idx], arr[second_idx]) - neckline
        targets = [entry - measured * 0.5, entry - measured]
        overlays = _base_overlay(entry, stop, targets)
        overlays["lines"].append(
            {
                "x1": _to_iso(window["Date"].iloc[left]),
                "y1": _round(arr[left], 4),
                "x2": _to_iso(window["Date"].iloc[right]),
                "y2": _round(arr[right], 4),
                "color": "#ff7043",
                "dash": True,
            }
        )
        overlays["lines"].append(
            {
                "x1": _to_iso(window["Date"].iloc[left]),
                "y1": _round(neckline, 4),
                "x2": _to_iso(window["Date"].iloc[right]),
                "y2": _round(neckline, 4),
                "color": "#ff7043",
                "width": 2,
            }
        )
        score = 63.0 + min(20.0, measured / max(arr[max_idx], 1e-6) * 40.0)
        if atr:
            score -= min(10.0, max(0.0, (atr / max(entry, 1e-6)) * 120.0))
        score = max(0.0, min(90.0, score))
        extra = {"structure": "double_top"}
        extra["atr14"] = _round(atr, 4) if atr else None
        evidence = [
            f"neckline {neckline:.2f}",
            f"peak distance {abs(max_idx - second_idx)} bars",
        ]
        return _result("double", score, entry, stop, targets, overlays, extra, evidence)
    # Double bottom
    min_idx = int(np.argmin(arr))
    alt = arr.copy()
    alt[max(0, min_idx - 5): min(len(arr), min_idx + 6)] = arr.max()
    second_idx = int(np.argmin(alt))
    if abs(arr[second_idx] - arr[min_idx]) / max(arr[min_idx], 1e-6) <= 0.03 and abs(min_idx - second_idx) > 5:
        left, right = sorted([min_idx, second_idx])
        neckline = float(window["High"].iloc[left:right + 1].max())
        entry = neckline * 1.005
        stop = float(min(arr[min_idx], arr[second_idx]) * 0.98)
        measured = neckline - min(arr[min_idx], arr[second_idx])
        targets = [entry + measured * 0.5, entry + measured]
        overlays = _base_overlay(entry, stop, targets)
        overlays["lines"].append(
            {
                "x1": _to_iso(window["Date"].iloc[left]),
                "y1": _round(arr[left], 4),
                "x2": _to_iso(window["Date"].iloc[right]),
                "y2": _round(arr[right], 4),
                "color": "#66bb6a",
                "dash": True,
            }
        )
        overlays["lines"].append(
            {
                "x1": _to_iso(window["Date"].iloc[left]),
                "y1": _round(neckline, 4),
                "x2": _to_iso(window["Date"].iloc[right]),
                "y2": _round(neckline, 4),
                "color": "#66bb6a",
                "width": 2,
            }
        )
        score = 63.0 + min(20.0, measured / max(neckline, 1e-6) * 40.0)
        if atr:
            score -= min(10.0, max(0.0, (atr / max(entry, 1e-6)) * 120.0))
        score = max(0.0, min(90.0, score))
        extra = {"structure": "double_bottom"}
        extra["atr14"] = _round(atr, 4) if atr else None
        evidence = [
            f"neckline {neckline:.2f}",
            f"trough distance {abs(min_idx - second_idx)} bars",
        ]
        return _result("double", score, entry, stop, targets, overlays, extra, evidence)
    return None


_DETECTORS: Dict[PatternName, Callable[[pd.DataFrame, str, str], Optional[PatternResult]]] = {
    "vcp": detect_vcp,
    "cup_handle": detect_cup_handle,
    "hns": detect_head_shoulders,
    "flag": detect_flag_pennant,
    "wedge": detect_wedge,
    "double": detect_double_top_bottom,
}


def detect(pattern: PatternName, df: pd.DataFrame, symbol: str = "", timeframe: str = "1d") -> Optional[PatternResult]:
    key = pattern.lower()  # type: ignore[arg-type]
    if key not in _DETECTORS:
        raise ValueError(f"Unsupported pattern: {pattern}")
    return _DETECTORS[key](df, symbol, timeframe)


__all__ = ["PatternName", "PatternResult", "detect"] + [func.__name__ for func in _DETECTORS.values()]
