#!/usr/bin/env python3
"""
Legend AI — Phase 4: Advanced AI Trading Implementation (portable)
- yfinance OHLCV
- Indicators: MACD/RSI/ATR/vol
- Volume-confirmed MACD cross signal + divergence hint
- Optional FinBERT sentiment (robust label mapping)
"""
import argparse, json, sys, time
from datetime import datetime

def _try_import(mod):
    try:
        return __import__(mod)
    except Exception:
        return None

np = _try_import("numpy")
pd = _try_import("pandas")
yf = _try_import("yfinance")
transformers = _try_import("transformers")
torch = _try_import("torch")

# TA imports (portable)
ta = _try_import("ta")
RSIIndicator = None
if ta:
    try:
        from ta.momentum import RSIIndicator as _RSI
        RSIIndicator = _RSI
    except Exception:
        RSIIndicator = None

def finbert_sentiment(text: str):
    if not transformers or not torch:
        return {"sentiment":"unknown","score":0.0,"confidence":0.0,"note":"transformers/torch not installed"}
    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        tok = AutoTokenizer.from_pretrained("ProsusAI/finbert")
        model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
        labels_map = getattr(model.config, "id2label", {0:"negative",1:"neutral",2:"positive"})
        inputs = tok(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            out = model(**inputs).logits
        probs = torch.nn.functional.softmax(out, dim=-1)[0].tolist()
        idx = int(max(range(len(probs)), key=lambda i: probs[i]))
        lab = str(labels_map.get(idx, "neutral")).lower()
        score = float(probs[idx])
        sign = 1 if lab=="positive" else (-1 if lab=="negative" else 0)
        return {"sentiment":lab, "score": round(sign*score,3), "confidence": round(max(probs),3)}
    except Exception as e:
        return {"sentiment":"error","score":0.0,"confidence":0.0,"note":str(e)}

def indicators(df):
    if df is None or df.empty or ta is None:
        return df
    close = df["Close"]; high = df["High"]; low = df["Low"]; vol = df["Volume"]
    # RSI (portable)
    if RSIIndicator:
        df["RSI14"] = RSIIndicator(close, window=14).rsi()
    else:
        df["RSI14"] = float("nan")
    macd = ta.trend.MACD(close)
    df["MACD"] = macd.macd()
    df["MACD_SIG"] = macd.macd_signal()
    df["MACD_HIST"] = macd.macd_diff()
    df["ATR14"] = ta.volatility.average_true_range(high, low, close, window=14)
    df["VOL20"] = vol.rolling(20).mean()
    return df

def macd_volume_signal(df):
    if df is None or len(df)<35: return {"label":"none","score":0}
    last = df.iloc[-1]; prev = df.iloc[-2]
    import math
    vol20 = last["VOL20"] if not pd.isna(last["VOL20"]) else 0
    vol_ok = last["Volume"] > vol20
    cross_up   = prev["MACD"] <= prev["MACD_SIG"] and last["MACD"] > last["MACD_SIG"]
    cross_down = prev["MACD"] >= prev["MACD_SIG"] and last["MACD"] < last["MACD_SIG"]
    score = 0; label = "neutral"
    if cross_up and vol_ok:
        score = 75 + min(25, 5*max(0, float(last["MACD_HIST"])))
        label = "bullish"
    elif cross_down and vol_ok:
        score = -75 - min(25, 5*max(0, -float(last["MACD_HIST"])))
        label = "bearish"
    return {"label":label, "score":int(score), "vol_ok":bool(vol_ok)}

def divergence_hint(df):
    if df is None or len(df)<40: return "none"
    seg = df.iloc[-40:]; c = seg["Close"].values; r = seg["RSI14"].values
    import numpy as np
    p_low1, p_low2 = np.min(c[-20:]), np.min(c[-40:-20])
    r_low1, r_low2 = np.nanmin(r[-20:]), np.nanmin(r[-40:-20])
    p_high1, p_high2 = np.max(c[-20:]), np.max(c[-40:-20])
    r_high1, r_high2 = np.nanmax(r[-20:]), np.nanmax(r[-40:-20])
    if p_low1 < p_low2 and r_low1 > r_low2: return "bullish-div"
    if p_high1 > p_high2 and r_high1 < r_high2: return "bearish-div"
    return "none"

def levels(df):
    if df is None or df.empty: return {}
    last = df.iloc[-1]
    close = float(last["Close"])
    import math
    atr = float(last["ATR14"]) if not pd.isna(last["ATR14"]) else 0.0
    return {"last": round(close,2),
            "risk": round(max(0.0, close - 2*atr),2),
            "t1": round(close + 2*atr,2),
            "t2": round(close + 3*atr,2)}

def run(tickers, days):
    out = []
    for t in tickers:
        try:
            df = yf.download(t, period=f"{max(30,days)}d", interval="1d", progress=False)
            if df is None or df.empty:
                out.append({"symbol":t,"error":"no data"}); continue
            # Ensure 1D Series for indicators that may return Nx1 arrays
            for col in list(df.columns):
                try:
                    if hasattr(df[col], 'to_numpy'):
                        arr = df[col].to_numpy()
                        if getattr(arr, 'ndim', 1) == 2 and arr.shape[1] == 1:
                            # Flatten to 1D
                            import numpy as _np
                            df[col] = _np.ravel(arr)
                except Exception:
                    pass
            df = indicators(df)
            sig = macd_volume_signal(df)
            div = divergence_hint(df)
            lev = levels(df)
            sentiment = finbert_sentiment(f"{t} earnings outlook growth revenue guidance momentum")
            out.append({"symbol":t,"signal":sig,"divergence":div,"levels":lev,
                        "sentiment":sentiment,"updated_at":datetime.utcnow().isoformat()+"Z"})
        except Exception as e:
            out.append({"symbol":t,"error":str(e)})
        time.sleep(0.2)
    print(json.dumps(out, indent=2)); return 0

if __name__ == "__main__":
    if not (pd and np and yf):
        print("[]"); sys.exit(0)
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", type=str, default="NVDA,AAPL,MSFT,AMD")
    ap.add_argument("--days", type=int, default=250)
    a = ap.parse_args()
    tickers = [t.strip().upper() for t in a.tickers.split(",") if t.strip()]
    sys.exit(run(tickers, a.days))
