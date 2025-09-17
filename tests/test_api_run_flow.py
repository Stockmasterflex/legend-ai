import json
from fastapi.testclient import TestClient
import os

from service_api import app


def test_runs_list_and_create_mock(monkeypatch):
    client = TestClient(app)

    # List runs should return at least sample when DB not initialized
    r = client.get("/api/v1/runs")
    assert r.status_code == 200
    data = r.json()
    assert "runs" in data

    # Create run via JSON body
    payload = {
        "start": "2024-01-01",
        "end": "2024-01-31",
        "universe": "simple",
        "provider": "yfinance",
        "detector_version": "v1",
    }
    r2 = client.post("/api/v1/runs", json=payload)
    assert r2.status_code == 202
    j = r2.json()
    assert "status" in j

