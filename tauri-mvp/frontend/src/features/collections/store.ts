import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  collectionsApi,
  type Collection,
  type CollectionArticle,
  type CollectionExportFormat,
} from '../../api/collections'

export const useCollectionsStore = defineStore('collections', () => {
  const collections = ref<Collection[]>([])
  const articles = ref<CollectionArticle[]>([])
  const selectedCollectionId = ref<string | null>(null)
  const selectedArticleId = ref<string | null>(null)
  const loading = ref(false)
  const articlesLoading = ref(false)
  const error = ref<string | null>(null)

  const selectedCollection = computed(() =>
    collections.value.find((c) => c.id === selectedCollectionId.value) ?? null
  )

  const selectedArticle = computed(() =>
    articles.value.find((a) => a.id === selectedArticleId.value) ?? null
  )

  const collectionWordCount = computed(() =>
    articles.value.reduce((total, article) => total + article.word_count, 0)
  )

  async function loadCollections() {
    loading.value = true
    error.value = null
    try {
      collections.value = await collectionsApi.listCollections()
      if (collections.value.length && !selectedCollectionId.value) {
        selectedCollectionId.value = collections.value[0].id
      }
      if (selectedCollectionId.value) {
        await loadArticles(selectedCollectionId.value)
      } else {
        articles.value = []
        selectedArticleId.value = null
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  async function loadArticles(collectionId = selectedCollectionId.value) {
    if (!collectionId) return
    articlesLoading.value = true
    error.value = null
    try {
      articles.value = await collectionsApi.listArticles(collectionId)
      if (!articles.value.some((article) => article.id === selectedArticleId.value)) {
        selectedArticleId.value = articles.value.length ? articles.value[0].id : null
      }
      const idx = collections.value.findIndex((collection) => collection.id === collectionId)
      if (idx !== -1) {
        collections.value[idx] = {
          ...collections.value[idx],
          article_count: articles.value.length,
        }
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      articlesLoading.value = false
    }
  }

  async function createCollection(title: string, description = '') {
    error.value = null
    try {
      const created = await collectionsApi.createCollection({ title, description })
      collections.value.unshift(created)
      selectedCollectionId.value = created.id
      articles.value = []
      selectedArticleId.value = null
      return created
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      throw e
    }
  }

  async function updateCollection(id: string, title: string, description: string) {
    error.value = null
    try {
      const updated = await collectionsApi.updateCollection(id, { title, description })
      const idx = collections.value.findIndex((c) => c.id === id)
      if (idx !== -1) collections.value[idx] = updated
      return updated
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      throw e
    }
  }

  async function deleteCollection(id: string) {
    error.value = null
    try {
      await collectionsApi.deleteCollection(id)
      collections.value = collections.value.filter((c) => c.id !== id)
      if (selectedCollectionId.value === id) {
        selectedCollectionId.value = collections.value.length ? collections.value[0].id : null
        if (selectedCollectionId.value) {
          await loadArticles(selectedCollectionId.value)
        } else {
          articles.value = []
          selectedArticleId.value = null
        }
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      throw e
    }
  }

  async function addArticles(entryIds: string[]) {
    if (!selectedCollectionId.value || !entryIds.length) return
    error.value = null
    try {
      articles.value = await collectionsApi.addArticles(selectedCollectionId.value, entryIds)
      selectedArticleId.value = entryIds.find((id) => articles.value.some((a) => a.id === id))
        ?? articles.value[0]?.id
        ?? null
      await refreshSelectedCollection()
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      throw e
    }
  }

  async function removeArticle(entryId: string) {
    if (!selectedCollectionId.value) return
    error.value = null
    try {
      await collectionsApi.removeArticle(selectedCollectionId.value, entryId)
      articles.value = articles.value.filter((article) => article.id !== entryId)
      if (selectedArticleId.value === entryId) {
        selectedArticleId.value = articles.value[0]?.id ?? null
      }
      await refreshSelectedCollection()
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      throw e
    }
  }

  async function moveArticle(entryId: string, direction: -1 | 1) {
    const index = articles.value.findIndex((article) => article.id === entryId)
    const nextIndex = index + direction
    if (!selectedCollectionId.value || index < 0 || nextIndex < 0 || nextIndex >= articles.value.length) {
      return
    }
    const reordered = [...articles.value]
    const [item] = reordered.splice(index, 1)
    reordered.splice(nextIndex, 0, item)
    await reorderArticles(reordered.map((article) => article.id))
  }

  async function reorderArticles(entryIds: string[]) {
    if (!selectedCollectionId.value) return
    error.value = null
    try {
      articles.value = await collectionsApi.reorderArticles(selectedCollectionId.value, entryIds)
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      throw e
    }
  }

  async function exportSelected(format: CollectionExportFormat) {
    if (!selectedCollectionId.value || !selectedCollection.value) return
    const blob = await collectionsApi.exportCollection(selectedCollectionId.value, format)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${selectedCollection.value.title || '作品集'}.${format}`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  async function refreshSelectedCollection() {
    if (!selectedCollectionId.value) return
    const updated = await collectionsApi.getCollection(selectedCollectionId.value)
    const idx = collections.value.findIndex((collection) => collection.id === updated.id)
    if (idx !== -1) collections.value[idx] = updated
  }

  async function selectCollection(id: string) {
    if (selectedCollectionId.value === id) return
    selectedCollectionId.value = id
    selectedArticleId.value = null
    await loadArticles(id)
  }

  function selectArticle(id: string) {
    selectedArticleId.value = id
  }

  return {
    collections,
    articles,
    selectedCollectionId,
    selectedArticleId,
    selectedCollection,
    selectedArticle,
    collectionWordCount,
    loading,
    articlesLoading,
    error,
    loadCollections,
    loadArticles,
    createCollection,
    updateCollection,
    deleteCollection,
    addArticles,
    removeArticle,
    moveArticle,
    reorderArticles,
    exportSelected,
    selectCollection,
    selectArticle,
  }
})
