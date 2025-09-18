import {defineConfig} from 'sanity'
import {deskTool} from 'sanity/desk'
import {visionTool} from '@sanity/vision'

import post from './sanity/schemas/post'
import author from './sanity/schemas/author'
import tag from './sanity/schemas/tag'
import settings from './sanity/schemas/settings'
import { sanityDataset, sanityProjectId } from './sanity/env'

export default defineConfig({
  name: 'legendStudio',
  title: 'Legend AI Studio',
  projectId: sanityProjectId,
  dataset: sanityDataset,
  basePath: '/studio',
  plugins: [deskTool(), visionTool()],
  schema: {
    types: [post, author, tag, settings],
  },
})
