# 🔍 Database Issue Diagnosis

**Problem**: API shows only 3 patterns, but local `legendai.db` has 185!

---

## ✅ What We Know

1. **Local database is correct**:
   - File: `legendai.db` (144KB)
   - Rows: 185 patterns
   - Committed to git: YES ✅

2. **Render is using wrong database**:
   - API returns: 3 patterns
   - `rows_total`: 3
   - Either using PostgreSQL or fresh SQLite

---

## 🔍 Root Cause

Render might be using a **PostgreSQL database** instead of the SQLite file!

Check Render environment variables:
- `DATABASE_URL` might point to PostgreSQL (from earlier setup)
- PostgreSQL only has the 3 demo patterns we seeded

---

## 🔧 Solution Options

### Option 1: Use SQLite from Repo (Quick Fix)

**In Render Dashboard** → legend-api → Environment:

1. **Find** `DATABASE_URL` variable
2. **Change it to**: `sqlite:///legendai.db`
3. **Save** and redeploy

This will use the SQLite file from the repo (with 185 patterns).

---

### Option 2: Migrate PostgreSQL (Better for Production)

**Copy data from SQLite to PostgreSQL**:

```bash
# 1. Export from local SQLite
sqlite3 legendai.db ".dump patterns" > patterns_export.sql

# 2. Clean up for PostgreSQL compatibility
sed 's/INTEGER PRIMARY KEY AUTOINCREMENT/SERIAL PRIMARY KEY/g' patterns_export.sql > patterns_pg.sql

# 3. Import to Render PostgreSQL
psql "$DATABASE_URL" < patterns_pg.sql
```

**Or use a Python script** (more reliable):

```python
import sqlite3
from sqlalchemy import create_engine
import os

# Read from SQLite
sqlite_conn = sqlite3.connect('legendai.db')
sqlite_conn.row_factory = sqlite3.Row
cursor = sqlite_conn.cursor()
rows = cursor.execute("SELECT * FROM patterns").fetchall()

# Write to PostgreSQL
pg_engine = create_engine(os.environ['DATABASE_URL'])
with pg_engine.connect() as conn:
    for row in rows:
        conn.execute("""
            INSERT INTO patterns (ticker, pattern, as_of, confidence, rs, price, meta)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (ticker, pattern, as_of) DO NOTHING
        """, dict(row))
```

---

### Option 3: Use Render's Persistent Disk (Advanced)

Mount a persistent disk and copy legendai.db there.

---

## 🎯 Recommended Fix (Do This Now)

### Step 1: Check DATABASE_URL in Render

1. Go to Render Dashboard
2. Click `legend-api` service  
3. Click "Environment" tab
4. Look for `DATABASE_URL`

**If it shows PostgreSQL URL** (starts with `postgres://` or `postgresql://`):
- This is the issue!
- PostgreSQL only has 3 demo rows

**If it shows SQLite** (`sqlite:///legendai.db`):
- SQLite file might not be persisting between deploys
- Render's filesystem is ephemeral!

---

### Step 2: Quick Fix - Use SQLite for Now

**Change DATABASE_URL to**:
```
sqlite:///app/legendai.db
```

**Or remove DATABASE_URL entirely** (code defaults to SQLite)

Then redeploy!

---

### Step 3: Verify

After redeploy:
```bash
curl -s 'https://legend-api.onrender.com/v1/meta/status' | grep rows_total
```

Should show: `"rows_total": 185`

---

## ⚠️ Important Note About SQLite on Render

**Render's filesystem is ephemeral!**

- Files reset on every deploy
- Database changes don't persist
- Fine for read-only/demo data
- NOT good for user-generated data

**For production**, you should:
1. Use Render PostgreSQL (persistent)
2. Copy the 185 patterns to PostgreSQL
3. Update DATABASE_URL to PostgreSQL

---

## 🚀 Fastest Fix Right Now

1. **Render Dashboard** → legend-api → Environment
2. **Check DATABASE_URL**:
   - If PostgreSQL → Change to `sqlite:///legendai.db`
   - If not set → Add: `DATABASE_URL=sqlite:///legendai.db`
3. **Manual Deploy** → Clear cache & deploy
4. **Wait 5 minutes**
5. **Test**: `curl https://legend-api.onrender.com/v1/meta/status`

Should show 185 patterns! 🎉

---

## 📊 What Each Option Gives You

| Option | Patterns | Persistent | Production-Ready |
|--------|----------|----------|------------------|
| SQLite from repo | 185 ✅ | ❌ Resets on deploy | ❌ Demo only |
| Migrate to PostgreSQL | 185 ✅ | ✅ Survives deploys | ✅ Production ready |
| Persistent Disk | 185 ✅ | ✅ Survives deploys | ⚠️ More complex |

---

## 💡 My Recommendation

**For now (to see dashboard working)**:
- Use SQLite from repo
- Change DATABASE_URL to `sqlite:///legendai.db`
- You'll see 185 patterns immediately!

**For production later**:
- Migrate to PostgreSQL
- Proper persistent storage
- Can add/update patterns that survive deploys

---

**Let's fix this now! Check your DATABASE_URL in Render!** 🔧

