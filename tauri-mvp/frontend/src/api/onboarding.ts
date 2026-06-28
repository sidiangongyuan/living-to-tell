import { apiFetch, handleResponse } from './base'

export interface SampleProjectState {
  installed: boolean
  collection_id: string | null
  entry_ids: string[]
  reference_ids: string[]
  ai_card_ids: string[]
  note_ids: string[]
  created_at: string | null
  missing_ids: string[]
}

export type SampleProjectAction = 'created' | 'already_installed' | 'removed' | 'not_installed'

export interface SampleProjectActionResult extends SampleProjectState {
  action: SampleProjectAction
}

export const onboardingApi = {
  async getSampleProject(): Promise<SampleProjectState> {
    const res = await apiFetch('/api/onboarding/sample-project')
    return handleResponse(res)
  },

  async createSampleProject(): Promise<SampleProjectActionResult> {
    const res = await apiFetch('/api/onboarding/sample-project', {
      method: 'POST',
    })
    return handleResponse(res)
  },

  async deleteSampleProject(): Promise<SampleProjectActionResult> {
    const res = await apiFetch('/api/onboarding/sample-project', {
      method: 'DELETE',
    })
    return handleResponse(res)
  },
}
