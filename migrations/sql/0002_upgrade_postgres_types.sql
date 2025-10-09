-- Upgrade PostgreSQL-specific types (run this ONLY on PostgreSQL, not SQLite)
-- This migration converts TEXT meta to JSONB and TIMESTAMP to TIMESTAMPTZ

-- Step 1: Convert meta column from TEXT to JSONB
-- This assumes meta contains valid JSON strings
DO $$
BEGIN
    -- Check if meta is already JSONB
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'patterns' 
        AND column_name = 'meta' 
        AND data_type != 'jsonb'
    ) THEN
        -- Convert TEXT to JSONB
        ALTER TABLE patterns 
        ALTER COLUMN meta TYPE JSONB 
        USING CASE 
            WHEN meta IS NULL THEN NULL
            WHEN meta = '' THEN '{}'::jsonb
            ELSE meta::jsonb
        END;
        
        RAISE NOTICE 'Converted meta column to JSONB';
    ELSE
        RAISE NOTICE 'meta column is already JSONB, skipping';
    END IF;
END $$;

-- Step 2: Convert as_of from TIMESTAMP to TIMESTAMPTZ
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'patterns' 
        AND column_name = 'as_of' 
        AND data_type = 'timestamp without time zone'
    ) THEN
        ALTER TABLE patterns 
        ALTER COLUMN as_of TYPE TIMESTAMPTZ 
        USING as_of AT TIME ZONE 'UTC';
        
        RAISE NOTICE 'Converted as_of column to TIMESTAMPTZ';
    ELSE
        RAISE NOTICE 'as_of column is already TIMESTAMPTZ, skipping';
    END IF;
END $$;

-- Step 3: Convert created_at from TIMESTAMP to TIMESTAMPTZ
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'patterns' 
        AND column_name = 'created_at' 
        AND data_type = 'timestamp without time zone'
    ) THEN
        ALTER TABLE patterns 
        ALTER COLUMN created_at TYPE TIMESTAMPTZ 
        USING created_at AT TIME ZONE 'UTC';
        
        RAISE NOTICE 'Converted created_at column to TIMESTAMPTZ';
    ELSE
        RAISE NOTICE 'created_at column is already TIMESTAMPTZ, skipping';
    END IF;
END $$;

-- Step 4: Create GIN index on meta for fast JSON queries
CREATE INDEX IF NOT EXISTS idx_patterns_meta_gin 
ON patterns USING GIN (meta jsonb_path_ops);

RAISE NOTICE 'PostgreSQL type upgrade complete!';

