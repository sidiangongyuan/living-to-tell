import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type Theme = 'light' | 'dark'
export type Language = 'zh' | 'en'
export type CloseBehavior = 'ask' | 'tray' | 'exit'

export const WELCOME_CHECKLIST_DISMISSED_KEY = 'living_to_tell_welcome_checklist_dismissed'
export const ONBOARDING_AI_REVIEWED_KEY = 'living_to_tell_onboarding_ai_reviewed'
export const ONBOARDING_STORAGE_REVIEWED_KEY = 'living_to_tell_onboarding_storage_reviewed'
export const COLLECTIONS_TOUR_DISMISSED_KEY = 'living_to_tell_collections_tour_dismissed'

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
  const collectionsTourDismissed = ref(localStorage.getItem(COLLECTIONS_TOUR_DISMISSED_KEY) === 'true')

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
    collectionsTourDismissed.value = true
    localStorage.setItem(COLLECTIONS_TOUR_DISMISSED_KEY, 'true')
  }

  function resetCollectionsTour() {
    collectionsTourDismissed.value = false
    localStorage.removeItem(COLLECTIONS_TOUR_DISMISSED_KEY)
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
    markOnboardingAiReviewed,
    markOnboardingStorageReviewed,
  }
})
