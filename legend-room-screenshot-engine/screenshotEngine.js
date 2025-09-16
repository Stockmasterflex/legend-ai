// screenshotEngine.js

const express = require('express');
const cors = require('cors');
const puppeteer = require('puppeteer-core');
const cloudinary = require('cloudinary').v2;
const fs = require('fs');
const path = require('path');

const app = express();
app.use(cors({ origin: '*'}));
app.use(express.json());
const PORT = process.env.PORT || 3010;
const EXEC_PATH = process.env.PUPPETEER_EXECUTABLE_PATH || '/usr/bin/chromium';

// --- IMPORTANT ---
// Configure Cloudinary using Environment Variables for security.
// DO NOT hardcode your API keys in the code.
// Set these in your Render.com service settings.
cloudinary.config({
  cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
  api_key: process.env.CLOUDINARY_API_KEY,
  api_secret: process.env.CLOUDINARY_API_SECRET,
  secure: true,
});

/**
 * The core screenshot and upload function.
 * @param {string} symbol The stock symbol to screenshot (e.g., 'AAPL').
 */
async function captureAndUpload(symbol, chartUrl) {
  let browser = null;
  // Point to the local HTML template, passing the symbol in the query string.
  const localUrl = chartUrl || `file://${path.resolve('chart-template.html')}?symbol=${symbol}`;
  // Write to repo reports dir for smoke
  const reportsDir = path.resolve('reports');
  if (!fs.existsSync(reportsDir)) fs.mkdirSync(reportsDir, { recursive: true });
  const screenshotPath = path.join(reportsDir, 'SMOKE.png');
  
  if (process.env.DRY_RUN === '1') {
    console.log('DRY_RUN enabled: skipping browser and upload.');
    return `https://dummyimage.com/1200x750/131722/ffffff&text=${encodeURIComponent(symbol)}+Chart`;
  }

  console.log(`Starting process for symbol: ${symbol}`);
  console.log(`Loading chart from: ${localUrl}`);

  try {
    browser = await puppeteer.launch({
      executablePath: EXEC_PATH,
      headless: 'new',
      args: [
        '--no-sandbox',
        '--disable-gpu',
        '--disable-dev-shm-usage',
      ],
      ignoreHTTPSErrors: true,
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1200, height: 750 });
    await page.goto(localUrl, { waitUntil: 'domcontentloaded' });
    try {
      await page.waitForSelector('#container', { timeout: 8000 });
    } catch {}
    // give TradingView time to render
    await page.waitForTimeout(2000);

    console.log('Page loaded. Taking screenshot...');
    await page.screenshot({ path: screenshotPath });
    console.log(`Screenshot saved locally to: ${screenshotPath}`);

    // For smoke: return the local file path; optionally still upload if creds present
    if (process.env.CLOUDINARY_CLOUD_NAME && process.env.CLOUDINARY_API_KEY && process.env.CLOUDINARY_API_SECRET) {
      try {
        console.log('Uploading to Cloudinary...');
        const uploadResult = await cloudinary.uploader.upload(screenshotPath, {
          public_id: `stock_chart_${symbol.toLowerCase()}_${Date.now()}`
        });
        console.log('Upload successful.');
        return uploadResult.secure_url;
      } catch (e) {
        console.warn('Cloudinary upload failed, returning local path.', e.message);
      }
    }
    return screenshotPath;

  } catch (error) {
    console.error('Error during capture and upload process:', error);
    throw new Error('Failed to generate and upload chart.'); // Re-throw a generic error
  } finally {
    // Cleanup: close the browser and delete the local file.
    if (browser) {
      await browser.close();
    }
    // keep SMOKE.png on disk for inspection
  }
}

// Screenshot endpoint: accepts GET or POST. If no symbol is provided, default to SPY.
// GET example: /screenshot?symbol=TSLA
// POST example: { "symbol": "TSLA" }
app.all('/screenshot', async (req, res) => {
  const symbolRaw = (req.query && req.query.symbol) || (req.body && req.body.symbol) || 'SPY';
  const pivot = req.query && req.query.pivot ? String(req.query.pivot) : undefined;
  const contractions = req.query && req.query.contractions ? String(req.query.contractions) : undefined;
  const symbol = String(symbolRaw).toUpperCase().trim();

  try {
    if (process.env.DRY_RUN === '1') {
      const url = `https://dummyimage.com/1200x750/131722/ffffff&text=${encodeURIComponent(symbol)}+Chart`;
      return res.status(200).json({ chart_url: url, symbol, pivot, contractions, dry_run: true });
    }
    let url = `file://${path.resolve('chart-template.html')}?symbol=${symbol}`;
    if (pivot) url += `&pivot=${encodeURIComponent(pivot)}`;
    if (contractions) url += `&contractions=${encodeURIComponent(contractions)}`;
    const chartOut = await captureAndUpload(symbol, url);
    res.status(200).json({ chart_url: chartOut, symbol, pivot, contractions });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Root endpoint to confirm the service is online.
app.get('/', (req, res) => {
  res.send('Screenshot service is running. Use /screenshot?symbol=YOUR_SYMBOL to capture an image.');
});

app.listen(PORT, () => {
  console.log(`Screenshot service listening on port ${PORT}`);
});
