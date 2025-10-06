import json
from pathlib import Path
import pytest
import pandas as pd

from vcp_ultimate_algorithm import VCPDetector


def load_fixture_set(path: Path):
    return json.loads(path.read_text())


def fetch_prices(symbol: str) -> pd.DataFrame | None:
    # Reuse seeded JSON price files if available
    p = Path("data/price_history") / f"{symbol}.json"
    if not p.exists():
        return None
    data = json.loads(p.read_text())
    if not data:
        return None
    df = pd.DataFrame(data)
    if df.empty:
        return None
    df = df.rename(columns={"date": "Date", "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])  # type: ignore[assignment]
        df = df.set_index("Date")
    return df[["Open", "High", "Low", "Close", "Volume"]]


@pytest.mark.slow
def test_true_vcp_windows():
    fixtures = load_fixture_set(Path("tests/fixtures/true_vcp.json"))
    # Mirror production scan: ignore trend template but require mid-priced stocks to reduce noise
    det = VCPDetector(check_trend_template=False, min_price=30)
    hits = 0
    for f in fixtures:
        df = fetch_prices(f["symbol"])  # ignore date windows for simplicity
        if df is None:
            continue
        sig = det.detect_vcp(df, symbol=f["symbol"])  # type: ignore[arg-type]
        if sig.detected:
            hits += 1
    assert hits >= 1


@pytest.mark.slow
def test_false_vcp_windows():
    fixtures = load_fixture_set(Path("tests/fixtures/false_vcp.json"))
    # Use same detector settings so false fixtures must pass tightened price filter
    det = VCPDetector(check_trend_template=False, min_price=30)
    hits = 0
    for f in fixtures:
        df = fetch_prices(f["symbol"])  # ignore date windows for simplicity
        if df is None:
            continue
        sig = det.detect_vcp(df, symbol=f["symbol"])  # type: ignore[arg-type]
        if sig.detected:
            hits += 1
    assert hits == 0
