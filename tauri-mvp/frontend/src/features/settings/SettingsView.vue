<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { appApi } from '../../api/app'
import { errorMessage, isHttpStatus } from '../../api/base'
import {
  settingsApi,
  type AiDiscoveredProfile,
  type AiLiveTestResult,
  type AiModelListResult,
  type AiProfile,
  type AiProfileCreate,
  type AiProviderName,
  type AiSettings,
  type AiSettingsUpdate,
  type DataLocationInfo,
} from '../../api/settings'
import { useI18n } from '../../i18n'
import { useAppUpdateStore } from '../../stores/appUpdate'
import { useSettingsStore } from '../../stores/settings'

interface DataDirectoryOverrideState {
  override_path?: string | null
  active_path?: string | null
  warning?: string | null
}

type UiLiveTestResult = AiLiveTestResult & { success: boolean }
type UiModelFetchResult = AiModelListResult & { success: boolean }

interface DiagnosticRow {
  label: string
  value: string
  detail?: string
  tone: 'default' | 'good' | 'warn' | 'bad'
}

const { t } = useI18n()
const route = useRoute()
const settings = useSettingsStore()
const appUpdate = useAppUpdateStore()
const OPENCODE_DEFAULT_MODEL = 'opencode/deepseek-v4-flash-free'

const aiProvider = ref<AiProviderName>('openai')
const model = ref('gpt-4o-mini')
const baseUrl = ref('')
const apiKeySource = ref('env:OPENAI_API_KEY')
const geminiCliProxy = ref('')
const aiSettings = ref<AiSettings | null>(null)
const loadingAiSettings = ref(false)
const savingSettings = ref(false)
const testingConnection = ref(false)
const testingLiveConnection = ref(false)
const fetchingModels = ref(false)
const importing = ref<'codex' | 'gemini' | null>(null)
const testResult = ref<{ success: boolean; message: string } | null>(null)
const liveTestResult = ref<UiLiveTestResult | null>(null)
const modelFetchResult = ref<UiModelFetchResult | null>(null)
const saveNotice = ref('')
const saveError = ref('')
const fetchedModelPresets = ref<Partial<Record<AiProviderName, string[]>>>({})
let applyingAiSettings = false

const aiProfiles = ref<AiProfile[]>([])
const loadingProfiles = ref(false)
const savingProfile = ref(false)
const testingProfile = ref(false)
const fetchingProfileModels = ref(false)
const profileEditorOpen = ref(false)
const editingProfileId = ref<string | null>(null)
const profileDraft = ref<AiProfileCreate>(createEmptyProfileDraft())
const profileNotice = ref('')
const profileError = ref('')
const profileTestResult = ref<UiLiveTestResult | null>(null)
const profileModelFetchResult = ref<UiModelFetchResult | null>(null)
const profileModelPresets = ref<Partial<Record<AiProviderName, string[]>>>({})
const discoveredProfiles = ref<AiDiscoveredProfile[]>([])
const discoveringProfiles = ref(false)
const importingLocalProfiles = ref(false)
const aiProfilesSectionRef = ref<HTMLElement | null>(null)
let profileStateSeq = 0

const closeBehaviorNotice = ref('')
const dataLocation = ref<DataLocationInfo | null>(null)
const dataOverride = ref<DataDirectoryOverrideState | null>(null)
const selectedDataDir = ref('')
const loadingDataLocation = ref(false)
const migratingDataLocation = ref(false)
const dataLocationNotice = ref('')
const dataLocationError = ref('')
const dataLocationUnsupported = ref(false)
const updateActionError = ref('')

const providerOptions = computed<Array<{ value: AiProviderName; label: string }>>(() => [
  { value: 'openai', label: t('settings.providers.openai') },
  { value: 'gemini', label: t('settings.providers.gemini') },
  { value: 'gemini_cli', label: t('settings.providers.geminiCli') },
  { value: 'opencode', label: t('settings.providers.opencode') },
])

function credentialOptionsFor(provider: AiProviderName): Array<{ value: string; label: string }> {
  if (provider === 'gemini') {
    return [
      { value: 'env:GEMINI_API_KEY', label: 'env:GEMINI_API_KEY' },
      { value: 'gemini', label: t('settings.credentialGemini') },
    ]
  }
  if (provider === 'gemini_cli') {
    return [{ value: 'gemini-cli', label: t('settings.credentialGeminiCli') }]
  }
  if (provider === 'opencode') {
    return [{ value: 'opencode', label: t('settings.credentialOpenCode') }]
  }
  return [
    { value: 'env:OPENAI_API_KEY', label: 'env:OPENAI_API_KEY' },
    { value: 'codex', label: t('settings.credentialCodex') },
  ]
}

const credentialOptions = computed<Array<{ value: string; label: string }>>(() => credentialOptionsFor(aiProvider.value))

const modelPresets = computed(() =>
  fetchedModelPresets.value[aiProvider.value]
  ?? aiSettings.value?.model_presets?.[aiProvider.value]
  ?? []
)

const profileModelOptions = computed(() =>
  profileModelPresets.value[profileDraft.value.provider_name]
  ?? fetchedModelPresets.value[profileDraft.value.provider_name]
  ?? aiSettings.value?.model_presets?.[profileDraft.value.provider_name]
  ?? []
)

const activeStatus = computed(() => {
  if (!aiSettings.value) return null
  if (aiProvider.value === 'opencode') return aiSettings.value.status.opencode
  if (aiProvider.value === 'gemini_cli') return aiSettings.value.status.gemini_cli
  if (apiKeySource.value === 'codex') return aiSettings.value.status.codex
  if (apiKeySource.value === 'gemini') return aiSettings.value.status.gemini
  return aiSettings.value.status.env
})

const statusMatchesSavedConfig = computed(() => {
  if (!aiSettings.value) return false
  if (aiProvider.value === 'opencode') return true
  if (aiSettings.value.provider_name !== aiProvider.value) return false
  if (aiProvider.value === 'gemini_cli') {
    return (aiSettings.value.gemini_cli_proxy ?? '') === (geminiCliProxy.value.trim() || '')
  }
  return aiSettings.value.api_key_source === apiKeySource.value.trim()
})

const statusLabel = computed(() => {
  if (!statusMatchesSavedConfig.value) return t('settings.statusPending')
  const status = activeStatus.value
  if (!status) return t('settings.statusUnknown')
  if (status.available) return t('settings.statusAvailable')
  return status.reason ? t('settings.statusUnavailableWithReason', { reason: status.reason }) : t('settings.statusUnavailable')
})

const statusDetail = computed(() => {
  if (!statusMatchesSavedConfig.value) return ''
  const status = activeStatus.value
  if (!status) return ''
  if (aiProvider.value === 'opencode') {
    const parts = [
      status.command ? `${t('settings.openCodeCommand')}: ${status.command}` : '',
      status.path ? `${t('settings.credentialPath')}: ${status.path}` : '',
    ].filter(Boolean)
    return parts.join('\n')
  }
  if (aiProvider.value === 'gemini_cli') {
    const parts = [
      status.command ? `${t('settings.geminiCliCommand')}: ${status.command}` : '',
      status.account ? `${t('settings.geminiCliAccount')}: ${status.account}` : '',
      status.path ? `${t('settings.credentialPath')}: ${status.path}` : '',
    ].filter(Boolean)
    return parts.join('\n')
  }
  return status.path ? `${t('settings.credentialPath')}: ${status.path}` : ''
})

const diagnosticRows = computed<DiagnosticRow[]>(() => {
  const providerLabel = providerOptions.value.find((provider) => provider.value === aiProvider.value)?.label ?? aiProvider.value
  const modelListSource = modelFetchResult.value
    ? modelFetchResult.value.source === 'live'
      ? t('settings.diagnostics.modelSourceLive')
      : t('settings.diagnostics.modelSourcePreset')
    : t('settings.diagnostics.notFetched')
  const localCheck = testResult.value
    ? testResult.value.success
      ? t('settings.diagnostics.localCheckPassed')
      : t('settings.diagnostics.localCheckFailed')
    : statusMatchesSavedConfig.value && activeStatus.value
      ? statusLabel.value
      : t('settings.diagnostics.notChecked')
  const liveStatus = liveTestResult.value
    ? liveTestResult.value.success
      ? t('settings.diagnostics.liveTestPassed')
      : t('settings.diagnostics.liveTestFailed')
    : t('settings.diagnostics.notTested')
  const elapsed = liveTestResult.value?.elapsed_ms ?? null

  return [
    {
      label: t('settings.diagnostics.provider'),
      value: providerLabel,
      detail: aiProvider.value,
      tone: 'default',
    },
    {
      label: t('settings.diagnostics.model'),
      value: model.value.trim() || t('settings.diagnostics.empty'),
      tone: model.value.trim() ? 'default' : 'warn',
    },
    {
      label: t('settings.diagnostics.transport'),
      value: liveTestResult.value?.transport || inferredTransportLabel(),
      detail: liveTestResult.value?.provider ? `${liveTestResult.value.provider} · ${liveTestResult.value.model}` : undefined,
      tone: liveTestResult.value?.success ? 'good' : 'default',
    },
    {
      label: t('settings.diagnostics.credential'),
      value: diagnosticCredentialSource(),
      detail: activeStatus.value?.command || undefined,
      tone: activeStatus.value?.available ? 'good' : 'warn',
    },
    {
      label: t('settings.diagnostics.localCheck'),
      value: localCheck,
      detail: testResult.value?.message,
      tone: testResult.value ? (testResult.value.success ? 'good' : 'bad') : activeStatus.value?.available ? 'good' : 'warn',
    },
    {
      label: t('settings.diagnostics.realRequest'),
      value: elapsed !== null && elapsed !== undefined ? `${liveStatus} · ${elapsed}ms` : liveStatus,
      detail: liveTestResult.value?.preview || liveTestResult.value?.message,
      tone: liveTestResult.value ? (liveTestResult.value.success ? 'good' : 'bad') : 'warn',
    },
    {
      label: t('settings.diagnostics.modelList'),
      value: modelListSource,
      detail: modelFetchResult.value?.message,
      tone: modelFetchResult.value?.source === 'live' ? 'good' : modelFetchResult.value ? 'warn' : 'default',
    },
  ]
})

function inferredTransportLabel(): string {
  if (aiProvider.value === 'opencode') return 'opencode_cli'
  if (aiProvider.value === 'gemini_cli') return 'gemini_cli'
  if (aiProvider.value === 'gemini') {
    if (baseUrl.value.trim() && apiKeySource.value.trim().startsWith('sk-')) return 'chat_completions'
    return baseUrl.value.trim() ? t('settings.diagnostics.autoTransport') : 'gemini_native'
  }
  return baseUrl.value.trim() ? (aiSettings.value?.wire_api || 'chat_completions') : 'chat_completions'
}

function diagnosticCredentialSource(): string {
  if (aiProvider.value === 'opencode') return t('settings.credentialOpenCode')
  if (aiProvider.value === 'gemini_cli') return t('settings.credentialGeminiCli')
  const option = credentialOptions.value.find((item) => item.value === apiKeySource.value)
  return option?.label ?? apiKeySource.value.trim() ?? t('settings.diagnostics.empty')
}

function diagnosticToneClass(tone: DiagnosticRow['tone']): string {
  if (tone === 'good') return 'border-emerald-100 bg-emerald-50 text-emerald-900'
  if (tone === 'bad') return 'border-red-100 bg-red-50 text-red-900'
  if (tone === 'warn') return 'border-amber-100 bg-amber-50 text-amber-900'
  return 'border-slate-100 bg-slate-50 text-slate-900'
}

onMounted(() => {
  void loadSettings()
  void loadProfiles()
  void loadDataLocation()
  void settings.loadNativePreferences()
  void appUpdate.ensureVersionLoaded()
  void focusRequestedSection()
})

watch(() => route.query.section, () => {
  void focusRequestedSection()
})

watch(aiProvider, (provider, previous) => {
  if (applyingAiSettings) return
  if (provider === previous) return
  testResult.value = null
  liveTestResult.value = null
  modelFetchResult.value = null
  saveNotice.value = ''
  saveError.value = ''
  if (provider === 'openai') {
    apiKeySource.value = 'env:OPENAI_API_KEY'
    if (!model.value || model.value.startsWith('gemini')) model.value = 'gpt-4o-mini'
  } else if (provider === 'gemini') {
    apiKeySource.value = 'env:GEMINI_API_KEY'
    if (!model.value || model.value.startsWith('gpt-') || model.value.startsWith('opencode/')) model.value = 'gemini-2.5-flash'
  } else if (provider === 'gemini_cli') {
    apiKeySource.value = 'gemini-cli'
    baseUrl.value = ''
    if (!model.value || model.value.startsWith('gpt-') || model.value.startsWith('opencode/')) model.value = 'gemini-cli-default'
  } else {
    apiKeySource.value = 'opencode'
    baseUrl.value = ''
    if (!model.value || model.value.startsWith('gpt-') || model.value.startsWith('gemini')) model.value = OPENCODE_DEFAULT_MODEL
  }
})

async function loadSettings() {
  loadingAiSettings.value = true
  saveError.value = ''
  try {
    const loaded = await settingsApi.getAiSettings()
    applyAiSettings(loaded)
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : String(e)
  } finally {
    loadingAiSettings.value = false
  }
}

function applyAiSettings(loaded: AiSettings) {
  applyingAiSettings = true
  aiSettings.value = loaded
  aiProvider.value = loaded.provider_name
  model.value = loaded.model
  baseUrl.value = loaded.base_url ?? ''
  apiKeySource.value = loaded.provider_name === 'gemini_cli'
    ? 'gemini-cli'
    : loaded.provider_name === 'opencode'
      ? 'opencode'
      : loaded.api_key_source
  geminiCliProxy.value = loaded.gemini_cli_proxy ?? loaded.status.gemini_cli.proxy ?? ''
  window.setTimeout(() => {
    applyingAiSettings = false
  }, 0)
}

function buildAiSettingsUpdate(): AiSettingsUpdate {
  return {
    provider_name: aiProvider.value,
    base_url: aiProvider.value === 'gemini_cli' || aiProvider.value === 'opencode' ? null : baseUrl.value.trim() || null,
    wire_api: 'responses',
    model: model.value.trim() || (aiProvider.value === 'gemini_cli' ? 'gemini-cli-default' : aiProvider.value === 'opencode' ? OPENCODE_DEFAULT_MODEL : ''),
    api_key_source: aiProvider.value === 'gemini_cli' ? 'gemini-cli' : aiProvider.value === 'opencode' ? 'opencode' : apiKeySource.value.trim(),
    gemini_cli_proxy: aiProvider.value === 'gemini_cli' ? geminiCliProxy.value.trim() || null : null,
  }
}

function createEmptyProfileDraft(): AiProfileCreate {
  return {
    name: '',
    provider_name: 'openai',
    base_url: '',
    wire_api: 'chat_completions',
    model: '',
    api_key_source: 'env:OPENAI_API_KEY',
    gemini_cli_proxy: null,
    enabled: true,
    source_key: null,
  }
}

function profileToDraft(profile: AiProfile): AiProfileCreate {
  return {
    name: profile.name,
    provider_name: profile.provider_name,
    base_url: profile.base_url ?? '',
    wire_api: profile.wire_api || 'responses',
    model: profile.model,
    api_key_source: profile.api_key_source,
    gemini_cli_proxy: profile.gemini_cli_proxy,
    enabled: profile.enabled,
    source_key: profile.source_key ?? null,
  }
}

function profileDraftToSettingsUpdate(draft = profileDraft.value): AiSettingsUpdate {
  const provider = draft.provider_name
  return {
    provider_name: provider,
    base_url: provider === 'gemini_cli' || provider === 'opencode' ? null : (draft.base_url || '').trim() || null,
    wire_api: provider === 'openai' ? (draft.wire_api || 'chat_completions') : 'responses',
    model: (draft.model || '').trim() || (provider === 'gemini_cli' ? 'gemini-cli-default' : provider === 'opencode' ? OPENCODE_DEFAULT_MODEL : ''),
    api_key_source: provider === 'gemini_cli' ? 'gemini-cli' : provider === 'opencode' ? 'opencode' : (draft.api_key_source || '').trim(),
    gemini_cli_proxy: provider === 'gemini_cli' ? (draft.gemini_cli_proxy || '').trim() || null : null,
  }
}

function normalizeProfileDraftForProvider() {
  const draft = profileDraft.value
  if (draft.provider_name === 'openai') {
    if (!draft.api_key_source || ['gemini', 'gemini-cli', 'opencode'].includes(draft.api_key_source)) {
      draft.api_key_source = 'env:OPENAI_API_KEY'
    }
    if (!draft.wire_api) draft.wire_api = 'chat_completions'
    if (draft.model.startsWith('gemini') || draft.model.startsWith('opencode/')) draft.model = ''
    return
  }
  if (draft.provider_name === 'gemini') {
    if (!draft.api_key_source || ['codex', 'gemini-cli', 'opencode'].includes(draft.api_key_source)) {
      draft.api_key_source = 'env:GEMINI_API_KEY'
    }
    draft.wire_api = 'responses'
    if (draft.model.startsWith('gpt-') || draft.model.startsWith('opencode/')) draft.model = ''
    return
  }
  if (draft.provider_name === 'gemini_cli') {
    draft.api_key_source = 'gemini-cli'
    draft.base_url = null
    draft.wire_api = 'responses'
    if (!draft.model || draft.model.startsWith('gpt-') || draft.model.startsWith('opencode/')) {
      draft.model = 'gemini-cli-default'
    }
    return
  }
  draft.api_key_source = 'opencode'
  draft.base_url = null
  draft.wire_api = 'responses'
  if (!draft.model || draft.model.startsWith('gpt-') || draft.model.startsWith('gemini')) {
    draft.model = OPENCODE_DEFAULT_MODEL
  }
}

async function loadProfiles() {
  const seq = ++profileStateSeq
  loadingProfiles.value = true
  profileError.value = ''
  try {
    const result = await settingsApi.listAiProfiles()
    if (seq !== profileStateSeq) return
    aiProfiles.value = result.profiles
  } catch (e) {
    if (seq !== profileStateSeq) return
    profileError.value = errorMessage(e)
  } finally {
    if (seq === profileStateSeq) loadingProfiles.value = false
  }
}

function startCreateProfile() {
  profileEditorOpen.value = true
  editingProfileId.value = null
  profileDraft.value = createEmptyProfileDraft()
  profileNotice.value = ''
  profileError.value = ''
  profileTestResult.value = null
  profileModelFetchResult.value = null
}

function startEditProfile(profile: AiProfile) {
  profileEditorOpen.value = true
  editingProfileId.value = profile.id
  profileDraft.value = profileToDraft(profile)
  profileNotice.value = ''
  profileError.value = ''
  profileTestResult.value = null
  profileModelFetchResult.value = null
}

function cancelProfileEdit() {
  profileEditorOpen.value = false
  editingProfileId.value = null
  profileDraft.value = createEmptyProfileDraft()
  profileError.value = ''
  profileTestResult.value = null
  profileModelFetchResult.value = null
}

async function saveProfile() {
  savingProfile.value = true
  profileNotice.value = ''
  profileError.value = ''
  profileTestResult.value = null
  profileModelFetchResult.value = null
  try {
    const update = profileDraftToSettingsUpdate()
    const payload: AiProfileCreate = {
      name: profileDraft.value.name.trim(),
      provider_name: update.provider_name,
      base_url: update.base_url,
      wire_api: update.wire_api,
      model: update.model,
      api_key_source: update.api_key_source,
      gemini_cli_proxy: update.gemini_cli_proxy,
      enabled: profileDraft.value.enabled ?? true,
      source_key: profileDraft.value.source_key ?? null,
    }
    if (!payload.name) {
      profileError.value = t('settings.aiProfileNameRequired')
      return
    }
    if (!payload.model) {
      profileError.value = t('settings.aiProfileModelRequired')
      return
    }
    if (editingProfileId.value) {
      await settingsApi.updateAiProfile(editingProfileId.value, payload)
      profileNotice.value = t('settings.aiProfileUpdated')
    } else {
      await settingsApi.createAiProfile(payload)
      profileNotice.value = t('settings.aiProfileCreated')
    }
    await loadProfiles()
    syncDiscoveredProfilesWithSavedProfiles()
    cancelProfileEdit()
  } catch (e) {
    profileError.value = errorMessage(e)
  } finally {
    savingProfile.value = false
  }
}

async function deleteProfile(profile: AiProfile) {
  if (!window.confirm(t('settings.aiProfileDeleteConfirm', { name: profile.name }))) return
  const seq = ++profileStateSeq
  loadingProfiles.value = false
  profileError.value = ''
  profileNotice.value = ''
  try {
    await settingsApi.deleteAiProfile(profile.id)
    if (seq !== profileStateSeq) return
    aiProfiles.value = aiProfiles.value.filter((item) => item.id !== profile.id)
    syncDiscoveredProfilesWithSavedProfiles()
    if (editingProfileId.value === profile.id) cancelProfileEdit()
    profileNotice.value = t('settings.aiProfileDeleted')
  } catch (e) {
    if (seq !== profileStateSeq) return
    profileError.value = errorMessage(e)
  }
}

async function discoverProfiles() {
  discoveringProfiles.value = true
  profileError.value = ''
  try {
    discoveredProfiles.value = await settingsApi.discoverAiProfiles()
    syncDiscoveredProfilesWithSavedProfiles()
  } catch (e) {
    profileError.value = errorMessage(e)
    discoveredProfiles.value = []
  } finally {
    discoveringProfiles.value = false
  }
}

async function importLocalProfiles(sourceKeys: string[] = []) {
  const seq = ++profileStateSeq
  importingLocalProfiles.value = true
  loadingProfiles.value = false
  profileError.value = ''
  profileNotice.value = ''
  try {
    const result = await settingsApi.importLocalAiProfiles(sourceKeys, true)
    if (seq !== profileStateSeq) return
    aiProfiles.value = result.profiles
    syncDiscoveredProfilesWithSavedProfiles()
    const changed = result.imported_count + result.updated_count
    if (changed > 0) {
      profileNotice.value = t('settings.localProfilesImported', {
        imported: result.imported_count,
        updated: result.updated_count,
      })
    } else if (result.skipped.length) {
      profileNotice.value = result.skipped.join('；')
    } else {
      profileNotice.value = t('settings.localProfilesNoChanges')
    }
  } catch (e) {
    if (seq !== profileStateSeq) return
    profileError.value = errorMessage(e)
  } finally {
    if (seq === profileStateSeq) {
      importingLocalProfiles.value = false
      loadingProfiles.value = false
    }
  }
}

function syncDiscoveredProfilesWithSavedProfiles() {
  if (!discoveredProfiles.value.length) return
  discoveredProfiles.value = discoveredProfiles.value.map((candidate) => ({
    ...candidate,
    existing_profile_id:
      aiProfiles.value.find((profile) =>
        (profile.source_key && profile.source_key === candidate.source_key)
        || (
          profile.provider_name === candidate.provider_name
          && (profile.base_url ?? '') === (candidate.base_url ?? '')
          && (profile.wire_api ?? '') === (candidate.wire_api ?? '')
          && profile.model === candidate.model
          && profile.api_key_source === candidate.api_key_source
        )
      )?.id ?? null,
  }))
}

function removeDiscoveredProfile(sourceKey: string) {
  discoveredProfiles.value = discoveredProfiles.value.filter((candidate) => candidate.source_key !== sourceKey)
}

function clearDiscoveredProfiles() {
  discoveredProfiles.value = []
}

function fillDraftFromDiscovered(candidate: AiDiscoveredProfile) {
  profileEditorOpen.value = true
  editingProfileId.value = candidate.existing_profile_id ?? null
  profileDraft.value = {
    name: candidate.name,
    provider_name: candidate.provider_name,
    base_url: candidate.base_url ?? '',
    wire_api: candidate.wire_api || (candidate.provider_name === 'openai' ? 'chat_completions' : 'responses'),
    model: candidate.model,
    api_key_source: candidate.api_key_source,
    gemini_cli_proxy: candidate.gemini_cli_proxy ?? null,
    enabled: candidate.enabled,
    source_key: candidate.source_key,
  }
  profileNotice.value = ''
  profileError.value = ''
  profileTestResult.value = null
  profileModelFetchResult.value = null
}

async function focusRequestedSection() {
  if (route.query.section !== 'ai_profiles') return
  await nextTick()
  aiProfilesSectionRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

async function toggleProfileEnabled(profile: AiProfile) {
  const seq = ++profileStateSeq
  loadingProfiles.value = false
  profileError.value = ''
  profileNotice.value = ''
  try {
    const updated = await settingsApi.updateAiProfile(profile.id, { enabled: !profile.enabled })
    if (seq !== profileStateSeq) return
    aiProfiles.value = aiProfiles.value.map((item) => item.id === updated.id ? updated : item)
  } catch (e) {
    if (seq !== profileStateSeq) return
    profileError.value = errorMessage(e)
  }
}

async function testProfileLive() {
  testingProfile.value = true
  profileTestResult.value = null
  profileError.value = ''
  profileNotice.value = ''
  try {
    const result = await settingsApi.testAiSettingsLive(profileDraftToSettingsUpdate())
    profileTestResult.value = {
      ...result,
      success: result.ok,
    }
  } catch (e) {
    profileTestResult.value = {
      ok: false,
      success: false,
      message: errorMessage(e),
      provider: profileDraft.value.provider_name,
      model: profileDraft.value.model,
      transport: null,
      elapsed_ms: null,
      preview: '',
      cost: null,
    }
  } finally {
    testingProfile.value = false
  }
}

async function fetchProfileModels() {
  fetchingProfileModels.value = true
  profileModelFetchResult.value = null
  profileError.value = ''
  profileNotice.value = ''
  try {
    const update = profileDraftToSettingsUpdate()
    const result = await settingsApi.getAiModels(update.provider_name, true, update)
    profileModelPresets.value = {
      ...profileModelPresets.value,
      [update.provider_name]: result.models,
    }
    profileModelFetchResult.value = {
      ...result,
      success: result.source === 'live',
    }
    if (!profileDraft.value.model.trim() && result.models.length > 0) {
      profileDraft.value.model = result.models[0]
    }
  } catch (e) {
    profileModelFetchResult.value = {
      provider: profileDraft.value.provider_name,
      models: [],
      source: 'preset',
      success: false,
      message: errorMessage(e),
    }
  } finally {
    fetchingProfileModels.value = false
  }
}

async function saveSettings() {
  savingSettings.value = true
  saveNotice.value = ''
  saveError.value = ''
  testResult.value = null
  liveTestResult.value = null
  modelFetchResult.value = null
  try {
    const saved = await settingsApi.saveAiSettings(buildAiSettingsUpdate())
    applyAiSettings(saved)
    closeBehaviorNotice.value = ''
    const requestedCloseBehavior = settings.closeBehavior
    const effectiveCloseBehavior = await settings.saveCloseBehavior(requestedCloseBehavior)
    if (effectiveCloseBehavior !== requestedCloseBehavior) {
      closeBehaviorNotice.value = t('settings.closeBehaviorTrayUnavailable')
    }
    saveNotice.value = t('settings.saved')
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : String(e)
  } finally {
    savingSettings.value = false
  }
}

async function testConnection() {
  testingConnection.value = true
  testResult.value = null
  liveTestResult.value = null
  modelFetchResult.value = null
  saveNotice.value = ''
  saveError.value = ''
  try {
    const result = await settingsApi.testAiSettings(buildAiSettingsUpdate())
    testResult.value = {
      success: result.ok,
      message: result.ok
        ? t('settings.configCheckPassed')
        : result.message,
    }
  } catch (e) {
    testResult.value = { success: false, message: e instanceof Error ? e.message : String(e) }
  } finally {
    testingConnection.value = false
  }
}

async function testLiveConnection() {
  testingLiveConnection.value = true
  testResult.value = null
  liveTestResult.value = null
  saveNotice.value = ''
  saveError.value = ''
  try {
    const result = await settingsApi.testAiSettingsLive(buildAiSettingsUpdate())
    liveTestResult.value = {
      ...result,
      success: result.ok,
    }
    if (result.ok) settings.markOnboardingAiReviewed()
  } catch (e) {
    liveTestResult.value = {
      ok: false,
      success: false,
      message: errorMessage(e),
      provider: aiProvider.value,
      model: model.value,
      transport: null,
      elapsed_ms: null,
      preview: '',
      cost: null,
    }
  } finally {
    testingLiveConnection.value = false
  }
}

async function importCodex() {
  importing.value = 'codex'
  saveNotice.value = ''
  saveError.value = ''
  try {
    const result = await settingsApi.importCodexSettings()
    applyAiSettings(result.config)
    saveNotice.value = t('settings.importedCodex')
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : String(e)
  } finally {
    importing.value = null
  }
}

async function importGemini() {
  importing.value = 'gemini'
  saveNotice.value = ''
  saveError.value = ''
  try {
    const result = await settingsApi.importGeminiSettings()
    applyAiSettings(result.config)
    saveNotice.value = t('settings.importedGemini')
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : String(e)
  } finally {
    importing.value = null
  }
}

function choosePreset(value: string) {
  if (value) model.value = value
}

async function fetchModels() {
  fetchingModels.value = true
  modelFetchResult.value = null
  saveNotice.value = ''
  saveError.value = ''
  try {
    const result = await settingsApi.getAiModels(aiProvider.value, true, buildAiSettingsUpdate())
    fetchedModelPresets.value = {
      ...fetchedModelPresets.value,
      [aiProvider.value]: result.models,
    }
    modelFetchResult.value = {
      ...result,
      success: result.source === 'live',
    }
    if (!model.value.trim() && result.models.length > 0) {
      model.value = result.models[0]
    }
  } catch (e) {
    modelFetchResult.value = {
      provider: aiProvider.value,
      models: [],
      source: 'preset',
      success: false,
      message: errorMessage(e),
    }
  } finally {
    fetchingModels.value = false
  }
}

function resetWelcomeChecklist() {
  settings.resetWelcomeChecklist()
  saveNotice.value = t('settings.welcomeChecklistReset')
}

async function invokeNative<T>(command: string, args?: Record<string, unknown>): Promise<T> {
  const { invoke } = await import('@tauri-apps/api/core')
  return invoke<T>(command, args)
}

async function loadDataLocation() {
  loadingDataLocation.value = true
  dataLocationError.value = ''
  dataLocationUnsupported.value = false
  try {
    const supportsDataLocation = await backendSupports('data_location')
    if (supportsDataLocation === false) {
      dataLocation.value = null
      dataLocationUnsupported.value = true
      return
    }
    const [info, native] = await Promise.all([
      settingsApi.getDataLocation(),
      invokeNative<DataDirectoryOverrideState>('get_data_directory_override').catch(() => null),
    ])
    dataLocation.value = info
    dataOverride.value = native
    selectedDataDir.value = native?.active_path || native?.override_path || ''
  } catch (e) {
    if (isHttpStatus(e, 404)) {
      dataLocation.value = null
      dataLocationUnsupported.value = true
    } else {
      dataLocationError.value = errorMessage(e)
    }
  } finally {
    loadingDataLocation.value = false
  }
}

async function backendSupports(capability: string): Promise<boolean | null> {
  try {
    const info = await appApi.getVersion()
    return info.capabilities.includes(capability)
  } catch (e) {
    if (isHttpStatus(e, 404)) return false
    return null
  }
}

async function chooseDataDirectory() {
  dataLocationError.value = ''
  dataLocationNotice.value = ''
  try {
    const picked = await invokeNative<string | null>('choose_data_directory')
    if (picked) {
      selectedDataDir.value = picked
      dataLocationNotice.value = t('settings.dataLocationSelected')
    }
  } catch (e) {
    dataLocationError.value = errorMessage(e)
  }
}

async function openDataPath(path?: string | null, kind: 'data' | 'backup' = 'data') {
  if (!path) return
  dataLocationError.value = ''
  dataLocationNotice.value = ''
  try {
    await invokeNative<void>('open_path', { path })
    dataLocationNotice.value = kind === 'backup'
      ? t('settings.backupDirectoryOpened')
      : t('settings.dataDirectoryOpened')
  } catch (e) {
    dataLocationError.value = errorMessage(e)
  }
}

async function restartAfterDataLocationChange() {
  window.setTimeout(() => {
    void invokeNative<void>('restart_app').catch((e) => {
      dataLocationError.value = errorMessage(e)
    })
  }, 900)
}

async function restartAppNow() {
  dataLocationError.value = ''
  dataLocationNotice.value = t('settings.restartRequested')
  try {
    await invokeNative<void>('restart_app')
  } catch (e) {
    dataLocationError.value = errorMessage(e)
  }
}

async function migrateToSelectedDirectory() {
  const target = selectedDataDir.value.trim()
  if (!target) {
    dataLocationError.value = t('settings.dataLocationChooseFirst')
    return
  }
  if (!window.confirm(t('settings.dataLocationMigrateConfirm'))) return
  migratingDataLocation.value = true
  dataLocationNotice.value = ''
  dataLocationError.value = ''
  try {
    const result = await settingsApi.migrateDataLocation({ target_dir: target })
    await invokeNative<DataDirectoryOverrideState>('set_data_directory_override', { path: result.target_dir })
    dataLocationNotice.value = t('settings.dataLocationMigrated')
    await restartAfterDataLocationChange()
  } catch (e) {
    dataLocationError.value = errorMessage(e)
  } finally {
    migratingDataLocation.value = false
  }
}

async function restoreDefaultDataDirectory() {
  if (!dataLocation.value) return
  if (!dataLocation.value.is_custom) {
    dataLocationNotice.value = t('settings.dataLocationAlreadyDefault')
    return
  }
  if (!window.confirm(t('settings.dataLocationRestoreConfirm'))) return
  migratingDataLocation.value = true
  dataLocationNotice.value = ''
  dataLocationError.value = ''
  try {
    await settingsApi.migrateDataLocation({
      target_dir: dataLocation.value.default_data_dir,
      replace_existing: true,
    })
    await invokeNative<DataDirectoryOverrideState>('clear_data_directory_override')
    dataLocationNotice.value = t('settings.dataLocationRestored')
    await restartAfterDataLocationChange()
  } catch (e) {
    dataLocationError.value = errorMessage(e)
  } finally {
    migratingDataLocation.value = false
  }
}

async function checkForUpdates() {
  updateActionError.value = ''
  try {
    await appUpdate.checkForUpdates({ force: true, source: 'manual' })
  } catch (e) {
    updateActionError.value = errorMessage(e)
  }
}

async function openLatestInstaller() {
  updateActionError.value = ''
  try {
    await appUpdate.openDownload()
  } catch (e) {
    updateActionError.value = errorMessage(e)
  }
}

async function downloadAndInstallLatest() {
  updateActionError.value = ''
  try {
    await appUpdate.downloadAndInstall()
  } catch (e) {
    updateActionError.value = errorMessage(e)
  }
}

async function openReleasePage() {
  updateActionError.value = ''
  try {
    await appUpdate.openReleasePage()
  } catch (e) {
    updateActionError.value = errorMessage(e)
  }
}
</script>

<template>
  <div class="flex h-full flex-col overflow-y-auto bg-gray-50">
    <div class="mx-auto w-full max-w-4xl space-y-6 p-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">{{ t('settings.title') }}</h1>
        <p class="mt-1 text-sm text-gray-500">{{ t('settings.subtitle') }}</p>
      </div>

      <section class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <div class="mb-4 flex items-center justify-between gap-3">
          <h2 class="text-lg font-bold text-gray-900">{{ t('settings.aiConfig') }}</h2>
          <span v-if="loadingAiSettings" class="text-sm text-gray-400">{{ t('common.loading') }}</span>
        </div>

        <div v-if="saveError" class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{{ saveError }}</div>
        <div v-if="saveNotice" class="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-700">{{ saveNotice }}</div>

        <div class="space-y-5">
          <div>
            <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('settings.provider') }}</label>
            <select
              v-model="aiProvider"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option v-for="provider in providerOptions" :key="provider.value" :value="provider.value">
                {{ provider.label }}
              </option>
            </select>
          </div>

          <div v-if="aiProvider !== 'gemini_cli' && aiProvider !== 'opencode'">
            <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('settings.baseUrl') }}</label>
            <input
              v-model="baseUrl"
              type="text"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
              :placeholder="aiProvider === 'gemini' ? 'https://generativelanguage.googleapis.com' : 'https://api.openai.com/v1'"
            />
            <p class="mt-1 text-xs text-gray-500">{{ t('settings.baseUrlHelp') }}</p>
          </div>

          <div>
            <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('settings.model') }}</label>
            <div class="grid gap-3 md:grid-cols-[1fr_220px_auto]">
              <input
                v-model="model"
                type="text"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
                :placeholder="aiProvider === 'openai' ? 'gpt-4o-mini' : aiProvider === 'gemini' ? 'gemini-2.5-flash' : aiProvider === 'opencode' ? OPENCODE_DEFAULT_MODEL : 'gemini-cli-default'"
              />
              <select
                :value="modelPresets.includes(model) ? model : ''"
                @change="choosePreset(($event.target as HTMLSelectElement).value)"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">{{ t('settings.customModel') }}</option>
                <option v-for="preset in modelPresets" :key="preset" :value="preset">{{ preset }}</option>
              </select>
              <button
                @click="fetchModels"
                :disabled="fetchingModels"
                class="rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-40"
              >
                {{ fetchingModels ? t('settings.fetchingModels') : t('settings.fetchModels') }}
              </button>
            </div>
            <div
              v-if="modelFetchResult"
              :class="[
                'mt-2 rounded-lg p-3 text-sm',
                modelFetchResult.success ? 'bg-green-50 text-green-800' : 'bg-amber-50 text-amber-800',
              ]"
            >
              {{ modelFetchResult.message }}
            </div>
          </div>

          <div v-if="aiProvider !== 'gemini_cli' && aiProvider !== 'opencode'">
            <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('settings.credentialSource') }}</label>
            <select
              v-model="apiKeySource"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option v-for="option in credentialOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
            <p class="mt-1 text-xs text-gray-500">{{ t('settings.credentialHelp') }}</p>
          </div>

          <div v-else-if="aiProvider === 'gemini_cli'">
            <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('settings.geminiCliProxy') }}</label>
            <input
              v-model="geminiCliProxy"
              type="text"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="http://127.0.0.1:7890"
            />
            <p class="mt-1 text-xs text-gray-500">{{ t('settings.geminiCliHelp') }}</p>
          </div>

          <div v-else class="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm leading-6 text-gray-600">
            {{ t('settings.openCodeHelp') }}
          </div>

          <div class="rounded-xl border border-gray-200 bg-gray-50 p-4">
            <div class="flex items-center justify-between gap-3">
              <div>
                <div class="text-sm font-semibold text-gray-800">{{ t('settings.credentialStatus') }}</div>
                <div :class="['mt-1 text-sm', activeStatus?.available ? 'text-green-700' : 'text-amber-700']">
                  {{ statusLabel }}
                </div>
              </div>
              <div class="flex flex-wrap justify-end gap-2">
                <button
                  v-if="aiProvider === 'openai'"
                  @click="importCodex"
                  :disabled="importing !== null"
                  class="rounded-lg bg-gray-900 px-3 py-2 text-sm font-semibold text-white hover:bg-gray-700 disabled:opacity-40"
                >
                  {{ importing === 'codex' ? t('common.loading') : t('settings.importCodex') }}
                </button>
                <button
                  v-if="aiProvider === 'gemini'"
                  @click="importGemini"
                  :disabled="importing !== null"
                  class="rounded-lg bg-gray-900 px-3 py-2 text-sm font-semibold text-white hover:bg-gray-700 disabled:opacity-40"
                >
                  {{ importing === 'gemini' ? t('common.loading') : t('settings.importGemini') }}
                </button>
                <button
                  @click="testConnection"
                  :disabled="testingConnection"
                  class="rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-40"
                >
                  {{ testingConnection ? t('settings.testing') : t('settings.testConnection') }}
                </button>
                <button
                  @click="testLiveConnection"
                  :disabled="testingLiveConnection"
                  class="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-40"
                >
                  {{ testingLiveConnection ? t('settings.liveTesting') : t('settings.testLiveConnection') }}
                </button>
              </div>
            </div>
            <pre v-if="statusDetail" class="mt-3 whitespace-pre-wrap text-xs leading-5 text-gray-500">{{ statusDetail }}</pre>
            <div
              v-if="testResult"
              :class="[
                'mt-3 rounded-lg p-3 text-sm',
                testResult.success ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800',
              ]"
            >
              {{ testResult.message }}
            </div>
            <div
              v-if="liveTestResult"
              :class="[
                'mt-3 rounded-lg p-3 text-sm',
                liveTestResult.success ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800',
              ]"
            >
              <div>{{ liveTestResult.message }}</div>
              <div v-if="liveTestResult.preview" class="mt-1 text-xs opacity-80">
                {{ t('settings.liveTestPreview') }}：{{ liveTestResult.preview }}
              </div>
              <div v-if="liveTestResult.cost !== undefined && liveTestResult.cost !== null" class="mt-1 text-xs opacity-80">
                {{ t('settings.liveTestCost') }}：{{ liveTestResult.cost }}
              </div>
            </div>
          </div>

          <section data-testid="ai-diagnostics-panel" class="rounded-2xl border border-slate-200 bg-white p-4">
            <div class="mb-3 flex items-start justify-between gap-3">
              <div>
                <h3 class="text-sm font-semibold text-slate-900">{{ t('settings.diagnostics.title') }}</h3>
                <p class="mt-1 text-xs leading-5 text-slate-500">{{ t('settings.diagnostics.help') }}</p>
              </div>
              <span class="shrink-0 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
                {{ liveTestResult?.success ? t('settings.diagnostics.ready') : t('settings.diagnostics.needsTest') }}
              </span>
            </div>
            <div class="grid gap-2 md:grid-cols-2">
              <article
                v-for="row in diagnosticRows"
                :key="row.label"
                :class="['rounded-xl border p-3', diagnosticToneClass(row.tone)]"
              >
                <div class="text-xs font-semibold opacity-70">{{ row.label }}</div>
                <div class="mt-1 break-words text-sm font-semibold">{{ row.value }}</div>
                <p v-if="row.detail" class="mt-1 line-clamp-2 break-words text-xs leading-5 opacity-70">{{ row.detail }}</p>
              </article>
            </div>
          </section>
        </div>
      </section>

      <section ref="aiProfilesSectionRef" class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <div class="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 class="text-lg font-bold text-gray-900">{{ t('settings.aiProfiles') }}</h2>
            <p class="mt-1 text-sm leading-6 text-gray-500">{{ t('settings.aiProfilesHelp') }}</p>
          </div>
          <div class="flex shrink-0 flex-wrap justify-end gap-2">
            <button
              @click="discoverProfiles"
              :disabled="discoveringProfiles"
              class="rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-40"
            >
              {{ discoveringProfiles ? t('settings.scanningLocalProfiles') : t('settings.scanLocalProfiles') }}
            </button>
            <button
              @click="startCreateProfile"
              class="rounded-lg bg-gray-900 px-3 py-2 text-sm font-semibold text-white hover:bg-gray-700"
            >
              {{ t('settings.addAiProfile') }}
            </button>
          </div>
        </div>

        <div v-if="profileError" class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{{ profileError }}</div>
        <div v-if="profileNotice" class="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-700">{{ profileNotice }}</div>

        <div class="mb-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 class="text-sm font-semibold text-slate-900">{{ t('settings.localProfileDiscovery') }}</h3>
              <p class="mt-1 text-xs leading-5 text-slate-500">{{ t('settings.localProfileDiscoveryHelp') }}</p>
            </div>
            <div class="flex flex-wrap gap-2">
              <button
                v-if="discoveredProfiles.length"
                @click="clearDiscoveredProfiles"
                class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50"
              >
                {{ t('settings.clearDiscoveredProfiles') }}
              </button>
              <button
                @click="importLocalProfiles()"
                :disabled="importingLocalProfiles || !discoveredProfiles.some((item) => item.available)"
                class="rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-700 disabled:opacity-40"
              >
                {{ importingLocalProfiles ? t('common.saving') : t('settings.importAllLocalProfiles') }}
              </button>
            </div>
          </div>
          <div v-if="discoveringProfiles && !discoveredProfiles.length" class="rounded-lg bg-white p-3 text-sm text-slate-500">
            {{ t('settings.scanningLocalProfiles') }}
          </div>
          <div v-else-if="!discoveredProfiles.length" class="rounded-lg border border-dashed border-slate-200 bg-white p-4 text-sm leading-6 text-slate-500">
            {{ t('settings.noDiscoveredProfiles') }}
          </div>
          <div v-else class="grid gap-3 lg:grid-cols-3">
            <article
              v-for="candidate in discoveredProfiles"
              :key="candidate.source_key"
              :class="[
                'rounded-xl border bg-white p-3 shadow-sm',
                candidate.available ? 'border-emerald-100' : 'border-amber-100',
              ]"
            >
              <div class="flex items-start justify-between gap-2">
                <div class="min-w-0">
                  <div class="text-xs font-semibold uppercase tracking-wide text-slate-400">{{ candidate.source_label }}</div>
                  <h4 class="mt-1 truncate text-sm font-semibold text-slate-900">{{ candidate.name }}</h4>
                  <p class="mt-1 break-all text-xs leading-5 text-slate-500">
                    {{ candidate.provider_name }} · {{ candidate.model }}
                  </p>
                </div>
                <span
                  :class="[
                    'shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold',
                    candidate.available ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-800',
                  ]"
                >
                  {{ candidate.available ? t('settings.importable') : t('settings.unavailable') }}
                </span>
              </div>
              <p v-if="candidate.reason" class="mt-2 line-clamp-2 text-xs leading-5 text-amber-800">{{ candidate.reason }}</p>
              <div class="mt-3 flex flex-wrap gap-2">
                <button
                  @click="importLocalProfiles([candidate.source_key])"
                  :disabled="importingLocalProfiles || !candidate.available"
                  class="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-40"
                >
                  {{ candidate.existing_profile_id ? t('settings.updateProfile') : t('settings.importProfile') }}
                </button>
                <button
                  @click="fillDraftFromDiscovered(candidate)"
                  class="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  {{ t('settings.fillProfileDraft') }}
                </button>
                <button
                  @click="removeDiscoveredProfile(candidate.source_key)"
                  class="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-500 hover:bg-slate-50"
                >
                  {{ t('settings.removeDiscoveredProfile') }}
                </button>
              </div>
            </article>
          </div>
        </div>

        <div v-if="loadingProfiles" class="rounded-lg bg-gray-50 p-4 text-sm text-gray-500">{{ t('common.loading') }}</div>
        <div v-else-if="!aiProfiles.length" class="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-4 text-sm leading-6 text-gray-500">
          {{ t('settings.noAiProfiles') }}
        </div>
        <div v-else class="grid gap-3">
          <article
            v-for="profile in aiProfiles"
            :key="profile.id"
            class="rounded-xl border border-gray-200 bg-gray-50 p-4"
          >
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="flex flex-wrap items-center gap-2">
                  <h3 class="font-semibold text-gray-900">{{ profile.name }}</h3>
                  <span
                    :class="[
                      'rounded-full px-2 py-0.5 text-xs font-semibold',
                      profile.enabled ? 'bg-green-100 text-green-700' : 'bg-gray-200 text-gray-600',
                    ]"
                  >
                    {{ profile.enabled ? t('settings.enabled') : t('settings.disabled') }}
                  </span>
                </div>
                <p class="mt-1 break-all text-sm text-gray-600">
                  {{ providerOptions.find((item) => item.value === profile.provider_name)?.label || profile.provider_name }}
                  · {{ profile.model }}
                  <span v-if="profile.provider_name === 'openai'"> · {{ profile.wire_api === 'chat_completions' ? 'Chat Completions' : 'Responses' }}</span>
                </p>
              </div>
              <div class="flex flex-wrap gap-2">
                <button
                  @click="toggleProfileEnabled(profile)"
                  class="rounded-lg border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-white"
                >
                  {{ profile.enabled ? t('settings.disable') : t('settings.enable') }}
                </button>
                <button
                  @click="startEditProfile(profile)"
                  class="rounded-lg bg-white px-3 py-2 text-xs font-semibold text-gray-700 ring-1 ring-gray-200 hover:bg-gray-100"
                >
                  {{ t('common.edit') }}
                </button>
                <button
                  @click="deleteProfile(profile)"
                  class="rounded-lg bg-red-50 px-3 py-2 text-xs font-semibold text-red-700 hover:bg-red-100"
                >
                  {{ t('common.delete') }}
                </button>
              </div>
            </div>
          </article>
        </div>

        <Teleport to="body">
          <div
            v-if="profileEditorOpen"
            class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-5"
            @click.self="cancelProfileEdit"
          >
            <div
              role="dialog"
              aria-modal="true"
              :aria-label="editingProfileId ? t('settings.editAiProfile') : t('settings.newAiProfile')"
              class="flex max-h-[88vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
            >
              <div class="flex items-start justify-between gap-3 border-b border-gray-100 px-5 py-4">
                <div>
                  <h3 class="text-lg font-bold text-gray-950">
                    {{ editingProfileId ? t('settings.editAiProfile') : t('settings.newAiProfile') }}
                  </h3>
                  <p class="mt-1 text-sm text-gray-500">{{ t('settings.aiProfileDialogHelp') }}</p>
                </div>
                <button
                  @click="cancelProfileEdit"
                  class="rounded-lg px-3 py-2 text-sm font-semibold text-gray-500 hover:bg-gray-100 hover:text-gray-800"
                >
                  {{ t('common.cancel') }}
                </button>
              </div>

              <div class="overflow-y-auto px-5 py-4">
                <div v-if="profileError" class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{{ profileError }}</div>

          <div class="grid gap-4 md:grid-cols-2">
            <div>
              <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('settings.aiProfileName') }}</label>
              <input
                v-model="profileDraft.name"
                type="text"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
                :placeholder="t('settings.aiProfileNamePlaceholder')"
              />
            </div>

            <div>
              <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('settings.provider') }}</label>
              <select
                v-model="profileDraft.provider_name"
                @change="normalizeProfileDraftForProvider"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option v-for="provider in providerOptions" :key="provider.value" :value="provider.value">
                  {{ provider.label }}
                </option>
              </select>
            </div>

            <div v-if="profileDraft.provider_name !== 'gemini_cli' && profileDraft.provider_name !== 'opencode'" class="md:col-span-2">
              <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('settings.baseUrl') }}</label>
              <input
                v-model="profileDraft.base_url"
                type="text"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
                :placeholder="profileDraft.provider_name === 'gemini' ? 'https://generativelanguage.googleapis.com' : 'https://api.openai.com/v1'"
              />
            </div>

            <div v-if="profileDraft.provider_name === 'openai'">
              <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('settings.wireApi') }}</label>
              <select
                v-model="profileDraft.wire_api"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="chat_completions">Chat Completions</option>
                <option value="responses">Responses</option>
              </select>
            </div>

            <div :class="profileDraft.provider_name === 'openai' ? '' : 'md:col-span-2'">
              <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('settings.model') }}</label>
              <div class="grid gap-2 md:grid-cols-[1fr_auto]">
                <input
                  v-model="profileDraft.model"
                  type="text"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
                  :placeholder="profileDraft.provider_name === 'openai' ? 'deepseek-chat / gpt-4o-mini' : profileDraft.provider_name === 'gemini' ? 'gemini-2.5-flash' : profileDraft.provider_name === 'opencode' ? OPENCODE_DEFAULT_MODEL : 'gemini-cli-default'"
                />
                <button
                  @click="fetchProfileModels"
                  :disabled="fetchingProfileModels"
                  class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-40"
                >
                  {{ fetchingProfileModels ? t('settings.fetchingModels') : t('settings.fetchModels') }}
                </button>
              </div>
              <select
                :value="profileModelOptions.includes(profileDraft.model) ? profileDraft.model : ''"
                @change="profileDraft.model = ($event.target as HTMLSelectElement).value || profileDraft.model"
                class="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">{{ t('settings.customModel') }}</option>
                <option v-for="preset in profileModelOptions" :key="preset" :value="preset">{{ preset }}</option>
              </select>
              <div
                v-if="profileModelFetchResult"
                :class="[
                  'mt-2 rounded-lg p-3 text-sm',
                  profileModelFetchResult.success ? 'bg-green-50 text-green-800' : 'bg-amber-50 text-amber-800',
                ]"
              >
                {{ profileModelFetchResult.message }}
              </div>
            </div>

            <div v-if="profileDraft.provider_name !== 'gemini_cli' && profileDraft.provider_name !== 'opencode'" class="md:col-span-2">
              <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('settings.credentialSource') }}</label>
              <select
                v-model="profileDraft.api_key_source"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option v-for="option in credentialOptionsFor(profileDraft.provider_name)" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
              <p class="mt-1 text-xs text-gray-500">{{ t('settings.credentialHelp') }}</p>
            </div>

            <div v-else-if="profileDraft.provider_name === 'gemini_cli'" class="md:col-span-2">
              <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('settings.geminiCliProxy') }}</label>
              <input
                v-model="profileDraft.gemini_cli_proxy"
                type="text"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="http://127.0.0.1:7890"
              />
            </div>

            <div v-else class="rounded-lg border border-blue-100 bg-white p-3 text-sm leading-6 text-blue-900 md:col-span-2">
              {{ t('settings.openCodeHelp') }}
            </div>
          </div>

          <label class="mt-4 flex items-center gap-2 text-sm font-semibold text-gray-700">
            <input v-model="profileDraft.enabled" type="checkbox" class="h-4 w-4 rounded border-gray-300" />
            {{ t('settings.aiProfileEnabled') }}
          </label>

          <div
            v-if="profileTestResult"
            :class="[
              'mt-3 rounded-lg p-3 text-sm',
              profileTestResult.success ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800',
            ]"
          >
            <div>{{ profileTestResult.message }}</div>
            <div v-if="profileTestResult.preview" class="mt-1 text-xs opacity-80">
              {{ t('settings.liveTestPreview') }}：{{ profileTestResult.preview }}
            </div>
            <div v-if="profileTestResult.cost !== undefined && profileTestResult.cost !== null" class="mt-1 text-xs opacity-80">
              {{ t('settings.liveTestCost') }}：{{ profileTestResult.cost }}
            </div>
          </div>

          <div class="mt-4 flex flex-wrap justify-end gap-2">
            <button
              @click="cancelProfileEdit"
              class="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
            >
              {{ t('common.cancel') }}
            </button>
            <button
              @click="testProfileLive"
              :disabled="testingProfile"
              class="rounded-lg border border-emerald-200 bg-white px-3 py-2 text-sm font-semibold text-emerald-700 hover:bg-emerald-50 disabled:opacity-40"
            >
              {{ testingProfile ? t('settings.liveTesting') : t('settings.testLiveConnection') }}
            </button>
            <button
              @click="saveProfile"
              :disabled="savingProfile"
              class="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-40"
            >
              {{ savingProfile ? t('common.saving') : t('settings.saveAiProfile') }}
            </button>
          </div>
              </div>
            </div>
          </div>
        </Teleport>
      </section>

      <section class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <div class="mb-4 flex items-center justify-between gap-3">
          <div>
            <h2 class="text-lg font-bold text-gray-900">{{ t('settings.dataStorage') }}</h2>
            <p class="mt-1 text-sm text-gray-500">{{ t('settings.dataStorageHelp') }}</p>
          </div>
          <span v-if="loadingDataLocation" class="text-sm text-gray-400">{{ t('common.loading') }}</span>
        </div>

        <div v-if="dataLocationUnsupported" class="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <div class="font-semibold">{{ t('settings.backendVersionMismatch') }}</div>
          <p class="mt-1 leading-5">{{ t('settings.dataLocationUnsupported') }}</p>
          <p class="mt-1 leading-5">{{ t('settings.reinstallLatestHint') }}</p>
          <button
            @click="restartAppNow"
            class="mt-3 rounded-lg bg-amber-900 px-3 py-2 text-xs font-semibold text-white hover:bg-amber-800"
          >
            {{ t('settings.restartApp') }}
          </button>
        </div>
        <div v-else-if="dataLocationError" class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{{ dataLocationError }}</div>
        <div v-if="dataLocationNotice" class="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-700">{{ dataLocationNotice }}</div>
        <div v-if="dataOverride?.warning || dataLocation?.warning" class="mb-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
          {{ dataOverride?.warning || dataLocation?.warning }}
        </div>

        <div v-if="dataLocation" class="space-y-4">
          <div class="grid gap-3">
            <div class="rounded-lg border border-gray-200 bg-gray-50 p-3">
              <div class="text-xs font-semibold uppercase tracking-wide text-gray-500">{{ t('settings.currentDataDirectory') }}</div>
              <div class="mt-1 break-all text-sm text-gray-900">{{ dataLocation.data_dir }}</div>
            </div>
            <div class="rounded-lg border border-gray-200 bg-gray-50 p-3">
              <div class="text-xs font-semibold uppercase tracking-wide text-gray-500">{{ t('settings.databasePath') }}</div>
              <div class="mt-1 break-all text-sm text-gray-900">{{ dataLocation.database_path }}</div>
            </div>
            <div class="grid gap-3 md:grid-cols-2">
              <div class="rounded-lg border border-gray-200 bg-gray-50 p-3">
                <div class="text-xs font-semibold uppercase tracking-wide text-gray-500">{{ t('settings.backupDirectory') }}</div>
                <div class="mt-1 break-all text-sm text-gray-900">{{ dataLocation.backup_dir }}</div>
              </div>
              <div class="rounded-lg border border-gray-200 bg-gray-50 p-3">
                <div class="text-xs font-semibold uppercase tracking-wide text-gray-500">{{ t('settings.checkpointDirectory') }}</div>
                <div class="mt-1 break-all text-sm text-gray-900">{{ dataLocation.checkpoint_dir }}</div>
              </div>
            </div>
          </div>

          <div class="flex flex-wrap gap-2">
            <button
              @click="openDataPath(dataLocation.data_dir, 'data')"
              class="rounded-lg bg-gray-900 px-3 py-2 text-sm font-semibold text-white hover:bg-gray-700"
            >
              {{ t('settings.openDataDirectory') }}
            </button>
            <button
              @click="openDataPath(dataLocation.backup_dir, 'backup')"
              class="rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
            >
              {{ t('settings.openBackupDirectory') }}
            </button>
          </div>

          <div class="rounded-lg border border-gray-200 p-4">
            <div class="mb-2 flex items-center justify-between gap-3">
              <label class="text-sm font-semibold text-gray-700">{{ t('settings.newDataDirectory') }}</label>
              <span class="rounded-full bg-gray-100 px-2 py-1 text-xs font-semibold text-gray-600">
                {{ dataLocation.is_custom ? t('settings.customDataDirectory') : t('settings.defaultDataDirectory') }}
              </span>
            </div>
            <div class="grid gap-2 md:grid-cols-[1fr_auto]">
              <input
                v-model="selectedDataDir"
                type="text"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
                :placeholder="dataLocation.default_data_dir"
              />
              <button
                @click="chooseDataDirectory"
                class="rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
              >
                {{ t('settings.chooseDataDirectory') }}
              </button>
            </div>
            <p class="mt-2 text-xs leading-5 text-gray-500">{{ t('settings.dataMigrationHelp') }}</p>
            <div class="mt-4 flex flex-wrap gap-2">
              <button
                @click="migrateToSelectedDirectory"
                :disabled="migratingDataLocation"
                class="rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-40"
              >
                {{ migratingDataLocation ? t('settings.dataLocationMigrating') : t('settings.migrateAndSwitch') }}
              </button>
              <button
                @click="restoreDefaultDataDirectory"
                :disabled="migratingDataLocation || !dataLocation.is_custom"
                class="rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-40"
              >
                {{ t('settings.restoreDefaultDataDirectory') }}
              </button>
            </div>
          </div>
        </div>
      </section>

      <section class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h2 class="mb-4 text-lg font-bold text-gray-900">{{ t('settings.interfaceSettings') }}</h2>
        <div class="space-y-4">
          <div>
            <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('settings.language') }}</label>
            <select
              :value="settings.language"
              @change="(e) => { if (settings.language !== (e.target as HTMLSelectElement).value) settings.toggleLanguage() }"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="zh">{{ t('settings.languages.zh') }}</option>
              <option value="en">{{ t('settings.languages.en') }}</option>
            </select>
          </div>

          <div>
            <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('settings.closeBehaviorLabel') }}</label>
            <select
              v-model="settings.closeBehavior"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="ask">{{ t('settings.closeBehaviorAsk') }}</option>
              <option value="tray">{{ t('settings.closeBehaviorTray') }}</option>
              <option value="exit">{{ t('settings.closeBehaviorExit') }}</option>
            </select>
            <p class="mt-1 text-xs text-gray-500">{{ t('settings.closeBehaviorHelp') }}</p>
            <p v-if="closeBehaviorNotice" class="mt-2 text-xs text-amber-700">{{ closeBehaviorNotice }}</p>
          </div>

          <div class="rounded-xl border border-gray-200 bg-gray-50 p-4">
            <div class="flex items-center justify-between gap-3">
              <div>
                <div class="text-sm font-semibold text-gray-800">{{ t('settings.welcomeChecklist') }}</div>
                <p class="mt-1 text-xs leading-5 text-gray-500">{{ t('settings.welcomeChecklistHelp') }}</p>
              </div>
              <button
                @click="resetWelcomeChecklist"
                class="shrink-0 rounded-lg bg-gray-900 px-3 py-2 text-sm font-semibold text-white hover:bg-gray-700"
              >
                {{ t('settings.showWelcomeChecklist') }}
              </button>
            </div>
          </div>
        </div>
      </section>

      <section class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <div class="mb-4">
          <h2 class="text-lg font-bold text-gray-900">{{ t('updates.sectionTitle') }}</h2>
          <p class="mt-1 text-sm text-gray-500">{{ t('updates.sectionHelp') }}</p>
        </div>

        <div class="grid gap-3 md:grid-cols-2">
          <div class="rounded-lg border border-gray-200 bg-gray-50 p-3">
            <div class="text-xs font-semibold uppercase tracking-wide text-gray-500">{{ t('updates.currentVersion') }}</div>
            <div class="mt-1 text-sm text-gray-900">{{ appUpdate.currentVersion || t('updates.notCheckedYet') }}</div>
          </div>
          <div class="rounded-lg border border-gray-200 bg-gray-50 p-3">
            <div class="text-xs font-semibold uppercase tracking-wide text-gray-500">{{ t('updates.latestVersion') }}</div>
            <div class="mt-1 text-sm text-gray-900">
              {{ appUpdate.latestVersion || t('updates.notCheckedYet') }}
            </div>
          </div>
        </div>

        <div
          v-if="appUpdate.status !== 'idle' || updateActionError"
          :class="[
            'mt-4 rounded-lg p-3 text-sm',
            updateActionError || appUpdate.status === 'error'
              ? 'bg-red-50 text-red-700'
              : appUpdate.status === 'update_available'
                ? 'bg-amber-50 text-amber-800'
                : appUpdate.status === 'up_to_date'
                  ? 'bg-green-50 text-green-700'
                  : 'bg-gray-100 text-gray-700',
          ]"
        >
          {{ updateActionError || appUpdate.message || t('updates.checking') }}
        </div>

        <div class="mt-4 flex flex-wrap gap-2">
          <button
            @click="checkForUpdates"
            :disabled="appUpdate.status === 'checking'"
            class="rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-40"
          >
            {{ appUpdate.status === 'checking' ? t('updates.checkingButton') : t('updates.checkNow') }}
          </button>
          <button
            @click="downloadAndInstallLatest"
            :disabled="!appUpdate.downloadUrl || appUpdate.downloadStatus === 'downloading' || appUpdate.downloadStatus === 'installing'"
            class="rounded-lg bg-gray-900 px-3 py-2 text-sm font-semibold text-white hover:bg-gray-700 disabled:opacity-40"
          >
            {{ appUpdate.downloadStatus === 'downloading' ? t('updates.downloadingInstaller') : appUpdate.downloadStatus === 'installing' ? t('updates.startingInstaller') : t('updates.downloadAndInstall') }}
          </button>
          <button
            @click="openLatestInstaller"
            :disabled="!appUpdate.downloadUrl && !appUpdate.releaseUrl"
            class="rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-40"
          >
            {{ t('updates.downloadInBrowser') }}
          </button>
          <button
            @click="openReleasePage"
            :disabled="!appUpdate.releaseUrl && !appUpdate.downloadUrl"
            class="rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-40"
          >
            {{ t('updates.viewRelease') }}
          </button>
          <button
            v-if="appUpdate.status === 'update_available'"
            @click="appUpdate.dismissUpdate()"
            class="rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
          >
            {{ t('updates.later') }}
          </button>
        </div>

        <div class="mt-4 space-y-3 text-sm text-gray-600">
          <div v-if="appUpdate.releaseName">
            <span class="font-semibold text-gray-800">{{ t('updates.releaseName') }}：</span>{{ appUpdate.releaseName }}
          </div>
          <div v-if="appUpdate.publishedAt">
            <span class="font-semibold text-gray-800">{{ t('updates.publishedAt') }}：</span>{{ appUpdate.publishedAt }}
          </div>
          <div v-if="appUpdate.checkedAt">
            <span class="font-semibold text-gray-800">{{ t('updates.lastCheckedAt') }}：</span>{{ appUpdate.checkedAt }}
          </div>
          <div v-if="appUpdate.downloadName">
            <span class="font-semibold text-gray-800">{{ t('updates.preferredInstaller') }}：</span>{{ appUpdate.downloadName }}
          </div>
          <div v-if="appUpdate.downloadSha256">
            <span class="font-semibold text-gray-800">SHA256：</span>{{ appUpdate.downloadSha256 }}
          </div>
          <div v-if="appUpdate.networkProxy">
            <span class="font-semibold text-gray-800">{{ t('updates.networkProxy') }}：</span>{{ appUpdate.networkProxy }}
          </div>
          <div v-if="appUpdate.downloadMessage">
            <span class="font-semibold text-gray-800">{{ t('updates.updateProgress') }}：</span>{{ appUpdate.downloadMessage }}
          </div>
          <p class="leading-6 text-gray-500">{{ t('updates.manualInstallerHint') }}</p>
        </div>

        <div v-if="appUpdate.releaseNotes" class="mt-4 rounded-lg border border-gray-200 bg-gray-50 p-4">
          <div class="text-sm font-semibold text-gray-800">{{ t('updates.releaseNotes') }}</div>
          <pre class="mt-2 max-h-64 overflow-y-auto whitespace-pre-wrap text-xs leading-6 text-gray-600">{{ appUpdate.releaseNotes }}</pre>
        </div>
      </section>

      <div class="flex justify-end">
        <button
          @click="saveSettings"
          :disabled="savingSettings"
          class="rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white transition-colors hover:bg-blue-700 disabled:opacity-40"
        >
          {{ savingSettings ? t('common.saving') : t('settings.save') }}
        </button>
      </div>
    </div>
  </div>
</template>
