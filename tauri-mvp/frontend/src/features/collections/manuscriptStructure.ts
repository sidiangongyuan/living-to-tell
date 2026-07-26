import type {
  Collection,
  CollectionArticle,
  CollectionProjectType,
  CollectionOutlineItem,
  OutlineItemType,
} from '../../api/collections'

export interface ManuscriptTreeNode {
  item: CollectionOutlineItem
  children: ManuscriptTreeNode[]
  depth: number
  path: number[]
}

export interface TypeLabels {
  part: string
  chapter: string
  scene: string
  note: string
}

export interface StructureIssue {
  itemId: string
  kind: 'duplicate_article' | 'linked_container' | 'invalid_parent' | 'children_on_leaf'
  entryId?: string
}

const ZH_TYPE_LABELS: Record<CollectionProjectType, TypeLabels> = {
  general: { part: '分组', chapter: '章节', scene: '文章', note: '笔记' },
  novel: { part: '分部', chapter: '章节', scene: '场景', note: '笔记' },
  essay: { part: '辑', chapter: '章节', scene: '文章', note: '笔记' },
  nonfiction: { part: '部分', chapter: '章节', scene: '小节', note: '笔记' },
}

const EN_TYPE_LABELS: Record<CollectionProjectType, TypeLabels> = {
  general: { part: 'Group', chapter: 'Chapter', scene: 'Article', note: 'Note' },
  novel: { part: 'Part', chapter: 'Chapter', scene: 'Scene', note: 'Note' },
  essay: { part: 'Section', chapter: 'Chapter', scene: 'Article', note: 'Note' },
  nonfiction: { part: 'Part', chapter: 'Chapter', scene: 'Section', note: 'Note' },
}

export function normalizeProjectType(value: string | null | undefined): CollectionProjectType {
  if (value === 'novel' || value === 'essay' || value === 'nonfiction') return value
  return 'general'
}

export function projectTypeLabel(type: CollectionProjectType, locale: string): string {
  const zh = locale !== 'en'
  if (zh) {
    if (type === 'novel') return '小说'
    if (type === 'essay') return '散文集 / 文集'
    if (type === 'nonfiction') return '非虚构'
    return '通用'
  }
  if (type === 'novel') return 'Novel'
  if (type === 'essay') return 'Essay Collection'
  if (type === 'nonfiction') return 'Nonfiction'
  return 'General'
}

export function labelsForProject(type: CollectionProjectType, locale: string): TypeLabels {
  return locale === 'en' ? EN_TYPE_LABELS[type] : ZH_TYPE_LABELS[type]
}

export function typeLabelForProject(
  itemType: OutlineItemType,
  projectType: CollectionProjectType,
  locale: string,
): string {
  return labelsForProject(projectType, locale)[itemType]
}

export function structureTabLabel(locale: string): string {
  return locale === 'en' ? 'Manuscript' : '书稿'
}

export function boardTabLabel(locale: string): string {
  return locale === 'en' ? 'Board' : '看板'
}

export function exportTabLabel(locale: string): string {
  return locale === 'en' ? 'Export' : '导出'
}

export function defaultChildType(parentType: OutlineItemType | null, projectType: CollectionProjectType): OutlineItemType {
  if (!parentType) return 'chapter'
  if (parentType === 'part') return 'chapter'
  if (parentType === 'chapter') return projectType === 'novel' || projectType === 'nonfiction' ? 'scene' : 'scene'
  return 'note'
}

export function articleTypeForProject(_projectType: CollectionProjectType): OutlineItemType {
  return 'scene'
}

export function displayTitleForItem(item: CollectionOutlineItem): string {
  return item.display_title || item.title
}

export function allowedChildTypes(parentType: OutlineItemType | null): OutlineItemType[] {
  if (parentType === null) return ['part', 'chapter']
  if (parentType === 'part') return ['chapter', 'note']
  if (parentType === 'chapter') return ['scene', 'note']
  return []
}

export function canLinkArticle(
  item: Pick<CollectionOutlineItem, 'item_type' | 'id'>,
  outline: CollectionOutlineItem[],
): boolean {
  if (item.item_type === 'part' || item.item_type === 'note') return false
  if (item.item_type === 'scene') return true
  return !outline.some((candidate) => candidate.parent_id === item.id)
}

export function canUseStructureParent(
  outline: CollectionOutlineItem[],
  item: Pick<CollectionOutlineItem, 'id' | 'item_type'>,
  parentId: string | null,
): boolean {
  if (!canUseParent(outline, item.id, parentId)) return false
  const parent = parentId
    ? outline.find((candidate) => candidate.id === parentId) ?? null
    : null
  return allowedChildTypes(parent?.item_type ?? null).includes(item.item_type)
    && !parent?.entry_id
}

export function descendantArticleProgress(
  itemId: string,
  outline: CollectionOutlineItem[],
): { total: number; done: number } {
  const children = new Map<string, CollectionOutlineItem[]>()
  for (const item of outline) {
    if (!item.parent_id) continue
    children.set(item.parent_id, [...(children.get(item.parent_id) ?? []), item])
  }
  let total = 0
  let done = 0
  const visit = (parentId: string) => {
    for (const child of children.get(parentId) ?? []) {
      if (child.entry_id) {
        total += 1
        if (child.status === 'done') done += 1
      }
      visit(child.id)
    }
  }
  visit(itemId)
  return { total, done }
}

export function findStructureIssues(outline: CollectionOutlineItem[]): StructureIssue[] {
  const issues: StructureIssue[] = []
  const byId = new Map(outline.map((item) => [item.id, item]))
  const children = new Map<string, CollectionOutlineItem[]>()
  const entryLocations = new Map<string, string[]>()
  for (const item of outline) {
    if (item.parent_id) {
      children.set(item.parent_id, [...(children.get(item.parent_id) ?? []), item])
    }
    if (item.entry_id) {
      entryLocations.set(item.entry_id, [...(entryLocations.get(item.entry_id) ?? []), item.id])
    }
  }

  for (const item of outline) {
    const parent = item.parent_id ? byId.get(item.parent_id) ?? null : null
    if (
      !allowedChildTypes(parent?.item_type ?? null).includes(item.item_type)
      || (item.parent_id && !parent)
    ) {
      issues.push({ itemId: item.id, kind: 'invalid_parent' })
    }
    const itemChildren = children.get(item.id) ?? []
    if (itemChildren.length && ['scene', 'note'].includes(item.item_type)) {
      issues.push({ itemId: item.id, kind: 'children_on_leaf' })
    }
    if (
      item.entry_id
      && (itemChildren.length > 0 || item.item_type === 'part' || item.item_type === 'note')
    ) {
      issues.push({ itemId: item.id, kind: 'linked_container' })
    }
  }
  for (const [entryId, itemIds] of entryLocations) {
    if (itemIds.length < 2) continue
    for (const itemId of itemIds) {
      issues.push({ itemId, kind: 'duplicate_article', entryId })
    }
  }
  return issues
}

export function buildManuscriptTree(outline: CollectionOutlineItem[]): ManuscriptTreeNode[] {
  const sorted = [...outline].sort(compareOutlineItems)
  const byParent = new Map<string | null, CollectionOutlineItem[]>()
  const byId = new Set(sorted.map((item) => item.id))
  for (const item of sorted) {
    const parentId = item.parent_id && byId.has(item.parent_id) ? item.parent_id : null
    const rows = byParent.get(parentId) ?? []
    rows.push(item)
    byParent.set(parentId, rows)
  }

  const seen = new Set<string>()
  const visit = (parentId: string | null, depth: number, prefix: number[]): ManuscriptTreeNode[] => {
    const children = byParent.get(parentId) ?? []
    return children
      .filter((item) => !seen.has(item.id))
      .map((item, index) => {
        seen.add(item.id)
        const path = [...prefix, index + 1]
        return {
          item,
          depth,
          path,
          children: visit(item.id, depth + 1, path),
        }
      })
  }

  const roots = visit(null, 0, [])
  for (const item of sorted) {
    if (!seen.has(item.id)) {
      seen.add(item.id)
      roots.push({
        item,
        depth: 0,
        path: [roots.length + 1],
        children: visit(item.id, 1, [roots.length + 1]),
      })
    }
  }
  return roots
}

export function flattenManuscriptTree(nodes: ManuscriptTreeNode[]): ManuscriptTreeNode[] {
  const result: ManuscriptTreeNode[] = []
  const visit = (items: ManuscriptTreeNode[]) => {
    for (const item of items) {
      result.push(item)
      visit(item.children)
    }
  }
  visit(nodes)
  return result
}

export function linkedArticleIds(outline: CollectionOutlineItem[]): Set<string> {
  return new Set(outline.map((item) => item.entry_id).filter((id): id is string => Boolean(id)))
}

export function unplannedArticles(
  articles: CollectionArticle[],
  outline: CollectionOutlineItem[],
): CollectionArticle[] {
  const linked = linkedArticleIds(outline)
  return articles.filter((article) => !linked.has(article.id))
}

export function articleTitleForId(
  entryId: string | null | undefined,
  articles: Pick<CollectionArticle, 'id' | 'title'>[],
): string {
  if (!entryId) return ''
  return articles.find((article) => article.id === entryId)?.title || entryId
}

export function canUseParent(
  outline: CollectionOutlineItem[],
  itemId: string,
  parentId: string | null,
): boolean {
  if (!parentId) return true
  if (itemId === parentId) return false
  let current = outline.find((item) => item.id === parentId) ?? null
  const seen = new Set<string>()
  while (current?.parent_id) {
    if (current.parent_id === itemId) return false
    if (seen.has(current.parent_id)) return false
    seen.add(current.parent_id)
    current = outline.find((item) => item.id === current?.parent_id) ?? null
  }
  return true
}

export function collectionProjectType(collection: Pick<Collection, 'project_type'> | null): CollectionProjectType {
  return normalizeProjectType(collection?.project_type)
}

function compareOutlineItems(a: CollectionOutlineItem, b: CollectionOutlineItem): number {
  if (a.sort_order !== b.sort_order) return a.sort_order - b.sort_order
  return (a.created_at || '').localeCompare(b.created_at || '') || a.id.localeCompare(b.id)
}
