import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { articlesApi, type Entry } from '../../api/articles'
import { errorMessage } from '../../api/base'

export const useArticlesStore = defineStore('articles', () => {
  const entries = ref<Entry[]>([])
  const selectedId = ref<string | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const searchQuery = ref('')
  const searchResults = ref<Entry[]>([])
  const saving = ref(false)

  const selectedEntry = computed(() =>
    entries.value.find((e) => e.id === selectedId.value) ?? null
  )

  async function loadEntries() {
    loading.value = true
    error.value = null
    try {
      entries.value = await articlesApi.list()
      const selectedStillExists = Boolean(
        selectedId.value && entries.value.some((entry) => entry.id === selectedId.value)
      )
      if (entries.value.length && !selectedStillExists) {
        selectedId.value = entries.value[0].id
      } else if (!entries.value.length) {
        selectedId.value = null
      }
    } catch (e) {
      error.value = errorMessage(e)
    } finally {
      loading.value = false
    }
  }

  async function search(query: string) {
    if (!query.trim()) {
      searchResults.value = []
      return
    }
    searchQuery.value = query
    try {
      searchResults.value = await articlesApi.search(query)
    } catch (e) {
      error.value = errorMessage(e)
    }
  }

  async function createEntry(title = 'Untitled', body = '') {
    try {
      const created = await articlesApi.create({ title, body, tags: [] })
      entries.value.unshift(created)
      selectedId.value = created.id
      return created
    } catch (e) {
      error.value = errorMessage(e)
      throw e
    }
  }

  async function updateEntry(id: string, title: string, body: string, tags?: string[]) {
    saving.value = true
    try {
      const updated = await articlesApi.update(id, { title, body, tags })
      const idx = entries.value.findIndex((e) => e.id === id)
      if (idx !== -1) entries.value[idx] = updated
      return updated
    } catch (e) {
      error.value = errorMessage(e)
      throw e
    } finally {
      saving.value = false
    }
  }

  async function deleteEntry(id: string) {
    try {
      await articlesApi.delete(id)
      entries.value = entries.value.filter((e) => e.id !== id)
      if (selectedId.value === id) {
        selectedId.value = entries.value.length ? entries.value[0].id : null
      }
    } catch (e) {
      error.value = errorMessage(e)
      throw e
    }
  }

  async function archiveEntry(id: string) {
    try {
      const updated = await articlesApi.archive(id)
      const idx = entries.value.findIndex((e) => e.id === id)
      if (idx !== -1) entries.value[idx] = updated
    } catch (e) {
      error.value = errorMessage(e)
    }
  }

  function selectEntry(id: string) {
    selectedId.value = id
  }

  function replaceEntry(entry: Entry) {
    const idx = entries.value.findIndex((item) => item.id === entry.id)
    if (idx === -1) {
      entries.value.unshift(entry)
    } else {
      entries.value[idx] = entry
    }
    selectedId.value = entry.id
  }

  return {
    entries,
    selectedId,
    selectedEntry,
    loading,
    error,
    searchQuery,
    searchResults,
    saving,
    loadEntries,
    search,
    createEntry,
    updateEntry,
    deleteEntry,
    archiveEntry,
    selectEntry,
    replaceEntry,
  }
})
