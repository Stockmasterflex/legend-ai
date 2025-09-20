import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ExternalLink, Github, TrendingUp, Brain, Zap } from 'lucide-react'

export default function ProjectsPage() {
  const projects = [
    {
      title: 'Legend AI Trading Platform',
      description: 'AI-powered VCP pattern detection with real-time market scanning and confidence scoring',
      image: '/api/placeholder/600/400',
      tags: ['Python', 'FastAPI', 'Next.js', 'AI/ML', 'Trading'],
      status: 'Live',
      links: {
        demo: '/demo',
        api: 'https://legend-api.onrender.com',
        github: '#',
      },
      features: [
        'Real-time VCP pattern detection',
        'AI confidence scoring (71-94% accuracy)', 
        'Automated chart generation',
        'REST API for integration',
        'Daily market scanning of 500+ stocks',
      ],
      stats: {
        accuracy: '94%',
        stocks: '500+',
        uptime: '99.9%',
      },
    },
    {
      title: 'Market Intelligence Dashboard',
      description: 'Comprehensive dashboard for tracking market trends, sector rotation, and momentum signals',
      image: '/api/placeholder/600/400', 
      tags: ['React', 'TypeScript', 'Charts', 'Real-time'],
      status: 'Development',
      links: {
        demo: '#',
        github: '#',
      },
      features: [
        'Sector rotation analysis',
        'Momentum tracking', 
        'Custom watchlists',
        'Performance analytics',
      ],
    },
    {
      title: 'Automated Trading Signals',
      description: 'End-to-end pipeline for generating, validating, and distributing trading signals',
      image: '/api/placeholder/600/400',
      tags: ['Python', 'PostgreSQL', 'Redis', 'Automation'],
      status: 'Beta',
      links: {
        api: 'https://legend-api.onrender.com/signals',
        github: '#',
      },
      features: [
        'Multi-timeframe analysis',
        'Risk-adjusted scoring',
        'Backtesting integration',
        'Signal validation',
      ],
    },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 pt-20">
      <div className="mx-auto max-w-7xl px-6 lg:px-8 py-24">
        {/* Header */}
        <div className="mx-auto max-w-2xl text-center mb-16">
          <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl">Projects</h1>
          <p className="mt-6 text-lg leading-8 text-gray-300">
            AI-powered trading tools and market intelligence platforms built for momentum traders
          </p>
        </div>

        {/* Featured Project - Legend AI */}
        <div className="mb-20">
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-white mb-2">Featured Project</h2>
            <p className="text-gray-300">Primary trading intelligence platform</p>
          </div>
          
          <Card className="bg-slate-800 border-slate-700 overflow-hidden">
            <div className="grid lg:grid-cols-2">
              <div className="p-8">
                <CardHeader className="p-0 mb-6">
                  <div className="flex items-center justify-between mb-4">
                    <Badge className="bg-green-600">Live Production</Badge>
                    <div className="flex gap-2">
                      <Link href="/demo">
                        <Button size="sm" className="bg-green-600 hover:bg-green-700">
                          <ExternalLink className="h-4 w-4 mr-1" />
                          Demo
                        </Button>
                      </Link>
                      <Button size="sm" variant="outline">
                        <Github className="h-4 w-4 mr-1" />
                        Code
                      </Button>
                    </div>
                  </div>
                  <CardTitle className="text-2xl text-white">{projects[0].title}</CardTitle>
                  <CardDescription className="text-gray-300 text-base">{projects[0].description}</CardDescription>
                </CardHeader>

                <div className="space-y-6">
                  <div>
                    <h4 className="font-semibold text-white mb-3">Key Features:</h4>
                    <ul className="space-y-2">
                      {projects[0].features.map((feature, i) => (
                        <li key={i} className="flex items-start gap-2 text-gray-300">
                          <div className="w-1.5 h-1.5 bg-green-500 rounded-full mt-2 flex-shrink-0" />
                          {feature}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div>
                    <h4 className="font-semibold text-white mb-3">Performance Stats:</h4>
                    <div className="grid grid-cols-3 gap-4">
                      <div className="text-center">
<div className="text-xl font-bold text-green-500">{projects[0]?.stats?.accuracy || ''}</div>
                        <div className="text-xs text-gray-400">Accuracy</div>
                      </div>
                      <div className="text-center">
<div className="text-xl font-bold text-green-500">{projects[0]?.stats?.stocks || ''}</div>
                        <div className="text-xs text-gray-400">Stocks Tracked</div>
                      </div>
                      <div className="text-center">
<div className="text-xl font-bold text-green-500">{projects[0]?.stats?.uptime || ''}</div>
                        <div className="text-xs text-gray-400">Uptime</div>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {projects[0].tags.map((tag) => (
                      <Badge key={tag} variant="secondary">{tag}</Badge>
                    ))}
                  </div>
                </div>
              </div>
              
              <div className="bg-slate-900 p-8 flex items-center">
                <div className="w-full">
                  <div className="bg-black rounded-lg p-4 font-mono text-sm">
                    <div className="text-green-400 mb-2">$ curl legend-api.onrender.com/signals?symbol=AAPL</div>
                    <div className="text-gray-300">{
`{
  "symbol": "AAPL",
  "confidence": 87,
  "signal": "BUY", 
  "pattern": "VCP",
  "entry_point": 175.23,
  "stop_loss": 168.50,
  "target": 192.75,
  "risk_reward": 2.85
}`
                    }</div>
                  </div>
                  <div className="mt-4 text-center">
                    <Link href="/demo">
                      <Button className="bg-green-600 hover:bg-green-700">Try Live Demo</Button>
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>

        {/* Other Projects */}
        <div>
          <h2 className="text-2xl font-bold text-white mb-8">Other Projects</h2>
          <div className="grid md:grid-cols-2 gap-8">
            {projects.slice(1).map((project, index) => (
              <Card key={index} className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant={project.status === 'Live' ? 'default' : 'secondary'}>{project.status}</Badge>
                    <div className="flex gap-2">
                      {project.links.demo && (
                        <Button size="sm" variant="outline">
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                      )}
                      {project.links.github && (
                        <Button size="sm" variant="outline">
                          <Github className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                  <CardTitle className="text-white">{project.title}</CardTitle>
                  <CardDescription className="text-gray-300">{project.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-1 mb-4">
                    {project.features.map((feature, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                        <div className="w-1 h-1 bg-green-500 rounded-full mt-2 flex-shrink-0" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                  <div className="flex flex-wrap gap-1">
                    {project.tags.map((tag) => (
                      <Badge key={tag} variant="outline" className="text-xs">{tag}</Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* Admin Access */}
        <div className="mt-20 text-center">
          <Card className="inline-block bg-slate-800 border-slate-700">
            <CardContent className="p-6">
              <h3 className="text-lg font-semibold text-white mb-2">Administrative Access</h3>
              <p className="text-gray-300 mb-4">View detailed analytics and manage system settings</p>
              <Link href="/admin">
                <Button variant="outline">Admin Portal</Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
