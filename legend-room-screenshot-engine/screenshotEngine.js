import express from 'express'
import cors from 'cors'
import cloudinaryLib from 'cloudinary'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import { launchBrowser } from './chromium.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const cloudinary = cloudinaryLib.v2

const app = express()
app.use(cors({ origin: '*' }))
app.use(express.json())
const PORT = process.env.PORT || 3010

cloudinary.config({
  cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
  api_key: process.env.CLOUDINARY_API_KEY,
  api_secret: process.env.CLOUDINARY_API_SECRET,
  secure: true,
})

async function captureAndUpload(symbol, chartUrl) {
  let browser = null
  const localUrl = chartUrl || `file://${path.resolve(__dirname, 'chart-template.html')}?symbol=${symbol}`
  const reportsDir = path.resolve(__dirname, 'reports')
  if (!fs.existsSync(reportsDir)) fs.mkdirSync(reportsDir, { recursive: true })
  const screenshotPath = path.join(reportsDir, 'SMOKE.png')

  if (process.env.DRY_RUN === '1') {
    const url = `https://dummyimage.com/1200x750/131722/ffffff&text=${encodeURIComponent(symbol)}+Chart`
    return url
  }

  try {
    browser = await launchBrowser()
    const page = await browser.newPage()
    await page.setViewport({ width: 1200, height: 750 })
    await page.goto(localUrl, { waitUntil: 'domcontentloaded' })
    try {
      await page.waitForSelector('#container', { timeout: 8000 })
    } catch (err) {
      console.warn('chart selector not found before timeout', err?.message)
    }
    await page.waitForTimeout(2000)
    await page.screenshot({ path: screenshotPath })

    if (process.env.CLOUDINARY_CLOUD_NAME && process.env.CLOUDINARY_API_KEY && process.env.CLOUDINARY_API_SECRET) {
      try {
        const uploadResult = await cloudinary.uploader.upload(screenshotPath, {
          public_id: `stock_chart_${symbol.toLowerCase()}_${Date.now()}`,
        })
        return uploadResult.secure_url
      } catch (uploadError) {
        console.warn('Cloudinary upload failed, returning local path', uploadError?.message)
      }
    }
    return screenshotPath
  } finally {
    if (browser) {
      await browser.close()
    }
  }
}

app.all('/screenshot', async (req, res) => {
  const symbolRaw = (req.query?.symbol) || (req.body?.symbol) || 'SPY'
  const pivot = req.query?.pivot ? String(req.query.pivot) : undefined
  const contractions = req.query?.contractions ? String(req.query.contractions) : undefined
  const symbol = String(symbolRaw).toUpperCase().trim()

  try {
    let templateUrl = `file://${path.resolve(__dirname, 'chart-template.html')}?symbol=${symbol}`
    if (pivot) templateUrl += `&pivot=${encodeURIComponent(pivot)}`
    if (contractions) templateUrl += `&contractions=${encodeURIComponent(contractions)}`
    const url = await captureAndUpload(symbol, templateUrl)
    res.status(200).json({ chart_url: url, symbol, pivot, contractions, dry_run: process.env.DRY_RUN === '1' })
  } catch (error) {
    res.status(500).json({ error: error?.message || 'Failed to generate chart' })
  }
})

app.get('/', (_req, res) => {
  res.send('Screenshot service running')
})

app.listen(PORT, () => {
  console.log(`Screenshot service listening on port ${PORT}`)
})
