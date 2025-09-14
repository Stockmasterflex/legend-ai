"""
Temporary compatibility shim.

Older code & endpoints still do:

    import scanner
    ...
    result = scanner.analyze(...)

After the repo restructure, the real logic now lives in
src/legend_room_backend/services/pattern_detection_service.py.

This module forwards the old API so the app can boot while we
gradually update the import paths everywhere else.
"""

from typing import Optional, Dict, Any, List
import pandas as pd

# --- wire up to the new service layer ---------------------------------------
from src.legend_room_backend.services.pattern_detection_service import (
    PatternDetectionService,
)

detector = PatternDetectionService()

def analyze(
    ticker: str,
    daily_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    spy_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Back-compat wrapper.
    Returns the first detected pattern (if any) plus basic diagnostics so
    existing API callers don’t break.
    """
    patterns: List[Dict[str, Any]] = detector.detect_all_patterns(
        ticker=ticker, historical_data=daily_df
    ).get("vcp", [])  # you can extend with other lists if needed

    if not patterns:
        return {
            "ticker": ticker,
            "primary_pattern": "None",
            "details": "No recognised pattern (shim).",
            "score": 0,
        }

    primary = patterns[0]
    primary["ticker"] = ticker
    primary.setdefault("score", 50)
    return primary


# everything else that used to be exported from the old scanner.py can be
# stubbed or progressively migrated here.