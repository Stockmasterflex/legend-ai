"""Universe loader utilities for scanner endpoints."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Literal
import os

UniverseName = Literal["sp500", "nasdaq100"]

_REPO_ROOT = Path(__file__).resolve().parent
_DATA_ROOT = _REPO_ROOT / "data" / "universe"

# Mapping from universe name to default data file.
_UNIVERSE_FILES = {
    "sp500": _DATA_ROOT / "sp500.txt",
    "nasdaq100": _DATA_ROOT / "nasdaq100.txt",
}

# Optional override for expanded NASDAQ universe. Future-proofed so adding a
# `nasdaq100_full.txt` file automatically becomes selectable via env toggle.
_EXPANDED_NASDAQ_FILES = [
    _DATA_ROOT / "nasdaq100_full.txt",
    _DATA_ROOT / "nasdaq_full.txt",
]


def _normalize_symbols(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for raw in items:
        symbol = raw.strip().upper()
        if not symbol or symbol.startswith("#"):
            continue
        symbol = symbol.replace(".", "-")
        if symbol.isascii() and symbol not in seen:
            seen.add(symbol)
            out.append(symbol)
    return out


def _load_file(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"Universe file missing: {path}")
    data = path.read_text(encoding="utf-8").splitlines()
    return _normalize_symbols(data)


@lru_cache(maxsize=8)
def get_universe(name: UniverseName) -> List[str]:
    """Return the requested universe as a list of uppercase tickers."""
    key = name.lower()
    if key not in _UNIVERSE_FILES:
        raise ValueError(f"Unsupported universe: {name}")

    path = _UNIVERSE_FILES[key]

    if key == "nasdaq100" and os.getenv("EXPAND_NASDAQ") in {"1", "true", "True"}:  # pragma: no cover - env-driven
        for candidate in _EXPANDED_NASDAQ_FILES:
            if candidate.exists():
                path = candidate
                break

    tickers = _load_file(path)
    if not tickers:
        raise ValueError(f"Universe {name} is empty")
    return tickers


__all__ = ["get_universe", "UniverseName"]
