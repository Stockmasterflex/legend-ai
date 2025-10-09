# Generate comprehensive sample trading data for the Legend AI platform
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# Set random seed for reproducibility
np.random.seed(42)
random.seed(42)

# Generate sample stock data with realistic patterns
def generate_stock_data(symbol, sector, industry, days=252):
    """Generate realistic OHLCV data with pattern formations"""
    
    # Base parameters
    base_price = random.uniform(20, 150)
    volatility = random.uniform(0.15, 0.35)
    trend = random.uniform(-0.02, 0.08)  # Daily trend
    
    dates = [datetime.now() - timedelta(days=days-i) for i in range(days)]
    
    # Generate price series with realistic movements
    prices = []
    volumes = []
    
    current_price = base_price
    
    for i, date in enumerate(dates):
        # Add trend and random walk
        daily_return = np.random.normal(trend, volatility)
        current_price *= (1 + daily_return)
        
        # Generate OHLC from daily return
        daily_vol = volatility * random.uniform(0.5, 1.5)
        high = current_price * (1 + abs(daily_vol * random.uniform(0.2, 0.8)))
        low = current_price * (1 - abs(daily_vol * random.uniform(0.2, 0.8)))
        open_price = current_price * (1 + daily_return * random.uniform(-0.5, 0.5))
        close_price = current_price
        
        # Ensure OHLC logic is maintained
        high = max(high, open_price, close_price)
        low = min(low, open_price, close_price)
        
        # Volume with realistic patterns
        avg_volume = random.randint(500000, 5000000)
        volume = int(avg_volume * (1 + random.uniform(-0.5, 2.0)))
        
        prices.append({
            'Date': date.strftime('%Y-%m-%d'),
            'Open': round(open_price, 2),
            'High': round(high, 2),
            'Low': round(low, 2),
            'Close': round(close_price, 2),
            'Volume': volume
        })
        
        volumes.append(volume)
    
    return pd.DataFrame(prices), current_price

# Define stock universe with sectors and industries
stock_universe = [
    # Technology
    {'symbol': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Technology', 'industry': 'Consumer Electronics'},
    {'symbol': 'MSFT', 'name': 'Microsoft Corp.', 'sector': 'Technology', 'industry': 'Software'},
    {'symbol': 'NVDA', 'name': 'NVIDIA Corp.', 'sector': 'Technology', 'industry': 'Semiconductors'},
    {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'sector': 'Technology', 'industry': 'Internet'},
    {'symbol': 'AMZN', 'name': 'Amazon.com Inc.', 'sector': 'Technology', 'industry': 'E-commerce'},
    {'symbol': 'META', 'name': 'Meta Platforms Inc.', 'sector': 'Technology', 'industry': 'Social Media'},
    {'symbol': 'TSLA', 'name': 'Tesla Inc.', 'sector': 'Technology', 'industry': 'Electric Vehicles'},
    {'symbol': 'CRM', 'name': 'Salesforce Inc.', 'sector': 'Technology', 'industry': 'Cloud Software'},
    {'symbol': 'ADBE', 'name': 'Adobe Inc.', 'sector': 'Technology', 'industry': 'Software'},
    {'symbol': 'NFLX', 'name': 'Netflix Inc.', 'sector': 'Technology', 'industry': 'Streaming'},
    
    # Healthcare/Biotech
    {'symbol': 'JNJ', 'name': 'Johnson & Johnson', 'sector': 'Healthcare', 'industry': 'Pharmaceuticals'},
    {'symbol': 'UNH', 'name': 'UnitedHealth Group', 'sector': 'Healthcare', 'industry': 'Health Insurance'},
    {'symbol': 'PFE', 'name': 'Pfizer Inc.', 'sector': 'Healthcare', 'industry': 'Pharmaceuticals'},
    {'symbol': 'MRNA', 'name': 'Moderna Inc.', 'sector': 'Healthcare', 'industry': 'Biotechnology'},
    {'symbol': 'ABBV', 'name': 'AbbVie Inc.', 'sector': 'Healthcare', 'industry': 'Pharmaceuticals'},
    {'symbol': 'TMO', 'name': 'Thermo Fisher Scientific', 'sector': 'Healthcare', 'industry': 'Life Sciences'},
    
    # Finance
    {'symbol': 'JPM', 'name': 'JPMorgan Chase & Co.', 'sector': 'Financial', 'industry': 'Banking'},
    {'symbol': 'BAC', 'name': 'Bank of America Corp.', 'sector': 'Financial', 'industry': 'Banking'},
    {'symbol': 'WFC', 'name': 'Wells Fargo & Co.', 'sector': 'Financial', 'industry': 'Banking'},
    {'symbol': 'GS', 'name': 'Goldman Sachs Group', 'sector': 'Financial', 'industry': 'Investment Banking'},
    {'symbol': 'MS', 'name': 'Morgan Stanley', 'sector': 'Financial', 'industry': 'Investment Banking'},
    {'symbol': 'V', 'name': 'Visa Inc.', 'sector': 'Financial', 'industry': 'Payment Processing'},
    {'symbol': 'MA', 'name': 'Mastercard Inc.', 'sector': 'Financial', 'industry': 'Payment Processing'},
    
    # Consumer
    {'symbol': 'WMT', 'name': 'Walmart Inc.', 'sector': 'Consumer Discretionary', 'industry': 'Retail'},
    {'symbol': 'HD', 'name': 'Home Depot Inc.', 'sector': 'Consumer Discretionary', 'industry': 'Home Improvement'},
    {'symbol': 'MCD', 'name': 'McDonald\'s Corp.', 'sector': 'Consumer Discretionary', 'industry': 'Restaurants'},
    {'symbol': 'NKE', 'name': 'Nike Inc.', 'sector': 'Consumer Discretionary', 'industry': 'Apparel'},
    {'symbol': 'SBUX', 'name': 'Starbucks Corp.', 'sector': 'Consumer Discretionary', 'industry': 'Restaurants'},
    {'symbol': 'KO', 'name': 'Coca-Cola Co.', 'sector': 'Consumer Staples', 'industry': 'Beverages'},
    {'symbol': 'PG', 'name': 'Procter & Gamble Co.', 'sector': 'Consumer Staples', 'industry': 'Household Products'},
    
    # Energy
    {'symbol': 'XOM', 'name': 'Exxon Mobil Corp.', 'sector': 'Energy', 'industry': 'Oil & Gas'},
    {'symbol': 'CVX', 'name': 'Chevron Corp.', 'sector': 'Energy', 'industry': 'Oil & Gas'},
    {'symbol': 'COP', 'name': 'ConocoPhillips', 'sector': 'Energy', 'industry': 'Oil & Gas'},
    
    # Industrial
    {'symbol': 'BA', 'name': 'Boeing Co.', 'sector': 'Industrials', 'industry': 'Aerospace'},
    {'symbol': 'CAT', 'name': 'Caterpillar Inc.', 'sector': 'Industrials', 'industry': 'Heavy Machinery'},
    {'symbol': 'GE', 'name': 'General Electric Co.', 'sector': 'Industrials', 'industry': 'Conglomerate'},
    
    # Emerging Growth Stocks
    {'symbol': 'PLTR', 'name': 'Palantir Technologies', 'sector': 'Technology', 'industry': 'Data Analytics'},
    {'symbol': 'SNOW', 'name': 'Snowflake Inc.', 'sector': 'Technology', 'industry': 'Cloud Data'},
    {'symbol': 'ZM', 'name': 'Zoom Video Communications', 'sector': 'Technology', 'industry': 'Video Conferencing'},
    {'symbol': 'ROKU', 'name': 'Roku Inc.', 'sector': 'Technology', 'industry': 'Streaming Hardware'},
    {'symbol': 'SQ', 'name': 'Block Inc.', 'sector': 'Financial', 'industry': 'Fintech'},
    {'symbol': 'PYPL', 'name': 'PayPal Holdings Inc.', 'sector': 'Financial', 'industry': 'Digital Payments'},
]

print(f"Generating data for {len(stock_universe)} stocks...")

# Generate market data and patterns for each stock
all_market_data = {}
pattern_detections = []
relative_strength_data = []

for stock in stock_universe:
    symbol = stock['symbol']
    
    # Generate OHLCV data
    df, current_price = generate_stock_data(symbol, stock['sector'], stock['industry'])
    all_market_data[symbol] = {
        'info': stock,
        'data': df.to_dict('records'),
        'current_price': current_price
    }
    
    # Generate pattern detection results
    patterns_for_stock = []
    
    # VCP Pattern Detection
    if random.random() < 0.15:  # 15% chance of VCP
        vcp_confidence = random.uniform(0.7, 0.95)
        patterns_for_stock.append({
            'type': 'VCP',
            'confidence': round(vcp_confidence, 2),
            'stage': random.choice(['Stage 1', 'Stage 2', 'Stage 3']),
            'contractions': random.randint(3, 6),
            'days_in_pattern': random.randint(15, 45),
            'pivot_price': round(current_price * random.uniform(1.02, 1.08), 2),
            'stop_loss': round(current_price * random.uniform(0.92, 0.96), 2)
        })
    
    # Cup & Handle Pattern
    if random.random() < 0.12:  # 12% chance of Cup & Handle
        ch_confidence = random.uniform(0.65, 0.90)
        patterns_for_stock.append({
            'type': 'Cup & Handle',
            'confidence': round(ch_confidence, 2),
            'cup_depth': round(random.uniform(15, 35), 1),
            'handle_depth': round(random.uniform(8, 18), 1),
            'days_in_pattern': random.randint(30, 120),
            'pivot_price': round(current_price * random.uniform(1.03, 1.10), 2),
            'stop_loss': round(current_price * random.uniform(0.90, 0.95), 2)
        })
    
    # Bull Flag Pattern
    if random.random() < 0.18:  # 18% chance of Bull Flag
        bf_confidence = random.uniform(0.60, 0.85)
        patterns_for_stock.append({
            'type': 'Bull Flag',
            'confidence': round(bf_confidence, 2),
            'flag_pole_gain': round(random.uniform(20, 60), 1),
            'flag_depth': round(random.uniform(5, 15), 1),
            'days_in_pattern': random.randint(5, 25),
            'pivot_price': round(current_price * random.uniform(1.02, 1.06), 2),
            'stop_loss': round(current_price * random.uniform(0.94, 0.98), 2)
        })
    
    # Flat Base Pattern
    if random.random() < 0.10:  # 10% chance of Flat Base
        fb_confidence = random.uniform(0.70, 0.88)
        patterns_for_stock.append({
            'type': 'Flat Base',
            'confidence': round(fb_confidence, 2),
            'base_tightness': round(random.uniform(8, 15), 1),
            'days_in_pattern': random.randint(20, 60),
            'pivot_price': round(current_price * random.uniform(1.01, 1.05), 2),
            'stop_loss': round(current_price * random.uniform(0.92, 0.97), 2)
        })
    
    # Ascending Triangle
    if random.random() < 0.14:  # 14% chance of Ascending Triangle
        at_confidence = random.uniform(0.65, 0.85)
        patterns_for_stock.append({
            'type': 'Ascending Triangle',
            'confidence': round(at_confidence, 2),
            'resistance_tests': random.randint(3, 6),
            'days_in_pattern': random.randint(20, 50),
            'pivot_price': round(current_price * random.uniform(1.03, 1.08), 2),
            'stop_loss': round(current_price * random.uniform(0.93, 0.97), 2)
        })
    
    # Add pattern detection data
    for pattern in patterns_for_stock:
        pattern_detections.append({
            'symbol': symbol,
            'name': stock['name'],
            'sector': stock['sector'],
            'industry': stock['industry'],
            'current_price': current_price,
            'market_cap': random.choice(['Small', 'Mid', 'Large', 'Mega']),
            **pattern
        })
    
    # Generate Relative Strength data
    sp500_performance = random.uniform(-10, 25)  # S&P 500 performance
    stock_performance = sp500_performance + random.uniform(-15, 40)  # Stock vs market
    rs_rating = min(99, max(1, int(50 + (stock_performance - sp500_performance) * 2)))
    
    relative_strength_data.append({
        'symbol': symbol,
        'name': stock['name'],
        'sector': stock['sector'],
        'industry': stock['industry'],
        'current_price': current_price,
        'rs_rating': rs_rating,
        'ytd_performance': round(stock_performance, 1),
        'sp500_performance': round(sp500_performance, 1),
        'relative_performance': round(stock_performance - sp500_performance, 1),
        'sector_rank': random.randint(1, 100),
        'industry_rank': random.randint(1, 50)
    })

print(f"Generated {len(pattern_detections)} pattern detections")
print(f"Generated relative strength data for {len(relative_strength_data)} stocks")

# Create pattern summary
pattern_summary = {}
for detection in pattern_detections:
    pattern_type = detection['type']
    if pattern_type not in pattern_summary:
        pattern_summary[pattern_type] = 0
    pattern_summary[pattern_type] += 1

print("\nPattern Distribution:")
for pattern, count in pattern_summary.items():
    print(f"  {pattern}: {count} detections")