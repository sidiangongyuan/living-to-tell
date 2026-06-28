<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useCollectionsStore } from './store'
import { articlesApi, type Entry } from '../../api/articles'
import type { CollectionOutlineItem, CollectionOutlineItemInput, OutlineItemStatus, OutlineItemType } from '../../api/collections'
import { useI18n } from '../../i18n'
import ContextMenu from '../../components/ContextMenu.vue'
import PaneResizeHandle from '../../components/PaneResizeHandle.vue'
import { useResizablePane } from '../../composables/useResizablePane'
import { saveBlobWithDialog } from '../../utils/exportFile'
import {
  buildOutlineMarkdown,
  buildOutlineProgressSummary,
  filterOutlineItems,
  type OutlineFilters,
} from './outlineEnhancements'

const LAST_SELECTED_COLLECTION_KEY = 'living_to_tell_last_selected_collection_id'

const store = useCollectionsStore()
const { t } = useI18n()
const router = useRouter()

const allArticles = ref<Entry[]>([])
const articlePickerOpen = ref(false)
const createDialogOpen = ref(false)
const selectedArticleIds = ref<string[]>([])
const viewMode = ref<'manuscript' | 'outline' | 'board'>('manuscript')
const newTitle = ref('')
const newDescription = ref('')
const draftTitle = ref('')
const draftDescription = ref('')
const savingMeta = ref(false)
const dragArticleId = ref<string | null>(null)
const dragOutlineItemId = ref<string | null>(null)
const actionError = ref<string | null>(null)
const outlineActionError = ref<string | null>(null)
const outlineSaving = ref(false)
const outlineDraftTitle = ref('')
const outlineDraftType = ref<OutlineItemType>('scene')
const outlineDraftStatus = ref<OutlineItemStatus>('idea')
const outlineDraftSummary = ref('')
const outlineDraftNotes = ref('')
const outlineDraftEntryId = ref('')
const outlineDraftPov = ref('')
const outlineDraftSetting = ref('')
const outlineDraftTimeline = ref('')
const outlineDraftTags = ref('')
const outlineDraftTargetWords = ref<number | null>(null)
const outlineFilterType = ref<OutlineFilters['type']>('all')
const outlineFilterStatus = ref<OutlineFilters['status']>('all')
const outlineFilterUnlinkedOnly = ref(false)
const outlineExporting = ref(false)
const collectionListPane = useResizablePane({
  key: 'collections:list',
  defaultSize: 240,
  minSize: 240,
  maxSize: 420,
})
const collectionArticlePane = useResizablePane({
  key: 'collections:articles',
  defaultSize: 320,
  minSize: 300,
  maxSize: 540,
})
const deleteContextMenuOpen = ref(false)
const deleteContextMenuX = ref(0)
const deleteContextMenuY = ref(0)
const deleteContextTarget = ref<
  | { kind: 'collection'; id: string }
  | { kind: 'article'; id: string }
  | null
>(null)

const currentArticleIds = computed(() => new Set(store.articles.map((article) => article.id)))
const previewArticle = computed(() => store.selectedArticle)
const outlineLinkedArticle = computed(() => {
  const entryId = store.selectedOutlineItem?.entry_id
  if (!entryId) return null
  return allArticles.value.find((article) => article.id === entryId)
    ?? store.articles.find((article) => article.id === entryId)
    ?? null
})
const outlineTypeOptions: { value: OutlineItemType; label: string }[] = [
  { value: 'part', label: t('collectionOutline.typePart') },
  { value: 'chapter', label: t('collectionOutline.typeChapter') },
  { value: 'scene', label: t('collectionOutline.typeScene') },
  { value: 'note', label: t('collectionOutline.typeNote') },
]
const outlineStatusOptions: { value: OutlineItemStatus; label: string }[] = [
  { value: 'idea', label: t('collectionOutline.statusIdea') },
  { value: 'drafting', label: t('collectionOutline.statusDrafting') },
  { value: 'revising', label: t('collectionOutline.statusRevising') },
  { value: 'done', label: t('collectionOutline.statusDone') },
  { value: 'parked', label: t('collectionOutline.statusParked') },
]
const outlineProgress = computed(() => buildOutlineProgressSummary(store.outline, store.articles))
const filteredOutline = computed(() => filterOutlineItems(store.outline, {
  type: outlineFilterType.value,
  status: outlineFilterStatus.value,
  unlinkedOnly: outlineFilterUnlinkedOnly.value,
}))
const outlineLinkedArticleCount = computed(() =>
  new Set(store.outline.map((item) => item.entry_id).filter(Boolean)).size
)
const outlineProgressPercent = computed(() => {
  if (!outlineProgress.value.targetWordTotal) return null
  return Math.min(100, Math.round((outlineProgress.value.linkedArticleWordCount / outlineProgress.value.targetWordTotal) * 100))
})
const outlineBoardColumns = computed(() =>
  outlineStatusOptions.map((status) => ({
    ...status,
    items: filteredOutline.value.filter((item) => item.status === status.value),
  }))
)

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
  const lastCollectionId = localStorage.getItem(LAST_SELECTED_COLLECTION_KEY)
  if (lastCollectionId && store.collections.some((collection) => collection.id === lastCollectionId)) {
    await store.selectCollection(lastCollectionId)
  }
  allArticles.value = await articlesApi.listArticles(500)
})

watch(
  () => store.selectedCollectionId,
  (id) => {
    if (id) localStorage.setItem(LAST_SELECTED_COLLECTION_KEY, id)
  },
  { immediate: true }
)

watch(
  () => store.selectedCollection,
  (collection) => {
    draftTitle.value = collection?.title ?? ''
    draftDescription.value = collection?.description ?? ''
  },
  { immediate: true }
)

watch(
  () => store.selectedOutlineItem,
  (item) => {
    loadOutlineDraft(item)
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

function loadOutlineDraft(item: CollectionOutlineItem | null) {
  outlineActionError.value = null
  outlineDraftTitle.value = item?.title ?? ''
  outlineDraftType.value = item?.item_type ?? 'scene'
  outlineDraftStatus.value = item?.status ?? 'idea'
  outlineDraftSummary.value = item?.summary ?? ''
  outlineDraftNotes.value = item?.notes ?? ''
  outlineDraftEntryId.value = item?.entry_id ?? ''
  outlineDraftPov.value = item?.pov ?? ''
  outlineDraftSetting.value = item?.setting ?? ''
  outlineDraftTimeline.value = item?.timeline ?? ''
  outlineDraftTags.value = item?.tags.join(', ') ?? ''
  outlineDraftTargetWords.value = item?.target_word_count ?? null
}

function outlinePayload(): CollectionOutlineItemInput {
  const tags = outlineDraftTags.value
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean)
  return {
    title: outlineDraftTitle.value.trim() || t('collectionOutline.untitled'),
    item_type: outlineDraftType.value,
    status: outlineDraftStatus.value,
    summary: outlineDraftSummary.value,
    notes: outlineDraftNotes.value,
    entry_id: outlineDraftEntryId.value || null,
    pov: outlineDraftPov.value,
    setting: outlineDraftSetting.value,
    timeline: outlineDraftTimeline.value,
    tags,
    target_word_count: outlineDraftTargetWords.value && outlineDraftTargetWords.value > 0
      ? outlineDraftTargetWords.value
      : null,
  }
}

function outlineTypeLabel(type: OutlineItemType): string {
  return outlineTypeOptions.find((item) => item.value === type)?.label ?? type
}

function outlineStatusLabel(status: OutlineItemStatus): string {
  return outlineStatusOptions.find((item) => item.value === status)?.label ?? status
}

function outlineStatusTone(status: OutlineItemStatus): string {
  if (status === 'done') return 'bg-emerald-50 text-emerald-700 ring-emerald-100'
  if (status === 'drafting') return 'bg-blue-50 text-blue-700 ring-blue-100'
  if (status === 'revising') return 'bg-violet-50 text-violet-700 ring-violet-100'
  if (status === 'parked') return 'bg-stone-100 text-stone-500 ring-stone-200'
  return 'bg-amber-50 text-amber-700 ring-amber-100'
}

async function createOutlineItem(type: OutlineItemType = 'scene') {
  if (!store.selectedCollection) return
  outlineActionError.value = null
  try {
    const created = await store.createOutlineItem({
      title: type === 'part' ? t('collectionOutline.newPart') : t('collectionOutline.newItem'),
      item_type: type,
      status: 'idea',
    })
    if (created) loadOutlineDraft(created)
  } catch (e) {
    outlineActionError.value = e instanceof Error ? e.message : String(e)
  }
}

async function saveOutlineItem() {
  if (!store.selectedOutlineItem) return
  outlineSaving.value = true
  outlineActionError.value = null
  try {
    await store.updateOutlineItem(store.selectedOutlineItem.id, outlinePayload())
  } catch (e) {
    outlineActionError.value = e instanceof Error ? e.message : String(e)
  } finally {
    outlineSaving.value = false
  }
}

async function deleteSelectedOutlineItem() {
  if (!store.selectedOutlineItem) return
  if (!confirm(t('collectionOutline.deleteConfirm'))) return
  try {
    await store.deleteOutlineItem(store.selectedOutlineItem.id)
  } catch (e) {
    outlineActionError.value = e instanceof Error ? e.message : String(e)
  }
}

async function createArticleFromOutline() {
  if (!store.selectedOutlineItem) return
  const saved = await saveOutlineItemIfDirty()
  if (!saved) return
  try {
    const article = await articlesApi.create({
      title: outlineDraftTitle.value.trim() || t('articles.untitled'),
      body: outlineDraftSummary.value.trim(),
      tags: outlineDraftTags.value.split(',').map((tag) => tag.trim()).filter(Boolean),
    })
    allArticles.value = [article, ...allArticles.value]
    if (!store.articles.some((item) => item.id === article.id)) {
      await store.addArticles([article.id])
    }
    outlineDraftEntryId.value = article.id
    await saveOutlineItem()
  } catch (e) {
    outlineActionError.value = e instanceof Error ? e.message : String(e)
  }
}

async function saveOutlineItemIfDirty(): Promise<boolean> {
  if (!store.selectedOutlineItem) return true
  const payload = outlinePayload()
  const current = store.selectedOutlineItem
  const dirty = payload.title !== current.title
    || payload.item_type !== current.item_type
    || payload.status !== current.status
    || payload.summary !== current.summary
    || payload.notes !== current.notes
    || (payload.entry_id ?? null) !== current.entry_id
    || payload.pov !== current.pov
    || payload.setting !== current.setting
    || payload.timeline !== current.timeline
    || (payload.target_word_count ?? null) !== current.target_word_count
    || payload.tags?.join(', ') !== current.tags.join(', ')
  if (!dirty) return true
  await saveOutlineItem()
  return !outlineActionError.value
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

function safeCollectionFilename(title: string, suffix: string): string {
  const safe = (title || t('collections.untitled')).replace(/[<>:"/\\|?*]/g, '').trim() || 'collection'
  return `${safe}.${suffix}`
}

async function exportOutlineMarkdown() {
  if (!store.selectedCollection) return
  const saved = await saveCollectionMetaIfNeeded()
  if (!saved || !store.selectedCollection) return
  outlineExporting.value = true
  outlineActionError.value = null
  try {
    const markdown = buildOutlineMarkdown({
      collectionTitle: store.selectedCollection.title,
      collectionDescription: store.selectedCollection.description,
      outline: filteredOutline.value,
      typeLabel: outlineTypeLabel,
      statusLabel: outlineStatusLabel,
      articleTitleForId: (entryId) =>
        allArticles.value.find((article) => article.id === entryId)?.title
        || store.articles.find((article) => article.id === entryId)?.title
        || entryId,
    })
    const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' })
    await saveBlobWithDialog(
      blob,
      safeCollectionFilename(`${store.selectedCollection.title}-大纲`, 'md'),
      'md',
    )
  } catch (e) {
    outlineActionError.value = e instanceof Error ? `导出大纲失败：${e.message}` : `导出大纲失败：${String(e)}`
  } finally {
    outlineExporting.value = false
  }
}

async function removeArticle(entryId: string) {
  if (!confirm(t('collections.confirmRemoveArticle'))) return
  try {
    await store.removeArticle(entryId)
  } catch (e) {
    actionError.value = e instanceof Error ? e.message : String(e)
  }
}

function closeDeleteContextMenu() {
  deleteContextMenuOpen.value = false
  deleteContextTarget.value = null
}

function openDeleteContextMenu(event: MouseEvent, target: typeof deleteContextTarget.value) {
  if (!target) return
  event.preventDefault()
  deleteContextTarget.value = target
  deleteContextMenuX.value = Math.max(12, Math.min(event.clientX + 8, window.innerWidth - 172))
  deleteContextMenuY.value = Math.max(12, Math.min(event.clientY + 8, window.innerHeight - 56))
  deleteContextMenuOpen.value = true
}

function handleDeleteContextMenuSelect(item: { key: string }) {
  const target = deleteContextTarget.value
  closeDeleteContextMenu()
  if (item.key !== 'delete' || !target) return
  if (target.kind === 'article') {
    void removeArticle(target.id)
    return
  }
  if (store.selectedCollectionId === target.id) {
    void deleteSelectedCollection()
    return
  }
  void selectCollection(target.id).then(() => deleteSelectedCollection())
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

async function selectOutlineItem(id: string) {
  const saved = await saveOutlineItemIfDirty()
  if (!saved) return
  store.selectOutlineItem(id)
}

async function moveOutlineItem(itemId: string, direction: -1 | 1) {
  const index = store.outline.findIndex((item) => item.id === itemId)
  const nextIndex = index + direction
  if (index < 0 || nextIndex < 0 || nextIndex >= store.outline.length) return
  const reordered = [...store.outline]
  const [moving] = reordered.splice(index, 1)
  reordered.splice(nextIndex, 0, moving)
  try {
    await store.reorderOutline(reordered.map((item) => item.id))
  } catch {
    // The store owns the visible error state; keep the click handler settled.
  }
}

function onOutlineDragStart(itemId: string) {
  dragOutlineItemId.value = itemId
}

async function onOutlineDrop(targetId: string) {
  if (!dragOutlineItemId.value || dragOutlineItemId.value === targetId) return
  const reordered = [...store.outline]
  const from = reordered.findIndex((item) => item.id === dragOutlineItemId.value)
  const to = reordered.findIndex((item) => item.id === targetId)
  if (from < 0 || to < 0) return
  const [moving] = reordered.splice(from, 1)
  reordered.splice(to, 0, moving)
  dragOutlineItemId.value = null
  try {
    await store.reorderOutline(reordered.map((item) => item.id))
  } catch {
    // The store owns the visible error state; keep the drop handler settled.
  }
}

async function openLinkedOutlineArticle() {
  if (!store.selectedOutlineItem?.entry_id) return
  await router.push({
    name: 'articles',
    query: { id: store.selectedOutlineItem.entry_id },
  })
}
</script>

<template>
  <div class="flex h-full overflow-hidden bg-[#f5f1e8] text-stone-900">
    <aside
      class="shrink-0 border-r border-stone-200 bg-[#2d2a25] text-stone-100 flex flex-col"
      :style="collectionListPane.paneStyle.value"
      data-testid="collections-list-pane"
    >
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
          @contextmenu="openDeleteContextMenu($event, { kind: 'collection', id: collection.id })"
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
    <PaneResizeHandle data-testid="collections-list-resizer" @pointerdown="collectionListPane.startResize" />

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
                <span class="rounded-full bg-stone-200/70 px-3 py-1">
                  {{ t('collectionOutline.itemCount', { count: store.outline.length }) }}
                </span>
                <span v-if="savingMeta" class="rounded-full bg-blue-100 px-3 py-1 text-blue-700">
                  {{ t('common.saving') }}
                </span>
              </div>
              <div class="grid gap-2 text-xs text-stone-600 md:grid-cols-4">
                <div class="rounded-2xl bg-white/70 px-3 py-2 shadow-sm">
                  <div class="text-[11px] text-stone-400">已关联大纲</div>
                  <div class="mt-1 text-base font-semibold text-stone-900">{{ outlineProgress.linkedItems }} / {{ outlineProgress.totalItems }}</div>
                </div>
                <div class="rounded-2xl bg-white/70 px-3 py-2 shadow-sm">
                  <div class="text-[11px] text-stone-400">目标字数</div>
                  <div class="mt-1 text-base font-semibold text-amber-700">{{ outlineProgress.targetWordTotal || '—' }}</div>
                </div>
                <div class="rounded-2xl bg-white/70 px-3 py-2 shadow-sm">
                  <div class="text-[11px] text-stone-400">当前字数</div>
                  <div class="mt-1 text-base font-semibold text-emerald-700">{{ outlineProgress.linkedArticleWordCount }}</div>
                </div>
                <div class="rounded-2xl bg-white/70 px-3 py-2 shadow-sm">
                  <div class="text-[11px] text-stone-400">目标进度</div>
                  <div class="mt-1 text-base font-semibold text-stone-900">{{ outlineProgressPercent === null ? '—' : `${outlineProgressPercent}%` }}</div>
                </div>
              </div>
              <div class="inline-flex rounded-xl bg-stone-100 p-1 text-sm font-semibold text-stone-600">
                <button
                  type="button"
                  :class="[
                    'rounded-lg px-3 py-1.5 transition',
                    viewMode === 'manuscript' ? 'bg-white text-stone-950 shadow-sm' : 'hover:text-stone-900'
                  ]"
                  @click="viewMode = 'manuscript'"
                >
                  {{ t('collectionOutline.manuscriptTab') }}
                </button>
                <button
                  type="button"
                  :class="[
                    'rounded-lg px-3 py-1.5 transition',
                    viewMode === 'board' ? 'bg-white text-stone-950 shadow-sm' : 'hover:text-stone-900'
                  ]"
                  @click="viewMode = 'board'"
                >
                  规划看板
                </button>
                <button
                  type="button"
                  :class="[
                    'rounded-lg px-3 py-1.5 transition',
                    viewMode === 'outline' ? 'bg-white text-stone-950 shadow-sm' : 'hover:text-stone-900'
                  ]"
                  @click="viewMode = 'outline'"
                >
                  {{ t('collectionOutline.outlineTab') }}
                </button>
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
        <template v-if="viewMode === 'manuscript'">
        <section
          class="shrink-0 overflow-y-auto border-r border-stone-200 p-5"
          :style="collectionArticlePane.paneStyle.value"
          data-testid="collections-article-pane"
        >
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
              @contextmenu="openDeleteContextMenu($event, { kind: 'article', id: article.id })"
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
        <PaneResizeHandle data-testid="collections-article-resizer" @pointerdown="collectionArticlePane.startResize" />

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
        </template>

        <template v-else-if="viewMode === 'board'">
          <section class="flex-1 overflow-y-auto p-6" data-testid="collection-planning-board">
            <div class="mb-5 flex flex-col gap-4 rounded-3xl border border-stone-200 bg-white/75 p-5 shadow-sm lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p class="text-xs font-semibold uppercase tracking-[0.22em] text-stone-400">Planning Board</p>
                <h3 class="mt-1 text-2xl font-semibold text-stone-900">长篇规划看板</h3>
                <p class="mt-2 max-w-3xl text-sm leading-6 text-stone-500">
                  按状态查看章节、场景和笔记。这里适合扫全局节奏；需要编辑细节时点开卡片，右侧大纲页仍是精修入口。
                </p>
              </div>
              <div class="flex flex-wrap gap-2">
                <select v-model="outlineFilterType" class="rounded-xl border border-stone-200 bg-white px-3 py-2 text-xs outline-none">
                  <option value="all">全部类型</option>
                  <option v-for="option in outlineTypeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                </select>
                <select v-model="outlineFilterStatus" class="rounded-xl border border-stone-200 bg-white px-3 py-2 text-xs outline-none">
                  <option value="all">全部状态</option>
                  <option v-for="option in outlineStatusOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                </select>
                <button
                  type="button"
                  class="rounded-xl bg-stone-900 px-3 py-2 text-xs font-semibold text-white hover:bg-stone-700"
                  @click="createOutlineItem('chapter')"
                >
                  新建章节
                </button>
              </div>
            </div>

            <div v-if="outlineActionError || store.error" class="mb-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
              {{ outlineActionError || store.error }}
            </div>
            <div v-if="store.outlineLoading" class="rounded-2xl bg-white/70 p-6 text-center text-sm text-stone-400">
              {{ t('common.loading') }}
            </div>
            <div v-else-if="!store.outline.length" class="rounded-3xl border border-dashed border-stone-300 bg-white/70 p-10 text-center">
              <div class="text-lg font-semibold text-stone-700">{{ t('collectionOutline.emptyTitle') }}</div>
              <p class="mt-2 text-sm text-stone-500">{{ t('collectionOutline.emptyHint') }}</p>
              <button class="mt-5 rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white" @click="createOutlineItem('chapter')">
                新建第一章
              </button>
            </div>
            <div v-else class="grid min-w-[920px] grid-cols-5 gap-3">
              <section
                v-for="column in outlineBoardColumns"
                :key="column.value"
                class="min-h-[420px] rounded-3xl border border-stone-200 bg-white/60 p-3"
              >
                <div class="mb-3 flex items-center justify-between gap-2">
                  <div class="font-semibold text-stone-800">{{ column.label }}</div>
                  <span :class="['rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1', outlineStatusTone(column.value)]">
                    {{ column.items.length }}
                  </span>
                </div>
                <div v-if="!column.items.length" class="rounded-2xl border border-dashed border-stone-200 p-4 text-center text-xs leading-5 text-stone-400">
                  暂无条目
                </div>
                <div v-else class="space-y-2">
                  <article
                    v-for="item in column.items"
                    :key="item.id"
                    class="cursor-pointer rounded-2xl border border-stone-200 bg-white p-3 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
                    @click="selectOutlineItem(item.id); viewMode = 'outline'"
                  >
                    <div class="flex items-start justify-between gap-2">
                      <h4 class="line-clamp-2 text-sm font-semibold leading-5 text-stone-900">{{ item.title || t('collectionOutline.untitled') }}</h4>
                      <span class="shrink-0 rounded-full bg-indigo-50 px-2 py-0.5 text-[10px] text-indigo-700">
                        {{ outlineTypeLabel(item.item_type) }}
                      </span>
                    </div>
                    <p class="mt-2 line-clamp-3 text-xs leading-5 text-stone-500">
                      {{ item.summary || t('collectionOutline.noSummary') }}
                    </p>
                    <div class="mt-3 flex flex-wrap gap-1.5">
                      <span v-if="item.entry_id" class="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] text-emerald-700">
                        {{ t('collectionOutline.linked') }}
                      </span>
                      <span v-if="item.target_word_count" class="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] text-amber-700">
                        {{ item.target_word_count }} 字
                      </span>
                      <span v-if="item.pov" class="rounded-full bg-stone-100 px-2 py-0.5 text-[10px] text-stone-500">
                        {{ item.pov }}
                      </span>
                    </div>
                  </article>
                </div>
              </section>
            </div>
          </section>
        </template>

        <template v-else>
          <section
            class="shrink-0 overflow-y-auto border-r border-stone-200 bg-[#fbf7ef] p-5"
            :style="collectionArticlePane.paneStyle.value"
            data-testid="collection-outline-pane"
          >
            <div class="mb-4 flex items-center justify-between gap-3">
              <div>
                <p class="text-xs font-semibold uppercase tracking-[0.22em] text-stone-400">{{ t('collectionOutline.kicker') }}</p>
                <h3 class="mt-1 text-lg font-semibold text-stone-900">{{ t('collectionOutline.title') }}</h3>
              </div>
              <button
                class="rounded-xl bg-stone-900 px-3 py-2 text-xs font-semibold text-white hover:bg-stone-700"
                @click="createOutlineItem('scene')"
              >
                {{ t('collectionOutline.newItem') }}
              </button>
            </div>
            <div class="mb-4 grid grid-cols-2 gap-2">
              <button class="rounded-xl bg-white px-3 py-2 text-xs text-stone-700 ring-1 ring-stone-200" @click="createOutlineItem('part')">
                {{ t('collectionOutline.newPart') }}
              </button>
              <button class="rounded-xl bg-white px-3 py-2 text-xs text-stone-700 ring-1 ring-stone-200" @click="createOutlineItem('chapter')">
                {{ t('collectionOutline.newChapter') }}
              </button>
            </div>
            <div class="mb-4 rounded-2xl border border-stone-200 bg-white/80 p-3 text-xs text-stone-600">
              <div class="grid grid-cols-2 gap-2">
                <div>
                  <div class="text-[11px] text-stone-400">大纲条目</div>
                  <div class="mt-0.5 text-lg font-semibold text-stone-900">{{ outlineProgress.totalItems }}</div>
                </div>
                <div>
                  <div class="text-[11px] text-stone-400">关联文章</div>
                  <div class="mt-0.5 text-lg font-semibold text-stone-900">{{ outlineLinkedArticleCount }}</div>
                </div>
                <div>
                  <div class="text-[11px] text-stone-400">目标字数</div>
                  <div class="mt-0.5 text-lg font-semibold text-amber-700">{{ outlineProgress.targetWordTotal }}</div>
                </div>
                <div>
                  <div class="text-[11px] text-stone-400">当前字数</div>
                  <div class="mt-0.5 text-lg font-semibold text-emerald-700">{{ outlineProgress.linkedArticleWordCount }}</div>
                </div>
              </div>
              <div class="mt-3 flex flex-wrap gap-1.5">
                <span v-for="status in outlineStatusOptions" :key="status.value" class="rounded-full bg-stone-100 px-2 py-0.5">
                  {{ status.label }} {{ outlineProgress.byStatus[status.value] || 0 }}
                </span>
              </div>
            </div>
            <div class="mb-4 space-y-2 rounded-2xl border border-stone-200 bg-white/70 p-3">
              <div class="grid grid-cols-2 gap-2">
                <select v-model="outlineFilterType" class="rounded-xl border border-stone-200 bg-white px-2 py-2 text-xs outline-none">
                  <option value="all">全部类型</option>
                  <option v-for="option in outlineTypeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                </select>
                <select v-model="outlineFilterStatus" class="rounded-xl border border-stone-200 bg-white px-2 py-2 text-xs outline-none">
                  <option value="all">全部状态</option>
                  <option v-for="option in outlineStatusOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                </select>
              </div>
              <label class="flex items-center gap-2 text-xs text-stone-600">
                <input v-model="outlineFilterUnlinkedOnly" type="checkbox" class="h-4 w-4 rounded border-stone-300 text-indigo-600" />
                只看未关联文章
              </label>
              <button
                type="button"
                class="w-full rounded-xl bg-white px-3 py-2 text-xs font-semibold text-stone-700 ring-1 ring-stone-200 hover:bg-stone-50 disabled:opacity-40"
                :disabled="outlineExporting"
                @click="exportOutlineMarkdown"
              >
                {{ outlineExporting ? '导出中…' : '导出当前筛选大纲 Markdown' }}
              </button>
            </div>
            <div v-if="outlineActionError || store.error" class="mb-3 rounded-xl bg-red-50 px-3 py-2 text-xs text-red-700">
              {{ outlineActionError || store.error }}
            </div>
            <div v-if="store.outlineLoading" class="rounded-xl bg-white/70 p-4 text-sm text-stone-400">
              {{ t('common.loading') }}
            </div>
            <div v-else-if="!store.outline.length" class="rounded-2xl border border-dashed border-stone-300 bg-white/70 p-6 text-center">
              <div class="text-sm font-semibold text-stone-700">{{ t('collectionOutline.emptyTitle') }}</div>
              <p class="mt-2 text-xs leading-5 text-stone-500">{{ t('collectionOutline.emptyHint') }}</p>
            </div>
            <div v-else-if="!filteredOutline.length" class="rounded-2xl border border-dashed border-stone-300 bg-white/70 p-6 text-center text-sm text-stone-500">
              当前筛选下没有大纲条目。
            </div>
            <div v-else class="space-y-2">
              <article
                v-for="(item, index) in filteredOutline"
                :key="item.id"
                draggable="true"
                @dragstart="onOutlineDragStart(item.id)"
                @dragover.prevent
                @drop="onOutlineDrop(item.id)"
                @click="selectOutlineItem(item.id)"
                :class="[
                  'group cursor-pointer rounded-2xl border bg-white p-4 shadow-sm transition-all',
                  store.selectedOutlineItemId === item.id
                    ? 'border-indigo-300 shadow-md'
                    : 'border-stone-200 hover:border-stone-300 hover:shadow-md'
                ]"
              >
                <div class="flex items-start gap-3">
                  <div class="w-7 shrink-0 rounded-full bg-stone-100 py-1 text-center text-xs font-semibold text-stone-500">
                    {{ index + 1 }}
                  </div>
                  <div class="min-w-0 flex-1">
                    <div class="flex flex-wrap items-center gap-2">
                      <h4 class="min-w-0 truncate font-semibold text-stone-900">{{ item.title || t('collectionOutline.untitled') }}</h4>
                      <span class="rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] text-indigo-700">
                        {{ outlineTypeLabel(item.item_type) }}
                      </span>
                      <span class="rounded-full bg-stone-100 px-2 py-0.5 text-[11px] text-stone-500">
                        {{ outlineStatusLabel(item.status) }}
                      </span>
                    </div>
                    <p class="mt-2 line-clamp-2 text-sm leading-6 text-stone-600">
                      {{ item.summary || t('collectionOutline.noSummary') }}
                    </p>
                    <div class="mt-3 flex flex-wrap gap-1.5">
                      <span v-if="item.entry_id" class="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] text-emerald-700">
                        {{ t('collectionOutline.linked') }}
                      </span>
                      <span v-if="item.target_word_count" class="rounded-full bg-amber-50 px-2 py-0.5 text-[11px] text-amber-700">
                        {{ item.target_word_count }}
                      </span>
                      <span v-for="tag in item.tags.slice(0, 3)" :key="`${item.id}-${tag}`" class="rounded-full bg-stone-100 px-2 py-0.5 text-[11px] text-stone-500">
                        {{ tag }}
                      </span>
                    </div>
                  </div>
                </div>
                <div class="mt-3 flex justify-end gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                  <button
                    class="rounded-lg px-2 py-1 text-xs text-stone-500 hover:bg-stone-100 disabled:opacity-30"
                    :disabled="index === 0"
                    @click.stop="moveOutlineItem(item.id, -1)"
                  >
                    ↑
                  </button>
                  <button
                    class="rounded-lg px-2 py-1 text-xs text-stone-500 hover:bg-stone-100 disabled:opacity-30"
                    :disabled="index === filteredOutline.length - 1"
                    @click.stop="moveOutlineItem(item.id, 1)"
                  >
                    ↓
                  </button>
                </div>
              </article>
            </div>
          </section>
          <PaneResizeHandle data-testid="collections-outline-resizer" @pointerdown="collectionArticlePane.startResize" />
          <section class="flex-1 overflow-y-auto p-8" data-testid="collection-outline-detail">
            <div v-if="store.selectedOutlineItem" class="mx-auto max-w-4xl space-y-5">
              <div class="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
                <div class="mb-5 flex items-start justify-between gap-4">
                  <div>
                    <p class="text-xs font-semibold uppercase tracking-[0.22em] text-stone-400">{{ t('collectionOutline.detailKicker') }}</p>
                    <h3 class="mt-1 text-2xl font-semibold text-stone-900">{{ t('collectionOutline.detailTitle') }}</h3>
                  </div>
                  <div class="flex gap-2">
                    <button class="rounded-xl bg-stone-100 px-3 py-2 text-sm text-stone-700" @click="createArticleFromOutline">
                      {{ t('collectionOutline.createArticle') }}
                    </button>
                    <button class="rounded-xl bg-stone-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-40" :disabled="outlineSaving" @click="saveOutlineItem">
                      {{ outlineSaving ? t('common.saving') : t('common.save') }}
                    </button>
                  </div>
                </div>

                <div class="grid gap-4 md:grid-cols-2">
                  <label class="md:col-span-2">
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldTitle') }}</span>
                    <input v-model="outlineDraftTitle" class="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200" />
                  </label>
                  <label>
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldType') }}</span>
                    <select v-model="outlineDraftType" class="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200">
                      <option v-for="option in outlineTypeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                    </select>
                  </label>
                  <label>
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldStatus') }}</span>
                    <select v-model="outlineDraftStatus" class="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200">
                      <option v-for="option in outlineStatusOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                    </select>
                  </label>
                  <label>
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldEntry') }}</span>
                    <select v-model="outlineDraftEntryId" class="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200">
                      <option value="">{{ t('collectionOutline.noLinkedArticle') }}</option>
                      <option v-for="article in allArticles" :key="article.id" :value="article.id">
                        {{ article.title || t('articles.untitled') }}
                      </option>
                    </select>
                  </label>
                  <label>
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldTargetWords') }}</span>
                    <input v-model.number="outlineDraftTargetWords" type="number" min="0" class="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200" />
                  </label>
                  <label class="md:col-span-2">
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldSummary') }}</span>
                    <textarea v-model="outlineDraftSummary" rows="4" class="w-full resize-none rounded-xl border border-stone-200 px-3 py-2 text-sm leading-6 outline-none focus:ring-2 focus:ring-indigo-200" />
                  </label>
                  <label>
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldPov') }}</span>
                    <input v-model="outlineDraftPov" class="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200" />
                  </label>
                  <label>
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldTimeline') }}</span>
                    <input v-model="outlineDraftTimeline" class="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200" />
                  </label>
                  <label>
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldSetting') }}</span>
                    <input v-model="outlineDraftSetting" class="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200" />
                  </label>
                  <label>
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldTags') }}</span>
                    <input v-model="outlineDraftTags" class="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200" :placeholder="t('collectionOutline.tagsPlaceholder')" />
                  </label>
                  <label class="md:col-span-2">
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldNotes') }}</span>
                    <textarea v-model="outlineDraftNotes" rows="6" class="w-full resize-none rounded-xl border border-stone-200 px-3 py-2 text-sm leading-6 outline-none focus:ring-2 focus:ring-indigo-200" :placeholder="t('collectionOutline.notesPlaceholder')" />
                  </label>
                </div>
              </div>

              <div class="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
                <div class="flex items-center justify-between gap-4">
                  <div>
                    <h4 class="font-semibold text-stone-900">{{ t('collectionOutline.linkedArticle') }}</h4>
                    <p class="mt-1 text-sm text-stone-500">
                      {{ outlineLinkedArticle?.title || t('collectionOutline.noLinkedArticle') }}
                    </p>
                  </div>
                  <button
                    class="rounded-xl bg-stone-100 px-3 py-2 text-sm text-stone-700 disabled:opacity-40"
                    :disabled="!store.selectedOutlineItem.entry_id"
                    @click="openLinkedOutlineArticle"
                  >
                    {{ t('collectionOutline.openArticle') }}
                  </button>
                </div>
              </div>

              <div class="flex justify-between">
                <button class="rounded-xl bg-red-50 px-4 py-2 text-sm text-red-700 hover:bg-red-100" @click="deleteSelectedOutlineItem">
                  {{ t('collectionOutline.deleteItem') }}
                </button>
              </div>
            </div>
            <div v-else class="mt-20 text-center text-stone-400">
              {{ t('collectionOutline.selectItem') }}
            </div>
          </section>
        </template>
      </div>
    </main>

    <ContextMenu
      :open="deleteContextMenuOpen"
      :x="deleteContextMenuX"
      :y="deleteContextMenuY"
      :items="[{ key: 'delete', label: t('common.delete'), danger: true }]"
      @close="closeDeleteContextMenu"
      @select="handleDeleteContextMenuSelect"
    />

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
