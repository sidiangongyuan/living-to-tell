<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from '../i18n'
import { useArticlesStore } from '../features/articles/store'
import { useCollectionsStore } from '../features/collections/store'
import { useSettingsStore } from '../stores/settings'

const router = useRouter()
const articlesStore = useArticlesStore()
const collectionsStore = useCollectionsStore()
const settingsStore = useSettingsStore()
const { t } = useI18n()

const show = ref(false)
const searchText = ref('')
const selectedIndex = ref(0)
const commandError = ref('')

interface Command {
  id: string
  label: string
  description: string
  action: () => void | Promise<void>
  category: 'navigation' | 'articles' | 'collections' | 'settings' | 'view'
}

const allCommands = computed<Command[]>(() => [
  { id: 'nav-dates', label: t('commandPalette.commands.navDates.label'), description: t('commandPalette.commands.navDates.description'), action: async () => { await router.push('/dates') }, category: 'navigation' },
  { id: 'nav-articles', label: t('commandPalette.commands.navArticles.label'), description: t('commandPalette.commands.navArticles.description'), action: async () => { await router.push('/articles') }, category: 'navigation' },
  { id: 'nav-collections', label: t('commandPalette.commands.navCollections.label'), description: t('commandPalette.commands.navCollections.description'), action: async () => { await router.push('/collections') }, category: 'navigation' },
  { id: 'nav-ai', label: t('commandPalette.commands.navAi.label'), description: t('commandPalette.commands.navAi.description'), action: async () => { await router.push('/ai') }, category: 'navigation' },
  { id: 'nav-library', label: t('commandPalette.commands.navLibrary.label'), description: t('commandPalette.commands.navLibrary.description'), action: async () => { await router.push('/library') }, category: 'navigation' },
  { id: 'nav-motifs', label: t('commandPalette.commands.navMotifs.label'), description: t('commandPalette.commands.navMotifs.description'), action: async () => { await router.push('/motifs') }, category: 'navigation' },
  { id: 'articles-new', label: t('commandPalette.commands.newArticle.label'), description: t('commandPalette.commands.newArticle.description'), action: async () => { await router.push('/articles'); await articlesStore.createEntry() }, category: 'articles' },
  { id: 'collections-new', label: t('commandPalette.commands.newCollection.label'), description: t('commandPalette.commands.newCollection.description'), action: async () => { await router.push('/collections'); await collectionsStore.createCollection('新建作品集', '') }, category: 'collections' },
  { id: 'view-focus', label: t('nav.focusMode'), description: t('commandPalette.commands.toggleFocus.description'), action: () => settingsStore.toggleFocusMode(), category: 'view' },
])

const filteredCommands = computed(() => {
  if (!searchText.value.trim()) return allCommands.value
  const query = searchText.value.toLowerCase()
  return allCommands.value.filter((cmd) =>
    cmd.label.toLowerCase().includes(query) ||
    cmd.description.toLowerCase().includes(query) ||
    t(`commandPalette.${cmd.category}`).toLowerCase().includes(query)
  )
})

function open() {
  show.value = true
  searchText.value = ''
  selectedIndex.value = 0
  commandError.value = ''
}

function close() {
  show.value = false
}

async function executeCommand(cmd: Command) {
  commandError.value = ''
  try {
    await cmd.action()
    close()
  } catch (e) {
    console.error('Command failed:', e)
    commandError.value = e instanceof Error ? e.message : String(e)
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (!show.value) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault()
      open()
    }
    return
  }

  if (e.key === 'Escape') {
    e.preventDefault()
    close()
  } else if (e.key === 'ArrowDown') {
    e.preventDefault()
    selectedIndex.value = Math.min(selectedIndex.value + 1, filteredCommands.value.length - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    selectedIndex.value = Math.max(selectedIndex.value - 1, 0)
  } else if (e.key === 'Enter') {
    e.preventDefault()
    const command = filteredCommands.value[selectedIndex.value]
    if (command) void executeCommand(command)
  }
}

onMounted(() => window.addEventListener('keydown', handleKeydown))
onUnmounted(() => window.removeEventListener('keydown', handleKeydown))

defineExpose({ open })
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="fixed inset-0 z-50 flex items-start justify-center bg-black/50 pt-32" @click.self="close">
      <div class="w-full max-w-2xl overflow-hidden rounded-lg bg-white shadow-2xl" @click.stop>
        <div class="border-b border-gray-200 p-4">
          <input
            v-model="searchText"
            @input="selectedIndex = 0"
            :placeholder="t('commandPalette.placeholder')"
            class="w-full px-4 py-3 text-lg outline-none"
            autofocus
          />
          <p v-if="commandError" class="mt-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
            {{ commandError }}
          </p>
        </div>

        <div class="max-h-96 overflow-y-auto">
          <div v-if="filteredCommands.length === 0" class="p-8 text-center text-gray-400">
            {{ t('commandPalette.noCommands') }}
          </div>
          <div
            v-for="(cmd, idx) in filteredCommands"
            :key="cmd.id"
            @click="void executeCommand(cmd)"
            @mouseenter="selectedIndex = idx"
            :class="[
              'cursor-pointer border-b border-gray-100 px-4 py-3 transition-colors',
              idx === selectedIndex ? 'border-l-4 border-l-blue-600 bg-blue-50' : 'hover:bg-gray-50',
            ]"
          >
            <div class="flex items-start justify-between gap-4">
              <div>
                <div class="font-semibold text-gray-900">{{ cmd.label }}</div>
                <div class="text-sm text-gray-500">{{ cmd.description }}</div>
              </div>
              <span class="rounded bg-gray-100 px-2 py-1 text-xs uppercase text-gray-600">
                {{ t(`commandPalette.${cmd.category}`) }}
              </span>
            </div>
          </div>
        </div>

        <div class="flex items-center justify-between border-t border-gray-200 bg-gray-50 px-4 py-3 text-xs text-gray-500">
          <div class="flex items-center gap-4">
            <span><kbd class="rounded border border-gray-300 bg-white px-2 py-1">↑↓</kbd> {{ t('commandPalette.hints.navigate') }}</span>
            <span><kbd class="rounded border border-gray-300 bg-white px-2 py-1">Enter</kbd> {{ t('commandPalette.hints.execute') }}</span>
            <span><kbd class="rounded border border-gray-300 bg-white px-2 py-1">Esc</kbd> {{ t('commandPalette.hints.close') }}</span>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
kbd {
  font-family: ui-monospace, monospace;
  font-size: 0.75rem;
}
</style>
