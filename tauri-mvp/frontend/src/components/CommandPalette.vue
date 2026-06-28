<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from '../i18n'
import { useArticlesStore } from '../features/articles/store'
import { useCollectionsStore } from '../features/collections/store'
import { useSettingsStore } from '../stores/settings'
import { articlesApi, type Entry } from '../api/articles'
import { collectionsApi, type Collection } from '../api/collections'
import { libraryApi, type Reference } from '../api/library'
import { motifsApi, type MotifNode } from '../api/motifs'
import { aiCardApi, type AiCard } from '../api/aiCards'

type SectionKey = 'commands' | 'articles' | 'collections' | 'references' | 'motifs' | 'ai_cards' | 'settings'
type CommandCategory = 'navigation' | 'articles' | 'collections' | 'settings' | 'view'

interface Command {
  id: string
  label: string
  description: string
  action: () => void | Promise<void>
  category: CommandCategory
  section: SectionKey
  shortcut?: string
}

interface PaletteItem {
  id: string
  label: string
  description: string
  section: SectionKey
  action: () => void | Promise<void>
  kind: 'command' | 'result'
  shortcut?: string
}

interface PaletteSection {
  key: SectionKey
  label: string
  items: Array<PaletteItem & { index: number }>
}

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
const inputRef = ref<HTMLInputElement | null>(null)
let searchTimer: number | null = null
let searchSeq = 0

const sectionOrder: SectionKey[] = ['commands', 'articles', 'collections', 'references', 'motifs', 'ai_cards', 'settings']

const sectionLabels = computed<Record<SectionKey, string>>(() => ({
  commands: t('commandPalette.sections.commands'),
  articles: t('commandPalette.sections.articles'),
  collections: t('commandPalette.sections.collections'),
  references: t('commandPalette.sections.references'),
  motifs: t('commandPalette.sections.motifs'),
  ai_cards: t('commandPalette.sections.aiCards'),
  settings: t('commandPalette.sections.settings'),
}))

const allCommands = computed<Command[]>(() => [
  {
    id: 'today-writing',
    label: t('commandPalette.commands.todayWriting.label'),
    description: t('commandPalette.commands.todayWriting.description'),
    action: async () => { await router.push('/dates') },
    category: 'navigation',
    section: 'commands',
    shortcut: 'D',
  },
  {
    id: 'articles-new',
    label: t('commandPalette.commands.newArticle.label'),
    description: t('commandPalette.commands.newArticle.description'),
    action: async () => { await router.push('/articles'); await articlesStore.createEntry() },
    category: 'articles',
    section: 'commands',
    shortcut: 'N',
  },
  {
    id: 'reference-new',
    label: t('commandPalette.commands.newReference.label'),
    description: t('commandPalette.commands.newReference.description'),
    action: async () => { await router.push({ name: 'library', query: { action: 'create_reference' } }) },
    category: 'navigation',
    section: 'commands',
  },
  {
    id: 'collections-new',
    label: t('commandPalette.commands.newCollection.label'),
    description: t('commandPalette.commands.newCollection.description'),
    action: async () => { await router.push('/collections'); await collectionsStore.createCollection(t('collections.untitled'), '') },
    category: 'collections',
    section: 'commands',
  },
  {
    id: 'settings-ai',
    label: t('commandPalette.commands.aiSettings.label'),
    description: t('commandPalette.commands.aiSettings.description'),
    action: async () => { await router.push({ name: 'settings', query: { section: 'ai_config' } }) },
    category: 'settings',
    section: 'settings',
  },
  {
    id: 'nav-backup',
    label: t('nav.backup'),
    description: t('commandPalette.commands.navBackup.description'),
    action: async () => { await router.push('/backup') },
    category: 'settings',
    section: 'settings',
  },
  {
    id: 'nav-articles',
    label: t('nav.articles'),
    description: t('commandPalette.commands.navArticles.description'),
    action: async () => { await router.push('/articles') },
    category: 'articles',
    section: 'commands',
  },
  {
    id: 'nav-library',
    label: t('nav.library'),
    description: t('commandPalette.commands.navLibrary.description'),
    action: async () => { await router.push('/library') },
    category: 'navigation',
    section: 'commands',
  },
  {
    id: 'nav-collections',
    label: t('nav.collections'),
    description: t('commandPalette.commands.navCollections.description'),
    action: async () => { await router.push('/collections') },
    category: 'collections',
    section: 'commands',
  },
  {
    id: 'nav-ai',
    label: t('nav.ai'),
    description: t('commandPalette.commands.navAi.description'),
    action: async () => { await router.push('/ai') },
    category: 'navigation',
    section: 'commands',
  },
  {
    id: 'nav-ai-cards',
    label: t('nav.aiCards'),
    description: t('commandPalette.commands.navAiCards.description'),
    action: async () => { await router.push('/ai-cards') },
    category: 'navigation',
    section: 'commands',
  },
  {
    id: 'nav-motifs',
    label: t('commandPalette.commands.navMotifs.label'),
    description: t('commandPalette.commands.navMotifs.description'),
    action: async () => { await router.push('/motifs') },
    category: 'navigation',
    section: 'commands',
  },
  {
    id: 'nav-settings',
    label: t('nav.settings'),
    description: t('commandPalette.commands.navSettings.description'),
    action: async () => { await router.push('/settings') },
    category: 'settings',
    section: 'settings',
  },
  {
    id: 'view-focus',
    label: t('nav.focusMode'),
    description: t('commandPalette.commands.toggleFocus.description'),
    action: () => settingsStore.toggleFocusMode(),
    category: 'view',
    section: 'settings',
  },
])

const filteredCommands = computed(() => {
  const query = searchText.value.trim().toLowerCase()
  if (!query) return allCommands.value
  return allCommands.value.filter((cmd) =>
    cmd.label.toLowerCase().includes(query)
    || cmd.description.toLowerCase().includes(query)
    || t(`commandPalette.${cmd.category}`).toLowerCase().includes(query)
  )
})

const commandItems = computed<PaletteItem[]>(() =>
  filteredCommands.value.map((cmd) => ({
    id: cmd.id,
    label: cmd.label,
    description: cmd.description,
    section: cmd.section,
    kind: 'command',
    action: cmd.action,
    shortcut: cmd.shortcut,
  }))
)

const visibleItems = computed<PaletteItem[]>(() => {
  const query = searchText.value.trim()
  if (!query) return commandItems.value
  return [...commandItems.value, ...searchResults.value]
})

const groupedSections = computed<PaletteSection[]>(() => {
  const bySection = new Map<SectionKey, Array<PaletteItem & { index: number }>>()
  visibleItems.value.forEach((item, index) => {
    const bucket = bySection.get(item.section) ?? []
    bucket.push({ ...item, index })
    bySection.set(item.section, bucket)
  })
  return sectionOrder
    .map((key) => ({
      key,
      label: sectionLabels.value[key],
      items: bySection.get(key) ?? [],
    }))
    .filter((section) => section.items.length > 0)
})

function compact(text: string, limit = 92): string {
  const value = (text || '').replace(/\s+/g, ' ').trim()
  return value.length > limit ? `${value.slice(0, limit)}...` : value
}

function asList<T>(value: T[] | unknown): T[] {
  return Array.isArray(value) ? value : []
}

function matches(value: string | null | undefined, query: string): boolean {
  return String(value ?? '').toLowerCase().includes(query.toLowerCase())
}

function friendlyPaletteError(): string {
  return t('commandPalette.searchFailed')
}

async function runGlobalSearch(query: string) {
  const needle = query.trim()
  const seq = ++searchSeq
  if (needle.length < 2) {
    searchResults.value = []
    searchLoading.value = false
    commandError.value = ''
    return
  }
  searchLoading.value = true
  commandError.value = ''
  try {
    const [articleRaw, collectionRaw, referenceRaw, motifRaw, cardRaw] = await Promise.all([
      articlesApi.search(needle, 8).catch(() => []),
      collectionsApi.listCollections().catch(() => []),
      libraryApi.searchReferences(needle, 8).catch(() => []),
      motifsApi.listMotifs(needle, 8).catch(() => []),
      aiCardApi.searchCards(needle, undefined, 8).catch(() => []),
    ])
    if (seq !== searchSeq || searchText.value.trim() !== needle) return
    const articles = asList<Entry>(articleRaw)
    const collections = asList<Collection>(collectionRaw)
    const references = asList<Reference>(referenceRaw)
    const motifs = asList<MotifNode>(motifRaw)
    const cards = asList<AiCard>(cardRaw)
    const collectionMatches = collections
      .filter((collection) => matches(collection.title, needle) || matches(collection.description, needle))
      .slice(0, 8)
    searchResults.value = [
      ...articles.map((article) => ({
        id: `article-${article.id}`,
        label: article.title || t('articles.untitled'),
        description: compact(article.body || t('articles.noContent')),
        section: 'articles' as const,
        kind: 'result' as const,
        action: async () => { await router.push({ name: 'articles', query: { id: article.id } }) },
      })),
      ...collectionMatches.map((collection) => ({
        id: `collection-${collection.id}`,
        label: collection.title || t('collections.untitled'),
        description: compact(collection.description || t('collections.noDescription')),
        section: 'collections' as const,
        kind: 'result' as const,
        action: async () => {
          await router.push({ name: 'collections' })
          if (!collectionsStore.collections.length) await collectionsStore.loadCollections()
          await collectionsStore.selectCollection(collection.id)
        },
      })),
      ...references.map((reference) => ({
        id: `reference-${reference.id}`,
        label: reference.source_title || reference.source_author || t('commandPalette.fallback.reference'),
        description: compact(reference.content),
        section: 'references' as const,
        kind: 'result' as const,
        action: async () => { await router.push({ name: 'library', query: { ref: reference.id } }) },
      })),
      ...motifs.map((motif) => ({
        id: `motif-${motif.id}`,
        label: motif.name,
        description: compact([...(motif.aliases ?? []), ...(motif.tags ?? [])].join(' / ') || motif.note || ''),
        section: 'motifs' as const,
        kind: 'result' as const,
        action: async () => { await router.push({ name: 'motifs', query: { id: motif.id } }) },
      })),
      ...cards.map((card) => ({
        id: `ai-card-${card.id}`,
        label: card.title || t('commandPalette.fallback.aiCard'),
        description: compact(card.content),
        section: 'ai_cards' as const,
        kind: 'result' as const,
        action: async () => { await router.push({ name: 'ai-cards', query: { id: card.id } }) },
      })),
    ]
  } catch {
    if (seq === searchSeq) commandError.value = friendlyPaletteError()
  } finally {
    if (seq === searchSeq) searchLoading.value = false
  }
}

watch(searchText, (value) => {
  selectedIndex.value = 0
  if (searchTimer) window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => {
    void runGlobalSearch(value)
  }, 180)
})

watch(visibleItems, (items) => {
  if (!items.length) {
    selectedIndex.value = 0
    return
  }
  if (selectedIndex.value > items.length - 1) selectedIndex.value = items.length - 1
})

function open() {
  show.value = true
  searchText.value = ''
  selectedIndex.value = 0
  commandError.value = ''
  searchResults.value = []
  searchLoading.value = false
  void nextTick(() => inputRef.value?.focus())
}

function close() {
  show.value = false
}

async function executeCommand(cmd: PaletteItem) {
  commandError.value = ''
  try {
    await cmd.action()
    close()
  } catch {
    commandError.value = t('commandPalette.commandFailed')
  }
}

function moveSelection(delta: number) {
  if (!visibleItems.value.length) return
  selectedIndex.value = Math.min(Math.max(selectedIndex.value + delta, 0), visibleItems.value.length - 1)
}

function handleKeydown(e: KeyboardEvent) {
  if (!show.value) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
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
    moveSelection(1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    moveSelection(-1)
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
    <div v-if="show" class="fixed inset-0 z-50 flex items-start justify-center bg-slate-950/35 px-4 pt-20" @click.self="close">
      <div class="w-full max-w-3xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl" @click.stop>
        <div class="border-b border-slate-100 bg-white p-4">
          <div class="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
            <span class="text-lg text-slate-400">⌘</span>
            <input
              ref="inputRef"
              v-model="searchText"
              @input="selectedIndex = 0"
              :placeholder="t('commandPalette.placeholder')"
              class="min-w-0 flex-1 bg-transparent text-base outline-none"
            />
            <span class="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs font-semibold text-slate-400">Ctrl K</span>
          </div>
          <p class="mt-3 text-xs leading-5 text-slate-500">{{ t('commandPalette.help') }}</p>
          <p v-if="commandError" class="mt-2 rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">
            {{ commandError }}
          </p>
        </div>

        <div class="max-h-[62vh] overflow-y-auto bg-slate-50/60 p-3">
          <div v-if="searchLoading" class="mb-3 rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-800">
            {{ t('commandPalette.searching') }}
          </div>
          <div v-if="!visibleItems.length && !searchLoading" class="rounded-2xl border border-dashed border-slate-200 bg-white p-8 text-center text-sm text-slate-400">
            {{ t('commandPalette.noCommands') }}
          </div>

          <section
            v-for="section in groupedSections"
            :key="section.key"
            class="mb-3 last:mb-0"
          >
            <div class="mb-1 px-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
              {{ section.label }}
            </div>
            <div class="overflow-hidden rounded-2xl border border-slate-200 bg-white">
              <button
                v-for="item in section.items"
                :key="item.id"
                type="button"
                @click="void executeCommand(item)"
                @mouseenter="selectedIndex = item.index"
                :class="[
                  'flex w-full items-start justify-between gap-4 border-b border-slate-100 px-4 py-3 text-left last:border-b-0',
                  item.index === selectedIndex ? 'bg-blue-50' : 'hover:bg-slate-50',
                ]"
              >
                <span class="min-w-0">
                  <span class="block truncate text-sm font-semibold text-slate-950">{{ item.label }}</span>
                  <span class="mt-1 block line-clamp-2 text-xs leading-5 text-slate-500">{{ item.description }}</span>
                </span>
                <span class="flex shrink-0 items-center gap-2">
                  <span
                    v-if="item.shortcut"
                    class="rounded-md border border-slate-200 bg-white px-1.5 py-0.5 text-xs font-semibold text-slate-400"
                  >
                    {{ item.shortcut }}
                  </span>
                  <span
                    :class="[
                      'rounded-full px-2 py-0.5 text-xs font-semibold',
                      item.kind === 'command' ? 'bg-slate-100 text-slate-600' : 'bg-emerald-50 text-emerald-700',
                    ]"
                  >
                    {{ item.kind === 'command' ? t('commandPalette.kindCommand') : t('commandPalette.kindResult') }}
                  </span>
                </span>
              </button>
            </div>
          </section>
        </div>

        <div class="flex items-center justify-between border-t border-slate-200 bg-white px-4 py-3 text-xs text-slate-500">
          <div class="flex flex-wrap items-center gap-4">
            <span><kbd class="rounded border border-slate-300 bg-white px-2 py-1">↑↓</kbd> {{ t('commandPalette.hints.navigate') }}</span>
            <span><kbd class="rounded border border-slate-300 bg-white px-2 py-1">Enter</kbd> {{ t('commandPalette.hints.execute') }}</span>
            <span><kbd class="rounded border border-slate-300 bg-white px-2 py-1">Esc</kbd> {{ t('commandPalette.hints.close') }}</span>
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

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
