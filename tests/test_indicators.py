import pandas as pd
import numpy as np
from indicators.ta import compute_all_indicators

def test_basic_indicators():
    close = pd.Series(np.linspace(100, 110, 50))
    vol = pd.Series(np.random.randint(1000, 2000, size=50))
    df = pd.DataFrame({
        "Open": close,
        "High": close + 1,
        "Low": close - 1,
        "Close": close,
        "Volume": vol,
    })
    out = compute_all_indicators(df)
    assert "ema21" in out
    assert "rsi14" in out and 0 <= out["rsi14"] <= 100
    assert isinstance(out.get("macd"), dict)

