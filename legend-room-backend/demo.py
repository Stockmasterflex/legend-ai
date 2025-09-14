import os
import sys
import pathlib
from urllib.parse import urlencode
import requests

SYMBOL = (len(sys.argv) > 1 and sys.argv[1]) or os.getenv("SYMBOL", "SPY")
PORT = int(os.getenv("SHOTS_PORT", "3010"))
ENGINE = f"http://localhost:{PORT}/screenshot"
SHOTS = pathlib.Path("/Users/kyleholthaus/Projects/LegendAI/legend-room-screenshot-engine")
PNG = SHOTS / "reports" / "SMOKE.png"


def call_engine(symbol: str):
    try:
        r = requests.get(f"{ENGINE}?{urlencode({'symbol': symbol})}", timeout=30)
        r.raise_for_status()
        data = r.json()
        print(f"[engine] {data}")
        # screenshot engine returns 'chart_url'
        return data.get("chart_url")
    except Exception as e:
        print(f"[engine] error: {e}")
        return None


def main():
    print(f"[demo] requesting screenshot for: {SYMBOL}")
    url = call_engine(SYMBOL)
    if PNG.exists():
        print(f"[demo] local PNG: {PNG.resolve()}")
    else:
        print("[demo] no local PNG found (run 'npm run smoke' in shots)")
    if url:
        print(f"[demo] URL from engine: {url}")
    else:
        print("[demo] no URL returned (DRY_RUN likely)")

if __name__ == "__main__":
    main()
