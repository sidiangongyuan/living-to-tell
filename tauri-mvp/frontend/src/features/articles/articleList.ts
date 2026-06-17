import type { Entry } from '../../api/articles'

export function countParagraphs(body: string): number {
  return body.split(/\n+/).filter((paragraph) => paragraph.trim()).length
}

export function collectArticleTags(entries: Entry[]): string[] {
  return Array.from(new Set(entries.flatMap((entry) => entry.tags))).sort((a, b) => a.localeCompare(b))
}

export function filterArticlesByTag(entries: Entry[], selectedTag: string): Entry[] {
  if (!selectedTag) return entries
  return entries.filter((entry) => entry.tags.includes(selectedTag))
}
