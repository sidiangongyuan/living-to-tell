<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { articlesApi, type Entry } from '../../api/articles'
import type {
  CollectionArticle,
  CollectionOutlineItem,
  CollectionOutlineItemInput,
  CollectionProjectType,
  OutlineItemStatus,
  OutlineItemType,
} from '../../api/collections'
import ContextMenu from '../../components/ContextMenu.vue'
import GuidedTourOverlay from '../../components/GuidedTourOverlay.vue'
import PaneResizeHandle from '../../components/PaneResizeHandle.vue'
import { useResizablePane } from '../../composables/useResizablePane'
import { useI18n } from '../../i18n'
import { useSettingsStore } from '../../stores/settings'
import {
  buildOutlineMarkdown,
  buildOutlineProgressSummary,
  filterOutlineItems,
  type OutlineFilters,
} from './outlineEnhancements'
import {
  articleTitleForId,
  articleTypeForProject,
  boardTabLabel,
  buildManuscriptTree,
  canUseParent,
  collectionProjectType,
  defaultChildType,
  exportTabLabel,
  flattenManuscriptTree,
  labelsForProject,
  projectTypeLabel,
  structureTabLabel,
  typeLabelForProject,
  unplannedArticles,
  type ManuscriptTreeNode,
} from './manuscriptStructure'
import { useCollectionsStore } from './store'

const LAST_SELECTED_COLLECTION_KEY = 'living_to_tell_last_selected_collection_id'

const store = useCollectionsStore()
const { t, locale } = useI18n()
const router = useRouter()
const route = useRoute()
const settings = useSettingsStore()

const allArticles = ref<Entry[]>([])
const articlePickerOpen = ref(false)
const createDialogOpen = ref(false)
const selectedArticleIds = ref<string[]>([])
const viewMode = ref<'structure' | 'board' | 'export'>('structure')
const newTitle = ref('')
const newDescription = ref('')
const newProjectType = ref<CollectionProjectType>('general')
const draftTitle = ref('')
const draftDescription = ref('')
const draftProjectType = ref<CollectionProjectType>('general')
const savingMeta = ref(false)
const dragOutlineItemId = ref<string | null>(null)
const actionError = ref<string | null>(null)
const outlineActionError = ref<string | null>(null)
const outlineSaving = ref(false)
const outlineExporting = ref(false)
const outlineDraftTitle = ref('')
const outlineDraftType = ref<OutlineItemType>('scene')
const outlineDraftStatus = ref<OutlineItemStatus>('idea')
const outlineDraftParentId = ref('')
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
const tourOpen = ref(false)
const tourStepIndex = ref(0)

const collectionListPane = useResizablePane({
  key: 'collections:list',
  defaultSize: 240,
  minSize: 240,
  maxSize: 420,
})
const structurePane = useResizablePane({
  key: 'collections:structure',
  defaultSize: 380,
  minSize: 320,
  maxSize: 560,
})

const deleteContextMenuOpen = ref(false)
const deleteContextMenuX = ref(0)
const deleteContextMenuY = ref(0)
const deleteContextTarget = ref<{ kind: 'collection'; id: string } | null>(null)

const projectType = computed(() => collectionProjectType(store.selectedCollection))
const projectLabels = computed(() => labelsForProject(projectType.value, locale.value))
const currentArticleIds = computed(() => new Set(store.articles.map((article) => article.id)))
const outlineProgress = computed(() => buildOutlineProgressSummary(store.outline, store.articles))
const outlineProgressPercent = computed(() => {
  if (!outlineProgress.value.targetWordTotal) return null
  return Math.min(100, Math.round((outlineProgress.value.linkedArticleWordCount / outlineProgress.value.targetWordTotal) * 100))
})
const manuscriptTree = computed(() => buildManuscriptTree(store.outline))
const flatTree = computed(() => flattenManuscriptTree(manuscriptTree.value))
const filteredOutline = computed(() => filterOutlineItems(store.outline, {
  type: outlineFilterType.value,
  status: outlineFilterStatus.value,
  unlinkedOnly: outlineFilterUnlinkedOnly.value,
}))
const unplanned = computed(() => unplannedArticles(store.articles, store.outline))
const hasLinkedStructure = computed(() => store.outline.some((item) => Boolean(item.entry_id)))
const selectedParent = computed(() => {
  const parentId = store.selectedOutlineItem?.parent_id
  return parentId ? store.outline.find((item) => item.id === parentId) ?? null : null
})
const outlineLinkedArticle = computed(() => {
  const entryId = store.selectedOutlineItem?.entry_id
  if (!entryId) return null
  return allArticles.value.find((article) => article.id === entryId)
    ?? store.articles.find((article) => article.id === entryId)
    ?? null
})
const parentOptions = computed(() => {
  const currentId = store.selectedOutlineItemId
  return flatTree.value.filter((node) =>
    !currentId || node.item.id !== currentId && canUseParent(store.outline, currentId, node.item.id)
  )
})
const outlineBoardColumns = computed(() =>
  outlineStatusOptions.value.map((status) => ({
    ...status,
    items: filteredOutline.value.filter((item) => item.status === status.value),
  }))
)

const projectTypeOptions = computed(() => ([
  { value: 'general' as const, label: projectTypeLabel('general', locale.value) },
  { value: 'novel' as const, label: projectTypeLabel('novel', locale.value) },
  { value: 'essay' as const, label: projectTypeLabel('essay', locale.value) },
  { value: 'nonfiction' as const, label: projectTypeLabel('nonfiction', locale.value) },
]))
const outlineTypeOptions = computed(() => ([
  { value: 'part' as const, label: projectLabels.value.part },
  { value: 'chapter' as const, label: projectLabels.value.chapter },
  { value: 'scene' as const, label: projectLabels.value.scene },
  { value: 'note' as const, label: projectLabels.value.note },
]))
const outlineStatusOptions = computed(() => ([
  { value: 'idea' as const, label: t('collectionOutline.statusIdea') },
  { value: 'drafting' as const, label: t('collectionOutline.statusDrafting') },
  { value: 'revising' as const, label: t('collectionOutline.statusRevising') },
  { value: 'done' as const, label: t('collectionOutline.statusDone') },
  { value: 'parked' as const, label: t('collectionOutline.statusParked') },
]))

interface CollectionTourStep {
  id: string
  title: string
  body: string
  target?: string
}

const collectionTourSteps = computed<CollectionTourStep[]>(() => {
  if (!store.selectedCollection) {
    return [
      {
        id: 'intro',
        title: t('collectionsTour.introTitle'),
        body: t('collectionsTour.introBody'),
        target: '[data-tour="collections-list"]',
      },
      {
        id: 'create',
        title: t('collectionsTour.createTitle'),
        body: t('collectionsTour.createBody'),
        target: '[data-tour="collections-create"]',
      },
    ]
  }
  return [
    {
      id: 'intro',
      title: t('collectionsTour.introTitle'),
      body: t('collectionsTour.introBody'),
      target: '[data-tour="collections-header"]',
    },
    {
      id: 'structure',
      title: t('collectionsTour.structureTitle'),
      body: t('collectionsTour.structureBody'),
      target: '[data-tour="collections-structure"]',
    },
    {
      id: 'project-type',
      title: t('collectionsTour.projectTypeTitle'),
      body: t('collectionsTour.projectTypeBody'),
      target: '[data-tour="collections-project-type"]',
    },
    {
      id: 'tree',
      title: t('collectionsTour.treeTitle'),
      body: t('collectionsTour.treeBody'),
      target: '[data-tour="manuscript-tree"]',
    },
    {
      id: 'unplanned',
      title: t('collectionsTour.unplannedTitle'),
      body: t('collectionsTour.unplannedBody'),
      target: '[data-tour="unplanned-articles"]',
    },
    {
      id: 'node-types',
      title: t('collectionsTour.typeTitle'),
      body: t('collectionsTour.typeBody'),
      target: '[data-tour="outline-type-field"]',
    },
    {
      id: 'linked-article',
      title: t('collectionsTour.linkedArticleTitle'),
      body: t('collectionsTour.linkedArticleBody'),
      target: '[data-tour="outline-linked-article"]',
    },
    {
      id: 'board',
      title: t('collectionsTour.boardTitle'),
      body: t('collectionsTour.boardBody'),
      target: '[data-tour="collections-board"]',
    },
    {
      id: 'export',
      title: t('collectionsTour.exportTitle'),
      body: t('collectionsTour.exportBody'),
      target: '[data-tour="collections-export-panel"]',
    },
    {
      id: 'done',
      title: t('collectionsTour.doneTitle'),
      body: t('collectionsTour.doneBody'),
      target: '[data-tour="collections-tabs"]',
    },
  ]
})

const currentTourProgressLabel = computed(() =>
  t('collectionsTour.progress', {
    current: Math.min(tourStepIndex.value + 1, collectionTourSteps.value.length),
    total: collectionTourSteps.value.length,
  })
)

onMounted(async () => {
  await store.loadCollections()
  const lastCollectionId = localStorage.getItem(LAST_SELECTED_COLLECTION_KEY)
  if (lastCollectionId && store.collections.some((collection) => collection.id === lastCollectionId)) {
    await store.selectCollection(lastCollectionId)
  }
  allArticles.value = await articlesApi.listArticles(500)
  if (route.query.tour === 'collection' || !settings.collectionsTourDismissed) {
    startCollectionTour()
    if (route.query.tour === 'collection') {
      void clearCollectionTourQuery()
    }
  }
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
    draftProjectType.value = collectionProjectType(collection)
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

watch(
  () => route.query.tour,
  (value) => {
    if (value === 'collection') {
      startCollectionTour()
      void clearCollectionTourQuery()
    }
  }
)

watch(
  () => store.selectedCollectionId,
  () => {
    if (!tourOpen.value) return
    tourStepIndex.value = 0
    prepareCollectionTourStep(0)
  }
)

function prepareCollectionTourStep(index = tourStepIndex.value) {
  const step = collectionTourSteps.value[index]
  if (!step || !store.selectedCollection) return
  if (step.id === 'board') {
    viewMode.value = 'board'
  } else if (step.id === 'export') {
    viewMode.value = 'export'
  } else {
    viewMode.value = 'structure'
  }
}

function startCollectionTour() {
  tourStepIndex.value = 0
  tourOpen.value = true
  prepareCollectionTourStep(0)
}

function closeCollectionTour() {
  tourOpen.value = false
  settings.dismissCollectionsTour()
  void clearCollectionTourQuery()
}

function finishCollectionTour() {
  closeCollectionTour()
}

async function clearCollectionTourQuery() {
  if (route.query.tour !== 'collection') return
  const query = { ...route.query }
  delete query.tour
  await router.replace({ name: 'collections', query })
}

async function nextCollectionTourStep() {
  tourStepIndex.value = Math.min(tourStepIndex.value + 1, collectionTourSteps.value.length - 1)
  prepareCollectionTourStep()
  await nextTick()
}

async function previousCollectionTourStep() {
  tourStepIndex.value = Math.max(tourStepIndex.value - 1, 0)
  prepareCollectionTourStep()
  await nextTick()
}

function articlePreview(body: string): string {
  const compact = body.trim().replace(/\s+/g, ' ')
  return compact.slice(0, 140) || t('collections.emptyArticle')
}

function outlineTypeLabel(type: OutlineItemType): string {
  return typeLabelForProject(type, projectType.value, locale.value)
}

function outlineStatusLabel(status: OutlineItemStatus): string {
  return outlineStatusOptions.value.find((item) => item.value === status)?.label ?? status
}

function outlineStatusTone(status: OutlineItemStatus): string {
  if (status === 'done') return 'bg-emerald-50 text-emerald-700 ring-emerald-100'
  if (status === 'drafting') return 'bg-blue-50 text-blue-700 ring-blue-100'
  if (status === 'revising') return 'bg-violet-50 text-violet-700 ring-violet-100'
  if (status === 'parked') return 'bg-stone-100 text-stone-500 ring-stone-200'
  return 'bg-amber-50 text-amber-700 ring-amber-100'
}

function nodeTitle(node: ManuscriptTreeNode): string {
  if (node.item.title) return node.item.title
  if (node.item.entry_id) return articleTitleForId(node.item.entry_id, store.articles)
  return t('collectionOutline.untitled')
}

function defaultTitleForType(type: OutlineItemType): string {
  if (type === 'part') return `${projectLabels.value.part}：`
  if (type === 'chapter') return `${projectLabels.value.chapter}：`
  if (type === 'scene') return `${projectLabels.value.scene}：`
  return `${projectLabels.value.note}：`
}

async function openCreateDialog() {
  newTitle.value = ''
  newDescription.value = ''
  newProjectType.value = 'general'
  createDialogOpen.value = true
}

async function createCollection() {
  if (!newTitle.value.trim()) return
  actionError.value = null
  try {
    await store.createCollection(newTitle.value.trim(), newDescription.value.trim(), newProjectType.value)
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
    && draftProjectType.value === collectionProjectType(store.selectedCollection)
  ) {
    return true
  }
  savingMeta.value = true
  try {
    await store.updateCollection(
      store.selectedCollection.id,
      draftTitle.value.trim(),
      draftDescription.value.trim(),
      draftProjectType.value,
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
  outlineDraftType.value = item?.item_type ?? articleTypeForProject(projectType.value)
  outlineDraftStatus.value = item?.status ?? 'idea'
  outlineDraftParentId.value = item?.parent_id ?? ''
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
    parent_id: outlineDraftParentId.value || null,
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

function payloadFromItem(
  item: CollectionOutlineItem,
  patch: Partial<CollectionOutlineItemInput>,
): CollectionOutlineItemInput {
  return {
    parent_id: item.parent_id,
    entry_id: item.entry_id,
    title: item.title,
    item_type: item.item_type,
    status: item.status,
    summary: item.summary,
    notes: item.notes,
    pov: item.pov,
    setting: item.setting,
    timeline: item.timeline,
    tags: item.tags,
    target_word_count: item.target_word_count,
    ...patch,
  }
}

async function createOutlineItem(type: OutlineItemType = articleTypeForProject(projectType.value), parentId: string | null = null) {
  if (!store.selectedCollection) return
  outlineActionError.value = null
  try {
    const created = await store.createOutlineItem({
      title: defaultTitleForType(type),
      item_type: type,
      status: 'idea',
      parent_id: parentId,
    })
    if (created) {
      store.selectOutlineItem(created.id)
      loadOutlineDraft(created)
      viewMode.value = 'structure'
    }
  } catch (e) {
    outlineActionError.value = e instanceof Error ? e.message : String(e)
  }
}

async function createChildOutlineItem() {
  const parent = store.selectedOutlineItem
  const type = defaultChildType(parent?.item_type ?? null, projectType.value)
  await createOutlineItem(type, parent?.id ?? null)
}

async function createSiblingOutlineItem() {
  const selected = store.selectedOutlineItem
  await createOutlineItem(selected?.item_type ?? defaultChildType(null, projectType.value), selected?.parent_id ?? null)
}

async function createNodeFromArticle(article: CollectionArticle, parentId: string | null = store.selectedOutlineItemId) {
  if (!store.selectedCollection) return
  outlineActionError.value = null
  try {
    const created = await store.createOutlineItem({
      title: article.title || t('articles.untitled'),
      item_type: articleTypeForProject(projectType.value),
      status: article.body.trim() ? 'drafting' : 'idea',
      entry_id: article.id,
      parent_id: parentId,
      target_word_count: article.word_count || null,
    })
    if (created) {
      store.selectOutlineItem(created.id)
      viewMode.value = 'structure'
    }
  } catch (e) {
    outlineActionError.value = e instanceof Error ? e.message : String(e)
  }
}

async function saveOutlineItem() {
  if (!store.selectedOutlineItem) return
  const payload = outlinePayload()
  if (!canUseParent(store.outline, store.selectedOutlineItem.id, payload.parent_id ?? null)) {
    outlineActionError.value = t('collectionOutline.parentCycleError')
    return
  }
  outlineSaving.value = true
  outlineActionError.value = null
  try {
    await store.updateOutlineItem(store.selectedOutlineItem.id, payload)
    if (payload.entry_id && !store.articles.some((article) => article.id === payload.entry_id)) {
      await store.addArticles([payload.entry_id])
      await store.loadOutline()
    }
  } catch (e) {
    outlineActionError.value = e instanceof Error ? e.message : String(e)
  } finally {
    outlineSaving.value = false
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
    || (payload.parent_id ?? null) !== current.parent_id
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

async function selectOutlineItem(id: string) {
  const saved = await saveOutlineItemIfDirty()
  if (!saved) return
  store.selectOutlineItem(id)
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

async function moveOutlineItem(itemId: string, direction: -1 | 1) {
  const item = store.outline.find((row) => row.id === itemId)
  if (!item) return
  const global = [...store.outline].sort((a, b) => a.sort_order - b.sort_order)
  const siblings = global.filter((row) => (row.parent_id ?? null) === (item.parent_id ?? null))
  const index = siblings.findIndex((row) => row.id === itemId)
  const next = siblings[index + direction]
  if (index < 0 || !next) return
  const ids = global.map((row) => row.id)
  const from = ids.indexOf(item.id)
  const to = ids.indexOf(next.id)
  const [moving] = ids.splice(from, 1)
  ids.splice(to, 0, moving)
  try {
    await store.reorderOutline(ids)
  } catch {
    // Store owns visible error state.
  }
}

async function changeOutlineParent(item: CollectionOutlineItem, parentId: string | null) {
  if (!canUseParent(store.outline, item.id, parentId)) {
    outlineActionError.value = t('collectionOutline.parentCycleError')
    return
  }
  try {
    await store.updateOutlineItem(item.id, payloadFromItem(item, { parent_id: parentId }))
  } catch (e) {
    outlineActionError.value = e instanceof Error ? e.message : String(e)
  }
}

function onOutlineDragStart(itemId: string) {
  dragOutlineItemId.value = itemId
}

async function onOutlineDrop(targetId: string) {
  const movingId = dragOutlineItemId.value
  dragOutlineItemId.value = null
  if (!movingId || movingId === targetId) return
  const moving = store.outline.find((item) => item.id === movingId)
  const target = store.outline.find((item) => item.id === targetId)
  if (!moving || !target) return
  await changeOutlineParent(moving, target.parent_id ?? null)
  const global = [...store.outline].sort((a, b) => a.sort_order - b.sort_order).map((item) => item.id)
  const from = global.indexOf(movingId)
  const to = global.indexOf(targetId)
  if (from < 0 || to < 0) return
  const [row] = global.splice(from, 1)
  global.splice(to, 0, row)
  await store.reorderOutline(global)
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

async function openLinkedOutlineArticle() {
  if (!store.selectedOutlineItem?.entry_id) return
  await router.push({
    name: 'articles',
    query: { id: store.selectedOutlineItem.entry_id },
  })
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

function togglePickArticle(entryId: string) {
  if (currentArticleIds.value.has(entryId)) return
  if (selectedArticleIds.value.includes(entryId)) {
    selectedArticleIds.value = selectedArticleIds.value.filter((id) => id !== entryId)
  } else {
    selectedArticleIds.value = [...selectedArticleIds.value, entryId]
  }
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

async function removeUnplannedArticle(entryId: string) {
  if (!confirm(t('collections.confirmRemoveArticle'))) return
  try {
    await store.removeArticle(entryId)
  } catch (e) {
    actionError.value = e instanceof Error ? e.message : String(e)
  }
}

async function selectCollection(id: string) {
  const saved = await saveCollectionMetaIfNeeded()
  if (!saved) return
  await store.selectCollection(id)
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
    await import('../../utils/exportFile').then(({ saveBlobWithDialog }) =>
      saveBlobWithDialog(blob, safeCollectionFilename(`${store.selectedCollection?.title || 'collection'}-planning`, 'md'), 'md')
    )
  } catch (e) {
    outlineActionError.value = e instanceof Error ? `导出大纲失败：${e.message}` : `导出大纲失败：${String(e)}`
  } finally {
    outlineExporting.value = false
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
  if (store.selectedCollectionId === target.id) {
    void deleteSelectedCollection()
    return
  }
  void selectCollection(target.id).then(() => deleteSelectedCollection())
}
</script>

<template>
  <div class="flex h-full overflow-hidden bg-[#f5f1e8] text-stone-900">
    <aside
      class="flex shrink-0 flex-col border-r border-stone-200 bg-[#2d2a25] text-stone-100"
      :style="collectionListPane.paneStyle.value"
      data-testid="collections-list-pane"
      data-tour="collections-list"
    >
      <div class="border-b border-white/10 p-5">
        <div class="flex items-center justify-between gap-3">
          <div>
            <p class="text-xs uppercase tracking-[0.28em] text-stone-400">{{ t('collections.shelf') }}</p>
            <h2 class="mt-1 text-xl font-semibold">{{ t('collections.title') }}</h2>
          </div>
          <button
            class="rounded-xl bg-amber-200 px-3 py-2 text-sm font-semibold text-stone-900 hover:bg-amber-100"
            data-tour="collections-create"
            @click="openCreateDialog"
          >
            {{ t('collections.newCollection') }}
          </button>
        </div>
        <p class="mt-3 text-sm text-stone-400">
          {{ t('collections.total', { count: store.collections.length }) }}
        </p>
      </div>

      <div class="flex-1 space-y-2 overflow-y-auto p-3">
        <div v-if="store.loading" class="p-4 text-sm text-stone-400">{{ t('common.loading') }}</div>
        <div v-else-if="store.error" class="p-4 text-sm text-red-300">{{ store.error }}</div>
        <div v-else-if="!store.collections.length" class="p-4 text-sm text-stone-400">
          {{ t('collections.emptyCollections') }}
        </div>
        <button
          v-for="collection in store.collections"
          :key="collection.id"
          :class="[
            'w-full rounded-2xl p-4 text-left transition-all',
            store.selectedCollectionId === collection.id
              ? 'bg-amber-100 text-stone-950 shadow-lg'
              : 'bg-white/5 text-stone-200 hover:bg-white/10'
          ]"
          @click="selectCollection(collection.id)"
          @contextmenu="openDeleteContextMenu($event, { kind: 'collection', id: collection.id })"
        >
          <div class="font-semibold leading-snug">{{ collection.title || t('collections.untitled') }}</div>
          <div class="mt-1 line-clamp-2 text-xs opacity-70">
            {{ collection.description || t('collections.noDescription') }}
          </div>
          <div class="mt-3 flex flex-wrap gap-2 text-xs opacity-75">
            <span>{{ projectTypeLabel(collection.project_type, locale) }}</span>
            <span>{{ t('collections.articleCount', { count: collection.article_count }) }}</span>
          </div>
        </button>
      </div>
    </aside>
    <PaneResizeHandle data-testid="collections-list-resizer" @pointerdown="collectionListPane.startResize" />

    <main class="flex min-w-0 flex-1 flex-col">
      <header class="border-b border-stone-200 bg-[#fbf7ef]/95 px-6 py-5">
        <template v-if="store.selectedCollection">
          <div class="flex items-start justify-between gap-4">
            <div class="min-w-0 flex-1 space-y-3" data-tour="collections-header">
              <input
                v-model="draftTitle"
                class="w-full bg-transparent text-3xl font-semibold tracking-tight outline-none"
                :placeholder="t('collections.titlePlaceholder')"
                @blur="saveCollectionMeta"
              />
              <textarea
                v-model="draftDescription"
                rows="2"
                class="w-full resize-none bg-transparent text-sm leading-relaxed text-stone-600 outline-none"
                :placeholder="t('collections.descriptionPlaceholder')"
                @blur="saveCollectionMeta"
              />
              <div class="flex flex-wrap items-center gap-2 text-xs text-stone-500">
                <label class="flex items-center gap-2 rounded-full bg-white px-3 py-1.5 shadow-sm" data-tour="collections-project-type">
                  <span>{{ t('collectionOutline.projectType') }}</span>
                  <select
                    v-model="draftProjectType"
                    class="bg-transparent text-xs font-semibold text-stone-800 outline-none"
                    @change="saveCollectionMeta"
                  >
                    <option v-for="option in projectTypeOptions" :key="option.value" :value="option.value">
                      {{ option.label }}
                    </option>
                  </select>
                </label>
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
                  <div class="text-[11px] text-stone-400">{{ t('collectionOutline.linkedStructure') }}</div>
                  <div class="mt-1 text-base font-semibold text-stone-900">{{ outlineProgress.linkedItems }} / {{ outlineProgress.totalItems }}</div>
                </div>
                <div class="rounded-2xl bg-white/70 px-3 py-2 shadow-sm">
                  <div class="text-[11px] text-stone-400">{{ t('collectionOutline.targetWords') }}</div>
                  <div class="mt-1 text-base font-semibold text-amber-700">{{ outlineProgress.targetWordTotal || '—' }}</div>
                </div>
                <div class="rounded-2xl bg-white/70 px-3 py-2 shadow-sm">
                  <div class="text-[11px] text-stone-400">{{ t('collectionOutline.currentWords') }}</div>
                  <div class="mt-1 text-base font-semibold text-emerald-700">{{ outlineProgress.linkedArticleWordCount }}</div>
                </div>
                <div class="rounded-2xl bg-white/70 px-3 py-2 shadow-sm">
                  <div class="text-[11px] text-stone-400">{{ t('collectionOutline.targetProgress') }}</div>
                  <div class="mt-1 text-base font-semibold text-stone-900">{{ outlineProgressPercent === null ? '—' : `${outlineProgressPercent}%` }}</div>
                </div>
              </div>
              <div class="space-y-2" data-tour="collections-tabs">
                <div class="inline-flex rounded-xl bg-stone-100 p-1 text-sm font-semibold text-stone-600">
                  <button
                    type="button"
                    :class="[
                      'rounded-lg px-3 py-1.5 transition',
                      viewMode === 'structure' ? 'bg-white text-stone-950 shadow-sm' : 'hover:text-stone-900'
                    ]"
                    @click="viewMode = 'structure'"
                  >
                    {{ structureTabLabel(locale) }}
                  </button>
                  <button
                    type="button"
                    :class="[
                      'rounded-lg px-3 py-1.5 transition',
                      viewMode === 'board' ? 'bg-white text-stone-950 shadow-sm' : 'hover:text-stone-900'
                    ]"
                    @click="viewMode = 'board'"
                  >
                    {{ boardTabLabel(locale) }}
                  </button>
                  <button
                    type="button"
                    :class="[
                      'rounded-lg px-3 py-1.5 transition',
                      viewMode === 'export' ? 'bg-white text-stone-950 shadow-sm' : 'hover:text-stone-900'
                    ]"
                    @click="viewMode = 'export'"
                  >
                    {{ exportTabLabel(locale) }}
                  </button>
                </div>
                <p class="max-w-3xl text-xs leading-5 text-stone-500">
                  {{
                    viewMode === 'structure'
                      ? t('collectionOutline.structureHelp')
                      : viewMode === 'board'
                        ? t('collectionOutline.boardHelp')
                        : t('collectionOutline.exportHelp')
                  }}
                </p>
              </div>
            </div>
            <div class="flex flex-wrap justify-end gap-2">
              <button
                class="rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white hover:bg-stone-700"
                @click="openArticlePicker"
              >
                {{ t('collections.addArticles') }}
              </button>
              <button
                class="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700 hover:bg-red-100"
                @click="deleteSelectedCollection"
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
            class="rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white"
            @click="openCreateDialog"
          >
            {{ t('collections.newCollection') }}
          </button>
        </div>
      </header>

      <div class="flex min-h-0 flex-1 overflow-hidden">
        <template v-if="viewMode === 'structure'">
          <section
            class="shrink-0 overflow-y-auto border-r border-stone-200 bg-[#fbf7ef] p-5"
            :style="structurePane.paneStyle.value"
            data-testid="collection-outline-pane"
            data-tour="collections-structure"
          >
            <div class="mb-4 flex items-start justify-between gap-3">
              <div>
                <p class="text-xs font-semibold uppercase tracking-[0.22em] text-stone-400">{{ t('collectionOutline.structureKicker') }}</p>
                <h3 class="mt-1 text-lg font-semibold text-stone-900">{{ t('collectionOutline.structureTitle') }}</h3>
              </div>
              <button
                class="rounded-xl bg-stone-900 px-3 py-2 text-xs font-semibold text-white hover:bg-stone-700"
                @click="createOutlineItem(defaultChildType(null, projectType), null)"
              >
                {{ t('collectionOutline.newTopLevel') }}
              </button>
            </div>
            <div class="mb-4 grid grid-cols-2 gap-2">
              <button
                v-for="option in outlineTypeOptions"
                :key="option.value"
                class="rounded-xl bg-white px-3 py-2 text-xs text-stone-700 ring-1 ring-stone-200 hover:bg-stone-50"
                @click="createOutlineItem(option.value, null)"
              >
                + {{ option.label }}
              </button>
            </div>

            <div class="mb-4 rounded-2xl border border-stone-200 bg-white/80 p-3 text-xs text-stone-600">
              <p class="leading-5">{{ t('collectionOutline.structureRule') }}</p>
            </div>

            <div v-if="outlineActionError || store.error" class="mb-3 rounded-xl bg-red-50 px-3 py-2 text-xs text-red-700">
              {{ outlineActionError || store.error }}
            </div>
            <div v-if="store.outlineLoading" class="rounded-xl bg-white/70 p-4 text-sm text-stone-400">
              {{ t('common.loading') }}
            </div>
            <div v-else-if="!store.outline.length" class="rounded-2xl border border-dashed border-stone-300 bg-white/70 p-6 text-center">
              <div class="text-sm font-semibold text-stone-700">{{ t('collectionOutline.emptyTitle') }}</div>
              <p class="mt-2 text-xs leading-5 text-stone-500">{{ t('collectionOutline.emptyStructureHint') }}</p>
            </div>
            <div v-else class="space-y-2" data-tour="manuscript-tree">
              <article
                v-for="node in flatTree"
                :key="node.item.id"
                draggable="true"
                :style="{ paddingLeft: `${12 + node.depth * 18}px` }"
                :class="[
                  'group cursor-pointer rounded-2xl border bg-white py-3 pr-3 shadow-sm transition-all',
                  store.selectedOutlineItemId === node.item.id
                    ? 'border-indigo-300 shadow-md'
                    : 'border-stone-200 hover:border-stone-300 hover:shadow-md'
                ]"
                @click="selectOutlineItem(node.item.id)"
                @dragstart="onOutlineDragStart(node.item.id)"
                @dragover.prevent
                @drop="onOutlineDrop(node.item.id)"
              >
                <div class="flex items-start gap-3">
                  <div class="w-8 shrink-0 rounded-full bg-stone-100 py-1 text-center text-[11px] font-semibold text-stone-500">
                    {{ node.path.join('.') }}
                  </div>
                  <div class="min-w-0 flex-1">
                    <div class="flex flex-wrap items-center gap-2">
                      <h4 class="min-w-0 truncate font-semibold text-stone-900">{{ nodeTitle(node) }}</h4>
                      <span class="rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] text-indigo-700">
                        {{ outlineTypeLabel(node.item.item_type) }}
                      </span>
                      <span :class="['rounded-full px-2 py-0.5 text-[11px] ring-1', outlineStatusTone(node.item.status)]">
                        {{ outlineStatusLabel(node.item.status) }}
                      </span>
                    </div>
                    <p class="mt-2 line-clamp-2 text-xs leading-5 text-stone-500">
                      {{ node.item.summary || t('collectionOutline.noSummary') }}
                    </p>
                    <div class="mt-2 flex flex-wrap gap-1.5">
                      <span v-if="node.item.entry_id" class="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] text-emerald-700">
                        {{ t('collectionOutline.linked') }}
                      </span>
                      <span v-if="node.children.length" class="rounded-full bg-stone-100 px-2 py-0.5 text-[11px] text-stone-500">
                        {{ t('collectionOutline.childCount', { count: node.children.length }) }}
                      </span>
                    </div>
                  </div>
                </div>
                <div class="mt-3 flex flex-wrap justify-end gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                  <button
                    class="rounded-lg px-2 py-1 text-xs text-stone-500 hover:bg-stone-100"
                    @click.stop="moveOutlineItem(node.item.id, -1)"
                  >
                    ↑
                  </button>
                  <button
                    class="rounded-lg px-2 py-1 text-xs text-stone-500 hover:bg-stone-100"
                    @click.stop="moveOutlineItem(node.item.id, 1)"
                  >
                    ↓
                  </button>
                  <button
                    class="rounded-lg px-2 py-1 text-xs text-stone-500 hover:bg-stone-100"
                    @click.stop="createOutlineItem(defaultChildType(node.item.item_type, projectType), node.item.id)"
                  >
                    {{ t('collectionOutline.newChild') }}
                  </button>
                </div>
              </article>
            </div>

            <div class="mt-5 rounded-2xl border border-stone-200 bg-white/80 p-4" data-tour="unplanned-articles">
              <div class="flex items-center justify-between gap-3">
                <div>
                  <h4 class="text-sm font-semibold text-stone-900">{{ t('collectionOutline.unplannedTitle') }}</h4>
                  <p class="mt-1 text-xs leading-5 text-stone-500">{{ t('collectionOutline.unplannedHelp') }}</p>
                </div>
                <button class="rounded-xl bg-stone-100 px-3 py-2 text-xs text-stone-700" @click="openArticlePicker">
                  {{ t('collections.addArticles') }}
                </button>
              </div>
              <div v-if="!unplanned.length" class="mt-4 rounded-xl border border-dashed border-stone-200 p-4 text-center text-xs text-stone-400">
                {{ t('collectionOutline.noUnplanned') }}
              </div>
              <div v-else class="mt-4 space-y-2">
                <article v-for="article in unplanned" :key="article.id" class="rounded-xl border border-stone-200 bg-white p-3">
                  <div class="font-semibold text-sm text-stone-900">{{ article.title || t('articles.untitled') }}</div>
                  <p class="mt-1 line-clamp-2 text-xs leading-5 text-stone-500">{{ articlePreview(article.body) }}</p>
                  <div class="mt-3 flex flex-wrap gap-2">
                    <button
                      class="rounded-lg bg-stone-900 px-2 py-1 text-xs font-semibold text-white"
                      @click="createNodeFromArticle(article, store.selectedOutlineItemId)"
                    >
                      {{ store.selectedOutlineItem ? t('collectionOutline.placeUnderSelected') : t('collectionOutline.placeTopLevel') }}
                    </button>
                    <button class="rounded-lg bg-stone-100 px-2 py-1 text-xs text-stone-600" @click="removeUnplannedArticle(article.id)">
                      {{ t('collectionOutline.removeFromCollection') }}
                    </button>
                  </div>
                </article>
              </div>
            </div>
          </section>
          <PaneResizeHandle data-testid="collections-outline-resizer" @pointerdown="structurePane.startResize" />

          <section class="flex-1 overflow-y-auto p-8" data-testid="collection-outline-detail">
            <div v-if="store.selectedOutlineItem" class="mx-auto max-w-4xl space-y-5">
              <div class="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
                <div class="mb-5 flex items-start justify-between gap-4">
                  <div>
                    <p class="text-xs font-semibold uppercase tracking-[0.22em] text-stone-400">{{ t('collectionOutline.detailKicker') }}</p>
                    <h3 class="mt-1 text-2xl font-semibold text-stone-900">{{ t('collectionOutline.detailTitle') }}</h3>
                    <p class="mt-2 max-w-2xl text-sm leading-6 text-stone-500">
                      {{ t('collectionOutline.nodeRuleHelp') }}
                    </p>
                  </div>
                  <div class="flex flex-wrap justify-end gap-2">
                    <button class="rounded-xl bg-stone-100 px-3 py-2 text-sm text-stone-700" @click="createSiblingOutlineItem">
                      {{ t('collectionOutline.newSibling') }}
                    </button>
                    <button class="rounded-xl bg-stone-100 px-3 py-2 text-sm text-stone-700" @click="createChildOutlineItem">
                      {{ t('collectionOutline.newChild') }}
                    </button>
                    <button class="rounded-xl bg-stone-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-40" :disabled="outlineSaving" @click="saveOutlineItem">
                      {{ outlineSaving ? t('common.saving') : t('common.save') }}
                    </button>
                  </div>
                </div>

                <div class="grid gap-4 md:grid-cols-2" data-tour="outline-detail-fields">
                  <label class="md:col-span-2" data-tour="outline-title-field">
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldTitle') }}</span>
                    <input v-model="outlineDraftTitle" class="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200" />
                    <span class="mt-1 block text-xs leading-5 text-stone-400">{{ t('collectionOutline.fieldTitleHelp') }}</span>
                  </label>
                  <label data-tour="outline-type-field">
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldType') }}</span>
                    <select v-model="outlineDraftType" class="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200">
                      <option v-for="option in outlineTypeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                    </select>
                    <span class="mt-1 block text-xs leading-5 text-stone-400">{{ t('collectionOutline.fieldTypeHelp') }}</span>
                  </label>
                  <label>
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldParent') }}</span>
                    <select v-model="outlineDraftParentId" class="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200">
                      <option value="">{{ t('collectionOutline.noParent') }}</option>
                      <option v-for="node in parentOptions" :key="node.item.id" :value="node.item.id">
                        {{ '　'.repeat(node.depth) }}{{ node.path.join('.') }} {{ nodeTitle(node) }}
                      </option>
                    </select>
                    <span class="mt-1 block text-xs leading-5 text-stone-400">
                      {{ selectedParent ? t('collectionOutline.currentParent', { title: selectedParent.title }) : t('collectionOutline.parentHelp') }}
                    </span>
                  </label>
                  <label>
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldStatus') }}</span>
                    <select v-model="outlineDraftStatus" class="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200">
                      <option v-for="option in outlineStatusOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                    </select>
                  </label>
                  <label data-tour="outline-linked-article">
                    <span class="mb-1 block text-xs font-semibold text-stone-500">{{ t('collectionOutline.fieldEntry') }}</span>
                    <select v-model="outlineDraftEntryId" class="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200">
                      <option value="">{{ t('collectionOutline.noLinkedArticle') }}</option>
                      <option v-for="article in allArticles" :key="article.id" :value="article.id">
                        {{ article.title || t('articles.untitled') }}
                      </option>
                    </select>
                    <span class="mt-1 block text-xs leading-5 text-stone-400">{{ t('collectionOutline.fieldEntryHelp') }}</span>
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
                    <textarea v-model="outlineDraftNotes" rows="5" class="w-full resize-none rounded-xl border border-stone-200 px-3 py-2 text-sm leading-6 outline-none focus:ring-2 focus:ring-indigo-200" :placeholder="t('collectionOutline.notesPlaceholder')" />
                  </label>
                </div>
              </div>

              <div class="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
                <div class="flex items-start justify-between gap-4">
                  <div>
                    <h4 class="font-semibold text-stone-900">{{ t('collectionOutline.linkedArticle') }}</h4>
                    <p class="mt-1 text-sm text-stone-500">
                      {{ outlineLinkedArticle?.title || t('collectionOutline.noLinkedArticle') }}
                    </p>
                    <p class="mt-1 text-xs leading-5 text-stone-400">{{ t('collectionOutline.linkedArticleHelp') }}</p>
                  </div>
                  <div class="flex flex-wrap justify-end gap-2">
                    <button class="rounded-xl bg-stone-100 px-3 py-2 text-sm text-stone-700" @click="createArticleFromOutline">
                      {{ t('collectionOutline.createArticle') }}
                    </button>
                    <button
                      class="rounded-xl bg-stone-100 px-3 py-2 text-sm text-stone-700 disabled:opacity-40"
                      :disabled="!store.selectedOutlineItem.entry_id"
                      @click="openLinkedOutlineArticle"
                    >
                      {{ t('collectionOutline.openArticle') }}
                    </button>
                  </div>
                </div>
                <pre v-if="outlineLinkedArticle" class="mt-4 max-h-48 overflow-y-auto whitespace-pre-wrap rounded-xl bg-stone-50 p-4 text-sm leading-7 text-stone-700">{{ outlineLinkedArticle.body || t('collections.emptyArticle') }}</pre>
              </div>

              <div class="flex justify-between">
                <button class="rounded-xl bg-red-50 px-4 py-2 text-sm text-red-700 hover:bg-red-100" @click="deleteSelectedOutlineItem">
                  {{ t('collectionOutline.deleteItem') }}
                </button>
              </div>
            </div>
            <div v-else class="mx-auto mt-20 max-w-xl rounded-2xl border border-dashed border-stone-300 bg-white/70 p-8 text-center text-stone-500">
              <h3 class="text-lg font-semibold text-stone-700">{{ t('collectionOutline.selectItem') }}</h3>
              <p class="mt-2 text-sm leading-6">{{ t('collectionOutline.selectItemHelp') }}</p>
            </div>
          </section>
        </template>

        <template v-else-if="viewMode === 'board'">
          <section class="flex-1 overflow-y-auto p-6" data-testid="collection-planning-board" data-tour="collections-board">
            <div class="mb-5 flex flex-col gap-4 rounded-3xl border border-stone-200 bg-white/75 p-5 shadow-sm lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p class="text-xs font-semibold uppercase tracking-[0.22em] text-stone-400">Planning Board</p>
                <h3 class="mt-1 text-2xl font-semibold text-stone-900">{{ t('collectionOutline.boardTitle') }}</h3>
                <p class="mt-2 max-w-3xl text-sm leading-6 text-stone-500">
                  {{ t('collectionOutline.boardDescription') }}
                </p>
              </div>
              <div class="flex flex-wrap gap-2">
                <select v-model="outlineFilterType" class="rounded-xl border border-stone-200 bg-white px-3 py-2 text-xs outline-none">
                  <option value="all">{{ t('collectionOutline.allTypes') }}</option>
                  <option v-for="option in outlineTypeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                </select>
                <select v-model="outlineFilterStatus" class="rounded-xl border border-stone-200 bg-white px-3 py-2 text-xs outline-none">
                  <option value="all">{{ t('collectionOutline.allStatuses') }}</option>
                  <option v-for="option in outlineStatusOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                </select>
                <button
                  type="button"
                  class="rounded-xl bg-stone-900 px-3 py-2 text-xs font-semibold text-white hover:bg-stone-700"
                  @click="createOutlineItem('chapter')"
                >
                  {{ t('collectionOutline.newChapter') }}
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
              <p class="mt-2 text-sm text-stone-500">{{ t('collectionOutline.emptyStructureHint') }}</p>
              <button class="mt-5 rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white" @click="createOutlineItem('chapter')">
                {{ t('collectionOutline.newChapter') }}
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
                  {{ t('collectionOutline.emptyColumn') }}
                </div>
                <div v-else class="space-y-2">
                  <article
                    v-for="item in column.items"
                    :key="item.id"
                    class="cursor-pointer rounded-2xl border border-stone-200 bg-white p-3 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
                    @click="selectOutlineItem(item.id); viewMode = 'structure'"
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
          <section class="flex-1 overflow-y-auto p-8" data-tour="collections-export-panel">
            <div class="mx-auto max-w-4xl space-y-5">
              <div class="rounded-3xl border border-stone-200 bg-white p-6 shadow-sm">
                <p class="text-xs font-semibold uppercase tracking-[0.22em] text-stone-400">Export</p>
                <h3 class="mt-1 text-2xl font-semibold text-stone-900">{{ t('collectionOutline.exportTitle') }}</h3>
                <p class="mt-2 text-sm leading-6 text-stone-500">
                  {{ hasLinkedStructure ? t('collectionOutline.exportStructureMode') : t('collectionOutline.exportFallbackMode') }}
                </p>
                <div v-if="unplanned.length && hasLinkedStructure" class="mt-4 rounded-2xl bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-800">
                  {{ t('collectionOutline.unplannedExportWarning', { count: unplanned.length }) }}
                </div>
                <div class="mt-6 flex flex-wrap gap-3">
                  <button
                    class="rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
                    :disabled="(!store.articles.length && !store.outline.length) || store.exportingFormat !== null"
                    @click="exportSelected('md')"
                  >
                    {{ store.exportingFormat === 'md' ? '...' : 'Markdown' }}
                  </button>
                  <button
                    class="rounded-xl bg-white px-4 py-2 text-sm font-semibold text-stone-700 shadow-sm ring-1 ring-stone-200 disabled:opacity-40"
                    :disabled="(!store.articles.length && !store.outline.length) || store.exportingFormat !== null"
                    @click="exportSelected('txt')"
                  >
                    {{ store.exportingFormat === 'txt' ? '...' : 'TXT' }}
                  </button>
                  <button
                    class="rounded-xl bg-white px-4 py-2 text-sm font-semibold text-stone-700 shadow-sm ring-1 ring-stone-200 disabled:opacity-40"
                    :disabled="(!store.articles.length && !store.outline.length) || store.exportingFormat !== null"
                    @click="exportSelected('docx')"
                  >
                    {{ store.exportingFormat === 'docx' ? '...' : 'DOCX' }}
                  </button>
                </div>
              </div>

              <div class="rounded-3xl border border-stone-200 bg-white p-6 shadow-sm">
                <h4 class="font-semibold text-stone-900">{{ t('collectionOutline.planningExportTitle') }}</h4>
                <p class="mt-2 text-sm leading-6 text-stone-500">{{ t('collectionOutline.planningExportHelp') }}</p>
                <div class="mt-4 flex flex-wrap gap-2">
                  <select v-model="outlineFilterType" class="rounded-xl border border-stone-200 bg-white px-3 py-2 text-xs outline-none">
                    <option value="all">{{ t('collectionOutline.allTypes') }}</option>
                    <option v-for="option in outlineTypeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                  </select>
                  <select v-model="outlineFilterStatus" class="rounded-xl border border-stone-200 bg-white px-3 py-2 text-xs outline-none">
                    <option value="all">{{ t('collectionOutline.allStatuses') }}</option>
                    <option v-for="option in outlineStatusOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                  </select>
                  <label class="flex items-center gap-2 rounded-xl bg-stone-50 px-3 py-2 text-xs text-stone-600">
                    <input v-model="outlineFilterUnlinkedOnly" type="checkbox" class="h-4 w-4 rounded border-stone-300 text-indigo-600" />
                    {{ t('collectionOutline.unlinkedOnly') }}
                  </label>
                  <button
                    type="button"
                    class="rounded-xl bg-stone-900 px-3 py-2 text-xs font-semibold text-white hover:bg-stone-700 disabled:opacity-40"
                    :disabled="outlineExporting"
                    @click="exportOutlineMarkdown"
                  >
                    {{ outlineExporting ? t('collectionOutline.exporting') : t('collectionOutline.exportPlanningMarkdown') }}
                  </button>
                </div>
              </div>
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
      <div class="w-[480px] rounded-3xl bg-white p-6 shadow-2xl">
        <h3 class="text-xl font-semibold">{{ t('collections.createTitle') }}</h3>
        <input
          v-model="newTitle"
          class="mt-5 w-full rounded-xl border border-stone-200 px-4 py-3 outline-none focus:ring-2 focus:ring-amber-300"
          :placeholder="t('collections.titlePlaceholder')"
        />
        <select v-model="newProjectType" class="mt-3 w-full rounded-xl border border-stone-200 px-4 py-3 outline-none focus:ring-2 focus:ring-amber-300">
          <option v-for="option in projectTypeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
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
          <button class="rounded-xl bg-stone-100 px-4 py-2 text-sm" @click="createDialogOpen = false">
            {{ t('common.cancel') }}
          </button>
          <button
            class="rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
            :disabled="!newTitle.trim()"
            @click="createCollection"
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
              :class="[
                'w-full rounded-2xl border p-4 text-left transition-all',
                selectedArticleIds.includes(article.id)
                  ? 'border-amber-400 bg-amber-50'
                  : 'border-stone-200 hover:border-stone-300',
                currentArticleIds.has(article.id) ? 'cursor-not-allowed opacity-45' : ''
              ]"
              :disabled="currentArticleIds.has(article.id)"
              @click="togglePickArticle(article.id)"
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
            <button class="rounded-xl bg-stone-100 px-4 py-2 text-sm" @click="articlePickerOpen = false">
              {{ t('common.cancel') }}
            </button>
            <button
              class="rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
              :disabled="!selectedArticleIds.length"
              @click="addSelectedArticles"
            >
              {{ t('collections.addSelected') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <GuidedTourOverlay
      :open="tourOpen"
      :steps="collectionTourSteps"
      :step-index="tourStepIndex"
      :previous-label="t('collectionsTour.previous')"
      :next-label="t('collectionsTour.next')"
      :skip-label="t('collectionsTour.skip')"
      :finish-label="t('collectionsTour.finish')"
      :progress-label="currentTourProgressLabel"
      @previous="previousCollectionTourStep"
      @next="nextCollectionTourStep"
      @close="closeCollectionTour"
      @finish="finishCollectionTour"
    />
  </div>
</template>
