from __future__ import annotations

from fastapi.testclient import TestClient

import service_api


def test_analytics_overview_empty(monkeypatch):
    # Monkeypatch artifacts root to a non-existent temp dir to simulate empty data
    def fake_artifacts_root(run_id, db):
        from pathlib import Path
        return Path("/tmp/legend-nonexistent-artifacts")

    monkeypatch.setattr(service_api, "_artifacts_root_for_run", fake_artifacts_root)

    client = TestClient(service_api.app)
    resp = client.get("/api/v1/analytics/overview", params={"run_id": 1})
    assert resp.status_code == 200
    payload = resp.json()
    # Validate stable schema and defaults
    assert isinstance(payload.get("kpis"), dict)
    kpis = payload["kpis"]
    for key in ("win_rate", "avg_r", "trades"):
        assert key in kpis
    assert isinstance(payload.get("pattern_distribution"), list)
    assert isinstance(payload.get("recent_candidates"), list)
    assert isinstance(payload.get("performance_timeline"), list)
    assert payload.get("data_status") in {"ok", "empty", "partial"}


