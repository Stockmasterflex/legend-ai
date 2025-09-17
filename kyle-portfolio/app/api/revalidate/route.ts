import { revalidatePath } from 'next/cache'
import { NextRequest, NextResponse } from 'next/server'

function normalizeSecret(raw: string | null): string | null {
  if (!raw) return null
  if (raw.startsWith('Bearer ')) return raw.slice(7)
  return raw
}

export async function POST(request: NextRequest) {
  const configuredSecret = process.env.SANITY_REVALIDATE_SECRET
  if (!configuredSecret) {
    return NextResponse.json({ ok: false, revalidated: [], error: 'Revalidation secret not configured' }, { status: 500 })
  }

  const headerSecret = request.headers.get('x-revalidate-secret') || normalizeSecret(request.headers.get('authorization'))
  const querySecret = request.nextUrl.searchParams.get('secret')

  let body: any = null
  try {
    body = await request.json()
  } catch {
    body = null
  }

  const payloadSecret = typeof body?.secret === 'string' ? body.secret : null
  const providedSecret = headerSecret ?? querySecret ?? payloadSecret

  if (!providedSecret || providedSecret !== configuredSecret) {
    return NextResponse.json({ ok: false, revalidated: [], error: 'Unauthorized' }, { status: 401 })
  }

  const slug = body?.slug?.current ?? body?.slug ?? null

  const revalidated: string[] = []
  revalidatePath('/blog')
  revalidated.push('/blog')
  if (typeof slug === 'string' && slug.length > 0) {
    const path = `/blog/${slug}`
    revalidatePath(path)
    revalidated.push(path)
  }
  return NextResponse.json({ ok: true, revalidated })
}
