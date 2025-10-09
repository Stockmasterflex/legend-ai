from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

from sqlalchemy import text
from sqlalchemy.engine import Engine


def upsert_patterns(engine: Engine, rows: List[Dict]) -> None:
    if not rows:
        return
    cols = list(rows[0].keys())
    keys = ",".join(cols)
    placeholders = ",".join([f":{c}" for c in cols])
    conflict = "(ticker, pattern, as_of)"
    set_expr = ", ".join(
        [f"{c}=EXCLUDED.{c}" for c in cols if c not in ("ticker", "pattern", "as_of")]
    )
    sql = text(
        f"INSERT INTO patterns ({keys}) VALUES ({placeholders}) ON CONFLICT {conflict} DO UPDATE SET {set_expr}"
    )
    with engine.begin() as conn:
        conn.execute(sql, rows)


def load_universe() -> List[str]:
    p = Path("data/universe.csv")
    if p.exists():
        tickers: List[str] = []
        with p.open() as f:
            for row in csv.reader(f):
                for cell in row:
                    sym = cell.strip()
                    if sym:
                        tickers.append(sym)
        return tickers
    # fallback small universe
    return ["AAPL", "MSFT", "NVDA", "AMZN", "TSLA"]
