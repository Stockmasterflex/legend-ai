'use client'

import { signOut } from 'next-auth/react'

export function SignOutButton() {
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

export default SignOutButton
