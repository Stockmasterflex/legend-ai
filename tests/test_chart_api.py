from __future__ import annotations

from fastapi.testclient import TestClient

import service_api


def test_chart_post_with_overlays(monkeypatch):
    async def fake_fetch(symbol, params=None, overlays=None, client=None, *, include_meta=False):
        assert include_meta is True
        assert overlays and overlays.get("lines")
        return "https://example.com/chart.png", {
            "fallback": False,
            "overlay_applied": True,
            "source": "shots-test",
        }

    monkeypatch.setattr(service_api, "_fetch_chart_url", fake_fetch)
    client = TestClient(service_api.app)
    payload = {
        "overlays": {
            "lines": [{"x1": "2024-01-01", "y1": 100, "x2": "2024-02-01", "y2": 110}],
            "labels": [{"x": "2024-02-01", "y": 110, "text": "test"}],
        }
    }
    resp = client.post("/api/v1/chart", params={"symbol": "TEST"}, json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["chart_url"] == "https://example.com/chart.png"
    meta = body["meta"]
    assert meta["overlay_applied"] is True
    assert meta["overlay_counts"]["lines"] == 1
    assert meta["overlay_counts"]["labels"] == 1


def test_chart_get_fallback(monkeypatch):
    async def fake_fetch(symbol, params=None, overlays=None, client=None, *, include_meta=False):
        assert include_meta is True
        return "https://dummyimage.com/fallback", {
            "fallback": True,
            "overlay_applied": False,
            "source": "dummy",
            "error": "shots unavailable",
        }

    monkeypatch.setattr(service_api, "_fetch_chart_url", fake_fetch)
    client = TestClient(service_api.app)
    resp = client.get("/api/v1/chart", params={"symbol": "TEST"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["chart_url"].startswith("https://dummyimage.com")
    assert body["meta"]["fallback"] is True
    assert body["meta"]["overlay_applied"] is False
