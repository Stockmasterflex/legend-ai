# 🚀 Legend AI Deployment Guide

## Render Deployment Troubleshooting

### 1. Pre-deployment Checks

**Syntax validation:**
```bash
# Test all Python files compile
find . -name "*.py" -not -path "./.venv/*" -exec python -m py_compile {} \;

# Test main imports
python -c "import service_api; from vcp.vcp_detector import VCPDetector; print('✅ Imports OK')"
```

**Local testing:**
```bash
# Test API locally
source .venv/bin/activate
uvicorn service_api:app --reload --port 8000 &
sleep 3
curl -s http://127.0.0.1:8000/healthz
pkill -f uvicorn
```

### 2. Render Configuration

**Environment Variables (Set in Render Dashboard):**
- `PYTHON_VERSION`: `3.11`
- `PORT`: (Auto-set by Render)
- `LEGEND_MOCK_MODE`: `0` (production)
- `NEWSAPI_KEY`: (optional)
- `SHOTS_BASE_URL`: (optional)
- `SCAN_REDIS_CACHE`: `1` (enable Redis response cache; requires `REDIS_URL`)
- `SCAN_RESPONSE_CACHE_TTL`: `240`
- `SCAN_RATE_LIMIT`: `60`
- `SCAN_RATE_WINDOW`: `60`
- `CHART_RATE_LIMIT`: `120`
- `CHART_RATE_WINDOW`: `60`

**Build Command:**
```bash
pip install -r requirements.txt
```

**Start Command:**
```bash
python -m alembic upgrade head && uvicorn service_api:app --host 0.0.0.0 --port $PORT --workers 1
```

### 3. Common Render Issues & Fixes

**Issue: "Module not found" errors**
```bash
# Fix: Ensure PYTHONPATH is set
export PYTHONPATH=/opt/render/project/src
```

**Issue: "Port already in use"**
- Render automatically sets PORT environment variable
- Use `--port $PORT` in start command

**Issue: Database migrations fail**
```bash
# Fix: Create alembic.ini if missing
python -c "
from alembic.config import Config
from alembic import command
cfg = Config('alembic.ini')
cfg.set_main_option('sqlalchemy.url', 'sqlite:///legend_runs.db')
command.upgrade(cfg, 'head')
"
```

### 4. Docker Local Testing

**Build and test production image:**
```bash
# Build
docker build -f Dockerfile.production -t legend-ai:latest .

# Test
docker run -p 8000:8000 legend-ai:latest &
sleep 10
curl -s http://localhost:8000/healthz
docker stop $(docker ps -q --filter ancestor=legend-ai:latest)
```

**Full stack test:**
```bash
# Start full stack
docker-compose -f docker-compose.prod.yml up -d

# Test endpoints
curl -s http://localhost:8000/healthz
curl -s http://localhost:8000/scan/AAPL

# Cleanup
docker-compose -f docker-compose.prod.yml down
```

### 5. Git Deployment Commands

**Force redeploy:**
```bash
git add -A
git commit -m "🚀 Production deployment $(date)"
git push origin main
```

**Rollback (if needed):**
```bash
git log --oneline -10  # Find last good commit
git reset --hard <commit-hash>
git push --force origin main
```

### 6. Health Check Endpoints

```bash
# Basic health
curl -s https://your-render-url.com/healthz

# VCP scan test
curl -s "https://your-render-url.com/scan/AAPL" | jq

# Today's candidates
curl -s "https://your-render-url.com/api/v1/vcp/today" | jq

# Metrics
curl -s "https://your-render-url.com/api/v1/vcp/metrics?start=2024-01-01&end=2024-12-31" | jq
```

### 7. Emergency Fixes

**Quick syntax check:**
```bash
python -m py_compile service_api.py && echo "✅ Syntax OK"
```

**Missing dependencies:**
```bash
pip freeze > requirements.txt
git add requirements.txt && git commit -m "📦 Update requirements" && git push
```

**Database issues:**
```bash
# Reset database
rm -f legend_runs.db
python seed_sample_data.py
```

## Production Optimization Checklist

- [x] Syntax errors fixed
- [x] Docker configuration ready  
- [x] Health checks implemented
- [x] Environment variables documented
- [x] Error handling in place
- [x] Logging configured
- [ ] SSL/HTTPS configured
- [ ] Rate limiting active
- [ ] Monitoring setup
- [ ] Backup strategy
