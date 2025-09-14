from pathlib import Path
import pandas as pd
from backtest.run_backtest import scan_once
from fastapi.testclient import TestClient
from service_api import app


def test_scan_produces_csv():
    out = scan_once("ci-smoke")
    assert Path(out).exists()
    df = pd.read_csv(out)
    # Columns should exist even if no rows
    assert "symbol" in df.columns


def test_candidates_by_date_endpoint():
    client = TestClient(app)
    r = client.get("/api/v1/vcp/candidates", params={"day": "ci-smoke"})
    assert r.status_code == 200
    body = r.json()
    assert "rows" in body

