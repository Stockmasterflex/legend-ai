import {createClient} from '@sanity/client'

const projectId = process.env.NEXT_PUBLIC_SANITY_PROJECT_ID || 'demo'
const dataset = process.env.NEXT_PUBLIC_SANITY_DATASET || 'production'

export const sanityClient = createClient({
  projectId,
  dataset,
  apiVersion: '2025-01-01',
  useCdn: true,
  perspective: 'published',
})
