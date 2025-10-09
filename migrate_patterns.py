import json
import os
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

SQLITE_PATH = os.getenv("SQLITE_PATH", os.path.abspath("legendai.db"))
RAW_POSTGRES_URL = os.getenv(
    "TIMESCALE_DATABASE_URL",
    os.getenv(
        "DATABASE_URL",
        "postgres://tsdbadmin:svcse15kzcdre6e8@ok2ig4hlfo.qajnoj2za7.tsdb.cloud.timescale.com:39031/tsdb?sslmode=require",
    ),
)

# Normalize scheme for SQLAlchemy 2.x
POSTGRES_URL = (
    RAW_POSTGRES_URL.replace("postgres://", "postgresql+psycopg2://", 1)
    if RAW_POSTGRES_URL.startswith("postgres://")
    else RAW_POSTGRES_URL
)


def get_engine(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True)


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS patterns (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10),
    pattern_type VARCHAR(50),
    confidence DOUBLE PRECISION,
    pivot_price DOUBLE PRECISION,
    stop_loss DOUBLE PRECISION,
    days_in_pattern INTEGER,
    pattern_data JSONB,
    detected_at TIMESTAMPTZ,
    status VARCHAR(20)
);
CREATE INDEX IF NOT EXISTS ix_patterns_symbol ON patterns(symbol);
"""


def fetch_sqlite_rows(sqlite_engine: Engine):
    with sqlite_engine.connect() as conn:
        result = conn.execute(text(
            """
            SELECT symbol, pattern_type, confidence, pivot_price, stop_loss,
                   days_in_pattern, pattern_data, detected_at, status
            FROM patterns
            """
        ))
        rows = []
        for r in result:
            pattern_data = r.pattern_data
            if isinstance(pattern_data, str):
                try:
                    pattern_data = json.loads(pattern_data)
                except Exception:
                    # keep as string if invalid JSON
                    pass
            detected_at = r.detected_at
            if isinstance(detected_at, str):
                try:
                    detected_at = datetime.fromisoformat(detected_at)
                except Exception:
                    detected_at = None
            rows.append({
                "symbol": r.symbol,
                "pattern_type": r.pattern_type,
                "confidence": r.confidence,
                "pivot_price": r.pivot_price,
                "stop_loss": r.stop_loss,
                "days_in_pattern": r.days_in_pattern,
                "pattern_data": pattern_data,
                "detected_at": detected_at,
                "status": r.status,
            })
        return rows


def upsert_postgres(pg_engine: Engine, rows):
    with pg_engine.begin() as conn:
        conn.execute(text(CREATE_TABLE_SQL))
        # Clear existing to avoid duplicates for this one-time migration
        conn.execute(text("DELETE FROM patterns"))
        insert_sql = text(
            """
            INSERT INTO patterns (
                symbol, pattern_type, confidence, pivot_price, stop_loss,
                days_in_pattern, pattern_data, detected_at, status
            ) VALUES (
                :symbol, :pattern_type, :confidence, :pivot_price, :stop_loss,
                :days_in_pattern, CAST(:pattern_data AS JSONB), :detected_at, :status
            )
            """
        )
        for row in rows:
            pattern_json = row["pattern_data"]
            if isinstance(pattern_json, (dict, list)):
                pattern_json = json.dumps(pattern_json)
            conn.execute(insert_sql, {
                "symbol": row["symbol"],
                "pattern_type": row["pattern_type"],
                "confidence": row["confidence"],
                "pivot_price": row["pivot_price"],
                "stop_loss": row["stop_loss"],
                "days_in_pattern": row["days_in_pattern"],
                "pattern_data": pattern_json,
                "detected_at": row["detected_at"],
                "status": row["status"],
            })


def count_postgres(pg_engine: Engine) -> int:
    with pg_engine.connect() as conn:
        res = conn.execute(text("SELECT COUNT(*) FROM patterns"))
        return int(res.scalar() or 0)


def main():
    print(f"Using SQLite at: {SQLITE_PATH}")
    print(f"Using TimescaleDB URL: {POSTGRES_URL.split('@')[-1]}")

    sqlite_engine = get_engine(f"sqlite:///{SQLITE_PATH}")
    pg_engine = get_engine(POSTGRES_URL)

    rows = fetch_sqlite_rows(sqlite_engine)
    print(f"Fetched {len(rows)} rows from SQLite patterns")

    upsert_postgres(pg_engine, rows)
    total = count_postgres(pg_engine)
    print(f"Timescale patterns count: {total}")


if __name__ == "__main__":
    main()


