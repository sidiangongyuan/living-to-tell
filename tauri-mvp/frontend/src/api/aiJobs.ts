import { apiFetch, handleResponse } from './base'
import type { AiCardDraftRequest } from './aiCards'
import type { MotifEnrichmentRequest, MotifRelationDiscoveryRequest } from './motifs'

export type AiJobStatus =
  | 'queued'
  | 'preparing_context'
  | 'sending_request'
  | 'waiting_model'
  | 'parsing_response'
  | 'building_candidates'
  | 'succeeded'
  | 'failed'
  | 'cancelled'

export type AiJobStage = AiJobStatus

export interface AiJobSnapshot {
  job_id: string
  kind: 'motif_enrichment' | 'motif_relation_discovery' | 'ai_card_draft'
  status: AiJobStatus
  stage: AiJobStage
  stage_label: string
  concept: string
  motif_id?: string | null
  profile_id: string
  started_at: string
  updated_at: string
  elapsed_ms: number
  result?: any | null
  error: string
  provider?: string | null
  model?: string | null
  transport?: string | null
}

export type MotifEnrichmentJobRequest = MotifEnrichmentRequest
export type MotifEnrichmentJobResult = AiJobSnapshot
export type AiCardDraftJobRequest = AiCardDraftRequest & { card_id?: string | null }

export const aiJobsApi = {
  async createMotifEnrichmentJob(data: MotifEnrichmentJobRequest): Promise<AiJobSnapshot> {
    const res = await apiFetch('/api/ai/jobs/motif-enrichment', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async createAiCardDraftJob(data: AiCardDraftJobRequest): Promise<AiJobSnapshot> {
    const res = await apiFetch('/api/ai/jobs/ai-card-draft', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async createMotifRelationDiscoveryJob(data: MotifRelationDiscoveryRequest): Promise<AiJobSnapshot> {
    const res = await apiFetch('/api/ai/jobs/motif-relation-discovery', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async getJob(jobId: string): Promise<AiJobSnapshot> {
    const res = await apiFetch(`/api/ai/jobs/${encodeURIComponent(jobId)}`)
    return handleResponse(res)
  },

  async cancelJob(jobId: string): Promise<AiJobSnapshot> {
    const res = await apiFetch(`/api/ai/jobs/${encodeURIComponent(jobId)}/cancel`, {
      method: 'POST',
    })
    return handleResponse(res)
  },
}
