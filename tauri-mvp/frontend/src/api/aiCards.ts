/**
 * AI Card API client
 */
import { apiFetch, handleResponse } from './base'

export type AiCardType = 'style' | 'character' | 'scene'

export interface AiCard {
  id: string
  title: string
  content: string
  card_type: AiCardType
  tags: string[]
  created_at: string | null
  updated_at: string | null
}

export interface AiCardCreate {
  title: string
  content: string
  card_type?: AiCardType
  tags?: string[]
}

export interface AiCardUpdate {
  title: string
  content: string
  card_type: AiCardType
  tags: string[]
}

export interface AiCardDraftRequest {
  card_type: AiCardType
  source_text: string
  keep_source_quotes?: boolean
  cost_tier?: 'thrifty' | 'balanced' | 'strong'
  profile_id?: string
}

export interface AiCardDraft {
  title: string
  card_type: AiCardType
  content: string
  tags?: string[]
  provider?: string | null
  model?: string | null
  transport?: string | null
  elapsed_ms?: number | null
}

export const aiCardApi = {
  async listCards(cardType?: string): Promise<AiCard[]> {
    const params = cardType ? `?card_type=${cardType}` : ''
    const res = await apiFetch(`/api/ai-cards${params}`)
    return handleResponse(res)
  },

  async searchCards(query: string, cardType?: AiCardType, limit?: number): Promise<AiCard[]> {
    const params = new URLSearchParams({ q: query })
    if (cardType) params.set('card_type', cardType)
    if (limit) params.set('limit', String(limit))
    const res = await apiFetch(`/api/ai-cards/search?${params.toString()}`)
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

  async generateDraft(data: AiCardDraftRequest): Promise<AiCardDraft> {
    const res = await apiFetch('/api/ai-cards/generate-draft', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async upgradeDraft(id: string, data: AiCardDraftRequest): Promise<AiCardDraft> {
    const res = await apiFetch(`/api/ai-cards/${id}/upgrade-draft`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },
}
