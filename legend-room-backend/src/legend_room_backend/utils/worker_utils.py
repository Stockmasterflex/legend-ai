# Importing scanner_utils as 'scanner' for better clarity and maintainability,
# ensuring the module name reflects its purpose.
import scanner_utils as scanner
import database
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
import pandas as pd
from datetime import datetime

# The list of stocks our worker will fetch data for.
# You can expand this list over time.
TICKERS_TO_FETCH = ["SPY", "AAPL", "MSFT", "GOOG", "AMZN", "NVDA", "TSLA", "META", "SMCI"]

def run_worker():
    """The main function for the background worker."""
    print("Starting data fetch worker...")
    
    # Get a database session
    db: Session = next(database.get_db())
    
    for ticker in TICKERS_TO_FETCH:
        for interval in ["1d", "1wk"]:
            print(f"Fetching {interval} data for {ticker}...")
            # Use the robust get_data function from our scanner
            data_df = scanner.get_data(ticker, interval=interval)
            
            if data_df is not None and not data_df.empty:
                print(f"Data fetched for {ticker} ({interval}). Upserting to database...")
                
                # Convert DataFrame to JSON format for storage
                data_json = data_df.to_json(orient='split')
                
                # "Upsert" logic: Insert new data, or update it if it already exists for that ticker/interval
                stmt = insert(database.StockData).values(
                    ticker=ticker,
                    interval=interval,
                    data=data_json,
                    last_fetched=datetime.utcnow()
                ).on_conflict_do_update(
                    index_elements=['ticker', 'interval'],
                    set_=dict(data=data_json, last_fetched=datetime.utcnow())
                )
                
                db.execute(stmt)
                db.commit()
                print(f"Successfully saved data for {ticker} ({interval}).")
            else:
                print(f"Skipping database save for {ticker} ({interval}) due to fetch failure.")
    
    db.close()
    print("Data fetch worker finished.")

if __name__ == "__main__":
    # This allows the script to be run directly
    database.create_all_tables() # Ensure tables exist before running
    run_worker()
