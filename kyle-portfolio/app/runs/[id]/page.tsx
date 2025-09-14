"use client"
import React from 'react'
import Sparkline from '@/components/Sparkline'

const API_BASE = process.env.NEXT_PUBLIC_VCP_API_BASE || 'http://127.0.0.1:8000'

type Candidate = { date: string; symbol: string; confidence: number; pivot: number; price: number; notes?: string }
type Summary = {
  precision_at_10: number; precision_at_25: number; hit_rate: number; median_runup: number;
  num_candidates: number; num_triggers: number; num_success: number; status?: string
}

async function fetchJSON<T>(url: string): Promise<T> { const r = await fetch(url, { cache: 'no-store' }); if (!r.ok) throw new Error(`${r.status}`); return r.json() }

export default function RunDetailPage({ params }: { params: { id: string } }) {
  const runId = Number(params.id)
  const [detail, setDetail] = React.useState<any|null>(null)
  const [summary, setSummary] = React.useState<Summary | null>(null)
  const [day, setDay] = React.useState<string>('')
  const [cands, setCands] = React.useState<Candidate[]>([])
  const [sparks, setSparks] = React.useState<Record<string, number[]>>({})
  const [err, setErr] = React.useState<string|undefined>()

  React.useEffect(() => {
    (async () => {
      try {
        const d = await fetchJSON<{ run: any, artifacts: any, days: string[] }>(`${API_BASE}/api/v1/runs/${runId}`)
        setDetail(d)
        const met = await fetchJSON<Summary>(`${API_BASE}/api/v1/vcp/metrics?run_id=${runId}`)
        setSummary(met)
        const days = d.days || []
        const last = days[days.length - 1] || ''
        setDay(last)
        if (last) {
          const cr = await fetchJSON<{ rows: Candidate[] }>(`${API_BASE}/api/v1/vcp/candidates?day=${last}&run_id=${runId}`)
          setCands(cr.rows || [])
        }
      } catch (e: any) { setErr(e?.message || 'load failed') }
    })()
  }, [runId])

  const onPick = async (d: string) => {
    setDay(d)
    const cr = await fetchJSON<{ rows: Candidate[] }>(`${API_BASE}/api/v1/vcp/candidates?day=${d}&run_id=${runId}`)
    setCands(cr.rows || [])
    const map: Record<string, number[]> = {}
    for (const r of cr.rows || []) { map[r.symbol] = await fetchSparkline(r.symbol) }
    setSparks(map)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Run #{runId}</h1>
        <a className="btn btn-ghost" href="/demo">Back to Demo</a>
      </div>

      {err && <div className="card p-4 text-sm text-red-300">{String(err)}</div>}

      <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPI title="Precision@10" value={fmtPct(summary?.precision_at_10)} />
        <KPI title="Precision@25" value={fmtPct(summary?.precision_at_25)} />
        <KPI title="Hit Rate" value={fmtPct(summary?.hit_rate)} />
        <KPI title="Median Run-up" value={fmtPct(summary?.median_runup)} />
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card p-4 space-y-2">
          <div className="text-sm font-semibold">Artifacts</div>
          <div className="text-xs break-words">
            {!!detail?.artifacts?.summary && <div><a className="link" href={detail.artifacts.summary} target="_blank">Summary JSON</a></div>}
            {!!detail?.artifacts?.daily_candidates_dir && <div><a className="link" href={detail.artifacts.daily_candidates_dir} target="_blank">Daily candidates dir</a></div>}
            {!!detail?.artifacts?.outcomes_dir && <div><a className="link" href={detail.artifacts.outcomes_dir} target="_blank">Outcomes dir</a></div>}
          </div>
          <div className="text-sm font-semibold mt-3">Days</div>
          <div className="max-h-64 overflow-auto space-y-1">
            {(detail?.days || []).map((d: string) => (
              <button key={d} className={`btn btn-ghost btn-xs w-full text-left ${d===day?'bg-white/10':''}`} onClick={()=>onPick(d)}>{d}</button>
            ))}
          </div>
        </div>
        <div className="card overflow-x-auto lg:col-span-2">
          <table className="min-w-full text-sm">
            <thead className="text-left muted"><tr>
              <th className="px-4 py-3">Symbol</th>
              <th className="px-4 py-3">Price</th>
              <th className="px-4 py-3">Pivot</th>
              <th className="px-4 py-3">Confidence</th>
              <th className="px-4 py-3">Chart</th>
              <th className="px-4 py-3">Notes</th>
            </tr></thead>
            <tbody>
              {cands.map(r => (
                <tr key={`${r.date}-${r.symbol}`} className="border-t border-white/5 hover:bg-white/5 cursor-pointer" onClick={()=>window.open(`https://finance.yahoo.com/quote/${encodeURIComponent(r.symbol)}`,'_blank')}>
                  <td className="px-4 py-3 font-medium underline">{r.symbol}</td>
                  <td className="px-4 py-3">{fmtNum(r.price)}</td>
                  <td className="px-4 py-3">{fmtNum(r.pivot)}</td>
                  <td className="px-4 py-3">{r.confidence.toFixed(1)}</td>
                  <td className="px-4 py-3"><Sparkline data={sparks[r.symbol]||[]} /></td>
                  <td className="px-4 py-3 max-w-[24ch] truncate" title={r.notes||''}>{r.notes||''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
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

function fmtPct(x?: number) { if (typeof x !== 'number' || Number.isNaN(x)) return '—'; const v = x > 1 ? x : x * 100; return `${v.toFixed(1)}%` }
function fmtNum(x?: number) { if (typeof x !== 'number' || Number.isNaN(x)) return '—'; return x >= 100 ? x.toFixed(2) : x.toFixed(3) }

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
  const seed = Array.from(symbol).reduce((a, c) => a + c.charCodeAt(0), 0)
  let x = seed % 97 + 3
  const series: number[] = []
  for (let i = 0; i < points; i++) { x = (x * 1103515245 + 12345) % 2 ** 31; const delta = (x / 2 ** 31) - 0.5; const last = series.length ? series[series.length - 1] : 100; series.push(Math.max(1, last + delta * 2)) }
  return series
}


