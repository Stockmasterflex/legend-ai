import { ArrowRight, BarChart3, BrainCircuit, LineChart } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="space-y-10 fade-in">
      {/* Hero */}
      <section className="text-center">
        <div className="inline-block badge mb-3">Momentum • VCP • AI</div>
        <h1 className="text-3xl md:text-5xl font-semibold tracking-tight">Kyle Holthaus – Technical Analyst & AI Builder</h1>
        <p className="muted mt-3 max-w-2xl mx-auto">Momentum/VCP trader • SIE passed • CMT Level I candidate. Building Legend Room AI — signals, screenshots, and trading intelligence.</p>
        <div className="mt-6 flex items-center justify-center gap-3">
          <a href="/projects" className="btn btn-primary"><BarChart3 size={18}/> View Projects</a>
          <a href="/about" className="btn btn-ghost"><ArrowRight size={18}/> About Kyle</a>
        </div>
      </section>

      {/* Highlights */}
      <section className="grid-cards">
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-2 text-accent"><LineChart size={18}/> Signals</div>
          <p className="text-sm muted">Deterministic detection paths (e.g., VCP) with clean inputs/outputs and contract tests.</p>
        </div>
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-2 text-accent"><BrainCircuit size={18}/> AI Workflows</div>
          <p className="text-sm muted">LLM-assisted scoring and summaries, with safe fallbacks and DRY_RUN options for CI.</p>
        </div>
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-2 text-accent"><BarChart3 size={18}/> Charts</div>
          <p className="text-sm muted">Headless chart screenshots and overlays; dockerized services for reproducible demos.</p>
        </div>
      </section>
    </div>
  )
}

