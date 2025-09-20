import type { MetadataRoute } from 'next'

import { sanityClient } from '@/sanity/lib/client'
import { allPostsQuery } from '@/sanity/lib/queries'

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://legend-ai.vercel.app'

interface Post {
  slug: string
  date?: string
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticRoutes: MetadataRoute.Sitemap = [
    '',
    '/about',
    '/projects',
    '/blog',
    '/contact',
  ].map((route) => ({
    url: `${siteUrl}${route || '/'}`,
    changefreq: 'weekly',
    priority: route === '' ? 1 : 0.7,
  }))

  let posts: Post[] = []
  try {
    posts = await sanityClient.fetch<Post[]>(allPostsQuery)
  } catch (error) {
    console.warn('[sitemap] unable to fetch posts from Sanity', error)
  }

  const postRoutes: MetadataRoute.Sitemap = posts.map((post) => ({
    url: `${siteUrl}/blog/${post.slug}`,
    lastModified: post.date ? new Date(post.date) : undefined,
    changefreq: 'monthly',
    priority: 0.6,
  }))

  return [...staticRoutes, ...postRoutes]
}
