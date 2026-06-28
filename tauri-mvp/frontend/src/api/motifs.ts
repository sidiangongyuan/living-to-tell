import { apiFetch, handleResponse } from './base'

export type MotifSourceKind = 'article' | 'reference'

export interface MotifNode {
  id: string
  name: string
  aliases: string[]
  note: string
  tags: string[]
  pinned: boolean
  excerpt_count: number
  created_at: string | null
  updated_at: string | null
}

export interface MotifNodeInput {
  name: string
  aliases?: string[]
  note?: string
  tags?: string[]
  pinned?: boolean
}

export interface MotifExcerpt {
  id: string
  source_kind: MotifSourceKind
  source_id: string
  source_title_snapshot: string
  excerpt_text: string
  note: string
  selection_start: number | null
  selection_end: number | null
  before_context: string
  after_context: string
  motif_ids: string[]
  motif_names: string[]
  source_exists: boolean
  source_current_title: string
  created_at: string | null
  updated_at: string | null
}

export interface CreateMotifExcerptPayload {
  source_kind: MotifSourceKind
  source_id: string
  source_title_snapshot?: string
  excerpt_text: string
  note?: string
  selection_start?: number | null
  selection_end?: number | null
  before_context?: string
  after_context?: string
  motif_ids?: string[]
  motif_names?: string[]
}

export interface LookupMotifExcerptPayload {
  source_kind: MotifSourceKind
  source_id: string
  excerpt_text?: string
  selection_start?: number | null
  selection_end?: number | null
  before_context?: string
  after_context?: string
}

export interface AddMotifsToExcerptPayload {
  motif_ids?: string[]
  motif_names?: string[]
  note?: string | null
}

export interface SetMotifsForExcerptResult {
  excerpt: MotifExcerpt | null
  deleted: boolean
}

export interface MotifEnrichmentRequest {
  motif_id?: string | null
  concept: string
  direction?: string
  include_excerpts?: boolean
  request_web_context?: boolean
  profile_id?: string
  cost_tier?: 'balanced' | 'strong'
}

export interface MotifSourceHint {
  title: string
  url?: string | null
  note: string
}

export interface MotifEnrichmentDraft {
  title: string
  concept: string
  aliases: string[]
  tags: string[]
  note: string
  related_suggestions: string[]
  source_hints: MotifSourceHint[]
  provider?: string | null
  model?: string | null
  transport?: string | null
  elapsed_ms: number
}

export interface MotifGraphNode {
  id: string
  name: string
  excerpt_count: number
  pinned: boolean
  is_center: boolean
}

export interface MotifGraphEdge {
  source_id: string
  target_id: string
  weight: number
  shared_excerpts: number
  shared_sources: number
}

export interface MotifGraph {
  nodes: MotifGraphNode[]
  edges: MotifGraphEdge[]
}

function paramsFrom(input: Record<string, string | number | undefined>) {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(input)) {
    if (value !== undefined && value !== '') {
      params.set(key, String(value))
    }
  }
  const text = params.toString()
  return text ? `?${text}` : ''
}

export const motifsApi = {
  async listMotifs(query = '', limit = 500): Promise<MotifNode[]> {
    const res = await apiFetch(`/api/motifs${paramsFrom({ q: query, limit })}`)
    return handleResponse(res)
  },

  async createMotif(data: MotifNodeInput): Promise<MotifNode> {
    const res = await apiFetch('/api/motifs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async updateMotif(id: string, data: MotifNodeInput): Promise<MotifNode> {
    const res = await apiFetch(`/api/motifs/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async deleteMotif(id: string): Promise<void> {
    const res = await apiFetch(`/api/motifs/${id}`, { method: 'DELETE' })
    return handleResponse(res)
  },

  async generateEnrichmentDraft(data: MotifEnrichmentRequest): Promise<MotifEnrichmentDraft> {
    const res = await apiFetch('/api/motifs/enrich-draft', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      signal: AbortSignal.timeout(120000),
    })
    return handleResponse(res)
  },

  async createExcerpt(data: CreateMotifExcerptPayload): Promise<MotifExcerpt> {
    const res = await apiFetch('/api/motifs/excerpts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async lookupExcerpt(data: LookupMotifExcerptPayload): Promise<MotifExcerpt | null> {
    const res = await apiFetch('/api/motifs/excerpts/lookup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    if (res.status === 404) return null
    return handleResponse(res)
  },

  async addMotifsToExcerpt(id: string, data: AddMotifsToExcerptPayload): Promise<MotifExcerpt> {
    const res = await apiFetch(`/api/motifs/excerpts/${id}/motifs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async setMotifsForExcerpt(id: string, data: AddMotifsToExcerptPayload): Promise<SetMotifsForExcerptResult> {
    const res = await apiFetch(`/api/motifs/excerpts/${id}/motifs`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async listExcerpts(motifId: string, limit = 200): Promise<MotifExcerpt[]> {
    const res = await apiFetch(`/api/motifs/${motifId}/excerpts${paramsFrom({ limit })}`)
    return handleResponse(res)
  },

  async listExcerptsForSource(sourceKind: MotifSourceKind, sourceId: string, limit = 500): Promise<MotifExcerpt[]> {
    const res = await apiFetch(`/api/motifs/excerpts/source/${sourceKind}/${encodeURIComponent(sourceId)}${paramsFrom({ limit })}`)
    return handleResponse(res)
  },

  async graph(query = '', limit = 80): Promise<MotifGraph> {
    const res = await apiFetch(`/api/motifs/graph${paramsFrom({ q: query, limit })}`)
    return handleResponse(res)
  },

  async localGraph(motifId: string, limit = 32): Promise<MotifGraph> {
    const res = await apiFetch(`/api/motifs/${motifId}/graph${paramsFrom({ limit })}`)
    return handleResponse(res)
  },

  async deleteExcerpt(id: string): Promise<void> {
    const res = await apiFetch(`/api/motifs/excerpts/${id}`, { method: 'DELETE' })
    return handleResponse(res)
  },

  async unlinkMotifFromExcerpt(excerptId: string, motifId: string): Promise<void> {
    const res = await apiFetch(`/api/motifs/excerpts/${excerptId}/motifs/${motifId}`, { method: 'DELETE' })
    return handleResponse(res)
  },
}
