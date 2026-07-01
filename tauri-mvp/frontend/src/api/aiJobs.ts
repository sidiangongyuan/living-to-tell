import { apiFetch, handleResponse } from './base'
import type { MotifEnrichmentDraft, MotifEnrichmentRequest } from './motifs'

export type AiJobStatus =
  | 'queued'
  | 'preparing_context'
  | 'sending_request'
  | 'waiting_model'
  | 'parsing_response'
  | 'succeeded'
  | 'failed'
  | 'cancelled'

export type AiJobStage = AiJobStatus

export interface AiJobSnapshot {
  job_id: string
  kind: 'motif_enrichment'
  status: AiJobStatus
  stage: AiJobStage
  stage_label: string
  concept: string
  motif_id?: string | null
  profile_id: string
  started_at: string
  updated_at: string
  elapsed_ms: number
  result?: MotifEnrichmentDraft | null
  error: string
  provider?: string | null
  model?: string | null
  transport?: string | null
}

export type MotifEnrichmentJobRequest = MotifEnrichmentRequest
export type MotifEnrichmentJobResult = AiJobSnapshot

export const aiJobsApi = {
  async createMotifEnrichmentJob(data: MotifEnrichmentJobRequest): Promise<AiJobSnapshot> {
    const res = await apiFetch('/api/ai/jobs/motif-enrichment', {
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
