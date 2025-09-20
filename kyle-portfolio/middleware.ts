import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const username = process.env.STUDIO_USERNAME
const password = process.env.STUDIO_PASSWORD

export const config = {
  matcher: ['/studio/:path*', '/api/:path*', '/platform/:path*'],
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Optional basic auth for /studio if credentials are provided
  if (pathname.startsWith('/studio')) {
    if (!username || !password) {
      return NextResponse.next()
    }

    const authHeader = request.headers.get('authorization')
    if (authHeader) {
      const [scheme, encoded] = authHeader.split(' ')
      if (scheme === 'Basic' && encoded) {
        const decoded = atob(encoded)
        const separatorIndex = decoded.indexOf(':')
        if (separatorIndex > -1) {
          const user = decoded.slice(0, separatorIndex)
          const pass = decoded.slice(separatorIndex + 1)
          if (user === username && pass === password) {
            return NextResponse.next()
          }
        }
      }
    }

    return new NextResponse('Authentication required', {
      status: 401,
      headers: {
        'WWW-Authenticate': 'Basic realm="Legend Studio"',
      },
    })
  }

  // Placeholder: add rate limiting for /api if desired
  if (pathname.startsWith('/api/')) {
    return NextResponse.next()
  }

  // Placeholder: protect /platform in the future (currently open)
  if (pathname.startsWith('/platform')) {
    return NextResponse.next()
  }

  return NextResponse.next()
}
