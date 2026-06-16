import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { libraryApi, type Reference } from '../../api/library'
import {
  type LibraryGroupMode,
  type ReferenceGroup,
  getReferenceSourceGroupKey,
  getReferenceUsageGroupKey,
  groupReferencesBySource,
  groupReferencesByUsage,
  normalizeLibraryGroupMode,
  readStoredLibraryGroupMode,
  writeStoredLibraryGroupMode,
} from './grouping'

export const useLibraryStore = defineStore('library', () => {
  const references = ref<Reference[]>([])
  const selectedRefId = ref<string | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const searchQuery = ref('')
  const groupMode = ref<LibraryGroupMode>(
    readStoredLibraryGroupMode(typeof window !== 'undefined' ? window.localStorage : null),
  )
  const activeSourceGroupKey = ref<string | null>(null)
  const activeUsageGroupKey = ref<string | null>(null)

  const selectedReference = computed(() =>
    references.value.find((r) => r.id === selectedRefId.value) ?? null
  )
  const sourceGroups = computed<ReferenceGroup[]>(() => groupReferencesBySource(references.value))
  const usageGroups = computed<ReferenceGroup[]>(() => groupReferencesByUsage(references.value))
  const activeSourceGroup = computed(() =>
    sourceGroups.value.find((group) => group.key === activeSourceGroupKey.value)
    ?? sourceGroups.value[0]
    ?? null
  )
  const activeUsageGroup = computed(() =>
    usageGroups.value.find((group) => group.key === activeUsageGroupKey.value)
    ?? usageGroups.value[0]
    ?? null
  )
  const visibleReferences = computed(() =>
    groupMode.value === 'usage'
      ? activeUsageGroup.value?.references ?? []
      : activeSourceGroup.value?.references ?? []
  )

  function setReferences(nextReferences: Reference[]) {
    references.value = nextReferences
    ensureSelection()
  }

  function ensureSelection() {
    if (selectedRefId.value && references.value.some((reference) => reference.id === selectedRefId.value)) {
      syncActiveGroups(selectedRefId.value)
      return
    }

    const firstReference = references.value[0] ?? null
    if (!firstReference) {
      selectedRefId.value = null
      activeSourceGroupKey.value = null
      activeUsageGroupKey.value = null
      return
    }

    selectedRefId.value = firstReference.id
    syncActiveGroups(firstReference.id)
  }

  function syncActiveGroups(referenceId: string | null = selectedRefId.value) {
    const reference = referenceId
      ? references.value.find((item) => item.id === referenceId) ?? null
      : null

    if (reference) {
      activeSourceGroupKey.value = getReferenceSourceGroupKey(reference)
      activeUsageGroupKey.value = getReferenceUsageGroupKey(reference)
      return
    }

    activeSourceGroupKey.value = sourceGroups.value[0]?.key ?? null
    activeUsageGroupKey.value = usageGroups.value[0]?.key ?? null
  }

  function upsertReference(reference: Reference) {
    const index = references.value.findIndex((item) => item.id === reference.id)
    if (index === -1) {
      references.value = [reference, ...references.value]
      return
    }

    references.value = references.value.map((item, itemIndex) =>
      itemIndex === index ? reference : item
    )
  }

  async function loadReferences() {
    loading.value = true
    error.value = null
    try {
      const loadedReferences = await libraryApi.listReferences()
      setReferences(loadedReferences)
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  async function search(query: string) {
    searchQuery.value = query
    if (!query.trim()) {
      await loadReferences()
      return
    }
    loading.value = true
    try {
      const results = await libraryApi.searchReferences(query)
      setReferences(results)
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  async function createReference() {
    try {
      const created = await libraryApi.createReference({
        source_title: '',
        content: '新标本',
        source_author: '',
        tags: [],
      })
      references.value = [created, ...references.value]
      selectedRefId.value = created.id
      syncActiveGroups(created.id)
      return created
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      throw e
    }
  }

  async function updateReference(ref: Reference) {
    try {
      const updated = await libraryApi.updateReference(ref.id, {
        source_title: ref.source_title,
        content: ref.content,
        source_author: ref.source_author,
        tags: ref.tags,
        kind: ref.kind,
        usage_kind: ref.usage_kind,
        personal_note: ref.personal_note,
      })
      upsertReference(updated)
      syncActiveGroups(updated.id)
      return updated
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      throw e
    }
  }

  async function deleteReference(id: string) {
    try {
      await libraryApi.deleteReference(id)
      references.value = references.value.filter((r) => r.id !== id)
      if (selectedRefId.value === id) {
        selectedRefId.value = references.value[0]?.id ?? null
      }
      ensureSelection()
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      throw e
    }
  }

  function selectReference(id: string) {
    selectedRefId.value = id
    syncActiveGroups(id)
  }

  function selectSourceGroup(key: string) {
    activeSourceGroupKey.value = key
    const group = sourceGroups.value.find((item) => item.key === key)
    if (!group) return

    if (!group.references.some((reference) => reference.id === selectedRefId.value)) {
      selectReference(group.references[0].id)
    }
  }

  function selectUsageGroup(key: string) {
    activeUsageGroupKey.value = key
    const group = usageGroups.value.find((item) => item.key === key)
    if (!group) return

    if (!group.references.some((reference) => reference.id === selectedRefId.value)) {
      selectReference(group.references[0].id)
    }
  }

  function setGroupMode(mode: LibraryGroupMode | string) {
    groupMode.value = normalizeLibraryGroupMode(mode)
    writeStoredLibraryGroupMode(
      groupMode.value,
      typeof window !== 'undefined' ? window.localStorage : null,
    )
    syncActiveGroups()
  }

  async function ensureReferenceLoaded(id: string) {
    const existing = references.value.find((reference) => reference.id === id)
    if (existing) {
      return existing
    }

    const reference = await libraryApi.getReference(id)
    upsertReference(reference)
    return reference
  }

  async function selectReferenceFromDeepLink(id: string, mode?: LibraryGroupMode | null) {
    const reference = await ensureReferenceLoaded(id)

    if (mode) {
      setGroupMode(mode)
    }

    selectReference(reference.id)
    return reference
  }

  watch(sourceGroups, (groups) => {
    if (!groups.length) {
      activeSourceGroupKey.value = null
      return
    }

    if (!groups.some((group) => group.key === activeSourceGroupKey.value)) {
      activeSourceGroupKey.value = groups[0].key
    }
  })

  watch(usageGroups, (groups) => {
    if (!groups.length) {
      activeUsageGroupKey.value = null
      return
    }

    if (!groups.some((group) => group.key === activeUsageGroupKey.value)) {
      activeUsageGroupKey.value = groups[0].key
    }
  })

  watch(
    () => [
      selectedReference.value?.id ?? null,
      selectedReference.value?.source_title ?? null,
      selectedReference.value?.usage_kind ?? null,
    ],
    () => {
      syncActiveGroups()
    }
  )

  return {
    references,
    selectedRefId,
    selectedReference,
    loading,
    error,
    searchQuery,
    groupMode,
    activeSourceGroupKey,
    activeUsageGroupKey,
    sourceGroups,
    usageGroups,
    activeSourceGroup,
    activeUsageGroup,
    visibleReferences,
    loadReferences,
    search,
    createReference,
    updateReference,
    deleteReference,
    selectReference,
    selectSourceGroup,
    selectUsageGroup,
    setGroupMode,
    ensureReferenceLoaded,
    selectReferenceFromDeepLink,
  }
})
