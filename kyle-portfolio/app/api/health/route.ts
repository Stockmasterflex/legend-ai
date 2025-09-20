import { NextResponse } from 'next/server'

export async function GET() {
  try {
    const timestamp = new Date().toISOString()

    const apiCheck = await fetch('https://legend-api.onrender.com/healthz')
      .then(res => res.ok)
      .catch(() => false)

    const shotCheck = await fetch('https://legend-shots.onrender.com/health')
      .then(res => res.ok)
      .catch(() => false)

    const health = {
      status: 'healthy',
      timestamp,
      services: {
        frontend: true,
        api: apiCheck,
        screenshots: shotCheck,
      },
      uptime: process.uptime(),
      memory: process.memoryUsage(),
      version: process.env.VERCEL_GIT_COMMIT_SHA || 'unknown',
    }

    return NextResponse.json(health)
  } catch (error) {
    return NextResponse.json(
      { status: 'error', message: 'Health check failed' },
      { status: 500 }
    )
  }
}
