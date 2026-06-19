<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useCollectionsStore } from './store'
import { articlesApi, type Entry } from '../../api/articles'
import { useI18n } from '../../i18n'

const store = useCollectionsStore()
const { t } = useI18n()

const allArticles = ref<Entry[]>([])
const articlePickerOpen = ref(false)
const createDialogOpen = ref(false)
const selectedArticleIds = ref<string[]>([])
const newTitle = ref('')
const newDescription = ref('')
const draftTitle = ref('')
const draftDescription = ref('')
const savingMeta = ref(false)
const dragArticleId = ref<string | null>(null)
const actionError = ref<string | null>(null)

const currentArticleIds = computed(() => new Set(store.articles.map((article) => article.id)))
const previewArticle = computed(() => store.selectedArticle)

function articlePreview(body: string): string {
  const compact = body.trim().replace(/\s+/g, ' ')
  return compact.slice(0, 140) || t('collections.emptyArticle')
}

function formatDate(value: string | null): string {
  if (!value) return '—'
  return new Date(value).toLocaleDateString()
}

onMounted(async () => {
  await store.loadCollections()
  allArticles.value = await articlesApi.listArticles(500)
})

watch(
  () => store.selectedCollection,
  (collection) => {
    draftTitle.value = collection?.title ?? ''
    draftDescription.value = collection?.description ?? ''
  },
  { immediate: true }
)

async function openCreateDialog() {
  newTitle.value = ''
  newDescription.value = ''
  createDialogOpen.value = true
}

async function createCollection() {
  if (!newTitle.value.trim()) return
  actionError.value = null
  try {
    await store.createCollection(newTitle.value.trim(), newDescription.value.trim())
    createDialogOpen.value = false
  } catch (e) {
    actionError.value = e instanceof Error ? e.message : String(e)
  }
}

async function saveCollectionMeta() {
  await saveCollectionMetaIfNeeded()
}

async function saveCollectionMetaIfNeeded(): Promise<boolean> {
  actionError.value = null
  if (!store.selectedCollection) return true
  if (!draftTitle.value.trim()) {
    actionError.value = t('collections.titleRequired')
    return false
  }
  if (
    draftTitle.value.trim() === store.selectedCollection.title
    && draftDescription.value.trim() === store.selectedCollection.description
  ) {
    return true
  }
  savingMeta.value = true
  try {
    await store.updateCollection(
      store.selectedCollection.id,
      draftTitle.value.trim(),
      draftDescription.value.trim()
    )
    return true
  } catch (e) {
    actionError.value = e instanceof Error ? e.message : String(e)
    return false
  } finally {
    savingMeta.value = false
  }
}

async function openArticlePicker() {
  if (!store.selectedCollection) return
  const saved = await saveCollectionMetaIfNeeded()
  if (!saved) return
  try {
    actionError.value = null
    allArticles.value = await articlesApi.listArticles(500)
  } catch (e) {
    actionError.value = e instanceof Error ? e.message : String(e)
    return
  }
  selectedArticleIds.value = []
  articlePickerOpen.value = true
}

async function addSelectedArticles() {
  if (!selectedArticleIds.value.length) return
  try {
    actionError.value = null
    await store.addArticles(selectedArticleIds.value)
    articlePickerOpen.value = false
  } catch (e) {
    actionError.value = e instanceof Error ? e.message : String(e)
  }
}

async function deleteSelectedCollection() {
  if (!store.selectedCollection) return
  if (!confirm(t('collections.confirmDeleteCollection'))) return
  try {
    await store.deleteCollection(store.selectedCollection.id)
  } catch (e) {
    actionError.value = e instanceof Error ? e.message : String(e)
  }
}

async function selectCollection(id: string) {
  const saved = await saveCollectionMetaIfNeeded()
  if (!saved) return
  await store.selectCollection(id)
}

async function exportSelected(format: 'md' | 'txt' | 'docx') {
  const saved = await saveCollectionMetaIfNeeded()
  if (!saved) return
  await store.exportSelected(format)
}

async function removeArticle(entryId: string) {
  if (!confirm(t('collections.confirmRemoveArticle'))) return
  try {
    await store.removeArticle(entryId)
  } catch (e) {
    actionError.value = e instanceof Error ? e.message : String(e)
  }
}

async function moveArticleSafely(entryId: string, direction: -1 | 1) {
  try {
    await store.moveArticle(entryId, direction)
  } catch {
    // The store owns the visible error state; keep the click handler settled.
  }
}

function togglePickArticle(entryId: string) {
  if (currentArticleIds.value.has(entryId)) return
  if (selectedArticleIds.value.includes(entryId)) {
    selectedArticleIds.value = selectedArticleIds.value.filter((id) => id !== entryId)
  } else {
    selectedArticleIds.value = [...selectedArticleIds.value, entryId]
  }
}

function onDragStart(entryId: string) {
  dragArticleId.value = entryId
}

async function onDrop(targetId: string) {
  if (!dragArticleId.value || dragArticleId.value === targetId) return
  const reordered = [...store.articles]
  const from = reordered.findIndex((article) => article.id === dragArticleId.value)
  const to = reordered.findIndex((article) => article.id === targetId)
  if (from < 0 || to < 0) return
  const [moving] = reordered.splice(from, 1)
  reordered.splice(to, 0, moving)
  dragArticleId.value = null
  try {
    await store.reorderArticles(reordered.map((article) => article.id))
  } catch {
    // The store owns the visible error state; keep the drop handler settled.
  }
}
</script>

<template>
  <div class="flex h-full overflow-hidden bg-[#f5f1e8] text-stone-900">
    <aside class="w-72 shrink-0 border-r border-stone-200 bg-[#2d2a25] text-stone-100 flex flex-col">
      <div class="p-5 border-b border-white/10">
        <div class="flex items-center justify-between gap-3">
          <div>
            <p class="text-xs tracking-[0.28em] text-stone-400 uppercase">{{ t('collections.shelf') }}</p>
            <h2 class="text-xl font-semibold mt-1">{{ t('collections.title') }}</h2>
          </div>
          <button
            @click="openCreateDialog"
            class="rounded-xl bg-amber-200 px-3 py-2 text-sm font-semibold text-stone-900 hover:bg-amber-100"
          >
            {{ t('collections.newCollection') }}
          </button>
        </div>
        <p class="mt-3 text-sm text-stone-400">
          {{ t('collections.total', { count: store.collections.length }) }}
        </p>
      </div>

      <div class="flex-1 overflow-y-auto p-3 space-y-2">
        <div v-if="store.loading" class="p-4 text-sm text-stone-400">{{ t('common.loading') }}</div>
        <div v-else-if="store.error" class="p-4 text-sm text-red-300">{{ store.error }}</div>
        <div v-else-if="!store.collections.length" class="p-4 text-sm text-stone-400">
          {{ t('collections.emptyCollections') }}
        </div>
        <button
          v-for="collection in store.collections"
          :key="collection.id"
          @click="selectCollection(collection.id)"
          :class="[
            'w-full rounded-2xl p-4 text-left transition-all',
            store.selectedCollectionId === collection.id
              ? 'bg-amber-100 text-stone-950 shadow-lg'
              : 'bg-white/5 text-stone-200 hover:bg-white/10'
          ]"
        >
          <div class="font-semibold leading-snug">{{ collection.title || t('collections.untitled') }}</div>
          <div class="mt-1 text-xs opacity-70 line-clamp-2">
            {{ collection.description || t('collections.noDescription') }}
          </div>
          <div class="mt-3 text-xs opacity-70">
            {{ t('collections.articleCount', { count: collection.article_count }) }}
          </div>
        </button>
      </div>
    </aside>

    <main class="flex-1 min-w-0 flex flex-col">
      <header class="border-b border-stone-200 bg-[#fbf7ef]/95 px-6 py-5">
        <template v-if="store.selectedCollection">
          <div class="flex items-start justify-between gap-4">
            <div class="min-w-0 flex-1 space-y-3">
              <input
                v-model="draftTitle"
                @blur="saveCollectionMeta"
                class="w-full bg-transparent text-3xl font-semibold tracking-tight outline-none"
                :placeholder="t('collections.titlePlaceholder')"
              />
              <textarea
                v-model="draftDescription"
                @blur="saveCollectionMeta"
                rows="2"
                class="w-full resize-none bg-transparent text-sm leading-relaxed text-stone-600 outline-none"
                :placeholder="t('collections.descriptionPlaceholder')"
              />
              <div class="flex flex-wrap gap-2 text-xs text-stone-500">
                <span class="rounded-full bg-stone-200/70 px-3 py-1">
                  {{ t('collections.articleCount', { count: store.articles.length }) }}
                </span>
                <span class="rounded-full bg-stone-200/70 px-3 py-1">
                  {{ t('collections.wordCount', { count: store.collectionWordCount }) }}
                </span>
                <span v-if="savingMeta" class="rounded-full bg-blue-100 px-3 py-1 text-blue-700">
                  {{ t('common.saving') }}
                </span>
              </div>
            </div>
            <div class="flex flex-wrap justify-end gap-2">
              <button
                @click="openArticlePicker"
                class="rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white hover:bg-stone-700"
              >
                {{ t('collections.addArticles') }}
              </button>
              <button
                @click="exportSelected('md')"
                :disabled="!store.articles.length || store.exportingFormat !== null"
                class="rounded-xl bg-white px-3 py-2 text-sm text-stone-700 shadow-sm disabled:opacity-40"
              >
                {{ store.exportingFormat === 'md' ? '...' : 'Markdown' }}
              </button>
              <button
                @click="exportSelected('txt')"
                :disabled="!store.articles.length || store.exportingFormat !== null"
                class="rounded-xl bg-white px-3 py-2 text-sm text-stone-700 shadow-sm disabled:opacity-40"
              >
                {{ store.exportingFormat === 'txt' ? '...' : 'TXT' }}
              </button>
              <button
                @click="exportSelected('docx')"
                :disabled="!store.articles.length || store.exportingFormat !== null"
                class="rounded-xl bg-white px-3 py-2 text-sm text-stone-700 shadow-sm disabled:opacity-40"
              >
                {{ store.exportingFormat === 'docx' ? '...' : 'DOCX' }}
              </button>
              <button
                @click="deleteSelectedCollection"
                class="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700 hover:bg-red-100"
              >
                {{ t('common.delete') }}
              </button>
            </div>
          </div>
          <p v-if="store.exportMessage" class="mt-3 text-sm text-emerald-700">
            {{ store.exportMessage }}
          </p>
          <p v-if="actionError || store.error" class="mt-3 text-sm text-red-700">
            {{ actionError || store.error }}
          </p>
        </template>
        <div v-else class="flex items-center justify-between">
          <div>
            <h1 class="text-3xl font-semibold">{{ t('collections.selectCollection') }}</h1>
            <p class="mt-2 text-sm text-stone-500">{{ t('collections.selectHint') }}</p>
          </div>
          <button
            @click="openCreateDialog"
            class="rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white"
          >
            {{ t('collections.newCollection') }}
          </button>
        </div>
      </header>

      <div class="flex-1 min-h-0 flex overflow-hidden">
        <section class="w-[420px] shrink-0 overflow-y-auto border-r border-stone-200 p-5">
          <div v-if="!store.selectedCollection" class="mt-16 text-center text-stone-400">
            {{ t('collections.noCollectionSelected') }}
          </div>
          <div v-else-if="store.articlesLoading" class="text-sm text-stone-400">
            {{ t('common.loading') }}
          </div>
          <div v-else-if="!store.articles.length" class="rounded-3xl border border-dashed border-stone-300 bg-white/60 p-8 text-center">
            <div class="text-lg font-semibold">{{ t('collections.emptyArticles') }}</div>
            <p class="mt-2 text-sm text-stone-500">{{ t('collections.emptyArticlesHint') }}</p>
            <button
              @click="openArticlePicker"
              class="mt-5 rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white"
            >
              {{ t('collections.addArticles') }}
            </button>
          </div>
          <div v-else class="space-y-3">
            <article
              v-for="(article, index) in store.articles"
              :key="article.id"
              draggable="true"
              @dragstart="onDragStart(article.id)"
              @dragover.prevent
              @drop="onDrop(article.id)"
              @click="store.selectArticle(article.id)"
              :class="[
                'group cursor-pointer rounded-3xl border bg-white p-4 shadow-sm transition-all',
                store.selectedArticleId === article.id
                  ? 'border-amber-400 shadow-md'
                  : 'border-stone-200 hover:border-stone-300 hover:shadow-md'
              ]"
            >
              <div class="flex items-start gap-3">
                <div class="pt-1 text-xs font-semibold text-stone-400">{{ index + 1 }}</div>
                <div class="min-w-0 flex-1">
                  <h3 class="font-semibold leading-snug">{{ article.title || t('articles.untitled') }}</h3>
                  <p class="mt-2 line-clamp-3 text-sm leading-relaxed text-stone-600">
                    {{ articlePreview(article.body) }}
                  </p>
                  <div class="mt-3 flex flex-wrap gap-2 text-xs text-stone-500">
                    <span>{{ t('collections.wordCount', { count: article.word_count }) }}</span>
                    <span>{{ formatDate(article.updated_at) }}</span>
                  </div>
                </div>
              </div>
              <div class="mt-4 flex items-center justify-between">
                <div class="flex flex-wrap gap-1">
                  <span
                    v-for="tag in article.tags.slice(0, 3)"
                    :key="tag"
                    class="rounded-full bg-stone-100 px-2 py-1 text-xs text-stone-600"
                  >
                    {{ tag }}
                  </span>
                </div>
                <div class="flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                  <button
                    @click.stop="moveArticleSafely(article.id, -1)"
                    :disabled="index === 0"
                    class="rounded-lg px-2 py-1 text-xs text-stone-500 hover:bg-stone-100 disabled:opacity-30"
                  >
                    ↑
                  </button>
                  <button
                    @click.stop="moveArticleSafely(article.id, 1)"
                    :disabled="index === store.articles.length - 1"
                    class="rounded-lg px-2 py-1 text-xs text-stone-500 hover:bg-stone-100 disabled:opacity-30"
                  >
                    ↓
                  </button>
                  <button
                    @click.stop="removeArticle(article.id)"
                    class="rounded-lg px-2 py-1 text-xs text-red-600 hover:bg-red-50"
                  >
                    {{ t('common.delete') }}
                  </button>
                </div>
              </div>
            </article>
          </div>
        </section>

        <section class="flex-1 overflow-y-auto p-8">
          <div v-if="previewArticle" class="mx-auto max-w-3xl rounded-[2rem] bg-[#fffdf8] px-10 py-9 shadow-[0_18px_60px_rgba(73,55,35,0.12)]">
            <p class="text-xs tracking-[0.3em] text-stone-400 uppercase">{{ t('collections.preview') }}</p>
            <h2 class="mt-3 text-3xl font-semibold leading-tight">{{ previewArticle.title || t('articles.untitled') }}</h2>
            <div class="mt-3 flex flex-wrap gap-2 text-xs text-stone-500">
              <span>{{ t('collections.wordCount', { count: previewArticle.word_count }) }}</span>
              <span>{{ t('collections.charCount', { count: previewArticle.char_count }) }}</span>
              <span>{{ t('articles.updatedAt') }} {{ formatDate(previewArticle.updated_at) }}</span>
            </div>
            <div v-if="previewArticle.tags.length" class="mt-5 flex flex-wrap gap-2">
              <span
                v-for="tag in previewArticle.tags"
                :key="tag"
                class="rounded-full bg-amber-100 px-3 py-1 text-xs text-amber-800"
              >
                {{ tag }}
              </span>
            </div>
            <pre class="mt-8 whitespace-pre-wrap break-words font-serif text-[17px] leading-8 text-stone-800">{{ previewArticle.body || t('collections.emptyArticle') }}</pre>
          </div>
          <div v-else class="mt-20 text-center text-stone-400">
            {{ t('collections.selectArticle') }}
          </div>
        </section>
      </div>
    </main>

    <div v-if="createDialogOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div class="w-[460px] rounded-3xl bg-white p-6 shadow-2xl">
        <h3 class="text-xl font-semibold">{{ t('collections.createTitle') }}</h3>
        <input
          v-model="newTitle"
          class="mt-5 w-full rounded-xl border border-stone-200 px-4 py-3 outline-none focus:ring-2 focus:ring-amber-300"
          :placeholder="t('collections.titlePlaceholder')"
        />
        <textarea
          v-model="newDescription"
          rows="4"
          class="mt-3 w-full resize-none rounded-xl border border-stone-200 px-4 py-3 outline-none focus:ring-2 focus:ring-amber-300"
          :placeholder="t('collections.descriptionPlaceholder')"
        />
        <div v-if="actionError || store.error" class="mt-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
          {{ actionError || store.error }}
        </div>
        <div class="mt-6 flex justify-end gap-3">
          <button @click="createDialogOpen = false" class="rounded-xl bg-stone-100 px-4 py-2 text-sm">
            {{ t('common.cancel') }}
          </button>
          <button
            @click="createCollection"
            :disabled="!newTitle.trim()"
            class="rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
          >
            {{ t('common.create') }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="articlePickerOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div class="flex max-h-[82vh] w-[720px] flex-col rounded-3xl bg-white shadow-2xl">
        <div class="border-b border-stone-200 p-6">
          <h3 class="text-xl font-semibold">{{ t('collections.pickArticles') }}</h3>
          <p class="mt-1 text-sm text-stone-500">{{ t('collections.pickHint') }}</p>
        </div>
        <div class="flex-1 overflow-y-auto p-4">
          <div v-if="actionError || store.error" class="mb-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
            {{ actionError || store.error }}
          </div>
          <div v-if="!allArticles.length" class="p-8 text-center text-stone-400">
            {{ t('collections.noArticlesAvailable') }}
          </div>
          <div v-else class="space-y-2">
            <button
              v-for="article in allArticles"
              :key="article.id"
              @click="togglePickArticle(article.id)"
              :disabled="currentArticleIds.has(article.id)"
              :class="[
                'w-full rounded-2xl border p-4 text-left transition-all',
                selectedArticleIds.includes(article.id)
                  ? 'border-amber-400 bg-amber-50'
                  : 'border-stone-200 hover:border-stone-300',
                currentArticleIds.has(article.id) ? 'cursor-not-allowed opacity-45' : ''
              ]"
            >
              <div class="flex items-start gap-3">
                <input
                  type="checkbox"
                  class="mt-1"
                  :checked="selectedArticleIds.includes(article.id) || currentArticleIds.has(article.id)"
                  :disabled="currentArticleIds.has(article.id)"
                  readonly
                />
                <div class="min-w-0 flex-1">
                  <div class="font-semibold">{{ article.title || t('articles.untitled') }}</div>
                  <p class="mt-1 line-clamp-2 text-sm text-stone-500">
                    {{ articlePreview(article.body) }}
                  </p>
                  <div v-if="currentArticleIds.has(article.id)" class="mt-2 text-xs text-amber-700">
                    {{ t('collections.alreadyInCollection') }}
                  </div>
                </div>
              </div>
            </button>
          </div>
        </div>
        <div class="flex items-center justify-between border-t border-stone-200 p-5">
          <span class="text-sm text-stone-500">
            {{ t('collections.selectedCount', { count: selectedArticleIds.length }) }}
          </span>
          <div class="flex gap-3">
            <button @click="articlePickerOpen = false" class="rounded-xl bg-stone-100 px-4 py-2 text-sm">
              {{ t('common.cancel') }}
            </button>
            <button
              @click="addSelectedArticles"
              :disabled="!selectedArticleIds.length"
              class="rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
            >
              {{ t('collections.addSelected') }}
            </button>
          </div>
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

.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
