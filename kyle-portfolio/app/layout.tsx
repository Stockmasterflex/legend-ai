import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Navbar from '@/components/navbar'
import { cn } from '@/lib/utils'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Kyle Thomas - Technical Analyst & AI Builder',
  description: 'Technical analyst and AI builder specializing in momentum trading and automated market intelligence',
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
