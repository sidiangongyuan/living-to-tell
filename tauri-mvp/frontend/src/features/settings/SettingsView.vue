<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { settingsApi, type AiProviderName, type AiSettings, type AiSettingsUpdate } from '../../api/settings'
import { useI18n } from '../../i18n'
import { useSettingsStore } from '../../stores/settings'

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

const autoBackupEnabled = ref(false)
const autoBackupInterval = ref('daily')
const closeBehaviorNotice = ref('')

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

function loadLocalSettings() {
  autoBackupEnabled.value = localStorage.getItem('auto_backup_enabled') === 'true'
  autoBackupInterval.value = localStorage.getItem('auto_backup_interval') || 'daily'
}

async function loadSettings() {
  loadingAiSettings.value = true
  saveError.value = ''
  loadLocalSettings()
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
    localStorage.setItem('auto_backup_enabled', String(autoBackupEnabled.value))
    localStorage.setItem('auto_backup_interval', autoBackupInterval.value)
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
    testResult.value = { success: result.ok, message: result.message }
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
        <h2 class="mb-4 text-lg font-bold text-gray-900">{{ t('settings.autoBackup') }}</h2>
        <div class="space-y-4">
          <div class="flex items-center gap-3">
            <input
              v-model="autoBackupEnabled"
              type="checkbox"
              id="auto-backup"
              class="h-4 w-4 rounded text-blue-600 focus:ring-2 focus:ring-blue-500"
            />
            <label for="auto-backup" class="text-sm font-semibold text-gray-700">
              {{ t('settings.enableAutoBackup') }}
            </label>
          </div>

          <div v-if="autoBackupEnabled">
            <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('settings.backupFrequency') }}</label>
            <select v-model="autoBackupInterval" class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500">
              <option value="hourly">{{ t('settings.intervals.hourly') }}</option>
              <option value="daily">{{ t('settings.intervals.daily') }}</option>
              <option value="weekly">{{ t('settings.intervals.weekly') }}</option>
            </select>
          </div>

          <p class="text-xs text-gray-500">{{ t('settings.autoBackupHelp') }}</p>
        </div>
      </section>

      <section class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h2 class="mb-4 text-lg font-bold text-gray-900">{{ t('settings.interfaceSettings') }}</h2>
        <div class="space-y-4">
          <div>
            <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('settings.theme') }}</label>
            <select
              :value="settings.theme"
              @change="(e) => { if (settings.theme !== (e.target as HTMLSelectElement).value) settings.toggleTheme() }"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="light">{{ t('settings.themes.light') }}</option>
              <option value="dark">{{ t('settings.themes.dark') }}</option>
            </select>
          </div>

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
