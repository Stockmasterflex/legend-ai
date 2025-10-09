import json
import os
import random
from datetime import datetime, timedelta

from legend_ai_backend import SessionLocal, Stock


def upsert_stock(session, stock_data):
    existing = session.query(Stock).filter(Stock.symbol == stock_data["symbol"]).first()
    timestamp = datetime.utcnow()
    if existing:
        existing.name = stock_data["name"]
        existing.sector = stock_data["sector"]
        existing.industry = stock_data["industry"]
        existing.market_cap = stock_data["market_cap"]
        existing.current_price = stock_data["current_price"]
        existing.rs_rating = stock_data["rs_rating"]
        existing.updated_at = timestamp
    else:
        session.add(
            Stock(
                symbol=stock_data["symbol"],
                name=stock_data["name"],
                sector=stock_data["sector"],
                industry=stock_data["industry"],
                market_cap=stock_data["market_cap"],
                current_price=stock_data["current_price"],
                rs_rating=stock_data["rs_rating"],
                created_at=timestamp,
                updated_at=timestamp,
            )
        )


def generate_mock_ohlcv(symbol: str, start_price: float, days: int = 252):
    """
    Generate simple OHLCV history resembling a random walk around start_price.
    Output format matches get_stock_price_data() expectations.
    """
    data = []
    price = max(1.0, start_price)
    today = datetime.utcnow().date()
    for i in range(days):
        date = today - timedelta(days=(days - 1 - i))
        pct_change = random.gauss(0, 0.01)
        price = max(1.0, price * (1 + pct_change))
        intraday_spread = abs(random.gauss(0, 0.015))
        high = price * (1 + intraday_spread)
        low = price * (1 - intraday_spread)
        volume = random.randint(600_000, 5_000_000)
        data.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "open": round(price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(price, 2),
                "volume": volume,
            }
        )
    return data


def save_price_history(symbol: str, data: list):
    out_dir = os.path.join("data", "price_history")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{symbol}.json")
    with open(out_path, "w") as f:
        json.dump(data, f)


def main():
    session = SessionLocal()
    try:
        stocks = [
            {
                "symbol": "NVDA",
                "name": "NVIDIA Corporation",
                "sector": "Technology",
                "industry": "Semiconductors",
                "market_cap": "3.0T",
                "current_price": 115.25,
                "rs_rating": 95,
            },
            {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "market_cap": "3.5T",
                "current_price": 210.40,
                "rs_rating": 87,
            },
            {
                "symbol": "TSLA",
                "name": "Tesla, Inc.",
                "sector": "Consumer Cyclical",
                "industry": "Auto Manufacturers",
                "market_cap": "900B",
                "current_price": 250.30,
                "rs_rating": 82,
            },
        ]

        for s in stocks:
            upsert_stock(session, s)
            # Extra credit: generate and save mock OHLCV history for potential future use
            history = generate_mock_ohlcv(s["symbol"], s["current_price"])
            save_price_history(s["symbol"], history)

        session.commit()
        print("Seeded stocks!")
    finally:
        session.close()


if __name__ == "__main__":
    main()


