<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { listen, type UnlistenFn } from '@tauri-apps/api/event'
import { invoke } from '@tauri-apps/api/core'
import { getCurrentWindow } from '@tauri-apps/api/window'
import { useRouter } from 'vue-router'
import { useSettingsStore } from './stores/settings'
import { useAppUpdateStore } from './stores/appUpdate'
import { useI18n } from './i18n'
import CommandPalette from './components/CommandPalette.vue'
import QuickCapture from './components/QuickCapture.vue'

const router = useRouter()
const settings = useSettingsStore()
const appUpdate = useAppUpdateStore()
const { t } = useI18n()
const commandPaletteRef = ref<InstanceType<typeof CommandPalette> | null>(null)
const quickCaptureRef = ref<InstanceType<typeof QuickCapture> | null>(null)
const showCloseDialog = ref(false)
const closeChoice = ref<'tray' | 'exit'>('tray')
const rememberCloseChoice = ref(false)
const closeDialogMessage = ref('')
const updateBannerError = ref('')
let closeDialogUnlisten: UnlistenFn | null = null
let closeDialogWindowUnlisten: UnlistenFn | null = null

const navItems = computed(() => [
  { name: 'dates', label: t('nav.dates'), icon: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z' },
  { name: 'articles', label: t('nav.articles'), icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
  { name: 'collections', label: t('nav.collections'), icon: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10' },
  { name: 'ai', label: t('nav.ai'), icon: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z' },
  { name: 'library', label: t('nav.library'), icon: 'M8 14v3m4-3v3m4-3v3M3 21h18M3 10h18M3 7l9-4 9 4M4 10h16v11H4V10z' },
  { name: 'motifs', label: t('nav.motifs'), icon: 'M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3z M5 16l.8 2.2L8 19l-2.2.8L5 22l-.8-2.2L2 19l2.2-.8L5 16z M19 15l.9 2.6L22 18.5l-2.1.9L19 22l-.9-2.6L16 18.5l2.1-.9L19 15z' },
  { name: 'ai-cards', label: t('nav.aiCards'), icon: 'M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0a4 4 0 004-4v-4a2 2 0 012-2h4a2 2 0 012 2v4a4 4 0 01-4 4h-8z' },
  { name: 'backup', label: t('nav.backup'), icon: 'M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12' },
  { name: 'settings', label: t('nav.settings'), icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z' }
])

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'F11') {
    e.preventDefault()
    settings.toggleFocusMode()
  } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    commandPaletteRef.value?.open()
  } else if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'N') {
    e.preventDefault()
    quickCaptureRef.value?.open()
  }
}

onMounted(() => {
  settings.loadNativePreferences()
  void appUpdate.ensureVersionLoaded()
  appUpdate.scheduleAutomaticCheck()
  window.addEventListener('keydown', handleKeydown)
  void bindCloseDialogListener()
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  if (closeDialogUnlisten) {
    closeDialogUnlisten()
    closeDialogUnlisten = null
  }
  if (closeDialogWindowUnlisten) {
    closeDialogWindowUnlisten()
    closeDialogWindowUnlisten = null
  }
})

async function bindCloseDialogListener() {
  const openCloseDialog = () => {
    closeChoice.value = settings.closeBehavior === 'exit' ? 'exit' : 'tray'
    rememberCloseChoice.value = false
    closeDialogMessage.value = ''
    showCloseDialog.value = true
  }
  try {
    closeDialogUnlisten = await listen('writer-confirm-close', openCloseDialog)
  } catch {
    closeDialogUnlisten = null
  }
  try {
    closeDialogWindowUnlisten = await getCurrentWindow().listen('writer-confirm-close', openCloseDialog)
  } catch {
    closeDialogWindowUnlisten = null
  }
}

async function confirmCloseChoice() {
  closeDialogMessage.value = ''
  try {
    const effective = await invoke<'ask' | 'tray' | 'exit'>('resolve_close_action', {
      action: closeChoice.value,
      remember: rememberCloseChoice.value,
    })
    if (rememberCloseChoice.value) {
      settings.closeBehavior = effective
    }
    if (effective !== closeChoice.value && closeChoice.value === 'tray') {
      closeDialogMessage.value = t('settings.closeBehaviorTrayUnavailable')
      closeChoice.value = 'exit'
    } else if (effective !== 'exit') {
      showCloseDialog.value = false
    }
  } catch (error) {
    closeDialogMessage.value = error instanceof Error ? error.message : String(error)
  }
}

async function openUpdateDownload() {
  updateBannerError.value = ''
  try {
    await appUpdate.downloadAndInstall()
  } catch (error) {
    updateBannerError.value = error instanceof Error ? error.message : String(error)
  }
}

async function openUpdateReleasePage() {
  updateBannerError.value = ''
  try {
    await appUpdate.openReleasePage()
  } catch (error) {
    updateBannerError.value = error instanceof Error ? error.message : String(error)
  }
}
</script>

<template>
  <div class="flex h-screen bg-gray-50">
    <CommandPalette ref="commandPaletteRef" />
    <QuickCapture ref="quickCaptureRef" />
    <div
      v-if="appUpdate.hasVisibleUpdate"
      :class="[
        'fixed right-4 z-[65] w-[min(24rem,calc(100vw-2rem))] rounded-3xl border border-amber-200 bg-white/95 p-4 shadow-2xl backdrop-blur',
        settings.focusMode ? 'top-20' : 'top-4',
      ]"
    >
      <div class="flex items-start justify-between gap-3">
        <div>
          <div class="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">{{ t('updates.bannerEyebrow') }}</div>
          <h2 class="mt-1 text-lg font-semibold text-stone-900">
            {{ t('updates.bannerTitle', { version: appUpdate.latestVersion || appUpdate.latestTag }) }}
          </h2>
          <p class="mt-2 text-sm leading-6 text-stone-600">
            {{ t('updates.bannerBody', { current: appUpdate.currentVersion, latest: appUpdate.latestVersion }) }}
          </p>
        </div>
        <button
          type="button"
          class="rounded-full border border-stone-200 px-2 py-1 text-xs font-semibold text-stone-500 hover:border-stone-300 hover:text-stone-700"
          @click="appUpdate.dismissUpdate()"
        >
          {{ t('updates.later') }}
        </button>
      </div>
      <div class="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          class="rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white hover:bg-stone-700"
          :disabled="appUpdate.downloadStatus === 'downloading' || appUpdate.downloadStatus === 'installing'"
          @click="openUpdateDownload"
        >
          {{ appUpdate.downloadStatus === 'downloading' ? t('updates.downloadingInstaller') : appUpdate.downloadStatus === 'installing' ? t('updates.startingInstaller') : t('updates.downloadAndInstall') }}
        </button>
        <button
          type="button"
          class="rounded-xl border border-stone-300 px-4 py-2 text-sm font-semibold text-stone-700 hover:bg-stone-50"
          @click="openUpdateReleasePage"
        >
          {{ t('updates.viewRelease') }}
        </button>
      </div>
      <div v-if="updateBannerError" class="mt-3 rounded-2xl bg-red-50 px-3 py-2 text-sm text-red-700">
        {{ updateBannerError }}
      </div>
    </div>
    <div v-if="showCloseDialog" class="fixed inset-0 z-[70] flex items-center justify-center bg-black/45 px-4">
      <div class="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl">
        <h2 class="text-xl font-semibold text-stone-900">{{ t('settings.closeBehaviorPromptTitle') }}</h2>
        <p class="mt-2 text-sm leading-6 text-stone-600">{{ t('settings.closeBehaviorPromptBody') }}</p>
        <div class="mt-5 grid grid-cols-2 gap-3">
          <button
            @click="closeChoice = 'tray'"
            :class="[
              'rounded-2xl border px-4 py-3 text-sm font-semibold transition-colors',
              closeChoice === 'tray'
                ? 'border-amber-400 bg-amber-50 text-amber-900'
                : 'border-stone-200 bg-white text-stone-700 hover:border-stone-300'
            ]"
          >
            {{ t('settings.closeBehaviorTray') }}
          </button>
          <button
            @click="closeChoice = 'exit'"
            :class="[
              'rounded-2xl border px-4 py-3 text-sm font-semibold transition-colors',
              closeChoice === 'exit'
                ? 'border-amber-400 bg-amber-50 text-amber-900'
                : 'border-stone-200 bg-white text-stone-700 hover:border-stone-300'
            ]"
          >
            {{ t('settings.closeBehaviorExit') }}
          </button>
        </div>
        <label class="mt-4 flex items-center gap-3 text-sm text-stone-700">
          <input v-model="rememberCloseChoice" type="checkbox" class="h-4 w-4 rounded border-stone-300 text-amber-600" />
          {{ t('settings.closeBehaviorRemember') }}
        </label>
        <div v-if="closeDialogMessage" class="mt-4 rounded-2xl bg-stone-100 px-4 py-3 text-sm text-stone-700">
          {{ closeDialogMessage }}
        </div>
        <div class="mt-6 flex justify-end gap-3">
          <button
            @click="showCloseDialog = false"
            class="rounded-xl bg-stone-100 px-4 py-2 text-sm text-stone-700 hover:bg-stone-200"
          >
            {{ t('common.cancel') }}
          </button>
          <button
            @click="confirmCloseChoice"
            class="rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white hover:bg-stone-700"
          >
            {{ t('common.confirm') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Left Navigation Rail (80px) -->
    <div v-show="!settings.focusMode" class="w-20 shrink-0 bg-gray-900 flex flex-col items-center py-6 gap-2">
      <div class="mb-2 text-xl font-bold text-white">讲</div>

      <!-- Main nav items -->
      <button
        v-for="item in navItems"
        :key="item.name"
        @click="router.push({ name: item.name })"
        :class="[
          'w-14 h-14 rounded-xl flex flex-col items-center justify-center gap-1 transition-colors',
          router.currentRoute.value.name === item.name
            ? 'bg-blue-600 text-white'
            : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200'
        ]"
        :title="item.label"
      >
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="item.icon" />
        </svg>
        <span class="text-xs">{{ item.label }}</span>
      </button>

      <!-- Spacer -->
      <div class="flex-1"></div>

      <!-- Bottom utility buttons -->
      <button
        @click="settings.toggleLanguage"
        class="w-14 h-14 rounded-xl flex items-center justify-center bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200 transition-colors"
        :title="settings.language === 'zh' ? t('nav.switchToEnglish') : t('nav.switchToChinese')"
      >
        <span class="text-sm font-bold">{{ settings.language === 'zh' ? '中' : 'EN' }}</span>
      </button>

      <button
        @click="settings.toggleFocusMode"
        class="w-14 h-14 rounded-xl flex items-center justify-center bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200 transition-colors"
        :title="t('nav.focusMode')"
      >
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
        </svg>
      </button>

    </div>

    <!-- Main Content Area (router-view for each feature) -->
    <div class="flex-1 min-w-0 relative">
      <!-- Focus mode exit button -->
      <button
        v-if="settings.focusMode"
        @click="settings.toggleFocusMode"
        class="absolute top-4 right-4 z-50 px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors shadow-lg"
      >
        {{ t('nav.exitFocusMode') }}
      </button>
      <router-view />
    </div>
  </div>
</template>
