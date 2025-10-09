"""Simple feature flag parser for Legend AI.

Read LEGEND_FLAGS env var as a comma-separated list and expose as a set.
"""

import os
from typing import Set


def get_flags() -> Set[str]:
    raw = os.getenv("LEGEND_FLAGS", "")
    return {f.strip() for f in raw.split(",") if f.strip()}
