<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { apiFetch } from '../../api/base'
import { useI18n } from '../../i18n'
import { useSettingsStore } from '../../stores/settings'

const { t } = useI18n()
const settings = useSettingsStore()

const aiProvider = ref('openai')
const apiKey = ref('')
const apiKeyMasked = ref(true)
const modelThrifty = ref('gpt-4o-mini')
const modelBalanced = ref('gpt-4o')
const modelStrong = ref('gpt-4o')
const baseUrl = ref('')
const testingConnection = ref(false)
const testResult = ref<{ success: boolean; message: string } | null>(null)
const autoBackupEnabled = ref(false)
const autoBackupInterval = ref('daily')
const closeBehaviorNotice = ref('')

onMounted(() => {
  loadSettings()
  void settings.loadNativePreferences()
})

function loadSettings() {
  aiProvider.value = localStorage.getItem('ai_provider') || 'openai'
  apiKey.value = localStorage.getItem('ai_api_key') || ''
  modelThrifty.value = localStorage.getItem('ai_model_thrifty') || 'gpt-4o-mini'
  modelBalanced.value = localStorage.getItem('ai_model_balanced') || 'gpt-4o'
  modelStrong.value = localStorage.getItem('ai_model_strong') || 'gpt-4o'
  baseUrl.value = localStorage.getItem('ai_base_url') || ''
  autoBackupEnabled.value = localStorage.getItem('auto_backup_enabled') === 'true'
  autoBackupInterval.value = localStorage.getItem('auto_backup_interval') || 'daily'
}

async function saveSettings() {
  localStorage.setItem('ai_provider', aiProvider.value)
  localStorage.setItem('ai_api_key', apiKey.value)
  localStorage.setItem('ai_model_thrifty', modelThrifty.value)
  localStorage.setItem('ai_model_balanced', modelBalanced.value)
  localStorage.setItem('ai_model_strong', modelStrong.value)
  localStorage.setItem('ai_base_url', baseUrl.value)
  localStorage.setItem('auto_backup_enabled', String(autoBackupEnabled.value))
  localStorage.setItem('auto_backup_interval', autoBackupInterval.value)
  closeBehaviorNotice.value = ''
  const requestedCloseBehavior = settings.closeBehavior
  const effectiveCloseBehavior = await settings.saveCloseBehavior(requestedCloseBehavior)
  if (effectiveCloseBehavior !== requestedCloseBehavior) {
    closeBehaviorNotice.value = t('settings.closeBehaviorTrayUnavailable')
  }
  alert(t('settings.saved'))
}

async function testConnection() {
  if (!apiKey.value.trim()) {
    testResult.value = { success: false, message: t('settings.apiKeyHelp') }
    return
  }

  testingConnection.value = true
  testResult.value = null

  try {
    const response = await apiFetch('/api/ai/task', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        task_type: 'rewrite',
        text: 'Hello',
      }),
      signal: AbortSignal.timeout(10000),
    })

    if (response.ok) {
      testResult.value = { success: true, message: t('common.success') }
    } else {
      testResult.value = { success: false, message: `${t('common.error')}: ${await response.text()}` }
    }
  } catch (e) {
    testResult.value = { success: false, message: `${t('common.error')}: ${e instanceof Error ? e.message : String(e)}` }
  } finally {
    testingConnection.value = false
  }
}

function toggleApiKeyVisibility() {
  apiKeyMasked.value = !apiKeyMasked.value
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
        <h2 class="mb-4 text-lg font-bold text-gray-900">{{ t('settings.aiConfig') }}</h2>
        <div class="space-y-4">
          <div>
            <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('settings.provider') }}</label>
            <select
              v-model="aiProvider"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="openai">{{ t('settings.providers.openai') }}</option>
              <option value="gemini">{{ t('settings.providers.gemini') }}</option>
              <option value="anthropic">{{ t('settings.providers.anthropicSoon') }}</option>
            </select>
          </div>

          <div>
            <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('settings.apiKey') }}</label>
            <div class="flex gap-2">
              <input
                v-model="apiKey"
                :type="apiKeyMasked ? 'password' : 'text'"
                class="flex-1 rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="sk-..."
              />
              <button
                @click="toggleApiKeyVisibility"
                class="rounded-lg bg-gray-200 px-4 py-2 transition-colors hover:bg-gray-300"
                :title="apiKeyMasked ? t('settings.showApiKey') : t('settings.hideApiKey')"
              >
                {{ apiKeyMasked ? '👁' : '👁‍🗨' }}
              </button>
            </div>
            <p class="mt-1 text-xs text-gray-500">{{ t('settings.apiKeyHelp') }}</p>
          </div>

          <div>
            <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('settings.baseUrl') }}</label>
            <input
              v-model="baseUrl"
              type="text"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="https://api.openai.com/v1"
            />
            <p class="mt-1 text-xs text-gray-500">{{ t('settings.baseUrlHelp') }}</p>
          </div>

          <div class="grid grid-cols-3 gap-4">
            <div>
              <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('settings.modelThrifty') }}</label>
              <input v-model="modelThrifty" type="text" class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('settings.modelBalanced') }}</label>
              <input v-model="modelBalanced" type="text" class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('settings.modelStrong') }}</label>
              <input v-model="modelStrong" type="text" class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>

          <div class="space-y-2">
            <button
              @click="testConnection"
              :disabled="testingConnection"
              class="rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700 disabled:bg-gray-400"
            >
              {{ testingConnection ? t('settings.testing') : t('settings.testConnection') }}
            </button>
            <p class="text-xs text-gray-500">{{ t('settings.connectionTestUnavailableHelp') }}</p>
            <div
              v-if="testResult"
              :class="[
                'rounded-lg p-3 text-sm',
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
          class="rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white transition-colors hover:bg-blue-700"
        >
          {{ t('settings.saveLocal') }}
        </button>
      </div>
    </div>
  </div>
</template>
