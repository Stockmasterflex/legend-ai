import fs from 'fs';
import puppeteer from 'puppeteer';

export async function launchBrowser() {
  const configuredPath = process.env.PUPPETEER_EXECUTABLE_PATH;
  const fallbackPath = (() => {
    try {
      return puppeteer.executablePath();
    } catch (err) {
      return undefined;
    }
  })();
  const executablePath = configuredPath && fs.existsSync(configuredPath) ? configuredPath : fallbackPath;
  const headless = process.env.PUPPETEER_HEADLESS || 'new';
  return puppeteer.launch({
    headless,
    executablePath,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--no-zygote',
      '--single-process',
      '--window-size=1200,628'
    ]
  });
}
