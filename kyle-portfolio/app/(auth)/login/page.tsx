import type { Metadata } from 'next'
import LoginForm from '@/components/auth/LoginForm'

export const metadata: Metadata = {
  title: 'Sign in – Legend AI',
  description: 'Secure access to private Legend AI projects.',
}

export default function LoginPage({ searchParams }: { searchParams: { callbackUrl?: string } }) {
  const callbackUrl = searchParams?.callbackUrl || '/projects'

  return (
    <main className="mx-auto mt-12 max-w-md rounded-2xl border border-slate-800/80 bg-slate-950/80 p-8 shadow-xl shadow-black/40">
      <div className="space-y-6 text-center">
        <div>
          <h1 className="text-2xl font-semibold text-white">Legend AI Access</h1>
          <p className="mt-2 text-sm text-slate-300">
            Sign in with your administrator credentials to view private project demos.
          </p>
        </div>
        <LoginForm callbackUrl={callbackUrl} />
      </div>
    </main>
  )
}
