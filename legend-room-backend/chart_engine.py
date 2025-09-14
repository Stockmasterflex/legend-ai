import os
import requests
from urllib.parse import urlencode


def generate_chart(symbol: str) -> str:
    """
    Return a chart URL for the given symbol.

    - If DRY_RUN=1, return a dummy image URL.
    - Otherwise, call the local screenshot engine (defaults to port 3010)
      and return its chart_url field. If that fails, fall back to a dummy URL.
    """
    ticker = (symbol or "SPY").upper()

    if os.getenv("DRY_RUN") == "1":
        return f"https://dummyimage.com/1200x750/131722/ffffff&text={ticker}+Chart"

    shots_port = int(os.getenv("SHOTS_PORT", "3010"))
    engine = f"http://127.0.0.1:{shots_port}/screenshot"

    try:
        resp = requests.get(f"{engine}?{urlencode({'symbol': ticker})}", timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("chart_url") or f"https://dummyimage.com/1200x750/131722/ffffff&text={ticker}+Chart"
    except Exception:
        return f"https://dummyimage.com/1200x750/131722/ffffff&text={ticker}+Chart"


