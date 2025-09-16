import json
from typing import List
from indicators.ta import compute_all_indicators
from signals.core import score_from_indicators
from service_api import yf_history_cached

UNIVERSE: List[str] = ["NVDA", "TSLA", "AAPL"]

def main():
    out = {}
    for sym in UNIVERSE:
        df = yf_history_cached(sym, period="6mo")
        ind = compute_all_indicators(df) if not df.empty else {}
        sig = score_from_indicators(ind, df) if ind else {"score": 0, "reasons": ["no_data"], "badges": []}
        out[sym] = {"indicators": ind, "signal": sig}
    print(json.dumps(out, indent=2))
    with open("/tmp/legend_signals.json", "w") as f:
        json.dump(out, f, indent=2)

if __name__ == "__main__":
    main()

