# Legend AI Deployment Guide

## Prerequisites

- GitHub account with repository access
- Render account (free tier works)
- Vercel account (free tier works)
- Python 3.11+ installed locally
- Node.js 16+ (for local frontend testing)

## Local Development Setup

### 1. Clone Repository

```bash
git clone https://github.com/[YOUR_ORG]/legend-ai-mvp.git
cd legend-ai-mvp
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # Mac/Linux
# OR
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Create Environment File

```bash
cp .env.example .env  # If you have an example
# OR create .env manually
```

**.env** contents:
```bash
# Database (development)
DATABASE_URL=sqlite:///./legendai.db

# Data providers (optional)
FINNHUB_API_KEY=your_key_here
VCP_PROVIDER=yfinance

# Redis (optional, falls back to in-memory)
# REDIS_URL=redis://localhost:6379/0

# Observability (optional)
# SENTRY_DSN=your_sentry_dsn

# CORS (development)
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### 4. Initialize Database

```bash
# Run migrations
python -c "from app.legend_ai_backend import app; from app.db import engine; from sqlalchemy import text; engine.execute(text(open('migrations/sql/0001_create_patterns_table.sql').read()))"

# OR use the API endpoint
python -m uvicorn app.legend_ai_backend:app --reload &
curl -X POST http://localhost:8000/admin/init-db

# Seed demo data (optional)
curl -X POST http://localhost:8000/admin/seed-demo
```

### 5. Run Local Server

```bash
# Start API
uvicorn app.legend_ai_backend:app --reload --port 8000

# In another terminal, start simple HTTP server for frontend
python -m http.server 3000
# OR
npx serve -p 3000
```

Visit:
- API docs: http://localhost:8000/docs
- Dashboard: http://localhost:3000

### 6. Run Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov=vcp_ultimate_algorithm --cov-report=html

# Specific test
pytest tests/detectors/test_vcp_fixtures.py -v
```

## Production Deployment

### Backend Deployment (Render)

#### Step 1: Create Render Web Service

1. Go to [render.com/dashboard](https://dashboard.render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: `legend-api`
   - **Region**: Oregon (or closest to users)
   - **Branch**: `main`
   - **Runtime**: Docker
   - **Dockerfile Path**: `./Dockerfile`
   - **Instance Type**: Starter ($7/month, or Free tier for testing)

#### Step 2: Set Environment Variables

In Render dashboard → legend-api → Environment:

```bash
# Database
DATABASE_URL=sqlite:///./legendai.db
# OR for PostgreSQL:
# DATABASE_URL=postgresql://user:pass@host:5432/dbname?sslmode=require

# Data providers
FINNHUB_API_KEY=your_key_here  # Optional
VCP_PROVIDER=yfinance

# CORS
ALLOWED_ORIGINS=https://legend-ai.vercel.app,https://legend-ai-dashboard.vercel.app
ALLOWED_ORIGIN_REGEX=https://.*\.vercel\.app

# Optional
REDIS_URL=  # Leave empty for in-memory cache
SENTRY_DSN=  # Optional error tracking
```

#### Step 3: Configure Health Check

- **Health Check Path**: `/healthz`
- **Health Check Interval**: 30 seconds

#### Step 4: Deploy

- Click "Manual Deploy" or push to `main` branch
- Wait for build (2-3 minutes)
- Verify at: `https://legend-api.onrender.com/healthz`

#### Step 5: Set Up Cron Job

In `render.yaml` (already configured):

```yaml
cronJobs:
  - name: daily-market-scanner
    schedule: "0 10 * * *"  # 6 AM ET
    command: "python daily_market_scanner.py"
```

Render will automatically detect and deploy the cron job.

**Verify cron job**:
- Dashboard → Cron Jobs → daily-market-scanner
- Check logs for execution history

### Frontend Deployment (Vercel)

#### Step 1: Connect Repository

1. Go to [vercel.com/dashboard](https://vercel.com/dashboard)
2. Click "New Project"
3. Import your GitHub repository
4. Configure:
   - **Framework Preset**: Other (it's vanilla JS)
   - **Root Directory**: `./`
   - **Build Command**: (leave empty)
   - **Output Directory**: (leave empty)

#### Step 2: Set Environment Variables

In Vercel dashboard → Project → Settings → Environment Variables:

```bash
NEXT_PUBLIC_API_BASE=https://legend-api.onrender.com
```

**Note**: The dashboard uses a meta tag for API base, so this may not be needed. Check `index.html`:
```html
<meta name="legend-ai-api-base" content="https://legend-api.onrender.com">
```

#### Step 3: Configure Build

`vercel.json` (already configured):

```json
{
  "version": 2,
  "builds": [
    { "src": "index.html", "use": "@vercel/static" },
    { "src": "style.css", "use": "@vercel/static" },
    { "src": "app.js", "use": "@vercel/static" },
    { "src": "public/api.js", "use": "@vercel/static" }
  ],
  "routes": [
    { "handle": "filesystem" },
    { "src": "/(.*)", "dest": "/index.html" }
  ]
}
```

#### Step 4: Deploy

- Click "Deploy"
- Wait for build (30-60 seconds)
- Verify at: `https://legend-ai.vercel.app`

### Database Setup (Optional PostgreSQL)

#### Option A: Render PostgreSQL

1. Render Dashboard → New + → PostgreSQL
2. Configure:
   - **Name**: `legend-db`
   - **Region**: Same as API
   - **Plan**: Starter ($7/month) or Free
3. Copy **External Database URL**
4. Update `DATABASE_URL` in API environment:
   ```bash
   DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
   ```

#### Option B: TimescaleDB Cloud

1. Sign up at [timescale.com](https://www.timescale.com)
2. Create new service
3. Copy connection string
4. Update `DATABASE_URL` with `?sslmode=require` suffix

#### Migrate Data (SQLite → PostgreSQL)

```bash
# Local: Export patterns
python -c "
import sqlite3, json
conn = sqlite3.connect('legendai.db')
patterns = conn.execute('SELECT * FROM patterns').fetchall()
with open('patterns_export.json', 'w') as f:
    json.dump([dict(p) for p in patterns], f)
"

# Deploy migration script
python migrate_to_postgres.py
```

## Post-Deployment Verification

### 1. API Health Check

```bash
# Health
curl https://legend-api.onrender.com/healthz
# Expected: {"ok": true, "version": "0.1.0"}

# Readiness
curl https://legend-api.onrender.com/readyz
# Expected: {"ok": true}

# Status
curl https://legend-api.onrender.com/v1/meta/status
# Expected: {"last_scan_time": "...", "rows_total": 185, ...}
```

### 2. Pattern Endpoint

```bash
curl https://legend-api.onrender.com/v1/patterns/all?limit=5
# Expected: {"items": [...], "next": "cursor_string"}
```

### 3. Dashboard

1. Visit `https://legend-ai.vercel.app`
2. Check console for errors (F12)
3. Verify patterns load in table
4. Check data freshness indicator
5. Test filters and sorting

### 4. Cron Job

```bash
# Check last scan
curl https://legend-api.onrender.com/v1/meta/status | jq '.last_scan_time'

# Manual trigger (if needed)
curl -X POST https://legend-api.onrender.com/admin/run-scan?limit=5
```

## Troubleshooting

### Build Failures

**Problem**: Render build fails
- Check: `requirements.txt` has all dependencies
- Verify: `Dockerfile` syntax correct
- Look at: Build logs in Render dashboard

**Problem**: Vercel build fails
- Check: `vercel.json` syntax
- Verify: All referenced files exist
- Look at: Deployment logs

### Runtime Errors

**Problem**: API returns 500
- Check: Render logs (Dashboard → Logs → Recent)
- Verify: `DATABASE_URL` is correct
- Test: `/healthz` works but `/readyz` fails → database issue

**Problem**: CORS errors in dashboard
- Check: `ALLOWED_ORIGINS` includes Vercel domain
- Verify: Dashboard API base URL matches Render URL
- Look at: Browser console (F12) for exact error

**Problem**: No patterns returned
- Check: `/v1/meta/status` shows `rows_total: 0`
- Verify: Cron job ran successfully (Render → Cron Jobs → Logs)
- Fix: Run manual scan or seed demo data

### Performance Issues

**Problem**: Slow API responses
- Check: Render logs for slow queries
- Verify: Database has indexes
- Consider: Upgrading Render instance type
- Profile: Use `/admin/test-legacy-transform` endpoint

**Problem**: Dashboard slow to load
- Check: Pattern count (>500 may be slow)
- Verify: Pagination working (check Network tab)
- Optimize: Reduce initial `limit` in app.js

## Maintenance

### Daily Checks

- [ ] Verify cron job ran (check last_scan_time)
- [ ] Check Render logs for errors
- [ ] Monitor API response times
- [ ] Review Sentry errors (if configured)

### Weekly Tasks

- [ ] Review pattern detection accuracy
- [ ] Check database size growth
- [ ] Update dependencies (security patches)
- [ ] Review and triage GitHub issues

### Monthly Tasks

- [ ] Review and optimize database indexes
- [ ] Analyze cron job performance trends
- [ ] Update documentation
- [ ] Plan feature enhancements

## Rollback Procedure

### Quick Rollback (Render)

1. Dashboard → legend-api → Deployments
2. Find previous successful deployment
3. Click "..." → "Rollback to this version"
4. Confirm

### Quick Rollback (Vercel)

1. Dashboard → Project → Deployments
2. Find previous deployment
3. Click "..." → "Promote to Production"

### Database Rollback

**Warning**: Database changes are harder to roll back.

```bash
# If you have backups
# Render PostgreSQL: Automatic backups (paid plan)
# Manual backup before changes:
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

## Scaling Considerations

### When to Scale

- API response times > 500ms p95
- Cron job takes > 30 minutes
- Pattern count > 10,000
- Dashboard users > 100 concurrent

### Scaling Options

1. **Render**: Upgrade instance type (Starter → Standard → Pro)
2. **Database**: Move to dedicated PostgreSQL/TimescaleDB
3. **Caching**: Add Redis for pattern cache
4. **CDN**: Already handled by Vercel
5. **Worker**: Separate scan worker from API

## Security Checklist

Before going live:

- [ ] Admin endpoints protected (add API key auth)
- [ ] Environment variables secured (no hardcoded secrets)
- [ ] CORS properly configured (no `*` wildcard)
- [ ] Database backups enabled
- [ ] HTTPS enforced (automatic on Render/Vercel)
- [ ] Rate limiting implemented (future enhancement)
- [ ] Input validation on all endpoints
- [ ] Error messages don't leak sensitive info

## Support

- **Issues**: GitHub Issues
- **Logs**: Render Dashboard → Logs
- **Monitoring**: Sentry (if configured)
- **Docs**: `/docs` directory

## Quick Reference

### URLs

- API Base: `https://legend-api.onrender.com`
- Dashboard: `https://legend-ai.vercel.app`
- API Docs: `https://legend-api.onrender.com/docs`
- Health Check: `https://legend-api.onrender.com/healthz`

### Key Files

- `app/legend_ai_backend.py` - Main API
- `vcp_ultimate_algorithm.py` - Detector
- `daily_market_scanner.py` - Cron job
- `app.js` - Dashboard logic
- `render.yaml` - Render configuration
- `vercel.json` - Vercel configuration

### Common Commands

```bash
# Local development
uvicorn app.legend_ai_backend:app --reload

# Run tests
pytest tests/ -v

# Run scanner
python daily_market_scanner.py

# Check status
curl https://legend-api.onrender.com/v1/meta/status
```

