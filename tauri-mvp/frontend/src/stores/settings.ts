import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

export type Theme = 'light' | 'dark'
export type Language = 'zh' | 'en'
export type CloseBehavior = 'ask' | 'tray' | 'exit'

export const WELCOME_CHECKLIST_DISMISSED_KEY = 'living_to_tell_welcome_checklist_dismissed'
export const ONBOARDING_AI_REVIEWED_KEY = 'living_to_tell_onboarding_ai_reviewed'
export const ONBOARDING_STORAGE_REVIEWED_KEY = 'living_to_tell_onboarding_storage_reviewed'
export const COLLECTIONS_TOUR_DISMISSED_KEY = 'living_to_tell_collections_tour_dismissed'
export const APP_TOUR_STATE_KEY = 'living_to_tell_guided_tours_v2'
export type AppTourId = 'collections' | 'ai-edit' | 'agent' | 'motifs'
export type AppTourStatus = 'unseen' | 'completed' | 'dismissed'

const DEFAULT_TOUR_STATUSES: Record<AppTourId, AppTourStatus> = {
  collections: 'unseen',
  'ai-edit': 'unseen',
  agent: 'unseen',
  motifs: 'unseen',
}

export function readAppTourStatuses(
  storage: Pick<Storage, 'getItem'>,
): Record<AppTourId, AppTourStatus> {
  const next = { ...DEFAULT_TOUR_STATUSES }
  try {
    const parsed = JSON.parse(storage.getItem(APP_TOUR_STATE_KEY) || '{}') as Partial<Record<AppTourId, AppTourStatus>>
    for (const id of Object.keys(next) as AppTourId[]) {
      if (['unseen', 'completed', 'dismissed'].includes(parsed[id] || '')) next[id] = parsed[id] as AppTourStatus
    }
  } catch {
    // Invalid local preferences fall back to the unobtrusive first-run invite.
  }
  if (storage.getItem(COLLECTIONS_TOUR_DISMISSED_KEY) === 'true' && next.collections === 'unseen') {
    next.collections = 'dismissed'
  }
  return next
}

function loadTourStatuses(): Record<AppTourId, AppTourStatus> {
  return readAppTourStatuses(localStorage)
}

export const useSettingsStore = defineStore('settings', () => {
  // 从 localStorage 读取保存的设置
  localStorage.setItem('theme', 'light')
  const theme = ref<Theme>('light')
  const language = ref<Language>((localStorage.getItem('language') as Language) || 'zh')
  const focusMode = ref(false)
  const rightContextPaneCollapsed = ref(localStorage.getItem('right_context_pane_collapsed') === 'true')
  const closeBehavior = ref<CloseBehavior>('ask')
  const closeBehaviorLoaded = ref(false)
  const welcomeChecklistDismissed = ref(localStorage.getItem(WELCOME_CHECKLIST_DISMISSED_KEY) === 'true')
  const onboardingAiReviewed = ref(localStorage.getItem(ONBOARDING_AI_REVIEWED_KEY) === 'true')
  const onboardingStorageReviewed = ref(localStorage.getItem(ONBOARDING_STORAGE_REVIEWED_KEY) === 'true')
  const tourStatuses = ref<Record<AppTourId, AppTourStatus>>(loadTourStatuses())
  const collectionsTourDismissed = computed(() => tourStatuses.value.collections !== 'unseen')

  function toggleTheme() {
    theme.value = 'light'
    applyTheme()
  }

  function toggleLanguage() {
    language.value = language.value === 'zh' ? 'en' : 'zh'
  }

  function toggleFocusMode() {
    focusMode.value = !focusMode.value
  }

  function toggleRightContextPane() {
    rightContextPaneCollapsed.value = !rightContextPaneCollapsed.value
  }

  async function loadNativePreferences() {
    if (closeBehaviorLoaded.value) return
    try {
      const { invoke } = await import('@tauri-apps/api/core')
      const value = await invoke<CloseBehavior>('get_close_preference')
      closeBehavior.value = value
    } catch {
      const fallback = localStorage.getItem('close_behavior') as CloseBehavior | null
      closeBehavior.value = fallback || 'ask'
    } finally {
      closeBehaviorLoaded.value = true
    }
  }

  async function saveCloseBehavior(next: CloseBehavior): Promise<CloseBehavior> {
    try {
      const { invoke } = await import('@tauri-apps/api/core')
      const effective = await invoke<CloseBehavior>('set_close_preference', {
        preference: next,
      })
      closeBehavior.value = effective
      return effective
    } catch {
      closeBehavior.value = next
      localStorage.setItem('close_behavior', next)
      return next
    }
  }

  function dismissWelcomeChecklist() {
    welcomeChecklistDismissed.value = true
    localStorage.setItem(WELCOME_CHECKLIST_DISMISSED_KEY, 'true')
  }

  function resetWelcomeChecklist() {
    welcomeChecklistDismissed.value = false
    localStorage.removeItem(WELCOME_CHECKLIST_DISMISSED_KEY)
    onboardingAiReviewed.value = false
    onboardingStorageReviewed.value = false
    localStorage.removeItem(ONBOARDING_AI_REVIEWED_KEY)
    localStorage.removeItem(ONBOARDING_STORAGE_REVIEWED_KEY)
  }

  function dismissCollectionsTour() {
    dismissTour('collections')
  }

  function resetCollectionsTour() {
    resetTour('collections')
  }

  function tourStatus(id: AppTourId): AppTourStatus {
    return tourStatuses.value[id]
  }

  function setTourStatus(id: AppTourId, status: AppTourStatus) {
    tourStatuses.value = { ...tourStatuses.value, [id]: status }
    localStorage.setItem(APP_TOUR_STATE_KEY, JSON.stringify(tourStatuses.value))
    if (id === 'collections') {
      if (status === 'unseen') localStorage.removeItem(COLLECTIONS_TOUR_DISMISSED_KEY)
      else localStorage.setItem(COLLECTIONS_TOUR_DISMISSED_KEY, 'true')
    }
  }

  function completeTour(id: AppTourId) {
    setTourStatus(id, 'completed')
  }

  function dismissTour(id: AppTourId) {
    setTourStatus(id, 'dismissed')
  }

  function resetTour(id: AppTourId) {
    setTourStatus(id, 'unseen')
  }

  function markOnboardingAiReviewed() {
    onboardingAiReviewed.value = true
    localStorage.setItem(ONBOARDING_AI_REVIEWED_KEY, 'true')
  }

  function markOnboardingStorageReviewed() {
    onboardingStorageReviewed.value = true
    localStorage.setItem(ONBOARDING_STORAGE_REVIEWED_KEY, 'true')
  }

  function applyTheme() {
    theme.value = 'light'
    document.documentElement.classList.remove('dark')
  }

  // 监听主题变化，保存到 localStorage
  watch(theme, (newTheme) => {
    localStorage.setItem('theme', newTheme)
  })

  // 监听语言变化，保存到 localStorage
  watch(language, (newLang) => {
    localStorage.setItem('language', newLang)
  })

  watch(rightContextPaneCollapsed, (collapsed) => {
    localStorage.setItem('right_context_pane_collapsed', String(collapsed))
  })

  // Initialize theme on load
  applyTheme()

  return {
    theme,
    language,
    focusMode,
    rightContextPaneCollapsed,
    closeBehavior,
    closeBehaviorLoaded,
    welcomeChecklistDismissed,
    onboardingAiReviewed,
    onboardingStorageReviewed,
    collectionsTourDismissed,
    tourStatuses,
    toggleTheme,
    toggleLanguage,
    toggleFocusMode,
    toggleRightContextPane,
    loadNativePreferences,
    saveCloseBehavior,
    dismissWelcomeChecklist,
    resetWelcomeChecklist,
    dismissCollectionsTour,
    resetCollectionsTour,
    tourStatus,
    completeTour,
    dismissTour,
    resetTour,
    markOnboardingAiReviewed,
    markOnboardingStorageReviewed,
  }
})
