export const allPostsQuery = `
*[_type == "post" && defined(slug.current) && !(_id in path("drafts.**"))] | order(date desc) {
  _id,
  "slug": slug.current,
  title,
  description,
  date,
  cover,
  "coverAlt": cover.alt,
  "tags": tags[]-> {title, "slug": slug.current}
}`

export const postBySlugQuery = `
*[_type == "post" && slug.current == $slug][0] {
  _id,
  "slug": slug.current,
  title,
  description,
  date,
  cover,
  "coverAlt": cover.alt,
  author-> {
    name,
    avatar
  },
  "tags": tags[]-> {title, "slug": slug.current},
  seo {
    title,
    description,
    ogImage
  },
  body[] {
    ...,
    _type == "image" => {
      ...,
      "alt": coalesce(alt, asset->altText),
      caption
    },
    _type == "chart" => {
      ...,
      "asset": {
        "url": asset->url
      },
      "title": coalesce(title, asset->originalFilename)
    }
  }
}`
