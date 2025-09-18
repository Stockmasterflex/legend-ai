import type { Metadata } from 'next'
import Link from 'next/link'
import Image from 'next/image'
import { sanityClient } from '@/sanity/lib/client'
import { allPostsQuery } from '@/sanity/lib/queries'
import { urlFor } from '@/sanity/lib/image'
import JsonLd from '@/components/JsonLd'

export const revalidate = 60

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://legend-ai.vercel.app'

export const metadata: Metadata = {
  title: 'Legend AI Blog',
  description: 'Strategy notes, scan breakdowns, and product updates from the Legend AI desk.',
  alternates: { canonical: '/blog' },
  openGraph: {
    title: 'Legend AI Blog',
    description: 'Strategy notes, scan breakdowns, and product updates from the Legend AI desk.',
    url: `${siteUrl}/blog`,
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Legend AI Blog',
    description: 'Strategy notes, scan breakdowns, and product updates from the Legend AI desk.',
  },
}

interface Post {
  slug: string
  title: string
  description?: string
  date?: string
  cover?: any
  coverAlt?: string
  tags?: { title: string; slug: string }[]
}

function formatDate(input?: string) {
  if (!input) return ''
  try {
    return new Date(input).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  } catch {
    return input
  }
}

export default async function BlogIndex() {
  let posts: Post[] = []
  try {
    posts = await sanityClient.fetch<Post[]>(allPostsQuery)
  } catch (error) {
    console.warn('[blog] failed to fetch posts from Sanity', error)
  }
  const hasPosts = posts.length > 0
  const blogJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Blog',
    name: 'Legend AI Blog',
    url: `${siteUrl}/blog`,
    blogPost: posts.map((post) => ({
      '@type': 'BlogPosting',
      headline: post.title,
      url: `${siteUrl}/blog/${post.slug}`,
      datePublished: post.date,
    })),
  }

  return (
    <main className="prose prose-invert prose-zinc mx-auto max-w-3xl px-4 py-10">
      <JsonLd id="legend-blog" data={blogJsonLd} />
      <h1 className="text-white">Legend AI Blog</h1>
      <p className="text-slate-300">
        Strategy notes, scan breakdowns, and platform updates straight from the Legend AI desk.
      </p>
      {!hasPosts && (
        <div className="not-prose mt-8 rounded-xl border border-slate-800/80 bg-slate-900/60 p-6 text-sm text-slate-300">
          <p className="font-medium text-white">No posts yet.</p>
          <p className="mt-2">
            Use Legend Studio to publish your first update. Posts go live as soon as you press publish in Sanity.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Link href="/studio" className="btn btn-primary text-sm">
              Open Studio
            </Link>
          </div>
        </div>
      )}
      {hasPosts && (
        <ul className="not-prose mt-8 space-y-8">
          {posts.map((post) => (
            <li key={post.slug} className="overflow-hidden rounded-xl border border-slate-800/80 bg-slate-900/60">
              <Link href={`/blog/${post.slug}`} className="block">
                {post.cover && (
                  <div className="relative h-56 w-full overflow-hidden bg-slate-950">
                    <Image
                      src={urlFor(post.cover).width(1200).height(630).url()}
                      alt={post.coverAlt || post.title}
                      fill
                      className="object-cover transition-transform duration-500 hover:scale-105"
                      sizes="(min-width: 768px) 768px, 100vw"
                    />
                  </div>
                )}
                <div className="space-y-3 p-5">
                  <div className="text-xs uppercase tracking-wide text-slate-400">
                    {formatDate(post.date)}
                  </div>
                  <h2 className="text-2xl font-semibold text-white">{post.title}</h2>
                  {post.description && <p className="text-sm text-slate-300">{post.description}</p>}
                  {post.tags && post.tags.length > 0 && (
                    <div className="flex flex-wrap gap-2 text-xs text-slate-400">
                      {post.tags.map((tag) => (
                        <span key={tag.slug || tag.title} className="rounded-full bg-slate-800 px-3 py-1">
                          #{tag.title}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  )
}
