import os
from datetime import datetime, timedelta

import pandas as pd


def test_market_indices_cached(monkeypatch):
    os.environ["LEGEND_FLAGS"] = "cache"

    # Import target module (note: this may import SQLAlchemy; that's okay here)
    import app.legend_ai_backend as mod

    # Build fake price history
    base_date = datetime.utcnow()
    df = pd.DataFrame({
        "Date": [base_date - timedelta(days=i) for i in range(60)][::-1],
        "Close": [100 + i for i in range(60)],
    })

    calls = {"n": 0}

    def fake_fetch(symbol: str, days: int = 120):
        calls["n"] += 1
        return df.copy()

    store = {}

    def fake_get(key: str):
        return store.get(key)

    def fake_set(key: str, payload, ttl: int = 60):
        store[key] = payload

    # Patch helpers on the module namespace used by the route
    monkeypatch.setattr(mod, "_fetch_price_history", fake_fetch)
    monkeypatch.setattr(mod, "cache_get", fake_get)
    monkeypatch.setattr(mod, "cache_set", fake_set)

    # First call computes and caches
    result1 = mod.market_indices_overview()
    assert result1 and getattr(result1, "indices", None)
    assert calls["n"] > 0

    # Second call should be served from cache (no extra fetches)
    calls_before = calls["n"]
    result2 = mod.market_indices_overview()
    assert result2 and getattr(result2, "indices", None)
    assert calls["n"] == calls_before
