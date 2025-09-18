import os
import requests
from urllib.parse import urlencode

DUMMY_BASE = "https://dummyimage.com/1200x750/131722/ffffff"

def _dummy(symbol: str) -> str:
    ticker = (symbol or "SPY").upper()
    return f"{DUMMY_BASE}&text={ticker}+Chart"

def _shots_base() -> str:
    """
    Resolve the screenshot engine base URL.

    - If SHOTS_BASE_URL is set (e.g., https://legend-shots.onrender.com), use that.
    - Else fallback to localhost with SHOTS_PORT (default 3010).
    """
    base = os.getenv("SHOTS_BASE_URL")
    if base:
        return base.rstrip("/")
    port = int(os.getenv("SHOTS_PORT", "3010"))
    return f"http://127.0.0.1:{port}"

def generate_chart(symbol: str) -> str:
    """
    Return a chart URL for the given symbol.

    - If DRY_RUN=1, return a dummy image URL.
    - Otherwise, call the screenshot engine's /screenshot endpoint and return its chart_url field.
      If anything fails, fall back to a dummy URL.
    """
    ticker = (symbol or "SPY").upper()

    if os.getenv("DRY_RUN") == "1":
        return _dummy(ticker)

    engine = f"{_shots_base()}/screenshot"

    try:
        resp = requests.get(f"{engine}?{urlencode({'symbol': ticker})}", timeout=30)
        resp.raise_for_status()
        data = resp.json()
        url = data.get("chart_url")
        return url if isinstance(url, str) and url else _dummy(ticker)
    except Exception:
        return _dummy(ticker)
