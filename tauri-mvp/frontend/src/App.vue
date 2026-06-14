<script setup lang="ts">
import { onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useSettingsStore } from './stores/settings'
import { useI18n } from './i18n'
import CommandPalette from './components/CommandPalette.vue'
import QuickCapture from './components/QuickCapture.vue'
import { ref } from 'vue'

const router = useRouter()
const settings = useSettingsStore()
const { t } = useI18n()
const commandPaletteRef = ref<InstanceType<typeof CommandPalette> | null>(null)
const quickCaptureRef = ref<InstanceType<typeof QuickCapture> | null>(null)

const navItems = computed(() => [
  { name: 'dates', label: t('nav.dates'), icon: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z' },
  { name: 'articles', label: t('nav.articles'), icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
  { name: 'collections', label: t('nav.collections'), icon: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10' },
  { name: 'ai', label: t('nav.ai'), icon: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z' },
  { name: 'library', label: t('nav.library'), icon: 'M8 14v3m4-3v3m4-3v3M3 21h18M3 10h18M3 7l9-4 9 4M4 10h16v11H4V10z' },
  { name: 'ai-cards', label: t('nav.aiCards'), icon: 'M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0a4 4 0 004-4v-4a2 2 0 012-2h4a2 2 0 012 2v4a4 4 0 01-4 4h-8z' },
  { name: 'backup', label: t('nav.backup'), icon: 'M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12' },
  { name: 'settings', label: t('nav.settings'), icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z' }
])

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'F11') {
    e.preventDefault()
    settings.toggleFocusMode()
  } else if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault()
    commandPaletteRef.value?.open()
  } else if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'N') {
    e.preventDefault()
    quickCaptureRef.value?.open()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <div class="flex h-screen bg-gray-50">
    <CommandPalette ref="commandPaletteRef" />
    <QuickCapture ref="quickCaptureRef" />

    <!-- Left Navigation Rail (80px) -->
    <div v-show="!settings.focusMode" class="w-20 shrink-0 bg-gray-900 flex flex-col items-center py-6 gap-2">
      <div class="text-white font-bold text-xl mb-2">W</div>

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

      <button
        @click="settings.toggleTheme"
        class="w-14 h-14 rounded-xl flex items-center justify-center bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200 transition-colors"
        :title="settings.theme === 'light' ? t('nav.darkMode') : t('nav.lightMode')"
      >
        <svg v-if="settings.theme === 'light'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
        </svg>
        <svg v-else class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
      </button>
    </div>

    <!-- Main Content Area (router-view for each feature) -->
    <div class="flex-1 min-w-0 relative">
      <!-- Focus mode exit button -->
      <button
        v-if="settings.focusMode"
        @click="settings.toggleFocusMode"
        class="absolute top-4 left-4 z-50 px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors shadow-lg"
      >
        {{ t('nav.exitFocusMode') }}
      </button>
      <router-view />
    </div>
  </div>
</template>
