import { describe, expect, it } from 'vitest'
import type { AiProfile, AiSettings } from '../../api/settings'
import {
  buildCredentialOptions,
  collectSavedLocalCredentialSources,
  localEnvVarFromCredentialSource,
} from './credentialOptions'

const t = (key: string, params?: Record<string, string>) => {
  if (key === 'settings.credentialSavedLocalWithSource') return `saved:${params?.source}`
  return key
}

function settings(source: string): AiSettings {
  return {
    provider_name: 'openai',
    base_url: 'https://elysiver.h-e.top/',
    wire_api: 'chat_completions',
    model: 'deepseek-v4-pro',
    api_key_source: source,
    gemini_cli_proxy: null,
    status: {} as AiSettings['status'],
    model_presets: {},
  }
}

function profile(name: string, source: string, model = 'deepseek-v4-pro'): AiProfile {
  return {
    id: name,
    name,
    provider_name: 'openai',
    base_url: 'https://elysiver.h-e.top/',
    wire_api: 'chat_completions',
    model,
    api_key_source: source,
    gemini_cli_proxy: null,
    enabled: true,
    source_key: null,
    created_at: '2026-07-01T00:00:00Z',
    updated_at: '2026-07-01T00:00:00Z',
  }
}

describe('settings credential options', () => {
  it('keeps saved local profile credentials selectable after switching source', () => {
    const sources = collectSavedLocalCredentialSources(
      'openai',
      'env:OPENAI_API_KEY',
      settings('env:LTT_AI_GLOBAL_KEY'),
      [
        profile('glm', 'env:LTT_AI_GLM_KEY', 'glm-5.2'),
        profile('deepseek', 'env:LTT_AI_DEEPSEEK_KEY'),
        profile('plain', 'env:OPENAI_API_KEY'),
      ],
    )

    expect(sources).toEqual([
      'env:LTT_AI_GLOBAL_KEY',
      'env:LTT_AI_GLM_KEY',
      'env:LTT_AI_DEEPSEEK_KEY',
    ])

    const options = buildCredentialOptions('openai', 'env:OPENAI_API_KEY', t, sources)
    expect(options.map((option) => option.value)).toEqual([
      'env:OPENAI_API_KEY',
      'codex',
      'env:LTT_AI_GLOBAL_KEY',
      'env:LTT_AI_GLM_KEY',
      'env:LTT_AI_DEEPSEEK_KEY',
    ])
    expect(options.find((option) => option.value === 'env:LTT_AI_GLM_KEY')?.label).toBe('saved:env:LTT_AI_GLM_KEY')
  })

  it('extracts only local Living to Tell env var names for key overwrite', () => {
    expect(localEnvVarFromCredentialSource('env:LTT_AI_DEEPSEEK_KEY')).toBe('LTT_AI_DEEPSEEK_KEY')
    expect(localEnvVarFromCredentialSource('env:OPENAI_API_KEY')).toBeNull()
    expect(localEnvVarFromCredentialSource('codex')).toBeNull()
  })
})
