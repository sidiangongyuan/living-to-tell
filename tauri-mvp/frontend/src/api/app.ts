import { apiFetch, handleResponse } from './base'

export interface AppVersionInfo {
  app_name: string
  version: string
  api_version: string
  capabilities: string[]
}

export type AppUpdateStatus = 'up_to_date' | 'update_available' | 'error'

export interface AppUpdateInfo {
  current_version: string
  latest_version: string | null
  latest_tag: string | null
  release_name: string | null
  release_url: string | null
  published_at: string | null
  release_notes: string
  source: string
  status: AppUpdateStatus
  message: string
  checked_at: string
  cached: boolean
  download_url: string | null
  download_name: string | null
}

export const appApi = {
  async getVersion(): Promise<AppVersionInfo> {
    const res = await apiFetch('/api/app/version')
    return handleResponse(res)
  },

  async checkForUpdate(force = false): Promise<AppUpdateInfo> {
    const params = new URLSearchParams()
    if (force) params.set('force', 'true')
    const suffix = params.toString()
    const res = await apiFetch(`/api/app/update-check${suffix ? `?${suffix}` : ''}`)
    return handleResponse(res)
  },
}
