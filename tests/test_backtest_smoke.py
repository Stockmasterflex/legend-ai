from pathlib import Path
import json
from backtest.run_backtest import run_backtest
from fastapi.testclient import TestClient
from service_api import app


def test_walk_forward_smoke():
    start = "2024-01-02"
    end = "2024-01-10"
    summary_path = run_backtest(start, end, "simple", "yfinance")
    assert Path(summary_path).exists()
    data = json.loads(Path(summary_path).read_text())
    # Keys exist
    for k in ("precision_at_10","hit_rate","num_candidates","num_triggers","num_success"):
        assert k in data


def test_runs_endpoint_lists_runs():
    client = TestClient(app)
    r = client.get("/api/v1/runs?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert "runs" in body
    assert isinstance(body["runs"], list)
    # If a run was persisted by previous test, ensure fields present
    if body["runs"]:
        sample = body["runs"][0]
        for k in ("id","start","end","universe","provider"):
            assert k in sample

