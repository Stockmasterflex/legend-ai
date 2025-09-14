import ProtectedDemo from '@/components/ProtectedDemo'

export default function ProjectsPage() {
  return (
    <div className="space-y-8 fade-in">
      <h1 className="text-2xl font-semibold">Projects</h1>

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

      <ProtectedDemo>
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
      </ProtectedDemo>
    </div>
  )
}

