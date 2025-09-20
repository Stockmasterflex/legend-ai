import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Navbar from '@/components/navbar'
import { cn } from '@/lib/utils'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Kyle Thomas - Technical Analyst & AI Builder',
  description: 'Technical analyst and AI builder specializing in momentum trading and automated market intelligence',
  keywords: ['technical analysis', 'VCP trading', 'momentum trading', 'AI trading', 'pattern recognition'],
  authors: [{ name: 'Kyle Thomas' }],
  openGraph: {
    title: 'Kyle Thomas - Technical Analyst & AI Builder',
    description: 'Advanced AI-powered VCP pattern detection and trading intelligence platform',
    url: 'https://legend-ai.vercel.app',
    siteName: 'Legend AI',
    images: [
      {
        url: 'https://legend-ai.vercel.app/og-image.png',
        width: 1200,
        height: 630,
        alt: 'Legend AI Trading Platform',
      },
    ],
    locale: 'en_US',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Kyle Thomas - Technical Analyst & AI Builder',
    description: 'Advanced AI-powered VCP pattern detection and trading intelligence',
    images: ['https://legend-ai.vercel.app/og-image.png'],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={cn(inter.className, 'bg-slate-900 text-white antialiased')}>
        <Navbar />
        <main className="pt-20">
          {children}
        </main>
      </body>
    </html>
  )
}
