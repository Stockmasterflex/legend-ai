"use client"
import React from 'react'

const API_BASE = process.env.NEXT_PUBLIC_VCP_API_BASE || 'http://127.0.0.1:8000'

async function fetchJSON<T>(url: string): Promise<T> { const r = await fetch(url, { cache: 'no-store' }); if (!r.ok) throw new Error(`${r.status}`); return r.json() }

function PatternDistributionChart({ data }: { data: any[] }) {
  const total = data.reduce((sum, item) => sum + item.count, 0)
  let currentAngle = 0
  return (
    <div className="relative w-48 h-48 mx-auto">
      <svg className="w-48 h-48 transform -rotate-90">
        {data.map((item, index) => {
          const percentage = item.count / total
          const strokeDasharray = `${percentage * 314.16} 314.16`
          const strokeDashoffset = -currentAngle * 314.16 / 360
          currentAngle += percentage * 360
          return (
            <circle key={index} cx="96" cy="96" r="50" fill="none" stroke={item.color} strokeWidth="20" strokeDasharray={strokeDasharray} strokeDashoffset={strokeDashoffset} className="transition-all duration-300" />
          )
        })}
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="text-center">
          <div className="text-2xl font-bold">{total}</div>
          <div className="text-sm muted">Total Patterns</div>
        </div>
      </div>
    </div>
  )
}

function PatternSuccessChart({ data }: { data: any[] }) {
  const maxCount = Math.max(...data.map(d => d.count))
  return (
    <div className="space-y-3">
      {data.map((pattern, index) => (
        <div key={index} className="space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium">{pattern.name}</span>
            <span className="text-sm muted">{pattern.count}</span>
          </div>
          <div className="relative">
            <div className="w-full bg-white/10 rounded-full h-3">
              <div className="h-3 rounded-full flex" style={{ width: `${(pattern.count / maxCount) * 100}%` }}>
                <div className="h-full rounded-l-full" style={{ backgroundColor: pattern.color, width: `${pattern.successRate}%` }} />
                <div className="h-full bg-white/5 rounded-r-full" style={{ width: `${100 - pattern.successRate}%` }} />
              </div>
            </div>
            <div className="text-xs muted mt-1 flex justify-between">
              <span>{pattern.successRate}% success</span>
              <span>{pattern.avgConfidence.toFixed(1)} avg confidence</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function KPICard({ title, value, subtitle, trend, color = 'green' }: { title: string, value: string, subtitle?: string, trend?: number, color?: 'green'|'red'|'blue' }) {
  return (
    <div className="card p-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs muted mb-1">{title}</div>
          <div className={`text-2xl font-bold ${color === 'green' ? 'text-green-400' : color === 'red' ? 'text-red-400' : 'text-blue-400'}`}>{value}</div>
          {subtitle && <div className="text-xs muted">{subtitle}</div>}
        </div>
        {typeof trend === 'number' && <div className={`text-sm ${trend > 0 ? 'text-green-400' : 'text-red-400'}`}>{trend > 0 ? '+' : ''}{trend}%</div>}
      </div>
    </div>
  )
}

function CandidateCard({ candidate }: { candidate: any }) {
  return (
    <div className="card p-4 hover:bg-white/5 transition-colors">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="text-lg font-bold">{candidate.symbol}</div>
            <div className="px-2 py-1 bg-white/10 rounded text-xs">{candidate.sector}</div>
          </div>
          <div className="text-xs muted">{candidate.pattern}</div>
        </div>
        <div className="text-right">
          <div className="text-xs muted">Confidence</div>
          <div className="text-lg font-semibold text-blue-400">{candidate.confidence}</div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3 mb-3 text-sm">
        <div>
          <div className="text-xs muted">Price</div>
          <div className="font-medium">${candidate.price}</div>
        </div>
        <div>
          <div className="text-xs muted">Pivot</div>
          <div className="font-medium">${candidate.pivot}</div>
        </div>
      </div>
      <div className="flex items-center justify-between">
        <div className="text-xs muted">{candidate.detected}</div>
        <div className="flex gap-2">
          <button className="btn btn-primary btn-xs" onClick={async ()=>{ try{ const r=await fetch(`${API_BASE}/api/v1/chart?symbol=${encodeURIComponent(candidate.symbol)}&pivot=${encodeURIComponent(candidate.pivot)}`); const j=await r.json(); const url=j.chart_url||j.local_png; if(url) window.open(url,'_blank'); }catch{}}}>View Chart</button>
          <button className="btn btn-ghost btn-xs" onClick={()=>window.open(`/runs/1`, '_self')}>Details</button>
        </div>
      </div>
    </div>
  )
}

function TimelineChart({ data }: { data: any[] }) {
  return (
    <div className="space-y-4">
      {data.map((period, index) => (
        <div key={index} className="card p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="font-medium">{period.period}</div>
            <div className="text-sm muted">{period.totalScans} scans</div>
          </div>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <div className="muted">Patterns</div>
              <div className="font-medium">{period.patternsDetected}</div>
            </div>
            <div>
              <div className="muted">Hit Rate</div>
              <div className="text-green-400 font-medium">{period.hitRate}%</div>
            </div>
            <div>
              <div className="muted">Avg Return</div>
              <div className="text-blue-400 font-medium">+{period.avgReturn}%</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

export default function Dashboard() {
  const [activeTab, setActiveTab] = React.useState<'overview'|'patterns'|'candidates'|'performance'>('overview')
  const [runId, setRunId] = React.useState<number | null>(1)
  const [patternData, setPatternData] = React.useState<any[]>([])
  const [recent, setRecent] = React.useState<any[]>([])
  const [timeline, setTimeline] = React.useState<any[]>([])
  const [kpis, setKpis] = React.useState<any>({})
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    (async () => {
      try {
        const rid = runId ?? 1
        const a = await fetchJSON<any>(`${API_BASE}/api/v1/analytics/overview?run_id=${rid}`)
        setPatternData(a.pattern_distribution || [])
        setRecent(a.recent_candidates || [])
        setTimeline(a.performance_timeline || [])
        setKpis(a.kpis || {})
      } catch (e: any) {
        setError(e?.message || 'Failed to load analytics')
      }
    })()
  }, [runId])
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Legend Room – Dashboard</h1>
          <div className="text-xs muted">Advanced VCP analytics and performance</div>
        </div>
        <div className="flex gap-2">
          <a className="btn btn-ghost" href="/demo">Open Demo</a>
          <button className="btn btn-primary">Run Scan</button>
        </div>
      </div>

      <div className="flex space-x-1 bg-white/5 rounded-lg p-1 w-max">
        {[
          { id: 'overview', label: 'Overview' },
          { id: 'patterns', label: 'Pattern Analytics' },
          { id: 'candidates', label: 'Recent Candidates' },
          { id: 'performance', label: 'Performance' }
        ].map(t => (
          <button key={t.id} onClick={()=>setActiveTab(t.id as any)} className={`px-4 py-2 rounded-md ${activeTab===t.id?'bg-primary text-black':'hover:bg-white/10'}`}>{t.label}</button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <KPICard title="Active Patterns" value={(kpis.active_patterns ?? 0).toString()} subtitle="Latest day" />
            <KPICard title="Success Rate" value={`${(kpis.success_rate ?? 0).toFixed?.(1) || kpis.success_rate || 0}%`} subtitle="Run window" />
            <KPICard title="Avg Confidence" value={`${kpis.avg_confidence ?? 0}`} subtitle="Candidates" />
            <KPICard title="Market Coverage" value={`${kpis.market_coverage ?? 0}`} subtitle="Unique symbols" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card p-6">
              <h3 className="text-lg font-semibold mb-4">Pattern Distribution</h3>
              <PatternDistributionChart data={patternData} />
              <div className="mt-4 space-y-2 text-sm">
                {patternData.map((p, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full" style={{backgroundColor:p.color}} />{p.name}</div>
                    <span className="muted">{p.count}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="card p-6">
              <h3 className="text-lg font-semibold mb-4">Performance Timeline</h3>
              <TimelineChart data={timeline} />
            </div>
          </div>

          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Recent High-Confidence Candidates</h3>
              <a className="link" href="/demo">View in Demo</a>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {recent.map((c, i) => <CandidateCard key={i} candidate={c} />)}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'patterns' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card p-6">
            <h3 className="text-lg font-semibold mb-4">Pattern Success Analysis</h3>
            <PatternSuccessChart data={patternData} />
          </div>
          <div className="card p-6">
            <h3 className="text-lg font-semibold mb-4">Pattern Usage Over Time</h3>
            <div className="text-sm muted text-center py-8">Interactive timeline chart would go here</div>
          </div>
        </div>
      )}

      {activeTab === 'candidates' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">All Candidates</h3>
            <div className="flex gap-2">
              <select className="input input-sm"><option>All Patterns</option><option>VCP</option><option>Cup & Handle</option><option>Flat Base</option></select>
              <select className="input input-sm"><option>All Sectors</option><option>Technology</option><option>Healthcare</option><option>Finance</option></select>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {recent.map((c, i) => <CandidateCard key={i} candidate={c} />)}
          </div>
        </div>
      )}

      {activeTab === 'performance' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 card p-6">
            <h3 className="text-lg font-semibold mb-4">Performance Metrics</h3>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <KPICard title="Total Returns" value="+$47,293" subtitle="YTD Performance" trend={15.7} />
                <KPICard title="Win Rate" value="68.4%" subtitle="Closed positions" trend={2.1} />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <KPICard title="Avg Hold" value="12.3 days" subtitle="Position duration" />
                <KPICard title="Best Trade" value="+47.2%" subtitle="NVDA Aug-Sep" />
                <KPICard title="Worst Trade" value="-8.3%" subtitle="META Jul-Aug" color="red" />
              </div>
            </div>
          </div>
          <div className="card p-6">
            <h3 className="text-lg font-semibold mb-4">Risk Metrics</h3>
            <div className="space-y-4 text-sm">
              <div className="flex justify-between"><span className="muted">Sharpe Ratio</span><span className="font-medium">1.34</span></div>
              <div className="flex justify-between"><span className="muted">Max Drawdown</span><span className="text-red-400 font-medium">-12.7%</span></div>
              <div className="flex justify-between"><span className="muted">Volatility</span><span className="font-medium">18.4%</span></div>
              <div className="flex justify-between"><span className="muted">Beta</span><span className="font-medium">0.89</span></div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}


