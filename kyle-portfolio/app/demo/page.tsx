"use client"
import React from 'react'
import Sparkline from '@/components/Sparkline'

type Candidate = {
  date: string
  symbol: string
  confidence: number
  pivot: number
  price: number
  notes?: string
}

type Summary = {
  precision_at_10: number
  precision_at_25: number
  hit_rate: number
  median_runup: number
  num_candidates: number
  num_triggers: number
  num_success: number
  status?: string
}

type Run = {
  id: number
  created_at: string
  start: string
  end: string
  universe: string
  provider: string
  precision_at_10?: number
  precision_at_25?: number
  hit_rate?: number
  median_runup?: number
  num_candidates?: number
  num_triggers?: number
  num_success?: number
}

const API_BASE = process.env.NEXT_PUBLIC_VCP_API_BASE || 'http://127.0.0.1:8000'

async function fetchWithRetry<T>(url: string, tries = 3, backoffMs = 500): Promise<T> {
  let lastErr: any
  for (let i = 0; i < tries; i++) {
    try {
      const r = await fetch(url, { cache: 'no-store' })
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
      return r.json()
    } catch (e) {
      lastErr = e
      if (i < tries - 1) await new Promise(res => setTimeout(res, backoffMs))
    }
  }
  throw lastErr
}

async function fetchJSON<T>(url: string): Promise<T> { return fetchWithRetry<T>(url, 3, 500) }

// Attempt to fetch sparkline data from Yahoo chart API; if blocked, fall back to synthetic deterministic series
async function fetchSparkline(symbol: string, points = 60): Promise<number[]> {
  try {
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?range=6mo&interval=1d`
    const r = await fetch(url)
    if (r.ok) {
      const j = await r.json()
      const closes: number[] | undefined = j?.chart?.result?.[0]?.indicators?.quote?.[0]?.close
      if (Array.isArray(closes)) {
        const filtered = closes.filter((x: number | null) => typeof x === 'number') as number[]
        if (filtered.length) return filtered.slice(-points)
      }
    }
  } catch {}
  // Fallback: pseudo-random but deterministic by symbol
  const seed = Array.from(symbol).reduce((a, c) => a + c.charCodeAt(0), 0)
  let x = seed % 97 + 3
  const series: number[] = []
  for (let i = 0; i < points; i++) {
    x = (x * 1103515245 + 12345) % 2 ** 31
    const delta = (x / 2 ** 31) - 0.5
    const last = series.length ? series[series.length - 1] : 100
    series.push(Math.max(1, last + delta * 2))
  }
  return series
}

export default function DemoPage() {
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)
  const [candidates, setCandidates] = React.useState<Candidate[]>([])
  const [summary, setSummary] = React.useState<Summary | null>(null)
  const [sparks, setSparks] = React.useState<Record<string, number[]>>({})
  const [healthy, setHealthy] = React.useState<boolean | null>(null)
  const [runs, setRuns] = React.useState<Run[]>([])
  const [selectedRunId, setSelectedRunId] = React.useState<number | null>(null)
  const [selectedDay, setSelectedDay] = React.useState<string>('')
  const [availableDays, setAvailableDays] = React.useState<string[]>([])
  const [runDetail, setRunDetail] = React.useState<any|null>(null)

  const start = React.useMemo(() => new Date(Date.now() - 90 * 864e5).toISOString().slice(0, 10), [])
  const end = React.useMemo(() => new Date().toISOString().slice(0, 10), [])

  const load = React.useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      // health check
      try {
        const hz = await fetchWithRetry<{ ok: boolean }>(`${API_BASE}/healthz`, 2, 500)
        setHealthy(!!hz?.ok)
      } catch {
        setHealthy(false)
      }
      // load recent runs, pick latest by created_at
      const runResp = await fetchJSON<{ runs: Run[] }>(`${API_BASE}/api/v1/runs?limit=50`)
      const sorted = (runResp.runs || []).slice().sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))
      setRuns(sorted)
      const latest = sorted[0] || null
      const runId = latest?.id ?? null
      setSelectedRunId(runId)
      const met = runId
        ? await fetchJSON<Summary>(`${API_BASE}/api/v1/vcp/metrics?run_id=${runId}`)
        : await fetchJSON<Summary>(`${API_BASE}/api/v1/vcp/metrics?start=${start}&end=${end}`)
      setSummary(met || null)
      // default day: today
      // days index for selected run (or global)
      const daysResp = runId
        ? await fetchJSON<{ days: string[] }>(`${API_BASE}/api/v1/vcp/candidates?run_id=${runId}`)
        : await fetchJSON<{ days: string[] }>(`${API_BASE}/api/v1/vcp/candidates`)
      const days = daysResp.days || []
      setAvailableDays(days)
      const defaultDay = days[days.length - 1] || new Date().toISOString().slice(0, 10)
      setSelectedDay(defaultDay)
      // candidates for default day
      const cands = await fetchJSON<{ rows: Candidate[] }>(`${API_BASE}/api/v1/vcp/candidates?day=${defaultDay}${runId?`&run_id=${runId}`:''}`)
      setCandidates(cands.rows || [])
      // fetch sparklines in parallel
      const map: Record<string, number[]> = {}
      await Promise.all((cands.rows || []).map(async (r) => {
        map[r.symbol] = await fetchSparkline(r.symbol)
      }))
      setSparks(map)
    } catch (e: any) {
      setError(e?.message || 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }, [start, end])

  React.useEffect(() => {
    load()
  }, [load])

  const rescan = async () => {
    setLoading(true)
    setError(null)
    try {
      await fetchJSON(`${API_BASE}/api/v1/vcp/today`)
      // refresh candidates for same selectedDay
      const cands = await fetchJSON<{ rows: Candidate[] }>(`${API_BASE}/api/v1/vcp/candidates?day=${selectedDay}${selectedRunId?`&run_id=${selectedRunId}`:''}`)
      setCandidates(cands.rows || [])
      // re-fetch sparks
      const map: Record<string, number[]> = {}
      await Promise.all((cands.rows || []).map(async (r) => {
        map[r.symbol] = await fetchSparkline(r.symbol)
      }))
      setSparks(map)
    } catch (e: any) {
      setError(e?.message || 'Rescan failed')
      setLoading(false)
    }
  }

  const onSelectRun = async (val: string) => {
    const id = val ? parseInt(val, 10) : NaN
    if (!Number.isFinite(id)) return
    setSelectedRunId(id)
    setLoading(true)
    setError(null)
    try {
      const met = await fetchJSON<Summary>(`${API_BASE}/api/v1/vcp/metrics?run_id=${id}`)
      setSummary(met || null)
      const detail = await fetchJSON<{ run: any, artifacts: any, days: string[] }>(`${API_BASE}/api/v1/runs/${id}`)
      setRunDetail(detail)
      // refresh days index
      const days = detail.days || []
      setAvailableDays(days)
      const latest = days[days.length - 1] || ''
      if (latest) {
        setSelectedDay(latest)
        const cands = await fetchJSON<{ rows: Candidate[] }>(`${API_BASE}/api/v1/vcp/candidates?day=${latest}&run_id=${id}`)
        setCandidates(cands.rows || [])
        const map: Record<string, number[]> = {}
        await Promise.all((cands.rows || []).map(async (r) => { map[r.symbol] = await fetchSparkline(r.symbol) }))
        setSparks(map)
      }
    } catch (e: any) {
      setError(e?.message || 'Failed to load run metrics')
    } finally {
      setLoading(false)
    }
  }

  const onSelectDay = async (val: string) => {
    setSelectedDay(val)
    setLoading(true)
    setError(null)
    try {
      const cands = await fetchJSON<{ rows: Candidate[] }>(`${API_BASE}/api/v1/vcp/candidates?day=${val}${selectedRunId?`&run_id=${selectedRunId}`:''}`)
      setCandidates(cands.rows || [])
      const map: Record<string, number[]> = {}
      await Promise.all((cands.rows || []).map(async (r) => {
        map[r.symbol] = await fetchSparkline(r.symbol)
      }))
      setSparks(map)
    } catch (e: any) {
      setError(e?.message || 'Failed to load candidates')
    } finally {
      setLoading(false)
    }
  }

  const exportCSV = () => {
    if (!candidates || candidates.length === 0) return
    const headers = ['date','symbol','price','pivot','confidence','notes']
    const rows = candidates.map(r => [r.date, r.symbol, r.price, r.pivot, r.confidence, (r.notes||'').replace(/\n/g,' ')])
    const lines = [headers.join(','), ...rows.map(r=>r.join(','))]
    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `candidates_${new Date().toISOString().slice(0,10)}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  // Simple Run creation UI state
  const [newRun, setNewRun] = React.useState({ start, end, universe: 'simple', provider: 'yfinance' })
  const [creating, setCreating] = React.useState(false)
  const createRun = async () => {
    setCreating(true)
    try {
      const qs = new URLSearchParams(newRun as any).toString()
      const res = await fetch(`${API_BASE}/api/v1/runs?${qs}`, { method: 'POST' })
      if (!res.ok) throw new Error(`${res.status}`)
      const j = await res.json()
      // Set selected run to new id and reload metrics/days
      if (j.run_id || j.id || j.run?.id) {
        const rid = j.run_id || j.id || j.run.id
        await onSelectRun(String(rid))
      }
    } catch (e: any) {
      setError(e?.message || 'Failed to create run')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold flex items-center gap-2">Legend Room – Demo
          <span title={healthy === null ? 'checking…' : healthy ? 'healthy' : 'unreachable'}
            className={`inline-block w-2.5 h-2.5 rounded-full ${healthy===null?'bg-white/40 animate-pulse':healthy?'bg-green-500':'bg-red-500'}`} />
        </h1>
        <div className="flex items-center gap-2">
          <a className="btn btn-ghost" href="/dashboard">Dashboard</a>
          <div className="flex items-center gap-2">
            <label className="text-xs muted">Run</label>
            <select className="select select-sm" value={selectedRunId ?? ''} onChange={(e)=>onSelectRun(e.target.value)}>
              <option value="">Ad-hoc ({start} → {end})</option>
              {runs.map(r => (
                <option key={r.id} value={r.id}>#{r.id} {r.start} → {r.end} ({r.universe})</option>
              ))}
            </select>
            {!!selectedRunId && <a className="btn btn-ghost btn-xs" href={`/runs/${selectedRunId}`}>Open</a>}
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs muted">Day</label>
            <select className="select select-sm" value={selectedDay} onChange={(e)=>onSelectDay(e.target.value)}>
              {availableDays.map(d => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
          <button className="btn btn-ghost" onClick={exportCSV} disabled={!candidates.length}>Export latest CSV</button>
          <button className="btn btn-primary" onClick={rescan} disabled={loading}>{loading ? 'Scanning…' : 'Rescan Today'}</button>
        </div>
      </div>

      {/* Create Run */}
      <div className="card p-4 flex flex-wrap items-end gap-3">
        <div>
          <label className="text-xs muted">Start</label>
          <input type="date" className="input input-sm" value={newRun.start} onChange={e=>setNewRun(v=>({...v, start: e.target.value}))} />
        </div>
        <div>
          <label className="text-xs muted">End</label>
          <input type="date" className="input input-sm" value={newRun.end} onChange={e=>setNewRun(v=>({...v, end: e.target.value}))} />
        </div>
        <div>
          <label className="text-xs muted">Universe</label>
          <input type="text" className="input input-sm" value={newRun.universe} onChange={e=>setNewRun(v=>({...v, universe: e.target.value}))} />
        </div>
        <div>
          <label className="text-xs muted">Provider</label>
          <input type="text" className="input input-sm" value={newRun.provider} onChange={e=>setNewRun(v=>({...v, provider: e.target.value}))} />
        </div>
        <button className="btn" onClick={createRun} disabled={creating}>{creating ? 'Enqueuing…' : 'Create Run'}</button>
      </div>

      {/* KPI header */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPI title="Precision@10" value={fmtPct(summary?.precision_at_10)} />
        <KPI title="Precision@25" value={fmtPct(summary?.precision_at_25)} />
        <KPI title="Hit Rate" value={fmtPct(summary?.hit_rate)} />
        <KPI title="Median Run-up" value={fmtPct(summary?.median_runup)} />
      </section>

      {/* Errors / Empty */}
      {error && <div className="card p-4 text-sm text-red-300">Unable to load data from the backend. Please ensure the API is running at {API_BASE}. Error: {error}</div>}
      {!error && !loading && candidates.length === 0 && (
        <div className="card p-6 text-sm muted">No candidates today. Try Rescan or adjust your backtest window for metrics.</div>
      )}

      {/* Loading */}
      {loading && (
        <div className="card p-6 animate-pulse text-sm muted">Loading data…</div>
      )}

      {/* Candidates table */}
      {!loading && candidates.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="card overflow-x-auto lg:col-span-2">
          <table className="min-w-full text-sm">
            <thead className="text-left muted">
              <tr>
                <th className="px-4 py-3">Symbol</th>
                <th className="px-4 py-3">Price</th>
                <th className="px-4 py-3">Pivot</th>
                <th className="px-4 py-3">Confidence</th>
                <th className="px-4 py-3">Chart</th>
                <th className="px-4 py-3">Notes</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((r) => (
                <tr key={`${r.date}-${r.symbol}`} className="border-t border-white/5 hover:bg-white/5 cursor-pointer" onClick={()=>window.open(`https://finance.yahoo.com/quote/${encodeURIComponent(r.symbol)}`, '_blank')}>
                  <td className="px-4 py-3 font-medium underline">{r.symbol}</td>
                  <td className="px-4 py-3">{fmtNum(r.price)}</td>
                  <td className="px-4 py-3">{fmtNum(r.pivot)}</td>
                  <td className="px-4 py-3">{r.confidence.toFixed(1)}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Sparkline data={sparks[r.symbol] || []} />
                      <button className="btn btn-ghost btn-xs" onClick={async (e)=>{e.stopPropagation(); try{ const res = await fetch(`${API_BASE}/api/v1/chart?symbol=${encodeURIComponent(r.symbol)}`); const j = await res.json(); const url = j.chart_url || j.engine?.chart_url || j.local_png; if (url) window.open(url, '_blank'); } catch{}}}>Chart</button>
                    </div>
                  </td>
                  <td className="px-4 py-3 max-w-[24ch] truncate" title={r.notes || ''}>{r.notes || ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
          <div className="card p-4 space-y-3">
            <div className="text-sm font-semibold">Run Details</div>
            <div className="text-xs break-words">
              <div><span className="muted">Run ID:</span> {selectedRunId ?? '—'}</div>
              {!!runDetail?.artifacts?.summary && (
                <div><a className="link" href={runDetail.artifacts.summary} target="_blank">Summary JSON</a></div>
              )}
              {!!runDetail?.artifacts?.daily_candidates_dir && (
                <div><a className="link" href={runDetail.artifacts.daily_candidates_dir} target="_blank">Daily candidates dir</a></div>
              )}
              <div className="mt-2">
                <div className="muted">Days</div>
                <div className="max-h-48 overflow-auto space-y-1">
                  {(availableDays || []).slice(-30).map(d => (
                    <button key={d} className={`btn btn-ghost btn-xs w-full text-left ${d===selectedDay?'bg-white/10':''}`} onClick={()=>onSelectDay(d)}>{d}</button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function KPI({ title, value }: { title: string, value: string }) {
  return (
    <div className="card p-4">
      <div className="text-xs muted">{title}</div>
      <div className="text-xl font-semibold">{value}</div>
    </div>
  )
}

function fmtPct(x?: number) {
  if (typeof x !== 'number' || Number.isNaN(x)) return '—'
  // hit_rate may be proportion (0..1) or percent (0..100) depending on upstream; normalize
  const v = x > 1 ? x : x * 100
  return `${v.toFixed(1)}%`
}

function fmtNum(x?: number) {
  if (typeof x !== 'number' || Number.isNaN(x)) return '—'
  return x >= 100 ? x.toFixed(2) : x.toFixed(3)
}
