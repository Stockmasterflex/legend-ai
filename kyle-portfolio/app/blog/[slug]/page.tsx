import type { Metadata } from 'next'
import Image from 'next/image'
import { notFound } from 'next/navigation'
import { PortableText } from '@portabletext/react'

import { sanityClient } from '@/sanity/lib/client'
import { postBySlugQuery } from '@/sanity/lib/queries'
import { urlFor } from '@/sanity/lib/image'
import GiscusComments from '@/components/GiscusComments'

interface PostPayload {
  slug: string
  title: string
  description?: string
  date?: string
  cover?: any
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

export async function generateStaticParams() {
  try {
    const slugs: { slug: string }[] = await sanityClient.fetch(`*[_type=="post" && !draft]{"slug": slug.current}`)
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
  const image = post.cover ? urlFor(post.cover).width(1200).height(630).url() : undefined
  const canonical = `${siteUrl}/blog/${params.slug}`
  return {
    title: post.title,
    description: post.description,
    alternates: { canonical },
    openGraph: {
      title: post.title,
      description: post.description,
      url: canonical,
      images: image ? [image] : [],
    },
    twitter: {
      card: 'summary_large_image',
      title: post.title,
      description: post.description,
      images: image ? [image] : [],
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

  return (
    <main className="prose prose-invert prose-zinc mx-auto max-w-3xl px-4 py-10">
      <article>
        <header className="mb-6 space-y-3">
          <p className="text-sm uppercase tracking-wide text-slate-400">{formatDate(post.date)}</p>
          <h1 className="text-4xl font-bold text-white">{post.title}</h1>
          {post.description && <p className="text-lg text-slate-300">{post.description}</p>}
        </header>
        {post.cover && (
          <div className="relative mb-8 h-72 w-full overflow-hidden rounded-xl bg-slate-950">
            <Image
              src={urlFor(post.cover).width(1600).height(900).url()}
              alt={post.title}
              fill
              className="object-cover"
              sizes="(min-width: 768px) 768px, 100vw"
            />
          </div>
        )}
        <PortableText value={post.body} />
      </article>
      <section className="mt-12 border-t border-slate-800 pt-6">
        <GiscusComments />
      </section>
    </main>
  )
}
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://legend-ai.vercel.app'
