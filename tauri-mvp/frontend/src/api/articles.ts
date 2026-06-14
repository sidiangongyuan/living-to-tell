/**
 * Articles API client
 */
import { apiFetch, handleResponse } from './base'

export interface Entry {
  id: string
  title: string
  body: string
  entry_type: string
  created_at: string | null
  updated_at: string | null
  tags: string[]
  archived_at: string | null
  curation_status: string
}

export interface EntryCreate {
  title?: string
  body?: string
  tags?: string[]
}

export interface EntryUpdate {
  title: string
  body: string
  tags?: string[]
}

export const articlesApi = {
  async listArticles(limit = 100, includeArchived = false): Promise<Entry[]> {
    const params = new URLSearchParams({
      limit: String(limit),
      include_archived: String(includeArchived),
    })
    const res = await apiFetch(`/api/articles?${params}`)
    return handleResponse(res)
  },

  async list(limit = 100, includeArchived = false): Promise<Entry[]> {
    return this.listArticles(limit, includeArchived)
  },

  async search(query: string, limit = 50): Promise<Entry[]> {
    const params = new URLSearchParams({ q: query, limit: String(limit) })
    const res = await apiFetch(`/api/articles/search?${params}`)
    return handleResponse(res)
  },

  async get(id: string): Promise<Entry> {
    const res = await apiFetch(`/api/articles/${id}`)
    return handleResponse(res)
  },

  async create(data: EntryCreate): Promise<Entry> {
    const res = await apiFetch('/api/articles', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async update(id: string, data: EntryUpdate): Promise<Entry> {
    const res = await apiFetch(`/api/articles/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async updateArticle(id: string, data: Partial<EntryUpdate>): Promise<Entry> {
    // 获取当前文章
    const current = await this.get(id)
    return this.update(id, {
      title: data.title ?? current.title,
      body: data.body ?? current.body,
      tags: data.tags ?? current.tags,
    })
  },

  async delete(id: string): Promise<void> {
    const res = await apiFetch(`/api/articles/${id}`, {
      method: 'DELETE',
    })
    return handleResponse(res)
  },

  async archive(id: string): Promise<Entry> {
    const res = await apiFetch(`/api/articles/${id}/archive`, {
      method: 'POST',
    })
    return handleResponse(res)
  },

  async unarchive(id: string): Promise<Entry> {
    const res = await apiFetch(`/api/articles/${id}/unarchive`, {
      method: 'POST',
    })
    return handleResponse(res)
  },
}
