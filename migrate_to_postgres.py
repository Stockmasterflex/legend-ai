#!/usr/bin/env python3
"""
Migrate patterns from SQLite to PostgreSQL/TimescaleDB
Copies all 185 patterns from legendai.db to Render PostgreSQL
"""

import os
import sqlite3
from datetime import datetime

from sqlalchemy import create_engine, text


def migrate_patterns():
    """Migrate patterns from SQLite to PostgreSQL"""
    
    print("🔄 Legend AI - SQLite to PostgreSQL Migration")
    print("=" * 60)
    print()
    
    # Get PostgreSQL URL from environment or prompt
    postgres_url = os.environ.get('DATABASE_URL')
    if not postgres_url:
        print("❌ ERROR: DATABASE_URL not found in environment")
        print()
        print("To fix:")
        print("1. Go to Render Dashboard → legend-db")
        print("2. Copy the 'External Database URL'")
        print("3. Run:")
        print("   export DATABASE_URL='your-postgres-url-here'")
        print("   python migrate_to_postgres.py")
        return False
    
    # Fix postgres:// to postgresql:// if needed
    if postgres_url.startswith('postgres://'):
        postgres_url = postgres_url.replace('postgres://', 'postgresql://', 1)
    
    print("📊 Source: legendai.db (SQLite)")
    print(f"📊 Target: {postgres_url[:50]}... (PostgreSQL)")
    print()
    
    try:
        # Connect to SQLite
        print("📖 Reading from SQLite...")
        sqlite_conn = sqlite3.connect('legendai.db')
        sqlite_conn.row_factory = sqlite3.Row
        cursor = sqlite_conn.cursor()
        
        # Get all patterns with proper column mapping
        rows = cursor.execute("""
            SELECT 
                symbol as ticker,
                pattern_type as pattern,
                detected_at as as_of,
                confidence,
                pivot_price as price,
                pattern_data as meta
            FROM patterns
        """).fetchall()
        total_rows = len(rows)
        print(f"   Found: {total_rows} patterns ✅")
        print()
        
        if total_rows == 0:
            print("⚠️  No patterns found in SQLite database")
            return False
        
        # Connect to PostgreSQL
        print("📝 Connecting to PostgreSQL...")
        pg_engine = create_engine(postgres_url)
        
        # Check if table exists, if not create it
        print("🔧 Ensuring patterns table exists...")
        with pg_engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id SERIAL PRIMARY KEY,
                    ticker TEXT NOT NULL,
                    pattern TEXT NOT NULL,
                    as_of TIMESTAMPTZ NOT NULL,
                    confidence FLOAT,
                    rs FLOAT,
                    price NUMERIC,
                    meta JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(ticker, pattern, as_of)
                )
            """))
            conn.commit()
            print("   Table ready ✅")
        print()
        
        # Insert patterns
        print("📥 Migrating patterns...")
        inserted = 0
        updated = 0
        skipped = 0
        
        with pg_engine.begin() as conn:  # Use begin() for auto-commit
            for i, row in enumerate(rows, 1):
                try:
                    # Convert row to dict
                    row_dict = dict(row)
                    
                    # Handle datetime conversion
                    as_of = row_dict.get('as_of')
                    if isinstance(as_of, str):
                        # Parse ISO format timestamp
                        if 'T' in as_of:
                            as_of = as_of  # Already ISO format
                        else:
                            # Convert SQLite datetime to ISO (handle microseconds)
                            try:
                                # Try with microseconds first
                                dt = datetime.strptime(as_of, '%Y-%m-%d %H:%M:%S.%f')
                            except ValueError:
                                # Fall back to no microseconds
                                dt = datetime.strptime(as_of, '%Y-%m-%d %H:%M:%S')
                            as_of = dt.isoformat()
                    
                    # Prepare meta as proper JSON string
                    meta_str = row_dict.get('meta', '{}')
                    if not isinstance(meta_str, str):
                        meta_str = '{}'
                    
                    # Default RS to 50.0 if not available
                    rs_value = 50.0  # Placeholder since old schema doesn't have RS
                    
                    # Upsert query (fixed parameter style) - removed updated_at since it doesn't exist
                    result = conn.execute(text("""
                        INSERT INTO patterns (ticker, pattern, as_of, confidence, rs, price, meta)
                        VALUES (:ticker, :pattern, :as_of, :confidence, :rs, :price, CAST(:meta AS jsonb))
                        ON CONFLICT (ticker, pattern, as_of) 
                        DO UPDATE SET
                            confidence = EXCLUDED.confidence,
                            rs = EXCLUDED.rs,
                            price = EXCLUDED.price,
                            meta = EXCLUDED.meta
                    """), {
                        'ticker': row_dict.get('ticker'),
                        'pattern': row_dict.get('pattern'),
                        'as_of': as_of,
                        'confidence': row_dict.get('confidence'),
                        'rs': rs_value,
                        'price': row_dict.get('price'),
                        'meta': meta_str
                    })
                    
                    # Count as inserted (ON CONFLICT will handle updates)
                    inserted += 1
                    
                    # Progress indicator
                    if i % 10 == 0:
                        print(f"   Progress: {i}/{total_rows} ({(i/total_rows*100):.0f}%)")
                
                except Exception as e:
                    print(f"   ⚠️  Skipped row {i}: {e}")
                    skipped += 1
                    continue
        
        print()
        print("✅ Migration complete!")
        print()
        print(f"   Inserted: {inserted}")
        print(f"   Updated:  {updated}")
        print(f"   Skipped:  {skipped}")
        print(f"   Total:    {inserted + updated}")
        print()
        
        # Verify
        print("🔍 Verifying PostgreSQL...")
        with pg_engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) as count FROM patterns"))
            pg_count = result.fetchone()[0]
            print(f"   Patterns in PostgreSQL: {pg_count} ✅")
        print()
        
        if pg_count == total_rows:
            print("🎉 SUCCESS! All patterns migrated successfully!")
            print()
            print("📋 Next Steps:")
            print("1. Render should already be using DATABASE_URL (PostgreSQL)")
            print("2. Redeploy Render service (if needed)")
            print("3. Test: curl https://legend-api.onrender.com/v1/meta/status")
            print("4. Should show: 'rows_total': 185")
            print()
            return True
        else:
            print("⚠️  Warning: Row count mismatch!")
            print(f"   SQLite: {total_rows}")
            print(f"   PostgreSQL: {pg_count}")
            return False
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        sqlite_conn.close()

if __name__ == '__main__':
    success = migrate_patterns()
    exit(0 if success else 1)

