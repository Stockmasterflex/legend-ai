import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ArrowRight, TrendingUp, Brain, Zap } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Hero Section */}
      <section className="relative px-6 lg:px-8 pt-14">
        <div className="mx-auto max-w-7xl pt-20 pb-32 sm:pt-48 sm:pb-40">
          <div className="text-center">
            <h1 className="text-4xl font-bold tracking-tight text-white sm:text-6xl">
              Kyle Holthaus
            </h1>
            <p className="mt-6 text-lg leading-8 text-gray-300">
              Technical Analyst & AI Builder specializing in momentum trading and automated market intelligence
            </p>
            <div className="mt-6 flex items-center justify-center gap-4">
              <Badge variant="secondary">SIE Passed</Badge>
              <Badge variant="secondary">CMT Level I Candidate</Badge>
              <Badge variant="secondary">VCP Specialist</Badge>
            </div>
            <div className="mt-10 flex items-center justify-center gap-x-6">
              <Link href="/projects">
                <Button size="lg" className="bg-green-600 hover:bg-green-700">
                  View Projects <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <Link href="/about">
                <Button variant="outline" size="lg">
                  About Me
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Featured Project - Legend AI */}
      <section className="py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
              Featured Project
            </h2>
            <p className="mt-4 text-lg leading-8 text-gray-300">
              Advanced AI-powered trading intelligence platform
            </p>
          </div>
          
          <div className="mx-auto mt-16 max-w-5xl">
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Brain className="h-6 w-6 text-green-500" />
                  <CardTitle className="text-white">Legend AI Trading Platform</CardTitle>
                </div>
                <CardDescription className="text-gray-300">
                  Automated VCP pattern detection with real-time confidence scoring and market intelligence
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="font-semibold text-white mb-3">Key Features:</h4>
                    <ul className="space-y-2 text-gray-300">
                      <li className="flex items-center gap-2">
                        <TrendingUp className="h-4 w-4 text-green-500" />
                        Real-time VCP pattern scanning
                      </li>
                      <li className="flex items-center gap-2">
                        <Zap className="h-4 w-4 text-green-500" />
                        AI-powered confidence scoring
                      </li>
                      <li className="flex items-center gap-2">
                        <Brain className="h-4 w-4 text-green-500" />
                        Automated chart generation
                      </li>
                    </ul>
                    <div className="mt-6">
                      <Link href="/demo">
                        <Button className="bg-green-600 hover:bg-green-700">
                          Try Live Demo
                        </Button>
                      </Link>
                    </div>
                  </div>
                  <div className="bg-slate-900 rounded-lg p-4">
                    <div className="text-green-400 font-mono text-sm">
                      <div>$ curl legend-api.onrender.com/signals?symbol=AAPL</div>
                      <div className="mt-2 text-gray-400">
                        {"{"}<br />
                        {"  "}confidence: 87,<br />
                        {"  "}signal: "BUY",<br />
                        {"  "}pattern: "VCP"<br />
                        {"}"}
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Quick Stats */}
      <section className="py-24 sm:py-32 bg-slate-800/50">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
            <div className="text-center">
              <div className="text-3xl font-bold text-green-500">94%</div>
              <div className="text-sm text-gray-300">Pattern Detection Accuracy</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-green-500">500+</div>
              <div className="text-sm text-gray-300">Stocks Monitored Daily</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-green-500">24/7</div>
              <div className="text-sm text-gray-300">Automated Scanning</div>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}

