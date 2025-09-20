import { NextResponse } from 'next/server'

export async function GET() {
  try {
    const systemInfo = {
      timestamp: new Date().toISOString(),
      environment: process.env.NODE_ENV,
      deployment: {
        vercel_url: process.env.VERCEL_URL,
        git_commit: process.env.VERCEL_GIT_COMMIT_SHA?.slice(0, 7),
        region: process.env.VERCEL_REGION,
      },
      services: {
        api: 'https://legend-api.onrender.com',
        screenshots: 'https://legend-shots.onrender.com',
        frontend: 'https://legend-ai.vercel.app',
      },
      features: {
        scanner: 'active',
        platform: 'active',
        auth: 'active',
        monitoring: 'active',
      },
      performance: {
        uptime: process.uptime(),
        memory: process.memoryUsage(),
        node_version: process.version,
      },
    }

    return NextResponse.json(systemInfo)
  } catch (error) {
    return NextResponse.json({ error: 'System info unavailable' }, { status: 500 })
  }
}