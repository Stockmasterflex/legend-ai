export const allPostsQuery = `
*[_type == "post" && !draft] | order(date desc) {
  _id,
  "slug": slug.current,
  title,
  description,
  date,
  cover,
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
  body[] {
    ...,
    _type == "image" => {
      ...,
      "alt": coalesce(alt, asset->altText)
    }
  }
}`
