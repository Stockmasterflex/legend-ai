import sys

from daily_market_scanner import run_scan, run_scan_for_symbols, test_finnhub_connection

if __name__ == "__main__":
    # Usage:
    #   python trigger_scan.py                 -> full scan
    #   python trigger_scan.py test            -> finnhub connectivity test
    #   python trigger_scan.py subset AAPL,MSFT,NVDA
    if len(sys.argv) == 1:
        run_scan()
    elif sys.argv[1] == 'test':
        test_finnhub_connection()
    elif sys.argv[1] == 'subset' and len(sys.argv) > 2:
        symbols = [s.strip().upper() for s in sys.argv[2].split(',') if s.strip()]
        run_scan_for_symbols(symbols)
    else:
        print("Usage: python trigger_scan.py [test | subset TICKER1,TICKER2,...]")


