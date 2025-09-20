import express from 'express';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import { launchBrowser } from './chromium.js';

const app = express();
app.use(express.json({ limit: '512kb' }));

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const reportsDir = path.join(__dirname, 'reports');
if (!fs.existsSync(reportsDir)) {
  fs.mkdirSync(reportsDir, { recursive: true });
}
app.use('/reports', express.static(reportsDir, { maxAge: '1h', fallthrough: true }));

const parseOverlay = (payload) => {
  if (!payload) return null;
  if (typeof payload === 'object') return payload;
  if (typeof payload === 'string') {
    try {
      return JSON.parse(payload);
    } catch (err) {
      return null;
    }
  }
  return null;
};

app.all('/screenshot', async (req, res) => {
  const symbol = String(req.query.symbol || '').toUpperCase();
  if (!symbol) {
    return res.status(400).json({ error: 'symbol required' });
  }

  const overlayPayload = parseOverlay(req.body?.overlays) || parseOverlay(req.query.overlays);
  const pivot = req.query.pivot ? String(req.query.pivot) : '';
  const renderStart = Date.now();
  const overlayCounts = {
    lines: overlayPayload?.lines?.length || 0,
    boxes: overlayPayload?.boxes?.length || 0,
    labels: overlayPayload?.labels?.length || 0,
    arrows: overlayPayload?.arrows?.length || 0,
    zones: overlayPayload?.zones?.length || 0,
  };

  if (String(process.env.DRY_RUN || '0') === '1') {
    const dummy = `https://dummyimage.com/1200x628/0b1221/9be7ff.png&text=${encodeURIComponent(symbol)}+Chart`;
    console.log('shots_dry_run', { symbol, overlay_counts: overlayCounts });
    return res.json({ chart_url: dummy, dry_run: true, overlay_counts: overlayCounts });
  }

  try {
    const browser = await launchBrowser();
    const page = await browser.newPage();
    await page.setUserAgent('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari LegendShots');
    try {
      const htmlPath = path.join(__dirname, 'chart-template.html');
      const params = new URLSearchParams();
      params.set('symbol', symbol);
      if (pivot) params.set('pivot', pivot);
      ['entry', 'stop', 'target', 'pattern'].forEach((key) => {
        if (req.query[key]) params.set(key, String(req.query[key]));
      });
      const safeOverlay = overlayPayload ? JSON.parse(JSON.stringify(overlayPayload)) : null;
      if (safeOverlay) {
        await page.evaluateOnNewDocument((overlay) => {
          window.__LEGEND_OVERLAYS = overlay;
        }, safeOverlay);
      }
      const fileUrl = `file://${htmlPath}?${params.toString()}`;
      await page.setViewport({ width: 1200, height: 628, deviceScaleFactor: 1 });
      await page.goto(fileUrl, { waitUntil: 'networkidle0', timeout: 45000 });
      await new Promise((r) => setTimeout(r, 2200));
      const filename = `${symbol}-${Date.now()}.png`;
      const outPath = path.join(reportsDir, filename);
      await page.screenshot({ path: outPath, type: 'png' });
      const proto = (req.headers['x-forwarded-proto'] || req.protocol || 'http').toString();
      const host = req.get('host');
      const chartUrl = `${proto}://${host}/reports/${filename}`;
      const durationMs = Date.now() - renderStart;
      console.log('shot_render_success', {
        symbol,
        duration_ms: durationMs,
        overlay_counts: overlayCounts,
        file: filename,
      });
      return res.json({ chart_url: chartUrl, overlay_counts: overlayCounts, duration_ms: durationMs });
    } finally {
      await page.close().catch(() => {});
      await browser.close().catch(() => {});
    }
  } catch (err) {
    console.error('screenshot error', err);
    const fallback = `https://dummyimage.com/1200x628/0b1221/9be7ff.png&text=${encodeURIComponent(symbol)}+Chart`;
    return res.status(200).json({
      chart_url: fallback,
      error: 'shot-failed',
      message: err instanceof Error ? err.message : String(err),
      overlay_counts: overlayCounts,
    });
  }
});

app.get('/healthz', async (_req, res) => {
  const dryRun = String(process.env.DRY_RUN || '0') === '1'
  const payload = { ok: true, service: 'legend-shots', dryRun };

  if (dryRun) {
    payload.browserVersion = null;
    return res.json(payload);
  }

  let browser;
  try {
    browser = await launchBrowser();
    payload.browserVersion = await browser.version();
    return res.json(payload);
  } catch (err) {
    payload.ok = false;
    payload.browserVersion = null;
    payload.error = err instanceof Error ? err.message : String(err);
    return res.status(503).json(payload);
  } finally {
    if (browser) {
      await browser.close().catch(() => {});
    }
  }
});

// Simple /health alias for external monitors expecting this path
app.get('/health', (_req, res) => {
  try {
    return res.json({ status: 'healthy', service: 'legend-shots', timestamp: new Date().toISOString() });
  } catch (err) {
    return res.status(500).json({ status: 'error', message: err instanceof Error ? err.message : String(err) });
  }
});

const port = process.env.PORT || 3010;
app.listen(port, () => console.log(`legend-shots listening on :${port}`));
