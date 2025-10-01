# 🚨 CRITICAL: Fix Render Repository Configuration

**Issue**: The `legend-api` service on Render is deploying from the WRONG repository!

---

## ❌ Current (WRONG) Configuration

```
Service: legend-api
Repository: https://github.com/Stockmasterflex/legend-ai-dashboard
Status: Wrong repo - this is the FRONTEND code!
```

---

## ✅ Correct Configuration

```
Service: legend-api
Repository: https://github.com/Stockmasterflex/legend-ai-mvp
Branch: main
Root Directory: (leave empty or /)
```

**Why**: The `legend-ai-mvp` repo contains:
- `app/legend_ai_backend.py` - The actual FastAPI application
- `legendai.db` - SQLite database with 185 patterns
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container configuration
- All the backend code

---

## 🔧 How to Fix (Step-by-Step)

### Option 1: Via Render Dashboard (RECOMMENDED)

1. **Go to Render Dashboard**
   - URL: https://dashboard.render.com

2. **Find the `legend-api` service**
   - Click on it

3. **Go to Settings**
   - Click "Settings" tab

4. **Update Repository**
   - Scroll to "Repository" section
   - Click "Disconnect Repository"
   - Click "Connect Repository"
   - Select: `Stockmasterflex/legend-ai-mvp`
   - Branch: `main`

5. **Verify Build Settings**
   - Build Command: (should auto-detect or use `pip install -r requirements.txt`)
   - Start Command: (should auto-detect or use `uvicorn app.legend_ai_backend:app --host 0.0.0.0 --port $PORT`)
   - Dockerfile Path: `Dockerfile` (if using Docker)

6. **Save and Redeploy**
   - Click "Save Changes"
   - Click "Manual Deploy" → "Clear build cache & deploy"

---

### Option 2: Via Render CLI (If You Have It)

```bash
# Update the service
render services update legend-api \
  --repo https://github.com/Stockmasterflex/legend-ai-mvp \
  --branch main

# Trigger redeploy
render services deploy legend-api
```

---

### Option 3: Delete and Recreate (LAST RESORT)

If updating doesn't work:

1. **Export environment variables** from current service
   - Go to Environment tab
   - Copy all env vars (DATABASE_URL, FINNHUB_API_KEY, etc.)

2. **Delete the service**
   - Settings → Delete Service

3. **Create new service**
   - New → Web Service
   - Connect: `legend-ai-mvp` repo
   - Name: `legend-api`
   - Environment: Docker
   - Plan: Free
   - Add all environment variables

---

## 🔍 Verify After Fix

### 1. Check Render Service
```bash
# Should show legend-ai-mvp repo
curl -s https://legend-api.onrender.com/healthz
# Should return: {"ok":true,"version":"0.1.0"}
```

### 2. Check Database Access
```bash
curl -s 'https://legend-api.onrender.com/v1/patterns/all?limit=5'
# Should return 5 patterns from the 185 in legendai.db
```

### 3. Check Logs
- Go to Render Dashboard → legend-api → Logs
- Should see: "Uvicorn running on http://0.0.0.0:$PORT"
- Should NOT see errors about missing files

---

## 📊 What Will Change

### Before (Wrong Repo):
```
legend-ai-dashboard repo:
  ├── index.html          ← Frontend
  ├── app.js              ← Frontend
  ├── style.css           ← Frontend
  ├── Dockerfile.api      ← Has basic backend (NOT the real one!)
  └── legend_ai_backend.py ← Old/incomplete version
```

### After (Correct Repo):
```
legend-ai-mvp repo:
  ├── app/
  │   ├── legend_ai_backend.py  ← REAL FastAPI app with /v1 API
  │   ├── data_fetcher.py       ← Multi-source data fetching
  │   ├── db_queries.py         ← Database queries
  │   └── config.py             ← Configuration
  ├── legendai.db               ← SQLite with 185 patterns! 🎉
  ├── requirements.txt          ← All dependencies
  ├── Dockerfile                ← Proper container config
  └── migrations/               ← SQL migrations
```

---

## 🎯 Expected Results After Fix

1. **API will have access to the full database**
   - 185 patterns instead of just 3!
   
2. **All endpoints will work properly**
   - `/healthz` ✅
   - `/readyz` ✅
   - `/v1/patterns/all` ✅ (with 185 patterns!)
   - `/v1/meta/status` ✅
   - `/admin/*` endpoints ✅

3. **Dashboard will show 185 patterns**
   - Sector Performance will show multiple sectors
   - High-Prob Setups will have 10+ options
   - Scan Statistics will show real numbers

---

## ⚠️ Important Notes

### Don't Lose Data
- The `legendai.db` file is in `legend-ai-mvp` repo
- It already has 185 patterns seeded
- Make sure Render can access it

### Environment Variables
Keep these env vars in Render:
```
DATABASE_URL=sqlite:///legendai.db  (or PostgreSQL if using Render DB)
FINNHUB_API_KEY=your_key
ALLOWED_ORIGINS=https://legend-ai-dashboard.vercel.app
```

### Dockerfile
The `legend-ai-mvp` repo has the correct Dockerfile that:
- Installs all dependencies
- Copies the database file
- Sets up the FastAPI app
- Binds to $PORT

---

## 🚀 Quick Fix Command

If you have Render connected via GitHub:

1. **Go to**: https://dashboard.render.com/web/srv-xxxxx/settings
2. **Repository**: Click "Disconnect"
3. **Repository**: Click "Connect" → Select `legend-ai-mvp`
4. **Save Changes**
5. **Manual Deploy**: "Clear build cache & deploy"

**Time to fix**: 2-3 minutes  
**Deployment time**: 5-10 minutes  
**Total downtime**: ~15 minutes

---

## 🆘 If You Need Help

Can't access Render dashboard? Let me know and I can:
1. Create a script to automate this via Render API
2. Guide you through each click step-by-step
3. Help troubleshoot any issues

---

**This is the missing piece! Once fixed, you'll have 185 patterns instead of 3!** 🎉

