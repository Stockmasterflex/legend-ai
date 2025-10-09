# Legend AI Troubleshooting Guide

## Data Freshness Issues

### Problem: Patterns are stale (weeks old)

**Symptoms:**
- Data freshness indicator shows "Updated X days ago"
- `/v1/meta/status` shows `last_scan_time` from weeks ago
- Pattern count hasn't changed in days

**Investigation Steps:**

1. **Check Render Cron Job Status**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Navigate to: Cron Jobs → `daily-market-scanner`
   - Check recent execution logs
   - Look for errors or failures

2. **Verify Cron Schedule**
   - Confirm schedule is `0 10 * * *` (6 AM ET / 10:00 UTC)
   - Check if server timezone is UTC (it should be)
   - Verify the job is not paused/disabled

3. **Check Scanner Logs**
   ```bash
   # Via Render dashboard: Logs tab
   # Look for:
   - "Scan completed: X succeeded, Y failed, patterns: Z"
   - Any error traces
   - Database connection issues
   ```

4. **Test Manual Scan**
   ```bash
   curl -X POST https://legend-api.onrender.com/admin/run-scan?limit=5
   # Should return: {"ok": true, "scanned": 5, "results": [...]}
   ```

5. **Check Database Connection**
   ```bash
   curl https://legend-api.onrender.com/readyz
   # Should return: {"ok": true}
   # If false, database connection is broken
   ```

**Common Causes:**

- **Cron job not configured**: Check `render.yaml` is deployed
- **Insufficient memory**: Scanner OOMs during execution (upgrade instance)
- **Rate limiting**: Too many API calls to yfinance/Finnhub
- **Database locked**: SQLite file locked (upgrade to PostgreSQL)
- **Environment variable missing**: `DATABASE_URL` not set

**Solutions:**

1. **Quick Fix: Manual Scan**
   - Use dashboard "Run Scan" button
   - OR call `/admin/run-scan` endpoint
   - This provides immediate fresh data

2. **Enable Cron Job** (if not running)
   ```yaml
   # In render.yaml:
   cronJobs:
     - name: daily-market-scanner
       schedule: "0 10 * * *"
       command: "python daily_market_scanner.py"
   ```
   - Commit and push to trigger redeployment

3. **Upgrade Instance** (if memory issues)
   - Render Dashboard → legend-api → Settings
   - Change from Free/Starter to Standard
   - More memory for full S&P 500 scan

4. **Switch to PostgreSQL** (if SQLite locking)
   - Create Render PostgreSQL database
   - Update `DATABASE_URL` environment variable
   - Run migration: `python migrate_to_postgres.py`

## API Performance Issues

### Problem: Slow response times

**Investigation:**

1. **Check Pattern Count**
   ```bash
   curl https://legend-api.onrender.com/v1/meta/status | jq '.rows_total'
   ```
   - If >1000, pagination becomes important

2. **Profile Enrichment**
   - Pattern enrichment calls yfinance for each ticker
   - Check cache hit rate in logs

3. **Database Query Time**
   - Look for slow query logs
   - Check if indexes are present

**Solutions:**

- Reduce initial page size in dashboard (100 → 50)
- Enable Redis caching (set `REDIS_URL`)
- Add database indexes (should already exist)
- Consider pre-enriching patterns during scan

## Dashboard Issues

### Problem: Empty pattern table

**Investigation:**

1. **Check API Response**
   ```javascript
   // In browser console:
   fetch('https://legend-api.onrender.com/v1/patterns/all?limit=5')
     .then(r => r.json())
     .then(console.log)
   ```

2. **Check Console Errors**
   - Press F12 to open DevTools
   - Look for CORS errors, 404s, or JavaScript errors

3. **Verify API Base URL**
   ```html
   <!-- In index.html: -->
   <meta name="legend-ai-api-base" content="https://legend-api.onrender.com">
   ```

**Solutions:**

- Update API base URL in `index.html`
- Check CORS configuration in `render.yaml`
- Clear browser cache and reload

### Problem: Filters not working

**Symptoms:**
- Moving sliders doesn't update results
- Sector filter has no effect

**Investigation:**

1. **Check JavaScript Console**
   - Look for errors in `app.js`
   - Verify `applyFilters()` is called

2. **Test Manually**
   ```javascript
   // In console:
   app.applyFilters()
   ```

**Solutions:**

- Hard refresh (Cmd+Shift+R / Ctrl+Shift+R)
- Clear browser cache
- Check if `app.js` loaded correctly (Network tab)

## Database Issues

### Problem: Database connection errors

**Symptoms:**
- `/readyz` returns `{"ok": false}`
- API returns 500 errors
- Logs show "database is locked" (SQLite)

**Investigation:**

1. **Check DATABASE_URL**
   ```bash
   # Render Dashboard → Environment
   # Verify DATABASE_URL is set correctly
   ```

2. **Test Connection**
   ```python
   from sqlalchemy import create_engine, text
   engine = create_engine(DATABASE_URL)
   with engine.connect() as conn:
       result = conn.execute(text("SELECT 1"))
       print(result.fetchone())
   ```

**Solutions:**

- For SQLite: Only one writer at a time (upgrade to PostgreSQL)
- For PostgreSQL: Check connection string includes `?sslmode=require`
- Verify database server is running (Render dashboard)

### Problem: Schema mismatch errors

**Symptoms:**
- TypeError: 'str' object has no attribute 'isoformat'
- json.JSONDecodeError when reading meta field

**Investigation:**

Check database type:
```python
from app.config import get_database_url
url = get_database_url()
print("SQLite" if "sqlite" in url else "PostgreSQL")
```

**Solutions:**

- Run appropriate migration:
  - SQLite: Already compatible (TEXT, TIMESTAMP)
  - PostgreSQL: Run `migrations/sql/0002_upgrade_postgres_types.sql`

## Deployment Issues

### Problem: Render build fails

**Common Errors:**

1. **Missing dependency**
   ```
   ModuleNotFoundError: No module named 'X'
   ```
   **Fix**: Add to `requirements.txt`

2. **Dockerfile error**
   ```
   Error: COPY failed: file not found
   ```
   **Fix**: Check paths in `Dockerfile` are correct

3. **Port binding issue**
   ```
   Error: address already in use
   ```
   **Fix**: Ensure Dockerfile uses `PORT` env var

**Investigation:**

- Check build logs in Render dashboard
- Verify `requirements.txt` is up to date
- Test Dockerfile locally: `docker build -t legend-api .`

### Problem: Vercel deployment fails

**Common Errors:**

1. **vercel.json syntax error**
   **Fix**: Validate JSON syntax

2. **Build output not found**
   **Fix**: Verify `builds` section in `vercel.json`

**Investigation:**

- Check deployment logs in Vercel dashboard
- Verify all referenced files exist
- Test locally: `vercel dev`

## Pattern Detection Issues

### Problem: No patterns detected

**Symptoms:**
- Scanner runs but finds 0 patterns
- `/v1/meta/status` shows `rows_total: 0`

**Investigation:**

1. **Check Scanner Parameters**
   ```python
   # In vcp_ultimate_algorithm.py:
   detector = VCPDetector(
       min_price=30.0,         # Not too high?
       min_volume=1_000_000,   # Not too restrictive?
       check_trend_template=True  # Not filtering everything?
   )
   ```

2. **Test Single Ticker**
   ```bash
   curl -X POST "https://legend-api.onrender.com/admin/run-scan?limit=1"
   ```

3. **Check Data Quality**
   ```bash
   curl "https://legend-api.onrender.com/admin/test-data?ticker=AAPL"
   # Verify yfinance returns data
   ```

**Solutions:**

- Relax detector parameters temporarily
- Check if yfinance is working (might be blocked)
- Verify FINNHUB_API_KEY if using Finnhub
- Test with known VCP patterns (NVDA Jan 2023, MSFT Nov 2022)

### Problem: Too many false positives

**Symptoms:**
- Scanner finds 500+ patterns
- Most patterns don't look like VCPs on chart

**Solutions:**

- Tighten parameters:
  ```python
  min_price=50.0,           # Higher price filter
  min_volume=2_000_000,     # More liquidity
  check_trend_template=True # Enable Minervini filter
  ```
- Review detected patterns manually
- Add more test fixtures to validate accuracy

## Quick Diagnostics

### Health Check Script

```bash
#!/bin/bash
# check_legend_health.sh

API_BASE="https://legend-api.onrender.com"

echo "=== Legend AI Health Check ==="

echo -n "1. API Health: "
curl -s $API_BASE/healthz | jq -r '.ok'

echo -n "2. Database Ready: "
curl -s $API_BASE/readyz | jq -r '.ok'

echo "3. Pattern Status:"
curl -s $API_BASE/v1/meta/status | jq '{rows: .rows_total, last_scan: .last_scan_time}'

echo "4. Sample Patterns:"
curl -s "$API_BASE/v1/patterns/all?limit=3" | jq '.items | length'

echo "=== Check Complete ==="
```

### Common Error Codes

- **500**: Server error (check logs)
- **503**: Service unavailable (database down?)
- **404**: Endpoint not found (check URL)
- **CORS error**: Origin not allowed (update CORS config)

## Getting Help

1. **Check logs first**
   - Render Dashboard → Logs
   - Browser Console (F12)

2. **Search existing issues**
   - GitHub Issues
   - Look for similar problems

3. **Create detailed issue**
   - Include error messages
   - Steps to reproduce
   - Environment details (dev/prod)
   - Screenshots if applicable

4. **Emergency contacts**
   - For production outages
   - Include severity level

