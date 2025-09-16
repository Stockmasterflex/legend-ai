import chromium from '@sparticuz/chromium'
import puppeteer from 'puppeteer-core'

export async function launchBrowser() {
  const executablePath = await chromium.executablePath()
  return puppeteer.launch({
    executablePath,
    headless: 'new',
    args: [
      ...chromium.args,
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
    ],
    defaultViewport: chromium.defaultViewport,
  })
}
