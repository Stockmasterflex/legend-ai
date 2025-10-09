#!/usr/bin/env python3
"""
Initialize the database schema for Legend AI.
Reads SQL files in order and applies them to the DATABASE_URL.
"""

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text


def init_database():
    """Initialize database with schema migrations."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    print("Connecting to database...")
    engine = create_engine(database_url, pool_pre_ping=True)
    
    # Get migrations directory
    migrations_dir = Path(__file__).parent.parent / "migrations" / "sql"
    
    # Get all SQL files sorted by name
    sql_files = sorted(migrations_dir.glob("*.sql"))
    
    if not sql_files:
        print("No SQL migration files found")
        sys.exit(1)
    
    print(f"Found {len(sql_files)} migration file(s)")
    
    for sql_file in sql_files:
        print(f"\nApplying: {sql_file.name}")
        with open(sql_file) as f:
            sql = f.read()
        
        # Split by semicolons and execute each statement
        statements = [s.strip() for s in sql.split(";") if s.strip()]
        
        with engine.begin() as conn:
            for stmt in statements:
                if stmt:
                    try:
                        conn.execute(text(stmt))
                        print(f"  ✓ Executed statement ({len(stmt)} chars)")
                    except Exception as e:
                        print(f"  ⚠ Warning: {e}")
    
    print("\n✅ Database initialization complete!")


if __name__ == "__main__":
    init_database()

