"""Centralized application settings for Legend AI.

Reads environment variables and provides typed accessors for the VCP detector
and demo behavior flags. Defaults are safe for production.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _get_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip() in {"1", "true", "True", "yes", "on"}


@dataclass(frozen=True)
class VCPSettings:
    min_dryup_ratio: float = 0.60
    max_base_depth: float = 0.40
    min_tighten_steps: int = 3
    max_final_range: float = 0.10
    pivot_window: int = 7
    breakout_volx: float = 1.8


def load_vcp_settings() -> VCPSettings:
    return VCPSettings(
        min_dryup_ratio=_get_float("VCP_MIN_DRYUP", 0.60),
        max_base_depth=_get_float("VCP_MAX_BASE_DEPTH", 0.40),
        min_tighten_steps=_get_int("VCP_MIN_TIGHTEN_STEPS", 3),
        max_final_range=_get_float("VCP_MAX_FINAL_RANGE", 0.10),
        pivot_window=_get_int("VCP_PIVOT_WINDOW", 7),
        breakout_volx=_get_float("VCP_BREAKOUT_VOLX", 1.8),
    )


def is_mock_enabled() -> bool:
    return _get_bool("LEGEND_MOCK", False)


