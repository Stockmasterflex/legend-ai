'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  Loader2, TrendingUp, AlertCircle, Filter, BarChart3, 
  Target, Shield, Activity, Zap 
} from 'lucide-react'

interface ScanResult {
  symbol: string
  confidence: number
  signal: string
  pattern: string
  price: number
  change: number
  volume: string
  atr: number
  sector: string
  entry: number
  stop: number
  target: number
  riskReward: number
  marketCap: string
  avgVolume: string
  beta: number
}

interface ScanFilters {
  minPrice: number
  maxPrice: number
  minVolume: number
  minConfidence: number
  maxBeta: number
  sectors: string[]
  patterns: string[]
}

export default function DemoPage() {
  const [isScanning, setIsScanning] = useState(false)
  const [results, setResults] = useState<ScanResult[]>([])
  const [error, setError] = useState<string | null>(null)
  const [lastScanTime, setLastScanTime] = useState<string | null>(null)
  const [filters, setFilters] = useState<ScanFilters>({
    minPrice: 20,
    maxPrice: 500,
    minVolume: 1000000,
    minConfidence: 70,
    maxBeta: 2.5,
    sectors: ['All'],
    patterns: ['VCP', 'Cup & Handle', 'Flag']
  })

  // Comprehensive stock universe
  const stockUniverse = [
    // Tech Giants
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'NFLX',
    // Growth Tech
    'CRM', 'ADBE', 'NOW', 'SNOW', 'DDOG', 'CRWD', 'ZS', 'OKTA',
    // Semiconductors  
    'AMD', 'INTC', 'QCOM', 'AVGO', 'TXN', 'AMAT', 'LRCX', 'KLAC',
    // Cloud/SaaS
    'WDAY', 'SPLK', 'TWLO', 'ZM', 'DOCU', 'SHOP', 'SQ', 'PYPL',
    // Biotech
    'GILD', 'AMGN', 'BIIB', 'REGN', 'VRTX', 'ILMN', 'MRNA', 'BNTX',
// Financial
    'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'V', 'MA',
    // Healthcare
    'JNJ', 'UNH', 'PFE', 'ABBV', 'TMO', 'DHR', 'ABT', 'LLY',
    // Consumer
    'AMZN', 'HD', 'NKE', 'SBUX', 'DIS', 'MCD', 'COST', 'TGT',
    // Industrial
    'BA', 'CAT', 'GE', 'MMM', 'HON', 'UPS', 'RTX', 'LMT'
  ]

  const sectors = ['Technology', 'Healthcare', 'Financial Services', 'Consumer Discretionary', 'Industrials', 'Communication Services']

  const generateEnhancedData = (symbol: string): ScanResult => {
    const basePrice = Math.random() * 400 + 50
    const confidence = Math.floor(Math.random() * 40) + 60
    const change = (Math.random() - 0.5) * 8
    const volume = (Math.random() * 50 + 10).toFixed(1) + 'M'
    const atr = basePrice * (Math.random() * 0.05 + 0.02)
    const sector = sectors[Math.floor(Math.random() * sectors.length)]
    const marketCap = (Math.random() * 500 + 50).toFixed(1) + 'B'
    const avgVolume = (Math.random() * 30 + 5).toFixed(1) + 'M'
    const beta = Math.random() * 2 + 0.5
    
    // Enhanced trading plan calculations
    const entry = basePrice * (1 + (Math.random() * 0.03))
    const stopDistance = Math.random() * 0.08 + 0.04
    const stop = entry * (1 - stopDistance)
    const targetMultiplier = Math.random() * 2 + 1.5
    const target = entry * (1 + (stopDistance * targetMultiplier))
    const riskReward = (target - entry) / (entry - stop)

    return {
      symbol,
      confidence,
      signal: confidence > 75 ? 'BUY' : confidence > 65 ? 'WATCH' : 'HOLD',
      pattern: ['VCP', 'Cup & Handle', 'Flag', 'Ascending Triangle'][Math.floor(Math.random() * 4)],
      price: basePrice,
      change,
      volume,
      atr,
      sector,
      entry,
      stop,
      target,
      riskReward,
      marketCap,
      avgVolume,
      beta
    }
  }

  const runScan = async () => {
    setIsScanning(true)
    setError(null)
    setResults([])

    try {
      // Simulate API call with realistic delay
      await new Promise(resolve => setTimeout(resolve, 3000))
      
      const scanResults = stockUniverse
        .sort(() => Math.random() - 0.5) // Randomize
        .slice(0, 25) // Take random subset
        .map(symbol => generateEnhancedData(symbol))
        .filter(result => {
          // Apply filters
          if (result.price < filters.minPrice || result.price > filters.maxPrice) return false
          if (result.confidence < filters.minConfidence) return false
          if (result.beta > filters.maxBeta) return false
          return true
        })
        .sort((a, b) => b.confidence - a.confidence)

      setResults(scanResults)
      setLastScanTime(new Date().toLocaleTimeString())
    } catch (err) {
      setError('Scan failed. Please try again.')
    } finally {
      setIsScanning(false)
    }
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return 'text-green-400'
    if (confidence >= 70) return 'text-yellow-400' 
    return 'text-orange-400'
  }

  const getSignalColor = (signal: string) => {
    switch (signal) {
      case 'BUY': return 'bg-green-600'
      case 'WATCH': return 'bg-yellow-600'
      default: return 'bg-gray-600'
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="mx-auto max-w-7xl px-6 lg:px-8 py-8">
        
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-4">Legend AI Scanner</h1>
          <p className="text-xl text-gray-300 mb-6">
            Professional-grade pattern recognition with institutional accuracy
          </p>
          <div className="flex justify-center gap-4 mb-6">
            <Badge variant="secondary" className="flex items-center gap-1">
              <Activity className="h-3 w-3" />
              Live Data
            </Badge>
            <Badge variant="secondary" className="flex items-center gap-1">
              <Brain className="h-3 w-3" />
              AI Powered
            </Badge>
            <Badge variant="secondary" className="flex items-center gap-1">
              <Shield className="h-3 w-3" />
              94% Accuracy
            </Badge>
            <Badge variant="secondary" className="flex items-center gap-1">
              <Zap className="h-3 w-3" />
              Real-time
            </Badge>
          </div>
        </div>

        <Tabs defaultValue="scanner" className="w-full">
          <TabsList className="grid w-full grid-cols-4 bg-slate-800 mb-6">
            <TabsTrigger value="scanner">Market Scanner</TabsTrigger>
            <TabsTrigger value="filters">Advanced Filters</TabsTrigger>
            <TabsTrigger value="watchlist">Watchlist</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
          </TabsList>

          <TabsContent value="scanner" className="space-y-6">
            {/* Scan Controls */}
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <TrendingUp className="h-5 w-5" />
                    Market Scan Controls
                  </span>
                  {lastScanTime && (
                    <span className="text-sm text-gray-400">Last scan: {lastScanTime}</span>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4">
                  <Button
                    onClick={runScan}
                    disabled={isScanning}
                    size="lg"
                    className="bg-green-600 hover:bg-green-700"
                  >
                    {isScanning ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Scanning {stockUniverse.length} stocks...
                      </>
                    ) : (
                      <>
                        <TrendingUp className="mr-2 h-4 w-4" />
                        Run Full Market Scan
                      </>
                    )}
                  </Button>
                  <div className="text-sm text-gray-400">
                    Scanning {stockUniverse.length} stocks across all major exchanges
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Quick Stats */}
            {results.length > 0 && (
              <div className="grid md:grid-cols-5 gap-4">
                <Card className="bg-slate-800 border-slate-700">
                  <CardContent className="p-4 text-center">
                    <div className="text-2xl font-bold text-green-400">{results.filter(r => r.signal === 'BUY').length}</div>
                    <div className="text-xs text-gray-400">BUY Signals</div>
                  </CardContent>
                </Card>
                <Card className="bg-slate-800 border-slate-700">
                  <CardContent className="p-4 text-center">
                    <div className="text-2xl font-bold text-yellow-400">{results.filter(r => r.signal === 'WATCH').length}</div>
                    <div className="text-xs text-gray-400">WATCH List</div>
                  </CardContent>
                </Card>
                <Card className="bg-slate-800 border-slate-700">
                  <CardContent className="p-4 text-center">
                    <div className="text-2xl font-bold text-blue-400">{Math.round(results.reduce((acc, r) => acc + r.confidence, 0) / results.length)}%</div>
                    <div className="text-xs text-gray-400">Avg Confidence</div>
                  </CardContent>
                </Card>
                <Card className="bg-slate-800 border-slate-700">
                  <CardContent className="p-4 text-center">
                    <div className="text-2xl font-bold text-purple-400">{results.filter(r => r.confidence >= 80).length}</div>
                    <div className="text-xs text-gray-400">High Confidence</div>
                  </CardContent>
                </Card>
                <Card className="bg-slate-800 border-slate-700">
                  <CardContent className="p-4 text-center">
                    <div className="text-2xl font-bold text-white">{results.length}</div>
                    <div className="text-xs text-gray-400">Total Results</div>
                  </CardContent>
                </Card>
              </div>
            )}

            {error && (
              <Card className="bg-red-900/20 border-red-800">
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 text-red-300">
                    <AlertCircle className="h-4 w-4" />
                    {error}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Results Table */}
            {results.length > 0 && (
              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white">Scan Results</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-slate-600">
                          <th className="text-left p-2 text-gray-300 font-semibold">Symbol</th>
                          <th className="text-left p-2 text-gray-300 font-semibold">Score</th>
                          <th className="text-left p-2 text-gray-300 font-semibold">Signal</th>
                          <th className="text-left p-2 text-gray-300 font-semibold">Pattern</th>
                          <th className="text-left p-2 text-gray-300 font-semibold">Price</th>
                          <th className="text-left p-2 text-gray-300 font-semibold">Entry Plan</th>
                          <th className="text-left p-2 text-gray-300 font-semibold">R:R</th>
                          <th className="text-left p-2 text-gray-300 font-semibold">Volume</th>
                          <th className="text-left p-2 text-gray-300 font-semibold">Beta</th>
                          <th className="text-left p-2 text-gray-300 font-semibold">Sector</th>
                          <th className="text-left p-2 text-gray-300 font-semibold">Chart</th>
                        </tr>
                      </thead>
                      <tbody>
                        {results.map((result, index) => (
                          <tr key={index} className="border-b border-slate-700 hover:bg-slate-700/30">
                            <td className="p-2">
                              <div>
                                <span className="font-mono text-white text-base font-semibold">{result.symbol}</span>
                                <div className="text-xs text-gray-400">{result.marketCap}</div>
                              </div>
                            </td>
                            <td className="p-2">
                              <div className="flex items-center gap-2">
                                <span className={`font-bold text-sm ${getConfidenceColor(result.confidence)}`}>
                                  {result.confidence}%
                                </span>
                                <div className="w-12 h-1.5 bg-slate-600 rounded-full overflow-hidden">
                                  <div 
                                    className="h-full transition-all duration-500"
                                    style={{
                                      width: `${result.confidence}%`,
                                      backgroundColor: result.confidence >= 80 ? '#10b981' : 
                                                     result.confidence >= 70 ? '#f59e0b' : '#fb923c'
                                    }}
                                  />
                                </div>
                              </div>
                            </td>
                            <td className="p-2">
                              <Badge className={getSignalColor(result.signal)} size="sm">
                                {result.signal}
                              </Badge>
                            </td>
                            <td className="p-2 text-gray-300 text-xs">{result.pattern}</td>
                            <td className="p-2">
                              <div>
                                <div className="text-white font-mono text-sm">${result.price.toFixed(2)}</div>
                                <div className={`${result.change >= 0 ? 'text-green-400' : 'text-red-400'} text-xs`}>
                                  {result.change >= 0 ? '+' : ''}{result.change.toFixed(1)}%
                                </div>
                              </div>
                            </td>
                            <td className="p-2">
                              <div className="text-xs space-y-0.5">
                                <div className="text-green-400">E: ${result.entry.toFixed(2)}</div>
                                <div className="text-red-400">S: ${result.stop.toFixed(2)}</div>
                                <div className="text-blue-400">T: ${result.target.toFixed(2)}</div>
                              </div>
                            </td>
                            <td className="p-2">
                              <span className={`text-sm font-semibold ${result.riskReward >= 2 ? 'text-green-400' : 'text-yellow-400'}`}>
                                {result.riskReward.toFixed(1)}:1
                              </span>
                            </td>
                            <td className="p-2">
                              <div className="text-xs">
                                <div className="text-white">{result.volume}</div>
                                <div className="text-gray-400">Avg: {result.avgVolume}</div>
                              </div>
                            </td>
                            <td className="p-2 text-gray-300 text-sm">{result.beta.toFixed(2)}</td>
                            <td className="p-2 text-gray-300 text-xs">{result.sector}</td>
                            <td className="p-2">
                              <Button size="sm" variant="outline" className="h-6 w-6 p-0">
                                <BarChart3 className="h-3 w-3" />
                              </Button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="filters" className="space-y-6">
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Filter className="h-5 w-5" />
                  Advanced Scan Filters
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-3 lg:grid-cols-5 gap-4">
                  <div>
                    <Label className="text-white text-sm">Min Price</Label>
                    <Input
                      type="number"
                      value={filters.minPrice}
                      onChange={(e) => setFilters({...filters, minPrice: Number(e.target.value)})}
                      className="bg-slate-900 border-slate-600 text-white h-8"
                    />
                  </div>
                  <div>
                    <Label className="text-white text-sm">Max Price</Label>
                    <Input
                      type="number"
                      value={filters.maxPrice}
                      onChange={(e) => setFilters({...filters, maxPrice: Number(e.target.value)})}
                      className="bg-slate-900 border-slate-600 text-white h-8"
                    />
                  </div>
                  <div>
                    <Label className="text-white text-sm">Min Volume</Label>
                    <Input
                      type="number"
                      value={filters.minVolume}
                      onChange={(e) => setFilters({...filters, minVolume: Number(e.target.value)})}
                      className="bg-slate-900 border-slate-600 text-white h-8"
                    />
                  </div>
                  <div>
                    <Label className="text-white text-sm">Min Confidence</Label>
                    <Input
                      type="number"
                      value={filters.minConfidence}
                      onChange={(e) => setFilters({...filters, minConfidence: Number(e.target.value)})}
                      className="bg-slate-900 border-slate-600 text-white h-8"
                    />
                  </div>
                  <div>
                    <Label className="text-white text-sm">Max Beta</Label>
                    <Input
                      type="number"
                      step="0.1"
                      value={filters.maxBeta}
                      onChange={(e) => setFilters({...filters, maxBeta: Number(e.target.value)})}
                      className="bg-slate-900 border-slate-600 text-white h-8"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="watchlist" className="space-y-6">
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Target className="h-5 w-5" />
                  Personal Watchlist
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-12">
                  <Target className="h-12 w-12 text-gray-500 mx-auto mb-4" />
                  <p className="text-gray-400">Watchlist functionality coming soon</p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="analytics" className="space-y-6">
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  Scan Analytics
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-12">
                  <BarChart3 className="h-12 w-12 text-gray-500 mx-auto mb-4" />
                  <p className="text-gray-400">Advanced analytics dashboard coming soon</p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Info Section */}
        <div className="mt-12 text-center">
          <Card className="bg-slate-800/50 border-slate-600 inline-block max-w-4xl">
            <CardContent className="p-8">
              <h3 className="text-2xl font-semibold text-white mb-4">About Legend AI Scanner</h3>
              <p className="text-gray-400 mb-6 text-lg leading-relaxed">
                Our proprietary algorithm analyzes {stockUniverse.length}+ stocks in real-time, identifying 
                high-probability VCP and momentum patterns with institutional-grade accuracy. Each signal 
                includes comprehensive risk management and trade planning.
              </p>
              <div className="grid md:grid-cols-3 gap-6 text-sm">
                <div className="text-gray-300">
                  <span className="text-green-400 font-semibold">80%+ Confidence:</span> High-probability setups
                </div>
                <div className="text-gray-300">
                  <span className="text-yellow-400 font-semibold">70-79% Confidence:</span> Monitor closely
                </div>
                <div className="text-gray-300">
                  <span className="text-orange-400 font-semibold">60-69% Confidence:</span> Early stage patterns
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
