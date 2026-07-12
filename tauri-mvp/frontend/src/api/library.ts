/**
 * Library API client - 文脉标本库
 * 字段对齐 Qt 版 ReferencePassage
 */
import { apiFetch, handleResponse } from './base'

export interface Reference {
  id: string
  source_title: string      // 出处（书名/篇名）
  content: string           // 标本正文
  source_author: string     // 作者
  tags: string[]
  kind: string              // excerpt 等
  usage_kind: string        // style/imagery/...
  personal_note: string     // 个人笔记
  created_at: string | null
  updated_at: string | null
}

export interface ReferenceCreate {
  source_title?: string
  content: string
  source_author?: string
  tags?: string[]
  kind?: string
  usage_kind?: string
  personal_note?: string
}

export interface ReferenceUpdate {
  source_title: string
  content: string
  source_author?: string
  tags?: string[]
  kind?: string
  usage_kind?: string
  personal_note?: string
}

export interface LibraryStats {
  total: number
  by_usage_kind: Record<string, number>
}

export const libraryApi = {
  async getStats(): Promise<LibraryStats> {
    const res = await apiFetch('/api/library/stats')
    return handleResponse(res)
  },

  async listReferences(limit = 500, usageKind?: string): Promise<Reference[]> {
    const params = new URLSearchParams({ limit: String(limit) })
    if (usageKind) params.set('usage_kind', usageKind)
    const res = await apiFetch(`/api/library/references?${params}`)
    return handleResponse(res)
  },

  async searchReferences(query: string, limit = 100, usageKind?: string): Promise<Reference[]> {
    const params = new URLSearchParams({ q: query, limit: String(limit) })
    if (usageKind) params.set('usage_kind', usageKind)
    const res = await apiFetch(`/api/library/references/search?${params}`)
    return handleResponse(res)
  },

  async getReference(id: string): Promise<Reference> {
    const res = await apiFetch(`/api/library/references/${id}`)
    return handleResponse(res)
  },

  async createReference(data: ReferenceCreate): Promise<Reference> {
    const res = await apiFetch('/api/library/references', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async updateReference(id: string, data: ReferenceUpdate): Promise<Reference> {
    const res = await apiFetch(`/api/library/references/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async deleteReference(id: string): Promise<void> {
    const res = await apiFetch(`/api/library/references/${id}`, {
      method: 'DELETE',
    })
    return handleResponse(res)
  },
}
