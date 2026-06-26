import type { CollectionArticle, CollectionOutlineItem, OutlineItemStatus, OutlineItemType } from '../../api/collections'

export interface OutlineFilters {
  type: 'all' | OutlineItemType
  status: 'all' | OutlineItemStatus
  unlinkedOnly: boolean
}

export interface OutlineProgressSummary {
  totalItems: number
  linkedItems: number
  unlinkedItems: number
  targetWordTotal: number
  linkedArticleWordCount: number
  byStatus: Record<OutlineItemStatus, number>
}

const OUTLINE_STATUSES: OutlineItemStatus[] = ['idea', 'drafting', 'revising', 'done', 'parked']

export function buildOutlineProgressSummary(
  outline: CollectionOutlineItem[],
  articles: Pick<CollectionArticle, 'id' | 'word_count'>[],
): OutlineProgressSummary {
  const articleWords = new Map(articles.map((article) => [article.id, article.word_count]))
  const byStatus = Object.fromEntries(OUTLINE_STATUSES.map((status) => [status, 0])) as Record<OutlineItemStatus, number>
  const linkedIds = new Set<string>()

  let targetWordTotal = 0
  for (const item of outline) {
    byStatus[item.status] = (byStatus[item.status] ?? 0) + 1
    if (item.entry_id) linkedIds.add(item.entry_id)
    if (item.target_word_count && item.target_word_count > 0) {
      targetWordTotal += item.target_word_count
    }
  }

  let linkedArticleWordCount = 0
  for (const id of linkedIds) {
    linkedArticleWordCount += articleWords.get(id) ?? 0
  }

  return {
    totalItems: outline.length,
    linkedItems: outline.filter((item) => Boolean(item.entry_id)).length,
    unlinkedItems: outline.filter((item) => !item.entry_id).length,
    targetWordTotal,
    linkedArticleWordCount,
    byStatus,
  }
}

export function filterOutlineItems(
  outline: CollectionOutlineItem[],
  filters: OutlineFilters,
): CollectionOutlineItem[] {
  return outline.filter((item) => {
    if (filters.type !== 'all' && item.item_type !== filters.type) return false
    if (filters.status !== 'all' && item.status !== filters.status) return false
    if (filters.unlinkedOnly && item.entry_id) return false
    return true
  })
}

function joinInline(values: string[]): string {
  return values.map((value) => value.trim()).filter(Boolean).join(' / ')
}

export function buildOutlineMarkdown(options: {
  collectionTitle: string
  collectionDescription?: string
  outline: CollectionOutlineItem[]
  typeLabel: (value: OutlineItemType) => string
  statusLabel: (value: OutlineItemStatus) => string
  articleTitleForId?: (entryId: string) => string
}): string {
  const lines: string[] = []
  const title = options.collectionTitle.trim() || '作品集大纲'
  lines.push(`# ${title}`)
  if (options.collectionDescription?.trim()) {
    lines.push('', options.collectionDescription.trim())
  }
  lines.push('', '## 大纲')

  for (const [index, item] of options.outline.entries()) {
    const headerParts = [
      options.typeLabel(item.item_type),
      options.statusLabel(item.status),
      item.target_word_count ? `目标 ${item.target_word_count} 字` : '',
    ]
    lines.push('', `### ${index + 1}. ${item.title || '未命名大纲'}`)
    lines.push(`- 状态：${joinInline(headerParts) || '未设置'}`)
    if (item.entry_id) {
      const articleTitle = options.articleTitleForId?.(item.entry_id) || item.entry_id
      lines.push(`- 关联文章：${articleTitle}`)
    }
    if (item.summary.trim()) lines.push(`- 摘要：${item.summary.trim()}`)
    const context = joinInline([
      item.pov ? `POV：${item.pov}` : '',
      item.timeline ? `时间：${item.timeline}` : '',
      item.setting ? `地点：${item.setting}` : '',
    ])
    if (context) lines.push(`- 场景信息：${context}`)
    if (item.tags.length) lines.push(`- 标签：${item.tags.join('、')}`)
    if (item.notes.trim()) {
      lines.push('', item.notes.trim())
    }
  }

  if (!options.outline.length) {
    lines.push('', '暂无大纲条目。')
  }

  return `${lines.join('\n')}\n`
}
