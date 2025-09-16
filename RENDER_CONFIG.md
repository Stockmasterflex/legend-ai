# 🚀 RENDER DEPLOYMENT CONFIGURATION

## IMMEDIATE ACTIONS FOR FAILED DEPLOY

### 1. 🚨 CRITICAL - Check Render Dashboard Settings

**In your Render dashboard for legend-api service:**

1. **Branch Settings:**
   - Go to Settings → Build & Deploy
   - **Branch**: Change to `feat/signals-phase3-4-demo` (current working branch)
   - OR merge your fix to main: `git checkout main && git merge feat/signals-phase3-4-demo && git push origin main`

2. **Environment Variables:**
   ```
   PYTHON_VERSION=3.11
   PORT=(auto-set by Render)
   PYTHONPATH=/opt/render/project/src
   LEGEND_MOCK_MODE=0
   ```

3. **Build Command:**
   ```bash
   pip install --upgrade pip && pip install -r requirements.txt
   ```

4. **Start Command:**
   ```bash
   python -m alembic upgrade head && uvicorn service_api:app --host 0.0.0.0 --port $PORT --workers 1
   ```

### 2. 🔍 COMMON RENDER DEPLOYMENT FAILURES

**Error: "Module not found"**
- **Fix:** Add `PYTHONPATH=/opt/render/project/src` to environment variables

**Error: "Port already in use"**
- **Fix:** Use `--port $PORT` (Render sets this automatically)

**Error: "Syntax Error in service_api.py"**
- **Status:** ✅ FIXED (just pushed to GitHub)

**Error: "Database migration failed"**
- **Fix:** Ignore for now, SQLite creates automatically

**Error: "Requirements installation failed"**
- **Fix:** Update build command to upgrade pip first

### 3. 🔄 FORCE CLEAN REBUILD COMMANDS

**Option A: Via Render Dashboard**
1. Go to your legend-api service
2. Click "Manual Deploy" 
3. Select latest commit (5210fe5)
4. Click "Deploy"

**Option B: Force Push (Trigger Rebuild)**
```bash
# Add empty commit to force rebuild
git commit --allow-empty -m "🚀 Force Render rebuild"
git push origin feat/signals-phase3-4-demo
```

**Option C: Merge to Main (Recommended)**
```bash
# Switch to main and merge the fix
git checkout main
git merge feat/signals-phase3-4-demo
git push origin main

# Then update Render to use main branch
```

### 4. 📊 DEPLOYMENT HEALTH CHECK

**Once deployment starts, monitor these:**

1. **Build Logs** - Should show:
   ```
   ✅ Requirements installing...
   ✅ Python 3.11 detected
   ✅ service_api.py syntax OK
   ✅ Build completed
   ```

2. **Start Logs** - Should show:
   ```
   ✅ Alembic migrations running...
   ✅ Uvicorn starting...
   ✅ Application startup complete
   ✅ Listening on 0.0.0.0:PORT
   ```

3. **Health Endpoint** - Should return:
   ```json
   {"ok": true, "version": "0.1.0"}
   ```

### 5. 🧪 POST-DEPLOYMENT TESTING

**Test these endpoints once live:**

```bash
# Replace YOUR_RENDER_URL with actual URL
RENDER_URL="https://legend-api-xxx.onrender.com"

# Basic health
curl -s "$RENDER_URL/healthz" | jq

# VCP scan
curl -s "$RENDER_URL/scan/AAPL" | jq '.detected,.confidence_score'

# API endpoints
curl -s "$RENDER_URL/api/v1/vcp/today" | jq '.rows | length'
curl -s "$RENDER_URL/api/v1/runs" | jq '.runs | length'
```

## 🚨 EMERGENCY TROUBLESHOOTING

### If deployment still fails:

1. **Check Render Logs:**
   - Go to Render Dashboard
   - Click on legend-api service
   - Click "Logs" tab
   - Look for Python errors

2. **Common Error Patterns:**

   **"SyntaxError: invalid syntax"**
   ```
   ✅ FIXED: service_api.py line 364 corrected
   ```

   **"ModuleNotFoundError: No module named 'service_api'"**
   ```bash
   # Add to Render Environment Variables:
   PYTHONPATH=/opt/render/project/src
   ```

   **"uvicorn: command not found"**
   ```bash
   # Update start command to:
   python -m uvicorn service_api:app --host 0.0.0.0 --port $PORT
   ```

3. **Nuclear Option - Redeploy from Scratch:**
   - Delete the legend-api service in Render
   - Create new Web Service
   - Connect to GitHub repo
   - Use settings from this guide

### 6. 🎯 OPTIMAL RENDER CONFIGURATION

**Service Type:** Web Service
**Repository:** Your GitHub repo
**Branch:** `main` (after merging fix)
**Root Directory:** Leave blank

**Build Command:**
```bash
pip install --upgrade pip && pip install -r requirements.txt
```

**Start Command:**
```bash
python -m alembic upgrade head && python -m uvicorn service_api:app --host 0.0.0.0 --port $PORT
```

**Environment Variables:**
```
PYTHON_VERSION=3.11
PYTHONPATH=/opt/render/project/src
LEGEND_MOCK_MODE=0
```

**Auto-Deploy:** ON (will redeploy when you push to GitHub)

## 📞 SUPPORT CHECKLIST

If you need help:
1. ✅ Syntax fix is pushed to GitHub
2. ✅ Render configuration updated  
3. ✅ Build/start commands corrected
4. ✅ Environment variables set
5. ✅ Correct branch selected
6. ✅ Auto-deploy enabled