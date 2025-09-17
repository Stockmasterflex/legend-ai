import imageUrlBuilder from '@sanity/image-url'
import type { Image } from 'sanity'
import { sanityClient } from './client'

const builder = imageUrlBuilder(sanityClient)

export const urlFor = (source: Image | any) => builder.image(source)
