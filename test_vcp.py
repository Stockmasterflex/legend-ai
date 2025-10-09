import yfinance as yf

from vcp_ultimate_algorithm import VCPDetector

symbol = 'NVDA'
print(f"Fetching {symbol}...")
hist = yf.Ticker(symbol).history(period='1y', interval='1d', auto_adjust=False, actions=False)
print(hist.head())
print(f"Rows: {len(hist)}")

print("Running VCP detector...")
detector = VCPDetector()
signal = detector.detect_vcp(hist, symbol)

if signal.detected:
    print(f"VCP detected! Confidence: {signal.confidence_score:.1f}% Contractions: {len(signal.contractions)} Pivot: {signal.pivot_price:.2f}")
else:
    print("No VCP detected")
