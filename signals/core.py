import logging
import os
from typing import Dict, Any
import pandas as pd

log = logging.getLogger("legend.signals")

def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except Exception:
        return default

SIGNAL_VOLX = _env_float("SIGNAL_VOLX", 1.5)
SIGNAL_MIN_RSI = _env_float("SIGNAL_MIN_RSI", 45.0)
SIGNAL_MAX_BBWIDTH = _env_float("SIGNAL_MAX_BBWIDTH", 0.25)
SIGNAL_BUY_MIN = _env_float("SIGNAL_BUY_MIN", 70.0)
SIGNAL_SELL_MAX = _env_float("SIGNAL_SELL_MAX", 40.0)

def score_from_indicators(ind: Dict[str, Any], df: pd.DataFrame) -> Dict[str, Any]:
    score = 50.0
    reasons = []
    badges = []
    # RSI
    rsi = float(ind.get("rsi14") or 0.0)
    if rsi >= 60:
        score += 10; reasons.append("RSI≥60")
    elif rsi >= SIGNAL_MIN_RSI:
        score += 5; reasons.append(f"RSI≥{int(SIGNAL_MIN_RSI)}")
    else:
        score -= 5; reasons.append("RSI<min")
    # MACD cross + volume
    macd = ind.get("macd", {}) or {}
    macd_val = float(macd.get("macd") or 0.0)
    macd_sig = float(macd.get("signal") or 0.0)
    vol = float(df["Volume"].iloc[-1]) if len(df) else 0.0
    vol50 = float(ind.get("vol_sma50") or 0.0)
    volx = (vol / vol50) if vol50 else 0.0
    if macd_val > macd_sig and volx >= SIGNAL_VOLX:
        score += 12
        reasons.append("MACD bullish + vol")
        badges.append("volume-confirmed MACD")
    elif macd_val > macd_sig:
        score += 6
        reasons.append("MACD bullish")
    # BB width (tightness)
    bbwidth = float(ind.get("bb_width") or 1.0)
    if bbwidth and bbwidth <= SIGNAL_MAX_BBWIDTH:
        score += 8; reasons.append("tight BB")
    # Trend/regime alignment (price vs EMA)
    close = float(df["Close"].iloc[-1]) if len(df) else 0.0
    ema50 = float(ind.get("ema50") or 0.0)
    ema200 = float(ind.get("ema200") or 0.0)
    regime = "unknown"
    if close and ema50 and ema200:
        if close > ema50 > ema200:
            score += 8; reasons.append("trend aligned"); regime = "bullish"
        elif close < ema50 < ema200:
            score -= 6; reasons.append("downtrend"); regime = "bearish"
        else:
            regime = "neutral"

    score = max(1.0, min(100.0, score))
    label = "Neutral"
    if score >= SIGNAL_BUY_MIN:
        label = "Buy"
    elif score <= SIGNAL_SELL_MAX:
        label = "Sell"
    return {
        "score": round(score, 1),
        "label": label,
        "reasons": reasons,
        "ema21": ind.get("ema21"),
        "ema50": ind.get("ema50"),
        "ema200": ind.get("ema200"),
        "rsi": rsi,
        "macd": {"macd": macd_val, "signal": macd_sig, "hist": float(macd.get("hist") or 0.0)},
        "bbwidth": bbwidth,
        "badges": badges,
        "regime": regime,
        "volx": round(volx, 2) if volx else None,
    }

