import json
import os
from sentiment.core import fetch_headlines_and_sentiment

UNIVERSE = ["NVDA", "TSLA", "AAPL"]

def main():
    out = {}
    for sym in UNIVERSE:
        out[sym] = fetch_headlines_and_sentiment(sym, limit=5)
    print(json.dumps(out, indent=2))
    with open("/tmp/legend_sentiment.json", "w") as f:
        json.dump(out, f, indent=2)

if __name__ == "__main__":
    if not os.getenv("NEWSAPI_KEY"):
        print("Note: NEWSAPI_KEY not set; returning neutral samples.")
    main()

