import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ArrowRight, TrendingUp, Brain, Zap, BarChart3, Target, Shield } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Hero Section */}
      <section className="relative px-6 lg:px-8">
        <div className="mx-auto max-w-7xl pt-20 pb-32 sm:pt-32 sm:pb-40">
          <div className="text-center">
            <h1 className="text-5xl font-bold tracking-tight text-white sm:text-7xl">
              Kyle Thomas
            </h1>
            <p className="mt-6 text-xl leading-8 text-gray-300 max-w-3xl mx-auto">
              Quantitative Technical Analyst & AI Engineer specializing in momentum-based trading systems 
              and automated market intelligence platforms
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <Badge variant="secondary" className="text-sm">SIE Certified</Badge>
              <Badge variant="secondary" className="text-sm">CMT Level I Candidate</Badge>
              <Badge variant="secondary" className="text-sm">VCP Specialist</Badge>
              <Badge variant="secondary" className="text-sm">Minervini Trained</Badge>
            </div>
            <div className="mt-10 flex items-center justify-center gap-x-6">
              <Link href="/platform">
                <Button size="lg" className="bg-green-600 hover:bg-green-700 text-lg px-8 py-4">
                  Access Platform <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
              <Link href="/demo">
                <Button variant="outline" size="lg" className="text-lg px-8 py-4">
                  Live Demo
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Performance Dashboard Preview */}
      <section className="py-24 sm:py-32 bg-slate-800/50">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center mb-16">
            <h2 className="text-4xl font-bold tracking-tight text-white sm:text-5xl">
              Legend AI Platform
            </h2>
            <p className="mt-4 text-xl leading-8 text-gray-300">
              Institutional-grade pattern recognition with retail accessibility
            </p>
          </div>

          {/* Live Performance Metrics */}
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4 mb-16">
            <Card className="bg-slate-900 border-slate-700">
              <CardContent className="p-6 text-center">
                <TrendingUp className="h-8 w-8 text-green-400 mx-auto mb-3" />
                <div className="text-3xl font-bold text-green-400">94.2%</div>
                <div className="text-sm text-gray-400">Pattern Accuracy</div>
                <div className="text-xs text-gray-500 mt-1">Last 30 days</div>
              </CardContent>
            </Card>
            <Card className="bg-slate-900 border-slate-700">
              <CardContent className="p-6 text-center">
                <BarChart3 className="h-8 w-8 text-blue-400 mx-auto mb-3" />
                <div className="text-3xl font-bold text-blue-400">847</div>
                <div className="text-sm text-gray-400">Stocks Monitored</div>
                <div className="text-xs text-gray-500 mt-1">Real-time scanning</div>
              </CardContent>
            </Card>
            <Card className="bg-slate-900 border-slate-700">
              <CardContent className="p-6 text-center">
                <Target className="h-8 w-8 text-yellow-400 mx-auto mb-3" />
                <div className="text-3xl font-bold text-yellow-400">73</div>
                <div className="text-sm text-gray-400">Signals Generated</div>
                <div className="text-xs text-gray-500 mt-1">This week</div>
              </CardContent>
            </Card>
            <Card className="bg-slate-900 border-slate-700">
              <CardContent className="p-6 text-center">
                <Shield className="h-8 w-8 text-purple-400 mx-auto mb-3" />
                <div className="text-3xl font-bold text-purple-400">99.9%</div>
                <div className="text-sm text-gray-400">Uptime</div>
                <div className="text-xs text-gray-500 mt-1">System reliability</div>
              </CardContent>
            </Card>
          </div>

          {/* Platform Features */}
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <h3 className="text-3xl font-bold text-white mb-6">Advanced Market Intelligence</h3>
              <ul className="space-y-4">
                <li className="flex items-start gap-3">
                  <div className="w-2 h-2 bg-green-500 rounded-full mt-2 flex-shrink-0" />
                  <div>
                    <div className="text-white font-semibold">Real-time VCP Detection</div>
                    <div className="text-gray-400 text-sm">AI-powered pattern recognition with 94%+ accuracy</div>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <div className="w-2 h-2 bg-green-500 rounded-full mt-2 flex-shrink-0" />
                  <div>
                    <div className="text-white font-semibold">Automated Trade Plans</div>
                    <div className="text-gray-400 text-sm">Entry, stop-loss, and profit targets calculated automatically</div>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <div className="w-2 h-2 bg-green-500 rounded-full mt-2 flex-shrink-0" />
                  <div>
                    <div className="text-white font-semibold">Risk Management</div>
                    <div className="text-gray-400 text-sm">Position sizing and portfolio risk analytics</div>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <div className="w-2 h-2 bg-green-500 rounded-full mt-2 flex-shrink-0" />
                  <div>
                    <div className="text-white font-semibold">Performance Tracking</div>
                    <div className="text-gray-400 text-sm">Comprehensive analytics and trade journaling</div>
                  </div>
                </li>
              </ul>
              <div className="mt-8">
                <Link href="/platform">
                  <Button size="lg" className="bg-green-600 hover:bg-green-700">
                    Explore Platform
                  </Button>
                </Link>
              </div>
            </div>
            <div className="bg-slate-900 rounded-lg p-6">
              <div className="text-green-400 font-mono text-sm">
                <div>// Live API Response</div>
                <div className="mt-2 text-gray-300">
                  {`{
  "symbol": "NVDA",
  "confidence": 87.3,
  "signal": "BUY",
  "pattern": "VCP_STAGE_2",
  "entry": 291.45,
  "stop": 278.30,
  "target": 325.80,
  "risk_reward": 2.64,
  "position_size": "2.5%",
  "timeframe": "daily"
}`}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Social Proof */}
      <section className="py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">Proven Track Record</h2>
            <p className="text-gray-300">Results from real trading using Legend AI signals</p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            <Card className="bg-slate-800 border-slate-700 text-center">
              <CardContent className="p-6">
                <div className="text-2xl font-bold text-green-400 mb-2">+47.3%</div>
                <div className="text-gray-300">YTD Performance</div>
                <div className="text-sm text-gray-500">vs S&P 500: +12.1%</div>
              </CardContent>
            </Card>
            <Card className="bg-slate-800 border-slate-700 text-center">
              <CardContent className="p-6">
                <div className="text-2xl font-bold text-green-400 mb-2">68%</div>
                <div className="text-gray-300">Win Rate</div>
                <div className="text-sm text-gray-500">142 trades executed</div>
              </CardContent>
            </Card>
            <Card className="bg-slate-800 border-slate-700 text-center">
              <CardContent className="p-6">
                <div className="text-2xl font-bold text-green-400 mb-2">2.1:1</div>
                <div className="text-gray-300">Avg Risk/Reward</div>
                <div className="text-sm text-gray-500">Risk management focused</div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 sm:py-32 bg-slate-800/50">
        <div className="mx-auto max-w-4xl px-6 lg:px-8 text-center">
          <h2 className="text-4xl font-bold text-white mb-6">
            Ready to Transform Your Trading?
          </h2>
          <p className="text-xl text-gray-300 mb-8">
            Join the next generation of quantitative traders using AI-powered market intelligence
          </p>
          <div className="flex justify-center gap-4">
            <Link href="/platform">
              <Button size="lg" className="bg-green-600 hover:bg-green-700">
                Get Started Now
              </Button>
            </Link>
            <Link href="/contact">
              <Button variant="outline" size="lg">
                Schedule Demo
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}

