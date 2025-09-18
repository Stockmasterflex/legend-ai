'use client'

import Link from 'next/link'
import { useSession } from 'next-auth/react'
import { signOut } from 'next-auth/react'

export function AuthNav() {
  const { data: session, status } = useSession()

  if (status === 'loading') {
    return <span className="btn btn-ghost text-xs opacity-70">Auth…</span>
  }

  if (session) {
    return (
      <button
        type="button"
        className="btn btn-ghost text-sm"
        onClick={() => signOut({ callbackUrl: '/' })}
      >
        Sign out
      </button>
    )
  }

  return (
    <Link href="/login" className="btn btn-ghost text-sm">
      Sign in
    </Link>
  )
}

export default AuthNav
