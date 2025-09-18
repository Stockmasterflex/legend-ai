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
    defineField({
      name: 'description',
      title: 'Summary',
      type: 'text',
      rows: 3,
      validation: (rule) => rule.max(280).warning('Keep the summary under 280 characters for social previews.'),
    }),
    defineField({
      name: 'cover',
      title: 'Cover Image',
      type: 'image',
      options: { hotspot: true },
      fields: [
        defineField({ name: 'alt', title: 'Alt text', type: 'string', validation: (rule) => rule.required() }),
      ],
    }),
    defineField({
      name: 'author',
      type: 'reference',
      to: [{ type: 'author' }],
      validation: (rule) => rule.required(),
    }),
    defineField({
      name: 'tags',
      type: 'array',
      of: [{ type: 'reference', to: [{ type: 'tag' }] }],
      options: { layout: 'tags' },
    }),
    defineField({ name: 'date', type: 'datetime', initialValue: () => new Date().toISOString() }),
    defineField({ name: 'draft', type: 'boolean', initialValue: false }),
    defineField({
      name: 'body',
      type: 'array',
      of: [
        { type: 'block' },
        defineField({
          type: 'image',
          title: 'Image',
          options: { hotspot: true },
          fields: [
            defineField({ name: 'alt', title: 'Alt text', type: 'string', validation: (rule) => rule.required() }),
            defineField({ name: 'caption', type: 'string' }),
          ],
        }),
        defineField({
          name: 'chart',
          title: 'Chart or Attachment',
          type: 'file',
          options: { storeOriginalFilename: true },
          fields: [
            defineField({ name: 'title', title: 'Display name', type: 'string' }),
          ],
        }),
        defineField({
          type: 'code',
          title: 'Code Snippet',
          options: {
            withFilename: true,
          },
        }),
      ],
      validation: (rule) => rule.required().min(1),
    }),
    defineField({
      name: 'seo',
      title: 'SEO Overrides',
      type: 'object',
      fields: [
        defineField({ name: 'title', type: 'string' }),
        defineField({ name: 'description', type: 'text' }),
        defineField({ name: 'ogImage', type: 'image', options: { hotspot: true } }),
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
