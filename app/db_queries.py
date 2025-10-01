"""
Database query layer for Legend AI API v1 endpoints.

Provides cursor-based pagination over the Timescale-backed `patterns` table and
API status aggregation queries. Designed to be pure functions with type hints.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import List, Optional, Tuple, Dict

from sqlalchemy import text
from sqlalchemy.engine import Engine


def _encode_cursor(as_of_iso: str, ticker: str) -> str:
    payload = {"as_of_iso": as_of_iso, "ticker": ticker}
    return base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")


def _decode_cursor(cursor: Optional[str]) -> Optional[Dict[str, str]]:
    if not cursor:
        return None
    try:
        data = base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8")
        obj = json.loads(data)
        if not isinstance(obj, dict):
            return None
        return {"as_of_iso": obj.get("as_of_iso", ""), "ticker": obj.get("ticker", "")}
    except Exception:
        return None


def fetch_patterns(engine: Engine, limit: int, cursor: Optional[str]) -> Tuple[List[Dict], Optional[str]]:
    """Fetch paginated patterns ordered by (as_of DESC, ticker ASC).

    Returns a tuple (items, next_cursor).
    Each item is a dict containing a subset of pattern columns for API use.
    """
    after = _decode_cursor(cursor)

    where_clause = ""
    params: Dict[str, object] = {"limit": int(limit)}
    if after and after.get("as_of_iso") and after.get("ticker"):
        # For ordering as_of DESC, ticker ASC: next page items satisfy
        # (as_of < last_asof) OR (as_of = last_asof AND ticker > last_ticker)
        where_clause = "WHERE (as_of < :after_as_of) OR (as_of = :after_as_of AND ticker > :after_ticker)"
        params["after_as_of"] = datetime.fromisoformat(after["as_of_iso"])  # type: ignore[arg-type]
        params["after_ticker"] = after["ticker"]

    sql = text(
        f"""
        SELECT ticker, pattern, as_of, confidence, rs, price, meta
        FROM patterns
        {where_clause}
        ORDER BY as_of DESC, ticker ASC
        LIMIT :limit
        """
    )

    rows: List[Dict] = []
    with engine.connect() as conn:
        result = conn.execute(sql, params)
        for r in result.mappings():
            # Handle as_of - can be datetime (PostgreSQL) or string (SQLite)
            as_of_val = r["as_of"]
            if as_of_val is not None:
                as_of_str = as_of_val.isoformat() if hasattr(as_of_val, 'isoformat') else str(as_of_val)
            else:
                as_of_str = None
            
            # Handle meta - can be dict (PostgreSQL jsonb) or string (SQLite text)
            meta_val = r.get("meta")
            if meta_val is not None:
                if isinstance(meta_val, str):
                    # SQLite returns JSON as string - parse it
                    try:
                        meta_dict = json.loads(meta_val) if meta_val else {}
                    except (json.JSONDecodeError, TypeError):
                        meta_dict = {}
                else:
                    # PostgreSQL returns dict directly
                    meta_dict = meta_val
            else:
                meta_dict = {}
            
            rows.append(
                {
                    "ticker": r["ticker"],
                    "pattern": r["pattern"],
                    "as_of": as_of_str,
                    "confidence": float(r["confidence"]) if r["confidence"] is not None else None,
                    "rs": float(r["rs"]) if r.get("rs") is not None else None,
                    "price": float(r["price"]) if r.get("price") is not None else None,
                    "meta": meta_dict,
                }
            )

    next_cursor: Optional[str] = None
    if rows:
        last = rows[-1]
        if last.get("as_of") and last.get("ticker"):
            next_cursor = _encode_cursor(str(last["as_of"]), str(last["ticker"]))

    return rows, next_cursor


def get_status(engine: Engine) -> Dict[str, object]:
    """Return status metadata for the API and UI.

    - last_scan_time: MAX(as_of)
    - rows_total: COUNT(*)
    - patterns_daily_span_days: date span between MIN(as_of) and MAX(as_of)
    - version: API version string
    """
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT MAX(as_of) AS last_as_of,
                       MIN(as_of) AS first_as_of,
                       COUNT(*)   AS total
                FROM patterns
                """
            )
        ).mappings().first()

    last_as_of = row["last_as_of"] if row else None
    first_as_of = row["first_as_of"] if row else None
    total = int(row["total"]) if row and row["total"] is not None else 0

    span_days: Optional[int] = None
    if last_as_of and first_as_of:
        # Handle datetime objects (PostgreSQL) vs strings (SQLite)
        if hasattr(last_as_of, 'days'):
            span_days = (last_as_of - first_as_of).days
        # For SQLite strings, just set None - it's not critical

    # Handle last_as_of - can be datetime or string
    last_scan_str = None
    if last_as_of:
        last_scan_str = last_as_of.isoformat() if hasattr(last_as_of, 'isoformat') else str(last_as_of)

    return {
        "last_scan_time": last_scan_str,
        "rows_total": total,
        "patterns_daily_span_days": span_days,
        "version": "0.1.0",
    }


