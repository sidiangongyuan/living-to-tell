<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { articlesApi, type Entry } from '../../api/articles'
import { collectionsApi } from '../../api/collections'
import type {
  CollectionAgentAction,
  CollectionAgentMemory,
  CollectionAgentReference,
  CollectionAgentRun,
  CollectionAgentState,
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
const AGENT_LONG_ANSWER_THRESHOLD = 700
const ROUTE_HIGHLIGHT_MS = 2600

type AgentQuickTaskKind = 'init' | 'health' | 'continuity' | 'next' | 'memory'
type AgentSlashCommand = {
  command: string
  title: string
  subtitle: string
  action: 'task' | 'clear'
  taskKind?: AgentQuickTaskKind
}

const store = useCollectionsStore()
const { t, locale } = useI18n()
const router = useRouter()
const route = useRoute()
const settings = useSettingsStore()

const allArticles = ref<Entry[]>([])
const articlePickerOpen = ref(false)
const createDialogOpen = ref(false)
const selectedArticleIds = ref<string[]>([])
const viewMode = ref<'structure' | 'board' | 'export' | 'agent'>('structure')
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
const agentState = ref<CollectionAgentState | null>(null)
const agentLoading = ref(false)
const agentError = ref<string | null>(null)
const agentPrompt = ref('')
const agentReferenceQuery = ref('')
const agentReferenceResults = ref<CollectionAgentReference[]>([])
const selectedAgentRefs = ref<CollectionAgentReference[]>([])
const agentReferencePickerOpen = ref(false)
const agentSearchLoading = ref(false)
const agentRunning = ref(false)
const agentRequestWebContext = ref(false)
const agentProfileId = ref('default')
const agentMemoryDraft = ref<Record<string, string>>({})
const agentMemorySaving = ref(false)
const agentApplyingActionId = ref<string | null>(null)
const agentPendingQuickTask = ref<AgentQuickTaskKind | null>(null)
const agentCollapsedRunIds = ref<string[]>([])
const agentExpandedRunIds = ref<string[]>([])
const agentHighlightedRunId = ref<string | null>(null)
const agentPromptIndexQuery = ref('')
const agentSlashMenuOpen = ref(false)
const agentSlashQuery = ref('')
const agentSlashSelectedIndex = ref(0)
const agentClearDialogOpen = ref(false)
const agentClearing = ref(false)
const highlightedCollectionArticleId = ref<string | null>(null)
const windowWidth = ref(typeof window === 'undefined' ? 1440 : window.innerWidth)
let agentLoadToken = 0
let agentPollTimer: number | null = null
let agentReferenceSearchToken = 0
let collectionArticleHighlightTimer: number | null = null
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

const collectionListPaneStyle = computed(() => ({
  width: windowWidth.value < 920
    ? `${Math.max(190, Math.min(collectionListPane.size.value, Math.floor(windowWidth.value * 0.34)))}px`
    : `${collectionListPane.size.value}px`,
}))
const structurePaneStyle = computed(() => ({
  width: windowWidth.value < 1180
    ? `${Math.max(260, Math.min(structurePane.size.value, Math.floor(windowWidth.value * 0.38)))}px`
    : `${structurePane.size.value}px`,
}))

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
const agentRuns = computed(() => agentState.value?.runs ?? [])
const agentActions = computed(() => agentState.value?.actions ?? [])
const pendingAgentActions = computed(() => agentActions.value.filter((action) => action.status === 'pending'))
const activeAgentRun = computed(() =>
  agentRuns.value.find((run) => !['succeeded', 'failed', 'cancelled'].includes(run.status)) ?? null
)
const agentProfileOptions = computed(() => agentState.value?.profiles ?? [{ id: 'default', name: '默认配置' }])
const agentQuickTasks = computed(() => [
  {
    kind: 'init' as const,
    title: '初始化 Agent',
    subtitle: '绑定本书、建立基线',
    prompt: '请初始化你作为当前作品集 Agent 的工作基线：阅读作品集结构、未编排文章和项目圣经，说明你已经掌握了什么、还缺什么、建议作者先补哪些记忆或结构信息。只生成可确认提案，不要改正文。',
  },
  {
    kind: 'health' as const,
    title: '体检作品集',
    subtitle: '结构、缺口、下一步',
    prompt: '请体检这个作品集：结构是否清楚、章节/场景是否缺口明显、下一步最该补什么。请给出证据和可确认提案。',
  },
  {
    kind: 'continuity' as const,
    title: '检查连续性',
    subtitle: '人物、时间线、伏笔',
    prompt: '请检查这个作品集的连续性风险：人物动机、时间线、伏笔、设定是否有断裂或未解决问题。请给出具体位置和下一步。',
  },
  {
    kind: 'next' as const,
    title: '建议下一步',
    subtitle: '今天最该推进什么',
    prompt: '请根据当前作品集结构和项目记忆，建议今天最该推进的一步。请说明理由、风险和可执行动作。',
  },
  {
    kind: 'memory' as const,
    title: '整理项目记忆',
    subtitle: '稳定事实先提案',
    prompt: '请整理当前作品集的项目圣经。只把稳定事实做成记忆更新提案，不确定内容放到未解决问题。',
  },
])
const pendingQuickTask = computed(() =>
  agentQuickTasks.value.find((task) => task.kind === agentPendingQuickTask.value) ?? null
)
const agentSlashCommands = computed<AgentSlashCommand[]>(() => [
  ...agentQuickTasks.value.map((task) => ({
    command: task.kind,
    title: task.title,
    subtitle: task.subtitle,
    action: 'task' as const,
    taskKind: task.kind,
  })),
  {
    command: 'clear',
    title: '清空会话',
    subtitle: '保留项目圣经和待确认提案',
    action: 'clear',
  },
])
const filteredAgentSlashCommands = computed(() => {
  const query = agentSlashQuery.value.trim().toLowerCase()
  if (!query) return agentSlashCommands.value
  return agentSlashCommands.value.filter((command) =>
    command.command.includes(query)
    || command.title.toLowerCase().includes(query)
    || command.subtitle.toLowerCase().includes(query)
  )
})
const selectedAgentProfileName = computed(() =>
  agentProfileOptions.value.find((profile) => profile.id === agentProfileId.value)?.name || '当前配置'
)
const filteredAgentPromptIndex = computed(() => {
  const query = agentPromptIndexQuery.value.trim().toLowerCase()
  return agentRuns.value.filter((run) => {
    const text = agentRunMessage(run)
    if (!query) return true
    return text.toLowerCase().includes(query) || agentRunTaskLabel(run).toLowerCase().includes(query)
  })
})

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
const outlineTypeGuide = computed(() => {
  if (locale.value === 'en') {
    if (projectType.value === 'novel') {
      return 'Novel structure usually reads Part -> Chapter -> Scene. A part is a large act or volume, a chapter is what readers see in the table of contents, a scene is one concrete beat or draft slot, and a note is planning-only.'
    }
    if (projectType.value === 'essay') {
      return 'Essay collections usually read Section -> Group -> Essay. A section is a large theme, a group gathers related essays, an essay is a real piece, and a note is planning-only.'
    }
    if (projectType.value === 'nonfiction') {
      return 'Nonfiction usually reads Part -> Chapter -> Section. A part is the large argument block, a chapter develops one claim, a section is a smaller unit, and a note is planning-only.'
    }
    return 'Use Group for a large bucket, Chapter for a middle layer, Article for a real draft slot, and Note for planning-only reminders.'
  }
  if (projectType.value === 'novel') {
    return '小说通常是“分部 -> 章节 -> 场景”。分部是一卷、一幕或一大段；章节是读者看到的一章；场景是章节里的具体事件或一个正文位置；笔记只放规划提醒，不代表正文。'
  }
  if (projectType.value === 'essay') {
    return '散文集通常是“辑 -> 篇组 -> 篇章”。辑是一组主题，篇组收纳相近文章，篇章才是一篇真实作品；笔记只放规划提醒。'
  }
  if (projectType.value === 'nonfiction') {
    return '非虚构通常是“部分 -> 章节 -> 小节”。部分是一大块论述，章节推进一个主要问题，小节承载更小的论证或材料；笔记只放规划提醒。'
  }
  return '通用作品集可用“分组 -> 章节 -> 文章”。分组是大容器，章节是中层，文章才是正文位置；笔记只放规划提醒。'
})

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
      id: 'project-type',
      title: t('collectionsTour.projectTypeTitle'),
      body: t('collectionsTour.projectTypeBody'),
      target: '[data-tour="collections-project-type"]',
    },
    {
      id: 'add-articles',
      title: t('collectionsTour.addArticlesTitle'),
      body: t('collectionsTour.addArticlesBody'),
      target: '[data-tour="collections-add-articles"]',
    },
    {
      id: 'structure',
      title: t('collectionsTour.structureTitle'),
      body: t('collectionsTour.structureBody'),
      target: '[data-tour="collections-structure"]',
    },
    {
      id: 'create-node',
      title: t('collectionsTour.createNodeTitle'),
      body: t('collectionsTour.createNodeBody'),
      target: '[data-tour="outline-create-buttons"]',
    },
    {
      id: 'tree',
      title: t('collectionsTour.treeTitle'),
      body: t('collectionsTour.treeBody'),
      target: '[data-tour="manuscript-tree"]',
    },
    {
      id: 'child-node',
      title: t('collectionsTour.childNodeTitle'),
      body: t('collectionsTour.childNodeBody'),
      target: '[data-tour="outline-new-child"]',
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
      id: 'fields',
      title: t('collectionsTour.fieldsTitle'),
      body: t('collectionsTour.fieldsBody'),
      target: '[data-tour="outline-detail-fields"]',
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
      id: 'agent',
      title: t('collectionsTour.agentTitle'),
      body: t('collectionsTour.agentBody'),
      target: '[data-tour="collection-agent-panel"]',
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
  window.addEventListener('resize', handleWindowResize)
  await store.loadCollections()
  const routeCollectionId = typeof route.query.id === 'string' ? route.query.id : ''
  const lastCollectionId = localStorage.getItem(LAST_SELECTED_COLLECTION_KEY)
  if (routeCollectionId && store.collections.some((collection) => collection.id === routeCollectionId)) {
    await store.selectCollection(routeCollectionId)
  } else if (lastCollectionId && store.collections.some((collection) => collection.id === lastCollectionId)) {
    await store.selectCollection(lastCollectionId)
  }
  allArticles.value = await articlesApi.listArticles(500)
  await applyCollectionRouteContext()
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
  () => [route.query.id, route.query.article, route.query.tab] as const,
  () => {
    void applyCollectionRouteContext()
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

watch(
  () => [viewMode.value, store.selectedCollectionId] as const,
  ([mode, collectionId]) => {
    if (mode === 'agent' && collectionId) {
      void loadAgentState()
    }
  }
)

onBeforeUnmount(() => {
  stopAgentPolling()
  window.removeEventListener('resize', handleWindowResize)
  clearCollectionArticleHighlightTimer()
})

function handleWindowResize() {
  windowWidth.value = window.innerWidth
}

function prepareCollectionTourStep(index = tourStepIndex.value) {
  const step = collectionTourSteps.value[index]
  if (!step || !store.selectedCollection) return
  if (step.id === 'board') {
    viewMode.value = 'board'
  } else if (step.id === 'export') {
    viewMode.value = 'export'
  } else if (step.id === 'agent') {
    viewMode.value = 'agent'
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

async function applyCollectionRouteContext() {
  const collectionId = typeof route.query.id === 'string' ? route.query.id : ''
  if (collectionId && store.collections.some((collection) => collection.id === collectionId)) {
    if (store.selectedCollectionId !== collectionId) {
      await store.selectCollection(collectionId)
    }
  } else if (collectionId && store.collections.length) {
    actionError.value = '要打开的作品集已不存在。'
    return
  }

  const tab = typeof route.query.tab === 'string' ? route.query.tab : ''
  if (tab === 'agent') viewMode.value = 'agent'
  else if (tab === 'board') viewMode.value = 'board'
  else if (tab === 'export') viewMode.value = 'export'

  const articleId = typeof route.query.article === 'string' ? route.query.article : ''
  if (!articleId || !store.selectedCollectionId) return
  setCollectionArticleHighlight(articleId)
  if (!tab) viewMode.value = 'structure'
  const linkedItem = store.outline.find((item) => item.entry_id === articleId)
  const inCollection = store.articles.some((article) => article.id === articleId)
  if (!inCollection) {
    actionError.value = '这篇文章已不在当前作品集中。'
    return
  }
  if (linkedItem) {
    store.selectOutlineItem(linkedItem.id)
  }
  await nextTick()
  scrollToCollectionArticle(articleId)
}

function clearCollectionArticleHighlightTimer() {
  if (collectionArticleHighlightTimer !== null) {
    window.clearTimeout(collectionArticleHighlightTimer)
    collectionArticleHighlightTimer = null
  }
}

function setCollectionArticleHighlight(articleId: string | null) {
  clearCollectionArticleHighlightTimer()
  highlightedCollectionArticleId.value = articleId
  if (articleId) {
    collectionArticleHighlightTimer = window.setTimeout(() => {
      if (highlightedCollectionArticleId.value === articleId) highlightedCollectionArticleId.value = null
      collectionArticleHighlightTimer = null
    }, ROUTE_HIGHLIGHT_MS)
  }
}

function scrollToCollectionArticle(articleId: string) {
  const target = Array
    .from(document.querySelectorAll<HTMLElement>('[data-collection-article-id]'))
    .find((element) => element.dataset.collectionArticleId === articleId)
  if (target instanceof HTMLElement) {
    target.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

function scrollToOutlineItem(itemId: string) {
  const target = document.querySelector<HTMLElement>(`[data-outline-item-id="${itemId}"]`)
  if (target instanceof HTMLElement) {
    target.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }
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

function stopAgentPolling() {
  if (agentPollTimer !== null) {
    window.clearTimeout(agentPollTimer)
    agentPollTimer = null
  }
}

function isTerminalAgentRun(run: CollectionAgentRun | null): boolean {
  return Boolean(run && ['succeeded', 'failed', 'cancelled'].includes(run.status))
}

function syncAgentDrafts(state: CollectionAgentState) {
  agentProfileId.value = state.settings.profile_id || 'default'
  const next: Record<string, string> = {}
  for (const section of state.memory.sections) {
    next[section.id] = section.content || ''
  }
  agentMemoryDraft.value = next
}

function syncAgentRunCollapse(state: CollectionAgentState) {
  const validIds = new Set(state.runs.map((run) => run.id))
  const collapsed = new Set(agentCollapsedRunIds.value.filter((id) => validIds.has(id)))
  for (const run of state.runs) {
    if (
      agentRunAnswer(run).length > AGENT_LONG_ANSWER_THRESHOLD
      && !agentExpandedRunIds.value.includes(run.id)
    ) {
      collapsed.add(run.id)
    }
  }
  agentCollapsedRunIds.value = [...collapsed]
  agentExpandedRunIds.value = agentExpandedRunIds.value.filter((id) => validIds.has(id))
}

async function loadAgentState() {
  if (!store.selectedCollectionId) return
  const token = ++agentLoadToken
  const collectionId = store.selectedCollectionId
  agentLoading.value = true
  agentError.value = null
  try {
    const state = await collectionsApi.getAgentState(collectionId)
    if (token !== agentLoadToken || store.selectedCollectionId !== collectionId) return
    agentState.value = state
    syncAgentDrafts(state)
    syncAgentRunCollapse(state)
    const running = activeAgentRun.value
    if (running && !isTerminalAgentRun(running)) scheduleAgentPoll(running.id)
  } catch (e) {
    if (token !== agentLoadToken) return
    agentError.value = e instanceof Error ? e.message : String(e)
  } finally {
    if (token === agentLoadToken) agentLoading.value = false
  }
}

function scheduleAgentPoll(runId: string) {
  stopAgentPolling()
  agentPollTimer = window.setTimeout(() => {
    void pollAgentRun(runId)
  }, 1500)
}

async function pollAgentRun(runId: string) {
  if (!store.selectedCollectionId) return
  const collectionId = store.selectedCollectionId
  try {
    const run = await collectionsApi.getAgentRun(collectionId, runId)
    if (store.selectedCollectionId !== collectionId) return
    if (agentState.value) {
      const runs = [...agentState.value.runs]
      const index = runs.findIndex((item) => item.id === run.id)
      if (index === -1) runs.unshift(run)
      else runs[index] = run
      agentState.value = { ...agentState.value, runs }
      syncAgentRunCollapse(agentState.value)
    }
    if (isTerminalAgentRun(run)) {
      await loadAgentState()
    } else {
      scheduleAgentPoll(run.id)
    }
  } catch (e) {
    agentError.value = `正在重连 Agent 状态：${e instanceof Error ? e.message : String(e)}`
    scheduleAgentPoll(runId)
  }
}

async function saveAgentSettings() {
  if (!store.selectedCollectionId || !agentState.value) return
  agentError.value = null
  try {
    const settings = await collectionsApi.saveAgentSettings(store.selectedCollectionId, {
      profile_id: agentProfileId.value || 'default',
      enabled: agentState.value.settings.enabled,
    })
    agentState.value = { ...agentState.value, settings }
  } catch (e) {
    agentError.value = e instanceof Error ? e.message : String(e)
  }
}

async function saveAgentMemory() {
  if (!store.selectedCollectionId || !agentState.value) return
  agentMemorySaving.value = true
  agentError.value = null
  try {
    const memory: CollectionAgentMemory = await collectionsApi.saveAgentMemory(
      store.selectedCollectionId,
      agentMemoryDraft.value,
    )
    agentState.value = { ...agentState.value, memory }
    syncAgentDrafts(agentState.value)
  } catch (e) {
    agentError.value = e instanceof Error ? e.message : String(e)
  } finally {
    agentMemorySaving.value = false
  }
}

async function searchAgentReferences() {
  if (!store.selectedCollectionId) return
  const token = ++agentReferenceSearchToken
  const collectionId = store.selectedCollectionId
  agentReferencePickerOpen.value = true
  agentSearchLoading.value = true
  agentError.value = null
  try {
    const results = await collectionsApi.searchAgentReferences(
      collectionId,
      agentReferenceQuery.value.trim(),
      30,
    )
    if (token !== agentReferenceSearchToken || store.selectedCollectionId !== collectionId) return
    agentReferenceResults.value = results
  } catch (e) {
    if (token !== agentReferenceSearchToken || store.selectedCollectionId !== collectionId) return
    agentError.value = e instanceof Error ? e.message : String(e)
  } finally {
    if (token === agentReferenceSearchToken && store.selectedCollectionId === collectionId) {
      agentSearchLoading.value = false
    }
  }
}

function openAgentReferencePicker(query = agentReferenceQuery.value) {
  agentReferenceQuery.value = query
  agentReferencePickerOpen.value = true
  void searchAgentReferences()
}

function closeAgentReferencePicker() {
  agentReferencePickerOpen.value = false
}

function clearAgentReferenceSearch() {
  agentReferenceQuery.value = ''
  agentReferenceResults.value = []
}

function addAgentReference(ref: CollectionAgentReference) {
  const mention = agentPrompt.value.match(/(^|\s)@[^\s@]{0,40}$/)
  if (mention && typeof mention.index === 'number') {
    agentPrompt.value = `${agentPrompt.value.slice(0, mention.index)}${mention[1] ?? ''}`
  }
  if (!selectedAgentRefs.value.some((item) => item.kind === ref.kind && item.ref_id === ref.ref_id)) {
    selectedAgentRefs.value = [...selectedAgentRefs.value, ref]
  }
  agentReferencePickerOpen.value = false
}

function removeAgentReference(ref: CollectionAgentReference) {
  selectedAgentRefs.value = selectedAgentRefs.value.filter((item) =>
    !(item.kind === ref.kind && item.ref_id === ref.ref_id)
  )
}

function closeAgentSlashMenu() {
  agentSlashMenuOpen.value = false
  agentSlashQuery.value = ''
  agentSlashSelectedIndex.value = 0
}

function syncAgentSlashMenuFromPrompt() {
  const match = agentPrompt.value.match(/^\/([A-Za-z0-9_-]*)$/)
  if (!match) {
    if (agentSlashMenuOpen.value) closeAgentSlashMenu()
    return
  }
  agentSlashQuery.value = match[1] || ''
  agentSlashMenuOpen.value = true
  agentReferencePickerOpen.value = false
  if (agentSlashSelectedIndex.value >= filteredAgentSlashCommands.value.length) {
    agentSlashSelectedIndex.value = Math.max(0, filteredAgentSlashCommands.value.length - 1)
  }
}

function moveAgentSlashSelection(direction: 1 | -1) {
  const total = filteredAgentSlashCommands.value.length
  if (!total) return
  agentSlashSelectedIndex.value = (agentSlashSelectedIndex.value + direction + total) % total
}

function selectAgentSlashCommand(command = filteredAgentSlashCommands.value[agentSlashSelectedIndex.value]) {
  if (!command) return
  closeAgentSlashMenu()
  agentPrompt.value = ''
  if (command.action === 'clear') {
    requestAgentClear()
    return
  }
  if (command.taskKind) {
    runQuickAgentTask(command.taskKind)
  }
}

function runAgentSlashCommandText(message: string): boolean {
  if (!message.startsWith('/')) return false
  const commandName = message.slice(1).trim().toLowerCase()
  const command = agentSlashCommands.value.find((item) => item.command === commandName)
  if (command) {
    selectAgentSlashCommand(command)
    return true
  }
  agentError.value = '未知斜杠命令。输入 / 后从菜单选择可用功能。'
  agentSlashQuery.value = commandName
  agentSlashSelectedIndex.value = 0
  agentSlashMenuOpen.value = true
  return true
}

function handleAgentPromptKeydown(event: KeyboardEvent) {
  if (agentSlashMenuOpen.value) {
    if (event.key === 'Escape') {
      event.preventDefault()
      closeAgentSlashMenu()
      return
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      moveAgentSlashSelection(1)
      return
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      moveAgentSlashSelection(-1)
      return
    }
    if (event.key === 'Enter' || event.key === 'Tab') {
      event.preventDefault()
      selectAgentSlashCommand()
      return
    }
  }
  if (event.key === 'Escape' && agentReferencePickerOpen.value) {
    agentReferencePickerOpen.value = false
    return
  }
  if (event.key === '@') {
    agentReferencePickerOpen.value = true
    agentReferenceQuery.value = ''
    void searchAgentReferences()
  }
}

function handleAgentPromptInput() {
  syncAgentSlashMenuFromPrompt()
  if (agentSlashMenuOpen.value) return
  const match = agentPrompt.value.match(/(?:^|\s)@([^\s@]{0,40})$/)
  if (!match) return
  agentReferenceQuery.value = match[1] || ''
  agentReferencePickerOpen.value = true
  void searchAgentReferences()
}

async function runAgentPrompt(taskType = 'free_chat', prompt = agentPrompt.value) {
  if (!store.selectedCollectionId) return
  const message = prompt.trim()
  if (runAgentSlashCommandText(message)) {
    return
  }
  if (!message) {
    agentError.value = '请先输入要交给作品集 Agent 的问题或任务。'
    return
  }
  if (activeAgentRun.value) {
    agentError.value = 'Agent 正在工作，请等待完成或先中断本地等待。'
    return
  }
  agentRunning.value = true
  agentError.value = null
  try {
    const run = await collectionsApi.createAgentRun(store.selectedCollectionId, {
      message,
      task_type: taskType,
      request_web_context: agentRequestWebContext.value,
      profile_id: agentProfileId.value,
      context_refs: selectedAgentRefs.value.map((ref) => ({ kind: ref.kind, ref_id: ref.ref_id })),
    })
    if (agentState.value) {
      agentState.value = { ...agentState.value, runs: [run, ...agentState.value.runs] }
    }
    agentPrompt.value = ''
    closeAgentSlashMenu()
    agentPendingQuickTask.value = null
    scheduleAgentPoll(run.id)
  } catch (e) {
    agentError.value = e instanceof Error ? e.message : String(e)
  } finally {
    agentRunning.value = false
  }
}

function runQuickAgentTask(kind: AgentQuickTaskKind) {
  agentPendingQuickTask.value = kind
}

async function confirmQuickAgentTask() {
  if (!pendingQuickTask.value) return
  await runAgentPrompt(pendingQuickTask.value.kind, pendingQuickTask.value.prompt)
}

function cancelQuickAgentTask() {
  agentPendingQuickTask.value = null
}

async function cancelActiveAgentRun() {
  if (!store.selectedCollectionId || !activeAgentRun.value) return
  try {
    const run = await collectionsApi.cancelAgentRun(store.selectedCollectionId, activeAgentRun.value.id)
    if (agentState.value) {
      agentState.value = {
        ...agentState.value,
        runs: agentState.value.runs.map((item) => item.id === run.id ? run : item),
      }
    }
    stopAgentPolling()
  } catch (e) {
    agentError.value = e instanceof Error ? e.message : String(e)
  }
}

function requestAgentClear() {
  if (activeAgentRun.value) {
    agentError.value = 'Agent 正在工作，请等待完成或先中断本地等待。'
    return
  }
  agentClearDialogOpen.value = true
}

async function clearAgentConversation() {
  if (!store.selectedCollectionId || activeAgentRun.value) return
  agentClearing.value = true
  agentError.value = null
  try {
    const state = await collectionsApi.clearAgentConversation(store.selectedCollectionId)
    agentState.value = state
    agentPrompt.value = ''
    agentReferenceResults.value = []
    selectedAgentRefs.value = []
    agentPendingQuickTask.value = null
    agentCollapsedRunIds.value = []
    agentExpandedRunIds.value = []
    syncAgentDrafts(state)
    syncAgentRunCollapse(state)
    agentClearDialogOpen.value = false
  } catch (e) {
    agentError.value = e instanceof Error ? e.message : String(e)
  } finally {
    agentClearing.value = false
  }
}

async function applyAgentAction(action: CollectionAgentAction) {
  if (!store.selectedCollectionId) return
  agentApplyingActionId.value = action.id
  agentError.value = null
  try {
    const updated = await collectionsApi.applyAgentAction(store.selectedCollectionId, action.id)
    if (agentState.value) {
      agentState.value = {
        ...agentState.value,
        actions: agentState.value.actions.map((item) => item.id === updated.id ? updated : item),
        runs: agentState.value.runs.map((run) => ({
          ...run,
          actions: run.actions.map((item) => item.id === updated.id ? updated : item),
        })),
      }
    }
    await Promise.all([
      store.loadOutline(),
      store.loadArticles(),
      loadAgentState(),
    ])
  } catch (e) {
    agentError.value = e instanceof Error ? e.message : String(e)
  } finally {
    agentApplyingActionId.value = null
  }
}

async function rejectAgentAction(action: CollectionAgentAction) {
  if (!store.selectedCollectionId) return
  agentApplyingActionId.value = action.id
  agentError.value = null
  try {
    const updated = await collectionsApi.rejectAgentAction(store.selectedCollectionId, action.id)
    if (agentState.value) {
      agentState.value = {
        ...agentState.value,
        actions: agentState.value.actions.map((item) => item.id === updated.id ? updated : item),
        runs: agentState.value.runs.map((run) => ({
          ...run,
          actions: run.actions.map((item) => item.id === updated.id ? updated : item),
        })),
      }
    }
  } catch (e) {
    agentError.value = e instanceof Error ? e.message : String(e)
  } finally {
    agentApplyingActionId.value = null
  }
}

function agentReferenceKindLabel(kind: string): string {
  if (kind === 'outline') return '结构'
  if (kind === 'article') return '文章'
  if (kind === 'ai_card') return 'AI卡片'
  if (kind === 'motif') return '意象'
  if (kind === 'reference') return '文脉'
  return kind
}

function agentActionTypeLabel(type: string): string {
  if (type === 'update_memory') return '更新记忆'
  if (type === 'create_outline_item') return '新增结构'
  if (type === 'update_outline_item') return '修改结构'
  if (type === 'create_article_note') return '创建便签'
  return type
}

function agentActionStatusTone(status: string): string {
  if (status === 'applied') return 'bg-emerald-50 text-emerald-700 ring-emerald-100'
  if (status === 'rejected') return 'bg-stone-100 text-stone-500 ring-stone-200'
  return 'bg-amber-50 text-amber-700 ring-amber-100'
}

function formatAgentPreview(value: Record<string, unknown>): string {
  return JSON.stringify(value, null, 2)
}

function agentRunAnswer(run: CollectionAgentRun): string {
  const answer = run.result?.answer
  return typeof answer === 'string' && answer.trim() ? answer : ''
}

function agentRunMessage(run: CollectionAgentRun): string {
  const message = run.request?.message
  return typeof message === 'string' ? message : ''
}

function agentRunTaskLabel(run: CollectionAgentRun): string {
  const taskType = typeof run.request?.task_type === 'string' ? run.request.task_type : 'free_chat'
  const quickTask = agentQuickTasks.value.find((task) => task.kind === taskType)
  if (quickTask) return quickTask.title
  return '普通对话'
}

function agentRunTimeLabel(run: CollectionAgentRun): string {
  const raw = run.completed_at || run.updated_at || run.created_at
  if (!raw) return ''
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return raw
  return date.toLocaleString()
}

function agentRunVisibleAnswer(run: CollectionAgentRun): string {
  const answer = agentRunAnswer(run)
  if (!agentCollapsedRunIds.value.includes(run.id)) return answer
  return `${answer.slice(0, AGENT_LONG_ANSWER_THRESHOLD).trim()}...`
}

function agentRunCanCollapse(run: CollectionAgentRun): boolean {
  return agentRunAnswer(run).length > AGENT_LONG_ANSWER_THRESHOLD
}

function toggleAgentRunCollapsed(run: CollectionAgentRun) {
  if (!agentRunCanCollapse(run)) return
  if (agentCollapsedRunIds.value.includes(run.id)) {
    agentCollapsedRunIds.value = agentCollapsedRunIds.value.filter((id) => id !== run.id)
    if (!agentExpandedRunIds.value.includes(run.id)) {
      agentExpandedRunIds.value = [...agentExpandedRunIds.value, run.id]
    }
  } else {
    agentCollapsedRunIds.value = [...agentCollapsedRunIds.value, run.id]
    agentExpandedRunIds.value = agentExpandedRunIds.value.filter((id) => id !== run.id)
  }
}

async function scrollToAgentRun(runId: string) {
  await nextTick()
  const target = document.getElementById(`collection-agent-run-${runId}`)
  if (target) {
    target.scrollIntoView({ behavior: 'smooth', block: 'center' })
    agentHighlightedRunId.value = runId
    window.setTimeout(() => {
      if (agentHighlightedRunId.value === runId) agentHighlightedRunId.value = null
    }, 1800)
  }
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
  setCollectionArticleHighlight(null)
  store.selectOutlineItem(id)
  await nextTick()
  scrollToOutlineItem(id)
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
      :style="collectionListPaneStyle"
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
          <div class="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
            <div class="min-w-0 flex-1 space-y-3" data-tour="collections-header">
              <input
                v-model="draftTitle"
                class="w-full bg-transparent text-2xl font-semibold tracking-tight outline-none md:text-3xl"
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
              <div class="grid gap-2 text-xs text-stone-600 sm:grid-cols-2 xl:grid-cols-4">
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
                    data-tour="collection-agent-tab"
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
                  <button
                    type="button"
                    :class="[
                      'rounded-lg px-3 py-1.5 transition',
                      viewMode === 'agent' ? 'bg-white text-stone-950 shadow-sm' : 'hover:text-stone-900'
                    ]"
                    @click="viewMode = 'agent'"
                  >
                    Agent
                  </button>
                </div>
                <p class="max-w-3xl text-xs leading-5 text-stone-500">
                  {{
                    viewMode === 'structure'
                      ? t('collectionOutline.structureHelp')
                      : viewMode === 'board'
                        ? t('collectionOutline.boardHelp')
                        : viewMode === 'export'
                          ? t('collectionOutline.exportHelp')
                          : '作品集 Agent 是绑定这本书的总编助手：读取结构和项目记忆，给出诊断与可确认提案，不会自动改正文。'
                  }}
                </p>
              </div>
            </div>
            <div class="flex flex-wrap justify-end gap-2">
              <button
                class="rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white hover:bg-stone-700"
                data-tour="collections-add-articles"
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
            :style="structurePaneStyle"
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
            <div class="mb-4 grid grid-cols-2 gap-2" data-tour="outline-create-buttons">
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
                :data-outline-item-id="node.item.id"
                :data-collection-article-id="node.item.entry_id || undefined"
                :class="[
                  'group cursor-pointer rounded-2xl border bg-white py-3 pr-3 shadow-sm transition-all',
                  store.selectedOutlineItemId === node.item.id
                    ? 'border-amber-400 ring-2 ring-amber-200 shadow-md'
                    : highlightedCollectionArticleId === node.item.entry_id
                    ? 'border-amber-300 ring-1 ring-amber-100'
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
                <article
                  v-for="article in unplanned"
                  :key="article.id"
                  :data-collection-article-id="article.id"
                  :class="[
                    'rounded-xl border bg-white p-3',
                    highlightedCollectionArticleId === article.id ? 'border-amber-400 ring-2 ring-amber-200' : 'border-stone-200'
                  ]"
                >
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
                    <button class="rounded-xl bg-stone-100 px-3 py-2 text-sm text-stone-700" data-tour="outline-new-child" @click="createChildOutlineItem">
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
                    <span class="mt-2 block rounded-xl bg-indigo-50 px-3 py-2 text-xs leading-5 text-indigo-800">{{ outlineTypeGuide }}</span>
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
                    <input v-model="outlineDraftPov" class="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-200" :placeholder="t('collectionOutline.fieldPovPlaceholder')" />
                    <span class="mt-1 block text-xs leading-5 text-stone-400">{{ t('collectionOutline.fieldPovHelp') }}</span>
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
                    <p class="mt-2 rounded-xl bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800">{{ t('collectionOutline.multiArticleHelp') }}</p>
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
            <div v-else class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-5">
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

        <template v-else-if="viewMode === 'agent'">
          <section class="flex-1 overflow-y-auto p-4 sm:p-6" data-testid="collection-agent-panel" data-tour="collection-agent-panel">
            <div class="mx-auto grid max-w-7xl gap-5 xl:grid-cols-[220px_minmax(0,1fr)] 2xl:grid-cols-[240px_minmax(0,1.05fr)_minmax(300px,0.7fr)]">
              <aside class="space-y-4 xl:sticky xl:top-0 xl:self-start">
                <div class="rounded-3xl border border-stone-200 bg-white p-4 shadow-sm">
                  <div class="flex items-start justify-between gap-3">
                    <div>
                      <h4 class="font-semibold text-stone-900">会话索引</h4>
                      <p class="mt-1 text-xs leading-5 text-stone-500">只列你的 prompt，点击定位到回答。</p>
                    </div>
                    <button
                      class="rounded-xl bg-stone-100 px-2.5 py-1.5 text-xs text-stone-600 hover:bg-stone-200 disabled:opacity-40"
                      :disabled="Boolean(activeAgentRun)"
                      @click="requestAgentClear"
                    >
                      清空
                    </button>
                  </div>
                  <input
                    v-model="agentPromptIndexQuery"
                    class="mt-3 w-full rounded-xl border border-stone-200 px-3 py-2 text-xs outline-none focus:ring-2 focus:ring-indigo-200"
                    placeholder="搜索 prompt"
                  />
                  <p class="mt-3 rounded-xl bg-stone-50 px-3 py-2 text-[11px] leading-5 text-stone-500">
                    记忆只来自“保存记忆”或应用“更新记忆”提案；拒绝的提案不会进入长期记忆。
                  </p>
                  <div v-if="!filteredAgentPromptIndex.length" class="mt-4 rounded-2xl border border-dashed border-stone-200 p-4 text-center text-xs text-stone-400">
                    暂无可定位的 prompt。
                  </div>
                  <div v-else class="mt-4 max-h-[58vh] space-y-2 overflow-y-auto pr-1">
                    <button
                      v-for="run in filteredAgentPromptIndex"
                      :key="run.id"
                      class="w-full rounded-2xl border border-stone-200 bg-stone-50 p-3 text-left hover:border-indigo-200 hover:bg-white"
                      @click="scrollToAgentRun(run.id)"
                    >
                      <div class="flex items-center justify-between gap-2">
                        <span class="rounded-full bg-white px-2 py-0.5 text-[11px] text-stone-500 ring-1 ring-stone-200">{{ agentRunTaskLabel(run) }}</span>
                        <span :class="['rounded-full px-2 py-0.5 text-[11px] ring-1', run.status === 'succeeded' ? 'bg-emerald-50 text-emerald-700 ring-emerald-100' : run.status === 'failed' ? 'bg-red-50 text-red-700 ring-red-100' : 'bg-amber-50 text-amber-700 ring-amber-100']">
                          {{ run.status }}
                        </span>
                      </div>
                      <p class="mt-2 line-clamp-2 text-xs font-semibold leading-5 text-stone-800">{{ agentRunMessage(run) || '空任务' }}</p>
                      <p class="mt-1 truncate text-[11px] text-stone-400">{{ run.model || run.profile_id }} · {{ agentRunTimeLabel(run) }}</p>
                    </button>
                  </div>
                </div>
              </aside>
              <div class="space-y-5">
                <div class="rounded-3xl border border-stone-200 bg-white p-5 shadow-sm">
                  <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <p class="text-xs font-semibold uppercase tracking-[0.22em] text-stone-400">Collection Agent</p>
                      <h3 class="mt-1 text-2xl font-semibold text-stone-900">书稿总编与长期记忆</h3>
                      <p class="mt-2 max-w-3xl text-sm leading-6 text-stone-500">
                        这个 Agent 只服务当前作品集。它会读取书稿结构、项目圣经和你显式引用的对象，生成诊断、建议和可确认提案；不会自动改正文。
                      </p>
                    </div>
                    <div class="flex flex-wrap items-center gap-2">
                      <select
                        v-model="agentProfileId"
                        class="rounded-xl border border-stone-200 bg-white px-3 py-2 text-xs outline-none"
                        @change="saveAgentSettings"
                      >
                        <option v-for="profile in agentProfileOptions" :key="profile.id" :value="profile.id">
                          {{ profile.name }}
                        </option>
                      </select>
                      <button
                        class="rounded-xl bg-stone-100 px-3 py-2 text-xs text-stone-700 hover:bg-stone-200"
                        @click="loadAgentState"
                      >
                        刷新
                      </button>
                    </div>
                  </div>

                  <div class="mt-5 rounded-2xl border border-stone-200 bg-stone-50/80 p-2" data-testid="agent-quick-task-strip">
                    <div class="flex items-center gap-2 overflow-x-auto pb-1">
                      <button
                        v-for="task in agentQuickTasks"
                        :key="task.kind"
                        type="button"
                        :class="[
                          'min-w-[11.25rem] rounded-xl px-3 py-2 text-left ring-1 transition focus:outline-none focus:ring-2 focus:ring-amber-300',
                          agentPendingQuickTask === task.kind
                            ? 'bg-amber-50 text-stone-900 ring-amber-200'
                            : 'bg-white text-stone-800 ring-stone-200 hover:bg-stone-100'
                        ]"
                        @click="runQuickAgentTask(task.kind)"
                      >
                        <span class="block whitespace-nowrap text-sm font-semibold leading-5">{{ task.title }}</span>
                        <span class="mt-0.5 block truncate text-[11px] font-normal leading-4 text-stone-500">{{ task.subtitle }}</span>
                      </button>
                    </div>
                    <p class="mt-1 px-1 text-[11px] leading-5 text-stone-500">
                      快捷任务会先进入确认区；输入 <span class="font-semibold text-stone-700">/</span> 也能打开同一组功能。
                    </p>
                  </div>

                  <div v-if="pendingQuickTask" class="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                    <div class="flex flex-wrap items-start justify-between gap-3">
                      <div class="min-w-0 flex-1">
                        <div class="font-semibold">准备运行：{{ pendingQuickTask.title }}</div>
                        <p class="mt-1 text-xs leading-5 text-amber-800">
                          将使用 {{ selectedAgentProfileName }}，读取作品集结构、项目圣经和你已选择的引用芯片。确认后才会发送请求。
                        </p>
                        <p class="mt-2 line-clamp-2 text-xs leading-5 text-amber-700">{{ pendingQuickTask.prompt }}</p>
                      </div>
                      <div class="flex shrink-0 gap-2">
                        <button
                          class="rounded-xl bg-stone-900 px-3 py-2 text-xs font-semibold text-white disabled:opacity-40"
                          :disabled="agentRunning || Boolean(activeAgentRun)"
                          @click="confirmQuickAgentTask"
                        >
                          确认运行
                        </button>
                        <button class="rounded-xl bg-white px-3 py-2 text-xs text-amber-800 ring-1 ring-amber-200" @click="cancelQuickAgentTask">
                          取消
                        </button>
                      </div>
                    </div>
                    <p v-if="activeAgentRun" class="mt-2 text-xs text-amber-700">Agent 正在工作，不能同时启动新的快捷任务。</p>
                  </div>
                </div>

                <div v-if="agentError" class="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">
                  {{ agentError }}
                </div>

                <div v-if="activeAgentRun" class="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                  <div class="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <span class="font-semibold">Agent 正在工作</span>
                      <span class="ml-2">{{ activeAgentRun.stage_label }}</span>
                    </div>
                    <button class="rounded-xl bg-white px-3 py-1.5 text-xs font-semibold text-amber-800 ring-1 ring-amber-200" @click="cancelActiveAgentRun">
                      中断本地等待
                    </button>
                  </div>
                  <div class="mt-2 h-1.5 overflow-hidden rounded-full bg-amber-100">
                    <div class="h-full w-1/2 animate-pulse rounded-full bg-amber-400"></div>
                  </div>
                </div>

                <div class="rounded-3xl border border-stone-200 bg-white p-5 shadow-sm">
                  <div class="mb-4 flex items-center justify-between gap-3">
                    <div>
                      <h4 class="text-lg font-semibold text-stone-900">对话</h4>
                      <p class="mt-1 text-xs leading-5 text-stone-500">用自然语言提问；需要精确上下文时，先搜索并加入引用芯片。</p>
                    </div>
                    <label class="flex items-center gap-2 rounded-xl bg-stone-50 px-3 py-2 text-xs text-stone-600">
                      <input v-model="agentRequestWebContext" type="checkbox" class="h-4 w-4 rounded border-stone-300 text-indigo-600" />
                      请求模型联网
                    </label>
                  </div>

                  <div class="mb-4 rounded-2xl border border-stone-200 bg-stone-50 p-3">
                    <div class="flex flex-wrap items-center justify-between gap-2">
                      <button
                        class="rounded-xl bg-white px-3 py-2 text-sm font-semibold text-stone-700 ring-1 ring-stone-200 hover:bg-stone-100"
                        @click="openAgentReferencePicker()"
                      >
                        + 添加引用
                      </button>
                      <p class="text-xs text-stone-500">输入框里键入 @ 也会打开引用选择器。</p>
                    </div>
                    <div v-if="selectedAgentRefs.length" class="mt-3 flex flex-wrap gap-2">
                      <button
                        v-for="ref in selectedAgentRefs"
                        :key="`${ref.kind}:${ref.ref_id}`"
                        class="rounded-full bg-indigo-50 px-3 py-1 text-xs text-indigo-700 ring-1 ring-indigo-100"
                        @click="removeAgentReference(ref)"
                      >
                        {{ agentReferenceKindLabel(ref.kind) }} · {{ ref.name }} ×
                      </button>
                    </div>
                    <div v-if="agentReferencePickerOpen" class="mt-3 rounded-2xl border border-stone-200 bg-white p-3 shadow-sm">
                      <div class="flex flex-col gap-2 md:flex-row">
                        <input
                          v-model="agentReferenceQuery"
                          class="min-w-0 flex-1 rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm outline-none"
                          placeholder="搜索结构节点、文章、AI卡片、意象、文脉"
                          @keyup.enter="searchAgentReferences"
                          @input="searchAgentReferences"
                        />
                        <button class="rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white" @click="searchAgentReferences">
                          {{ agentSearchLoading ? '搜索中...' : '搜索引用' }}
                        </button>
                        <button class="rounded-xl bg-stone-100 px-3 py-2 text-sm text-stone-600" @click="clearAgentReferenceSearch">
                          清空
                        </button>
                        <button class="rounded-xl bg-white px-3 py-2 text-sm text-stone-600 ring-1 ring-stone-200" @click="closeAgentReferencePicker">
                          收起
                        </button>
                      </div>
                      <div class="mt-3 max-h-72 overflow-y-auto pr-1">
                        <div v-if="agentSearchLoading" class="rounded-xl bg-stone-50 p-3 text-sm text-stone-400">搜索中...</div>
                        <div v-else-if="!agentReferenceResults.length" class="rounded-xl border border-dashed border-stone-200 p-4 text-center text-xs text-stone-400">
                          没有匹配引用。换一个关键词，或先创建结构节点/文章/文脉。
                        </div>
                        <div v-else class="grid gap-2 md:grid-cols-2">
                          <button
                            v-for="ref in agentReferenceResults"
                            :key="`${ref.kind}:${ref.ref_id}`"
                            class="rounded-2xl border border-stone-200 bg-white p-3 text-left hover:border-indigo-200"
                            @click="addAgentReference(ref)"
                          >
                            <div class="flex items-center gap-2">
                              <span class="rounded-full bg-stone-100 px-2 py-0.5 text-[11px] text-stone-500">{{ agentReferenceKindLabel(ref.kind) }}</span>
                              <span class="truncate text-sm font-semibold text-stone-900">{{ ref.name }}</span>
                            </div>
                            <p class="mt-1 line-clamp-2 text-xs leading-5 text-stone-500">{{ ref.body_preview || '无预览' }}</p>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="relative">
                    <div
                      v-if="agentSlashMenuOpen"
                      class="absolute bottom-full left-0 z-30 mb-2 w-full max-w-xl rounded-2xl border border-stone-200 bg-white p-2 shadow-2xl"
                      data-testid="agent-slash-menu"
                    >
                      <div class="flex items-center justify-between px-3 py-2">
                        <span class="text-[11px] font-semibold uppercase tracking-[0.18em] text-stone-400">斜杠菜单</span>
                        <span class="text-[11px] text-stone-400">↑↓ 选择 · Enter 确认</span>
                      </div>
                      <div v-if="!filteredAgentSlashCommands.length" class="rounded-xl border border-dashed border-stone-200 p-3 text-center text-xs text-stone-400">
                        没有匹配功能。
                      </div>
                      <button
                        v-for="(command, index) in filteredAgentSlashCommands"
                        :key="command.command"
                        type="button"
                        :class="[
                          'flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left transition',
                          index === agentSlashSelectedIndex ? 'bg-stone-900 text-white' : 'text-stone-700 hover:bg-stone-50'
                        ]"
                        @mousedown.prevent="selectAgentSlashCommand(command)"
                      >
                        <span
                          :class="[
                            'shrink-0 rounded-lg px-2 py-1 font-mono text-[11px]',
                            index === agentSlashSelectedIndex ? 'bg-white/15 text-white' : 'bg-stone-100 text-stone-500'
                          ]"
                        >/{{ command.command }}</span>
                        <span class="min-w-0 flex-1">
                          <span class="block truncate text-sm font-semibold">{{ command.title }}</span>
                          <span :class="['block truncate text-xs', index === agentSlashSelectedIndex ? 'text-stone-200' : 'text-stone-500']">{{ command.subtitle }}</span>
                        </span>
                      </button>
                    </div>
                    <textarea
                      v-model="agentPrompt"
                      rows="5"
                      class="w-full resize-none rounded-2xl border border-stone-200 px-4 py-3 text-sm leading-6 outline-none focus:ring-2 focus:ring-indigo-200"
                      placeholder="例如：帮我检查第一部的结构断点；输入 @ 加引用；输入 / 打开功能菜单。"
                      @keydown="handleAgentPromptKeydown"
                      @input="handleAgentPromptInput"
                    />
                  </div>
                  <div class="mt-3 flex flex-wrap items-center justify-between gap-3">
                    <p class="max-w-xl text-xs leading-5 text-stone-500">
                      普通文字会作为对话发送；<span class="font-semibold text-stone-700">/</span> 打开功能菜单，<span class="font-semibold text-stone-700">@</span> 添加上下文引用。
                    </p>
                    <button
                      class="rounded-xl bg-stone-900 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-40"
                      :disabled="agentRunning || Boolean(activeAgentRun) || !agentPrompt.trim()"
                      @click="runAgentPrompt()"
                    >
                      {{ agentRunning ? '启动中...' : '发送给 Agent' }}
                    </button>
                  </div>
                </div>

                <div class="space-y-3">
                  <article
                    v-for="run in agentRuns"
                    :key="run.id"
                    :id="`collection-agent-run-${run.id}`"
                    :class="[
                      'rounded-3xl border bg-white p-5 shadow-sm transition-all',
                      agentHighlightedRunId === run.id ? 'border-amber-400 ring-2 ring-amber-200' : 'border-stone-200'
                    ]"
                  >
                    <div class="flex flex-wrap items-start justify-between gap-3">
                      <div class="min-w-0">
                        <div class="flex flex-wrap items-center gap-2 text-xs font-semibold text-stone-400">
                          <span>{{ agentRunTaskLabel(run) }}</span>
                          <span>·</span>
                          <span>{{ run.stage_label }}</span>
                          <span>·</span>
                          <span>{{ run.model || run.profile_id }}</span>
                        </div>
                        <h4 class="mt-1 line-clamp-2 text-base font-semibold text-stone-900">{{ agentRunMessage(run) }}</h4>
                      </div>
                      <span :class="['rounded-full px-2 py-1 text-xs ring-1', run.status === 'succeeded' ? 'bg-emerald-50 text-emerald-700 ring-emerald-100' : run.status === 'failed' ? 'bg-red-50 text-red-700 ring-red-100' : 'bg-amber-50 text-amber-700 ring-amber-100']">
                        {{ run.status }}
                      </span>
                    </div>
                    <div v-if="agentRunAnswer(run)" class="mt-4 whitespace-pre-wrap text-sm leading-7 text-stone-700">
                      {{ agentRunVisibleAnswer(run) }}
                    </div>
                    <button
                      v-if="agentRunCanCollapse(run)"
                      class="mt-3 rounded-xl bg-stone-100 px-3 py-1.5 text-xs font-semibold text-stone-600 hover:bg-stone-200"
                      @click="toggleAgentRunCollapsed(run)"
                    >
                      {{ agentCollapsedRunIds.includes(run.id) ? '展开完整回答' : '收起长回答' }}
                    </button>
                    <div v-if="run.error" class="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">
                      {{ run.error }}
                    </div>
                    <div v-if="run.actions.length" class="mt-4 space-y-2">
                      <div class="text-xs font-semibold uppercase tracking-[0.18em] text-stone-400">Proposals</div>
                      <article
                        v-for="action in run.actions"
                        :key="action.id"
                        class="rounded-2xl border border-stone-200 bg-stone-50 p-3"
                      >
                        <div class="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <div class="flex flex-wrap items-center gap-2">
                              <span class="rounded-full bg-white px-2 py-0.5 text-[11px] text-stone-500 ring-1 ring-stone-200">{{ agentActionTypeLabel(action.action_type) }}</span>
                              <span :class="['rounded-full px-2 py-0.5 text-[11px] ring-1', agentActionStatusTone(action.status)]">{{ action.status }}</span>
                            </div>
                            <h5 class="mt-2 text-sm font-semibold text-stone-900">{{ action.title }}</h5>
                            <p class="mt-1 text-xs leading-5 text-stone-500">{{ action.summary || action.reason }}</p>
                          </div>
                          <div v-if="action.status === 'pending'" class="flex shrink-0 gap-2">
                            <button class="rounded-xl bg-stone-900 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40" :disabled="agentApplyingActionId === action.id" @click="applyAgentAction(action)">
                              应用
                            </button>
                            <button class="rounded-xl bg-white px-3 py-1.5 text-xs text-stone-600 ring-1 ring-stone-200 disabled:opacity-40" :disabled="agentApplyingActionId === action.id" @click="rejectAgentAction(action)">
                              拒绝
                            </button>
                          </div>
                        </div>
                        <pre class="mt-3 max-h-44 overflow-auto whitespace-pre-wrap rounded-xl bg-white p-3 text-xs leading-5 text-stone-600">{{ formatAgentPreview(action.preview) }}</pre>
                        <p v-if="action.risk" class="mt-2 text-xs leading-5 text-amber-700">风险：{{ action.risk }}</p>
                      </article>
                    </div>
                  </article>
                  <div v-if="!agentLoading && !agentRuns.length" class="rounded-3xl border border-dashed border-stone-300 bg-white/70 p-8 text-center">
                    <h4 class="text-base font-semibold text-stone-700">还没有 Agent 记录</h4>
                    <p class="mt-2 text-sm leading-6 text-stone-500">先点一次体检作品集，或者直接在对话框里提出你的问题。</p>
                  </div>
                </div>
              </div>

              <aside class="space-y-5">
                <div class="rounded-3xl border border-stone-200 bg-white p-5 shadow-sm">
                  <div class="flex items-start justify-between gap-3">
                    <div>
                      <h4 class="font-semibold text-stone-900">项目圣经</h4>
                      <p class="mt-1 text-xs leading-5 text-stone-500">这是 Agent 的长期记忆。你可以手动维护，也可以应用 Agent 的记忆更新提案。</p>
                    </div>
                    <button class="shrink-0 whitespace-nowrap rounded-xl bg-stone-900 px-3 py-2 text-xs font-semibold text-white disabled:opacity-40" :disabled="agentMemorySaving" @click="saveAgentMemory">
                      {{ agentMemorySaving ? '保存中...' : '保存记忆' }}
                    </button>
                  </div>
                  <div v-if="agentLoading" class="mt-4 text-sm text-stone-400">加载中...</div>
                  <div v-else-if="agentState" class="mt-4 space-y-3">
                    <label v-for="section in agentState.memory.sections" :key="section.id" class="block">
                      <span class="text-xs font-semibold text-stone-600">{{ section.title }}</span>
                      <span class="mt-0.5 block text-[11px] leading-5 text-stone-400">{{ section.help }}</span>
                      <textarea
                        v-model="agentMemoryDraft[section.id]"
                        rows="3"
                        class="mt-1 w-full resize-y rounded-xl border border-stone-200 px-3 py-2 text-xs leading-5 outline-none focus:ring-2 focus:ring-indigo-200"
                      />
                    </label>
                  </div>
                </div>

                <div class="rounded-3xl border border-stone-200 bg-white p-5 shadow-sm">
                  <div class="flex items-center justify-between gap-3">
                    <div>
                      <h4 class="font-semibold text-stone-900">待确认提案</h4>
                      <p class="mt-1 text-xs text-stone-500">只有你点击应用后才会写入数据。</p>
                    </div>
                    <span class="rounded-full bg-amber-50 px-2 py-1 text-xs text-amber-700">{{ pendingAgentActions.length }}</span>
                  </div>
                  <div v-if="!pendingAgentActions.length" class="mt-4 rounded-2xl border border-dashed border-stone-200 p-4 text-center text-xs text-stone-400">
                    暂无待确认提案。
                  </div>
                  <div v-else class="mt-4 space-y-2">
                    <article v-for="action in pendingAgentActions" :key="action.id" class="rounded-2xl border border-stone-200 bg-stone-50 p-3">
                      <div class="text-[11px] text-stone-500">{{ agentActionTypeLabel(action.action_type) }}</div>
                      <div class="mt-1 text-sm font-semibold text-stone-900">{{ action.title }}</div>
                      <p class="mt-1 line-clamp-3 text-xs leading-5 text-stone-500">{{ action.summary || action.reason }}</p>
                      <div class="mt-3 flex gap-2">
                        <button class="rounded-xl bg-stone-900 px-3 py-1.5 text-xs font-semibold text-white" @click="applyAgentAction(action)">应用</button>
                        <button class="rounded-xl bg-white px-3 py-1.5 text-xs text-stone-600 ring-1 ring-stone-200" @click="rejectAgentAction(action)">拒绝</button>
                      </div>
                    </article>
                  </div>
                </div>

                <div class="rounded-3xl border border-stone-200 bg-white p-5 shadow-sm">
                  <h4 class="font-semibold text-stone-900">记忆规则</h4>
                  <div class="mt-4 space-y-2 text-xs leading-5 text-stone-500">
                    <p>普通对话只留在当前会话里，不会自动写入长期记忆。</p>
                    <p>“整理项目记忆”只生成更新提案；你应用提案后才会写入项目圣经。</p>
                    <p>被拒绝的提案不会进入记忆；清空会话也不会删除作品集、文章、大纲或项目圣经。</p>
                  </div>
                </div>
              </aside>
            </div>
          </section>
        </template>

        <template v-else-if="viewMode === 'export'">
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

    <div v-if="createDialogOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div class="w-full max-w-[480px] rounded-3xl bg-white p-6 shadow-2xl">
        <div class="flex items-center justify-between gap-3">
          <h3 class="text-xl font-semibold">{{ t('collections.createTitle') }}</h3>
          <button class="rounded-lg px-2 py-1 text-sm font-semibold text-stone-400 hover:bg-stone-100 hover:text-stone-700" @click="createDialogOpen = false">×</button>
        </div>
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

    <div v-if="articlePickerOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div class="flex max-h-[82vh] w-full max-w-[720px] flex-col rounded-3xl bg-white shadow-2xl">
        <div class="border-b border-stone-200 p-6">
          <div class="flex items-start justify-between gap-3">
            <div>
              <h3 class="text-xl font-semibold">{{ t('collections.pickArticles') }}</h3>
              <p class="mt-1 text-sm text-stone-500">{{ t('collections.pickHint') }}</p>
            </div>
            <button class="rounded-lg px-2 py-1 text-sm font-semibold text-stone-400 hover:bg-stone-100 hover:text-stone-700" @click="articlePickerOpen = false">×</button>
          </div>
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

    <div v-if="agentClearDialogOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div class="w-full max-w-lg rounded-3xl bg-white p-6 shadow-2xl">
        <h3 class="text-xl font-semibold text-stone-900">清空 Agent 会话？</h3>
        <p class="mt-3 text-sm leading-6 text-stone-600">
          这会清掉当前作品集 Agent 的对话消息、已结束任务和已处理提案记录；项目圣经、文章、大纲、已应用写入的数据，以及仍待确认的提案都会保留。
        </p>
        <p class="mt-3 rounded-2xl bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-800">
          普通对话不会自动进入长期记忆。只有手动保存项目圣经，或应用“更新记忆”提案，才会写入长期记忆。
        </p>
        <div v-if="agentError" class="mt-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
          {{ agentError }}
        </div>
        <div class="mt-6 flex justify-end gap-3">
          <button class="rounded-xl bg-stone-100 px-4 py-2 text-sm text-stone-700" :disabled="agentClearing" @click="agentClearDialogOpen = false">
            取消
          </button>
          <button
            class="rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
            :disabled="agentClearing || Boolean(activeAgentRun)"
            @click="clearAgentConversation"
          >
            {{ agentClearing ? '清空中...' : '确认清空' }}
          </button>
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
