
import yfinance as yf

from vcp_ultimate_algorithm import VCPDetector

# Fetch TSLA data covering the VCP period (April - October 2025)
hist = yf.Ticker('TSLA').history(start='2025-01-01', end='2025-10-15', interval='1d', auto_adjust=False, actions=False)

detector = VCPDetector(
    min_price=10.0,
    min_volume=500000,
    min_contractions=2,
    max_contractions=6,
    max_base_depth=0.35,
    final_contraction_max=0.10
)

signal = detector.detect_vcp(hist, 'TSLA')

print(f"VCP Detected: {signal.detected}")
if signal.detected:
    print(f"Confidence: {signal.confidence_score}")
    print(f"Contractions: {len(signal.contractions)}")
    print(f"Pivot: ${signal.pivot_price:.2f}")
else:
    print("Pattern not detected")
    print(f"Notes: {signal.notes}")
