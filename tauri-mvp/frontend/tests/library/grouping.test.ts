import { describe, expect, it } from 'vitest'
import type { Reference } from '../../src/api/library'
import {
  EMPTY_SOURCE_GROUP_KEY,
  LIBRARY_GROUP_MODE_STORAGE_KEY,
  groupReferencesBySource,
  groupReferencesByUsage,
  normalizeLibraryGroupMode,
  readStoredLibraryGroupMode,
  writeStoredLibraryGroupMode,
} from '../../src/features/library/grouping'

function makeReference(overrides: Partial<Reference>): Reference {
  return {
    id: overrides.id ?? 'ref-1',
    source_title: overrides.source_title ?? '',
    content: overrides.content ?? 'content',
    source_author: overrides.source_author ?? '',
    tags: overrides.tags ?? [],
    kind: overrides.kind ?? 'excerpt',
    usage_kind: overrides.usage_kind ?? 'other',
    personal_note: overrides.personal_note ?? '',
    created_at: overrides.created_at ?? null,
    updated_at: overrides.updated_at ?? null,
  }
}

describe('library grouping helpers', () => {
  it('groups references by source title and keeps blank sources in the fallback bucket', () => {
    const groups = groupReferencesBySource([
      makeReference({ id: '1', source_title: 'Zeta' }),
      makeReference({ id: '2', source_title: 'Alpha' }),
      makeReference({ id: '3', source_title: 'Alpha' }),
      makeReference({ id: '4', source_title: '' }),
    ])

    expect(groups.map((group) => group.key)).toEqual(['Alpha', 'Zeta', EMPTY_SOURCE_GROUP_KEY])
    expect(groups[0].references.map((reference) => reference.id)).toEqual(['2', '3'])
    expect(groups[2].count).toBe(1)
  })

  it('groups references by usage using the configured usage order', () => {
    const groups = groupReferencesByUsage([
      makeReference({ id: '1', usage_kind: 'other' }),
      makeReference({ id: '2', usage_kind: 'diction' }),
      makeReference({ id: '3', usage_kind: 'style' }),
      makeReference({ id: '4', usage_kind: 'reflection' }),
    ])

    expect(groups.map((group) => group.key)).toEqual(['style', 'diction', 'reflection', 'other'])
  })

  it('normalizes and persists the organization mode', () => {
    const storage = new Map<string, string>()
    const mockStorage = {
      getItem: (key: string) => storage.get(key) ?? null,
      setItem: (key: string, value: string) => {
        storage.set(key, value)
      },
    }

    expect(normalizeLibraryGroupMode('usage')).toBe('usage')
    expect(normalizeLibraryGroupMode('unexpected')).toBe('source')
    expect(readStoredLibraryGroupMode(mockStorage)).toBe('source')

    writeStoredLibraryGroupMode('usage', mockStorage)

    expect(storage.get(LIBRARY_GROUP_MODE_STORAGE_KEY)).toBe('usage')
    expect(readStoredLibraryGroupMode(mockStorage)).toBe('usage')
  })
})
