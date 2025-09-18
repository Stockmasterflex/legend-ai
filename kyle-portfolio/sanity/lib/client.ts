import {createClient} from '@sanity/client'
import {
  sanityApiVersion,
  sanityDataset,
  sanityProjectId,
  sanityReadToken,
  sanityUseCdn,
} from '../env'

export const sanityClient = createClient({
  projectId: sanityProjectId,
  dataset: sanityDataset,
  apiVersion: sanityApiVersion,
  useCdn: sanityUseCdn && process.env.NODE_ENV === 'production',
  perspective: 'published',
  token: typeof window === 'undefined' ? sanityReadToken : undefined,
})
