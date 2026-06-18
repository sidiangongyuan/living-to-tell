<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { appApi } from '../../api/app'
import { errorMessage, isHttpStatus } from '../../api/base'
import { settingsApi, type AiProviderName, type AiSettings, type AiSettingsUpdate, type DataLocationInfo } from '../../api/settings'
import { useI18n } from '../../i18n'
import { useSettingsStore } from '../../stores/settings'

interface DataDirectoryOverrideState {
  override_path?: string | null
  active_path?: string | null
  warning?: string | null
}

const { t } = useI18n()
const settings = useSettingsStore()

const aiProvider = ref<AiProviderName>('openai')
const model = ref('gpt-4o-mini')
const baseUrl = ref('')
const apiKeySource = ref('env:OPENAI_API_KEY')
const geminiCliProxy = ref('')
const aiSettings = ref<AiSettings | null>(null)
const loadingAiSettings = ref(false)
const savingSettings = ref(false)
const testingConnection = ref(false)
const importing = ref<'codex' | 'gemini' | null>(null)
const testResult = ref<{ success: boolean; message: string } | null>(null)
const saveNotice = ref('')
const saveError = ref('')
let applyingAiSettings = false

const closeBehaviorNotice = ref('')
const dataLocation = ref<DataLocationInfo | null>(null)
const dataOverride = ref<DataDirectoryOverrideState | null>(null)
const selectedDataDir = ref('')
const loadingDataLocation = ref(false)
const migratingDataLocation = ref(false)
const dataLocationNotice = ref('')
const dataLocationError = ref('')
const dataLocationUnsupported = ref(false)

const providerOptions = computed<Array<{ value: AiProviderName; label: string }>>(() => [
  { value: 'openai', label: t('settings.providers.openai') },
  { value: 'gemini', label: t('settings.providers.gemini') },
  { value: 'gemini_cli', label: t('settings.providers.geminiCli') },
])

const credentialOptions = computed<Array<{ value: string; label: string }>>(() => {
  if (aiProvider.value === 'gemini') {
    return [
      { value: 'env:GEMINI_API_KEY', label: 'env:GEMINI_API_KEY' },
      { value: 'gemini', label: t('settings.credentialGemini') },
    ]
  }
  if (aiProvider.value === 'gemini_cli') {
    return [{ value: 'gemini-cli', label: t('settings.credentialGeminiCli') }]
  }
  return [
    { value: 'env:OPENAI_API_KEY', label: 'env:OPENAI_API_KEY' },
    { value: 'codex', label: t('settings.credentialCodex') },
  ]
})

const modelPresets = computed(() =>
  aiSettings.value?.model_presets?.[aiProvider.value] ?? []
)

const activeStatus = computed(() => {
  if (!aiSettings.value) return null
  if (aiProvider.value === 'gemini_cli') return aiSettings.value.status.gemini_cli
  if (apiKeySource.value === 'codex') return aiSettings.value.status.codex
  if (apiKeySource.value === 'gemini') return aiSettings.value.status.gemini
  return aiSettings.value.status.env
})

const statusMatchesSavedConfig = computed(() => {
  if (!aiSettings.value) return false
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

onMounted(() => {
  void loadSettings()
  void loadDataLocation()
  void settings.loadNativePreferences()
})

watch(aiProvider, (provider, previous) => {
  if (applyingAiSettings) return
  if (provider === previous) return
  testResult.value = null
  saveNotice.value = ''
  saveError.value = ''
  if (provider === 'openai') {
    apiKeySource.value = 'env:OPENAI_API_KEY'
    if (!model.value || model.value.startsWith('gemini')) model.value = 'gpt-4o-mini'
  } else if (provider === 'gemini') {
    apiKeySource.value = 'env:GEMINI_API_KEY'
    if (!model.value || model.value.startsWith('gpt-')) model.value = 'gemini-2.5-flash'
  } else {
    apiKeySource.value = 'gemini-cli'
    baseUrl.value = ''
    if (!model.value || model.value.startsWith('gpt-')) model.value = 'gemini-cli-default'
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
  apiKeySource.value = loaded.provider_name === 'gemini_cli' ? 'gemini-cli' : loaded.api_key_source
  geminiCliProxy.value = loaded.gemini_cli_proxy ?? loaded.status.gemini_cli.proxy ?? ''
  window.setTimeout(() => {
    applyingAiSettings = false
  }, 0)
}

function buildAiSettingsUpdate(): AiSettingsUpdate {
  return {
    provider_name: aiProvider.value,
    base_url: aiProvider.value === 'gemini_cli' ? null : baseUrl.value.trim() || null,
    wire_api: 'responses',
    model: model.value.trim() || (aiProvider.value === 'gemini_cli' ? 'gemini-cli-default' : ''),
    api_key_source: aiProvider.value === 'gemini_cli' ? 'gemini-cli' : apiKeySource.value.trim(),
    gemini_cli_proxy: aiProvider.value === 'gemini_cli' ? geminiCliProxy.value.trim() || null : null,
  }
}

async function saveSettings() {
  savingSettings.value = true
  saveNotice.value = ''
  saveError.value = ''
  testResult.value = null
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
    if (picked) selectedDataDir.value = picked
  } catch (e) {
    dataLocationError.value = errorMessage(e)
  }
}

async function openDataPath(path?: string | null) {
  if (!path) return
  dataLocationError.value = ''
  try {
    await invokeNative<void>('open_path', { path })
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

          <div v-if="aiProvider !== 'gemini_cli'">
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
            <div class="grid gap-3 md:grid-cols-[1fr_220px]">
              <input
                v-model="model"
                type="text"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
                :placeholder="aiProvider === 'openai' ? 'gpt-4o-mini' : aiProvider === 'gemini' ? 'gemini-2.5-flash' : 'gemini-cli-default'"
              />
              <select
                :value="modelPresets.includes(model) ? model : ''"
                @change="choosePreset(($event.target as HTMLSelectElement).value)"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">{{ t('settings.customModel') }}</option>
                <option v-for="preset in modelPresets" :key="preset" :value="preset">{{ preset }}</option>
              </select>
            </div>
          </div>

          <div v-if="aiProvider !== 'gemini_cli'">
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

          <div v-else>
            <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('settings.geminiCliProxy') }}</label>
            <input
              v-model="geminiCliProxy"
              type="text"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="http://127.0.0.1:7890"
            />
            <p class="mt-1 text-xs text-gray-500">{{ t('settings.geminiCliHelp') }}</p>
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
          </div>
        </div>
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
              @click="openDataPath(dataLocation.data_dir)"
              class="rounded-lg bg-gray-900 px-3 py-2 text-sm font-semibold text-white hover:bg-gray-700"
            >
              {{ t('settings.openDataDirectory') }}
            </button>
            <button
              @click="openDataPath(dataLocation.backup_dir)"
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
