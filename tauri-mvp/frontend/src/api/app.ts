import { apiFetch, handleResponse } from './base'

export interface AppVersionInfo {
  app_name: string
  version: string
  api_version: string
  capabilities: string[]
}

export const appApi = {
  async getVersion(): Promise<AppVersionInfo> {
    const res = await apiFetch('/api/app/version')
    return handleResponse(res)
  },
}
