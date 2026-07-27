import { describe, expect, it } from 'vitest'
import type { CollectionArticle, CollectionOutlineItem } from '../../api/collections'
import {
  allowedChildTypes,
  buildManuscriptTree,
  canLinkArticle,
  canUseParent,
  descendantArticleProgress,
  findStructureIssues,
  flattenManuscriptTree,
  labelsForProject,
  unplannedArticles,
} from './manuscriptStructure'

function outlineItem(partial: Partial<CollectionOutlineItem>): CollectionOutlineItem {
  return {
    id: partial.id ?? 'item',
    collection_id: 'collection-1',
    parent_id: null,
    entry_id: null,
    title: '条目',
    display_title: partial.display_title ?? partial.title ?? '条目',
    item_type: 'scene',
    status: 'idea',
    summary: '',
    notes: '',
    pov: '',
    setting: '',
    timeline: '',
    tags: [],
    target_word_count: null,
    sort_order: 0,
    board_sort_order: 0,
    created_at: null,
    updated_at: null,
    ...partial,
  }
}

describe('manuscript structure helpers', () => {
  it('builds a nested tree from outline parent links', () => {
    const tree = buildManuscriptTree([
      outlineItem({ id: 'part', title: '第一辑', item_type: 'part', sort_order: 0 }),
      outlineItem({ id: 'chapter', parent_id: 'part', title: '人生哲思', item_type: 'chapter', sort_order: 1 }),
      outlineItem({ id: 'essay-a', parent_id: 'chapter', title: '奴隶道德', item_type: 'scene', sort_order: 2 }),
    ])

    expect(tree).toHaveLength(1)
    expect(tree[0].children[0].children[0].item.id).toBe('essay-a')
    expect(flattenManuscriptTree(tree).map((node) => node.item.id)).toEqual(['part', 'chapter', 'essay-a'])
  })

  it('returns project-aware labels', () => {
    expect(labelsForProject('novel', 'zh').part).toBe('分部')
    expect(labelsForProject('essay', 'zh').chapter).toBe('章节')
    expect(labelsForProject('essay', 'zh').scene).toBe('文章')
    expect(labelsForProject('nonfiction', 'en').scene).toBe('Section')
  })

  it('finds articles that have not been placed into the structure', () => {
    const articles: CollectionArticle[] = [
      { id: 'a', title: 'A', body: '', body_preview: '', tags: [], word_count: 0, char_count: 0, sort_order: 0, created_at: null, updated_at: null },
      { id: 'b', title: 'B', body: '', body_preview: '', tags: [], word_count: 0, char_count: 0, sort_order: 1, created_at: null, updated_at: null },
    ]
    const outline = [outlineItem({ id: 'item-a', entry_id: 'a' })]

    expect(unplannedArticles(articles, outline).map((article) => article.id)).toEqual(['b'])
  })

  it('prevents parent cycles', () => {
    const outline = [
      outlineItem({ id: 'parent' }),
      outlineItem({ id: 'child', parent_id: 'parent' }),
    ]

    expect(canUseParent(outline, 'parent', 'child')).toBe(false)
    expect(canUseParent(outline, 'child', 'parent')).toBe(true)
  })

  it('defines strict container and body-leaf roles', () => {
    expect(allowedChildTypes(null)).toEqual(['part', 'chapter'])
    expect(allowedChildTypes('part')).toEqual(['chapter', 'note'])
    expect(allowedChildTypes('chapter')).toEqual(['scene', 'note'])
    expect(allowedChildTypes('scene')).toEqual([])

    const chapter = outlineItem({ id: 'chapter', item_type: 'chapter' })
    const body = outlineItem({ id: 'body', parent_id: 'chapter', entry_id: 'article-1' })
    const outline = [chapter, body]
    expect(canLinkArticle(chapter, outline)).toBe(false)
    expect(canLinkArticle(body, outline)).toBe(true)
    expect(descendantArticleProgress('chapter', outline)).toEqual({ total: 1, done: 0 })
  })

  it('flags ambiguous legacy conflicts without mutating them', () => {
    const outline = [
      outlineItem({ id: 'legacy', item_type: 'scene', entry_id: 'article-1' }),
      outlineItem({ id: 'child', parent_id: 'legacy', item_type: 'note' }),
      outlineItem({ id: 'duplicate', item_type: 'chapter', entry_id: 'article-1' }),
    ]

    const issues = findStructureIssues(outline)
    expect(issues.some((issue) => issue.itemId === 'legacy' && issue.kind === 'children_on_leaf')).toBe(true)
    expect(issues.filter((issue) => issue.kind === 'duplicate_article')).toHaveLength(2)
    expect(outline[0].item_type).toBe('scene')
  })
})
