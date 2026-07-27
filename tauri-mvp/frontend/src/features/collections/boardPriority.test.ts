import { describe, expect, it } from 'vitest'
import type { CollectionOutlineItem } from '../../api/collections'
import { boardItemsForStatus, moveOutlineBoardLocally } from './boardPriority'

function outlineItem(partial: Partial<CollectionOutlineItem>): CollectionOutlineItem {
  return {
    id: partial.id ?? 'outline',
    collection_id: partial.collection_id ?? 'collection-a',
    parent_id: partial.parent_id ?? null,
    entry_id: partial.entry_id ?? null,
    title: partial.title ?? '条目',
    display_title: partial.display_title ?? partial.title ?? '条目',
    item_type: partial.item_type ?? 'chapter',
    status: partial.status ?? 'idea',
    summary: partial.summary ?? '',
    notes: partial.notes ?? '',
    pov: partial.pov ?? '',
    setting: partial.setting ?? '',
    timeline: partial.timeline ?? '',
    tags: partial.tags ?? [],
    target_word_count: partial.target_word_count ?? null,
    sort_order: partial.sort_order ?? 0,
    board_sort_order: partial.board_sort_order ?? partial.sort_order ?? 0,
    created_at: partial.created_at ?? null,
    updated_at: partial.updated_at ?? null,
  }
}

describe('boardPriority helpers', () => {
  it('sorts board items by board_sort_order before manuscript sort_order', () => {
    const items = boardItemsForStatus([
      outlineItem({ id: 'a', status: 'idea', sort_order: 0, board_sort_order: 2 }),
      outlineItem({ id: 'b', status: 'idea', sort_order: 2, board_sort_order: 0 }),
      outlineItem({ id: 'c', status: 'idea', sort_order: 1, board_sort_order: 1 }),
    ], 'idea')

    expect(items.map((item) => item.id)).toEqual(['b', 'c', 'a'])
  })

  it('reorders within one status without changing manuscript sort_order', () => {
    const moved = moveOutlineBoardLocally([
      outlineItem({ id: 'a', status: 'drafting', sort_order: 0, board_sort_order: 0 }),
      outlineItem({ id: 'b', status: 'drafting', sort_order: 1, board_sort_order: 1 }),
      outlineItem({ id: 'c', status: 'drafting', sort_order: 2, board_sort_order: 2 }),
    ], 'a', 'drafting', 3)

    const byId = new Map(moved.map((item) => [item.id, item]))
    expect(byId.get('b')?.board_sort_order).toBe(0)
    expect(byId.get('c')?.board_sort_order).toBe(1)
    expect(byId.get('a')?.board_sort_order).toBe(2)
    expect(byId.get('a')?.sort_order).toBe(0)
  })

  it('moves one card across statuses and keeps the source column dense', () => {
    const moved = moveOutlineBoardLocally([
      outlineItem({ id: 'idea-a', status: 'idea', board_sort_order: 0 }),
      outlineItem({ id: 'idea-b', status: 'idea', board_sort_order: 1 }),
      outlineItem({ id: 'draft-a', status: 'drafting', board_sort_order: 0 }),
    ], 'idea-b', 'drafting', 1)

    const byId = new Map(moved.map((item) => [item.id, item]))
    expect(byId.get('idea-a')?.board_sort_order).toBe(0)
    expect(byId.get('idea-b')?.status).toBe('drafting')
    expect(byId.get('idea-b')?.board_sort_order).toBe(1)
    expect(byId.get('draft-a')?.board_sort_order).toBe(0)
  })
})
