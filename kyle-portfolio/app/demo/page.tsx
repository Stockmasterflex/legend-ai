"use client"

import React from 'react'

type ScanLevels = { entry: number; stop: number; targets: number[] }

type ChartMeta = {
  fallback: boolean
  overlay_applied: boolean
  source: string
  dry_run?: boolean
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
  pattern?: string
  overlays?: any
  meta?: any
  key_levels?: ScanLevels
  avg_price?: number
  avg_volume?: number
  atr14?: number
  sector?: string
  chart_url?: string | null
  chart_meta?: ChartMeta | null
}

type PatternOption = 'vcp' | 'cup_handle' | 'hns' | 'flag' | 'wedge' | 'double'
type UniverseOption = 'sp500' | 'nasdaq100'
type TimeframeOption = '1d' | '1wk' | '60m'

type Metric = {
  title: string
  value: string
  tooltip: string
  trend?: 'up' | 'down' | 'neutral'
}

const API_BASE = (process.env.NEXT_PUBLIC_VCP_API_BASE as string) || (process.env.NEXT_PUBLIC_API_BASE as string) || 'https://legend-api.onrender.com'
const SHOTS_BASE = (process.env.NEXT_PUBLIC_SHOTS_BASE as string) || 'https://legend-shots.onrender.com'

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
  '60m': '60‑Minute',
}

const SECTOR_OPTIONS = [
  'All',
  'Technology',
  'Communication Services',
  'Consumer Discretionary',
  'Consumer Staples',
  'Energy',
  'Financial Services',
  'Healthcare',
  'Industrials',
  'Materials',
  'Real Estate',
  'Utilities',
]

async function fetchWithRetry<T>(url: string, tries = 3, backoffMs = 500): Promise<T> {
  let lastErr: any
  for (let i = 0; i < tries; i++) {
    try {
      const res = await fetch(url, { cache: 'no-store' })
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
      return res.json()
    } catch (err) {
      lastErr = err
      if (i < tries - 1) {
        await new Promise((resolve) => setTimeout(resolve, backoffMs * (i + 1)))
      }
    }
  }
  throw lastErr
}

async function fetchChart(
  symbol: string,
  opts?: { entry?: number | null; stop?: number | null; target?: number | null; pattern?: string; overlays?: any }
): Promise<{ url: string | null; meta?: ChartMeta }> {
  try {
    const params = new URLSearchParams({ symbol })
    if (opts?.entry != null) params.set('entry', String(opts.entry))
    if (opts?.stop != null) params.set('stop', String(opts.stop))
    if (opts?.target != null) params.set('target', String(opts.target))
    if (opts?.pattern) params.set('pattern', opts.pattern)

    const hasOverlays = opts?.overlays && typeof opts.overlays === 'object' && Object.keys(opts.overlays).length > 0
    const endpoint = `${API_BASE}/api/v1/chart?${params.toString()}`
    const init: RequestInit | undefined = hasOverlays
      ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ overlays: opts?.overlays }) }
      : undefined
    const res = await fetch(endpoint, init)
    if (!res.ok) return { url: null }
    const payload = await res.json()
    return {
      url: typeof payload?.chart_url === 'string' ? payload.chart_url : null,
      meta: payload?.meta as ChartMeta | undefined,
    }
  } catch (err) {
    console.error('chart fetch failed', err)
    return { url: null }
  }
}

const MetricCard: React.FC<Metric> = ({ title, value, tooltip, trend = 'neutral' }) => (
  <div className="bg-slate-800/70 border border-slate-700 rounded-lg p-4 group relative">
    <div className="flex items-center justify-between text-sm text-slate-400">
      <span>{title}</span>
      <span className="text-xs text-slate-500">ⓘ</span>
    </div>
    <div
      className={`mt-2 text-2xl font-semibold ${
        trend === 'up' ? 'text-emerald-400' : trend === 'down' ? 'text-rose-400' : 'text-white'
      }`}
    >
      {value}
    </div>
    <div className="absolute hidden group-hover:block bottom-full left-0 mb-2 w-60 rounded bg-black/90 px-3 py-2 text-xs text-slate-200 shadow-lg">
      {tooltip}
    </div>
  </div>
)

const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`

const formatPrice = (value?: number | null) => {
  if (value == null || Number.isNaN(value)) return '—'
  return `$${value.toFixed(value >= 100 ? 2 : 3)}`
}

const formatTargets = (targets?: number[]) => {
  if (!Array.isArray(targets) || !targets.length) return '—'
  return targets.map((t) => formatPrice(t)).join(', ')
}

export default function DemoPage() {
  const [healthy, setHealthy] = React.useState<boolean | null>(null)
  const [error, setError] = React.useState<string | null>(null)

  const [scanPattern, setScanPattern] = React.useState<PatternOption>('vcp')
  const [scanUniverse, setScanUniverse] = React.useState<UniverseOption>('sp500')
  const [scanTimeframe, setScanTimeframe] = React.useState<TimeframeOption>('1d')
  const [selectedSector, setSelectedSector] = React.useState<string>('All')

  const [startDate, setStartDate] = React.useState<string>(() => new Date(Date.now() - 60 * 864e5).toISOString().slice(0, 10))
  const [endDate, setEndDate] = React.useState<string>(() => new Date().toISOString().slice(0, 10))

  const [minPrice, setMinPrice] = React.useState<string>('20')
  const [minVolume, setMinVolume] = React.useState<string>('750000')
  const [maxAtrRatio, setMaxAtrRatio] = React.useState<string>('0.08')
  const [showOverlays, setShowOverlays] = React.useState(true)

  const [scanResults, setScanResults] = React.useState<ScanRow[]>([])
  const [scanLoading, setScanLoading] = React.useState(false)
  const [scanError, setScanError] = React.useState<string | null>(null)
  const [usingSample, setUsingSample] = React.useState(false)

  const [expandedRows, setExpandedRows] = React.useState<Record<string, boolean>>({})
  const [chartUrls, setChartUrls] = React.useState<Record<string, string | null>>({})
  const [chartMeta, setChartMeta] = React.useState<Record<string, ChartMeta | undefined>>({})
  const [loadingCharts, setLoadingCharts] = React.useState<Set<string>>(new Set())

  const updateChartLoading = React.useCallback((symbol: string, isLoading: boolean) => {
    setLoadingCharts((prev) => {
      const next = new Set(prev)
      if (isLoading) {
        next.add(symbol)
      } else {
        next.delete(symbol)
      }
      return next
    })
  }, [])

  const buildScanQuery = React.useCallback(
    (opts?: { sample?: boolean }) => {
      const qs = new URLSearchParams({
        pattern: scanPattern,
        universe: scanUniverse,
        limit: '150',
        timeframe: scanTimeframe,
        min_price: String(Number(minPrice) || 0),
        min_volume: String(Number(minVolume) || 0),
      })
      if (maxAtrRatio.trim()) {
        qs.set('max_atr_ratio', maxAtrRatio.trim())
      }
      if (opts?.sample) {
        qs.set('sample', 'true')
      }
      return qs
    },
    [scanPattern, scanUniverse, scanTimeframe, minPrice, minVolume, maxAtrRatio]
  )

  const runScan = React.useCallback(
    async (opts?: { sample?: boolean }) => {
      setScanLoading(true)
      setScanError(null)
      setUsingSample(Boolean(opts?.sample))
      try {
        const qs = buildScanQuery(opts)
        const payload = await fetchWithRetry<{ results: ScanRow[]; is_sample?: boolean }>(
          `${API_BASE}/api/v1/scan?${qs.toString()}`,
          2,
          600
        )
        const rows = Array.isArray(payload?.results) ? payload.results : []
        const sanitized = rows.map((row) => {
          const levels = row.key_levels || {
            entry: row.entry,
            stop: row.stop,
            targets: row.targets,
          }
          return {
            ...row,
            pattern: row.pattern || scanPattern,
            score: Number(row.score ?? 0),
            entry: Number(levels?.entry ?? row.entry ?? 0),
            stop: Number(levels?.stop ?? row.stop ?? 0),
            targets: Array.isArray(levels?.targets) ? levels.targets.map(Number) : [],
            key_levels: {
              entry: Number(levels?.entry ?? 0),
              stop: Number(levels?.stop ?? 0),
              targets: Array.isArray(levels?.targets) ? levels.targets.map(Number) : [],
            },
            sector:
              typeof row.sector === 'string'
                ? row.sector
                : typeof row.meta?.sector === 'string'
                  ? row.meta.sector
                  : undefined,
            chart_meta: row.chart_meta ?? null,
          }
        })

        setUsingSample(Boolean(opts?.sample || payload?.is_sample))
        if (!sanitized.length && !opts?.sample) {
          setScanError('No candidates matched these filters. Try adjusting inputs or view sample data.')
        }
        setScanResults(sanitized)
        setExpandedRows({})
        setChartUrls({})
        setChartMeta({})
      } catch (err: any) {
        setUsingSample(Boolean(opts?.sample))
        setScanError(err?.message || 'Scan failed')
        setScanResults([])
      } finally {
        setScanLoading(false)
      }
    },
    [buildScanQuery, scanPattern]
  )

  React.useEffect(() => {
    ;(async () => {
      try {
        const hz = await fetchWithRetry<{ ok: boolean }>(`${API_BASE}/healthz`, 2, 400)
        setHealthy(!!hz?.ok)
      } catch {
        setHealthy(false)
      }
      // probes shots health for DRY_RUN awareness (best-effort)
      try {
        const sh = await fetchWithRetry<{ ok: boolean; dryRun?: boolean }>(`${SHOTS_BASE}/healthz`, 1, 300)
        if (sh?.dryRun) {
          console.info('shots running in dry-run mode')
        }
      } catch {}
      runScan()
    })()
  }, [runScan])

  const filteredResults = React.useMemo(() => {
    if (selectedSector === 'All') return scanResults
    return scanResults.filter((row) => {
      const sector = (row.sector || row.meta?.sector || '').toString().toLowerCase()
      return sector === selectedSector.toLowerCase()
    })
  }, [scanResults, selectedSector])
  const hasResults = filteredResults.length > 0

  const metrics = React.useMemo(() => {
    if (!filteredResults.length) {
      const defaults: Metric[] = [
        { title: 'Win Rate', value: '0.0%', tooltip: 'Percentage of setups above the quality threshold', trend: 'neutral' },
        { title: 'Avg Return', value: '0.0%', tooltip: 'Average upside from entry to first target', trend: 'neutral' },
        { title: 'Hit Rate', value: '0.0%', tooltip: 'Percentage of symbols with liquidity > 1M shares', trend: 'neutral' },
        { title: 'Median Hold', value: '—', tooltip: 'Estimated holding period based on ATR vs. risk', trend: 'neutral' },
      ]
      return defaults
    }
    const winRate = filteredResults.filter((row) => row.score >= 80).length / filteredResults.length
    const returns = filteredResults
      .map((row) => {
        if (!row.entry || !row.targets?.length) return 0
        const firstTarget = row.targets[0]
        return (firstTarget - row.entry) / Math.max(row.entry, 1e-6)
      })
      .filter((v) => Number.isFinite(v) && v > 0)
    const avgReturn = returns.length ? returns.reduce((acc, val) => acc + val, 0) / returns.length : 0
    const hitRate = filteredResults.filter((row) => (row.avg_volume ?? 0) >= 1_000_000).length / filteredResults.length
    const holdEstimates = filteredResults
      .map((row) => {
        const risk = Math.max(row.entry - row.stop, 0.01)
        const atr = row.atr14 ?? Number(row.meta?.atr14 ?? 0)
        if (!atr || !risk) return 0
        return Math.min(30, Math.max(3, Math.round((risk / atr) * 10)))
      })
      .filter((val) => val > 0)
    const sortedHold = [...holdEstimates].sort((a, b) => a - b)
    const medianHold = sortedHold.length
      ? sortedHold[Math.floor(sortedHold.length / 2)]
      : 0
    const computed: Metric[] = [
      {
        title: 'Win Rate',
        value: formatPercent(winRate),
        tooltip: 'Percent of candidates scoring 80 or higher',
        trend: winRate >= 0.6 ? 'up' : winRate <= 0.4 ? 'down' : 'neutral',
      },
      {
        title: 'Avg Return',
        value: formatPercent(avgReturn),
        tooltip: 'Average upside from entry to first target',
        trend: avgReturn >= 0.1 ? 'up' : avgReturn <= 0.03 ? 'down' : 'neutral',
      },
      {
        title: 'Hit Rate',
        value: formatPercent(hitRate),
        tooltip: 'Percent trading above ~1M shares (30-day avg volume)',
        trend: hitRate >= 0.5 ? 'up' : hitRate <= 0.25 ? 'down' : 'neutral',
      },
      {
        title: 'Median Hold',
        value: medianHold ? `${medianHold} days` : '—',
        tooltip: 'Estimated holding period (risk ÷ ATR heuristic)',
        trend: 'neutral',
      },
    ]
    return computed
  }, [filteredResults])

  const ensureChart = React.useCallback(
    async (row: ScanRow) => {
      const currentUrl = chartUrls[row.symbol]
      const currentMeta = chartMeta[row.symbol]
      if (currentUrl && currentMeta && (!!currentMeta.overlay_applied) === showOverlays) {
        return currentUrl
      }
      updateChartLoading(row.symbol, true)
      try {
        const primaryTarget = row.targets?.[0] ?? row.key_levels?.targets?.[0] ?? null
        const { url, meta } = await fetchChart(row.symbol, {
          entry: row.entry ?? row.key_levels?.entry ?? null,
          stop: row.stop ?? row.key_levels?.stop ?? null,
          target: primaryTarget,
          pattern: row.pattern,
          overlays: showOverlays ? row.overlays : undefined,
        })
        if (meta) {
          setChartMeta((prev) => ({ ...prev, [row.symbol]: meta }))
        }
        setChartUrls((prev) => ({ ...prev, [row.symbol]: url }))
        return url
      } finally {
        updateChartLoading(row.symbol, false)
      }
    },
    [chartMeta, chartUrls, showOverlays, updateChartLoading]
  )

  const toggleRow = React.useCallback(
    async (row: ScanRow) => {
      setExpandedRows((prev) => ({ ...prev, [row.symbol]: !prev[row.symbol] }))
      if (!expandedRows[row.symbol]) {
        await ensureChart(row)
      }
    },
    [ensureChart, expandedRows]
  )

  const formattedStart = startDate
  const formattedEnd = endDate

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-white flex items-center gap-2">
          Legend Scanner
          <span
            title={healthy === null ? 'Checking…' : healthy ? 'API healthy' : 'API unreachable'}
            className={`inline-flex h-2.5 w-2.5 rounded-full ${
              healthy === null ? 'bg-white/40 animate-pulse' : healthy ? 'bg-emerald-400' : 'bg-rose-500'
            }`}
          />
          {usingSample && (
            <span className="inline-flex items-center gap-1 rounded-full border border-amber-400/50 bg-amber-500/20 px-2 py-0.5 text-xs font-medium text-amber-200">
              Sample data
            </span>
          )}
        </h1>
        {error && <span className="text-sm text-rose-300">{error}</span>}
      </div>

      <div className="flex flex-wrap items-end justify-between gap-4 rounded-lg border border-slate-700 bg-slate-800/70 p-4">
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex flex-col text-sm text-slate-400">
            <label className="mb-1">Start</label>
            <input
              type="date"
              value={formattedStart}
              onChange={(e) => setStartDate(e.target.value)}
              className="rounded bg-slate-900 px-3 py-2 text-white"
            />
          </div>
          <div className="flex flex-col text-sm text-slate-400">
            <label className="mb-1">End</label>
            <input
              type="date"
              value={formattedEnd}
              onChange={(e) => setEndDate(e.target.value)}
              className="rounded bg-slate-900 px-3 py-2 text-white"
            />
          </div>
          <div className="flex flex-col text-sm text-slate-400 min-w-[160px]">
            <label className="mb-1">Sector</label>
            <select
              className="rounded bg-slate-900 px-3 py-2 text-white"
              value={selectedSector}
              onChange={(e) => setSelectedSector(e.target.value)}
            >
              {SECTOR_OPTIONS.map((sector) => (
                <option key={sector} value={sector}>
                  {sector}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col text-sm text-slate-400 min-w-[150px]">
            <label className="mb-1">Pattern</label>
            <select
              className="rounded bg-slate-900 px-3 py-2 text-white"
              value={scanPattern}
              onChange={(e) => setScanPattern(e.target.value as PatternOption)}
            >
              {Object.entries(PATTERN_LABELS).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col text-sm text-slate-400 min-w-[140px]">
            <label className="mb-1">Universe</label>
            <select
              className="rounded bg-slate-900 px-3 py-2 text-white"
              value={scanUniverse}
              onChange={(e) => setScanUniverse(e.target.value as UniverseOption)}
            >
              <option value="sp500">S&amp;P 500</option>
              <option value="nasdaq100">NASDAQ-100</option>
            </select>
          </div>
          <div className="flex flex-col text-sm text-slate-400 min-w-[140px]">
            <label className="mb-1">Timeframe</label>
            <select
              className="rounded bg-slate-900 px-3 py-2 text-white"
              value={scanTimeframe}
              onChange={(e) => setScanTimeframe(e.target.value as TimeframeOption)}
            >
              {Object.entries(TIMEFRAME_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col text-sm text-slate-400 w-24">
            <label className="mb-1">Min Price</label>
            <input
              type="number"
              className="rounded bg-slate-900 px-3 py-2 text-white"
              value={minPrice}
              onChange={(e) => setMinPrice(e.target.value)}
            />
          </div>
          <div className="flex flex-col text-sm text-slate-400 w-28">
            <label className="mb-1">Min Volume</label>
            <input
              type="number"
              className="rounded bg-slate-900 px-3 py-2 text-white"
              value={minVolume}
              onChange={(e) => setMinVolume(e.target.value)}
            />
          </div>
          <div className="flex flex-col text-sm text-slate-400 w-28">
            <label className="mb-1">Max ATR / Price</label>
            <input
              type="number"
              step="0.01"
              className="rounded bg-slate-900 px-3 py-2 text-white"
              value={maxAtrRatio}
              onChange={(e) => setMaxAtrRatio(e.target.value)}
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-400">
            <input
              type="checkbox"
              className="checkbox checkbox-xs"
              checked={showOverlays}
              onChange={(e) => setShowOverlays(e.target.checked)}
            />
            Overlays
          </label>
        </div>
        <div className="flex items-center gap-3">
          <button
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500"
            onClick={() => {
              setScanResults([])
              runScan()
            }}
            disabled={scanLoading}
          >
            {scanLoading ? 'Scanning…' : 'Run Scan'}
          </button>
          <button
            className="rounded border border-slate-500/60 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700/60 disabled:opacity-60"
            onClick={() => runScan({ sample: true })}
            disabled={scanLoading}
          >
            {usingSample && !scanLoading ? 'Refresh Sample' : 'View Sample'}
          </button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {metrics.map((metric) => (
          <MetricCard key={metric.title} {...metric} />
        ))}
      </div>

      {scanError && (
        <div className="rounded border border-rose-500/60 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          {scanError}
          <div className="mt-2 flex flex-wrap gap-2">
            <button
              className="rounded bg-rose-500/20 px-3 py-1 text-xs font-medium text-rose-100 hover:bg-rose-500/30"
              onClick={() => runScan()}
              disabled={scanLoading}
            >
              Retry
            </button>
            <button
              className="rounded border border-amber-400/40 px-3 py-1 text-xs font-medium text-amber-200 hover:bg-amber-500/20 disabled:opacity-60"
              onClick={() => runScan({ sample: true })}
              disabled={scanLoading}
            >
              Load Sample
            </button>
          </div>
        </div>
      )}

      <div className="overflow-x-auto rounded-lg border border-slate-700 bg-slate-800/60">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-800/80 text-xs uppercase tracking-wide text-slate-400">
            <tr>
              <th className="px-4 py-3 text-left">Symbol</th>
              <th className="px-4 py-3 text-left">Pattern</th>
              <th className="px-4 py-3 text-left">Score</th>
              <th className="px-4 py-3 text-left">Trading Plan</th>
              <th className="px-4 py-3 text-left">ATR</th>
              <th className="px-4 py-3 text-left">Volume</th>
              <th className="px-4 py-3 text-left">Sector</th>
              <th className="px-4 py-3 text-right">Chart</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/60 text-slate-100">
            {hasResults ? filteredResults.map((row) => {
              const isExpanded = !!expandedRows[row.symbol]
              const plan = row.key_levels || { entry: row.entry, stop: row.stop, targets: row.targets }
              const volumeText = row.avg_volume ?
                Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 }).format(row.avg_volume) :
                '—'
              const chartUrl = chartUrls[row.symbol]
              const meta = chartMeta[row.symbol]
              const isLoadingChart = loadingCharts.has(row.symbol)
              return (
                <React.Fragment key={row.symbol}>
                  <tr
                    className="cursor-pointer hover:bg-slate-700/40"
                    onClick={() => toggleRow(row)}
                  >
                    <td className="px-4 py-3 text-left font-semibold tracking-wide">
                      <span>{row.symbol}</span>
                    </td>
                    <td className="px-4 py-3 text-left text-slate-300">{PATTERN_LABELS[row.pattern as PatternOption] ?? row.pattern?.toUpperCase() ?? '—'}</td>
                    <td className="px-4 py-3 text-left font-semibold text-emerald-300">{row.score.toFixed(1)}</td>
                    <td className="px-4 py-3 text-left text-xs">
                      <div className="flex flex-col gap-1">
                        <span className="text-emerald-300">Entry: {formatPrice(plan?.entry)}</span>
                        <span className="text-rose-300">Stop: {formatPrice(plan?.stop)}</span>
                        <span className="text-sky-300">Targets: {formatTargets(plan?.targets)}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-left text-slate-300">{row.atr14 ? formatPrice(row.atr14) : '—'}</td>
                    <td className="px-4 py-3 text-left text-slate-300">{volumeText}</td>
                    <td className="px-4 py-3 text-left text-slate-300">{row.sector || row.meta?.sector || '—'}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-2">
                        {isLoadingChart ? (
                          <div className="inline-flex items-center rounded bg-slate-700 px-3 py-1 text-xs text-slate-300">
                            Loading…
                          </div>
                        ) : chartUrl ? (
                          <button
                            className="rounded bg-slate-700/80 px-3 py-1 text-xs text-slate-200 hover:bg-slate-600"
                            onClick={async (e) => {
                              e.stopPropagation()
                              await ensureChart(row)
                              window.open(chartUrls[row.symbol] ?? '', '_blank', 'noopener')
                            }}
                          >
                            Open
                          </button>
                        ) : (
                          <button
                            className="rounded bg-blue-600 px-3 py-1 text-xs text-white hover:bg-blue-500"
                            onClick={async (e) => {
                              e.stopPropagation()
                              await ensureChart(row)
                            }}
                          >
                            Load
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr className="bg-slate-900/60">
                      <td colSpan={8} className="px-6 py-4 text-sm text-slate-200">
                        <div className="grid gap-4 md:grid-cols-5">
                          <div className="md:col-span-3 rounded border border-slate-700">
                            {chartUrl ? (
                              <img
                                src={chartUrl}
                                alt={`${row.symbol} chart`}
                                className="w-full rounded"
                              />
                            ) : (
                              <div className="flex h-48 items-center justify-center text-slate-400">No chart loaded yet.</div>
                            )}
                            {meta && (
                              <div className="flex flex-wrap items-center gap-2 border-t border-slate-700/80 px-3 py-2 text-xs text-slate-300">
                            {meta.dry_run && (
                                  <span className="rounded-full border border-amber-400/40 bg-amber-500/15 px-2 py-0.5 text-amber-200">
                                    Placeholder chart
                                  </span>
                                )}
                                {!meta.dry_run && meta.fallback && (
                                  <span className="rounded-full border border-rose-400/30 bg-rose-500/20 px-2 py-0.5 text-rose-200">
                                    Fallback image
                                  </span>
                                )}
                            {(meta.dry_run || meta.fallback) && (
                              <button
                                className="ml-auto rounded bg-slate-700/80 px-2 py-0.5 text-xs text-slate-200 hover:bg-slate-600"
                                onClick={async (e) => {
                                  e.stopPropagation()
                                  await ensureChart(row)
                                }}
                              >
                                Retry screenshot
                              </button>
                            )}
                                {meta.duration_ms != null && (
                                  <span>Render: {(meta.duration_ms / 1000).toFixed(2)}s</span>
                                )}
                                {meta.overlay_counts && (
                                  <span>
                                    Overlays:{' '}
                                    {Object.entries(meta.overlay_counts)
                                      .filter(([, count]) => (count ?? 0) > 0)
                                      .map(([key, count]) => `${key}:${count}`)
                                      .join(' ') || '—'}
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                          <div className="md:col-span-2 space-y-3">
                            <div>
                              <h4 className="text-xs uppercase tracking-wide text-slate-400">Evidence</h4>
                              <div className="mt-2 flex flex-wrap gap-2">
                                {Array.isArray(row.meta?.evidence) && row.meta.evidence.length
                                  ? row.meta.evidence.map((note: string) => (
                                      <span key={note} className="rounded-full bg-slate-700/80 px-3 py-1 text-xs text-slate-200">
                                        {note}
                                      </span>
                                    ))
                                  : <span className="text-xs text-slate-500">No evidence captured</span>}
                              </div>
                            </div>
                            <div>
                              <h4 className="text-xs uppercase tracking-wide text-slate-400">Chart Meta</h4>
                              <dl className="mt-2 space-y-1 text-xs text-slate-300">
                                <div className="flex justify-between"><dt>Source</dt><dd>{meta?.source || '—'}</dd></div>
                                <div className="flex justify-between"><dt>Overlays</dt><dd>{meta?.overlay_applied ? 'On' : 'Off'}</dd></div>
                                <div className="flex justify-between"><dt>Render</dt><dd>{meta?.duration_ms ? `${(meta.duration_ms / 1000).toFixed(1)} s` : '—'}</dd></div>
                                {meta?.error && <div className="text-amber-400">{meta.error}</div>}
                              </dl>
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              )
            }) : (
              <tr>
                <td colSpan={8} className="px-6 py-12 text-center text-sm text-slate-300">
                  {scanLoading
                    ? 'Running scan…'
                    : usingSample
                      ? 'Sample dataset currently contains no candidates.'
                      : 'No candidates found for these filters.'}
                  {!scanLoading && !usingSample && (
                    <div className="mt-3 flex justify-center gap-2 text-xs">
                      <button
                        className="rounded bg-blue-600 px-3 py-1 text-white hover:bg-blue-500"
                        onClick={() => runScan()}
                      >
                        Retry Scan
                      </button>
                      <button
                        className="rounded border border-amber-400/40 px-3 py-1 text-amber-200 hover:bg-amber-500/20"
                        onClick={() => runScan({ sample: true })}
                      >
                        Load Sample Data
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
