import Image from 'next/image'
import type { PortableTextComponents } from '@portabletext/react'
import { PortableText } from '@portabletext/react'
import type { Image as SanityImage } from 'sanity'

import { urlFor } from '@/sanity/lib/image'

const components: PortableTextComponents = {
  types: {
    image: ({ value }: { value: SanityImage }) => {
      if (!value?.asset?._ref) return null
      const imageUrl = urlFor(value).width(1200).height(675).fit('max').url()
      const alt = (value as any)?.alt || 'Blog illustration'
      const caption = (value as any)?.caption
      return (
        <figure className="my-8 overflow-hidden rounded-xl border border-slate-800/70 bg-slate-900/40">
          <div className="relative h-0 w-full pb-[56.25%]">
            <Image
              src={imageUrl}
              alt={alt}
              fill
              className="object-cover"
              sizes="(min-width: 1024px) 768px, 100vw"
            />
          </div>
          {(caption || alt) && (
            <figcaption className="px-4 pb-4 pt-2 text-center text-sm text-slate-400">{caption || alt}</figcaption>
          )}
        </figure>
      )
    },
    file: ({ value }: { value: { asset?: { url?: string }; title?: string } }) => {
      if (!value?.asset?.url) return null
      return (
        <a
          className="inline-flex items-center gap-2 rounded-full border border-slate-700/80 px-4 py-2 text-sm text-slate-200 hover:border-cyan-400/60 hover:text-cyan-300"
          href={value.asset.url}
          target="_blank"
          rel="noopener noreferrer"
        >
          📈 {value.title || 'Download attachment'}
        </a>
      )
    },
    chart: ({ value }: { value: { asset?: { url?: string }; title?: string } }) => {
      if (!value?.asset?.url) return null
      return (
        <a
          className="inline-flex items-center gap-2 rounded-full border border-slate-700/80 px-4 py-2 text-sm text-slate-200 hover:border-cyan-400/60 hover:text-cyan-300"
          href={value.asset.url}
          target="_blank"
          rel="noopener noreferrer"
        >
          📊 {value.title || 'Download chart'}
        </a>
      )
    },
    code: ({ value }: { value: { code?: string; language?: string } }) => {
      if (!value?.code) return null
      return (
        <pre className="my-6 overflow-x-auto rounded-xl bg-slate-950/80 p-5 font-mono text-sm text-slate-100 shadow-inner shadow-black/40">
          <code>{value.code}</code>
        </pre>
      )
    },
  },
  block: {
    h2: ({ children }) => <h2 className="mt-10 text-3xl font-semibold text-white">{children}</h2>,
    h3: ({ children }) => <h3 className="mt-8 text-2xl font-semibold text-white">{children}</h3>,
    normal: ({ children }) => <p className="leading-relaxed text-slate-200">{children}</p>,
    blockquote: ({ children }) => (
      <blockquote className="my-6 border-l-4 border-cyan-500/80 bg-slate-900/70 px-5 py-4 text-lg italic text-slate-100">
        {children}
      </blockquote>
    ),
  },
  marks: {
    link: ({ children, value }) => {
      const href = value?.href || '#'
      const isExternal = href.startsWith('http')
      return (
        <a
          href={href}
          className="font-medium text-cyan-300 underline underline-offset-4 hover:text-cyan-200"
          target={isExternal ? '_blank' : undefined}
          rel={isExternal ? 'noopener noreferrer' : undefined}
        >
          {children}
        </a>
      )
    },
    code: ({ children }) => (
      <code className="rounded bg-slate-800 px-1.5 py-0.5 text-sm text-cyan-200">{children}</code>
    ),
  },
  list: {
    bullet: ({ children }) => <ul className="list-disc space-y-2 pl-6 text-slate-200">{children}</ul>,
    number: ({ children }) => <ol className="list-decimal space-y-2 pl-6 text-slate-200">{children}</ol>,
  },
}

export function RichPortableText({ value }: { value: any }) {
  return <PortableText value={value} components={components} />
}

export default RichPortableText
