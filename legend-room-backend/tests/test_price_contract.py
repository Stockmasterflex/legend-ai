import os
from fastapi.testclient import TestClient


def test_price_contract_shape(tmp_path, monkeypatch):
    # Use a temp sqlite file DB for the test
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path}/prices.db"

    from legend_room_backend import main

    # Mock the fetcher to avoid network and pandas/yfinance
    def fake_fetch(symbol: str, limit: int):
        base = [
            {"symbol": symbol, "date": f"2025-09-{d:02d}", "open": 1.0*d, "high": 1.1*d, "low": 0.9*d, "close": 1.05*d, "volume": d*1000}
            for d in range(1, 11)
        ]
        # Convert date strings to date objects as main expects pre-insert
        from datetime import date
        out = []
        for row in base:
            y, m, d = map(int, row["date"].split("-"))
            out.append({**row, "date": date(y, m, d)})
        return out

    monkeypatch.setattr(main, "fetch_prices_yf", fake_fetch)

    client = TestClient(main.app)
    r = client.get("/api/price", params={"symbol": "SPY", "limit": 5})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 5
    row = data[0]
    assert set(row.keys()) == {"symbol", "date", "open", "high", "low", "close", "volume"}
    assert row["symbol"] == "SPY"

