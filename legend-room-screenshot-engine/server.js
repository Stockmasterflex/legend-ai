import express from 'express';
import { launchBrowser } from './chromium.js';

const app = express();

app.get('/screenshot', async (req, res) => {
  const symbol = String(req.query.symbol || '').toUpperCase();
  if (!symbol) return res.status(400).json({ error: 'symbol required' });

  try {
    const url = `https://dummyimage.com/1200x628/0b1221/9be7ff.png&text=${encodeURIComponent(symbol)}+Chart`;
    try {
      const browser = await launchBrowser();
      await browser.close();
    } catch (err) {
      console.warn('puppeteer smoke failed', err?.message);
    }

    return res.json({ chart_url: url });
  } catch (e) {
    console.error('screenshot error', e);
    return res.status(500).json({ error: 'shot-failed' });
  }
});

app.get('/healthz', (_, res) => res.json({ ok: true, service: 'legend-shots' }));

const port = process.env.PORT || 3000;
app.listen(port, () => console.log(`legend-shots listening on :${port}`));
