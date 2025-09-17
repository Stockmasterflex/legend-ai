import {defineConfig} from 'sanity'
import {deskTool} from 'sanity/desk'
import {visionTool} from '@sanity/vision'

import post from './sanity/schemas/post'
import author from './sanity/schemas/author'
import tag from './sanity/schemas/tag'
import settings from './sanity/schemas/settings'

const projectId = process.env.NEXT_PUBLIC_SANITY_PROJECT_ID || 'demo'
const dataset = process.env.NEXT_PUBLIC_SANITY_DATASET || 'production'

export default defineConfig({
  name: 'legendStudio',
  title: 'Legend AI Studio',
  projectId,
  dataset,
  basePath: '/studio',
  plugins: [deskTool(), visionTool()],
  schema: {
    types: [post, author, tag, settings],
  },
})
