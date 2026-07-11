import { afterEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { HttpError } from '../../api/base'
import {
  collectionsApi,
  type Collection,
  type CollectionArticle,
  type CollectionOutlineItem,
} from '../../api/collections'
import { useCollectionsStore } from './store'

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
}

function collection(id: string, title: string): Collection {
  return {
    id,
    title,
    description: '',
    project_type: 'novel',
    article_count: 1,
    created_at: null,
    updated_at: null,
  }
}

function article(id: string, title: string): CollectionArticle {
  return {
    id,
    title,
    body: title,
    body_preview: title,
    tags: [],
    word_count: 2,
    char_count: 2,
    sort_order: 0,
    created_at: null,
    updated_at: null,
  }
}

function outline(id: string, collectionId: string, title: string): CollectionOutlineItem {
  return {
    id,
    collection_id: collectionId,
    parent_id: null,
    entry_id: null,
    title,
    item_type: 'chapter',
    status: 'idea',
    summary: '',
    notes: '',
    pov: '',
    setting: '',
    timeline: '',
    tags: [],
    target_word_count: null,
    sort_order: 0,
    created_at: null,
    updated_at: null,
  }
}

describe('collections store request ownership', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('ignores a late 404 and stale outline after switching to another collection', async () => {
    setActivePinia(createPinia())
    const store = useCollectionsStore()
    const collectionA = collection('collection-a', '作品 A')
    const collectionB = collection('collection-b', '作品 B')
    store.collections = [collectionA, collectionB]

    const articlesA = deferred<CollectionArticle[]>()
    const articlesB = deferred<CollectionArticle[]>()
    const outlineA = deferred<CollectionOutlineItem[]>()
    const outlineB = deferred<CollectionOutlineItem[]>()

    vi.spyOn(collectionsApi, 'listArticles').mockImplementation((collectionId) => (
      collectionId === collectionA.id ? articlesA.promise : articlesB.promise
    ))
    vi.spyOn(collectionsApi, 'listOutline').mockImplementation((collectionId) => (
      collectionId === collectionA.id ? outlineA.promise : outlineB.promise
    ))

    const selectingA = store.selectCollection(collectionA.id)
    const selectingB = store.selectCollection(collectionB.id)

    articlesB.resolve([article('article-b', 'B 的正文')])
    outlineB.resolve([outline('outline-b', collectionB.id, 'B 的章节')])
    await selectingB

    articlesA.reject(new HttpError(404, 'Not Found', 'Collection not found'))
    outlineA.resolve([outline('outline-a', collectionA.id, 'A 的章节')])
    await selectingA

    expect(store.selectedCollectionId).toBe(collectionB.id)
    expect(store.articles.map((item) => item.id)).toEqual(['article-b'])
    expect(store.outline.map((item) => item.id)).toEqual(['outline-b'])
    expect(store.error).toBeNull()
    expect(store.articlesLoading).toBe(false)
    expect(store.outlineLoading).toBe(false)
  })
})
