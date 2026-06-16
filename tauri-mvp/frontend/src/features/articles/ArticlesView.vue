<script setup lang="ts">
import { nextTick, ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useArticlesStore } from './store'
import { useSettingsStore } from '../../stores/settings'
import { collectionsApi, type Collection } from '../../api/collections'
import { articlesApi, type ArticleExportFormat } from '../../api/articles'
import FindReplace from '../../components/FindReplace.vue'
import { useI18n } from '../../i18n'
import { composeArticleBody, detectEpigraph, type EpigraphParts } from './epigraph'

const store = useArticlesStore()
const settings = useSettingsStore()
const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const saveTimer = ref<number | null>(null)
const searchInput = ref('')
const showFindReplace = ref(false)
const bodyRef = ref<HTMLTextAreaElement | null>(null)
const findQuery = ref('')
const findCaseSensitive = ref(false)
const findMatches = ref<number[]>([])
const activeMatchIndex = ref(0)
const collectionsForEntry = ref<Collection[]>([])
const allCollections = ref<Collection[]>([])
const collectionPickerOpen = ref(false)
const selectedCollectionIds = ref<string[]>([])
const existingCollectionIds = computed(() => new Set(collectionsForEntry.value.map((collection) => collection.id)))
const collectionLoading = ref(false)
const collectionError = ref('')
const bodyDraft = ref('')
const epigraphActive = ref(false)
const epigraphQuote = ref('')
const epigraphAttribution = ref('')
const syncingDraft = ref(false)

const currentBodyText = computed(() => composeCurrentBody())
const wordCount = computed(() => countWords(currentBodyText.value))
const charCount = computed(() => currentBodyText.value.length)
const lineCount = computed(() => currentBodyText.value.split('\n').length)

function countWords(body: string): number {
  if (!body) return 0
  let total = 0
  let buffer = ''
  for (const ch of body) {
    if (/[\u3400-\u9fff]/.test(ch)) {
      if (buffer.trim()) total += buffer.trim().split(/\s+/).length
      buffer = ''
      total += 1
    } else {
      buffer += ch
    }
  }
  if (buffer.trim()) total += buffer.trim().split(/\s+/).length
  return total
}

function preview(body: string): string {
  return body.trim().replace(/\s+/g, ' ').slice(0, 80) || t('articles.noContent')
}

function scheduleSave() {
  if (syncingDraft.value) return
  applyDraftToSelected()
  if (saveTimer.value) clearTimeout(saveTimer.value)
  saveTimer.value = window.setTimeout(saveNow, 600)
}

async function saveNow() {
  const entry = store.selectedEntry
  if (!entry) return
  applyDraftToSelected()
  try {
    await store.updateEntry(entry.id, entry.title, entry.body, entry.tags)
  } catch (e) {
    console.error('Save failed:', e)
  }
}

async function handleSearch() {
  if (searchInput.value.trim()) {
    await store.search(searchInput.value)
  } else {
    store.searchResults = []
  }
}

function clearSearch() {
  searchInput.value = ''
  store.searchResults = []
}

function handleReplace(findText: string, replaceText: string, replaceAll: boolean) {
  if (!store.selectedEntry) return
  const flags = replaceAll ? 'g' : ''
  const regex = new RegExp(findText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), flags)
  bodyDraft.value = bodyDraft.value.replace(regex, replaceText)
  scheduleSave()
  refreshMatches(findText, false)
}

function handleKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
    e.preventDefault()
    showFindReplace.value = !showFindReplace.value
  }
}

function refreshMatches(query = findQuery.value, caseSensitive = findCaseSensitive.value) {
  if (!store.selectedEntry || !query.trim()) {
    findMatches.value = []
    activeMatchIndex.value = 0
    return
  }
  const pattern = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const flags = caseSensitive ? 'g' : 'gi'
  const regex = new RegExp(pattern, flags)
  const matches: number[] = []
  let match: RegExpExecArray | null
  while ((match = regex.exec(bodyDraft.value)) !== null) {
    matches.push(match.index)
    if (match.index === regex.lastIndex) {
      regex.lastIndex += 1
    }
  }
  findMatches.value = matches
  activeMatchIndex.value = matches.length ? Math.min(activeMatchIndex.value, matches.length - 1) : 0
}

async function navigateMatch(direction: 'prev' | 'next', query: string, caseSensitive: boolean) {
  if (!store.selectedEntry || !query.trim()) return
  findQuery.value = query
  findCaseSensitive.value = caseSensitive
  refreshMatches(query, caseSensitive)
  if (!findMatches.value.length || !bodyRef.value) return
  activeMatchIndex.value =
    direction === 'next'
      ? (activeMatchIndex.value + 1) % findMatches.value.length
      : (activeMatchIndex.value - 1 + findMatches.value.length) % findMatches.value.length
  await nextTick()
  const start = findMatches.value[activeMatchIndex.value]
  const length = query.length
  bodyRef.value.focus()
  bodyRef.value.setSelectionRange(start, start + length)
  const approxLine = bodyRef.value.value.slice(0, start).split('\n').length
  const lineHeight = 28
  bodyRef.value.scrollTop = Math.max(0, approxLine * lineHeight - bodyRef.value.clientHeight / 2)
}

function syncFindQuery(query: string, caseSensitive: boolean) {
  findQuery.value = query
  findCaseSensitive.value = caseSensitive
  refreshMatches(query, caseSensitive)
}

function composeCurrentBody(): string {
  if (!epigraphActive.value) {
    return bodyDraft.value
  }
  if (!epigraphQuote.value.trim() || !epigraphAttribution.value.trim()) {
    const prefix = [
      epigraphQuote.value.trim(),
      epigraphAttribution.value.trim() ? `——${epigraphAttribution.value.trim()}` : '',
    ].filter(Boolean).join('\n')
    return prefix ? `${prefix}\n\n${bodyDraft.value.trimStart()}` : bodyDraft.value
  }
  const parts: EpigraphParts = {
    quote: epigraphQuote.value,
    attribution: epigraphAttribution.value,
    body: bodyDraft.value,
    raw: '',
  }
  return composeArticleBody(parts, bodyDraft.value)
}

function syncDraftFromSelected() {
  syncingDraft.value = true
  const body = store.selectedEntry?.body ?? ''
  const epigraph = detectEpigraph(body)
  if (epigraph) {
    epigraphActive.value = true
    epigraphQuote.value = epigraph.quote
    epigraphAttribution.value = epigraph.attribution
    bodyDraft.value = epigraph.body
  } else {
    epigraphActive.value = false
    epigraphQuote.value = ''
    epigraphAttribution.value = ''
    bodyDraft.value = body
  }
  refreshMatches()
  void nextTick(() => {
    syncingDraft.value = false
  })
}

function applyDraftToSelected() {
  const entry = store.selectedEntry
  if (!entry) return

  if (epigraphActive.value && !epigraphQuote.value.trim() && !epigraphAttribution.value.trim()) {
    epigraphActive.value = false
  }

  entry.body = composeCurrentBody()
}

function enableEpigraph() {
  if (epigraphActive.value) return
  epigraphActive.value = true
  epigraphQuote.value = ''
  epigraphAttribution.value = ''
}

function moveEpigraphBackToBody() {
  if (!epigraphActive.value) return
  bodyDraft.value = composeCurrentBody()
  epigraphActive.value = false
  epigraphQuote.value = ''
  epigraphAttribution.value = ''
  scheduleSave()
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

function safeFilename(title: string, format: ArticleExportFormat): string {
  const safeTitle = (title || t('articles.untitled')).replace(/[<>:"/\\|?*]/g, '').trim() || 'article'
  return `${safeTitle}.${format}`
}

async function exportArticle(format: ArticleExportFormat) {
  if (!store.selectedEntry) return
  await saveNow()
  const blob = await articlesApi.exportArticle(store.selectedEntry.id, format)
  downloadBlob(blob, safeFilename(store.selectedEntry.title, format))
}

function openAiChatForArticle() {
  if (!store.selectedEntry) return
  router.push({
    name: 'ai',
    query: {
      tab: 'chat',
      scope_kind: 'article',
      scope_id: store.selectedEntry.id,
    },
  })
}

async function applyRouteArticle() {
  const articleId = typeof route.query.id === 'string' ? route.query.id : null
  if (!articleId) return
  if (!store.entries.some((entry) => entry.id === articleId)) {
    try {
      const loaded = await articlesApi.get(articleId)
      store.entries.unshift(loaded)
    } catch (e) {
      console.error('Load routed article failed:', e)
      return
    }
  }
  store.selectEntry(articleId)
}

async function refreshEntryCollections() {
  collectionError.value = ''
  if (!store.selectedEntry) {
    collectionsForEntry.value = []
    return
  }
  try {
    collectionsForEntry.value = await collectionsApi.listCollectionsForEntry(store.selectedEntry.id)
  } catch (e) {
    collectionError.value = e instanceof Error ? e.message : String(e)
  }
}

async function openCollectionPicker() {
  if (!store.selectedEntry) return
  collectionLoading.value = true
  collectionError.value = ''
  try {
    const [collections, current] = await Promise.all([
      collectionsApi.listCollections(),
      collectionsApi.listCollectionsForEntry(store.selectedEntry.id),
    ])
    allCollections.value = collections
    collectionsForEntry.value = current
    selectedCollectionIds.value = []
    collectionPickerOpen.value = true
  } catch (e) {
    collectionError.value = e instanceof Error ? e.message : String(e)
  } finally {
    collectionLoading.value = false
  }
}

function toggleCollection(id: string) {
  if (existingCollectionIds.value.has(id)) return
  if (selectedCollectionIds.value.includes(id)) {
    selectedCollectionIds.value = selectedCollectionIds.value.filter((item) => item !== id)
  } else {
    selectedCollectionIds.value = [...selectedCollectionIds.value, id]
  }
}

async function addToSelectedCollections() {
  if (!store.selectedEntry) return
  const idsToAdd = selectedCollectionIds.value.filter((id) => !existingCollectionIds.value.has(id))
  if (!idsToAdd.length) return
  collectionLoading.value = true
  try {
    collectionsForEntry.value = await collectionsApi.addEntryToCollections(
      store.selectedEntry.id,
      idsToAdd
    )
    collectionPickerOpen.value = false
  } catch (e) {
    collectionError.value = e instanceof Error ? e.message : String(e)
  } finally {
    collectionLoading.value = false
  }
}

onMounted(async () => {
  await store.loadEntries()
  await applyRouteArticle()
  syncDraftFromSelected()
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

watch(
  () => store.selectedEntry?.id,
  () => {
    syncDraftFromSelected()
    refreshEntryCollections()
  }
)

watch(
  () => route.query.id,
  () => {
    void applyRouteArticle()
  }
)

const displayList = computed(() =>
  store.searchResults.length ? store.searchResults : store.entries
)
</script>

<template>
  <div class="flex h-full overflow-hidden bg-[#f7f3ea] text-stone-900">
    <aside class="w-80 shrink-0 border-r border-stone-200 bg-white flex flex-col">
      <div class="p-4 border-b border-stone-200">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-xl font-bold">{{ t('articles.title') }}</h2>
          <button
            @click="store.createEntry(t('articles.untitled'))"
            class="px-3 py-2 bg-stone-900 hover:bg-stone-700 text-white rounded-lg text-sm transition-colors"
          >
            {{ t('articles.newArticle') }}
          </button>
        </div>
        <div class="relative">
          <input
            v-model="searchInput"
            @input="handleSearch"
            type="text"
            :placeholder="t('articles.search')"
            class="w-full px-3 py-2 pr-8 border border-stone-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
          />
          <button
            v-if="searchInput"
            @click="clearSearch"
            class="absolute right-2 top-2 text-stone-400 hover:text-stone-600"
          >
            ×
          </button>
        </div>
        <p class="text-sm text-stone-500 mt-2">
          {{ displayList.length }} {{ store.searchResults.length ? t('articles.results') : t('articles.total') }}
        </p>
      </div>

      <div class="flex-1 overflow-y-auto">
        <div v-if="store.loading" class="p-4 text-sm text-stone-400">{{ t('common.loading') }}</div>
        <div v-else-if="store.error" class="p-4 text-sm text-red-500">{{ store.error }}</div>
        <div v-else-if="!displayList.length" class="p-4 text-sm text-stone-400">
          {{ searchInput ? t('articles.noResults') : t('articles.noArticles') }}
        </div>
        <button
          v-for="entry in displayList"
          :key="entry.id"
          @click="store.selectEntry(entry.id)"
          :class="[
            'w-full p-4 border-b border-stone-100 cursor-pointer text-left transition-colors',
            store.selectedId === entry.id
              ? 'bg-amber-50 border-l-4 border-l-amber-500'
              : 'hover:bg-stone-50',
          ]"
        >
          <h3 class="font-semibold mb-1 truncate">{{ entry.title || t('articles.untitled') }}</h3>
          <p class="text-sm text-stone-500 line-clamp-2">{{ preview(entry.body) }}</p>
          <div v-if="entry.tags.length" class="flex flex-wrap gap-1 mt-2">
            <span
              v-for="tag in entry.tags"
              :key="tag"
              class="text-xs px-2 py-1 bg-stone-100 text-stone-600 rounded"
            >{{ tag }}</span>
          </div>
        </button>
      </div>
    </aside>

    <main class="flex-1 min-w-0 flex flex-col bg-[#fffdf8] overflow-hidden relative">
      <FindReplace
        :show="showFindReplace"
        :text="bodyDraft"
        @close="showFindReplace = false"
        @replace="handleReplace"
        @navigate="navigateMatch"
        @queryChange="syncFindQuery"
      />

      <div class="flex items-center justify-between gap-4 p-4 border-b border-stone-200 bg-white/80">
        <input
          v-if="store.selectedEntry"
          v-model="store.selectedEntry.title"
          @input="scheduleSave"
          class="text-2xl font-bold flex-1 min-w-0 bg-transparent focus:outline-none"
          :placeholder="t('articles.titlePlaceholder')"
        />
        <div v-else class="text-stone-400">{{ t('articles.noArticleSelected') }}</div>
        <div class="flex items-center gap-3 shrink-0">
          <button
            v-if="store.selectedEntry"
            @click="showFindReplace = !showFindReplace"
            class="px-3 py-2 text-sm bg-stone-100 hover:bg-stone-200 rounded transition-colors"
            :title="t('articles.findReplace')"
          >
            🔍
          </button>
          <button
            v-if="store.selectedEntry"
            @click="enableEpigraph"
            class="px-3 py-2 text-sm bg-stone-100 hover:bg-stone-200 rounded transition-colors"
          >
            {{ t('articles.addEpigraph') }}
          </button>
          <div v-if="store.selectedEntry" class="flex overflow-hidden rounded-lg border border-stone-200">
            <button
              v-for="format in ['md', 'txt', 'docx'] as const"
              :key="format"
              @click="exportArticle(format)"
              class="px-3 py-2 text-xs font-semibold uppercase text-stone-600 hover:bg-stone-100"
            >
              {{ format }}
            </button>
          </div>
          <span class="text-xs text-stone-400">{{ store.saving ? t('common.saving') : t('common.saved') }}</span>
          <button
            @click="settings.toggleRightContextPane"
            :class="[
              'px-4 py-2 rounded-lg text-sm font-semibold transition-colors',
              settings.rightContextPaneCollapsed
                ? 'bg-stone-100 text-stone-700 hover:bg-stone-200'
                : 'bg-stone-900 text-white hover:bg-stone-700'
            ]"
          >
            {{ settings.rightContextPaneCollapsed ? t('articles.showContext') : t('articles.hideContext') }}
          </button>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-6">
        <div v-if="store.selectedEntry" class="mx-auto flex h-full max-w-3xl flex-col gap-5">
          <section
            v-if="epigraphActive"
            class="rounded-[1.75rem] border border-amber-200 bg-[#fff8e8] px-8 py-6 shadow-sm"
          >
            <div class="mb-4 flex items-center justify-between gap-3">
              <div>
                <p class="text-xs font-semibold uppercase tracking-[0.28em] text-amber-700">{{ t('articles.epigraph') }}</p>
                <p class="mt-1 text-xs text-stone-500">{{ t('articles.epigraphHint') }}</p>
              </div>
              <button
                @click="moveEpigraphBackToBody"
                class="rounded-lg bg-white/80 px-3 py-2 text-xs text-stone-600 hover:bg-white"
              >
                {{ t('articles.epigraphBackToBody') }}
              </button>
            </div>
            <textarea
              v-model="epigraphQuote"
              @input="scheduleSave"
              rows="3"
              class="w-full resize-none border-none bg-transparent font-serif text-lg italic leading-8 text-stone-800 outline-none"
              :placeholder="t('articles.epigraphQuotePlaceholder')"
            />
            <input
              v-model="epigraphAttribution"
              @input="scheduleSave"
              class="mt-3 w-full bg-transparent text-right text-sm text-stone-500 outline-none"
              :placeholder="t('articles.epigraphAttributionPlaceholder')"
            />
          </section>
          <textarea
            ref="bodyRef"
            v-model="bodyDraft"
            @input="scheduleSave"
            class="w-full flex-1 min-h-[500px] block p-6 border border-stone-200 rounded-[1.5rem] bg-[#fffdf8] shadow-sm focus:outline-none focus:ring-2 focus:ring-amber-300 resize-none leading-relaxed"
            :placeholder="t('articles.startWriting')"
          />
        </div>
        <div v-else class="text-center text-stone-400 mt-20">
          {{ t('articles.selectOrCreate') }}
        </div>
      </div>
    </main>

    <aside
      v-if="!settings.rightContextPaneCollapsed"
      class="w-80 shrink-0 bg-white border-l border-stone-200 flex flex-col overflow-hidden"
    >
      <div class="p-4 border-b border-stone-200">
        <h2 class="text-lg font-bold">{{ t('articles.context') }}</h2>
      </div>
      <div class="flex-1 overflow-y-auto p-4 space-y-6">
        <template v-if="store.selectedEntry">
          <section>
            <h3 class="text-sm font-semibold text-stone-700 mb-2">{{ t('articles.statistics') }}</h3>
            <div class="space-y-2 text-sm text-stone-600">
              <div class="flex justify-between">
                <span>{{ t('articles.wordCount') }}</span><span class="font-medium">{{ wordCount }}</span>
              </div>
              <div class="flex justify-between">
                <span>{{ t('articles.charCount') }}</span><span class="font-medium">{{ charCount }}</span>
              </div>
              <div class="flex justify-between">
                <span>{{ t('articles.lineCount') }}</span><span class="font-medium">{{ lineCount }}</span>
              </div>
            </div>
          </section>

          <section>
            <h3 class="text-sm font-semibold text-stone-700 mb-2">{{ t('articles.tags') }}</h3>
            <div class="flex flex-wrap gap-2 mb-2">
              <span
                v-for="tag in store.selectedEntry.tags"
                :key="tag"
                class="text-xs px-2 py-1 bg-amber-100 text-amber-700 rounded"
              >{{ tag }}</span>
            </div>
            <input
              type="text"
              :placeholder="t('articles.addTag')"
              class="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
              @keydown.enter="(e) => {
                const val = (e.target as HTMLInputElement).value.trim()
                if (val && store.selectedEntry && !store.selectedEntry.tags.includes(val)) {
                  store.selectedEntry.tags.push(val);
                  (e.target as HTMLInputElement).value = '';
                  scheduleSave()
                }
              }"
            />
          </section>

          <section>
            <div class="flex items-center justify-between mb-2">
              <h3 class="text-sm font-semibold text-stone-700">{{ t('articles.collections') }}</h3>
              <button
                @click="openCollectionPicker"
                :disabled="collectionLoading"
                class="rounded-lg bg-stone-900 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40"
              >
                {{ t('articles.addToCollection') }}
              </button>
            </div>
            <div v-if="collectionError" class="mb-2 rounded-lg bg-red-50 p-2 text-xs text-red-700">
              {{ collectionError }}
            </div>
            <div v-if="collectionsForEntry.length" class="space-y-2">
              <div
                v-for="collection in collectionsForEntry"
                :key="collection.id"
                class="rounded-xl bg-stone-50 px-3 py-2 text-sm"
              >
                <div class="font-medium">{{ collection.title }}</div>
                <div class="text-xs text-stone-500">
                  {{ t('collections.articleCount', { count: collection.article_count }) }}
                </div>
              </div>
            </div>
            <p v-else class="text-sm text-stone-400">{{ t('articles.noCollections') }}</p>
          </section>

          <section>
            <h3 class="text-sm font-semibold text-stone-700 mb-2">{{ t('articles.actions') }}</h3>
            <div class="space-y-2">
              <button
                @click="saveNow"
                class="w-full px-3 py-2 bg-stone-900 hover:bg-stone-700 text-white rounded-lg text-sm transition-colors"
              >
                {{ t('articles.saveNow') }}
              </button>
              <button
                @click="openAiChatForArticle"
                class="w-full px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm transition-colors"
              >
                {{ t('articles.aiChat') }}
              </button>
              <button
                v-if="!store.selectedEntry.archived_at"
                @click="store.archiveEntry(store.selectedEntry.id)"
                class="w-full px-3 py-2 bg-stone-100 hover:bg-stone-200 text-stone-700 rounded-lg text-sm transition-colors"
              >
                {{ t('articles.archive') }}
              </button>
              <button
                @click="store.deleteEntry(store.selectedEntry.id)"
                class="w-full px-3 py-2 bg-red-50 hover:bg-red-100 text-red-600 rounded-lg text-sm transition-colors"
              >
                {{ t('common.delete') }}
              </button>
            </div>
          </section>
        </template>
        <div v-else class="text-sm text-stone-400">{{ t('articles.noArticleSelected') }}</div>
      </div>
    </aside>

    <div v-if="collectionPickerOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div class="flex max-h-[78vh] w-[560px] flex-col rounded-3xl bg-white shadow-2xl">
        <div class="border-b border-stone-200 p-6">
          <h3 class="text-xl font-semibold">{{ t('articles.addToCollection') }}</h3>
          <p class="mt-1 text-sm text-stone-500">{{ t('articles.collectionPickerHint') }}</p>
        </div>
        <div class="flex-1 overflow-y-auto p-4">
          <div v-if="!allCollections.length" class="p-8 text-center text-stone-400">
            {{ t('articles.noCollectionsToPick') }}
          </div>
          <button
            v-for="collection in allCollections"
            :key="collection.id"
            @click="toggleCollection(collection.id)"
            :disabled="existingCollectionIds.has(collection.id)"
            :class="[
              'mb-2 w-full rounded-2xl border p-4 text-left transition-all',
              selectedCollectionIds.includes(collection.id)
                ? 'border-amber-400 bg-amber-50'
                : 'border-stone-200 hover:border-stone-300',
              existingCollectionIds.has(collection.id) ? 'cursor-not-allowed opacity-50' : ''
            ]"
          >
            <div class="flex items-start gap-3">
              <input
                type="checkbox"
                class="mt-1"
                :checked="selectedCollectionIds.includes(collection.id) || existingCollectionIds.has(collection.id)"
                :disabled="existingCollectionIds.has(collection.id)"
                readonly
              />
              <div>
                <div class="font-semibold">{{ collection.title }}</div>
                <div class="mt-1 text-xs text-stone-500">
                  {{ collection.description || t('collections.noDescription') }}
                </div>
                <div v-if="existingCollectionIds.has(collection.id)" class="mt-2 text-xs text-amber-700">
                  {{ t('collections.alreadyInCollection') }}
                </div>
              </div>
            </div>
          </button>
        </div>
        <div class="flex justify-end gap-3 border-t border-stone-200 p-5">
          <button @click="collectionPickerOpen = false" class="rounded-xl bg-stone-100 px-4 py-2 text-sm">
            {{ t('common.cancel') }}
          </button>
          <button
            @click="addToSelectedCollections"
            :disabled="collectionLoading || !selectedCollectionIds.length"
            class="rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
          >
            {{ collectionLoading ? t('common.saving') : t('common.confirm') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
