-- Create patterns table for storing technical pattern detections
-- Compatible with both PostgreSQL (JSONB, TIMESTAMPTZ) and SQLite (TEXT, TIMESTAMP)
CREATE TABLE IF NOT EXISTS patterns (
    ticker TEXT NOT NULL,
    pattern TEXT NOT NULL,
    as_of TIMESTAMP NOT NULL,  -- Use TIMESTAMP for SQLite compatibility
    confidence REAL,            -- REAL is compatible with both
    rs REAL,
    price REAL,
    meta TEXT,                  -- Use TEXT for SQLite; PostgreSQL can cast to JSONB
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticker, pattern, as_of)
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_patterns_asof ON patterns (as_of DESC);
CREATE INDEX IF NOT EXISTS idx_patterns_ticker_asof ON patterns (ticker, as_of DESC);
CREATE INDEX IF NOT EXISTS idx_patterns_pattern ON patterns (pattern);

-- Note: For PostgreSQL production, consider:
-- 1. Converting meta column to JSONB: ALTER TABLE patterns ALTER COLUMN meta TYPE JSONB USING meta::jsonb;
-- 2. Converting timestamps to TIMESTAMPTZ: ALTER TABLE patterns ALTER COLUMN as_of TYPE TIMESTAMPTZ;
-- 3. Adding GIN index on meta: CREATE INDEX idx_patterns_meta_gin ON patterns USING GIN (meta jsonb_path_ops);

