'use client'

import Giscus, { GiscusProps } from '@giscus/react'

const repo = process.env.NEXT_PUBLIC_GISCUS_REPO
const repoId = process.env.NEXT_PUBLIC_GISCUS_REPO_ID
const category = process.env.NEXT_PUBLIC_GISCUS_CATEGORY
const categoryId = process.env.NEXT_PUBLIC_GISCUS_CATEGORY_ID

const isConfigured = repo && repoId && category && categoryId

export default function GiscusComments(props: Partial<GiscusProps> = {}) {
  if (!isConfigured) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/70 px-4 py-3 text-sm text-slate-400">
        Comments are disabled. Add Giscus environment variables to enable discussion.
      </div>
    )
  }

  return (
    <Giscus
      repo={repo as `${string}/${string}`}
      repoId={repoId!}
      category={category!}
      categoryId={categoryId!}
      mapping="pathname"
      reactionsEnabled="1"
      emitMetadata="0"
      inputPosition="bottom"
      theme="dark"
      lang="en"
      loading="lazy"
      {...props}
    />
  )
}
