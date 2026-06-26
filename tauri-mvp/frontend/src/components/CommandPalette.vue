<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from '../i18n'
import { useArticlesStore } from '../features/articles/store'
import { useCollectionsStore } from '../features/collections/store'
import { useSettingsStore } from '../stores/settings'
import { articlesApi } from '../api/articles'
import { collectionsApi } from '../api/collections'
import { libraryApi } from '../api/library'
import { motifsApi } from '../api/motifs'
import { aiCardApi } from '../api/aiCards'

const router = useRouter()
const articlesStore = useArticlesStore()
const collectionsStore = useCollectionsStore()
const settingsStore = useSettingsStore()
const { t } = useI18n()

const show = ref(false)
const searchText = ref('')
const selectedIndex = ref(0)
const commandError = ref('')
const searchLoading = ref(false)
const searchResults = ref<PaletteItem[]>([])
let searchTimer: number | null = null

interface Command {
  id: string
  label: string
  description: string
  action: () => void | Promise<void>
  category: 'navigation' | 'articles' | 'collections' | 'settings' | 'view'
}

interface PaletteItem {
  id: string
  label: string
  description: string
  category: string
  action: () => void | Promise<void>
  kind: 'command' | 'result'
}

const allCommands = computed<Command[]>(() => [
  { id: 'nav-dates', label: t('nav.dates'), description: t('commandPalette.commands.navDates.description'), action: async () => { await router.push('/dates') }, category: 'navigation' },
  { id: 'nav-articles', label: t('nav.articles'), description: t('commandPalette.commands.navArticles.description'), action: async () => { await router.push('/articles') }, category: 'navigation' },
  { id: 'nav-collections', label: t('nav.collections'), description: t('commandPalette.commands.navCollections.description'), action: async () => { await router.push('/collections') }, category: 'navigation' },
  { id: 'nav-ai', label: t('nav.ai'), description: t('commandPalette.commands.navAi.description'), action: async () => { await router.push('/ai') }, category: 'navigation' },
  { id: 'nav-ai-cards', label: t('nav.aiCards'), description: '管理风格、人物和场景卡', action: async () => { await router.push('/ai-cards') }, category: 'navigation' },
  { id: 'nav-backup', label: t('nav.backup'), description: '打开导出与备份中心', action: async () => { await router.push('/backup') }, category: 'navigation' },
  { id: 'nav-settings', label: t('nav.settings'), description: '打开设置和数据路径', action: async () => { await router.push('/settings') }, category: 'navigation' },
  { id: 'nav-library', label: t('nav.library'), description: t('commandPalette.commands.navLibrary.description'), action: async () => { await router.push('/library') }, category: 'navigation' },
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

const commandItems = computed<PaletteItem[]>(() =>
  filteredCommands.value.map((cmd) => ({
    ...cmd,
    kind: 'command',
    category: t(`commandPalette.${cmd.category}`),
  }))
)

const visibleItems = computed<PaletteItem[]>(() => {
  const query = searchText.value.trim()
  if (!query) return commandItems.value
  return [...searchResults.value, ...commandItems.value]
})

function compact(text: string, limit = 80): string {
  const value = (text || '').replace(/\s+/g, ' ').trim()
  return value.length > limit ? `${value.slice(0, limit)}...` : value
}

function matches(value: string, query: string): boolean {
  return value.toLowerCase().includes(query.toLowerCase())
}

async function runGlobalSearch(query: string) {
  const needle = query.trim()
  if (needle.length < 2) {
    searchResults.value = []
    searchLoading.value = false
    return
  }
  const token = needle
  searchLoading.value = true
  commandError.value = ''
  try {
    const [articles, collections, references, motifs, cards] = await Promise.all([
      articlesApi.search(needle, 8).catch(() => []),
      collectionsApi.listCollections().catch(() => []),
      libraryApi.searchReferences(needle, 8).catch(() => []),
      motifsApi.listMotifs(needle, 8).catch(() => []),
      aiCardApi.searchCards(needle, undefined, 8).catch(() => []),
    ])
    if (searchText.value.trim() !== token) return
    const collectionMatches = collections
      .filter((collection) => matches(collection.title, needle) || matches(collection.description, needle))
      .slice(0, 8)
    searchResults.value = [
      ...articles.map((article) => ({
        id: `article-${article.id}`,
        label: article.title || t('articles.untitled'),
        description: compact(article.body || t('articles.noContent')),
        category: '文章',
        kind: 'result' as const,
        action: async () => { await router.push({ name: 'articles', query: { id: article.id } }) },
      })),
      ...collectionMatches.map((collection) => ({
        id: `collection-${collection.id}`,
        label: collection.title || t('collections.untitled'),
        description: compact(collection.description || t('collections.noDescription')),
        category: '作品集',
        kind: 'result' as const,
        action: async () => {
          await router.push({ name: 'collections' })
          if (!collectionsStore.collections.length) await collectionsStore.loadCollections()
          await collectionsStore.selectCollection(collection.id)
        },
      })),
      ...references.map((reference) => ({
        id: `reference-${reference.id}`,
        label: reference.source_title || reference.source_author || '文脉标本',
        description: compact(reference.content),
        category: '文脉',
        kind: 'result' as const,
        action: async () => { await router.push({ name: 'library', query: { ref: reference.id } }) },
      })),
      ...motifs.map((motif) => ({
        id: `motif-${motif.id}`,
        label: motif.name,
        description: compact([...motif.aliases, ...motif.tags].join(' / ') || motif.note),
        category: '意象',
        kind: 'result' as const,
        action: async () => { await router.push({ name: 'motifs', query: { id: motif.id } }) },
      })),
      ...cards.map((card) => ({
        id: `ai-card-${card.id}`,
        label: card.title || 'AI 卡片',
        description: compact(card.content),
        category: 'AI 卡片',
        kind: 'result' as const,
        action: async () => { await router.push({ name: 'ai-cards', query: { id: card.id } }) },
      })),
    ]
  } catch (e) {
    commandError.value = e instanceof Error ? e.message : String(e)
  } finally {
    if (searchText.value.trim() === token) searchLoading.value = false
  }
}

watch(searchText, (value) => {
  selectedIndex.value = 0
  if (searchTimer) window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => {
    void runGlobalSearch(value)
  }, 180)
})

function open() {
  show.value = true
  searchText.value = ''
  selectedIndex.value = 0
  commandError.value = ''
  searchResults.value = []
  searchLoading.value = false
}

function close() {
  show.value = false
}

async function executeCommand(cmd: PaletteItem) {
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
    selectedIndex.value = Math.min(selectedIndex.value + 1, visibleItems.value.length - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    selectedIndex.value = Math.max(selectedIndex.value - 1, 0)
  } else if (e.key === 'Enter') {
    e.preventDefault()
    const command = visibleItems.value[selectedIndex.value]
    if (command) void executeCommand(command)
  }
}

onMounted(() => window.addEventListener('keydown', handleKeydown))
onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  if (searchTimer) window.clearTimeout(searchTimer)
})

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
          <div v-if="searchLoading" class="border-b border-gray-100 px-4 py-2 text-sm text-gray-400">
            正在搜索文章、作品集、文脉、意象和 AI 卡片…
          </div>
          <div v-if="visibleItems.length === 0" class="p-8 text-center text-gray-400">
            {{ t('commandPalette.noCommands') }}
          </div>
          <div
            v-for="(cmd, idx) in visibleItems"
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
                {{ cmd.category }}
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
