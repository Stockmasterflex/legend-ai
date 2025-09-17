import {defineField, defineType} from 'sanity'

export default defineType({
  name: 'post',
  title: 'Post',
  type: 'document',
  fields: [
    defineField({ name: 'title', type: 'string', validation: (rule) => rule.required() }),
    defineField({
      name: 'slug',
      type: 'slug',
      options: { source: 'title', maxLength: 96 },
      validation: (rule) => rule.required(),
    }),
    defineField({ name: 'description', type: 'text' }),
    defineField({ name: 'cover', title: 'Cover Image', type: 'image', options: { hotspot: true } }),
    defineField({ name: 'author', type: 'reference', to: [{ type: 'author' }] }),
    defineField({ name: 'tags', type: 'array', of: [{ type: 'reference', to: [{ type: 'tag' }] }] }),
    defineField({ name: 'date', type: 'datetime', initialValue: () => new Date().toISOString() }),
    defineField({ name: 'draft', type: 'boolean', initialValue: false }),
    defineField({
      name: 'body',
      type: 'array',
      of: [
        { type: 'block' },
        {
          type: 'image',
          options: { hotspot: true },
          fields: [
            defineField({ name: 'alt', title: 'Alt text', type: 'string' }),
          ],
        },
      ],
    }),
  ],
  preview: {
    select: {
      title: 'title',
      media: 'cover',
      subtitle: 'author.name',
    },
  },
})
