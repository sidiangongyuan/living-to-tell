/**
 * AI Card API client
 */
import { apiFetch, handleResponse } from './base'

export interface AiCard {
  id: string
  title: string
  content: string
  card_type: 'style' | 'character' | 'setting'
  tags: string[]
  created_at: string | null
  updated_at: string | null
}

export interface AiCardCreate {
  title: string
  content: string
  card_type?: 'style' | 'character' | 'setting'
  tags?: string[]
}

export interface AiCardUpdate {
  title: string
  content: string
  card_type: 'style' | 'character' | 'setting'
  tags: string[]
}

export const aiCardApi = {
  async listCards(cardType?: string): Promise<AiCard[]> {
    const params = cardType ? `?card_type=${cardType}` : ''
    const res = await apiFetch(`/api/ai-cards${params}`)
    return handleResponse(res)
  },

  async searchCards(query: string): Promise<AiCard[]> {
    const res = await apiFetch(`/api/ai-cards/search?q=${encodeURIComponent(query)}`)
    return handleResponse(res)
  },

  async getCard(id: string): Promise<AiCard> {
    const res = await apiFetch(`/api/ai-cards/${id}`)
    return handleResponse(res)
  },

  async createCard(data: AiCardCreate): Promise<AiCard> {
    const res = await apiFetch('/api/ai-cards', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async updateCard(id: string, data: AiCardUpdate): Promise<AiCard> {
    const res = await apiFetch(`/api/ai-cards/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async deleteCard(id: string): Promise<void> {
    const res = await apiFetch(`/api/ai-cards/${id}`, {
      method: 'DELETE',
    })
    return handleResponse(res)
  },

  async listPresets(): Promise<any[]> {
    const res = await apiFetch('/api/ai-cards/presets/list')
    return handleResponse(res)
  },

  async generateFromPresets(): Promise<{ created: number; cards: AiCard[] }> {
    const res = await apiFetch('/api/ai-cards/presets/generate', {
      method: 'POST',
    })
    return handleResponse(res)
  },
}
