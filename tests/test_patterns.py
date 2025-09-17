from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from signals import patterns


def _frame(values: np.ndarray) -> pd.DataFrame:
    dates = pd.date_range("2023-01-01", periods=len(values), freq="D")
    opens = values * 0.999
    highs = values * 1.01
    lows = values * 0.99
    volume = np.full(len(values), 1_200_000)
    return pd.DataFrame(
        {
            "Date": dates,
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": values,
            "Volume": volume,
        }
    )


def test_detect_vcp_uses_detector(monkeypatch: pytest.MonkeyPatch):
    values = np.linspace(100, 120, 200)
    df = _frame(values)
    mock_signal = SimpleNamespace(
        detected=True,
        pivot_price=125.0,
        final_contraction_tightness=0.06,
        volume_dry_up=True,
        notes=["stub"],
        contractions=[
            SimpleNamespace(
                start_date=datetime(2023, 3, 1),
                end_date=datetime(2023, 3, 10),
                high_price=118.0,
                low_price=112.0,
                percent_drop=0.05,
            ),
            SimpleNamespace(
                start_date=datetime(2023, 3, 11),
                end_date=datetime(2023, 3, 20),
                high_price=117.0,
                low_price=113.5,
                percent_drop=0.03,
            ),
        ],
    )

    class _StubDetector:
        def detect_vcp(self, *_args, **_kwargs):  # noqa: D401
            return mock_signal

    monkeypatch.setattr(patterns, "_VCP_DETECTOR", _StubDetector())

    result = patterns.detect_vcp(df, "TEST")
    assert result is not None
    assert result["entry"] == pytest.approx(125.0, rel=1e-2)
    assert result["targets"]
    overlays = result["overlays"]
    assert overlays["priceLevels"]["entry"] == pytest.approx(result["entry"])
    assert overlays["lines"], "expected contraction overlays"
    assert "key_levels" in result
    assert "evidence" in result


def test_detect_cup_handle_generates_levels():
    cup = np.concatenate(
        [
            np.linspace(100, 91, 70),
            np.linspace(91, 84, 30),
            np.linspace(84, 106, 70),
            np.linspace(106, 101, 10),
            np.linspace(101, 103, 10),
            np.linspace(103, 105, 10),
        ]
    )
    df = _frame(cup)
    result = patterns.detect_cup_handle(df, "TEST")
    assert result is not None
    assert result["entry"] > result["stop"]
    assert result["targets"], "cup-handle should compute targets"
    assert result["key_levels"]["entry"] == result["entry"]


def test_detect_double_bottom_spots_structure():
    series = np.concatenate(
        [
            np.linspace(100, 82, 50),
            np.linspace(82, 85, 15),
            np.linspace(85, 80, 15),
            np.linspace(80, 84, 15),
            np.linspace(84, 79.5, 15),
            np.linspace(79.5, 95, 30),
        ]
    )
    df = _frame(series)
    result = patterns.detect_double_top_bottom(df, "TEST")
    assert result is not None
    assert result["pattern"] == "double"
    assert result["targets"], "double bottom should include targets"
    assert result["overlays"]["priceLevels"]["entry"] > 0
    assert "evidence" in result
