import { redirect } from 'next/navigation'
import { auth } from '@/lib/auth'
import SignOutButton from '@/components/auth/SignOutButton'

export default async function ProjectsPage() {
  const session = await auth()
  if (!session) {
    redirect('/login?callbackUrl=/projects')
  }

  return (
    <div className="space-y-8 fade-in">
      <h1 className="text-2xl font-semibold">Projects</h1>

      <div className="flex items-center justify-between rounded-lg border border-slate-800/80 bg-slate-950/70 px-5 py-3 text-sm text-slate-300">
        <div>
          <p className="text-xs uppercase text-slate-500">Authenticated</p>
          <p>Signed in as <span className="text-white">{session.user?.email}</span></p>
        </div>
        <SignOutButton />
      </div>

      <section className="card p-6 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-medium">Legend Room AI</h2>
            <p className="muted text-sm">Signals, screenshots, and trading intelligence. Dockerized microservices (FastAPI backend + headless screenshot engine).</p>
          </div>
          <a className="btn btn-ghost" href="https://github.com/Stockmasterflex" target="_blank" rel="noreferrer">GitHub</a>
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <div className="badge">Highlights</div>
            <ul className="list-disc pl-5 muted text-sm">
              <li>Standard API: /api/health, /api/screenshot, /api/price</li>
              <li>DRY_RUN mode for fast CI</li>
              <li>Headless chart capture (Chromium)</li>
            </ul>
          </div>
          <div className="space-y-2">
            <div className="badge">Tech</div>
            <ul className="list-disc pl-5 muted text-sm">
              <li>Python (FastAPI), SQLAlchemy, yfinance</li>
              <li>Node/Chromium for screenshot service</li>
              <li>Docker Compose + GitHub Actions</li>
            </ul>
          </div>
        </div>
      </section>
      <section className="card p-6 space-y-3">
        <h3 className="font-medium">Private Demo</h3>
        <p className="muted text-sm">A preview of the trading dashboard and signal outputs. Replace mock data with live APIs later.</p>
        <div className="grid gap-3 md:grid-cols-3">
          <div className="bg-white/5 p-4 rounded">
            <div className="text-xs muted">Signal</div>
            <div className="text-green-400 font-medium">VCP (High)</div>
          </div>
          <div className="bg-white/5 p-4 rounded">
            <div className="text-xs muted">Pivot</div>
            <div className="font-medium">$945.10</div>
          </div>
          <div className="bg-white/5 p-4 rounded">
            <div className="text-xs muted">Setup Quality</div>
            <div className="font-medium">A-</div>
          </div>
        </div>
      </section>
    </div>
  )
}
