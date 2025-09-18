const projectId = process.env.NEXT_PUBLIC_SANITY_PROJECT_ID
const dataset = process.env.NEXT_PUBLIC_SANITY_DATASET

if (!projectId) {
  throw new Error('Missing NEXT_PUBLIC_SANITY_PROJECT_ID environment variable. Set it in your .env.local or project settings.')
}

if (!dataset) {
  throw new Error('Missing NEXT_PUBLIC_SANITY_DATASET environment variable. Set it in your .env.local or project settings.')
}

export const sanityProjectId = projectId
export const sanityDataset = dataset
export const sanityApiVersion = process.env.SANITY_API_VERSION || '2024-10-01'
export const sanityUseCdn = process.env.SANITY_USE_CDN !== 'false'
export const sanityReadToken = process.env.SANITY_READ_TOKEN
