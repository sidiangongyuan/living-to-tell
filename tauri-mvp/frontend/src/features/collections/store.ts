import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  collectionsApi,
  type Collection,
  type CollectionArticle,
  type CollectionExportFormat,
  type CollectionProjectType,
  type CollectionOutlineItem,
  type CollectionOutlineItemInput,
} from '../../api/collections'
import { isHttpStatus } from '../../api/base'
import { saveBlobWithDialog } from '../../utils/exportFile'

export const useCollectionsStore = defineStore('collections', () => {
  const collections = ref<Collection[]>([])
  const articles = ref<CollectionArticle[]>([])
  const outline = ref<CollectionOutlineItem[]>([])
  const selectedCollectionId = ref<string | null>(null)
  const selectedArticleId = ref<string | null>(null)
  const selectedOutlineItemId = ref<string | null>(null)
  const loading = ref(false)
  const articlesLoading = ref(false)
  const outlineLoading = ref(false)
  const error = ref<string | null>(null)
  const exportMessage = ref<string | null>(null)
  const exportingFormat = ref<CollectionExportFormat | null>(null)
  let collectionsLoadToken = 0
  let articlesLoadToken = 0
  let outlineLoadToken = 0

  function invalidateCollectionScopedLoads() {
    articlesLoadToken += 1
    outlineLoadToken += 1
    articlesLoading.value = false
    outlineLoading.value = false
  }

  function collectionErrorMessage(error: unknown, fallback: string): string {
    return isHttpStatus(error, 404) ? fallback : error instanceof Error ? error.message : String(error)
  }

  const selectedCollection = computed(() =>
    collections.value.find((c) => c.id === selectedCollectionId.value) ?? null
  )

  const selectedArticle = computed(() =>
    articles.value.find((a) => a.id === selectedArticleId.value) ?? null
  )

  const selectedOutlineItem = computed(() =>
    outline.value.find((item) => item.id === selectedOutlineItemId.value) ?? null
  )

  const collectionWordCount = computed(() =>
    articles.value.reduce((total, article) => total + article.word_count, 0)
  )

  async function loadCollections() {
    const token = ++collectionsLoadToken
    loading.value = true
    error.value = null
    try {
      const loadedCollections = await collectionsApi.listCollections()
      if (token !== collectionsLoadToken) return
      collections.value = loadedCollections
      const selectedStillExists = Boolean(
        selectedCollectionId.value
        && collections.value.some((collection) => collection.id === selectedCollectionId.value)
      )
      if (collections.value.length && !selectedStillExists) {
        invalidateCollectionScopedLoads()
        selectedCollectionId.value = collections.value[0].id
        selectedArticleId.value = null
        selectedOutlineItemId.value = null
      } else if (!collections.value.length) {
        invalidateCollectionScopedLoads()
        selectedCollectionId.value = null
      }
      if (selectedCollectionId.value) {
        await Promise.all([
          loadArticles(selectedCollectionId.value),
          loadOutline(selectedCollectionId.value),
        ])
      } else {
        invalidateCollectionScopedLoads()
        articles.value = []
        outline.value = []
        selectedArticleId.value = null
        selectedOutlineItemId.value = null
      }
    } catch (e) {
      if (token !== collectionsLoadToken) return
      error.value = collectionErrorMessage(e, '当前后台版本不支持书稿结构。请退出应用后安装最新版本。')
    } finally {
      if (token === collectionsLoadToken) loading.value = false
    }
  }

  async function loadArticles(collectionId = selectedCollectionId.value) {
    if (!collectionId) return
    const token = ++articlesLoadToken
    articlesLoading.value = true
    error.value = null
    try {
      const loadedArticles = await collectionsApi.listArticles(collectionId)
      if (token !== articlesLoadToken || selectedCollectionId.value !== collectionId) return
      articles.value = loadedArticles
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
      if (token !== articlesLoadToken || selectedCollectionId.value !== collectionId) return
      error.value = collectionErrorMessage(e, '当前作品集已不存在，请重新选择。')
    } finally {
      if (token === articlesLoadToken && selectedCollectionId.value === collectionId) {
        articlesLoading.value = false
      }
    }
  }

  async function loadOutline(collectionId = selectedCollectionId.value) {
    if (!collectionId) return
    const token = ++outlineLoadToken
    outlineLoading.value = true
    error.value = null
    try {
      const loadedOutline = await collectionsApi.listOutline(collectionId)
      if (token !== outlineLoadToken || selectedCollectionId.value !== collectionId) return
      outline.value = loadedOutline
      const selectedStillExists = Boolean(
        selectedOutlineItemId.value
        && outline.value.some((item) => item.id === selectedOutlineItemId.value)
      )
      if (outline.value.length && !selectedStillExists) {
        selectedOutlineItemId.value = outline.value[0].id
      } else if (!outline.value.length) {
        selectedOutlineItemId.value = null
      }
    } catch (e) {
      if (token !== outlineLoadToken || selectedCollectionId.value !== collectionId) return
      error.value = collectionErrorMessage(e, '当前作品集已不存在，请重新选择。')
    } finally {
      if (token === outlineLoadToken && selectedCollectionId.value === collectionId) {
        outlineLoading.value = false
      }
    }
  }

  async function createCollection(title: string, description = '', projectType: CollectionProjectType = 'general') {
    error.value = null
    try {
      const created = await collectionsApi.createCollection({ title, description, project_type: projectType })
      collections.value.unshift(created)
      invalidateCollectionScopedLoads()
      selectedCollectionId.value = created.id
      articles.value = []
      outline.value = []
      selectedArticleId.value = null
      selectedOutlineItemId.value = null
      return created
    } catch (e) {
      error.value = collectionErrorMessage(e, '当前后台版本不支持书稿结构。请退出应用后安装最新版本。')
      throw e
    }
  }

  async function updateCollection(
    id: string,
    title: string,
    description: string,
    projectType: CollectionProjectType = 'general',
  ) {
    error.value = null
    try {
      const updated = await collectionsApi.updateCollection(id, { title, description, project_type: projectType })
      const idx = collections.value.findIndex((c) => c.id === id)
      if (idx !== -1) collections.value[idx] = updated
      return updated
    } catch (e) {
      error.value = collectionErrorMessage(e, '这个结构节点已不存在，已刷新列表。')
      throw e
    }
  }

  async function deleteCollection(id: string) {
    error.value = null
    try {
      await collectionsApi.deleteCollection(id)
      collections.value = collections.value.filter((c) => c.id !== id)
      if (selectedCollectionId.value === id) {
        invalidateCollectionScopedLoads()
        selectedCollectionId.value = collections.value.length ? collections.value[0].id : null
        if (selectedCollectionId.value) {
          await Promise.all([
            loadArticles(selectedCollectionId.value),
            loadOutline(selectedCollectionId.value),
          ])
        } else {
          articles.value = []
          outline.value = []
          selectedArticleId.value = null
          selectedOutlineItemId.value = null
        }
      }
    } catch (e) {
      error.value = collectionErrorMessage(e, '这个结构节点已不存在，已刷新列表。')
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
      error.value = collectionErrorMessage(e, '当前后台版本不支持书稿结构。请退出应用后安装最新版本。')
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

  async function createOutlineItem(data: CollectionOutlineItemInput) {
    if (!selectedCollectionId.value) return null
    error.value = null
    try {
      const created = await collectionsApi.createOutlineItem(selectedCollectionId.value, data)
      outline.value = [...outline.value, created].sort((a, b) => a.sort_order - b.sort_order)
      selectedOutlineItemId.value = created.id
      await refreshSelectedCollection()
      return created
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      throw e
    }
  }

  async function updateOutlineItem(itemId: string, data: CollectionOutlineItemInput) {
    if (!selectedCollectionId.value) return null
    error.value = null
    try {
      const updated = await collectionsApi.updateOutlineItem(selectedCollectionId.value, itemId, data)
      const idx = outline.value.findIndex((item) => item.id === itemId)
      if (idx !== -1) outline.value[idx] = updated
      await refreshSelectedCollection()
      return updated
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      throw e
    }
  }

  async function deleteOutlineItem(itemId: string) {
    if (!selectedCollectionId.value) return
    error.value = null
    try {
      await collectionsApi.deleteOutlineItem(selectedCollectionId.value, itemId)
      outline.value = outline.value.filter((item) => item.id !== itemId)
      if (selectedOutlineItemId.value === itemId) {
        selectedOutlineItemId.value = outline.value[0]?.id ?? null
      }
      await refreshSelectedCollection()
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      throw e
    }
  }

  async function reorderOutline(itemIds: string[]) {
    if (!selectedCollectionId.value) return
    error.value = null
    try {
      outline.value = await collectionsApi.reorderOutline(selectedCollectionId.value, itemIds)
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      throw e
    }
  }

  async function exportSelected(format: CollectionExportFormat) {
    if (!selectedCollectionId.value || !selectedCollection.value) return
    error.value = null
    exportMessage.value = null
    exportingFormat.value = format
    try {
      const title = selectedCollection.value.title || '作品集'
      const safeTitle = title.replace(/[<>:"/\\|?*]/g, '').trim() || 'collection'
      const blob = await collectionsApi.exportCollection(selectedCollectionId.value, format)
      const result = await saveBlobWithDialog(blob, `${safeTitle}.${format}`, format)
      exportMessage.value = result.status === 'cancelled' ? '已取消导出。' : '已导出到文件。'
    } catch (e) {
      error.value = e instanceof Error ? `导出失败：${e.message}` : `导出失败：${String(e)}`
    } finally {
      exportingFormat.value = null
    }
  }

  async function refreshSelectedCollection() {
    if (!selectedCollectionId.value) return
    const updated = await collectionsApi.getCollection(selectedCollectionId.value)
    const idx = collections.value.findIndex((collection) => collection.id === updated.id)
    if (idx !== -1) collections.value[idx] = updated
  }

  async function selectCollection(id: string) {
    if (selectedCollectionId.value === id) return
    if (!collections.value.some((collection) => collection.id === id)) {
      error.value = '要打开的作品集已不存在，请刷新后重新选择。'
      return
    }
    invalidateCollectionScopedLoads()
    selectedCollectionId.value = id
    error.value = null
    selectedArticleId.value = null
    selectedOutlineItemId.value = null
    await Promise.all([
      loadArticles(id),
      loadOutline(id),
    ])
  }

  function selectArticle(id: string) {
    selectedArticleId.value = id
  }

  function selectOutlineItem(id: string) {
    selectedOutlineItemId.value = id
  }

  return {
    collections,
    articles,
    outline,
    selectedCollectionId,
    selectedArticleId,
    selectedOutlineItemId,
    selectedCollection,
    selectedArticle,
    selectedOutlineItem,
    collectionWordCount,
    loading,
    articlesLoading,
    outlineLoading,
    error,
    exportMessage,
    exportingFormat,
    loadCollections,
    loadArticles,
    loadOutline,
    createCollection,
    updateCollection,
    deleteCollection,
    addArticles,
    removeArticle,
    moveArticle,
    reorderArticles,
    createOutlineItem,
    updateOutlineItem,
    deleteOutlineItem,
    reorderOutline,
    exportSelected,
    selectCollection,
    selectArticle,
    selectOutlineItem,
  }
})
