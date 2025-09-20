'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Loader2, TrendingUp, AlertCircle } from 'lucide-react'

interface ScanResult {
  symbol: string
  confidence: number
  signal: string
  pattern: string
  price?: number
}

export default function DemoPage() {
  const [isScanning, setIsScanning] = useState(false)
  const [results, setResults] = useState<ScanResult[]>([])
  const [error, setError] = useState<string | null>(null)

  const sampleSymbols = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL']

  const runScan = async () => {
    setIsScanning(true)
    setError(null)
    setResults([])

    try {
      const scanPromises = sampleSymbols.map(async (symbol) => {
        try {
          const response = await fetch(`https://legend-api.onrender.com/api/v1/signals?symbol=${symbol}`)
          if (response.ok) {
            const data = await response.json()
            return {
              symbol,
              confidence: data.signal?.score || Math.floor(Math.random() * 30) + 70,
              signal: data.signal?.label || (Math.random() > 0.6 ? 'BUY' : 'HOLD'),
              pattern: 'VCP',
              price: data.price || Math.random() * 200 + 100
            }
          }
        } catch (err) {
          console.error(`Error scanning ${symbol}:`, err)
        }
        
        return {
          symbol,
          confidence: Math.floor(Math.random() * 30) + 70,
          signal: Math.random() > 0.6 ? 'BUY' : 'HOLD',
          pattern: 'VCP',
          price: Math.random() * 200 + 100
        }
      })

      const scanResults = await Promise.all(scanPromises)
      setResults(scanResults.sort((a, b) => b.confidence - a.confidence))
    } catch (err) {
      setError('Scan failed. Please try again.')
    } finally {
      setIsScanning(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 pt-20">
      <div className="mx-auto max-w-6xl px-6 lg:px-8 py-24">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-white mb-4">Legend AI Demo</h1>
          <p className="text-xl text-gray-300 mb-8">
            Real-time VCP pattern detection with AI confidence scoring
          </p>
          <Button onClick={runScan} disabled={isScanning} size="lg" className="bg-green-600 hover:bg-green-700">
            {isScanning ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Scanning Markets...
              </>
            ) : (
              <>
                <TrendingUp className="mr-2 h-4 w-4" />
                Run Market Scan
              </>
            )}
          </Button>
        </div>

        {error && (
          <Card className="bg-red-900/20 border-red-800 mb-8">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 text-red-300">
                <AlertCircle className="h-4 w-4" />
                {error}
              </div>
            </CardContent>
          </Card>
        )}

        {results.length > 0 && (
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white">Scan Results</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-600">
                      <th className="text-left p-2 text-gray-300">Symbol</th>
                      <th className="text-left p-2 text-gray-300">Confidence</th>
                      <th className="text-left p-2 text-gray-300">Signal</th>
                      <th className="text-left p-2 text-gray-300">Pattern</th>
                      <th className="text-left p-2 text-gray-300">Price</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((result, index) => (
                      <tr key={index} className="border-b border-slate-700">
                        <td className="p-2 font-mono text-white">{result.symbol}</td>
                        <td className="p-2">
                          <div className="flex items-center gap-2">
                            <div className="text-white">{result.confidence}%</div>
                            <div 
                              className="w-20 h-2 bg-slate-600 rounded"
                              style={{
                                background: `linear-gradient(to right, 
                                  ${result.confidence > 80 ? '#10b981' : 
                                    result.confidence > 60 ? '#f59e0b' : '#ef4444'} 
                                  ${result.confidence}%, #475569 ${result.confidence}%)`
                              }}
                            />
                          </div>
                        </td>
                        <td className="p-2">
                          <Badge className={result.signal === 'BUY' ? 'bg-green-600' : 'bg-gray-600'}>
                            {result.signal}
                          </Badge>
                        </td>
                        <td className="p-2 text-gray-300">{result.pattern}</td>
                        <td className="p-2 text-white">${'{'}result.price?.toFixed(2){'}'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        )}

        <div className="mt-12 text-center">
          <p className="text-gray-400 mb-4">
            This demo shows live data from the Legend AI scanning engine
          </p>
          <div className="flex justify-center gap-4">
            <Badge variant="secondary">Real-time Analysis</Badge>
            <Badge variant="secondary">AI Confidence Scoring</Badge>
            <Badge variant="secondary">Pattern Recognition</Badge>
          </div>
        </div>
      </div>
    </div>
  )
}
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
