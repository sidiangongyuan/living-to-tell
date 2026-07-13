<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { appApi } from '../../api/app'
import { errorMessage, isHttpStatus } from '../../api/base'
import { settingsApi, type DataLocationInfo } from '../../api/settings'
import { useI18n } from '../../i18n'
import { useAppUpdateStore } from '../../stores/appUpdate'
import { useSettingsStore, type AppTourId } from '../../stores/settings'
import AiProfilesSettings from './AiProfilesSettings.vue'

interface DataDirectoryOverrideState {
  override_path?: string | null
  active_path?: string | null
  warning?: string | null
}

type SettingsCategory = 'ai' | 'data' | 'interface' | 'about'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const settings = useSettingsStore()
const appUpdate = useAppUpdateStore()
const activeSettingsCategory = ref<SettingsCategory>('ai')
const settingsCategories = computed(() => [
  { id: 'ai' as const, label: t('settings.categories.ai') },
  { id: 'data' as const, label: t('settings.categories.data') },
  { id: 'interface' as const, label: t('settings.categories.interface') },
  { id: 'about' as const, label: t('settings.categories.about') },
])
const tutorialEntries = computed(() => [
  { id: 'collections' as const, title: t('settings.tutorials.collections'), help: t('settings.tutorials.collectionsHelp') },
  { id: 'ai-edit' as const, title: t('settings.tutorials.aiEdit'), help: t('settings.tutorials.aiEditHelp') },
  { id: 'agent' as const, title: t('settings.tutorials.agent'), help: t('settings.tutorials.agentHelp') },
  { id: 'motifs' as const, title: t('settings.tutorials.motifs'), help: t('settings.tutorials.motifsHelp') },
])

const savingSettings = ref(false)
const saveNotice = ref('')
const saveError = ref('')
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

onMounted(() => {
  void loadDataLocation()
  void settings.loadNativePreferences()
  void appUpdate.ensureVersionLoaded()
  focusRequestedSection()
})

watch(() => route.query.section, focusRequestedSection)

function focusRequestedSection() {
  const requested = String(route.query.section || '')
  if (requested === 'ai' || requested === 'ai_profiles') activeSettingsCategory.value = 'ai'
  else if (requested === 'data' || requested === 'storage') activeSettingsCategory.value = 'data'
  else if (requested === 'interface' || requested === 'tutorials') activeSettingsCategory.value = 'interface'
  else if (requested === 'about' || requested === 'updates') activeSettingsCategory.value = 'about'
}

async function saveSettings() {
  savingSettings.value = true
  saveNotice.value = ''
  saveError.value = ''
  try {
    closeBehaviorNotice.value = ''
    const requested = settings.closeBehavior
    const effective = await settings.saveCloseBehavior(requested)
    if (effective !== requested) closeBehaviorNotice.value = t('settings.closeBehaviorTrayUnavailable')
    saveNotice.value = t('settings.saved')
  } catch (error) {
    saveError.value = errorMessage(error)
  } finally {
    savingSettings.value = false
  }
}

function resetWelcomeChecklist() {
  settings.resetWelcomeChecklist()
  saveNotice.value = t('settings.welcomeChecklistReset')
  saveError.value = ''
}

async function showTutorial(id: AppTourId) {
  settings.resetTour(id)
  if (id === 'collections') await router.push({ name: 'collections', query: { tour: 'collections' } })
  else if (id === 'agent') await router.push({ name: 'collections', query: { tab: 'agent', tour: 'agent' } })
  else if (id === 'ai-edit') await router.push({ name: 'ai', query: { tour: 'ai-edit' } })
  else await router.push({ name: 'motifs', query: { tour: 'motifs' } })
}

function tutorialStatusLabel(id: AppTourId): string {
  return t(`settings.tutorials.status.${settings.tourStatus(id)}`)
}

async function invokeNative<T>(command: string, args?: Record<string, unknown>): Promise<T> {
  const { invoke } = await import('@tauri-apps/api/core')
  return invoke<T>(command, args)
}

async function backendSupports(capability: string): Promise<boolean | null> {
  try {
    const info = await appApi.getVersion()
    return info.capabilities.includes(capability)
  } catch (error) {
    if (isHttpStatus(error, 404)) return false
    return null
  }
}

async function loadDataLocation() {
  loadingDataLocation.value = true
  dataLocationError.value = ''
  dataLocationUnsupported.value = false
  try {
    const supported = await backendSupports('data_location')
    if (supported === false) {
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
  } catch (error) {
    if (isHttpStatus(error, 404)) {
      dataLocation.value = null
      dataLocationUnsupported.value = true
    } else {
      dataLocationError.value = errorMessage(error)
    }
  } finally {
    loadingDataLocation.value = false
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
  } catch (error) {
    dataLocationError.value = errorMessage(error)
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
  } catch (error) {
    dataLocationError.value = errorMessage(error)
  }
}

function restartAfterDataLocationChange() {
  window.setTimeout(() => {
    void invokeNative<void>('restart_app').catch((error) => {
      dataLocationError.value = errorMessage(error)
    })
  }, 900)
}

async function restartAppNow() {
  dataLocationError.value = ''
  dataLocationNotice.value = t('settings.restartRequested')
  try {
    await invokeNative<void>('restart_app')
  } catch (error) {
    dataLocationError.value = errorMessage(error)
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
    restartAfterDataLocationChange()
  } catch (error) {
    dataLocationError.value = errorMessage(error)
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
    restartAfterDataLocationChange()
  } catch (error) {
    dataLocationError.value = errorMessage(error)
  } finally {
    migratingDataLocation.value = false
  }
}

async function checkForUpdates() {
  updateActionError.value = ''
  try {
    await appUpdate.checkForUpdates({ force: true, source: 'manual' })
  } catch (error) {
    updateActionError.value = errorMessage(error)
  }
}

async function openLatestInstaller() {
  updateActionError.value = ''
  try {
    await appUpdate.openDownload()
  } catch (error) {
    updateActionError.value = errorMessage(error)
  }
}

async function downloadAndInstallLatest() {
  updateActionError.value = ''
  try {
    await appUpdate.downloadAndInstall()
  } catch (error) {
    updateActionError.value = errorMessage(error)
  }
}

async function openReleasePage() {
  updateActionError.value = ''
  try {
    await appUpdate.openReleasePage()
  } catch (error) {
    updateActionError.value = errorMessage(error)
  }
}
</script>

<template>
  <div class="flex h-full min-h-0 bg-stone-50">
    <aside class="w-52 shrink-0 border-r border-stone-200 bg-white p-4">
      <h1 class="px-2 text-lg font-semibold text-stone-900">{{ t('settings.title') }}</h1>
      <nav class="mt-5 space-y-1" :aria-label="t('settings.title')">
        <button
          v-for="category in settingsCategories"
          :key="category.id"
          type="button"
          :class="[
            'w-full rounded-md px-3 py-2 text-left text-sm font-medium transition-colors',
            activeSettingsCategory === category.id ? 'bg-stone-900 text-white' : 'text-stone-600 hover:bg-stone-100 hover:text-stone-900',
          ]"
          @click="activeSettingsCategory = category.id"
        >
          {{ category.label }}
        </button>
      </nav>
    </aside>
    <main class="min-w-0 flex-1 overflow-y-auto">
    <div class="mx-auto w-full max-w-5xl space-y-6 p-6 lg:p-8">
      <div>
        <h2 class="text-xl font-semibold text-stone-900">{{ settingsCategories.find((item) => item.id === activeSettingsCategory)?.label }}</h2>
        <p class="mt-1 text-sm text-stone-500">{{ t(`settings.categoryHelp.${activeSettingsCategory}`) }}</p>
      </div>

      <AiProfilesSettings v-if="activeSettingsCategory === 'ai'" />

      <section v-if="activeSettingsCategory === 'data'" class="border-t border-stone-200 bg-white p-6">
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

      <section v-if="activeSettingsCategory === 'interface'" class="border-t border-stone-200 bg-white p-6">
        <h2 class="mb-4 text-lg font-bold text-gray-900">{{ t('settings.interfaceSettings') }}</h2>
        <div v-if="saveError" class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{{ saveError }}</div>
        <div v-if="saveNotice" class="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-800">{{ saveNotice }}</div>
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

          <div class="border-t border-gray-200 pt-4">
            <div><h3 class="text-sm font-semibold text-gray-900">{{ t('settings.tutorials.title') }}</h3><p class="mt-1 text-xs leading-5 text-gray-500">{{ t('settings.tutorials.help') }}</p></div>
            <div class="mt-3 divide-y divide-gray-200 rounded-lg border border-gray-200 bg-white">
              <div v-for="tutorial in tutorialEntries" :key="tutorial.id" class="flex flex-wrap items-center justify-between gap-3 p-3">
                <div class="min-w-0"><div class="flex items-center gap-2"><h4 class="text-sm font-semibold text-gray-800">{{ tutorial.title }}</h4><span class="rounded bg-gray-100 px-2 py-1 text-xs text-gray-500">{{ tutorialStatusLabel(tutorial.id) }}</span></div><p class="mt-1 text-xs leading-5 text-gray-500">{{ tutorial.help }}</p></div>
                <button type="button" class="shrink-0 rounded-md bg-gray-900 px-3 py-2 text-sm font-semibold text-white hover:bg-gray-700" @click="showTutorial(tutorial.id)">{{ t('settings.tutorials.restart') }}</button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section v-if="activeSettingsCategory === 'about'" class="border-t border-stone-200 bg-white p-6">
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

      <div v-if="activeSettingsCategory === 'interface'" class="flex justify-end">
        <button
          @click="saveSettings"
          :disabled="savingSettings"
          class="rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white transition-colors hover:bg-blue-700 disabled:opacity-40"
        >
          {{ savingSettings ? t('common.saving') : t('settings.save') }}
        </button>
      </div>
    </div>
    </main>
  </div>
</template>
