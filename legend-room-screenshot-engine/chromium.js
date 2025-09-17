import fs from 'fs';
import { execSync } from 'child_process';
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
  const launch = () => puppeteer.launch({
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

  try {
    return await launch();
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    if (message.includes('Could not find Chrome')) {
      try {
        execSync('npx puppeteer browsers install chrome', { stdio: 'inherit' });
      } catch (installErr) {
        console.error('puppeteer install failed', installErr);
        throw err;
      }
      return launch();
    }
    throw err;
  }
}
