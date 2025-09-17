from __future__ import annotations

from fastapi.testclient import TestClient

import service_api


def test_scan_endpoint_returns_results(monkeypatch):
    monkeypatch.setattr(service_api, "get_universe", lambda name: ["AAA", "BBB"])

    async def fake_attach(_pattern, rows):
        for row in rows:
            row.setdefault("chart_url", f"https://example.com/{row['symbol']}")

    def fake_scan(pattern, symbol, *, timeframe, min_price, min_volume, max_atr_ratio):
        return {
            "symbol": symbol,
            "score": 87.5,
            "entry": 101.0,
            "stop": 96.0,
            "targets": [110.0, 116.0],
            "pattern": pattern,
            "overlays": {"priceLevels": {"entry": 101.0, "stop": 96.0, "targets": [110.0, 116.0]}},
            "chart_url": f"https://example.com/{symbol}",
            "avg_price": 150.0,
            "avg_volume": 1_000_000,
            "atr14": 2.5,
            "key_levels": {"entry": 101.0, "stop": 96.0, "targets": [110.0, 116.0]},
            "meta": {"evidence": ["test"]},
        }

    monkeypatch.setattr(service_api, "_scan_symbol", fake_scan)
    monkeypatch.setattr(service_api, "_attach_chart_urls", fake_attach)

    client = TestClient(service_api.app)
    resp = client.get("/api/v1/scan", params={"pattern": "vcp", "universe": "sp500", "limit": 10})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["pattern"] == "vcp"
    assert payload["universe"] == "sp500"
    assert payload["count"] == 2
    assert len(payload["results"]) == 2
    row = payload["results"][0]
    assert row["chart_url"].startswith("https://example.com/")
    assert "avg_price" in row and "avg_volume" in row
    assert "key_levels" in row


def test_scan_endpoint_rejects_bad_pattern():
    client = TestClient(service_api.app)
    resp = client.get("/api/v1/scan", params={"pattern": "unknown", "universe": "sp500"})
    assert resp.status_code == 400
