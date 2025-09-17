from fastapi.testclient import TestClient
from pathlib import Path
import pandas as pd

from service_api import app
from backtest.simulate import REPORT_ROOT


def test_analytics_overview_sample_when_no_run(tmp_path, monkeypatch):
    client = TestClient(app)
    # Ensure reports dir exists but empty
    (REPORT_ROOT / "daily_candidates").mkdir(parents=True, exist_ok=True)
    (REPORT_ROOT / "outcomes").mkdir(parents=True, exist_ok=True)

    # Use fallback sample by asking for a non-existent run id
    r = client.get("/api/v1/analytics/overview", params={"run_id": 999999})
    assert r.status_code == 200
    j = r.json()
    assert "pattern_distribution" in j
    assert "kpis" in j

