import { apiFetch, handleResponse } from './base'

export type AiProviderName = 'openai' | 'gemini' | 'gemini_cli' | 'opencode'

export interface AiCredentialStatus {
  available: boolean
  path?: string | null
  reason: string
  account?: string | null
  command?: string | null
  proxy?: string | null
}

export interface AiSettingsStatus {
  env: AiCredentialStatus
  codex: AiCredentialStatus
  gemini: AiCredentialStatus
  gemini_cli: AiCredentialStatus
  opencode: AiCredentialStatus
}

export interface AiSettings {
  provider_name: AiProviderName
  base_url: string | null
  wire_api: string
  model: string
  api_key_source: string
  gemini_cli_proxy: string | null
  status: AiSettingsStatus
  model_presets: Record<string, string[]>
}

export interface AiSettingsUpdate {
  provider_name: AiProviderName
  base_url?: string | null
  wire_api?: string
  model: string
  api_key_source: string
  gemini_cli_proxy?: string | null
}

export interface AiProfile {
  id: string
  name: string
  provider_name: AiProviderName
  base_url: string | null
  wire_api: string
  model: string
  api_key_source: string
  gemini_cli_proxy: string | null
  enabled: boolean
  source_key?: string | null
  created_at: string
  updated_at: string
}

export interface AiProfileCreate {
  name: string
  provider_name: AiProviderName
  base_url?: string | null
  wire_api?: string
  model: string
  api_key_source: string
  gemini_cli_proxy?: string | null
  enabled?: boolean
  source_key?: string | null
}

export type AiProfileUpdate = Partial<AiProfileCreate>

export interface AiProfileListResult {
  profiles: AiProfile[]
}

export interface AiDiscoveredProfile extends AiProfileCreate {
  source_key: string
  source_label: string
  available: boolean
  reason: string
  existing_profile_id?: string | null
  live_test_supported: boolean
}

export interface AiProfileImportLocalResult {
  profiles: AiProfile[]
  imported_count: number
  updated_count: number
  skipped: string[]
}

export interface AiImportResult {
  config: AiSettings
  imported: Record<string, unknown>
}

export interface AiTestResult {
  ok: boolean
  message: string
}

export interface AiLiveTestResult {
  ok: boolean
  message: string
  provider: string
  model: string
  transport?: string | null
  elapsed_ms?: number | null
  preview: string
  cost?: number | null
}

export interface AiModelListResult {
  provider: string
  models: string[]
  source: 'live' | 'preset'
  message: string
}

export interface DataLocationInfo {
  data_dir: string
  default_data_dir: string
  database_path: string
  default_database_path: string
  backup_dir: string
  checkpoint_dir: string
  is_custom: boolean
  database_exists: boolean
  warning?: string | null
}

export interface DataLocationMigrationRequest {
  target_dir: string
  replace_existing?: boolean
}

export interface DataLocationMigrationResult {
  target_dir: string
  target_database_path: string
  restart_required: boolean
  message: string
}

export const settingsApi = {
  async getAiSettings(): Promise<AiSettings> {
    const res = await apiFetch('/api/settings/ai')
    return handleResponse(res)
  },

  async saveAiSettings(data: AiSettingsUpdate): Promise<AiSettings> {
    const res = await apiFetch('/api/settings/ai', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async listAiProfiles(): Promise<AiProfileListResult> {
    const res = await apiFetch('/api/settings/ai/profiles')
    return handleResponse(res)
  },

  async discoverAiProfiles(): Promise<AiDiscoveredProfile[]> {
    const res = await apiFetch('/api/settings/ai/profiles/discover')
    return handleResponse(res)
  },

  async importLocalAiProfiles(sourceKeys: string[] = [], updateExisting = true): Promise<AiProfileImportLocalResult> {
    const res = await apiFetch('/api/settings/ai/profiles/import-local', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_keys: sourceKeys, update_existing: updateExisting }),
    })
    return handleResponse(res)
  },

  async createAiProfile(data: AiProfileCreate): Promise<AiProfile> {
    const res = await apiFetch('/api/settings/ai/profiles', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async updateAiProfile(id: string, data: AiProfileUpdate): Promise<AiProfile> {
    const res = await apiFetch(`/api/settings/ai/profiles/${encodeURIComponent(id)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async deleteAiProfile(id: string): Promise<void> {
    const res = await apiFetch(`/api/settings/ai/profiles/${encodeURIComponent(id)}`, {
      method: 'DELETE',
    })
    return handleResponse(res)
  },

  async testAiSettings(data: AiSettingsUpdate): Promise<AiTestResult> {
    const res = await apiFetch('/api/settings/ai/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async testAiSettingsLive(data: AiSettingsUpdate): Promise<AiLiveTestResult> {
    const res = await apiFetch('/api/settings/ai/test-live', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async getAiModels(provider: AiProviderName, refresh = true, config?: Partial<AiSettingsUpdate>): Promise<AiModelListResult> {
    const params = new URLSearchParams({ provider, refresh: String(refresh) })
    if (config?.base_url) params.set('base_url', config.base_url)
    if (config?.api_key_source) params.set('api_key_source', config.api_key_source)
    const res = await apiFetch(`/api/settings/ai/models?${params.toString()}`)
    return handleResponse(res)
  },

  async importCodexSettings(): Promise<AiImportResult> {
    const res = await apiFetch('/api/settings/ai/import-codex', {
      method: 'POST',
    })
    return handleResponse(res)
  },

  async importGeminiSettings(): Promise<AiImportResult> {
    const res = await apiFetch('/api/settings/ai/import-gemini', {
      method: 'POST',
    })
    return handleResponse(res)
  },

  async getDataLocation(): Promise<DataLocationInfo> {
    const res = await apiFetch('/api/settings/data-location')
    return handleResponse(res)
  },

  async migrateDataLocation(data: DataLocationMigrationRequest): Promise<DataLocationMigrationResult> {
    const res = await apiFetch('/api/settings/data-location/migrate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },
}
