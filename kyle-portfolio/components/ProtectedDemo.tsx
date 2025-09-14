"use client"
import { useMemo, useState } from 'react'

export default function ProtectedDemo({ children }: { children: React.ReactNode }) {
  const hint = process.env.NEXT_PUBLIC_DEMO_HINT || 'Use the provided demo password.'
  const pwd = process.env.NEXT_PUBLIC_LEGEND_ROOM_DEMO_PASSWORD || 'demo123'
  const [input, setInput] = useState('')
  const [ok, setOk] = useState(false)

  const handle = (e: React.FormEvent) => {
    e.preventDefault()
    setOk(input.trim() === pwd)
  }

  if (ok) return <>{children}</>

  return (
    <form onSubmit={handle} className="card p-6 space-y-3">
      <div className="font-medium">Protected Demo</div>
      <p className="muted text-sm">Enter the portfolio demo password to unlock content. Hint: {hint}</p>
      <div className="flex gap-2">
        <input value={input} onChange={e=>setInput(e.target.value)} placeholder="Password" type="password" className="w-full rounded bg-white/5 px-3 py-2 border border-white/10 outline-none focus:border-accent"/>
        <button className="btn btn-primary" type="submit">Unlock</button>
      </div>
    </form>
  )
}

