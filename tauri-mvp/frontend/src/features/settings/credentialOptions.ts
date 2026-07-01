import type { AiProfile, AiProviderName, AiSettings } from '../../api/settings'

export interface CredentialOption {
  value: string
  label: string
}

export type CredentialTranslator = (key: string, params?: Record<string, string>) => string

export function isLocalSavedCredentialSource(source: string): boolean {
  return source.trim().startsWith('env:LTT_AI_')
}

export function localEnvVarFromCredentialSource(source: string): string | null {
  const trimmed = source.trim()
  if (!isLocalSavedCredentialSource(trimmed)) return null
  return trimmed.split(':', 2)[1]?.trim() || null
}

export function collectSavedLocalCredentialSources(
  provider: AiProviderName,
  currentSource: string,
  settings: AiSettings | null,
  profiles: AiProfile[],
): string[] {
  const sources = new Set<string>()
  const add = (source?: string | null) => {
    const value = (source || '').trim()
    if (isLocalSavedCredentialSource(value)) sources.add(value)
  }

  if (settings?.provider_name === provider) add(settings.api_key_source)
  for (const profile of profiles) {
    if (profile.provider_name === provider) add(profile.api_key_source)
  }
  add(currentSource)
  return Array.from(sources)
}

export function buildCredentialOptions(
  provider: AiProviderName,
  currentSource: string,
  t: CredentialTranslator,
  savedLocalSources: string[] = [],
): CredentialOption[] {
  const options: CredentialOption[] = []
  const add = (value: string, label?: string) => {
    const trimmed = value.trim()
    if (!trimmed || options.some((item) => item.value === trimmed)) return
    options.push({
      value: trimmed,
      label: label
        ?? (isLocalSavedCredentialSource(trimmed)
          ? t('settings.credentialSavedLocalWithSource', { source: trimmed })
          : trimmed),
    })
  }

  if (provider === 'gemini') {
    add('env:GEMINI_API_KEY')
    add('gemini', t('settings.credentialGemini'))
  } else if (provider === 'gemini_cli') {
    add('gemini-cli', t('settings.credentialGeminiCli'))
  } else if (provider === 'opencode') {
    add('opencode', t('settings.credentialOpenCode'))
  } else {
    add('env:OPENAI_API_KEY')
    add('codex', t('settings.credentialCodex'))
  }

  for (const source of savedLocalSources) add(source)
  add(currentSource)
  return options
}
