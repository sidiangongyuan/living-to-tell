import { describe, expect, it } from 'vitest'
import type { CollectionArticle, CollectionOutlineItem } from '../../api/collections'
import { buildOutlineMarkdown, buildOutlineProgressSummary, filterOutlineItems } from './outlineEnhancements'

function outlineItem(partial: Partial<CollectionOutlineItem>): CollectionOutlineItem {
  return {
    id: partial.id ?? 'item',
    collection_id: 'collection-1',
    parent_id: null,
    entry_id: null,
    title: '条目',
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
    created_at: null,
    updated_at: null,
    ...partial,
  }
}

describe('outline enhancements', () => {
  it('summarizes progress from outline items and linked articles', () => {
    const outline = [
      outlineItem({ id: 'a', status: 'idea', entry_id: 'article-1', target_word_count: 1200 }),
      outlineItem({ id: 'b', status: 'done', entry_id: 'article-2', target_word_count: 800 }),
      outlineItem({ id: 'c', status: 'done', entry_id: 'article-1' }),
      outlineItem({ id: 'd', status: 'parked' }),
    ]
    const articles: Pick<CollectionArticle, 'id' | 'word_count'>[] = [
      { id: 'article-1', word_count: 500 },
      { id: 'article-2', word_count: 300 },
    ]

    const summary = buildOutlineProgressSummary(outline, articles)

    expect(summary.totalItems).toBe(4)
    expect(summary.linkedItems).toBe(3)
    expect(summary.unlinkedItems).toBe(1)
    expect(summary.targetWordTotal).toBe(2000)
    expect(summary.linkedArticleWordCount).toBe(800)
    expect(summary.byStatus.done).toBe(2)
  })

  it('filters outline items without mutating the original list', () => {
    const outline = [
      outlineItem({ id: 'scene', item_type: 'scene', status: 'drafting' }),
      outlineItem({ id: 'chapter', item_type: 'chapter', status: 'drafting', entry_id: 'article-1' }),
      outlineItem({ id: 'note', item_type: 'note', status: 'idea' }),
    ]

    const result = filterOutlineItems(outline, {
      type: 'all',
      status: 'drafting',
      unlinkedOnly: true,
    })

    expect(result.map((item) => item.id)).toEqual(['scene'])
    expect(outline).toHaveLength(3)
  })

  it('exports markdown for the currently visible outline', () => {
    const markdown = buildOutlineMarkdown({
      collectionTitle: '长篇计划',
      collectionDescription: '一个测试简介',
      outline: [
        outlineItem({
          title: '第一场',
          item_type: 'scene',
          status: 'drafting',
          entry_id: 'article-1',
          summary: '主人公返乡。',
          tags: ['返乡', '等待'],
          target_word_count: 1500,
        }),
      ],
      typeLabel: () => '场景',
      statusLabel: () => '草稿',
      articleTitleForId: () => '返乡章节',
    })

    expect(markdown).toContain('# 长篇计划')
    expect(markdown).toContain('## 大纲')
    expect(markdown).toContain('关联文章：返乡章节')
    expect(markdown).toContain('标签：返乡、等待')
  })
})
