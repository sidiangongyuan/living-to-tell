import type { Reference } from '../../api/library'

export type LibraryGroupMode = 'source' | 'usage'

export interface ReferenceGroup {
  key: string
  count: number
  references: Reference[]
}

export const LIBRARY_GROUP_MODE_STORAGE_KEY = 'writer.library.group_mode'
export const EMPTY_SOURCE_GROUP_KEY = '__empty_source__'
export const USAGE_KIND_ORDER = ['style', 'imagery', 'structure', 'rhetoric', 'diction', 'reflection', 'setting', 'technique', 'other'] as const

export function normalizeLibraryGroupMode(value: string | null | undefined): LibraryGroupMode {
  return value === 'usage' ? 'usage' : 'source'
}

export function getReferenceSourceGroupKey(reference: Pick<Reference, 'source_title'>): string {
  const sourceTitle = reference.source_title.trim()
  return sourceTitle || EMPTY_SOURCE_GROUP_KEY
}

export function getReferenceUsageGroupKey(reference: Pick<Reference, 'usage_kind'>): string {
  return reference.usage_kind.trim() || 'other'
}

export function findReferenceGroupKey(reference: Reference, mode: LibraryGroupMode): string {
  return mode === 'usage'
    ? getReferenceUsageGroupKey(reference)
    : getReferenceSourceGroupKey(reference)
}

export function groupReferencesBySource(references: Reference[]): ReferenceGroup[] {
  const groups = new Map<string, ReferenceGroup>()

  references.forEach((reference) => {
    const key = getReferenceSourceGroupKey(reference)
    const existing = groups.get(key)
    if (existing) {
      existing.references.push(reference)
      existing.count += 1
      return
    }

    groups.set(key, {
      key,
      count: 1,
      references: [reference],
    })
  })

  return Array.from(groups.values()).sort((a, b) => {
    if (a.key === EMPTY_SOURCE_GROUP_KEY) return 1
    if (b.key === EMPTY_SOURCE_GROUP_KEY) return -1
    return a.key.localeCompare(b.key, 'zh-CN')
  })
}

export function groupReferencesByUsage(references: Reference[]): ReferenceGroup[] {
  const groups = new Map<string, ReferenceGroup>()

  references.forEach((reference) => {
    const key = getReferenceUsageGroupKey(reference)
    const existing = groups.get(key)
    if (existing) {
      existing.references.push(reference)
      existing.count += 1
      return
    }

    groups.set(key, {
      key,
      count: 1,
      references: [reference],
    })
  })

  return Array.from(groups.values()).sort((a, b) => {
    const aIndex = USAGE_KIND_ORDER.indexOf(a.key as (typeof USAGE_KIND_ORDER)[number])
    const bIndex = USAGE_KIND_ORDER.indexOf(b.key as (typeof USAGE_KIND_ORDER)[number])
    const normalizedAIndex = aIndex === -1 ? Number.MAX_SAFE_INTEGER : aIndex
    const normalizedBIndex = bIndex === -1 ? Number.MAX_SAFE_INTEGER : bIndex

    if (normalizedAIndex !== normalizedBIndex) {
      return normalizedAIndex - normalizedBIndex
    }

    return a.key.localeCompare(b.key)
  })
}

export function readStoredLibraryGroupMode(storage: Pick<Storage, 'getItem'> | null | undefined): LibraryGroupMode {
  return normalizeLibraryGroupMode(storage?.getItem(LIBRARY_GROUP_MODE_STORAGE_KEY))
}

export function writeStoredLibraryGroupMode(
  mode: LibraryGroupMode,
  storage: Pick<Storage, 'setItem'> | null | undefined,
) {
  storage?.setItem(LIBRARY_GROUP_MODE_STORAGE_KEY, mode)
}
