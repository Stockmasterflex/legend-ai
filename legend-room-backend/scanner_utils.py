import yfinance as yf
import pandas as pd
import investpy
from alpha_vantage.timeseries import TimeSeries
import os
from datetime import datetime, timedelta
from cachetools import TTLCache

data_cache = TTLCache(maxsize=100, ttl=600)

def _clean_and_validate_df(df: pd.DataFrame, ticker: str, source: str = "unknown") -> pd.DataFrame:
    if not isinstance(df, pd.DataFrame) or df.empty: return pd.DataFrame()
    df = df.copy()
    df.reset_index(inplace=True)
    df.rename(columns={'index': 'Date', 'date': 'Date'}, inplace=True)
    if source == 'alpha_vantage':
        df.rename(columns={'1. open': 'Open', '2. high': 'High', '3. low': 'Low', '4. close': 'Close', '5. volume': 'Volume'}, inplace=True)
    cols_to_validate = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    if not all(col in df.columns for col in cols_to_validate): return pd.DataFrame()
    df['Date'] = pd.to_datetime(df['Date'])
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df.dropna(inplace=True)
    df.set_index('Date', inplace=True)
    return df

def _get_from_yfinance(ticker: str, interval: str) -> pd.DataFrame:
    period = "2y" if interval == "1wk" else "1y"
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)
    return _clean_and_validate_df(df, ticker, "yfinance")

def _get_from_investpy(ticker: str) -> pd.DataFrame:
    end_date, start_date = datetime.now(), datetime.now() - timedelta(days=365)
    df = investpy.get_stock_historical_data(stock=ticker, country='united states', from_date=start_date.strftime('%d/%m/%Y'), to_date=end_date.strftime('%d/%m/%Y'))
    return _clean_and_validate_df(df, ticker, "investpy")

def _get_from_alpha_vantage(ticker: str, interval: str) -> pd.DataFrame:
    api_key = os.getenv("ALPHA_VANTAGE_KEY")
    if not api_key: return pd.DataFrame()
    ts = TimeSeries(key=api_key, output_format='pandas')
    df, _ = ts.get_weekly(symbol=ticker) if interval == "1wk" else ts.get_daily(symbol=ticker, outputsize='full')
    return _clean_and_validate_df(df, ticker, "alpha_vantage")

def get_data(ticker: str, interval: str = "1d") -> pd.DataFrame:
    cache_key = f"{ticker}_{interval}"
    if cache_key in data_cache:
        print(f"Returning cached {interval} data for {ticker}.")
        return data_cache[cache_key]
    
    fetchers = [
        lambda: _get_from_yfinance(ticker, interval),
        lambda: _get_from_investpy(ticker) if interval == "1d" and ticker.upper() != "SPY" else pd.DataFrame(),
        lambda: _get_from_alpha_vantage(ticker, interval)
    ]
    for i, fetcher in enumerate(fetchers):
        try:
            df = fetcher()
            if df is not None and isinstance(df, pd.DataFrame) and len(df) >= 10:
                print(f"Success from data source #{i + 1} for {ticker}.")
                data_cache[cache_key] = df
                return df
        except Exception as e:
            print(f"Data source #{i + 1} failed for {ticker}: {e}")
            continue
    print(f"All data sources failed for {ticker}.")
    return pd.DataFrame()
