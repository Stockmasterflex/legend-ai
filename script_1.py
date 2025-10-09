# Generate additional market intelligence and sector data

# Generate sector performance data
sectors = [
    'Technology', 'Healthcare', 'Financial', 'Consumer Discretionary', 
    'Consumer Staples', 'Energy', 'Industrials', 'Materials', 
    'Utilities', 'Real Estate', 'Communication Services'
]

sector_performance = []
for sector in sectors:
    performance = random.uniform(-15, 30)
    sector_performance.append({
        'sector': sector,
        'ytd_performance': round(performance, 1),
        'momentum_score': random.randint(1, 100),
        'rs_rating': random.randint(1, 99),
        'leading_stocks': random.randint(8, 45),
        'avg_volume_change': round(random.uniform(-30, 150), 1)
    })

# Sort by performance for ranking
sector_performance.sort(key=lambda x: x['ytd_performance'], reverse=True)
for i, sector in enumerate(sector_performance):
    sector['rank'] = i + 1

# Generate market environment data
market_data = {
    'current_trend': 'Confirmed Uptrend',
    'days_in_trend': 23,
    'distribution_days': 2,
    'follow_through_date': '2024-08-15',
    'market_health_score': 78,
    'breadth_indicators': {
        'advance_decline_line': 'Strong',
        'new_highs_vs_lows': '245 vs 23',
        'up_volume_ratio': '68%'
    }
}

# Generate portfolio tracking data (sample trades)
portfolio_trades = [
    {
        'symbol': 'NVDA',
        'pattern_type': 'VCP',
        'entry_date': '2024-08-20',
        'entry_price': 118.50,
        'current_price': 128.75,
        'position_size': 200,
        'stop_loss': 112.00,
        'target_price': 145.00,
        'days_held': 8,
        'unrealized_pnl': 2050.00,
        'pnl_percent': 8.6
    },
    {
        'symbol': 'MSFT',
        'pattern_type': 'Cup & Handle',
        'entry_date': '2024-08-18',
        'entry_price': 425.20,
        'current_price': 438.90,
        'position_size': 50,
        'stop_loss': 402.00,
        'target_price': 485.00,
        'days_held': 10,
        'unrealized_pnl': 685.00,
        'pnl_percent': 3.2
    },
    {
        'symbol': 'AAPL',
        'pattern_type': 'Bull Flag',
        'entry_date': '2024-08-22',
        'entry_price': 224.50,
        'current_price': 229.80,
        'position_size': 100,
        'stop_loss': 218.00,
        'target_price': 245.00,
        'days_held': 6,
        'unrealized_pnl': 530.00,
        'pnl_percent': 2.4
    }
]

# Generate performance statistics
performance_stats = {
    'total_trades': 47,
    'winning_trades': 32,
    'losing_trades': 15,
    'win_rate': 68.1,
    'avg_win': 8.4,
    'avg_loss': -4.2,
    'profit_factor': 2.8,
    'sharpe_ratio': 1.65,
    'max_drawdown': -12.3,
    'total_return': 23.7,
    'pattern_performance': {
        'VCP': {'trades': 12, 'win_rate': 75.0, 'avg_return': 9.2},
        'Cup & Handle': {'trades': 8, 'win_rate': 62.5, 'avg_return': 7.8},
        'Bull Flag': {'trades': 15, 'win_rate': 66.7, 'avg_return': 6.4},
        'Flat Base': {'trades': 7, 'win_rate': 71.4, 'avg_return': 8.9},
        'Ascending Triangle': {'trades': 5, 'win_rate': 60.0, 'avg_return': 5.8}
    }
}

# Generate watchlist with high-probability setups
watchlist_stocks = []
high_confidence_patterns = [p for p in pattern_detections if p['confidence'] >= 0.80]

for pattern in high_confidence_patterns[:10]:  # Top 10 high-confidence patterns
    rs_data = next((r for r in relative_strength_data if r['symbol'] == pattern['symbol']), {})
    
    # Calculate Minervini Trend Template score (8 criteria)
    trend_template_score = 0
    if rs_data.get('rs_rating', 0) >= 70: trend_template_score += 1
    if pattern['current_price'] > pattern['current_price'] * 0.95: trend_template_score += 1  # Above 21-day MA (simulated)
    if pattern['current_price'] > pattern['current_price'] * 0.90: trend_template_score += 1  # Above 50-day MA (simulated)
    if pattern['current_price'] > pattern['current_price'] * 0.85: trend_template_score += 1  # Above 150-day MA (simulated)
    if pattern['current_price'] > pattern['current_price'] * 0.80: trend_template_score += 1  # Above 200-day MA (simulated)
    if random.random() > 0.3: trend_template_score += 1  # 21 > 50 MA
    if random.random() > 0.4: trend_template_score += 1  # 50 > 150 MA
    if random.random() > 0.5: trend_template_score += 1  # 150 > 200 MA
    
    watchlist_stocks.append({
        'symbol': pattern['symbol'],
        'name': pattern['name'],
        'sector': pattern['sector'],
        'pattern_type': pattern['type'],
        'confidence': pattern['confidence'],
        'current_price': pattern['current_price'],
        'pivot_price': pattern['pivot_price'],
        'stop_loss': pattern['stop_loss'],
        'rs_rating': rs_data.get('rs_rating', 50),
        'trend_template_score': trend_template_score,
        'risk_reward_ratio': round((pattern['pivot_price'] - pattern['current_price']) / (pattern['current_price'] - pattern['stop_loss']) * 2.5, 1),
        'days_in_pattern': pattern['days_in_pattern']
    })

# Sort watchlist by confidence and RS rating
watchlist_stocks.sort(key=lambda x: (x['confidence'], x['rs_rating']), reverse=True)

print(f"Generated sector performance data for {len(sector_performance)} sectors")
print(f"Created portfolio with {len(portfolio_trades)} active positions")
print(f"Generated watchlist with {len(watchlist_stocks)} high-probability setups")

# Save all data to files for the web application
data_files = {
    'market_data.json': all_market_data,
    'pattern_detections.json': pattern_detections,
    'relative_strength.json': relative_strength_data,
    'sector_performance.json': sector_performance,
    'market_environment.json': market_data,
    'portfolio_trades.json': portfolio_trades,
    'performance_stats.json': performance_stats,
    'watchlist.json': watchlist_stocks
}

# Create combined dataset for the application
combined_data = {
    'market_data': all_market_data,
    'patterns': pattern_detections,
    'relative_strength': relative_strength_data,
    'sectors': sector_performance,
    'market_environment': market_data,
    'portfolio': portfolio_trades,
    'performance': performance_stats,
    'watchlist': watchlist_stocks,
    'meta': {
        'last_updated': datetime.now().isoformat(),
        'total_stocks': len(stock_universe),
        'total_patterns': len(pattern_detections),
        'data_period': '252 trading days'
    }
}

# Save combined data
with open('legend_ai_data.json', 'w') as f:
    json.dump(combined_data, f, indent=2, default=str)

print("\nData Summary:")
print(f"  • {len(all_market_data)} stocks with full OHLCV data")
print(f"  • {len(pattern_detections)} pattern detections across 5 pattern types")
print(f"  • {len(relative_strength_data)} stocks with RS analysis")
print(f"  • {len(sector_performance)} sectors ranked by performance")
print(f"  • {len(portfolio_trades)} active portfolio positions")
print(f"  • {len(watchlist_stocks)} high-confidence watchlist entries")

print("\nTop 5 Watchlist Stocks:")
for i, stock in enumerate(watchlist_stocks[:5]):
    print(f"  {i+1}. {stock['symbol']} - {stock['pattern_type']} ({stock['confidence']:.2f} confidence, RS: {stock['rs_rating']})")