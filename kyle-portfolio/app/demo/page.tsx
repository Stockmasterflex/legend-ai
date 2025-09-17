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
type Signal = {
  score: number
  reasons: string[]
  badges?: string[]
}
type Sentiment = {
  label: 'bullish'|'neutral'|'bearish'|string
  score?: number
  confidence?: number
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

type ScanLevels = { entry: number; stop: number; targets: number[] }

type ChartMeta = {
  fallback: boolean
  overlay_applied: boolean
  source: string
  overlay_counts?: { lines?: number; boxes?: number; labels?: number; arrows?: number; zones?: number }
  error?: string
  duration_ms?: number
}

type ScanRow = {
  symbol: string
  score: number
  entry: number
  stop: number
  targets: number[]
  chart_url?: string | null
  overlays?: any
  pattern?: string
  meta?: any
  key_levels?: ScanLevels
  avg_price?: number
  avg_volume?: number
  atr14?: number
  chart_meta?: ChartMeta | null
}

type PatternOption = 'vcp'|'cup_handle'|'hns'|'flag'|'wedge'|'double'
type UniverseOption = 'sp500'|'nasdaq100'
type TimeframeOption = '1d'|'1wk'|'60m'

const PATTERN_LABELS: Record<PatternOption, string> = {
  vcp: 'VCP',
  cup_handle: 'Cup & Handle',
  hns: 'Head & Shoulders',
  flag: 'Flag / Pennant',
  wedge: 'Wedge',
  double: 'Double Top / Bottom',
}

const TIMEFRAME_LABELS: Record<TimeframeOption, string> = {
  '1d': 'Daily',
  '1wk': 'Weekly',
  '60m': '60 min',
}

const API_BASE = (process.env.NEXT_PUBLIC_VCP_API_BASE as string) || (process.env.NEXT_PUBLIC_API_BASE as string) || "https://legend-api.onrender.com"
const USE_REMOTE_SPARKLINE = process.env.NEXT_PUBLIC_USE_REMOTE_SPARKLINE === '1'

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
  if (!USE_REMOTE_SPARKLINE) {
    return generateFallbackSparkline(symbol, points)
  }
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
  return generateFallbackSparkline(symbol, points)
}

function generateFallbackSparkline(symbol: string, points = 60): number[] {
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

async function fetchChart(
  symbol: string,
  opts?: { pivot?: number|null, entry?: number|null, stop?: number|null, target?: number|null, pattern?: string, overlays?: any }
): Promise<{ url: string | null, meta?: ChartMeta }> {
  try {
    const q = new URLSearchParams({ symbol })
    if (opts?.pivot != null) q.set('pivot', String(opts.pivot))
    if (opts?.entry != null) q.set('entry', String(opts.entry))
    if (opts?.stop != null) q.set('stop', String(opts.stop))
    if (opts?.target != null) q.set('target', String(opts.target))
    if (opts?.pattern) q.set('pattern', opts.pattern)
    const hasOverlays = opts?.overlays && typeof opts.overlays === 'object' && Object.keys(opts.overlays).length > 0
    const endpoint = `${API_BASE}/api/v1/chart?${q.toString()}`
    const init: RequestInit | undefined = hasOverlays
      ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ overlays: opts?.overlays }) }
      : undefined
    const r = await fetch(endpoint, init)
    if (!r.ok) return { url: null }
    const j = await r.json()
    return {
      url: typeof j?.chart_url === 'string' ? j.chart_url : null,
      meta: j?.meta as ChartMeta | undefined,
    }
  } catch {
    return { url: null }
  }
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
  const [isSample, setIsSample] = React.useState(false)
  const [signalMap, setSignalMap] = React.useState<Record<string, Signal>>({})
  const [sentMap, setSentMap] = React.useState<Record<string, Sentiment>>({})
  // Inline chart preview cache per symbol
  const [chartUrls, setChartUrls] = React.useState<Record<string, string | null>>({})
  const [scanPattern, setScanPattern] = React.useState<PatternOption>('vcp')
  const [scanUniverse, setScanUniverse] = React.useState<UniverseOption>('sp500')
  const [scanTimeframe, setScanTimeframe] = React.useState<TimeframeOption>('1d')
  const [minPrice, setMinPrice] = React.useState<string>('20')
  const [minVolume, setMinVolume] = React.useState<string>('750000')
  const [maxAtrRatio, setMaxAtrRatio] = React.useState<string>('0.08')
  const [showOverlays, setShowOverlays] = React.useState(true)
  const [scanLoading, setScanLoading] = React.useState(false)
  const [scanError, setScanError] = React.useState<string | null>(null)
  const [scanResults, setScanResults] = React.useState<ScanRow[]>([])
  const [expandedRows, setExpandedRows] = React.useState<Record<string, boolean>>({})
  const [chartMeta, setChartMeta] = React.useState<Record<string, ChartMeta | undefined>>({})

  const start = React.useMemo(() => new Date(Date.now() - 90 * 864e5).toISOString().slice(0, 10), [])
  const end = React.useMemo(() => new Date().toISOString().slice(0, 10), [])
  const priceFormatter = React.useMemo(() => new Intl.NumberFormat(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 }), [])
  const scoreFormatter = React.useMemo(() => new Intl.NumberFormat(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 }), [])
  const volumeFormatter = React.useMemo(() => new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 }), [])

  const formatPrice = React.useCallback((value?: number | null) => {
    if (value == null || Number.isNaN(value)) return '—'
    return `$${priceFormatter.format(value)}`
  }, [priceFormatter])

  const formatTargets = React.useCallback((targets?: number[]) => {
    if (!Array.isArray(targets) || targets.length === 0) return '—'
    return targets.map(t => `$${priceFormatter.format(t)}`).join(', ')
  }, [priceFormatter])

  const copyText = React.useCallback(async (label: string, value?: string | null) => {
    if (!value) return
    try {
      await navigator.clipboard.writeText(value)
    } catch (err) {
      console.error('clipboard copy failed', label, err)
    }
  }, [])

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
      let rows: Candidate[] = []
      try {
        const cands = await fetchJSON<{ rows: Candidate[] }>(`${API_BASE}/api/v1/vcp/candidates?day=${defaultDay}${runId?`&run_id=${runId}`:''}`)
        rows = cands.rows || []
      } catch {}
      if ((!rows || rows.length === 0) && (runs || []).length === 0) {
        try {
          const latest = await fetchWithRetry<any>(`${API_BASE}/api/latest_run`, 2, 400)
          setIsSample(!!latest?.is_sample)
          const today = new Date().toISOString().slice(0, 10)
          rows = (latest?.patterns || []).map((p: any) => ({
            date: today,
            symbol: p.ticker || p.symbol || 'SAMPLE',
            confidence: typeof p.score === 'number' ? p.score : 75,
            pivot: typeof p.r_breakout === 'number' ? p.r_breakout : 0,
            price: 0,
            notes: 'Sample data',
          }))
        } catch {}
      }
      setCandidates(rows || [])
      // fetch sparklines + signals + sentiment in parallel
      const map: Record<string, number[]> = {}
      const sMap: Record<string, Signal> = {}
      const senMap: Record<string, Sentiment> = {}
      await Promise.all((rows || []).map(async (r) => {
        map[r.symbol] = await fetchSparkline(r.symbol)
        try {
          const sigResp = await fetchWithRetry<{ symbol: string, signal: Signal }>(`${API_BASE}/api/v1/signals?symbol=${encodeURIComponent(r.symbol)}`, 2, 400)
          if (sigResp?.signal) sMap[r.symbol] = sigResp.signal
        } catch {}
        try {
          const senResp = await fetchWithRetry<{ symbol: string, sentiment: any, is_sample?: boolean }>(`${API_BASE}/api/v1/sentiment?symbol=${encodeURIComponent(r.symbol)}`, 1, 0)
          const lab = (senResp?.sentiment?.label || 'neutral') as any
          if (lab && lab !== 'neutral') senMap[r.symbol] = { label: lab, score: senResp.sentiment?.score, confidence: senResp.sentiment?.confidence }
        } catch {}
      }))
      setSparks(map)
      setSignalMap(sMap)
      setSentMap(senMap)
    } catch (e: any) {
      setError(e?.message || 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }, [start, end])

  React.useEffect(() => {
    load()
  }, [load])

  const runScan = React.useCallback(async () => {
    setScanLoading(true)
    setScanError(null)
    try {
      const minPriceVal = Number(minPrice || 0) || 0
      const minVolumeVal = Number(minVolume || 0) || 0
      const maxAtrVal = maxAtrRatio.trim() ? Number(maxAtrRatio) : 0
      const qs = new URLSearchParams({
        pattern: scanPattern,
        universe: scanUniverse,
        limit: '100',
        timeframe: scanTimeframe,
        min_price: String(minPriceVal),
        min_volume: String(minVolumeVal),
      })
      if (maxAtrVal > 0) {
        qs.set('max_atr_ratio', String(maxAtrVal))
      }
      const resp = await fetchWithRetry<{ results: ScanRow[] }>(`${API_BASE}/api/v1/scan?${qs.toString()}`, 2, 600)
      const rows = Array.isArray(resp?.results) ? resp.results : []
      const sanitized = rows.map((row) => ({
        ...row,
        pattern: row.pattern || scanPattern,
        score: Number(row.score ?? 0),
        entry: Number(row.entry ?? row?.key_levels?.entry ?? 0),
        stop: Number(row.stop ?? row?.key_levels?.stop ?? 0),
        targets: Array.isArray(row.targets) ? row.targets.map((t) => Number(t)) : Array.isArray(row.key_levels?.targets) ? row.key_levels!.targets.map(Number) : [],
        chart_meta: row.chart_meta ?? null,
      }))
      setScanResults(sanitized)
      setExpandedRows({})
      const map: Record<string, string | null> = {}
      const metaMap: Record<string, ChartMeta | undefined> = {}
      sanitized.forEach(r => {
        if (typeof r.chart_url === 'string') map[r.symbol] = r.chart_url
        if (r.chart_meta) metaMap[r.symbol] = r.chart_meta
      })
      if (Object.keys(map).length) {
        setChartUrls(prev => ({ ...prev, ...map }))
      }
      if (Object.keys(metaMap).length) {
        setChartMeta(prev => ({ ...prev, ...metaMap }))
      }
      if (!sanitized.length) {
        setScanError('No matches found')
      }
    } catch (e: any) {
      setScanError(e?.message || 'Scan failed')
      setExpandedRows({})
      setScanResults([])
    } finally {
      setScanLoading(false)
    }
  }, [scanPattern, scanUniverse, scanTimeframe, minPrice, minVolume, maxAtrRatio])

  const ensureScanChart = async (row: ScanRow): Promise<string | null> => {
    const existingMeta = chartMeta[row.symbol]
    if (chartUrls[row.symbol] && existingMeta && (!!existingMeta.overlay_applied) === showOverlays) {
      return chartUrls[row.symbol] ?? null
    }
    try {
      const primaryTarget = Array.isArray(row.targets) && row.targets.length ? row.targets[0] : null
      const { url, meta } = await fetchChart(row.symbol, {
        entry: row.entry ?? row.key_levels?.entry ?? null,
        stop: row.stop ?? row.key_levels?.stop ?? null,
        target: primaryTarget ?? row.key_levels?.targets?.[0] ?? null,
        pattern: row.pattern || scanPattern,
        overlays: showOverlays ? row.overlays : undefined,
      })
      setChartUrls(prev => ({ ...prev, [row.symbol]: url }))
      if (meta) {
        setChartMeta(prev => ({ ...prev, [row.symbol]: meta }))
      }
      return url ?? null
    } catch (err) {
      console.error('chart fetch failed', err)
      setChartUrls(prev => ({ ...prev, [row.symbol]: null }))
      setChartMeta(prev => ({ ...prev, [row.symbol]: { fallback: true, overlay_applied: showOverlays, source: 'error', error: String(err) } }))
      return null
    }
  }

  const toggleScanRow = async (row: ScanRow) => {
    const willExpand = !expandedRows[row.symbol]
    setExpandedRows(prev => ({ ...prev, [row.symbol]: willExpand }))
    if (willExpand) {
      await ensureScanChart(row)
    }
  }

  React.useEffect(() => {
    const activeSymbols = Object.entries(expandedRows).filter(([, open]) => open).map(([sym]) => sym)
    if (!activeSymbols.length) return
    activeSymbols.forEach(sym => {
      const row = scanResults.find(r => r.symbol === sym)
      if (row) void ensureScanChart(row)
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showOverlays])

  const rescan = async () => {
    setLoading(true)
    setError(null)
    try {
      const resp = await fetchJSON<{ day: string }>(`${API_BASE}/api/v1/vcp/today`)
      const day = resp?.day || new Date().toISOString().slice(0,10)
      // switch to ad-hoc global day (not tied to a run)
      setSelectedRunId(null)
      setSelectedDay(day)
      // refresh candidates for new day from global reports root
      const cands = await fetchJSON<{ rows: Candidate[] }>(`${API_BASE}/api/v1/vcp/candidates?day=${day}`)
      setCandidates(cands.rows || [])
      // re-fetch sparks
      const map: Record<string, number[]> = {}
      await Promise.all((cands.rows || []).map(async (r) => {
        map[r.symbol] = await fetchSparkline(r.symbol)
      }))
      setSparks(map)
    } catch (e: any) {
      setError(e?.message || 'Rescan failed')
    } finally { setLoading(false) }
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

// Inline chart loader for dropdown preview
  const loadChart = async (symbol: string, row?: Partial<Candidate & { entry?: number, stop?: number, target?: number, pattern?: string }>) => {
    try {
      const { url, meta } = await fetchChart(symbol, {
        pivot: row?.pivot ?? null,
        entry: (row as any)?.entry ?? null,
        stop: (row as any)?.stop ?? null,
        target: (row as any)?.target ?? null,
        pattern: (row as any)?.pattern ?? undefined,
      })
      setChartUrls(prev => ({ ...prev, [symbol]: url }))
      if (meta) setChartMeta(prev => ({ ...prev, [symbol]: meta }))
      if (!url) console.warn('No chart_url from API for', symbol)
    } catch (e) {
      console.error('Failed to load chart:', e)
      setChartUrls(prev => ({ ...prev, [symbol]: null }))
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

      <div className="card p-4 space-y-4">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="text-xs muted">Universe</label>
            <select className="select select-sm" value={scanUniverse} onChange={(e) => setScanUniverse(e.target.value as UniverseOption)}>
              <option value="sp500">S&amp;P 500</option>
              <option value="nasdaq100">NASDAQ-100</option>
            </select>
          </div>
          <div>
            <label className="text-xs muted">Pattern</label>
            <select className="select select-sm" value={scanPattern} onChange={(e) => setScanPattern(e.target.value as PatternOption)}>
              {Object.entries(PATTERN_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs muted">Timeframe</label>
            <select className="select select-sm" value={scanTimeframe} onChange={(e) => setScanTimeframe(e.target.value as TimeframeOption)}>
              {Object.entries(TIMEFRAME_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs muted">Min Price ($)</label>
            <input className="input input-sm w-24" type="number" min={0} value={minPrice} onChange={(e) => setMinPrice(e.target.value)} />
          </div>
          <div>
            <label className="text-xs muted">Min Volume (30d avg)</label>
            <input className="input input-sm w-28" type="number" min={0} value={minVolume} onChange={(e) => setMinVolume(e.target.value)} />
          </div>
          <div>
            <label className="text-xs muted">Max ATR / Price</label>
            <input className="input input-sm w-24" type="number" step="0.01" min={0} value={maxAtrRatio} onChange={(e) => setMaxAtrRatio(e.target.value)} />
          </div>
          <label className="flex items-center gap-2 text-xs">
            <input type="checkbox" className="checkbox checkbox-xs" checked={showOverlays} onChange={(e) => setShowOverlays(e.target.checked)} />
            Overlays
          </label>
          <button className="btn btn-primary" onClick={runScan} disabled={scanLoading}>
            {scanLoading ? <span className="flex items-center gap-2"><span className="loading loading-spinner loading-xs" />Scanning…</span> : 'Scan'}
          </button>
          {scanResults.length > 0 && (
            <span className="text-xs text-neutral-400">{scanResults.length} matches</span>
          )}
        </div>
        {scanError && (
          <div className={`text-sm ${scanError?.startsWith?.('No matches') ? 'text-neutral-400' : (scanResults.length ? 'text-amber-400' : 'text-red-400')}`}>
            {scanError}
          </div>
        )}
        {scanResults.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="table table-sm w-full">
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Pattern</th>
                  <th>Score</th>
                  <th>Key Levels</th>
                  <th>Avg Price</th>
                  <th>Avg Volume</th>
                  <th>ATR</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {scanResults.map((row) => {
                  const isExpanded = !!expandedRows[row.symbol]
                  const levels = row.key_levels || { entry: row.entry, stop: row.stop, targets: row.targets }
                  const evidence: string[] = Array.isArray(row.meta?.evidence) ? row.meta.evidence : []
                  const meta = chartMeta[row.symbol]
                  const chartApiParams = new URLSearchParams({ symbol: row.symbol })
                  if (levels?.entry) chartApiParams.set('entry', String(levels.entry))
                  if (levels?.stop) chartApiParams.set('stop', String(levels.stop))
                  if (levels?.targets && levels.targets.length) chartApiParams.set('target', String(levels.targets[0]))
                  if (row.pattern) chartApiParams.set('pattern', row.pattern)
                  const chartApi = `${API_BASE}/api/v1/chart?${chartApiParams.toString()}`
                  return (
                    <React.Fragment key={row.symbol}>
                      <tr className="cursor-pointer hover:bg-base-200" onClick={() => toggleScanRow(row)}>
                        <td className="font-semibold tracking-wide">
                          <div className="flex items-center gap-2">
                            <span>{row.symbol}</span>
                            {meta?.fallback && <span className="badge badge-xs">fallback</span>}
                          </div>
                        </td>
                        <td>{PATTERN_LABELS[row.pattern as PatternOption] ?? (row.pattern?.toUpperCase() || '—')}</td>
                        <td>{Number.isFinite(row.score) ? scoreFormatter.format(row.score) : '—'}</td>
                        <td>
                          <div className="text-xs">
                            <div>Entry: {formatPrice(levels?.entry)}</div>
                            <div>Stop: {formatPrice(levels?.stop)}</div>
                            <div>Targets: {formatTargets(levels?.targets)}</div>
                          </div>
                        </td>
                        <td>{formatPrice(row.avg_price)}</td>
                        <td>{row.avg_volume ? volumeFormatter.format(row.avg_volume) : '—'}</td>
                        <td>{row.atr14 ? `$${priceFormatter.format(row.atr14)}` : '—'}</td>
                        <td className="text-right space-x-2">
                          <button
                            className="btn btn-ghost btn-xs"
                            onClick={(e) => {
                              e.stopPropagation()
                              toggleScanRow(row)
                            }}
                          >
                            {isExpanded ? 'Hide' : 'Details'}
                          </button>
                          <button
                            className="btn btn-ghost btn-xs"
                            onClick={(e) => {
                              e.stopPropagation()
                              void ensureScanChart(row).then((url) => {
                                const next = url ?? chartUrls[row.symbol]
                                if (next) window.open(next, '_blank', 'noopener')
                              })
                            }}
                          >
                            View
                          </button>
                          <button
                            className="btn btn-ghost btn-xs"
                            onClick={(e) => {
                              e.stopPropagation()
                              void ensureScanChart(row).then((url) => {
                                const next = url ?? chartUrls[row.symbol]
                                void copyText('chart-url', next || '')
                              })
                            }}
                          >
                            Copy Chart
                          </button>
                          <button
                            className="btn btn-ghost btn-xs"
                            onClick={(e) => {
                              e.stopPropagation()
                              void copyText('chart-api', chartApi)
                            }}
                          >
                            Copy API
                          </button>
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr>
                          <td colSpan={8} className="space-y-3">
                            {chartUrls[row.symbol] === undefined && (
                              <div className="py-3 text-sm text-neutral-400">Loading chart…</div>
                            )}
                            {chartUrls[row.symbol] === null && (
                              <div className="py-3 text-sm text-red-400">Chart unavailable for {row.symbol}</div>
                            )}
                            {chartUrls[row.symbol] && (
                              <img src={chartUrls[row.symbol] as string} alt={`${row.symbol} chart`} className="w-full rounded-md border border-base-200" />
                            )}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                              <div className="space-y-1">
                                <h4 className="font-semibold text-sm">Evidence</h4>
                                {evidence.length ? evidence.map(ev => (
                                  <div key={ev} className="badge badge-outline badge-xs mr-1">{ev}</div>
                                )) : <div className="text-neutral-400">No evidence captured</div>}
                              </div>
                              <div className="space-y-1">
                                <h4 className="font-semibold text-sm">Chart Meta</h4>
                                <div>Source: {meta?.source || 'n/a'}</div>
                                <div>Overlay: {meta?.overlay_applied ? 'on' : 'off'}</div>
                                {meta?.duration_ms != null && <div>Render: {meta.duration_ms} ms</div>}
                                {meta?.overlay_counts && (
                                  <div>Shapes: {Object.entries(meta.overlay_counts).filter(([, count]) => count).map(([key, count]) => `${key}:${count}`).join(' ') || '—'}</div>
                                )}
                                {meta?.error && <div className="text-amber-400">{meta.error}</div>}
                              </div>
                              <div className="space-y-1">
                                <h4 className="font-semibold text-sm">Analytics</h4>
                                <div>Avg Price: {formatPrice(row.avg_price)}</div>
                                <div>Avg Volume: {row.avg_volume ? volumeFormatter.format(row.avg_volume) : '—'}</div>
                                <div>ATR14: {row.atr14 ? `$${priceFormatter.format(row.atr14)}` : '—'}</div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : (
          !scanLoading && !scanError && (
            <p className="text-sm text-neutral-400">Scan the universe to surface fresh pattern candidates.</p>
          )
        )}
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
          <select className="select select-sm" value={newRun.universe} onChange={e=>setNewRun(v=>({...v, universe: e.target.value}))}>
            <option value="simple">Simple (Top tech)</option>
            <option value="file:backtest/data/custom_universe.csv">Custom CSV</option>
          </select>
        </div>
        <div>
          <label className="text-xs muted">Provider</label>
          <select className="select select-sm" value={newRun.provider} onChange={e=>setNewRun(v=>({...v, provider: e.target.value}))}>
            <option value="yfinance">Yahoo Finance</option>
          </select>
        </div>
        <button className="btn" onClick={createRun} disabled={creating}>{creating ? 'Enqueuing…' : 'Create Run'}</button>
      </div>

      {/* Live Scanner */}
      <LiveScanner />

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
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_,i)=>(
              <div key={i} className="card p-4 animate-pulse">
                <div className="h-3 w-16 bg-white/10 rounded mb-2" />
                <div className="h-5 w-24 bg-white/20 rounded" />
              </div>
            ))}
          </div>
          <div className="card p-4 animate-pulse">
            <div className="h-4 w-40 bg-white/10 rounded mb-3" />
            {[...Array(6)].map((_,i)=>(
              <div key={i} className="h-5 w-full bg-white/5 rounded mb-2" />
            ))}
          </div>
        </div>
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
                <th className="px-4 py-3">Signal</th>
                <th className="px-4 py-3">Chart</th>
                <th className="px-4 py-3">Notes</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((r) => (
                <tr key={`${r.date}-${r.symbol}`} className="border-t border-white/5 hover:bg-white/5">
                  <td className="px-4 py-3 font-medium"><a className="underline" href={`https://finance.yahoo.com/quote/${encodeURIComponent(r.symbol)}`} target="_blank" rel="noreferrer">{r.symbol}</a></td>
                  <td className="px-4 py-3">{fmtNum(r.price)}</td>
                  <td className="px-4 py-3">{fmtNum(r.pivot)}</td>
                  <td className="px-4 py-3">{Math.round(r.confidence)}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="inline-block rounded px-2 py-0.5 bg-white/10">
                        {typeof signalMap[r.symbol]?.score === 'number' ? `${signalMap[r.symbol]?.score}` : '—'}
                      </span>
                      {signalMap[r.symbol]?.badges?.includes('volume-confirmed MACD') && (
                        <span className="badge badge-success">Vol-confirmed MACD</span>
                      )}
                      {sentMap[r.symbol]?.label && (
                        <span className={`badge ${sentMap[r.symbol]?.label?.toLowerCase() === 'bearish' ? 'badge-error' : sentMap[r.symbol]?.label?.toLowerCase() === 'bullish' ? 'badge-success' : 'badge-ghost'}`}>
                          {sentMap[r.symbol]?.label}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <Sparkline data={sparks[r.symbol] || []} />
                      <select
                        className="select select-sm"
                        defaultValue=""
                        onChange={(e) => {
if (e.target.value === 'show') {
                            loadChart(r as any)
                          } else if (e.target.value === 'hide') {
                            setChartUrls(prev => ({ ...prev, [r.symbol]: null }))
                          }
                          e.currentTarget.value = ''
                        }}
                      >
                        <option value="" disabled>Chart…</option>
                        <option value="show">Show chart</option>
                        <option value="hide">Hide chart</option>
                      </select>
                    </div>
                    {chartUrls[r.symbol] && (
                      <div className="mt-2 space-y-1">
                        <a
                          href={chartUrls[r.symbol] as string}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="link link-primary text-xs"
                        >
                          Open image in new tab
                        </a>
                        <div className="border rounded p-1">
                          <img
                            src={chartUrls[r.symbol] as string}
                            alt={`${r.symbol} chart`}
                            style={{ maxWidth: 480, height: 'auto' }}
                          />
                        </div>
                      </div>
                    )}
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

function LiveScanner() {
  const [universe, setUniverse] = React.useState<UniverseOption>('sp500')
  const [pattern, setPattern] = React.useState<PatternOption>('vcp')
  const [timeframe, setTimeframe] = React.useState<TimeframeOption>('1d')
  const [limit, setLimit] = React.useState(50)
  const [rows, setRows] = React.useState<ScanRow[]>([])
  const [loading, setLoading] = React.useState(false)
  const [err, setErr] = React.useState<string | undefined>()
  const [charts, setCharts] = React.useState<Record<string, string | null>>({})
  const [overlay, setOverlay] = React.useState(true)

  const scan = async () => {
    setLoading(true); setErr(undefined)
    try {
      const qs = new URLSearchParams({ pattern, universe, limit: String(limit), timeframe })
      const resp = await fetchWithRetry<{ results: ScanRow[] }>(`${API_BASE}/api/v1/scan?${qs.toString()}`, 2, 600)
      setRows(Array.isArray(resp?.results) ? resp.results : [])
    } catch (e: any) {
      setErr(e?.message || 'scan failed')
    } finally { setLoading(false) }
  }

  const loadChart = async (row: ScanRow) => {
    const { url } = await fetchChart(row.symbol, {
      entry: row.entry ?? row.key_levels?.entry ?? null,
      stop: row.stop ?? row.key_levels?.stop ?? null,
      target: row.targets?.[0] ?? row.key_levels?.targets?.[0] ?? null,
      pattern,
      overlays: overlay ? row.overlays : undefined,
    })
    setCharts(prev => ({ ...prev, [row.symbol]: url }))
  }

  return (
    <div className="card p-4 space-y-3">
      <div className="flex items-end gap-3 flex-wrap">
        <div>
          <label className="text-xs muted">Universe</label>
          <select className="select select-sm" value={universe} onChange={e=>setUniverse(e.target.value as UniverseOption)}>
            <option value="sp500">S&amp;P 500</option>
            <option value="nasdaq100">NASDAQ-100</option>
          </select>
        </div>
        <div>
          <label className="text-xs muted">Pattern</label>
          <select className="select select-sm" value={pattern} onChange={e=>setPattern(e.target.value as PatternOption)}>
            {Object.entries(PATTERN_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs muted">Timeframe</label>
          <select className="select select-sm" value={timeframe} onChange={e=>setTimeframe(e.target.value as TimeframeOption)}>
            {Object.entries(TIMEFRAME_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs muted">Limit</label>
          <input className="input input-sm w-24" type="number" value={limit} min={10} max={500} onChange={e=>setLimit(parseInt(e.target.value || '50', 10) || 50)} />
        </div>
        <label className="flex items-center gap-2 text-xs">
          <input type="checkbox" className="checkbox checkbox-xs" checked={overlay} onChange={(e)=>setOverlay(e.target.checked)} />
          Overlays
        </label>
        <button className="btn btn-primary" onClick={scan} disabled={loading}>
          {loading ? <span className="flex items-center gap-2"><span className="loading loading-spinner loading-xs" />Scanning…</span> : 'Scan'}
        </button>
        {!!err && <div className="text-xs text-red-300">{err}</div>}
      </div>
      {!!rows?.length && (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left muted">
                <th className="px-2 py-2">Symbol</th>
                <th className="px-2 py-2">Score</th>
                <th className="px-2 py-2">Entry / Stop</th>
                <th className="px-2 py-2">Targets</th>
                <th className="px-2 py-2">Chart</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.symbol} className="border-t border-white/5">
                  <td className="px-2 py-2 font-medium">{r.symbol}</td>
                  <td className="px-2 py-2">{Number.isFinite(r.score) ? r.score.toFixed(1) : '—'}</td>
                  <td className="px-2 py-2">
                    <div>Entry: {r.entry ? r.entry.toFixed(2) : '—'}</div>
                    <div>Stop: {r.stop ? r.stop.toFixed(2) : '—'}</div>
                  </td>
                  <td className="px-2 py-2">{r.targets?.length ? r.targets.map(t => t.toFixed(2)).join(', ') : '—'}</td>
                  <td className="px-2 py-2 space-x-2">
                    <button className="btn btn-ghost btn-xs" onClick={()=>loadChart(r)}>Preview</button>
                    {charts[r.symbol] && <a className="btn btn-ghost btn-xs" href={charts[r.symbol] as string} target="_blank" rel="noreferrer">Open</a>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
