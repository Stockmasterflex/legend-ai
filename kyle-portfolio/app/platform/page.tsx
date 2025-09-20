'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  TrendingUp, BarChart3, Brain, Settings, BookOpen, 
  MessageSquare, Target, Activity, Calendar, PieChart 
} from 'lucide-react'

export default function PlatformPage() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  
  useEffect(() => {
    // Simple auth check - in production, use proper authentication
    const authKey = localStorage.getItem('platform_access')
    if (authKey === 'legend_ai_2025') {
      setIsAuthenticated(true)
    }
  }, [])

  const authenticate = () => {
    const key = prompt('Enter platform access key:')
    if (key === 'legend_ai_2025') {
      localStorage.setItem('platform_access', key)
      setIsAuthenticated(true)
    } else {
      alert('Invalid access key')
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <Card className="bg-slate-800 border-slate-700 w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle className="text-white">Platform Access</CardTitle>
            <p className="text-gray-300">Enter your credentials to access the trading platform</p>
          </CardHeader>
          <CardContent className="text-center">
            <Button onClick={authenticate} className="bg-green-600 hover:bg-green-700">
              Authenticate
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="mx-auto max-w-7xl px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Legend AI Platform</h1>
          <p className="text-gray-300">Professional trading intelligence dashboard</p>
        </div>

        <Tabs defaultValue="scanner" className="w-full">
          <TabsList className="grid w-full grid-cols-6 bg-slate-800">
            <TabsTrigger value="scanner">Scanner</TabsTrigger>
            <TabsTrigger value="portfolio">Portfolio</TabsTrigger>
            <TabsTrigger value="journal">Journal</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
            <TabsTrigger value="research">Research</TabsTrigger>
            <TabsTrigger value="tools">Tools</TabsTrigger>
          </TabsList>

          <TabsContent value="scanner" className="space-y-6">
            <div className="grid lg:grid-cols-3 gap-6">
              <Card className="lg:col-span-2 bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <TrendingUp className="h-5 w-5" />
                    Real-time Market Scanner
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-96 bg-slate-900 rounded-lg flex items-center justify-center">
                    <div className="text-center">
                      <BarChart3 className="h-12 w-12 text-green-500 mx-auto mb-4" />
                      <p className="text-white">Advanced Scanner Interface</p>
                      <p className="text-gray-400 text-sm">Live market data and pattern detection</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              
              <div className="space-y-6">
                <Card className="bg-slate-800 border-slate-700">
                  <CardHeader>
                    <CardTitle className="text-white text-lg">Active Signals</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-white font-mono">NVDA</span>
                        <Badge className="bg-green-600">87%</Badge>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-white font-mono">AAPL</span>
                        <Badge className="bg-yellow-600">74%</Badge>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-white font-mono">MSFT</span>
                        <Badge className="bg-green-600">81%</Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-slate-800 border-slate-700">
                  <CardHeader>
                    <CardTitle className="text-white text-lg">Market Status</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-gray-300">Market</span>
                        <span className="text-green-400">Open</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-300">VIX</span>
                        <span className="text-white">18.4</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-300">Trend</span>
                        <span className="text-green-400">Bullish</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="portfolio" className="space-y-6">
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
              <Card className="bg-slate-800 border-slate-700">
                <CardContent className="p-6 text-center">
                  <div className="text-2xl font-bold text-green-400">$127,450</div>
                  <div className="text-gray-400">Portfolio Value</div>
                </CardContent>
              </Card>
              <Card className="bg-slate-800 border-slate-700">
                <CardContent className="p-6 text-center">
                  <div className="text-2xl font-bold text-green-400">+12.7%</div>
                  <div className="text-gray-400">Monthly Return</div>
                </CardContent>
              </Card>
              <Card className="bg-slate-800 border-slate-700">
                <CardContent className="p-6 text-center">
                  <div className="text-2xl font-bold text-white">8</div>
                  <div className="text-gray-400">Open Positions</div>
                </CardContent>
              </Card>
              <Card className="bg-slate-800 border-slate-700">
                <CardContent className="p-6 text-center">
                  <div className="text-2xl font-bold text-yellow-400">72%</div>
                  <div className="text-gray-400">Win Rate</div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="journal" className="space-y-6">
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <BookOpen className="h-5 w-5" />
                  Trading Journal
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-12">
                  <BookOpen className="h-12 w-12 text-gray-500 mx-auto mb-4" />
                  <p className="text-gray-400">Advanced trade journaling and analysis coming soon</p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="analytics" className="space-y-6">
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <PieChart className="h-5 w-5" />
                  Performance Analytics
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-12">
                  <PieChart className="h-12 w-12 text-gray-500 mx-auto mb-4" />
                  <p className="text-gray-400">Comprehensive analytics dashboard coming soon</p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="research" className="space-y-6">
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Brain className="h-5 w-5" />
                  Research & AI Tools
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-12">
                  <Brain className="h-12 w-12 text-gray-500 mx-auto mb-4" />
                  <p className="text-gray-400">AI-powered research tools coming soon</p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="tools" className="space-y-6">
            <div className="grid md:grid-cols-2 gap-6">
              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white">Foreman Bot</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="bg-slate-900 p-4 rounded">
                      <div className="text-sm text-gray-400 mb-2">Chat with your AI assistant</div>
                      <div className="text-white">Ready to help with analysis and tasks</div>
                    </div>
                    <Button variant="outline" className="w-full">
                      Open Chat
                    </Button>
                  </div>
                </CardContent>
              </Card>
              
              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white">Content Tools</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <Button variant="outline" className="w-full justify-start">
                      <MessageSquare className="h-4 w-4 mr-2" />
                      Content Repurposer
                    </Button>
                    <Button variant="outline" className="w-full justify-start">
                      <Calendar className="h-4 w-4 mr-2" />
                      Schedule Posts
                    </Button>
                    <Button variant="outline" className="w-full justify-start">
                      <Settings className="h-4 w-4 mr-2" />
                      Platform Settings
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
