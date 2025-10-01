# 🚀 Run PostgreSQL Migration

**Goal**: Copy 185 patterns from SQLite to PostgreSQL (production-ready!)

---

## Step 1: Get PostgreSQL URL from Render

1. **Go to Render Dashboard**: https://dashboard.render.com
2. **Find your database**: `legend-db` (or whatever you named it)
3. **Click on it**
4. **Copy the "External Database URL"**
   - Should look like: `postgres://user:pass@host.render.com/dbname`

---

## Step 2: Run Migration Script

Open Terminal and run:

```bash
cd ~/Desktop/legend-ai-mvp

# Set the DATABASE_URL (paste your copied URL)
export DATABASE_URL='postgres://your-url-here'

# Run migration
python migrate_to_postgres.py
```

**Expected output**:
```
🔄 Legend AI - SQLite to PostgreSQL Migration
============================================================

📊 Source: legendai.db (SQLite)
📊 Target: postgres://... (PostgreSQL)

📖 Reading from SQLite...
   Found: 185 patterns ✅

📝 Connecting to PostgreSQL...
🔧 Ensuring patterns table exists...
   Table ready ✅

📥 Migrating patterns...
   Progress: 10/185 (5%)
   Progress: 20/185 (11%)
   ...
   Progress: 180/185 (97%)

✅ Migration complete!

   Inserted: 182
   Updated:  3
   Skipped:  0
   Total:    185

🔍 Verifying PostgreSQL...
   Patterns in PostgreSQL: 185 ✅

🎉 SUCCESS! All patterns migrated successfully!
```

---

## Step 3: Verify Render is Using PostgreSQL

The `legend-api` service should already have `DATABASE_URL` pointing to PostgreSQL.

**Check**:
1. Render Dashboard → `legend-api` → Environment
2. Look for `DATABASE_URL`
3. Should be the PostgreSQL URL (not SQLite!)

If it's not set or is still SQLite:
- Add/update `DATABASE_URL` to the PostgreSQL URL
- Save and redeploy

---

## Step 4: Redeploy API (If Needed)

If DATABASE_URL was already PostgreSQL but had only 3 rows:
1. Render Dashboard → `legend-api`
2. Manual Deploy → "Clear build cache & deploy"
3. Wait 5 minutes

---

## Step 5: Test!

```bash
# Should show 185 patterns!
curl -s 'https://legend-api.onrender.com/v1/meta/status' | python3 -m json.tool
```

**Expected**:
```json
{
    "last_scan_time": "2025-09-30T...",
    "rows_total": 185,  ← Should be 185!
    "patterns_daily_span_days": 30,
    "version": "0.1.0"
}
```

```bash
# Should show multiple patterns
curl -s 'https://legend-api.onrender.com/v1/patterns/all?limit=10'
```

---

## 🎉 What This Achieves

### Before (SQLite):
- ❌ Data resets on every deploy
- ❌ Not production-ready
- ❌ Can't add new patterns that persist
- ✅ But had 185 patterns

### After (PostgreSQL):
- ✅ Data persists across deploys
- ✅ Production-ready
- ✅ Can add new patterns via scans
- ✅ Scalable (TimescaleDB features)
- ✅ **Still has 185 patterns!**

---

## 🐛 Troubleshooting

### If migration fails with "DATABASE_URL not found"

Make sure you exported it:
```bash
export DATABASE_URL='your-postgres-url'
echo $DATABASE_URL  # Should print the URL
```

### If migration fails with "table doesn't exist"

The script creates it automatically, but if it fails:
```bash
psql "$DATABASE_URL" << EOF
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
);
EOF
```

### If you get "permission denied"

Make sure the script is executable:
```bash
chmod +x migrate_to_postgres.py
```

Or run with python directly:
```bash
python migrate_to_postgres.py
```

---

## ⚡ Quick Command (All-in-One)

```bash
cd ~/Desktop/legend-ai-mvp && \
export DATABASE_URL='YOUR_POSTGRES_URL_HERE' && \
python migrate_to_postgres.py && \
echo "" && \
echo "🧪 Testing API..." && \
curl -s 'https://legend-api.onrender.com/v1/meta/status' | grep rows_total
```

---

**Ready! Get your PostgreSQL URL and run the migration!** 🚀

