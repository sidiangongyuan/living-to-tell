/**
 * Article writing notes API client.
 */
import { apiFetch, handleResponse } from './base'

export type WritingNoteStatus = 'open' | 'done'

export interface WritingNote {
  id: string
  entry_id: string
  body: string
  status: WritingNoteStatus
  pinned: boolean
  sort_order: number
  created_at: string | null
  updated_at: string | null
  completed_at: string | null
}

export const notesApi = {
  async listNotes(entryId: string, includeDone = true): Promise<WritingNote[]> {
    const params = new URLSearchParams({ include_done: String(includeDone) })
    const res = await apiFetch(`/api/articles/${entryId}/notes?${params}`)
    return handleResponse(res)
  },

  async createNote(entryId: string, body: string, pinned = false): Promise<WritingNote> {
    const res = await apiFetch(`/api/articles/${entryId}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ body, pinned }),
    })
    return handleResponse(res)
  },

  async updateNote(entryId: string, noteId: string, body: string): Promise<WritingNote> {
    const res = await apiFetch(`/api/articles/${entryId}/notes/${noteId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ body }),
    })
    return handleResponse(res)
  },

  async setPinned(entryId: string, noteId: string, pinned: boolean): Promise<WritingNote> {
    const res = await apiFetch(`/api/articles/${entryId}/notes/${noteId}/pinned`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pinned }),
    })
    return handleResponse(res)
  },

  async setDone(entryId: string, noteId: string, done: boolean): Promise<WritingNote> {
    const res = await apiFetch(`/api/articles/${entryId}/notes/${noteId}/done`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ done }),
    })
    return handleResponse(res)
  },

  async deleteNote(entryId: string, noteId: string): Promise<void> {
    const res = await apiFetch(`/api/articles/${entryId}/notes/${noteId}`, {
      method: 'DELETE',
    })
    return handleResponse(res)
  },
}

