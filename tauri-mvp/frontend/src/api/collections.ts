/**
 * Article collections API client.
 */
import { apiFetch, handleResponse } from './base'

export interface Collection {
  id: string
  title: string
  description: string
  article_count: number
  created_at: string | null
  updated_at: string | null
}

export interface CollectionCreate {
  title: string
  description?: string
}

export interface CollectionUpdate {
  title: string
  description: string
}

export interface CollectionArticle {
  id: string
  title: string
  body: string
  body_preview: string
  tags: string[]
  word_count: number
  char_count: number
  sort_order: number
  created_at: string | null
  updated_at: string | null
}

export type CollectionExportFormat = 'txt' | 'md' | 'docx'

export const collectionsApi = {
  async listCollections(): Promise<Collection[]> {
    const res = await apiFetch('/api/collections')
    return handleResponse(res)
  },

  async getCollection(id: string): Promise<Collection> {
    const res = await apiFetch(`/api/collections/${id}`)
    return handleResponse(res)
  },

  async createCollection(data: CollectionCreate): Promise<Collection> {
    const res = await apiFetch('/api/collections', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async updateCollection(id: string, data: CollectionUpdate): Promise<Collection> {
    const res = await apiFetch(`/api/collections/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async deleteCollection(id: string): Promise<void> {
    const res = await apiFetch(`/api/collections/${id}`, {
      method: 'DELETE',
    })
    return handleResponse(res)
  },

  async listArticles(collectionId: string): Promise<CollectionArticle[]> {
    const res = await apiFetch(`/api/collections/${collectionId}/articles`)
    return handleResponse(res)
  },

  async addArticles(collectionId: string, entryIds: string[]): Promise<CollectionArticle[]> {
    const res = await apiFetch(`/api/collections/${collectionId}/articles`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entry_ids: entryIds }),
    })
    return handleResponse(res)
  },

  async removeArticle(collectionId: string, entryId: string): Promise<void> {
    const res = await apiFetch(`/api/collections/${collectionId}/articles/${entryId}`, {
      method: 'DELETE',
    })
    return handleResponse(res)
  },

  async reorderArticles(collectionId: string, entryIds: string[]): Promise<CollectionArticle[]> {
    const res = await apiFetch(`/api/collections/${collectionId}/articles/order`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entry_ids: entryIds }),
    })
    return handleResponse(res)
  },

  async listCollectionsForEntry(entryId: string): Promise<Collection[]> {
    const res = await apiFetch(`/api/collections/for-entry/${entryId}`)
    return handleResponse(res)
  },

  async addEntryToCollections(entryId: string, collectionIds: string[]): Promise<Collection[]> {
    const res = await apiFetch(`/api/collections/for-entry/${entryId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ collection_ids: collectionIds }),
    })
    return handleResponse(res)
  },

  async exportCollection(collectionId: string, format: CollectionExportFormat): Promise<Blob> {
    const res = await apiFetch(`/api/collections/${collectionId}/export?format=${format}`)
    if (!res.ok) {
      await handleResponse(res)
    }
    return res.blob()
  },
}
