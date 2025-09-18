import type { Metadata } from 'next'
import Image from 'next/image'
import { notFound } from 'next/navigation'

import { sanityClient } from '@/sanity/lib/client'
import { postBySlugQuery } from '@/sanity/lib/queries'
import { urlFor } from '@/sanity/lib/image'
import GiscusComments from '@/components/GiscusComments'
import { RichPortableText } from '@/components/blog/RichPortableText'
import JsonLd from '@/components/JsonLd'

export const revalidate = 60

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://legend-ai.vercel.app'

interface PostPayload {
  slug: string
  title: string
  description?: string
  date?: string
  cover?: any
  coverAlt?: string
  author?: {
    name?: string
  }
  tags?: { title: string; slug: string }[]
  seo?: {
    title?: string
    description?: string
    ogImage?: any
  }
  body: any
}

function formatDate(input?: string) {
  if (!input) return ''
  try {
    return new Date(input).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  } catch {
    return input
  }
}

function estimateReadingTime(value: any): number | null {
  if (!Array.isArray(value)) return null
  const text = value
    .filter((block: any) => block?._type === 'block' && Array.isArray(block.children))
    .map((block: any) => block.children.map((child: any) => child.text || '').join(' '))
    .join(' ')
    .trim()

  if (!text) return null

  const words = text.split(/\s+/).length
  return Math.max(1, Math.round(words / 200))
}

export async function generateStaticParams() {
  try {
    const slugs: { slug: string }[] = await sanityClient.fetch(
      `*[_type=="post" && defined(slug.current) && !(_id in path('drafts.**'))]{"slug": slug.current}`
    )
    return slugs
      .filter((entry) => typeof entry.slug === 'string' && entry.slug.length)
      .map((entry) => ({ slug: entry.slug }))
  } catch (error) {
    console.warn('[blog] failed to fetch slugs from Sanity', error)
    return []
  }
}

export async function generateMetadata({ params }: { params: { slug: string } }): Promise<Metadata> {
  let post: PostPayload | null = null
  try {
    post = await sanityClient.fetch<PostPayload | null>(postBySlugQuery, { slug: params.slug })
  } catch (error) {
    console.warn('[blog] metadata fetch failed', error)
  }
  if (!post) {
    return { title: 'Legend AI Blog', description: 'Legend AI insights and updates.' }
  }
  const preferredTitle = post.seo?.title || post.title
  const preferredDescription = post.seo?.description || post.description
  const imageSource = post.seo?.ogImage || post.cover
  const image = imageSource ? urlFor(imageSource).width(1200).height(630).url() : undefined
  const canonical = `${siteUrl}/blog/${params.slug}`
  const imageMeta = image
    ? [
        {
          url: image,
          width: 1200,
          height: 630,
          alt: post.coverAlt || post.title,
        },
      ]
    : []
  return {
    title: preferredTitle,
    description: preferredDescription,
    alternates: { canonical },
    openGraph: {
      title: preferredTitle,
      description: preferredDescription,
      url: canonical,
      images: imageMeta,
    },
    twitter: {
      card: 'summary_large_image',
      title: preferredTitle,
      description: preferredDescription,
      images: imageMeta,
    },
  }
}

export default async function BlogPost({ params }: { params: { slug: string } }) {
  let post: PostPayload | null = null
  try {
    post = await sanityClient.fetch<PostPayload | null>(postBySlugQuery, { slug: params.slug })
  } catch (error) {
    console.warn('[blog] post fetch failed', error)
  }
  if (!post) return notFound()

  const canonical = `${siteUrl}/blog/${post.slug}`
  const heroImage = post.seo?.ogImage || post.cover
  const heroUrl = heroImage ? urlFor(heroImage).width(1600).height(900).url() : undefined
  const heroAlt = heroImage === post.seo?.ogImage ? post.seo?.description || post.title : post.coverAlt || post.title
  const readingTime = estimateReadingTime(post.body)

  const articleJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'BlogPosting',
    headline: post.seo?.title || post.title,
    description: post.seo?.description || post.description,
    datePublished: post.date,
    dateModified: post.date,
    url: canonical,
    mainEntityOfPage: canonical,
    image: heroUrl ? [heroUrl] : undefined,
    author: post.author?.name ? { '@type': 'Person', name: post.author.name } : undefined,
    publisher: {
      '@type': 'Organization',
      name: 'Legend AI',
      url: siteUrl,
    },
    timeRequired: readingTime ? `PT${readingTime}M` : undefined,
  }

  return (
    <main className="prose prose-invert prose-zinc mx-auto max-w-3xl px-4 py-10">
      <JsonLd id={`article-${post.slug}`} data={articleJsonLd} />
      <article>
        <header className="mb-6 space-y-3">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs uppercase tracking-wide text-slate-400">
            {post.date && <span>{formatDate(post.date)}</span>}
            {post.author?.name && <span className="text-slate-300">By {post.author.name}</span>}
            {readingTime && <span className="text-slate-500">{readingTime} min read</span>}
          </div>
          <h1 className="text-4xl font-bold text-white">{post.title}</h1>
          {post.description && <p className="text-lg text-slate-300">{post.description}</p>}
          {post.tags && post.tags.length > 0 && (
            <div className="flex flex-wrap gap-2 text-xs text-slate-400">
              {post.tags.map((tag) => (
                <span key={tag.slug || tag.title} className="rounded-full bg-slate-900/60 px-3 py-1">
                  #{tag.title}
                </span>
              ))}
            </div>
          )}
        </header>
        {heroUrl && (
          <div className="relative mb-8 h-72 w-full overflow-hidden rounded-xl bg-slate-950">
            <Image
              src={heroUrl}
              alt={heroAlt}
              fill
              className="object-cover"
              sizes="(min-width: 768px) 768px, 100vw"
            />
          </div>
        )}
        <RichPortableText value={post.body ?? []} />
      </article>
      <section className="mt-12 border-t border-slate-800 pt-6">
        <GiscusComments />
      </section>
    </main>
  )
}
