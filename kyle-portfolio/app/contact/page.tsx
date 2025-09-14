import { Mail, Linkedin } from 'lucide-react'

export default function ContactPage() {
  return (
    <div className="space-y-6 fade-in">
      <h1 className="text-2xl font-semibold">Contact</h1>
      <div className="card p-6 space-y-3">
        <p className="muted text-sm">Open to roles in technical analysis, quantitative research, or applied AI for markets. Reach out professionally:</p>
        <div className="flex flex-wrap gap-3">
          <a className="btn btn-primary" href="mailto:kyle@example.com"><Mail size={18}/> Email</a>
          <a className="btn btn-ghost" href="https://www.linkedin.com/in/kyle-thomas-finance/" target="_blank" rel="noreferrer"><Linkedin size={18}/> LinkedIn</a>
        </div>
        <p className="text-xs muted">Replace email/link with your preferred details and a professional headshot.</p>
      </div>
    </div>
  )
}

