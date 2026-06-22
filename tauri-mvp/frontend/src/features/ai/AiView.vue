<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { appApi } from '../../api/app'
import { aiApi, type AiContextAttachment, type AiTaskPreset, type AiTaskPresetMap, type Message } from '../../api/ai'
import { articlesApi, type Entry } from '../../api/articles'
import { aiCardApi, type AiCard } from '../../api/aiCards'
import { errorMessage, isHttpStatus } from '../../api/base'
import { libraryApi, type Reference } from '../../api/library'
import { notesApi } from '../../api/notes'
import { useI18n } from '../../i18n'
import { countParagraphs } from '../articles/articleList'
import { applyArticleBodyEdit, selectArticleBodyText } from './applyArticleEdit'
import { useAiStore } from './store'
import {
  useAiWorkspaceStore,
  type AiTab,
  type ContextItem,
  type ContextKind,
  type RouteSelection,
  type TaskType,
  type ToolScope,
} from './workspaceStore'
import {
  buildTaskRequestOptions,
  cloneControls,
  isFocusTask,
  mergeControls,
} from './taskControls'

type ChatScopeKind = 'global' | 'article' | 'collection'

interface TaskOption {
  value: TaskType
  label: string
  desc: string
}

interface TaskGroup {
  name: string
  tasks: TaskOption[]
}

const store = useAiStore()
const workspace = useAiWorkspaceStore()
const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const aiCards = ref<AiCard[]>([])
const showCardSelector = ref(false)
const sceneSearchQuery = ref('')
const sceneSearchResults = ref<AiCard[]>([])
const sceneSearchLoading = ref(false)
const sceneSearchError = ref('')

const referencePickerOpen = ref(false)
const referenceSearch = ref('')
const referenceResults = ref<Reference[]>([])
const selectedReferenceIds = ref<string[]>([])
const referenceLoading = ref(false)

const articles = ref<Entry[]>([])
const taskPresets = ref<AiTaskPresetMap>({})
const taskPresetsSupported = ref(true)
const presetName = ref('')
const CHAT_SYSTEM_PROMPT_LIMIT = 4000
const chatSystemPrompt = ref('')
const chatSystemPromptDraft = ref('')
const chatSettingsSupported = ref(true)
const savingChatSettings = ref(false)
const chatNotice = ref('')
const backendCapabilities = ref<string[] | null>(null)
const activeTab = computed({
  get: () => workspace.activeTab,
  set: (value: AiTab) => {
    workspace.activeTab = value
  },
})
const taskType = computed({
  get: () => workspace.taskType,
  set: (value: TaskType) => {
    workspace.setTaskType(value)
  },
})
const currentTaskState = computed(() => workspace.currentTask())
const taskInput = computed({
  get: () => currentTaskState.value.taskInput,
  set: (value: string) => {
    currentTaskState.value.taskInput = value
  },
})
const taskResult = computed({
  get: () => currentTaskState.value.taskResult,
  set: (value: string) => {
    currentTaskState.value.taskResult = value
  },
})
const showComparison = computed({
  get: () => currentTaskState.value.showComparison,
  set: (value: boolean) => {
    currentTaskState.value.showComparison = value
  },
})
const selectedCardIds = computed({
  get: () => currentTaskState.value.selectedCardIds,
  set: (value: string[]) => {
    currentTaskState.value.selectedCardIds = value
  },
})
const manualContextItems = computed({
  get: () => currentTaskState.value.manualContextItems,
  set: (value: ContextItem[]) => {
    currentTaskState.value.manualContextItems = value
  },
})
const scopeType = computed({
  get: () => currentTaskState.value.scopeType,
  set: (value: ToolScope) => {
    currentTaskState.value.scopeType = value
  },
})
const selectedArticleId = computed({
  get: () => currentTaskState.value.selectedArticleId,
  set: (value: string | null) => {
    currentTaskState.value.selectedArticleId = value
  },
})
const routeSelection = computed({
  get: () => currentTaskState.value.routeSelection,
  set: (value: RouteSelection | null) => {
    currentTaskState.value.routeSelection = value
  },
})
const controlsByTask = computed(() => workspace.tasks)
const selectedPresetId = computed({
  get: () => currentTaskState.value.selectedPresetId,
  set: (value: string) => {
    currentTaskState.value.selectedPresetId = value
  },
})
const error = computed({
  get: () => currentTaskState.value.error,
  set: (value: string) => {
    currentTaskState.value.error = value
  },
})
const notice = computed({
  get: () => currentTaskState.value.notice,
  set: (value: string) => {
    currentTaskState.value.notice = value
  },
})
const chatInput = computed({
  get: () => workspace.chatInput,
  set: (value: string) => {
    workspace.chatInput = value
  },
})
const chatScopeKind = computed({
  get: () => workspace.chatScopeKind,
  set: (value: ChatScopeKind) => {
    workspace.chatScopeKind = value
  },
})
const chatScopeId = computed({
  get: () => workspace.chatScopeId,
  set: (value: string | null) => {
    workspace.chatScopeId = value
  },
})

const taskGroups = computed<TaskGroup[]>(() => [
  {
    name: t('ai.taskGroups.common'),
    tasks: [
      { value: 'polish', label: t('ai.tasks.polish.label'), desc: t('ai.tasks.polish.desc') },
      { value: 'expand', label: t('ai.tasks.expand.label'), desc: t('ai.tasks.expand.desc') },
      { value: 'continue', label: t('ai.tasks.continue.label'), desc: t('ai.tasks.continue.desc') },
      { value: 'rewrite', label: t('ai.tasks.rewrite.label'), desc: t('ai.tasks.rewrite.desc') },
    ],
  },
  {
    name: t('ai.taskGroups.advanced'),
    tasks: [
      { value: 'style_transfer', label: t('ai.tasks.styleTransfer.label'), desc: t('ai.tasks.styleTransfer.desc') },
      { value: 'outline', label: t('ai.tasks.outline.label'), desc: t('ai.tasks.outline.desc') },
      { value: 'title', label: t('ai.tasks.title.label'), desc: t('ai.tasks.title.desc') },
      { value: 'summarize', label: t('ai.tasks.summarize.label'), desc: t('ai.tasks.summarize.desc') },
    ],
  },
])

const selectedCards = computed(() =>
  [...aiCards.value, ...sceneSearchResults.value]
    .filter((card, index, allCards) => allCards.findIndex((item) => item.id === card.id) === index)
    .filter((card) => selectedCardIds.value.includes(card.id))
)

const nonSceneCards = computed(() => aiCards.value.filter((card) => card.card_type !== 'scene'))

const selectedArticle = computed(() =>
  articles.value.find((article) => article.id === selectedArticleId.value) ?? null
)

const selectedChatArticle = computed(() =>
  articles.value.find((article) => article.id === chatScopeId.value) ?? null
)

const selectedChatArticleChars = computed(() => selectedChatArticle.value?.body?.length ?? 0)

const selectedChatArticleParagraphs = computed(() => countParagraphs(selectedChatArticle.value?.body ?? ''))

const taskDescription = computed(() =>
  taskGroups.value.flatMap((group) => group.tasks).find((task) => task.value === taskType.value)?.desc ?? ''
)

const selectedArticleSubject = computed(() => {
  const article = selectedArticle.value
  if (!article) return ''
  const { bodyText } = selectArticleBodyText(article.body || '')
  const selection = routeSelection.value
  if (selection && selection.articleId === article.id && selection.end > selection.start) {
    return bodyText.slice(
      Math.max(0, selection.start),
      Math.min(bodyText.length, selection.end),
    )
  }
  return bodyText
})

const originalText = computed(() =>
  scopeType.value === 'article' ? selectedArticleSubject.value : taskInput.value
)

const hasArticleSelection = computed(() =>
  Boolean(routeSelection.value && routeSelection.value.articleId === selectedArticleId.value && routeSelection.value.end > routeSelection.value.start)
)

const currentTaskPresets = computed(() => taskPresets.value[taskType.value] ?? [])

const selectedContextItems = computed<ContextItem[]>(() => [
  ...selectedCards.value.map(cardToContextItem),
  ...manualContextItems.value,
])

const contextAttachments = computed<AiContextAttachment[]>(() =>
  selectedContextItems.value.map((item) => ({
    kind: item.kind,
    ref_id: item.ref_id,
    name: item.title,
    body: item.body,
  }))
)

const canAddArticleNotes = computed(() => scopeType.value === 'article' && Boolean(selectedArticleId.value))

const chatScopeLabel = computed(() => {
  return selectedChatArticle.value?.title || t('ai.chatNoArticleSelected')
})

const cardTypeLabels = computed<Record<string, string>>(() => ({
  style: t('aiCards.cardTypes.style'),
  character: t('aiCards.cardTypes.character'),
  scene: t('aiCards.cardTypes.scene'),
}))

onMounted(async () => {
  await loadBackendCapabilities()
  await Promise.all([loadAiCards(), loadArticles(), loadTaskPresets(), loadChatSettings()])
  applyRouteScope()
  await loadChatThread()
})

watch(
  () => [route.query.tab, route.query.scope_kind, route.query.scope_id, route.query.selection_start, route.query.selection_end, route.query.task],
  async () => {
    applyRouteScope()
    await loadChatThread()
  }
)

watch([chatScopeKind, chatScopeId], async () => {
  if (
    activeTab.value === 'chat'
    && chatScopeId.value
    && (route.query.scope_kind !== 'article' || route.query.scope_id !== chatScopeId.value)
  ) {
    await router.replace({
      name: 'ai',
      query: {
        ...route.query,
        tab: 'chat',
        scope_kind: 'article',
        scope_id: chatScopeId.value,
      },
    })
    return
  }
  if (activeTab.value === 'chat' && !chatScopeId.value && route.query.scope_id) {
    const nextQuery = { ...route.query }
    delete nextQuery.scope_kind
    delete nextQuery.scope_id
    await router.replace({
      name: 'ai',
      query: {
        ...nextQuery,
        tab: 'chat',
      },
    })
    return
  }
  await loadChatThread()
})

watch(taskType, () => {
  selectedPresetId.value = ''
})

async function loadAiCards() {
  try {
    aiCards.value = await aiCardApi.listCards()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function loadArticles() {
  try {
    articles.value = await articlesApi.listArticles(500)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function loadBackendCapabilities() {
  try {
    const info = await appApi.getVersion()
    backendCapabilities.value = info.capabilities
  } catch {
    backendCapabilities.value = null
  }
}

function backendCapabilityMissing(capability: string): boolean {
  return Array.isArray(backendCapabilities.value)
    && !backendCapabilities.value.includes(capability)
}

async function loadTaskPresets() {
  if (backendCapabilityMissing('ai_task_presets')) {
    taskPresetsSupported.value = false
    taskPresets.value = {}
    return
  }
  try {
    taskPresets.value = await aiApi.listTaskPresets()
    taskPresetsSupported.value = true
  } catch (e) {
    if (isHttpStatus(e, 404)) {
      taskPresetsSupported.value = false
      taskPresets.value = {}
    } else {
      error.value = errorMessage(e)
    }
  }
}

async function loadChatSettings() {
  if (backendCapabilityMissing('ai_chat_settings')) {
    chatSettingsSupported.value = false
    chatSystemPrompt.value = ''
    chatSystemPromptDraft.value = ''
    return
  }
  try {
    const settings = await aiApi.getChatSettings()
    chatSystemPrompt.value = settings.system_prompt
    chatSystemPromptDraft.value = settings.system_prompt
    chatSettingsSupported.value = true
  } catch (e) {
    if (isHttpStatus(e, 404)) {
      chatSettingsSupported.value = false
      chatSystemPrompt.value = ''
      chatSystemPromptDraft.value = ''
    } else {
      error.value = errorMessage(e)
    }
  }
}

function normalizeScopeKind(value: unknown): ChatScopeKind {
  return value === 'article' || value === 'collection' || value === 'global' ? value : 'global'
}

function normalizeTaskType(value: unknown): TaskType | null {
  return ['polish', 'rewrite', 'expand', 'continue', 'style_transfer', 'summarize', 'outline', 'title'].includes(String(value))
    ? String(value) as TaskType
    : null
}

function applyRouteScope() {
  if (route.query.tab === 'chat') activeTab.value = 'chat'
  if (route.query.tab === 'tools') activeTab.value = 'tools'

  const routedTask = normalizeTaskType(route.query.task)
  if (routedTask) taskType.value = routedTask

  const scopeKind = normalizeScopeKind(route.query.scope_kind)
  const scopeId = typeof route.query.scope_id === 'string' ? route.query.scope_id : null
  if (activeTab.value === 'chat') {
    chatScopeKind.value = 'article'
    chatScopeId.value = scopeKind === 'article' ? scopeId : null
  }

  if (activeTab.value === 'tools' && scopeKind === 'article' && scopeId) {
    scopeType.value = 'article'
    selectedArticleId.value = scopeId
    const start = parseNumberQuery(route.query.selection_start)
    const end = parseNumberQuery(route.query.selection_end)
    routeSelection.value =
      start !== null && end !== null && end > start
        ? { articleId: scopeId, start, end }
        : null
  }
}

async function loadChatThread() {
  if (activeTab.value !== 'chat') return
  chatScopeKind.value = 'article'
  if (!chatScopeId.value) {
    store.selectedThreadId = null
    store.messages = []
    return
  }
  try {
    store.selectedThreadId = null
    store.messages = []
    await store.loadCurrentThread('article', chatScopeId.value, true)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function openChatTab() {
  activeTab.value = 'chat'
  const scopeKind = normalizeScopeKind(route.query.scope_kind)
  const scopeId = typeof route.query.scope_id === 'string' ? route.query.scope_id : null
  if (scopeKind === 'article' && scopeId) {
    chatScopeId.value = scopeId
  }
  if (chatScopeId.value) {
    await router.replace({
      name: 'ai',
      query: {
        ...route.query,
        tab: 'chat',
        scope_kind: 'article',
        scope_id: chatScopeId.value,
      },
    })
    return
  }
  await loadChatThread()
}

async function handleRunTask() {
  error.value = ''
  notice.value = ''

  const subject = originalText.value
  if (!subject.trim()) {
    error.value = scopeType.value === 'article' ? t('ai.inputArticleRequired') : t('ai.inputTextRequired')
    return
  }

  try {
    const controls = controlsByTask.value[taskType.value].controls
    const focusOptions = isFocusTask(taskType.value)
      ? buildTaskRequestOptions(taskType.value, controls)
      : { extra_instructions: controls.extraInstructions }
    taskResult.value = await store.runTask({
      task_type: taskType.value,
      text: subject,
      target_kind: scopeType.value === 'article' ? (hasArticleSelection.value ? 'selection' : 'article') : 'paste',
      target_ref_id: selectedArticleId.value,
      attachments: contextAttachments.value,
      ...focusOptions,
    })
    showComparison.value = true
  } catch (e) {
    taskResult.value = `${t('common.error')}: ${e instanceof Error ? e.message : String(e)}`
    showComparison.value = true
  }
}

async function sendChat() {
  const message = chatInput.value.trim()
  if (!message || store.loading) return
  if (!chatScopeId.value) {
    error.value = t('ai.chatSelectArticleFirst')
    return
  }
  error.value = ''
  chatNotice.value = ''
  chatInput.value = ''
  try {
    await store.sendMessage(message, 'article', chatScopeId.value)
  } catch (e) {
    if (!chatInput.value.trim()) {
      chatInput.value = message
    }
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function saveChatSettings() {
  if (!chatSettingsSupported.value) {
    chatNotice.value = ''
    error.value = ''
    return
  }
  savingChatSettings.value = true
  error.value = ''
  chatNotice.value = ''
  try {
    const saved = await aiApi.saveChatSettings({
      system_prompt: chatSystemPromptDraft.value.slice(0, CHAT_SYSTEM_PROMPT_LIMIT),
    })
    chatSystemPrompt.value = saved.system_prompt
    chatSystemPromptDraft.value = saved.system_prompt
    chatNotice.value = t('ai.chatPromptSaved')
  } catch (e) {
    if (isHttpStatus(e, 404)) {
      chatSettingsSupported.value = false
    } else {
      error.value = errorMessage(e)
    }
  } finally {
    savingChatSettings.value = false
  }
}

async function copyChatMessage(message: Message) {
  try {
    await navigator.clipboard.writeText(message.content)
    chatNotice.value = t('ai.chatCopied')
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function saveAssistantReplyAsNote(message: Message) {
  const messageScopeId = typeof message.__scope_id === 'string' ? message.__scope_id : chatScopeId.value
  if (message.role !== 'assistant' || !messageScopeId || !message.content.trim()) return
  error.value = ''
  chatNotice.value = ''
  try {
    await notesApi.createNote(messageScopeId, message.content.trim(), false)
    chatNotice.value = t('ai.chatSavedAsNote')
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

function canSaveAssistantReply(message: Message): boolean {
  return message.role === 'assistant'
    && message.__scope_kind === 'article'
    && typeof message.__scope_id === 'string'
    && message.__scope_id.length > 0
}

function openChatArticle() {
  if (!chatScopeId.value) return
  router.push({ name: 'articles', query: { id: chatScopeId.value } })
}

async function copyResult() {
  try {
    await navigator.clipboard.writeText(taskResult.value)
    notice.value = t('ai.copied')
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function applyResultToArticle(mode: 'replace' | 'insert_after') {
  if (scopeType.value !== 'article' || !selectedArticleId.value || !taskResult.value.trim()) return
  error.value = ''
  notice.value = ''
  try {
    const article = await articlesApi.get(selectedArticleId.value)
    const { bodyText } = selectArticleBodyText(article.body || '')
    const selection = routeSelection.value?.articleId === article.id ? routeSelection.value : null
    const start = selection ? selection.start : 0
    const end = selection ? selection.end : bodyText.length
    if (!selection && mode === 'replace' && !confirm(t('ai.confirmReplace'))) return
    const edit = applyArticleBodyEdit(article.body || '', start, end, taskResult.value, mode)
    await articlesApi.updateArticle(article.id, {
      title: article.title,
      body: edit.body,
      tags: article.tags,
    })
    await loadArticles()
    notice.value = mode === 'replace' ? t('ai.replaceSuccess') : t('ai.insertSuccess')
    await router.push({
      name: 'articles',
      query: {
        id: article.id,
        focus_start: String(edit.selectionStart),
        focus_end: String(edit.selectionEnd),
      },
    })
  } catch (e) {
    error.value = `${t('ai.replaceFailed')}：${e instanceof Error ? e.message : String(e)}`
  }
}

function toggleCard(cardId: string) {
  if (selectedCardIds.value.includes(cardId)) {
    selectedCardIds.value = selectedCardIds.value.filter((id) => id !== cardId)
  } else {
    selectedCardIds.value = [...selectedCardIds.value, cardId]
  }
}

async function searchSceneCards() {
  const query = sceneSearchQuery.value.trim()
  sceneSearchError.value = ''
  if (!query) {
    sceneSearchResults.value = []
    return
  }
  sceneSearchLoading.value = true
  try {
    sceneSearchResults.value = await aiCardApi.searchCards(query, 'scene', 30)
  } catch (e) {
    sceneSearchError.value = errorMessage(e)
    sceneSearchResults.value = []
  } finally {
    sceneSearchLoading.value = false
  }
}

function removeContextItem(item: ContextItem) {
  if (item.kind === 'ai_card') {
    selectedCardIds.value = selectedCardIds.value.filter((id) => id !== item.ref_id)
    return
  }
  manualContextItems.value = manualContextItems.value.filter((context) => context.uid !== item.uid)
}

function clearContextItems() {
  selectedCardIds.value = []
  manualContextItems.value = []
}

function clearCurrentResult() {
  workspace.clearCurrentResult()
  notice.value = t('ai.currentResultCleared')
}

function clearCurrentTaskState() {
  workspace.clearCurrentTask()
  showCardSelector.value = false
  sceneSearchResults.value = []
  sceneSearchQuery.value = ''
  notice.value = t('ai.currentTaskCleared')
}

function clearAllWorkspaceState() {
  if (!confirm(t('ai.clearAllWorkspaceConfirm'))) return
  workspace.clearAllTools()
  showCardSelector.value = false
  sceneSearchResults.value = []
  sceneSearchQuery.value = ''
  notice.value = t('ai.allWorkspaceCleared')
}

async function addArticleNotesContext() {
  if (!selectedArticleId.value) return
  error.value = ''
  notice.value = ''
  try {
    const notes = await notesApi.listNotes(selectedArticleId.value, false)
    const openNotes = notes
      .filter((note) => note.status === 'open')
      .sort((a, b) => {
        if (a.pinned !== b.pinned) return a.pinned ? -1 : 1
        return a.sort_order - b.sort_order
      })
    if (!openNotes.length) {
      notice.value = t('ai.noOpenNotes')
      return
    }
    const body = openNotes.map((note, index) => `${index + 1}. ${note.body}`).join('\n')
    upsertManualContext({
      uid: `writing_note:${selectedArticleId.value}`,
      kind: 'writing_note',
      ref_id: selectedArticleId.value,
      title: t('ai.articleNotesContextTitle', { count: openNotes.length }),
      subtitle: selectedArticle.value?.title || t('articles.untitled'),
      body,
    })
    notice.value = t('ai.contextAdded')
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function openReferencePicker() {
  referencePickerOpen.value = true
  selectedReferenceIds.value = []
  await searchReferences()
}

async function searchReferences() {
  referenceLoading.value = true
  try {
    referenceResults.value = referenceSearch.value.trim()
      ? await libraryApi.searchReferences(referenceSearch.value.trim(), 100)
      : await libraryApi.listReferences(100)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    referenceLoading.value = false
  }
}

function toggleReference(referenceId: string) {
  if (selectedReferenceIds.value.includes(referenceId)) {
    selectedReferenceIds.value = selectedReferenceIds.value.filter((id) => id !== referenceId)
  } else {
    selectedReferenceIds.value = [...selectedReferenceIds.value, referenceId]
  }
}

function addSelectedReferences() {
  const selected = referenceResults.value.filter((reference) => selectedReferenceIds.value.includes(reference.id))
  for (const reference of selected) {
    upsertManualContext(referenceToContextItem(reference))
  }
  referencePickerOpen.value = false
  if (selected.length) notice.value = t('ai.contextAdded')
}

async function saveCurrentPreset() {
  if (!taskPresetsSupported.value) {
    notice.value = ''
    error.value = ''
    return
  }
  const name = presetName.value.trim()
  if (!name) {
    error.value = t('ai.presetNameRequired')
    return
  }
  const current = taskPresets.value[taskType.value] ?? []
  const nextPreset: AiTaskPreset = {
    id: makeId(),
    task_type: taskType.value,
    name,
    controls: cloneControls(controlsByTask.value[taskType.value].controls) as unknown as Record<string, unknown>,
  }
  const next = {
    ...taskPresets.value,
    [taskType.value]: [
      nextPreset,
      ...current.filter((preset) => preset.name.trim().toLowerCase() !== name.toLowerCase()),
    ],
  }
  try {
    taskPresets.value = await aiApi.saveTaskPresets(next)
    presetName.value = ''
    selectedPresetId.value = nextPreset.id
    notice.value = t('ai.presetSaved')
  } catch (e) {
    if (isHttpStatus(e, 404)) {
      taskPresetsSupported.value = false
    } else {
      error.value = errorMessage(e)
    }
  }
}

function applyPreset(presetId: string) {
  const preset = currentTaskPresets.value.find((item) => item.id === presetId)
  if (!preset) return
  controlsByTask.value[taskType.value].controls = mergeControls(preset.controls)
  selectedPresetId.value = presetId
  notice.value = t('ai.presetApplied')
}

async function deletePreset(preset: AiTaskPreset) {
  if (!taskPresetsSupported.value) return
  const next = {
    ...taskPresets.value,
    [taskType.value]: currentTaskPresets.value.filter((item) => item.id !== preset.id),
  }
  try {
    taskPresets.value = await aiApi.saveTaskPresets(next)
    if (selectedPresetId.value === preset.id) selectedPresetId.value = ''
  } catch (e) {
    if (isHttpStatus(e, 404)) {
      taskPresetsSupported.value = false
    } else {
      error.value = errorMessage(e)
    }
  }
}

function cardToContextItem(card: AiCard): ContextItem {
  return {
    uid: `ai_card:${card.id}`,
    kind: 'ai_card',
    ref_id: card.id,
    title: card.title,
    subtitle: cardTypeLabels.value[card.card_type] ?? card.card_type,
    body: aiCardContextBody(card),
  }
}

function aiCardContextBody(card: AiCard): string {
  if (card.card_type !== 'scene') return card.content
  return limitSceneReference(card.content)
}

function limitSceneReference(content: string): string {
  const marker = '【参考原文（可选）】'
  const index = content.indexOf(marker)
  if (index < 0) return content
  const before = content.slice(0, index + marker.length).trimEnd()
  const after = content.slice(index + marker.length)
  const quotes = after
    .split(/\n+/)
    .map((line) => line.trim())
    .filter((line) => line && line !== '无')
    .slice(0, 3)
  return `${before}\n${quotes.length ? quotes.join('\n') : '无'}`
}

function referenceToContextItem(reference: Reference): ContextItem {
  const source = [reference.source_title ? `《${reference.source_title}》` : '', reference.source_author].filter(Boolean).join(' ')
  return {
    uid: `reference:${reference.id}`,
    kind: 'reference',
    ref_id: reference.id,
    title: source || t('library.empty'),
    subtitle: reference.usage_kind ? t(`library.${reference.usage_kind}`) : t('library.other'),
    body: [
      reference.content,
      reference.personal_note ? `\n${t('library.personalNote')}：${reference.personal_note}` : '',
    ].join('').trim(),
  }
}

function upsertManualContext(item: ContextItem) {
  manualContextItems.value = [
    item,
    ...manualContextItems.value.filter((context) => context.uid !== item.uid),
  ]
}

function contextKindLabel(kind: ContextKind): string {
  if (kind === 'ai_card') return t('ai.contextAiCard')
  if (kind === 'writing_note') return t('ai.contextWritingNote')
  return t('ai.contextReference')
}

function parseNumberQuery(value: unknown): number | null {
  if (typeof value !== 'string') return null
  const parsed = Number.parseInt(value, 10)
  return Number.isFinite(parsed) ? parsed : null
}

function makeId(): string {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`
}
</script>

<template>
  <div class="flex h-full flex-col overflow-hidden bg-gray-50">
    <header class="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4">
      <div>
        <h1 class="text-xl font-bold">{{ t('ai.title') }}</h1>
        <p class="text-sm text-gray-500">{{ t('ai.subtitle') }}</p>
      </div>
      <div class="rounded-xl bg-gray-100 p-1">
        <button
          @click="activeTab = 'tools'"
          :class="[
            'rounded-lg px-4 py-2 text-sm font-semibold transition-colors',
            activeTab === 'tools' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-900',
          ]"
        >
          {{ t('ai.toolsTab') }}
        </button>
        <button
          @click="openChatTab"
          :class="[
            'rounded-lg px-4 py-2 text-sm font-semibold transition-colors',
            activeTab === 'chat' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-900',
          ]"
        >
          {{ t('ai.chatTab') }}
        </button>
      </div>
    </header>

    <div v-if="activeTab === 'tools'" class="flex min-h-0 flex-1 overflow-hidden">
      <aside class="flex w-[360px] shrink-0 flex-col overflow-y-auto border-r border-gray-200 bg-white">
        <div class="space-y-5 p-4">
          <div v-if="error" class="rounded-lg bg-red-50 p-3 text-sm text-red-700">{{ error }}</div>
          <div v-if="notice" class="rounded-lg bg-green-50 p-3 text-sm text-green-700">{{ notice }}</div>

          <section>
            <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('ai.taskType') }}</label>
            <select
              v-model="taskType"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
            >
              <optgroup v-for="group in taskGroups" :key="group.name" :label="group.name">
                <option v-for="task in group.tasks" :key="task.value" :value="task.value">
                  {{ task.label }}
                </option>
              </optgroup>
            </select>
            <p class="mt-2 text-xs leading-5 text-gray-500">{{ taskDescription }}</p>
          </section>

          <section v-if="isFocusTask(taskType)" class="space-y-3 rounded-2xl border border-blue-100 bg-blue-50/60 p-3">
            <div class="flex items-center justify-between">
              <h3 class="text-sm font-semibold text-blue-950">{{ t('ai.taskControls') }}</h3>
              <span class="text-xs text-blue-700">{{ t('ai.previewOnlyHint') }}</span>
            </div>

            <template v-if="taskType === 'polish'">
              <label class="block text-xs font-semibold text-gray-600">{{ t('ai.controls.intensity') }}</label>
              <select v-model="controlsByTask[taskType].controls.polishIntensity" class="w-full rounded-lg border border-blue-100 px-3 py-2 text-sm">
                <option value="light">{{ t('ai.options.light') }}</option>
                <option value="medium">{{ t('ai.options.medium') }}</option>
                <option value="strong">{{ t('ai.options.strong') }}</option>
              </select>
              <label class="block text-xs font-semibold text-gray-600">{{ t('ai.controls.languageStyle') }}</label>
              <input v-model="controlsByTask[taskType].controls.polishStyle" class="w-full rounded-lg border border-blue-100 px-3 py-2 text-sm" />
              <label class="flex items-center gap-2 text-sm text-gray-700">
                <input v-model="controlsByTask[taskType].controls.preserveVoice" type="checkbox" />
                {{ t('ai.controls.preserveVoice') }}
              </label>
              <label class="flex items-center gap-2 text-sm text-gray-700">
                <input v-model="controlsByTask[taskType].controls.compressRedundancy" type="checkbox" />
                {{ t('ai.controls.compressRedundancy') }}
              </label>
            </template>

            <template v-if="taskType === 'rewrite'">
              <label class="block text-xs font-semibold text-gray-600">{{ t('ai.controls.rewriteDirection') }}</label>
              <input v-model="controlsByTask[taskType].controls.rewriteDirection" class="w-full rounded-lg border border-blue-100 px-3 py-2 text-sm" />
              <label class="block text-xs font-semibold text-gray-600">{{ t('ai.controls.narrativeTone') }}</label>
              <input v-model="controlsByTask[taskType].controls.narrativeTone" class="w-full rounded-lg border border-blue-100 px-3 py-2 text-sm" />
              <label class="block text-xs font-semibold text-gray-600">{{ t('ai.controls.sentenceChange') }}</label>
              <select v-model="controlsByTask[taskType].controls.sentenceChange" class="w-full rounded-lg border border-blue-100 px-3 py-2 text-sm">
                <option value="light">{{ t('ai.options.light') }}</option>
                <option value="medium">{{ t('ai.options.medium') }}</option>
                <option value="strong">{{ t('ai.options.strong') }}</option>
              </select>
              <label class="flex items-center gap-2 text-sm text-gray-700">
                <input v-model="controlsByTask[taskType].controls.keepImagery" type="checkbox" />
                {{ t('ai.controls.keepImagery') }}
              </label>
            </template>

            <template v-if="taskType === 'expand'">
              <label class="block text-xs font-semibold text-gray-600">{{ t('ai.controls.expandLength') }}</label>
              <select v-model="controlsByTask[taskType].controls.expandLength" class="w-full rounded-lg border border-blue-100 px-3 py-2 text-sm">
                <option value="short">{{ t('ai.options.short') }}</option>
                <option value="medium">{{ t('ai.options.medium') }}</option>
                <option value="long">{{ t('ai.options.long') }}</option>
              </select>
              <label class="block text-xs font-semibold text-gray-600">{{ t('ai.controls.expandFocus') }}</label>
              <input v-model="controlsByTask[taskType].controls.expandFocus" class="w-full rounded-lg border border-blue-100 px-3 py-2 text-sm" />
              <label class="block text-xs font-semibold text-gray-600">{{ t('ai.controls.detailType') }}</label>
              <input v-model="controlsByTask[taskType].controls.detailType" class="w-full rounded-lg border border-blue-100 px-3 py-2 text-sm" />
              <label class="flex items-center gap-2 text-sm text-gray-700">
                <input v-model="controlsByTask[taskType].controls.sensoryDetail" type="checkbox" />
                {{ t('ai.controls.sensoryDetail') }}
              </label>
            </template>

            <template v-if="taskType === 'continue'">
              <label class="block text-xs font-semibold text-gray-600">{{ t('ai.controls.continueLength') }}</label>
              <select v-model="controlsByTask[taskType].controls.continueLength" class="w-full rounded-lg border border-blue-100 px-3 py-2 text-sm">
                <option value="short">{{ t('ai.options.short') }}</option>
                <option value="medium">{{ t('ai.options.medium') }}</option>
                <option value="long">{{ t('ai.options.long') }}</option>
              </select>
              <label class="block text-xs font-semibold text-gray-600">{{ t('ai.controls.emotionalDirection') }}</label>
              <input v-model="controlsByTask[taskType].controls.emotionalDirection" class="w-full rounded-lg border border-blue-100 px-3 py-2 text-sm" />
              <label class="block text-xs font-semibold text-gray-600">{{ t('ai.controls.pacing') }}</label>
              <input v-model="controlsByTask[taskType].controls.pacing" class="w-full rounded-lg border border-blue-100 px-3 py-2 text-sm" />
              <label class="block text-xs font-semibold text-gray-600">{{ t('ai.controls.continuationMode') }}</label>
              <input v-model="controlsByTask[taskType].controls.continuationMode" class="w-full rounded-lg border border-blue-100 px-3 py-2 text-sm" />
            </template>

            <label class="block text-xs font-semibold text-gray-600">{{ t('ai.controls.extraInstructions') }}</label>
            <textarea
              v-model="controlsByTask[taskType].controls.extraInstructions"
              rows="3"
              class="w-full resize-none rounded-lg border border-blue-100 px-3 py-2 text-sm"
              :placeholder="t('ai.controls.extraPlaceholder')"
            />
          </section>

          <section v-if="isFocusTask(taskType)" class="rounded-2xl border border-gray-200 p-3">
            <div class="mb-2 flex items-center justify-between">
              <h3 class="text-sm font-semibold text-gray-700">{{ t('ai.myPresets') }}</h3>
              <span class="text-xs text-gray-400">{{ currentTaskPresets.length }}</span>
            </div>
            <div v-if="!taskPresetsSupported" class="mb-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-900">
              {{ t('ai.taskPresetsUnsupported') }}
            </div>
            <div class="flex gap-2">
              <input
                v-model="presetName"
                :disabled="!taskPresetsSupported"
                class="min-w-0 flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm"
                :placeholder="t('ai.presetNamePlaceholder')"
              />
              <button
                @click="saveCurrentPreset"
                :disabled="!taskPresetsSupported"
                class="rounded-lg bg-gray-900 px-3 py-2 text-xs font-semibold text-white disabled:opacity-40"
              >
                {{ t('ai.savePreset') }}
              </button>
            </div>
            <div v-if="currentTaskPresets.length" class="mt-3 space-y-2">
              <div
                v-for="preset in currentTaskPresets"
                :key="preset.id"
                class="flex items-center gap-2 rounded-xl bg-gray-50 px-3 py-2 text-sm"
              >
                <button @click="applyPreset(preset.id)" class="min-w-0 flex-1 truncate text-left font-medium text-gray-700">
                  {{ preset.name }}
                </button>
                <button
                  @click="deletePreset(preset)"
                  :disabled="!taskPresetsSupported"
                  class="text-xs text-red-500 hover:text-red-700 disabled:opacity-40"
                >
                  {{ t('common.delete') }}
                </button>
              </div>
            </div>
            <p v-else class="mt-2 text-xs text-gray-400">{{ t('ai.noPresets') }}</p>
          </section>

          <section>
            <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('ai.scope') }}</label>
            <div class="mb-2 flex gap-2">
              <button
                @click="scopeType = 'paste'; routeSelection = null"
                :class="[
                  'flex-1 rounded-lg px-3 py-2 text-sm transition-colors',
                  scopeType === 'paste' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
                ]"
              >
                {{ t('ai.scopePaste') }}
              </button>
              <button
                @click="scopeType = 'article'"
                :class="[
                  'flex-1 rounded-lg px-3 py-2 text-sm transition-colors',
                  scopeType === 'article' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
                ]"
              >
                {{ t('ai.scopeArticle') }}
              </button>
            </div>

            <textarea
              v-if="scopeType === 'paste'"
              v-model="taskInput"
              class="h-32 w-full resize-none rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
              :placeholder="t('ai.pasteText')"
            />

            <select
              v-if="scopeType === 'article'"
              v-model="selectedArticleId"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option :value="null">{{ t('ai.selectArticle') }}</option>
              <option v-for="article in articles" :key="article.id" :value="article.id">
                {{ article.title || t('articles.untitled') }}
              </option>
            </select>
            <p v-if="hasArticleSelection" class="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
              {{ t('ai.selectionScopeHint') }}
            </p>
          </section>

          <section class="rounded-2xl border border-gray-200 p-3">
            <div class="mb-3 flex items-center justify-between">
              <h3 class="text-sm font-semibold text-gray-700">{{ t('ai.context') }}</h3>
              <button
                v-if="selectedContextItems.length"
                @click="clearContextItems"
                class="text-xs text-gray-500 hover:text-gray-800"
              >
                {{ t('ai.clearContext') }}
              </button>
            </div>
            <div class="mb-3 grid grid-cols-2 gap-2">
              <button
                @click="showCardSelector = !showCardSelector"
                class="rounded-lg bg-purple-50 px-3 py-2 text-xs font-semibold text-purple-700 hover:bg-purple-100"
              >
                {{ t('ai.addAiCard') }}
              </button>
              <button
                @click="addArticleNotesContext"
                :disabled="!canAddArticleNotes"
                class="rounded-lg bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-700 hover:bg-amber-100 disabled:opacity-40"
              >
                {{ t('ai.addArticleNotes') }}
              </button>
              <button
                @click="openReferencePicker"
                class="col-span-2 rounded-lg bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700 hover:bg-emerald-100"
              >
                {{ t('ai.addReference') }}
              </button>
            </div>

            <div v-if="showCardSelector" class="mb-3 max-h-44 space-y-1 overflow-y-auto rounded-lg border border-gray-200 p-2">
              <button
                v-for="card in nonSceneCards"
                :key="card.id"
                @click="toggleCard(card.id)"
                :class="[
                  'w-full rounded p-2 text-left text-xs transition-colors',
                  selectedCardIds.includes(card.id) ? 'border border-purple-300 bg-purple-100' : 'bg-gray-50 hover:bg-gray-100',
                ]"
              >
                <div class="font-semibold">{{ card.title }}</div>
                <div class="text-gray-500">{{ cardTypeLabels[card.card_type] }}</div>
              </button>
              <div v-if="!nonSceneCards.length" class="py-4 text-center text-gray-400">
                {{ t('ai.noCards') }}
              </div>
            </div>

            <div class="mb-3 rounded-lg border border-emerald-100 bg-emerald-50/70 p-3">
              <div class="mb-2 flex items-center justify-between gap-2">
                <div class="text-xs font-semibold text-emerald-900">{{ t('ai.sceneModuleTitle') }}</div>
                <span class="text-[11px] text-emerald-700">{{ t('ai.sceneModuleHint') }}</span>
              </div>
              <div class="flex gap-2">
                <input
                  v-model="sceneSearchQuery"
                  @keydown.enter.prevent="searchSceneCards"
                  class="min-w-0 flex-1 rounded-lg border border-emerald-200 bg-white px-3 py-2 text-xs outline-none focus:ring-2 focus:ring-emerald-500"
                  :placeholder="t('ai.sceneSearchPlaceholder')"
                />
                <button
                  @click="searchSceneCards"
                  :disabled="sceneSearchLoading"
                  class="rounded-lg bg-emerald-700 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-800 disabled:opacity-50"
                >
                  {{ sceneSearchLoading ? t('common.loading') : t('ai.sceneSearch') }}
                </button>
              </div>
              <div v-if="sceneSearchError" class="mt-2 rounded bg-red-50 p-2 text-xs text-red-700">{{ sceneSearchError }}</div>
              <div v-if="sceneSearchResults.length" class="mt-2 max-h-44 space-y-1 overflow-y-auto">
                <button
                  v-for="card in sceneSearchResults"
                  :key="card.id"
                  @click="toggleCard(card.id)"
                  :class="[
                    'w-full rounded p-2 text-left text-xs transition-colors',
                    selectedCardIds.includes(card.id) ? 'border border-emerald-300 bg-emerald-100' : 'bg-white hover:bg-emerald-50',
                  ]"
                >
                  <div class="font-semibold text-emerald-950">{{ card.title }}</div>
                  <div class="line-clamp-2 text-emerald-700">{{ card.content }}</div>
                </button>
              </div>
              <div v-else-if="sceneSearchQuery.trim() && !sceneSearchLoading" class="mt-2 text-xs text-emerald-700">
                {{ t('ai.sceneNoResults') }}
              </div>
            </div>

            <div v-if="selectedContextItems.length" class="space-y-2">
              <article
                v-for="item in selectedContextItems"
                :key="item.uid"
                class="rounded-xl border border-gray-100 bg-gray-50 p-3 text-xs"
              >
                <div class="flex items-start justify-between gap-2">
                  <div class="min-w-0">
                    <div class="font-semibold text-gray-800">{{ item.title }}</div>
                    <div class="mt-1 text-gray-500">{{ contextKindLabel(item.kind) }} · {{ item.subtitle }} · {{ item.body.length }} {{ t('ai.chars') }}</div>
                  </div>
                  <button @click="removeContextItem(item)" class="text-gray-400 hover:text-gray-700">×</button>
                </div>
              </article>
            </div>
            <p v-else class="text-xs leading-5 text-gray-400">{{ t('ai.noContext') }}</p>
          </section>

          <button
            @click="handleRunTask"
            :disabled="store.taskRunning"
            class="w-full rounded-lg bg-blue-600 px-4 py-3 font-semibold text-white transition-colors hover:bg-blue-700 disabled:bg-gray-400"
          >
            {{ store.taskRunning ? t('ai.running') : t('ai.runTask') }}
          </button>
          <div class="grid grid-cols-3 gap-2">
            <button
              @click="clearCurrentResult"
              :disabled="!taskResult.trim() && !showComparison"
              class="rounded-lg bg-gray-100 px-2 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-200 disabled:opacity-40"
            >
              {{ t('ai.clearCurrentResult') }}
            </button>
            <button
              @click="clearCurrentTaskState"
              class="rounded-lg bg-gray-100 px-2 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-200"
            >
              {{ t('ai.clearCurrentTask') }}
            </button>
            <button
              @click="clearAllWorkspaceState"
              class="rounded-lg bg-red-50 px-2 py-2 text-xs font-semibold text-red-600 hover:bg-red-100"
            >
              {{ t('ai.clearAllWorkspace') }}
            </button>
          </div>
        </div>
      </aside>

      <main v-if="!showComparison" class="flex flex-1 items-center justify-center text-gray-400">
        <div class="text-center">
          <p class="mb-2 text-lg">{{ t('ai.selectOrCreate') }}</p>
          <p class="text-sm">{{ t('ai.comparisonHint') }}</p>
        </div>
      </main>

      <main v-else class="flex min-w-0 flex-1 flex-col">
        <div class="flex items-center justify-between border-b border-gray-200 bg-white p-4">
          <div>
            <h2 class="text-lg font-bold">{{ t('ai.comparison') }}</h2>
            <p class="text-xs text-gray-500">{{ t('ai.previewOnlyHint') }}</p>
          </div>
          <div class="flex flex-wrap justify-end gap-2">
            <button @click="copyResult" class="rounded-lg bg-green-600 px-4 py-2 text-sm text-white transition-colors hover:bg-green-700">
              {{ t('ai.copyResult') }}
            </button>
            <button
              v-if="scopeType === 'article' && selectedArticleId"
              @click="applyResultToArticle('replace')"
              :disabled="!taskResult.trim()"
              class="rounded-lg bg-orange-600 px-4 py-2 text-sm text-white transition-colors hover:bg-orange-700 disabled:opacity-40"
            >
              {{ hasArticleSelection ? t('ai.replaceSelection') : t('ai.replaceOriginal') }}
            </button>
            <button
              v-if="scopeType === 'article' && selectedArticleId"
              @click="applyResultToArticle('insert_after')"
              :disabled="!taskResult.trim()"
              class="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white transition-colors hover:bg-blue-700 disabled:opacity-40"
            >
              {{ hasArticleSelection ? t('ai.insertAfterSelection') : t('ai.insertAtEnd') }}
            </button>
            <button @click="showComparison = false" class="rounded-lg bg-gray-600 px-4 py-2 text-sm text-white transition-colors hover:bg-gray-700">
              {{ t('ai.back') }}
            </button>
          </div>
        </div>

        <div class="flex flex-1 overflow-hidden">
          <section class="flex min-w-0 flex-1 flex-col border-r border-gray-200">
            <div class="border-b border-gray-200 bg-gray-100 p-3 text-sm font-semibold">{{ t('ai.original') }}</div>
            <div class="flex-1 overflow-y-auto p-6">
              <pre class="whitespace-pre-wrap font-sans leading-relaxed text-gray-700">{{ originalText }}</pre>
            </div>
          </section>

          <section class="flex min-w-0 flex-1 flex-col">
            <div class="border-b border-gray-200 bg-blue-100 p-3 text-sm font-semibold">{{ t('ai.result') }}</div>
            <div class="flex-1 overflow-y-auto bg-blue-50 p-6">
              <pre class="whitespace-pre-wrap font-sans leading-relaxed text-gray-900">{{ taskResult }}</pre>
            </div>
          </section>
        </div>
      </main>
    </div>

    <div v-else class="flex min-h-0 flex-1 overflow-hidden">
      <aside class="w-80 shrink-0 overflow-y-auto border-r border-gray-200 bg-white p-4">
        <div v-if="error" class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{{ error }}</div>
        <div v-if="chatNotice" class="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-700">{{ chatNotice }}</div>

        <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('ai.chatArticle') }}</label>
        <select
          v-model="chatScopeId"
          class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option :value="null">{{ t('ai.selectArticle') }}</option>
          <option v-for="article in articles" :key="article.id" :value="article.id">
            {{ article.title || t('articles.untitled') }}
          </option>
        </select>

        <div class="mt-5 rounded-2xl bg-blue-50 p-4 text-sm text-blue-900">
          <div class="font-semibold">{{ t('ai.currentChatScope') }}</div>
          <p class="mt-1">{{ chatScopeLabel }}</p>
          <p v-if="selectedChatArticle" class="mt-2 text-xs text-blue-700">
            {{ selectedChatArticleChars }} {{ t('ai.chars') }} · {{ selectedChatArticleParagraphs }} {{ t('ai.paragraphs') }}
          </p>
          <p class="mt-2 text-xs leading-5 text-blue-700">{{ t('ai.chatArticleContextHint') }}</p>
          <button
            v-if="selectedChatArticle"
            @click="openChatArticle"
            class="mt-3 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700"
          >
            {{ t('ai.backToArticle') }}
          </button>
        </div>

        <section class="mt-5 rounded-2xl border border-gray-200 p-4">
          <div class="mb-2 flex items-center justify-between">
            <label class="text-sm font-semibold text-gray-700">{{ t('ai.chatSystemPrompt') }}</label>
            <span class="text-xs text-gray-400">{{ chatSystemPromptDraft.length }}/{{ CHAT_SYSTEM_PROMPT_LIMIT }}</span>
          </div>
          <div v-if="!chatSettingsSupported" class="mb-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-900">
            {{ t('ai.chatSettingsUnsupported') }}
          </div>
          <textarea
            v-model="chatSystemPromptDraft"
            :maxlength="CHAT_SYSTEM_PROMPT_LIMIT"
            :disabled="!chatSettingsSupported"
            rows="7"
            class="w-full resize-none rounded-xl border border-gray-300 px-3 py-2 text-sm leading-6 outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-400"
            :placeholder="t('ai.chatSystemPromptPlaceholder')"
          />
          <p class="mt-2 text-xs leading-5 text-gray-500">{{ t('ai.chatSystemPromptHint') }}</p>
          <button
            @click="saveChatSettings"
            :disabled="!chatSettingsSupported || savingChatSettings || chatSystemPromptDraft === chatSystemPrompt"
            class="mt-3 w-full rounded-lg bg-gray-900 px-3 py-2 text-sm font-semibold text-white hover:bg-gray-700 disabled:opacity-40"
          >
            {{ savingChatSettings ? t('common.saving') : t('ai.saveChatPrompt') }}
          </button>
        </section>
      </aside>

      <main class="flex min-w-0 flex-1 flex-col bg-[#fbfaf7]">
        <div class="border-b border-gray-200 bg-white px-6 py-4">
          <h2 class="text-lg font-bold">{{ t('ai.chatTitle') }}</h2>
          <p class="text-sm text-gray-500">{{ selectedChatArticle ? chatScopeLabel : t('ai.chatSelectArticleFirst') }}</p>
        </div>

        <div class="flex-1 overflow-y-auto p-6">
          <div v-if="!selectedChatArticle" class="mt-20 text-center text-gray-400">
            {{ t('ai.chatSelectArticleFirst') }}
          </div>
          <div v-else-if="store.loading && !store.messages.length" class="mt-20 text-center text-gray-400">
            {{ t('common.loading') }}
          </div>
          <div v-else-if="!store.messages.length" class="mt-20 text-center text-gray-400">
            {{ t('ai.chatEmpty') }}
          </div>
          <div v-else class="mx-auto max-w-3xl space-y-4">
            <article
              v-for="(message, index) in store.messages"
              :key="message.id ?? `${message.role}-${index}`"
              :class="[
                'rounded-3xl px-5 py-4 shadow-sm',
                message.role === 'user'
                  ? 'ml-12 bg-stone-900 text-white'
                  : 'mr-12 bg-white text-stone-800'
              ]"
            >
              <div class="mb-2 text-xs opacity-60">
                {{ message.role === 'user' ? t('ai.chatYou') : t('ai.chatAssistant') }}
              </div>
              <p class="whitespace-pre-wrap leading-7">{{ message.content }}</p>
              <div v-if="message.role === 'assistant'" class="mt-4 flex flex-wrap gap-2">
                <button
                  @click="copyChatMessage(message)"
                  class="rounded-lg bg-stone-100 px-3 py-1.5 text-xs font-semibold text-stone-700 hover:bg-stone-200"
                >
                  {{ t('ai.copyReply') }}
                </button>
                <button
                  v-if="canSaveAssistantReply(message)"
                  @click="saveAssistantReplyAsNote(message)"
                  class="rounded-lg bg-amber-100 px-3 py-1.5 text-xs font-semibold text-amber-800 hover:bg-amber-200"
                >
                  {{ t('ai.saveReplyAsNote') }}
                </button>
              </div>
            </article>
          </div>
        </div>

        <div class="border-t border-gray-200 bg-white p-4">
          <div class="mx-auto flex max-w-3xl gap-3">
            <textarea
              v-model="chatInput"
              rows="3"
              class="flex-1 resize-none rounded-2xl border border-gray-300 px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
              :placeholder="t('ai.chatPlaceholder')"
              @keydown.ctrl.enter.prevent="sendChat"
              @keydown.meta.enter.prevent="sendChat"
            />
            <button
              @click="sendChat"
              :disabled="store.loading || !chatInput.trim() || !selectedChatArticle"
              class="self-end rounded-2xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-40"
            >
              {{ store.loading ? t('ai.running') : t('ai.chatSend') }}
            </button>
          </div>
        </div>
      </main>
    </div>

    <div v-if="referencePickerOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div class="flex max-h-[80vh] w-[680px] flex-col rounded-3xl bg-white shadow-2xl">
        <div class="border-b border-gray-200 p-6">
          <h3 class="text-xl font-bold">{{ t('ai.pickReferences') }}</h3>
          <p class="mt-1 text-sm text-gray-500">{{ t('ai.pickReferencesHint') }}</p>
          <div class="mt-4 flex gap-2">
            <input
              v-model="referenceSearch"
              class="min-w-0 flex-1 rounded-xl border border-gray-300 px-4 py-2 text-sm"
              :placeholder="t('library.search')"
              @keydown.enter.prevent="searchReferences"
            />
            <button @click="searchReferences" class="rounded-xl bg-gray-900 px-4 py-2 text-sm font-semibold text-white">
              {{ t('common.search') }}
            </button>
          </div>
        </div>
        <div class="flex-1 overflow-y-auto p-4">
          <div v-if="referenceLoading" class="p-8 text-center text-gray-400">{{ t('common.loading') }}</div>
          <div v-else-if="!referenceResults.length" class="p-8 text-center text-gray-400">{{ t('library.noReferences') }}</div>
          <template v-else>
            <button
              v-for="reference in referenceResults"
              :key="reference.id"
              @click="toggleReference(reference.id)"
              :class="[
                'mb-2 w-full rounded-2xl border p-4 text-left transition-all',
                selectedReferenceIds.includes(reference.id)
                  ? 'border-emerald-400 bg-emerald-50'
                  : 'border-gray-200 hover:border-gray-300'
              ]"
            >
              <div class="flex gap-3">
                <input type="checkbox" class="mt-1" :checked="selectedReferenceIds.includes(reference.id)" readonly />
                <div class="min-w-0 flex-1">
                  <div class="font-semibold">
                    {{ reference.source_title ? `《${reference.source_title}》` : t('library.empty') }}
                    <span class="text-sm font-normal text-gray-500">{{ reference.source_author }}</span>
                  </div>
                  <p class="mt-2 line-clamp-3 whitespace-pre-wrap text-sm leading-6 text-gray-600">{{ reference.content }}</p>
                  <div class="mt-2 text-xs text-gray-400">{{ reference.usage_kind || t('library.other') }}</div>
                </div>
              </div>
            </button>
          </template>
        </div>
        <div class="flex justify-end gap-3 border-t border-gray-200 p-5">
          <button @click="referencePickerOpen = false" class="rounded-xl bg-gray-100 px-4 py-2 text-sm">
            {{ t('common.cancel') }}
          </button>
          <button
            @click="addSelectedReferences"
            :disabled="!selectedReferenceIds.length"
            class="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
          >
            {{ t('ai.addSelectedContext', { count: selectedReferenceIds.length }) }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
