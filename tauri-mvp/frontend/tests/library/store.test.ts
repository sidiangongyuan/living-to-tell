import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import type { Reference } from '../../src/api/library'
import { libraryApi } from '../../src/api/library'
import { useLibraryStore } from '../../src/features/library/store'

function makeReference(overrides: Partial<Reference>): Reference {
  return {
    id: overrides.id ?? 'ref-1',
    source_title: overrides.source_title ?? 'Book',
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

describe('library store deep links', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('loads a missing reference and switches to the requested usage grouping', async () => {
    const targetReference = makeReference({
      id: 'target-ref',
      source_title: 'The Waves',
      usage_kind: 'imagery',
    })

    vi.spyOn(libraryApi, 'getReference').mockResolvedValue(targetReference)

    const store = useLibraryStore()
    store.references = [
      makeReference({ id: 'existing-ref', source_title: 'Collected Poems', usage_kind: 'style' }),
    ]
    store.selectReference('existing-ref')

    await store.selectReferenceFromDeepLink('target-ref', 'usage')

    expect(libraryApi.getReference).toHaveBeenCalledWith('target-ref')
    expect(store.groupMode).toBe('usage')
    expect(store.selectedRefId).toBe('target-ref')
    expect(store.activeUsageGroup?.key).toBe('imagery')
    expect(store.visibleReferences.map((reference) => reference.id)).toEqual(['target-ref'])
  })
})
