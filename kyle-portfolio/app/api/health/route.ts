import { NextResponse } from 'next/server'

async function checkWithTimeout(url: string, ms = 5000): Promise<boolean> {
  const ctrl = new AbortController()
  const id = setTimeout(() => ctrl.abort(), ms)
  try {
    const res = await fetch(url, { signal: ctrl.signal, cache: 'no-store' })
    return res.ok
  } catch {
    return false
  } finally {
    clearTimeout(id)
  }
}

export async function GET() {
  try {
    const timestamp = new Date().toISOString()

    const [apiOk, shotsOk] = await Promise.all([
      checkWithTimeout('https://legend-api.onrender.com/healthz', 5000),
      checkWithTimeout('https://legend-shots.onrender.com/health', 5000),
    ])

    const services = {
      frontend: true,
      api: apiOk,
      screenshots: shotsOk,
    }

    const allHealthy = Object.values(services).every(Boolean)

    const health = {
      status: allHealthy ? 'healthy' : 'degraded',
      timestamp,
      services,
      uptime: process.uptime(),
      memory: {
        used: Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
        total: Math.round(process.memoryUsage().heapTotal / 1024 / 1024),
      },
      version: process.env.VERCEL_GIT_COMMIT_SHA?.slice(0, 7) || 'unknown',
    }

    return NextResponse.json(health, { status: allHealthy ? 200 : 206 })
  } catch (error) {
    return NextResponse.json(
      { status: 'error', message: 'Health check failed', timestamp: new Date().toISOString() },
      { status: 500 }
    )
  }
}
