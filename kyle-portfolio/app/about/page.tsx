import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { TrendingUp, Brain, Award, Code } from 'lucide-react'

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 pt-20">
      <div className="mx-auto max-w-4xl px-6 lg:px-8 py-24">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl mb-6">
            About Kyle
          </h1>
          <p className="text-xl text-gray-300 max-w-2xl mx-auto">
            Technical analyst and AI builder focused on momentum trading strategies and automated market intelligence systems
          </p>
        </div>

        {/* Main Content */}
        <div className="space-y-12">
          {/* Professional Summary */}
          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="p-8">
              <h2 className="text-2xl font-bold text-white mb-6">Professional Background</h2>
              <div className="prose prose-gray max-w-none text-gray-300">
                <p className="text-lg leading-relaxed mb-6">
                  Kyle Holthaus is a technical analyst and AI builder with extensive experience in momentum trading 
                  and systematic market analysis. He combines robust market structure understanding with 
                  pragmatic engineering to ship reliable trading tools.
                </p>
                
                <div className="grid md:grid-cols-2 gap-8 mt-8">
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                      <TrendingUp className="h-5 w-5 text-green-500" />
                      Trading Expertise
                    </h3>
                    <ul className="space-y-2 text-gray-300">
                      <li>• SIE passed • CMT Level I candidate</li>
                      <li>• Momentum/VCP trader trained on Minervini principles</li>
                      <li>• Hands-on with yfinance, SQLAlchemy, headless Chromium for charts</li>
                      <li>• Systematic approach to pattern recognition and risk assessment</li>
                    </ul>
                  </div>
                  
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                      <Code className="h-5 w-5 text-green-500" />
                      Technical Skills
                    </h3>
                    <ul className="space-y-2 text-gray-300">
                      <li>• Python, FastAPI, Next.js, Tailwind; Dockerized microservices</li>
                      <li>• PostgreSQL, Redis for caching and session management</li>
                      <li>• Real-time data processing and API development</li>
                      <li>• AI/ML integration for pattern detection and scoring</li>
                    </ul>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Credentials & Certifications */}
          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="p-8">
              <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
                <Award className="h-6 w-6 text-green-500" />
                Credentials & Education
              </h2>
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-semibold text-white mb-3">Professional Certifications</h4>
                  <div className="space-y-2">
                    <Badge className="bg-green-600">SIE Passed</Badge>
                    <Badge variant="secondary">CMT Level I Candidate (Dec 2025)</Badge>
                  </div>
                </div>
                <div>
                  <h4 className="font-semibold text-white mb-3">Specialized Training</h4>
                  <div className="space-y-2 text-gray-300">
                    <div>• Minervini Private Training Program (2021-2023)</div>
                    <div>• Advanced VCP and momentum strategies</div>
                    <div>• Institutional-grade risk management</div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Current Focus */}
          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="p-8">
              <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
                <Brain className="h-6 w-6 text-green-500" />
                Current Focus
              </h2>
              <div className="prose prose-gray max-w-none text-gray-300">
                <p className="text-lg leading-relaxed mb-6">
                  Currently building <strong className="text-white">Legend Room</strong> - an AI-powered trading platform 
                  that democratizes institutional-grade pattern recognition. The platform combines automated VCP 
                  detection with real-time confidence scoring to help retail traders identify high-probability setups.
                </p>
                
                <div className="bg-slate-900 rounded-lg p-6 mt-6">
                  <h4 className="font-semibold text-white mb-3">Legend Room Key Metrics:</h4>
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <div className="text-2xl font-bold text-green-500">94%</div>
                      <div className="text-sm text-gray-400">Pattern Accuracy</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-green-500">500+</div>
                      <div className="text-sm text-gray-400">Daily Scans</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-green-500">24/7</div>
                      <div className="text-sm text-gray-400">Monitoring</div>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Skills Tags */}
          <div className="text-center">
            <h2 className="text-xl font-bold text-white mb-6">Core Competencies</h2>
            <div className="flex flex-wrap justify-center gap-2">
              {[
                'Technical Analysis', 'Pattern Detection', 'Backtesting (HIL)', 'FastAPI', 'Next.js', 
                'TypeScript', 'Docker', 'CI', 'PostgreSQL', 'Python/LLM'
              ].map((skill) => (
                <Badge key={skill} variant="secondary" className="text-sm">
                  {skill}
                </Badge>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

