"""
Copies rows from local SQLite 'legendai.db' table 'patterns' into TimescaleDB,
idempotently (ON CONFLICT DO NOTHING). Requires env: SQLITE_PATH, DATABASE_URL.
"""

import os

import pandas as pd
import sqlalchemy as sa

SQLITE_PATH = os.getenv("SQLITE_PATH", "legendai.db")
PG_URL = os.getenv("DATABASE_URL")
if not PG_URL:
    raise SystemExit("DATABASE_URL is required (postgresql+psycopg2://...)")

src = sa.create_engine(f"sqlite:///{SQLITE_PATH}", future=True)
dst = sa.create_engine(PG_URL, future=True)

with src.connect() as c:
    df = pd.read_sql("SELECT * FROM patterns", c)

with dst.begin() as conn:
    df.to_sql("__tmp_patterns", conn, if_exists="replace", index=False)
    conn.execute(sa.text(
        """
        INSERT INTO patterns SELECT * FROM __tmp_patterns
        ON CONFLICT (ticker, pattern, as_of) DO NOTHING;
        DROP TABLE __tmp_patterns;
        """
    ))

with dst.connect() as c:
    total = c.execute(sa.text("SELECT count(*) FROM patterns")).scalar()
print("Timescale rows:", total)


