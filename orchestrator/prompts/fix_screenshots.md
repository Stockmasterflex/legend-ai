# 🖨️ Screenshot Service Issue

**Service:** {{service_url}}/healthz
**Status:** {{error_detail}}

## Likely Causes

1. Chromium not found - Check Puppeteer setup:
   ```javascript
   // Needs @sparticuz/chromium for serverless
   const chromium = require('@sparticuz/chromium');
   ```

2. Memory limits - Render free tier = 512MB
   - Reduce concurrent renders
   - Clear page after each chart

3. DRY_RUN stuck - Check env:
   ```bash
   echo $DRY_RUN  # Should be 0 or false
   ```

## Quick Test
```bash
cd legend-room-screenshot-engine
npm start
curl localhost:3001/render?symbol=NVDA
```
