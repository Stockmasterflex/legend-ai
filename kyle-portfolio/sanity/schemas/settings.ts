import {defineField, defineType} from 'sanity'

export default defineType({
  name: 'settings',
  title: 'Site Settings',
  type: 'document',
  fields: [
    defineField({ name: 'siteTitle', type: 'string' }),
    defineField({ name: 'description', type: 'text' }),
    defineField({ name: 'heroImage', type: 'image', options: { hotspot: true } }),
  ],
})
