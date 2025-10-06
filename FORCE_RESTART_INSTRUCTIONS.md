# 🔄 Force Render Service Restart

## 🐛 Issue
Database is accessible with SSL ✅, but Render service still returns 0 patterns.

**Root Cause**: Service deployed but didn't reload the new `DATABASE_URL` environment variable.

---

## 🔧 Solution: Force Full Restart

### Option 1: Suspend & Resume (Fastest)
1. **Render Dashboard** → `legend-api`
2. **Click** the **"..."** menu (top right, near "Manual Deploy")
3. **Click** "Suspend"
4. **Wait** 10 seconds
5. **Click** "Resume"
6. **Wait** 2 minutes for startup
7. **Test**: `curl https://legend-api.onrender.com/v1/meta/status`

---

### Option 2: Clear Build Cache & Deploy
1. **Render Dashboard** → `legend-api`
2. **Click** "Manual Deploy"
3. **Select** "Clear build cache & deploy"
4. **Wait** ~5 minutes
5. **Test**: `curl https://legend-api.onrender.com/v1/meta/status`

---

### Option 3: Restart via Settings
1. **Render Dashboard** → `legend-api` → Settings
2. **Scroll down** to "Danger Zone"
3. **Click** "Restart Service"
4. **Confirm**
5. **Wait** 2 minutes
6. **Test**: `curl https://legend-api.onrender.com/v1/meta/status`

---

## 🧪 Test After Restart

```bash
# Should show 188!
curl -s 'https://legend-api.onrender.com/v1/meta/status' | python3 -m json.tool
```

**Expected**:
```json
{
    "last_scan_time": "2025-09-29T07:45:45...",
    "rows_total": 188,  ← Should be 188!
    "patterns_daily_span_days": 2,
    "version": "0.1.0"
}
```

---

## ✅ What We Know

| Check | Status | Details |
|-------|--------|---------|
| Database has data | ✅ | 188 patterns verified |
| SSL connection works | ✅ | Tested successfully |
| DATABASE_URL is correct | ✅ | With `?sslmode=require` |
| Service deployed | ✅ | Shows "Deployed <1m" |
| Env vars loaded | ❌ | Service using old cached value |

---

## 💡 Why This Happens

Render caches environment variables in running containers. When you:
1. Change an env var
2. Deploy

Sometimes the container doesn't reload the env vars. A **full restart** forces it to reload.

---

## 🚀 After Successful Restart

You should see:
- ✅ `/v1/meta/status` returns 188 patterns
- ✅ `/v1/patterns/all` returns data
- ✅ `/readyz` returns `{"ok": true}`

Then we can connect the dashboard! 🎉

---

**Recommend: Try Option 1 (Suspend/Resume) first - it's fastest!**

