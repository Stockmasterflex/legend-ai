export default function AboutPage() {
  return (
    <div className="space-y-6 fade-in">
      <h1 className="text-2xl font-semibold">About Kyle</h1>
      <div className="card p-6 space-y-3">
        <p>Kyle Holthaus is a technical analyst and AI builder focused on momentum and VCP-style trading. He combines robust market structure with pragmatic engineering to ship reliable trading tools.</p>
        <ul className="list-disc pl-5 muted">
          <li>SIE passed • CMT Level I candidate</li>
          <li>Momentum/VCP trader trained on Minervini principles</li>
          <li>Python, FastAPI, Next.js, Tailwind; Dockerized microservices</li>
          <li>Hands-on with yfinance, SQLAlchemy, headless Chromium for charts</li>
        </ul>
      </div>
      <div className="card p-6">
        <h2 className="font-medium mb-2">Skills</h2>
        <div className="flex flex-wrap gap-2">
          {['Technical Analysis','Pattern Detection','Backtesting (thin)','FastAPI','Next.js','TypeScript','Docker','CI','Prompt/LLM'].map(s => (
            <span key={s} className="badge">{s}</span>
          ))}
        </div>
      </div>
    </div>
  )
}

