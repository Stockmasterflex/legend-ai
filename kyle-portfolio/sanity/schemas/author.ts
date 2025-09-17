import {defineField, defineType} from 'sanity'

export default defineType({
  name: 'author',
  title: 'Author',
  type: 'document',
  fields: [
    defineField({ name: 'name', type: 'string', validation: (rule) => rule.required() }),
    defineField({ name: 'avatar', type: 'image', options: { hotspot: true } }),
    defineField({ name: 'bio', type: 'text' }),
    defineField({ name: 'website', type: 'url' }),
  ],
  preview: {
    select: { title: 'name', media: 'avatar' },
  },
})
