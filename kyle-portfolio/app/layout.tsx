import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Kyle Holthaus – Technical Analyst & AI Builder',
  description: 'Momentum/VCP trader • SIE passed • CMT Level I candidate',
  openGraph: {
    title: 'Kyle Holthaus – Technical Analyst & AI Builder',
    description: 'Momentum/VCP trader • SIE passed • CMT Level I candidate',
    type: 'website'
  },
  twitter: { card: 'summary_large_image', creator: '@' }
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        <div className="min-h-dvh flex flex-col">
          <header className="container-px sticky top-0 z-10 backdrop-blur supports-[backdrop-filter]:bg-background/70 border-b border-white/5">
            <div className="mx-auto max-w-6xl flex items-center justify-between py-4">
              <a href="/" className="font-semibold tracking-wide">Kyle Holthaus</a>
              <nav className="flex items-center gap-3">
                <a className="btn btn-ghost" href="/projects">Projects</a>
                <a className="btn btn-ghost" href="/about">About</a>
                <a className="btn btn-ghost" href="/blog">Blog</a>
                <a className="btn btn-primary" href="/contact">Contact</a>
              </nav>
            </div>
          </header>
          <main className="container-px mx-auto max-w-6xl py-8 grow">
            {children}
          </main>
          <footer className="container-px border-t border-white/5">
            <div className="mx-auto max-w-6xl py-6 text-sm muted">© {new Date().getFullYear()} Kyle Holthaus • Technical Analyst & AI Builder</div>
          </footer>
        </div>
      </body>
    </html>
  )
}

