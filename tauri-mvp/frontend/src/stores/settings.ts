import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type Theme = 'light' | 'dark'
export type Language = 'zh' | 'en'

export const useSettingsStore = defineStore('settings', () => {
  // 从 localStorage 读取保存的设置
  const theme = ref<Theme>((localStorage.getItem('theme') as Theme) || 'light')
  const language = ref<Language>((localStorage.getItem('language') as Language) || 'zh')
  const focusMode = ref(false)
  const rightContextPaneCollapsed = ref(localStorage.getItem('right_context_pane_collapsed') === 'true')

  function toggleTheme() {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
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

  function applyTheme() {
    if (theme.value === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
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
    toggleTheme,
    toggleLanguage,
    toggleFocusMode,
    toggleRightContextPane,
  }
})
