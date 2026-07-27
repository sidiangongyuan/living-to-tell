import type { CollectionOutlineItem, OutlineItemStatus } from '../../api/collections'

export function compareBoardItems(a: CollectionOutlineItem, b: CollectionOutlineItem): number {
  if (a.board_sort_order !== b.board_sort_order) return a.board_sort_order - b.board_sort_order
  if (a.sort_order !== b.sort_order) return a.sort_order - b.sort_order
  return a.id.localeCompare(b.id)
}

export function boardItemsForStatus(
  outline: CollectionOutlineItem[],
  status: OutlineItemStatus,
): CollectionOutlineItem[] {
  return outline.filter((item) => item.status === status).slice().sort(compareBoardItems)
}

export function moveOutlineBoardLocally(
  outline: CollectionOutlineItem[],
  itemId: string,
  status: OutlineItemStatus,
  targetIndex: number,
): CollectionOutlineItem[] {
  const moving = outline.find((item) => item.id === itemId)
  if (!moving) return outline
  const sourceItems = boardItemsForStatus(outline, moving.status)
  const sourceIds = sourceItems.map((item) => item.id)
  const sourceIndex = sourceIds.indexOf(itemId)
  if (sourceIndex < 0) return outline

  const updates = new Map<string, Partial<CollectionOutlineItem>>()
  if (moving.status === status) {
    const rawTarget = clamp(targetIndex, 0, sourceIds.length)
    let adjustedTarget = rawTarget
    if (rawTarget > sourceIndex) adjustedTarget -= 1
    const reordered = sourceIds.filter((id) => id !== itemId)
    adjustedTarget = clamp(adjustedTarget, 0, reordered.length)
    reordered.splice(adjustedTarget, 0, itemId)
    reordered.forEach((id, index) => {
      updates.set(id, { board_sort_order: index })
    })
  } else {
    const destIds = boardItemsForStatus(outline, status).map((item) => item.id)
    const insertAt = clamp(targetIndex, 0, destIds.length)
    const reorderedSource = sourceIds.filter((id) => id !== itemId)
    const reorderedDest = [...destIds]
    reorderedDest.splice(insertAt, 0, itemId)
    reorderedSource.forEach((id, index) => {
      updates.set(id, { board_sort_order: index })
    })
    reorderedDest.forEach((id, index) => {
      updates.set(id, id === itemId
        ? { status, board_sort_order: index }
        : { board_sort_order: index })
    })
  }

  return outline.map((item) => {
    const patch = updates.get(item.id)
    return patch ? { ...item, ...patch } : item
  })
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}
