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
  const slugs: { slug: string }[] = await sanityClient.fetch(`*[_type=="post" && !draft]{"slug": slug.current}`)
  return slugs.map((entry) => ({ slug: entry.slug }))
}

export async function generateMetadata({ params }: { params: { slug: string } }) {
  const post = await sanityClient.fetch<PostPayload | null>(postBySlugQuery, { slug: params.slug })
  if (!post) return {}
  const image = post.cover ? urlFor(post.cover).width(1200).height(630).url() : undefined
  return {
    title: post.title,
    description: post.description,
    openGraph: {
      title: post.title,
      description: post.description,
      images: image ? [image] : [],
    },
  }
}

export default async function BlogPost({ params }: { params: { slug: string } }) {
  const post = await sanityClient.fetch<PostPayload | null>(postBySlugQuery, { slug: params.slug })
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
