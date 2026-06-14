import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { libraryApi, type Reference } from '../../api/library'

export const useLibraryStore = defineStore('library', () => {
  const references = ref<Reference[]>([])
  const selectedRefId = ref<string | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const searchQuery = ref('')

  const selectedReference = computed(() =>
    references.value.find((r) => r.id === selectedRefId.value) ?? null
  )

  async function loadReferences() {
    loading.value = true
    error.value = null
    try {
      references.value = await libraryApi.listReferences()
      if (references.value.length && !selectedRefId.value) {
        selectedRefId.value = references.value[0].id
      }
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
      references.value = await libraryApi.searchReferences(query)
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
      references.value.unshift(created)
      selectedRefId.value = created.id
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
      const idx = references.value.findIndex((r) => r.id === ref.id)
      if (idx !== -1) references.value[idx] = updated
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
        selectedRefId.value = references.value.length ? references.value[0].id : null
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      throw e
    }
  }

  function selectReference(id: string) {
    selectedRefId.value = id
  }

  return {
    references,
    selectedRefId,
    selectedReference,
    loading,
    error,
    searchQuery,
    loadReferences,
    search,
    createReference,
    updateReference,
    deleteReference,
    selectReference,
  }
})
