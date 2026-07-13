import { apiFetch, handleResponse } from './base'

export type MotifSourceKind = 'article' | 'reference'

export interface MotifNode {
  id: string
  name: string
  aliases: string[]
  note: string
  profile: MotifProfile
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
  profile?: Partial<MotifProfile>
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

export interface MotifProfile {
  definition: string
  core_tension: string
  writing_functions: string[]
  scene_triggers: string[]
  character_signals: string[]
  imagery_translations: string[]
  short_examples: string[]
  misuse_warnings: string[]
  micro_exercises: string[]
  source_hints: MotifSourceHint[]
}

export interface MotifReferenceCandidate {
  text: string
  source_author: string
  source_title: string
  source_note: string
  reason: string
}

export type MotifRelationType = 'echo' | 'contrast' | 'transformation' | 'contains' | 'associated'
export type MotifRelationDirection = 'undirected' | 'from_current' | 'to_current'
export type MotifStoredRelationDirection = 'undirected' | 'a_to_b' | 'b_to_a'

export interface MotifRelationCandidate {
  kind: 'existing' | 'new'
  target_motif_id?: string | null
  name: string
  relation_type: MotifRelationType
  direction: MotifRelationDirection
  reason: string
}

export interface MotifRelation {
  id: string
  motif_id: string
  motif_name: string
  target_motif_id: string
  target_motif_name: string
  relation_type: MotifRelationType
  direction: MotifRelationDirection
  reason: string
  created_at: string | null
  updated_at: string | null
}

export interface MotifRelationInput {
  target_motif_id: string
  relation_type: MotifRelationType
  direction: MotifRelationDirection
  reason?: string
}

export interface ApplyMotifRelationCandidatesResult {
  relations: MotifRelation[]
  created_nodes: MotifNode[]
  skipped: string[]
}

export interface MotifRelationDiscoveryRequest {
  motif_id: string
  profile_id?: string
  cost_tier?: 'balanced' | 'strong'
}

export interface MotifRelationDiscoveryDraft {
  motif_id: string
  concept: string
  existing_relation_candidates: MotifRelationCandidate[]
  new_concept_candidates: MotifRelationCandidate[]
  provider?: string | null
  model?: string | null
  transport?: string | null
  elapsed_ms: number
}

export interface MotifEnrichmentDraft {
  title: string
  concept: string
  aliases: string[]
  tags: string[]
  note: string
  profile: MotifProfile
  related_suggestions: string[]
  source_hints: MotifSourceHint[]
  reference_candidates: MotifReferenceCandidate[]
  existing_relation_candidates: MotifRelationCandidate[]
  new_concept_candidates: MotifRelationCandidate[]
  provider?: string | null
  model?: string | null
  transport?: string | null
  elapsed_ms: number
}

export interface ApplyMotifReferenceCandidatesResult {
  imported: Array<{
    reference_id: string
    excerpt_id: string
    text: string
    source_author: string
    source_title: string
    reused_reference: boolean
  }>
  skipped: string[]
}

export interface MotifGraphNode {
  id: string
  name: string
  excerpt_count: number
  pinned: boolean
  is_center: boolean
  relation_count?: number
  needs_enrichment?: boolean
}

export interface MotifGraphEdge {
  source_id: string
  target_id: string
  weight: number
  shared_excerpts: number
  shared_sources: number
  relation_id?: string | null
  relation_type?: MotifRelationType | null
  relation_direction?: MotifStoredRelationDirection | null
  relation_reason?: string
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
      signal: AbortSignal.timeout(300000),
    })
    return handleResponse(res)
  },

  async applyReferenceCandidates(id: string, candidates: MotifReferenceCandidate[]): Promise<ApplyMotifReferenceCandidatesResult> {
    const res = await apiFetch(`/api/motifs/${id}/reference-candidates`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ candidates }),
    })
    return handleResponse(res)
  },

  async listRelations(id: string): Promise<MotifRelation[]> {
    const res = await apiFetch(`/api/motifs/${id}/relations`)
    return handleResponse(res)
  },

  async createRelation(id: string, data: MotifRelationInput): Promise<MotifRelation> {
    const res = await apiFetch(`/api/motifs/${id}/relations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async updateRelation(id: string, relationId: string, data: Omit<MotifRelationInput, 'target_motif_id'>): Promise<MotifRelation> {
    const res = await apiFetch(`/api/motifs/${id}/relations/${relationId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async deleteRelation(id: string, relationId: string): Promise<void> {
    const res = await apiFetch(`/api/motifs/${id}/relations/${relationId}`, { method: 'DELETE' })
    return handleResponse(res)
  },

  async applyRelationCandidates(id: string, candidates: MotifRelationCandidate[]): Promise<ApplyMotifRelationCandidatesResult> {
    const res = await apiFetch(`/api/motifs/${id}/relations/apply-candidates`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ candidates }),
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
