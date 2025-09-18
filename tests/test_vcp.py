from math import isclose
# Update imports to your actual module paths if different:
from vcp.vcp_detector import (
  clamp_stop_loss, within_52wk_band
)
from signals.patterns import profit_targets_bulkowski

def test_stop_loss_clamped():
    entry, stop = 100.0, 50.0
    assert clamp_stop_loss(entry, stop, max_pct=0.08) == 92.0

def test_within_52wk_band():
    assert within_52wk_band(85, 100, band=0.15) is True
    assert within_52wk_band(70, 100, band=0.15) is False

def test_bulkowski_targets():
    pt = profit_targets_bulkowski(entry=100, cup_depth=0.30, resistance=None)
    assert isclose(pt["cup_depth"], 100 + (0.30*100)*0.618, rel_tol=1e-6)
