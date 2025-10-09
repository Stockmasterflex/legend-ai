import pytest
from starlette.testclient import TestClient


def test_market_indices_cached(monkeypatch):
    calls = {"count": 0}

    def fake_fetch(symbol: str, days: int = 120):  # noqa: ARG001
        # return minimal DataFrame-like structure for recent.tail(60)
        import pandas as pd
        import numpy as np

        calls["count"] += 1
        dates = pd.date_range(end=pd.Timestamp.utcnow(), periods=90, freq="D")
        df = pd.DataFrame({
            "Date": dates,
            "Close": np.linspace(100, 110, len(dates)),
        })
        return df

    # Monkeypatch the internal fetch to count calls
    import app.legend_ai_backend as mod

    monkeypatch.setattr(mod, "_fetch_price_history", fake_fetch)

    c = TestClient(mod.app)

    # First call computes and should populate cache
    r1 = c.get("/api/market/indices")
    assert r1.status_code == 200
    out1 = r1.json()
    assert out1["indices"] and len(out1["indices"]) >= 1

    # Second call should use cache and not call underlying fetch again
    before = calls["count"]
    r2 = c.get("/api/market/indices")
    assert r2.status_code == 200
    out2 = r2.json()
    after = calls["count"]

    assert out2["indices"] and len(out2["indices"]) == len(out1["indices"])
    assert after == before
