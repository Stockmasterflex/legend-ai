# 🚨 API Service Down

**Time:** {{timestamp}}
**Service:** {{service_url}}
**Last Known Good:** {{last_healthy}}

## Quick Diagnosis Steps

1. Check recent commits that might have broken it:
   ```bash
   git log --oneline -5
   ```

2. View live logs:
   ```bash
   curl -H "Authorization: Bearer $RENDER_TOKEN" \
     "https://api.render.com/v1/services/{{service_id}}/logs?limit=100"
   ```

3. Test locally:
   ```bash
   python legend_ai/api.py
   curl -fsS localhost:8000/healthz
   ```

## Common Fixes

- Import Error: Check requirements.txt matches imports
- DB Connection: Verify DATABASE_URL is set
- Port Binding: Ensure PORT env var is used
- Timeout: Increase gunicorn timeout if needed

## Deploy Fix
Once fixed locally:
```bash
git add -A && git commit -m "fix: api health check"
git push origin main
```
