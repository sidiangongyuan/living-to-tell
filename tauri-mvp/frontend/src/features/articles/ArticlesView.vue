<script setup lang="ts">
import { nextTick, ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useArticlesStore } from './store'
import { useSettingsStore } from '../../stores/settings'
import { collectionsApi, type Collection } from '../../api/collections'
import { articlesApi, type ArticleExportFormat } from '../../api/articles'
import { notesApi, type WritingNote } from '../../api/notes'
import FindReplace from '../../components/FindReplace.vue'
import { useI18n } from '../../i18n'
import { saveBlobWithDialog } from '../../utils/exportFile'
import { collectArticleTags, countParagraphs, filterArticlesByTag } from './articleList'
import { composeArticleBody, detectEpigraph, type EpigraphParts } from './epigraph'
import {
  type ArticleEditorInteraction,
  COMFORT_ANCHOR_RATIO,
  editorTailSpace,
  getLastSelectedArticleId,
  getArticleEditorPosition,
  insertIndentedParagraph,
  saveLastSelectedArticleId,
  saveArticleEditorPosition,
  shouldRecenterCaret,
} from './editorPosition'

const store = useArticlesStore()
const settings = useSettingsStore()
const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const saveTimer = ref<number | null>(null)
const searchInput = ref('')
const selectedTag = ref('')
const showFindReplace = ref(false)
const bodyRef = ref<HTMLTextAreaElement | null>(null)
const editorScrollRef = ref<HTMLDivElement | null>(null)
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
const draftArticleId = ref<string | null>(null)
const epigraphActive = ref(false)
const epigraphQuote = ref('')
const epigraphAttribution = ref('')
const epigraphEditingArticleId = ref<string | null>(null)
const syncingDraft = ref(false)
const exportingFormat = ref<ArticleExportFormat | null>(null)
const exportMessage = ref('')
const exportError = ref('')
const writingNotes = ref<WritingNote[]>([])
const newNoteBody = ref('')
const editingNoteId = ref<string | null>(null)
const editingNoteBody = ref('')
const notesError = ref('')
const notesLoading = ref(false)
const showDoneNotes = ref(false)
const positionSaveTimer = ref<number | null>(null)
const pendingPositionArticleId = ref<string | null>(null)
const pendingPositionInteraction = ref<ArticleEditorInteraction>('edit')
const restoringEditorPosition = ref(false)
const tailSpace = ref(260)
const suppressReadPositionUntil = ref(0)
const lastProgrammaticScrollTop = ref<number | null>(null)
const userScrollIntentUntil = ref(0)
const lastEditorInteraction = ref<ArticleEditorInteraction | null>(null)
const hasSavedEditInteraction = ref(false)
let restoreToken = 0

interface ArticleSaveSnapshot {
  id: string
  title: string
  body: string
  tags: string[]
}

interface EpigraphDraftState {
  active: boolean
  quote: string
  attribution: string
  updatedAt: number
}

const pendingArticleSave = ref<ArticleSaveSnapshot | null>(null)

const EPIGRAPH_DRAFTS_KEY = 'article_epigraph_drafts'
const POSITION_DEBUG_LOG_KEY = 'article_editor_position_debug'
const POSITION_DEBUG_FLAG_KEY = 'article_editor_position_debug_enabled'
const POSITION_DEBUG_LIMIT = 180

type PositionDebugEvent =
  | 'save-edit'
  | 'save-read'
  | 'restore-edit'
  | 'restore-read'
  | 'restore-retry'
  | 'restore-missing'
  | 'skip-programmatic-read'
  | 'route-change'

function positionDebugEnabled(): boolean {
  return import.meta.env.DEV || localStorage.getItem(POSITION_DEBUG_FLAG_KEY) === '1'
}

function logPositionEvent(event: PositionDebugEvent, payload: Record<string, unknown> = {}) {
  if (!positionDebugEnabled()) return
  const entry = {
    event,
    at: new Date().toISOString(),
    ...payload,
  }
  console.debug('[article-position]', entry)
  try {
    const parsed = JSON.parse(localStorage.getItem(POSITION_DEBUG_LOG_KEY) || '[]')
    const log = Array.isArray(parsed) ? parsed : []
    log.push(entry)
    localStorage.setItem(POSITION_DEBUG_LOG_KEY, JSON.stringify(log.slice(-POSITION_DEBUG_LIMIT)))
  } catch {
    localStorage.setItem(POSITION_DEBUG_LOG_KEY, JSON.stringify([entry]))
  }
}

const currentBodyText = computed(() => composeCurrentBody())
const wordCount = computed(() => countWords(currentBodyText.value))
const charCount = computed(() => currentBodyText.value.length)
const paragraphCount = computed(() => countParagraphs(currentBodyText.value))
const openWritingNotes = computed(() => writingNotes.value.filter((note) => note.status === 'open'))
const doneWritingNotes = computed(() => writingNotes.value.filter((note) => note.status === 'done'))
const hasSearchQuery = computed(() => Boolean(searchInput.value.trim()))
const allTags = computed(() => collectArticleTags(store.entries))
const activeBaseList = computed(() => hasSearchQuery.value ? store.searchResults : store.entries)
const displayList = computed(() => filterArticlesByTag(activeBaseList.value, selectedTag.value))
const listStatusLabel = computed(() =>
  hasSearchQuery.value || selectedTag.value ? t('articles.results') : t('articles.total')
)
const emptyListLabel = computed(() =>
  hasSearchQuery.value || selectedTag.value ? t('articles.noResults') : t('articles.noArticles')
)

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
  const snapshot = applyDraftToSelected()
  if (!snapshot) return
  pendingArticleSave.value = snapshot
  if (saveTimer.value) clearTimeout(saveTimer.value)
  saveTimer.value = window.setTimeout(() => {
    void flushPendingArticleSave()
  }, 600)
}

function handleBodyInput() {
  lastEditorInteraction.value = 'edit'
  hasSavedEditInteraction.value = true
  resizeBodyEditor()
  saveCurrentEditorEditPositionNow()
  scheduleSave()
  void nextTick(() => {
    resizeBodyEditor()
    keepCaretNearComfortLine()
    saveCurrentEditorEditPositionNow()
  })
}

function handleBodyPointerSettled() {
  if (restoringEditorPosition.value) return
  lastEditorInteraction.value = 'edit'
  hasSavedEditInteraction.value = true
  saveCurrentEditorEditPositionNow()
}

function handleBodyFocusOut() {
  if (restoringEditorPosition.value) return
  lastEditorInteraction.value = lastEditorInteraction.value ?? 'edit'
  saveCurrentEditorPositionNow()
}

function handleBeforeUnload() {
  saveCurrentEditorPositionNow()
  void flushPendingArticleSave()
}

async function saveNow(): Promise<boolean> {
  const snapshot = applyDraftToSelected()
  if (snapshot) {
    pendingArticleSave.value = snapshot
  }
  return flushPendingArticleSave()
}

async function flushPendingArticleSave(): Promise<boolean> {
  if (saveTimer.value) {
    clearTimeout(saveTimer.value)
    saveTimer.value = null
  }
  const snapshot = pendingArticleSave.value
  if (!snapshot) return true
  pendingArticleSave.value = null
  try {
    await store.updateEntry(snapshot.id, snapshot.title, snapshot.body, snapshot.tags)
    return true
  } catch (e) {
    console.error('Save failed:', e)
    pendingArticleSave.value = snapshot
    return false
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

async function createEntryFromSidebar() {
  try {
    await store.createEntry(t('articles.untitled'))
  } catch {
    // The store owns the visible error state; keep the click handler settled.
  }
}

function selectTag(tag: string) {
  selectedTag.value = selectedTag.value === tag ? '' : tag
}

function clearTagFilter() {
  selectedTag.value = ''
}

async function selectEntryFromList(entryId: string) {
  flushPendingEditorPosition()
  saveLastKnownEditorPosition()
  const saved = await flushPendingArticleSave()
  if (!saved) return
  saveLastSelectedArticleId(entryId)
  if (route.query.id === entryId) {
    store.selectEntry(entryId)
    void restoreEditorPositionIfNeeded(entryId)
    return
  }
  router.push({ name: 'articles', query: { id: entryId } })
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

function handleBodyKeydown(e: KeyboardEvent) {
  if (e.key !== 'Enter' || e.shiftKey || e.ctrlKey || e.metaKey || e.altKey || e.isComposing || !bodyRef.value) {
    return
  }
  lastEditorInteraction.value = 'edit'
  hasSavedEditInteraction.value = true
  e.preventDefault()
  const edit = insertIndentedParagraph(
    bodyDraft.value,
    bodyRef.value.selectionStart,
    bodyRef.value.selectionEnd
  )
  bodyDraft.value = edit.text
  void nextTick(() => {
    bodyRef.value?.setSelectionRange(edit.selectionStart, edit.selectionEnd)
    keepCaretNearComfortLine()
    saveCurrentEditorPosition()
  })
  scheduleSave()
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
  scrollEditorTo(scrollTopForCaretPosition(bodyRef.value, start, 0.5))
}

function syncFindQuery(query: string, caseSensitive: boolean) {
  findQuery.value = query
  findCaseSensitive.value = caseSensitive
  refreshMatches(query, caseSensitive)
}

function readEpigraphDrafts(): Record<string, EpigraphDraftState> {
  try {
    const parsed = JSON.parse(localStorage.getItem(EPIGRAPH_DRAFTS_KEY) || '{}')
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
  } catch {
    return {}
  }
}

function getEpigraphDraft(articleId: string): EpigraphDraftState | null {
  const draft = readEpigraphDrafts()[articleId]
  return draft?.active ? draft : null
}

function saveEpigraphDraft(articleId: string, draft: Omit<EpigraphDraftState, 'updatedAt'>) {
  const drafts = readEpigraphDrafts()
  drafts[articleId] = {
    ...draft,
    updatedAt: Date.now(),
  }
  localStorage.setItem(EPIGRAPH_DRAFTS_KEY, JSON.stringify(drafts))
}

function clearEpigraphDraft(articleId: string | null | undefined) {
  if (!articleId) return
  const drafts = readEpigraphDrafts()
  if (!(articleId in drafts)) return
  delete drafts[articleId]
  localStorage.setItem(EPIGRAPH_DRAFTS_KEY, JSON.stringify(drafts))
}

function syncEpigraphDraftForSelected() {
  const articleId = store.selectedEntry?.id
  if (!articleId) return
  if (!epigraphActive.value) {
    clearEpigraphDraft(articleId)
    return
  }
  const complete = Boolean(epigraphQuote.value.trim() && epigraphAttribution.value.trim())
  if (complete) {
    clearEpigraphDraft(articleId)
    return
  }
  saveEpigraphDraft(articleId, {
    active: true,
    quote: epigraphQuote.value,
    attribution: epigraphAttribution.value,
  })
}

function composeCurrentBody(includeIncompleteEpigraph = false): string {
  if (!epigraphActive.value) {
    return bodyDraft.value
  }
  if (!epigraphQuote.value.trim() || !epigraphAttribution.value.trim()) {
    if (!includeIncompleteEpigraph) {
      return bodyDraft.value
    }
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
  const entry = store.selectedEntry
  const body = entry?.body ?? ''
  if (entry && draftArticleId.value === entry.id && epigraphActive.value && epigraphEditingArticleId.value === entry.id) {
    refreshMatches()
    void nextTick(() => {
      resizeBodyEditor()
      syncingDraft.value = false
    })
    return
  }
  draftArticleId.value = entry?.id ?? null
  epigraphEditingArticleId.value = null
  const epigraph = detectEpigraph(body)
  if (epigraph) {
    epigraphActive.value = true
    clearEpigraphDraft(entry?.id)
    epigraphQuote.value = epigraph.quote
    epigraphAttribution.value = epigraph.attribution
    bodyDraft.value = epigraph.body
  } else if (entry) {
    const draft = getEpigraphDraft(entry.id)
    if (draft) {
      epigraphActive.value = true
      epigraphEditingArticleId.value = entry.id
      epigraphQuote.value = draft.quote
      epigraphAttribution.value = draft.attribution
      bodyDraft.value = body
    } else {
      epigraphActive.value = false
      epigraphQuote.value = ''
      epigraphAttribution.value = ''
      bodyDraft.value = body
    }
  } else {
    epigraphActive.value = false
    epigraphQuote.value = ''
    epigraphAttribution.value = ''
    bodyDraft.value = body
  }
  refreshMatches()
  void nextTick(() => {
    resizeBodyEditor()
    syncingDraft.value = false
  })
}

function applyDraftToSelected(): ArticleSaveSnapshot | null {
  const entry = store.selectedEntry
  if (!entry) return null

  draftArticleId.value = entry.id
  syncEpigraphDraftForSelected()
  entry.body = composeCurrentBody()
  return {
    id: entry.id,
    title: entry.title,
    body: entry.body,
    tags: [...entry.tags],
  }
}

function enableEpigraph() {
  if (epigraphActive.value) return
  epigraphActive.value = true
  epigraphEditingArticleId.value = store.selectedEntry?.id ?? null
  epigraphQuote.value = ''
  epigraphAttribution.value = ''
  syncEpigraphDraftForSelected()
}

function handleEpigraphInput() {
  epigraphEditingArticleId.value = store.selectedEntry?.id ?? null
  syncEpigraphDraftForSelected()
  scheduleSave()
}

function moveEpigraphBackToBody() {
  if (!epigraphActive.value) return
  bodyDraft.value = composeCurrentBody(true)
  epigraphActive.value = false
  epigraphEditingArticleId.value = null
  epigraphQuote.value = ''
  epigraphAttribution.value = ''
  clearEpigraphDraft(store.selectedEntry?.id)
  scheduleSave()
}

function safeFilename(title: string, format: ArticleExportFormat): string {
  const safeTitle = (title || t('articles.untitled')).replace(/[<>:"/\\|?*]/g, '').trim() || 'article'
  return `${safeTitle}.${format}`
}

async function exportArticle(format: ArticleExportFormat) {
  if (!store.selectedEntry) return
  exportingFormat.value = format
  exportMessage.value = ''
  exportError.value = ''
  try {
    const saved = await saveNow()
    if (!saved) return
    const selected = store.selectedEntry
    if (!selected) return
    const blob = await articlesApi.exportArticle(selected.id, format)
    const result = await saveBlobWithDialog(blob, safeFilename(selected.title, format), format)
    if (result.status === 'cancelled') {
      exportMessage.value = t('articles.exportCancelled')
    } else {
      exportMessage.value = t('articles.exportSaved')
    }
  } catch (e) {
    exportError.value = t('articles.exportFailed', {
      message: e instanceof Error ? e.message : String(e),
    })
  } finally {
    exportingFormat.value = null
  }
}

async function openAiChatForArticle() {
  if (!store.selectedEntry) return
  const saved = await saveNow()
  if (!saved) return
  const entryId = store.selectedEntry.id
  router.push({
    name: 'ai',
    query: {
      tab: 'chat',
      scope_kind: 'article',
      scope_id: entryId,
    },
  })
}

async function openAiToolsForArticle() {
  if (!store.selectedEntry) return
  const saved = await saveNow()
  if (!saved) return
  const entryId = store.selectedEntry.id
  const start = bodyRef.value?.selectionStart ?? 0
  const end = bodyRef.value?.selectionEnd ?? 0
  const hasSelection = end > start
  router.push({
    name: 'ai',
    query: {
      tab: 'tools',
      task: 'polish',
      scope_kind: 'article',
      scope_id: entryId,
      ...(hasSelection
        ? {
            selection_start: String(start),
            selection_end: String(end),
          }
        : {}),
    },
  })
}

async function archiveSelectedEntry() {
  if (!store.selectedEntry) return
  const entryId = store.selectedEntry.id
  const saved = await saveNow()
  if (!saved) return
  await store.archiveEntry(entryId)
}

async function deleteSelectedEntry() {
  if (!store.selectedEntry) return
  if (!confirm(t('articles.deleteConfirm', { title: store.selectedEntry.title || t('articles.untitled') }))) return
  const entryId = store.selectedEntry.id
  if (saveTimer.value) {
    clearTimeout(saveTimer.value)
    saveTimer.value = null
  }
  if (pendingArticleSave.value?.id === entryId) {
    pendingArticleSave.value = null
  }
  try {
    await store.deleteEntry(entryId)
  } catch {
    // The store owns the visible error state; keep the click handler settled.
  }
}

async function applyRouteFocusRange() {
  if (typeof route.query.id === 'string' && store.selectedEntry?.id && route.query.id !== store.selectedEntry.id) {
    return false
  }
  const start = parseNumberQuery(route.query.focus_start)
  const end = parseNumberQuery(route.query.focus_end)
  if (start === null || end === null || !bodyRef.value) return false
  await nextTick()
  const safeStart = Math.max(0, Math.min(start, bodyDraft.value.length))
  const safeEnd = Math.max(safeStart, Math.min(end, bodyDraft.value.length))
  resizeBodyEditor()
  bodyRef.value.focus()
  bodyRef.value.setSelectionRange(safeStart, safeEnd)
  scrollEditorTo(scrollTopForCaretPosition(bodyRef.value, safeStart, 0.5))
  lastEditorInteraction.value = 'edit'
  saveEditorPositionForArticle(store.selectedEntry?.id, 'edit')
  return true
}

function parseNumberQuery(value: unknown): number | null {
  if (typeof value !== 'string') return null
  const parsed = Number.parseInt(value, 10)
  return Number.isFinite(parsed) ? parsed : null
}

async function applyRouteArticle() {
  const articleId = typeof route.query.id === 'string'
    ? route.query.id
    : getLastSelectedArticleId()
  if (!articleId) return
  if (store.selectedEntry?.id !== articleId) {
    resetEditorInteractionTracking()
  }
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
  saveLastSelectedArticleId(articleId)
}

function saveCurrentEditorPosition() {
  const articleId = store.selectedEntry?.id
  saveEditorPositionForArticle(articleId)
}

function saveLastKnownEditorPosition() {
  const articleId = store.selectedEntry?.id
  saveLastKnownEditorPositionForArticle(articleId)
}

function saveLastKnownEditorPositionForArticle(articleId: string | null | undefined) {
  if (!articleId) return
  if (bodyRef.value && hasSavedEditInteraction.value) {
    saveEditorPositionForArticle(articleId, 'edit')
    if (lastEditorInteraction.value === 'read') {
      saveEditorPositionForArticle(articleId, 'read')
    }
    return
  }
  if (lastEditorInteraction.value === 'read') {
    saveEditorPositionForArticle(articleId, 'read')
  }
}

function currentTextareaPosition() {
  if (!bodyRef.value) return null
  return {
    selectionStart: bodyRef.value.selectionStart,
    selectionEnd: bodyRef.value.selectionEnd,
    scrollTop: editorScrollRef.value?.scrollTop ?? 0,
  }
}

function saveEditorPositionForArticle(
  articleId: string | null | undefined,
  interaction: ArticleEditorInteraction = 'edit'
) {
  if (!articleId || !bodyRef.value) return
  const position = currentTextareaPosition()
  if (!position) return
  saveArticleEditorPosition(articleId, position, interaction)
  lastEditorInteraction.value = interaction
  if (interaction === 'edit') {
    hasSavedEditInteraction.value = true
  }
  logPositionEvent(interaction === 'read' ? 'save-read' : 'save-edit', {
    articleId,
    ...position,
  })
}

function scheduleEditorPositionSave(
  articleId = store.selectedEntry?.id,
  interaction: ArticleEditorInteraction = 'edit'
) {
  if (!articleId) return
  if (positionSaveTimer.value) clearTimeout(positionSaveTimer.value)
  pendingPositionArticleId.value = articleId
  pendingPositionInteraction.value = interaction
  positionSaveTimer.value = window.setTimeout(() => {
    saveEditorPositionForArticle(articleId, interaction)
    positionSaveTimer.value = null
    pendingPositionArticleId.value = null
    pendingPositionInteraction.value = 'edit'
  }, 120)
}

function scheduleCurrentEditorPositionSave() {
  if (restoringEditorPosition.value) return
  lastEditorInteraction.value = 'edit'
  hasSavedEditInteraction.value = true
  saveCurrentEditorEditPositionNow()
}

function scheduleReadPositionSave() {
  const now = Date.now()
  const hasUserScrollIntent = now < userScrollIntentUntil.value
  const currentScrollTop = editorScrollRef.value?.scrollTop ?? 0
  const isStillProgrammaticScroll =
    lastProgrammaticScrollTop.value !== null &&
    Math.abs(currentScrollTop - lastProgrammaticScrollTop.value) <= 4
  if (!hasUserScrollIntent && now < suppressReadPositionUntil.value && isStillProgrammaticScroll) {
    logPositionEvent('skip-programmatic-read', {
      articleId: store.selectedEntry?.id ?? null,
      suppressUntil: suppressReadPositionUntil.value,
      scrollTop: currentScrollTop,
      programmaticScrollTop: lastProgrammaticScrollTop.value,
    })
    return
  }
  lastEditorInteraction.value = 'read'
  scheduleEditorPositionSave(store.selectedEntry?.id, 'read')
}

function markUserScrollIntent() {
  userScrollIntentUntil.value = Date.now() + 1000
}

function saveCurrentEditorPositionNow() {
  flushPendingEditorPosition()
  saveLastKnownEditorPosition()
}

function saveCurrentEditorEditPositionNow() {
  flushPendingEditorPosition()
  const articleId = store.selectedEntry?.id
  saveEditorPositionForArticle(articleId, 'edit')
}

function resetEditorInteractionTracking() {
  lastEditorInteraction.value = null
  hasSavedEditInteraction.value = false
}

function flushPendingEditorPosition() {
  if (!positionSaveTimer.value) return
  clearTimeout(positionSaveTimer.value)
  const articleId = pendingPositionArticleId.value
  const interaction = pendingPositionInteraction.value
  positionSaveTimer.value = null
  pendingPositionArticleId.value = null
  pendingPositionInteraction.value = 'edit'
  saveEditorPositionForArticle(articleId, interaction)
}

function waitForAnimationFrame(): Promise<void> {
  return new Promise((resolve) => {
    window.requestAnimationFrame(() => resolve())
  })
}

async function waitForBodyEditor(): Promise<HTMLTextAreaElement | null> {
  await nextTick()
  resizeBodyEditor()
  if (bodyRef.value) return bodyRef.value
  await waitForAnimationFrame()
  resizeBodyEditor()
  return bodyRef.value
}

async function restoreSavedEditorPosition(articleId = store.selectedEntry?.id) {
  if (!articleId) return
  const token = ++restoreToken
  const position = getArticleEditorPosition(articleId)
  if (!position) {
    logPositionEvent('restore-missing', { articleId, token })
    const textarea = await waitForBodyEditor()
    if (store.selectedEntry?.id === articleId) {
      textarea?.focus()
    }
    return
  }
  restoringEditorPosition.value = true
  const textarea = await waitForBodyEditor()
  if (!textarea || store.selectedEntry?.id !== articleId) {
    restoringEditorPosition.value = false
    return
  }
  const textLength = bodyDraft.value.length
  const safeStart = Math.max(0, Math.min(position.selectionStart, textLength))
  const safeEnd = Math.max(safeStart, Math.min(position.selectionEnd, textLength))
  resizeBodyEditor()
  updateTailSpace()
  await nextTick()
  await waitForAnimationFrame()
  resizeBodyEditor()

  const applyRestore = (phase: 'initial' | 'retry-80' | 'retry-250') => {
    const current = bodyRef.value
    const scrollContainer = editorScrollRef.value
    if (!current || !scrollContainer || store.selectedEntry?.id !== articleId || token !== restoreToken) return false
    const restoreAsReadPosition = position.interaction === 'read'
    resizeBodyEditor()
    const maxScrollTop = Math.max(0, scrollContainer.scrollHeight - scrollContainer.clientHeight)
    if (!restoreAsReadPosition) {
      current.focus({ preventScroll: true })
      current.setSelectionRange(safeStart, safeEnd)
      resizeBodyEditor()
    }
    const nextScrollTop = restoreAsReadPosition
      ? Math.max(0, position.scrollTop)
      : scrollTopForCaretPosition(current, safeEnd, COMFORT_ANCHOR_RATIO)
    const clampedScrollTop = Math.min(maxScrollTop, nextScrollTop)

    suppressReadPositionUntil.value = Date.now() + 450
    lastProgrammaticScrollTop.value = clampedScrollTop
    if (restoreAsReadPosition) {
      scrollContainer.scrollTop = clampedScrollTop
    } else {
      scrollContainer.scrollTop = clampedScrollTop
    }
    lastEditorInteraction.value = position.interaction
    const actual = {
      selectionStart: current.selectionStart,
      selectionEnd: current.selectionEnd,
      scrollTop: scrollContainer.scrollTop,
    }
    logPositionEvent(restoreAsReadPosition ? 'restore-read' : 'restore-edit', {
      articleId,
      token,
      phase,
      expectedScrollTop: clampedScrollTop,
      expectedSelectionStart: safeStart,
      expectedSelectionEnd: safeEnd,
      actualSelectionStart: actual.selectionStart,
      actualSelectionEnd: actual.selectionEnd,
      actualScrollTop: actual.scrollTop,
    })
    return Math.abs(scrollContainer.scrollTop - clampedScrollTop) <= 4 &&
      (restoreAsReadPosition || (current.selectionStart === safeStart && current.selectionEnd === safeEnd))
  }

  applyRestore('initial')
  window.setTimeout(() => {
    if (!applyRestore('retry-80')) {
      logPositionEvent('restore-retry', { articleId, token, phase: 'retry-80' })
    }
  }, 80)
  window.setTimeout(() => {
    if (!applyRestore('retry-250')) {
      logPositionEvent('restore-retry', { articleId, token, phase: 'retry-250' })
    }
    if (store.selectedEntry?.id === articleId && token === restoreToken) {
      restoringEditorPosition.value = false
    }
  }, 250)
}

async function restoreEditorPositionIfNeeded(articleId = store.selectedEntry?.id) {
  const appliedRouteFocus = await applyRouteFocusRange()
  if (!appliedRouteFocus) {
    await restoreSavedEditorPosition(articleId)
  }
}

function updateTailSpace() {
  tailSpace.value = editorTailSpace(editorViewportHeight())
}

function editorViewportHeight(): number {
  return editorScrollRef.value?.clientHeight || bodyRef.value?.clientHeight || 600
}

function editorMaxScrollTop(): number {
  const scrollContainer = editorScrollRef.value
  if (!scrollContainer) return 0
  return Math.max(0, scrollContainer.scrollHeight - scrollContainer.clientHeight)
}

function scrollEditorTo(scrollTop: number) {
  const scrollContainer = editorScrollRef.value
  if (!scrollContainer) return
  suppressReadPositionUntil.value = Date.now() + 450
  const nextScrollTop = Math.min(editorMaxScrollTop(), Math.max(0, scrollTop))
  lastProgrammaticScrollTop.value = nextScrollTop
  scrollContainer.scrollTop = nextScrollTop
}

function resizeBodyEditor() {
  const textarea = bodyRef.value
  if (!textarea) return
  textarea.style.height = 'auto'
  const minHeight = settings.focusMode ? Math.max(720, editorViewportHeight() - 64) : 520
  textarea.style.height = `${Math.max(textarea.scrollHeight, minHeight)}px`
}

function caretOffsetTopForTextArea(textarea: HTMLTextAreaElement, position = textarea.selectionEnd): number {
  const style = window.getComputedStyle(textarea)
  const mirror = document.createElement('div')
  const caret = document.createElement('span')
  const properties = [
    'box-sizing',
    'width',
    'font-family',
    'font-size',
    'font-weight',
    'font-style',
    'letter-spacing',
    'text-transform',
    'word-spacing',
    'text-indent',
    'line-height',
    'padding-top',
    'padding-right',
    'padding-bottom',
    'padding-left',
    'border-top-width',
    'border-right-width',
    'border-bottom-width',
    'border-left-width',
    'white-space',
    'word-break',
    'overflow-wrap',
    'tab-size',
  ] as const
  for (const property of properties) {
    mirror.style.setProperty(property, style.getPropertyValue(property))
  }
  mirror.style.position = 'absolute'
  mirror.style.visibility = 'hidden'
  mirror.style.left = '-9999px'
  mirror.style.top = '0'
  mirror.style.height = 'auto'
  mirror.style.minHeight = '0'
  mirror.style.overflow = 'hidden'
  mirror.style.width = `${textarea.clientWidth}px`
  mirror.style.whiteSpace = 'pre-wrap'
  mirror.style.overflowWrap = 'break-word'
  mirror.textContent = textarea.value.slice(0, Math.max(0, Math.min(position, textarea.value.length)))
  caret.textContent = '\u200b'
  mirror.appendChild(caret)
  document.body.appendChild(mirror)
  const result = caret.offsetTop
  mirror.remove()
  return result
}

function scrollTopForCaretPosition(
  textarea: HTMLTextAreaElement,
  position = textarea.selectionEnd,
  anchorRatio = COMFORT_ANCHOR_RATIO
): number {
  return Math.max(
    0,
    textarea.offsetTop + caretOffsetTopForTextArea(textarea, position) - editorViewportHeight() * anchorRatio
  )
}

function keepCaretNearComfortLine(force = false) {
  if (!bodyRef.value || !editorScrollRef.value || restoringEditorPosition.value) return
  updateTailSpace()
  const textarea = bodyRef.value
  const scrollContainer = editorScrollRef.value
  const caretScrollTop = textarea.offsetTop + caretOffsetTopForTextArea(textarea)
  if (!force && !shouldRecenterCaret({
    caretScrollTop,
    currentScrollTop: scrollContainer.scrollTop,
    clientHeight: scrollContainer.clientHeight,
  })) {
    return
  }
  const nextScrollTop = Math.max(0, caretScrollTop - scrollContainer.clientHeight * COMFORT_ANCHOR_RATIO)
  scrollEditorTo(nextScrollTop)
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

async function refreshWritingNotes() {
  notesError.value = ''
  if (!store.selectedEntry) {
    writingNotes.value = []
    return
  }
  notesLoading.value = true
  try {
    writingNotes.value = await notesApi.listNotes(store.selectedEntry.id, true)
  } catch (e) {
    notesError.value = e instanceof Error ? e.message : String(e)
  } finally {
    notesLoading.value = false
  }
}

async function addWritingNote() {
  const body = newNoteBody.value.trim()
  if (!store.selectedEntry || !body) return
  notesError.value = ''
  try {
    const note = await notesApi.createNote(store.selectedEntry.id, body)
    writingNotes.value = sortWritingNotes([note, ...writingNotes.value.filter((item) => item.id !== note.id)])
    newNoteBody.value = ''
  } catch (e) {
    notesError.value = e instanceof Error ? e.message : String(e)
  }
}

function startEditNote(note: WritingNote) {
  editingNoteId.value = note.id
  editingNoteBody.value = note.body
}

function cancelEditNote() {
  editingNoteId.value = null
  editingNoteBody.value = ''
}

async function saveEditNote(note: WritingNote) {
  if (!store.selectedEntry) return
  const body = editingNoteBody.value.trim()
  if (!body) return
  notesError.value = ''
  try {
    const updated = await notesApi.updateNote(store.selectedEntry.id, note.id, body)
    replaceWritingNote(updated)
    cancelEditNote()
  } catch (e) {
    notesError.value = e instanceof Error ? e.message : String(e)
  }
}

async function toggleNotePinned(note: WritingNote) {
  if (!store.selectedEntry) return
  notesError.value = ''
  try {
    const updated = await notesApi.setPinned(store.selectedEntry.id, note.id, !note.pinned)
    replaceWritingNote(updated)
  } catch (e) {
    notesError.value = e instanceof Error ? e.message : String(e)
  }
}

async function toggleNoteDone(note: WritingNote) {
  if (!store.selectedEntry) return
  notesError.value = ''
  try {
    const updated = await notesApi.setDone(store.selectedEntry.id, note.id, note.status !== 'done')
    replaceWritingNote(updated)
  } catch (e) {
    notesError.value = e instanceof Error ? e.message : String(e)
  }
}

async function deleteWritingNote(note: WritingNote) {
  if (!store.selectedEntry) return
  if (!confirm(t('articles.notesDeleteConfirm'))) return
  notesError.value = ''
  try {
    await notesApi.deleteNote(store.selectedEntry.id, note.id)
    writingNotes.value = writingNotes.value.filter((item) => item.id !== note.id)
  } catch (e) {
    notesError.value = e instanceof Error ? e.message : String(e)
  }
}

function replaceWritingNote(note: WritingNote) {
  writingNotes.value = sortWritingNotes(
    writingNotes.value.map((item) => (item.id === note.id ? note : item))
  )
}

function sortWritingNotes(notes: WritingNote[]): WritingNote[] {
  return [...notes].sort((a, b) => {
    if (a.status !== b.status) return a.status === 'open' ? -1 : 1
    if (a.pinned !== b.pinned) return a.pinned ? -1 : 1
    return a.sort_order - b.sort_order
  })
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
  if (store.selectedEntry && route.name === 'articles' && typeof route.query.id !== 'string') {
    router.replace({ name: 'articles', query: { id: store.selectedEntry.id } })
  }
  syncDraftFromSelected()
  await Promise.all([refreshEntryCollections(), refreshWritingNotes()])
  await restoreEditorPositionIfNeeded()
  updateTailSpace()
  window.addEventListener('resize', updateTailSpace)
  window.addEventListener('keydown', handleKeydown)
  window.addEventListener('beforeunload', handleBeforeUnload)
})

onUnmounted(() => {
  flushPendingEditorPosition()
  saveCurrentEditorPositionNow()
  void flushPendingArticleSave()
  window.removeEventListener('resize', updateTailSpace)
  window.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('beforeunload', handleBeforeUnload)
})

watch(
  () => store.selectedEntry?.id,
  async (_newId, oldId) => {
    flushPendingEditorPosition()
    saveLastKnownEditorPositionForArticle(oldId)
    const saved = await flushPendingArticleSave()
    if (!saved) return
    syncDraftFromSelected()
    refreshEntryCollections()
    refreshWritingNotes()
    await restoreEditorPositionIfNeeded(_newId ?? undefined)
    updateTailSpace()
  }
)

watch(
  () => route.query.id,
  async () => {
    logPositionEvent('route-change', {
      fromArticleId: store.selectedEntry?.id ?? null,
      toArticleId: typeof route.query.id === 'string' ? route.query.id : null,
    })
    flushPendingEditorPosition()
    saveCurrentEditorPositionNow()
    const saved = await flushPendingArticleSave()
    if (!saved) return
    await applyRouteArticle()
    syncDraftFromSelected()
    await restoreEditorPositionIfNeeded()
    updateTailSpace()
  }
)

watch(
  () => [route.query.focus_start, route.query.focus_end],
  () => {
    void applyRouteFocusRange()
  }
)

</script>

<template>
  <div class="flex h-full overflow-hidden bg-[#f7f3ea] text-stone-900">
    <aside v-if="!settings.focusMode" class="w-80 shrink-0 border-r border-stone-200 bg-white flex flex-col">
      <div class="p-4 border-b border-stone-200">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-xl font-bold">{{ t('articles.title') }}</h2>
          <button
            @click="createEntryFromSidebar"
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
          {{ displayList.length }} {{ listStatusLabel }}
        </p>
        <div v-if="allTags.length" class="mt-3 flex flex-wrap gap-1.5">
          <button
            v-if="selectedTag"
            @click="clearTagFilter"
            class="rounded-full bg-stone-900 px-2.5 py-1 text-xs font-medium text-white"
          >
            {{ t('articles.allTags') }}
          </button>
          <button
            v-for="tag in allTags"
            :key="tag"
            @click="selectTag(tag)"
            :class="[
              'rounded-full px-2.5 py-1 text-xs font-medium transition-colors',
              selectedTag === tag
                ? 'bg-amber-500 text-white'
                : 'bg-stone-100 text-stone-600 hover:bg-stone-200',
            ]"
          >
            {{ tag }}
          </button>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto">
        <div v-if="store.loading" class="p-4 text-sm text-stone-400">{{ t('common.loading') }}</div>
        <div v-else-if="store.error" class="p-4 text-sm text-red-500">{{ store.error }}</div>
        <div v-else-if="!displayList.length" class="p-4 text-sm text-stone-400">
          {{ emptyListLabel }}
        </div>
        <button
          v-for="entry in displayList"
          :key="entry.id"
          @click="selectEntryFromList(entry.id)"
          :data-testid="`article-entry-${entry.id}`"
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
            <button
              v-for="tag in entry.tags"
              :key="tag"
              @click.stop="selectTag(tag)"
              :class="[
                'rounded px-2 py-1 text-xs transition-colors',
                selectedTag === tag ? 'bg-amber-500 text-white' : 'bg-stone-100 text-stone-600 hover:bg-stone-200',
              ]"
            >{{ tag }}</button>
          </div>
        </button>
      </div>
    </aside>

    <main class="flex-1 min-w-0 min-h-0 flex flex-col bg-[#fffdf8] overflow-hidden relative">
      <FindReplace
        v-if="!settings.focusMode"
        :show="showFindReplace"
        :text="bodyDraft"
        @close="showFindReplace = false"
        @replace="handleReplace"
        @navigate="navigateMatch"
        @queryChange="syncFindQuery"
      />

      <div v-if="!settings.focusMode" class="flex items-center justify-between gap-4 p-4 border-b border-stone-200 bg-white/80">
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
            data-testid="article-add-epigraph"
            class="px-3 py-2 text-sm bg-stone-100 hover:bg-stone-200 rounded transition-colors"
          >
            {{ t('articles.addEpigraph') }}
          </button>
          <div v-if="store.selectedEntry" class="flex overflow-hidden rounded-lg border border-stone-200">
            <button
              v-for="format in ['md', 'txt', 'docx'] as const"
              :key="format"
              @click="exportArticle(format)"
              :disabled="exportingFormat !== null"
              class="px-3 py-2 text-xs font-semibold uppercase text-stone-600 hover:bg-stone-100"
            >
              {{ exportingFormat === format ? '...' : format }}
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
      <div
        v-if="exportError || exportMessage"
        :class="[
          'border-b px-6 py-2 text-sm',
          exportError
            ? 'border-red-100 bg-red-50 text-red-700'
            : 'border-emerald-100 bg-emerald-50 text-emerald-700'
        ]"
      >
        {{ exportError || exportMessage }}
      </div>

      <div
        ref="editorScrollRef"
        :class="['flex-1 min-h-0 overflow-y-auto', settings.focusMode ? 'p-8 md:p-12' : 'p-6']"
        data-testid="article-editor-scroll"
        @wheel.passive="markUserScrollIntent"
        @pointerdown="markUserScrollIntent"
        @touchstart.passive="markUserScrollIntent"
        @scroll="scheduleReadPositionSave"
      >
        <div
          v-if="store.selectedEntry"
          :class="[
            'mx-auto flex min-h-full flex-col',
            settings.focusMode ? 'w-full max-w-[108rem] gap-0' : 'w-full max-w-7xl gap-5'
          ]"
        >
          <section
            v-if="epigraphActive && !settings.focusMode"
            class="rounded-[1.75rem] border border-amber-200 bg-[#fff8e8] px-8 py-6 shadow-sm"
          >
            <div class="mb-4 flex items-center justify-between gap-3">
              <div>
                <p class="text-xs font-semibold uppercase tracking-[0.28em] text-amber-700">{{ t('articles.epigraph') }}</p>
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
              data-testid="article-epigraph-quote"
              @input="handleEpigraphInput"
              rows="3"
              class="w-full resize-none border-none bg-transparent font-serif text-lg italic leading-8 text-stone-800 outline-none"
              :placeholder="t('articles.epigraphQuotePlaceholder')"
            />
            <input
              v-model="epigraphAttribution"
              data-testid="article-epigraph-attribution"
              @input="handleEpigraphInput"
              class="mt-3 w-full bg-transparent text-right text-sm text-stone-500 outline-none"
              :placeholder="t('articles.epigraphAttributionPlaceholder')"
            />
          </section>
          <textarea
            ref="bodyRef"
            data-testid="article-body-editor"
            v-model="bodyDraft"
            @input="handleBodyInput"
            @keydown="handleBodyKeydown"
            @keyup="scheduleCurrentEditorPositionSave"
            @click="scheduleCurrentEditorPositionSave"
            @pointerup="handleBodyPointerSettled"
            @mouseup="handleBodyPointerSettled"
            @focusout="handleBodyFocusOut"
            @select="scheduleCurrentEditorPositionSave"
            :style="{ paddingBottom: `${tailSpace}px` }"
            :class="[
              'w-full block overflow-hidden bg-[#fffdf8] focus:outline-none resize-none leading-relaxed',
              settings.focusMode
                ? 'min-h-[calc(100vh-5rem)] border-0 px-6 py-8 md:px-10 text-lg shadow-none focus:ring-0'
                : 'min-h-[520px] rounded-[1.5rem] border border-stone-200 p-6 shadow-sm focus:ring-2 focus:ring-amber-300'
            ]"
            :placeholder="t('articles.startWriting')"
          />
        </div>
        <div v-else class="text-center text-stone-400 mt-20">
          {{ t('articles.selectOrCreate') }}
        </div>
      </div>
    </main>

    <aside
      v-if="!settings.rightContextPaneCollapsed && !settings.focusMode"
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
                <span>{{ t('articles.paragraphCount') }}</span><span class="font-medium">{{ paragraphCount }}</span>
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
            <div class="mb-2 flex items-center justify-between gap-2">
              <h3 class="text-sm font-semibold text-stone-700">{{ t('articles.writingNotes') }}</h3>
              <span class="rounded-full bg-amber-50 px-2 py-1 text-xs text-amber-700">
                {{ t('articles.openNotesCount', { count: openWritingNotes.length }) }}
              </span>
            </div>
            <p class="mb-3 text-xs leading-5 text-stone-500">{{ t('articles.writingNotesHint') }}</p>
            <div v-if="notesError" class="mb-2 rounded-lg bg-red-50 p-2 text-xs text-red-700">
              {{ notesError }}
            </div>
            <div class="mb-3 rounded-2xl border border-amber-100 bg-amber-50/50 p-3">
              <textarea
                v-model="newNoteBody"
                rows="3"
                class="w-full resize-none rounded-xl border border-amber-100 bg-white/80 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-amber-300"
                :placeholder="t('articles.writingNotePlaceholder')"
                @keydown.ctrl.enter.prevent="addWritingNote"
                @keydown.meta.enter.prevent="addWritingNote"
              />
              <button
                @click="addWritingNote"
                :disabled="!newNoteBody.trim() || notesLoading"
                class="mt-2 w-full rounded-xl bg-amber-600 px-3 py-2 text-sm font-semibold text-white hover:bg-amber-700 disabled:opacity-40"
              >
                {{ t('articles.addWritingNote') }}
              </button>
            </div>

            <div v-if="notesLoading" class="text-sm text-stone-400">{{ t('common.loading') }}</div>
            <div v-else-if="!openWritingNotes.length" class="rounded-xl bg-stone-50 p-3 text-sm text-stone-400">
              {{ t('articles.noWritingNotes') }}
            </div>
            <div v-else class="space-y-2">
              <article
                v-for="note in openWritingNotes"
                :key="note.id"
                class="rounded-2xl border border-amber-100 bg-[#fff9e8] p-3 shadow-sm"
              >
                <textarea
                  v-if="editingNoteId === note.id"
                  v-model="editingNoteBody"
                  rows="4"
                  class="w-full resize-none rounded-xl border border-amber-200 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-amber-300"
                />
                <p v-else class="whitespace-pre-wrap text-sm leading-6 text-stone-700">{{ note.body }}</p>
                <div class="mt-3 flex flex-wrap gap-2">
                  <template v-if="editingNoteId === note.id">
                    <button @click="saveEditNote(note)" class="rounded-lg bg-stone-900 px-2.5 py-1 text-xs text-white">
                      {{ t('common.save') }}
                    </button>
                    <button @click="cancelEditNote" class="rounded-lg bg-stone-100 px-2.5 py-1 text-xs text-stone-600">
                      {{ t('common.cancel') }}
                    </button>
                  </template>
                  <template v-else>
                    <button @click="toggleNotePinned(note)" class="rounded-lg bg-white/80 px-2.5 py-1 text-xs text-stone-600 hover:bg-white">
                      {{ note.pinned ? t('articles.unpinNote') : t('articles.pinNote') }}
                    </button>
                    <button @click="startEditNote(note)" class="rounded-lg bg-white/80 px-2.5 py-1 text-xs text-stone-600 hover:bg-white">
                      {{ t('common.edit') }}
                    </button>
                    <button @click="toggleNoteDone(note)" class="rounded-lg bg-white/80 px-2.5 py-1 text-xs text-stone-600 hover:bg-white">
                      {{ t('articles.completeNote') }}
                    </button>
                    <button @click="deleteWritingNote(note)" class="rounded-lg bg-red-50 px-2.5 py-1 text-xs text-red-600 hover:bg-red-100">
                      {{ t('common.delete') }}
                    </button>
                  </template>
                </div>
              </article>
            </div>

            <div v-if="doneWritingNotes.length" class="mt-3">
              <button
                @click="showDoneNotes = !showDoneNotes"
                class="w-full rounded-xl bg-stone-50 px-3 py-2 text-left text-xs font-semibold text-stone-500 hover:bg-stone-100"
              >
                {{ showDoneNotes ? t('articles.hideDoneNotes') : t('articles.showDoneNotes', { count: doneWritingNotes.length }) }}
              </button>
              <div v-if="showDoneNotes" class="mt-2 space-y-2">
                <article
                  v-for="note in doneWritingNotes"
                  :key="note.id"
                  class="rounded-2xl border border-stone-100 bg-stone-50 p-3 opacity-75"
                >
                  <p class="whitespace-pre-wrap text-sm leading-6 text-stone-500 line-through">{{ note.body }}</p>
                  <div class="mt-2 flex gap-2">
                    <button @click="toggleNoteDone(note)" class="rounded-lg bg-white px-2.5 py-1 text-xs text-stone-600">
                      {{ t('articles.restoreNote') }}
                    </button>
                    <button @click="deleteWritingNote(note)" class="rounded-lg bg-red-50 px-2.5 py-1 text-xs text-red-600">
                      {{ t('common.delete') }}
                    </button>
                  </div>
                </article>
              </div>
            </div>
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
                @click="openAiToolsForArticle"
                class="w-full px-3 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm transition-colors"
              >
                {{ t('articles.aiTools') }}
              </button>
              <button
                v-if="!store.selectedEntry.archived_at"
                @click="archiveSelectedEntry"
                class="w-full px-3 py-2 bg-stone-100 hover:bg-stone-200 text-stone-700 rounded-lg text-sm transition-colors"
              >
                {{ t('articles.archive') }}
              </button>
              <button
                @click="deleteSelectedEntry"
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
