import { describe, expect, it } from 'vitest'
import type { Entry } from '../../api/articles'
import { collectArticleTags, countParagraphs, filterArticlesByTag } from './articleList'

function entry(id: string, tags: string[]): Entry {
  return {
    id,
    title: id,
    body: '',
    entry_type: 'fragment',
    created_at: null,
    updated_at: null,
    tags,
    archived_at: null,
    curation_status: 'active',
  }
}

describe('article list helpers', () => {
  it('counts non-empty paragraphs instead of raw newline rows', () => {
    expect(countParagraphs('')).toBe(0)
    expect(countParagraphs('\n\n')).toBe(0)
    expect(countParagraphs('第一段\n\n第二段\n  \n第三段')).toBe(3)
  })

  it('collects sorted unique tags from articles', () => {
    expect(collectArticleTags([
      entry('a', ['散文', '草稿']),
      entry('b', ['草稿', '小说']),
    ])).toEqual(['草稿', '散文', '小说'].sort((a, b) => a.localeCompare(b)))
  })

  it('filters by one selected tag and leaves the list unchanged without a tag', () => {
    const entries = [
      entry('a', ['散文']),
      entry('b', ['小说']),
      entry('c', ['散文', '草稿']),
    ]

    expect(filterArticlesByTag(entries, '').map((item) => item.id)).toEqual(['a', 'b', 'c'])
    expect(filterArticlesByTag(entries, '散文').map((item) => item.id)).toEqual(['a', 'c'])
  })
})
