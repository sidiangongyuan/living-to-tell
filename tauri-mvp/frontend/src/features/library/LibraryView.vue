<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLibraryStore } from './store'
import { libraryApi, type LibraryStats, type Reference } from '../../api/library'
import { motifsApi, type MotifExcerpt, type MotifNode } from '../../api/motifs'
import { errorMessage, isHttpStatus } from '../../api/base'
import { type LibraryGroupMode, EMPTY_SOURCE_GROUP_KEY } from './grouping'
import { useI18n } from '../../i18n'
import {
  addUniqueMotifName,
  buildMotifSelectionSnapshot,
  findMotifTextPosition,
  readMotifJumpSnapshot,
  resolveMotifExcerptRange,
} from '../motifs/selection'

const store = useLibraryStore()
const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const searchInput = ref('')
const saveTimer = ref<number | null>(null)
const stats = ref<LibraryStats | null>(null)
const initialized = ref(false)
const applyingRouteState = ref(false)
const copyNotice = ref('')
const pendingReferenceSave = ref<Reference | null>(null)
const saveNotice = ref('')
const saveFailed = ref(false)
const contentRef = ref<HTMLTextAreaElement | null>(null)
const detailScrollRef = ref<HTMLElement | null>(null)
const motifAttachOpen = ref(false)
const motifAttachX = ref(0)
const motifAttachY = ref(0)
const motifAttachPanelRef = ref<HTMLDivElement | null>(null)
const motifContextMenuOpen = ref(false)
const motifContextMenuX = ref(0)
const motifContextMenuY = ref(0)
const motifAttachQuery = ref('')
const motifAttachNote = ref('')
const motifAttachSaving = ref(false)
const motifAttachError = ref('')
const motifAttachNotice = ref('')
const motifAttachExistingExcerptId = ref<string | null>(null)
const motifAttachSelection = ref<{
  text: string
  start: number
  end: number
  beforeContext: string
  afterContext: string
} | null>(null)
const motifAttachNames = ref<string[]>([])
const motifCandidates = ref<MotifNode[]>([])
const motifSourceExcerpts = ref<MotifExcerpt[]>([])
const motifSourceLoading = ref(false)
const motifSourceError = ref('')
const motifHighlightActive = ref(false)
const motifJumpMessage = ref('')
let motifAttachLookupToken = 0
let motifSourceRefreshToken = 0
let motifAttachDragState: {
  pointerId: number
  startClientX: number
  startClientY: number
  startX: number
  startY: number
} | null = null

onMounted(async () => {
  await Promise.all([store.loadReferences(), loadStats()])
  initialized.value = true
  await applyRouteState()
  await refreshMotifSourceExcerpts()
  await applyMotifRouteFocus()
})

onUnmounted(() => {
  stopMotifAttachDrag()
  void flushPendingReferenceSave()
})

async function loadStats() {
  try {
    stats.value = await libraryApi.getStats()
  } catch (e) {
    console.error('Load stats failed:', e)
  }
}

const currentGroups = computed(() =>
  store.groupMode === 'usage'
    ? store.usageGroups
    : store.sourceGroups
)

const activeGroup = computed(() =>
  store.groupMode === 'usage'
    ? store.activeUsageGroup
    : store.activeSourceGroup
)

const activeGroupLabel = computed(() => {
  const group = activeGroup.value
  if (!group) return ''

  return store.groupMode === 'usage'
    ? usageLabel(group.key)
    : sourceGroupLabel(group.key)
})

const motifSuggestions = computed(() => {
  const query = motifAttachQuery.value.trim().toLowerCase()
  return motifCandidates.value
    .filter((motif) => {
      if (motifAttachNames.value.includes(motif.name)) return false
      if (!query) return true
      return motif.name.toLowerCase().includes(query) ||
        motif.aliases.some((alias) => alias.toLowerCase().includes(query))
    })
    .slice(0, 6)
})
const sortedMotifSourceExcerpts = computed(() =>
  [...motifSourceExcerpts.value].sort((a, b) => {
    const aStart = a.selection_start ?? Number.MAX_SAFE_INTEGER
    const bStart = b.selection_start ?? Number.MAX_SAFE_INTEGER
    if (aStart !== bStart) return aStart - bStart
    return a.excerpt_text.localeCompare(b.excerpt_text)
  })
)
const activeMotifExcerptId = computed(() =>
  typeof route.query.motif_excerpt === 'string' ? route.query.motif_excerpt : ''
)
const resolvedMotifSourceExcerpts = computed(() =>
  sortedMotifSourceExcerpts.value.map((excerpt) => ({
    excerpt,
    range: resolveMotifExcerptRange(store.selectedReference?.content ?? '', excerpt),
  }))
)

function isStaleReferenceRequest(referenceId: string, token: number): boolean {
  return token !== motifSourceRefreshToken || store.selectedReference?.id !== referenceId
}

function friendlyReferenceMotifError(e: unknown): string {
  if (isHttpStatus(e, 404)) return t('motifs.sourceMissing')
  return errorMessage(e)
}

let searchTimer: number | null = null
watch(searchInput, (value) => {
  if (searchTimer) window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => {
    void store.search(value)
  }, 300)
})

watch(
  () => [route.query.ref, route.query.group, route.query.action, route.query.motif_excerpt, route.query.focus_start, route.query.focus_end],
  async () => {
    if (!initialized.value || applyingRouteState.value) return
    const saved = await flushPendingReferenceSave()
    if (!saved) return
    await applyRouteState()
    await refreshMotifSourceExcerpts()
    await applyMotifRouteFocus()
  }
)

function scheduleSave() {
  const snapshot = snapshotSelectedReference()
  if (!snapshot) return
  pendingReferenceSave.value = snapshot
  saveNotice.value = t('library.savePending')
  saveFailed.value = false
  if (saveTimer.value) window.clearTimeout(saveTimer.value)
  saveTimer.value = window.setTimeout(() => {
    void flushPendingReferenceSave()
  }, 600)
}

async function flushPendingReferenceSave(): Promise<boolean> {
  if (saveTimer.value) {
    window.clearTimeout(saveTimer.value)
    saveTimer.value = null
  }
  const snapshot = pendingReferenceSave.value
  if (!snapshot) return true
  pendingReferenceSave.value = null
  saveNotice.value = t('library.savePending')
  saveFailed.value = false
  try {
    await store.updateReference(snapshot)
    saveNotice.value = t('library.saveSuccess')
    saveFailed.value = false
    return true
  } catch (e) {
    pendingReferenceSave.value = snapshot
    const message = e instanceof Error ? e.message : String(e)
    store.error = message
    saveNotice.value = t('library.saveFailed', { message })
    saveFailed.value = true
    return false
  }
}

function snapshotSelectedReference(): Reference | null {
  const reference = store.selectedReference
  if (!reference) return null
  return {
    ...reference,
    tags: [...reference.tags],
  }
}

async function selectReference(referenceId: string) {
  const saved = await flushPendingReferenceSave()
  if (!saved) return
  store.selectReference(referenceId)
  await refreshMotifSourceExcerpts()
}

async function selectGroup(mode: LibraryGroupMode, key: string) {
  const saved = await flushPendingReferenceSave()
  if (!saved) return
  if (mode === 'usage') {
    store.selectUsageGroup(key)
    return
  }

  store.selectSourceGroup(key)
}

async function setGroupMode(mode: LibraryGroupMode) {
  const saved = await flushPendingReferenceSave()
  if (!saved) return
  store.setGroupMode(mode)
}

function preview(content: string): string {
  return content.trim().slice(0, 140) || t('library.empty')
}

function usageLabel(kind: string): string {
  switch (kind) {
    case 'style':
      return t('library.style')
    case 'imagery':
      return t('library.imagery')
    case 'structure':
      return t('library.structure')
    case 'rhetoric':
      return t('library.rhetoric')
    case 'diction':
      return t('library.diction')
    case 'reflection':
      return t('library.reflection')
    case 'setting':
      return t('library.setting')
    case 'technique':
      return t('library.technique')
    case 'other':
      return t('library.other')
    default:
      return kind || t('library.other')
  }
}

function sourceGroupLabel(key: string): string {
  return key === EMPTY_SOURCE_GROUP_KEY ? t('library.empty') : key
}

function getRouteGroupMode(): LibraryGroupMode | null {
  const group = route.query.group
  return group === 'source' || group === 'usage' ? group : null
}

async function applyRouteState() {
  const refId = typeof route.query.ref === 'string' ? route.query.ref : null
  const groupMode = getRouteGroupMode()
  const action = typeof route.query.action === 'string' ? route.query.action : null

  if (!refId && !groupMode && action !== 'create_reference') {
    return
  }

  applyingRouteState.value = true
  try {
    if (action === 'create_reference') {
      const created = await store.createReference()
      await loadStats()
      const nextQuery: Record<string, string | string[]> = {
        ...route.query,
        ref: created.id,
        group: store.groupMode,
      }
      delete nextQuery.action
      await router.replace({ name: 'library', query: nextQuery })
      return
    }

    if (refId) {
      await store.selectReferenceFromDeepLink(refId, groupMode)
    } else if (groupMode) {
      store.setGroupMode(groupMode)
    }
  } catch (e) {
    console.error('Apply library deep link failed:', e)
  } finally {
    applyingRouteState.value = false
  }
}

async function deleteSelectedReference() {
  if (!store.selectedReference) return
  if (!confirm(t('library.deleteConfirm'))) return
  if (pendingReferenceSave.value?.id === store.selectedReference.id) {
    if (saveTimer.value) window.clearTimeout(saveTimer.value)
    saveTimer.value = null
    pendingReferenceSave.value = null
  }
  await store.deleteReference(store.selectedReference.id)
  await loadStats()
}

async function createReference() {
  const saved = await flushPendingReferenceSave()
  if (!saved) return
  await store.createReference()
  await loadStats()
}

async function createReferenceInActiveSource() {
  const saved = await flushPendingReferenceSave()
  if (!saved) return
  const sourceReference = store.activeSourceGroup?.references[0]
  await store.createReference({
    source_title: sourceReference?.source_title ?? '',
    source_author: sourceReference?.source_author ?? '',
  })
  store.setGroupMode('source')
  await loadStats()
}

function formatFullReferenceCopy(): string {
  const reference = store.selectedReference
  if (!reference) return ''
  const content = reference.content.trim()
  const title = reference.source_title.trim()
  const author = reference.source_author.trim()
  const sourceParts = [
    title ? `《${title}》` : '',
    author,
  ].filter(Boolean)
  if (!sourceParts.length) return content
  return [content, `——${sourceParts.join(' ')}`].filter(Boolean).join('\n\n')
}

async function copyText(text: string, noticeKey: string) {
  if (!text.trim()) return
  try {
    await navigator.clipboard.writeText(text)
    copyNotice.value = t(noticeKey)
  } catch (e) {
    copyNotice.value = e instanceof Error ? e.message : String(e)
  }
  window.setTimeout(() => {
    copyNotice.value = ''
  }, 1800)
}

async function copyReferenceContent() {
  await copyText(store.selectedReference?.content ?? '', 'library.copyContentDone')
}

async function copyReferenceFull() {
  await copyText(formatFullReferenceCopy(), 'library.copyFullDone')
}

function motifAttachPanelSize() {
  const rect = motifAttachPanelRef.value?.getBoundingClientRect()
  return {
    width: rect?.width ?? Math.min(380, window.innerWidth - 32),
    height: rect?.height ?? Math.min(560, window.innerHeight * 0.8),
  }
}

function clampMotifPanelTopLeft(x: number, y: number) {
  const { width, height } = motifAttachPanelSize()
  motifAttachX.value = Math.max(16, Math.min(x, window.innerWidth - width - 16))
  motifAttachY.value = Math.max(16, Math.min(y, window.innerHeight - height - 16))
}

function clampMotifPanelPosition(x: number, y: number) {
  const { height } = motifAttachPanelSize()
  const preferredX = x + 12
  const preferredY = y + 12 + height > window.innerHeight - 16 ? y - height - 12 : y + 12
  clampMotifPanelTopLeft(preferredX, preferredY)
}

function clampMotifContextMenuPosition(x: number, y: number) {
  const width = 180
  const height = 48
  motifContextMenuX.value = Math.max(16, Math.min(x + 8, window.innerWidth - width - 16))
  motifContextMenuY.value = Math.max(16, Math.min(y + 8, window.innerHeight - height - 16))
}

async function loadMotifCandidates() {
  try {
    motifCandidates.value = await motifsApi.listMotifs('', 500)
  } catch (e) {
    motifAttachError.value = e instanceof Error ? e.message : String(e)
  }
}

async function loadExistingMotifAttachmentForSelection() {
  const selection = motifAttachSelection.value
  const reference = store.selectedReference
  if (!selection || !reference) return
  const token = ++motifAttachLookupToken
  try {
    const existing = await motifsApi.lookupExcerpt({
      source_kind: 'reference',
      source_id: reference.id,
      excerpt_text: selection.text,
      selection_start: selection.start,
      selection_end: selection.end,
      before_context: selection.beforeContext,
      after_context: selection.afterContext,
    })
    if (token !== motifAttachLookupToken || store.selectedReference?.id !== reference.id) return
    motifAttachExistingExcerptId.value = existing?.id ?? null
    if (existing) {
      motifAttachNames.value = existing.motif_names
      if (!motifAttachNote.value.trim()) {
        motifAttachNote.value = existing.note
      }
      void refreshMotifSourceExcerpts()
    }
  } catch (e) {
    if (token === motifAttachLookupToken && store.selectedReference?.id === reference.id) {
      motifAttachError.value = friendlyReferenceMotifError(e)
    }
  }
}

async function refreshMotifSourceExcerpts() {
  const referenceId = store.selectedReference?.id
  const token = ++motifSourceRefreshToken
  motifSourceError.value = ''
  if (!referenceId) {
    motifSourceExcerpts.value = []
    motifSourceLoading.value = false
    return
  }
  motifSourceLoading.value = true
  try {
    const excerpts = await motifsApi.listExcerptsForSource('reference', referenceId)
    if (isStaleReferenceRequest(referenceId, token)) return
    motifSourceExcerpts.value = excerpts
  } catch (e) {
    if (isStaleReferenceRequest(referenceId, token)) return
    motifSourceError.value = friendlyReferenceMotifError(e)
    if (isHttpStatus(e, 404)) {
      motifSourceExcerpts.value = []
    }
  } finally {
    if (!isStaleReferenceRequest(referenceId, token)) {
      motifSourceLoading.value = false
    }
  }
}

function prepareMotifSelection() {
  const reference = store.selectedReference
  if (!contentRef.value || !reference) return false
  const snapshot = buildMotifSelectionSnapshot(
    reference.content,
    contentRef.value.selectionStart,
    contentRef.value.selectionEnd,
  )
  if (!snapshot) return false
  motifAttachSelection.value = snapshot
  motifAttachNames.value = []
  motifAttachNote.value = ''
  motifAttachQuery.value = ''
  motifAttachExistingExcerptId.value = null
  motifAttachError.value = ''
  motifAttachNotice.value = ''
  return true
}

function openMotifAttachPanelAt(x: number, y: number) {
  motifAttachOpen.value = true
  motifContextMenuOpen.value = false
  clampMotifPanelPosition(x, y)
  void loadMotifCandidates()
  void loadExistingMotifAttachmentForSelection()
}

function openMotifContextMenuFromSelection(event: MouseEvent) {
  if (!prepareMotifSelection()) return false
  motifContextMenuOpen.value = true
  motifAttachOpen.value = false
  clampMotifContextMenuPosition(event.clientX, event.clientY)
  return true
}

function openMotifAttachFromContextMenu() {
  if (!motifAttachSelection.value) return
  openMotifAttachPanelAt(motifContextMenuX.value, motifContextMenuY.value)
}

function closeMotifContextMenu() {
  motifContextMenuOpen.value = false
}

function handleContentContextMenu(event: MouseEvent) {
  if (openMotifContextMenuFromSelection(event)) {
    event.preventDefault()
  }
}

function handleContentPointerSettled(event?: MouseEvent | PointerEvent) {
  if (event && 'button' in event && event.button === 0) closeMotifContextMenu()
  void flushPendingReferenceSave()
}

function closeMotifAttach() {
  motifAttachOpen.value = false
  motifAttachError.value = ''
}

function startMotifAttachDrag(event: PointerEvent) {
  if (event.button !== 0) return
  event.preventDefault()
  motifAttachDragState = {
    pointerId: event.pointerId,
    startClientX: event.clientX,
    startClientY: event.clientY,
    startX: motifAttachX.value,
    startY: motifAttachY.value,
  }
  motifAttachPanelRef.value?.setPointerCapture?.(event.pointerId)
  window.addEventListener('pointermove', handleMotifAttachDrag)
  window.addEventListener('pointerup', stopMotifAttachDrag)
  window.addEventListener('pointercancel', stopMotifAttachDrag)
}

function handleMotifAttachDrag(event: PointerEvent) {
  if (!motifAttachDragState || event.pointerId !== motifAttachDragState.pointerId) return
  clampMotifPanelTopLeft(
    motifAttachDragState.startX + event.clientX - motifAttachDragState.startClientX,
    motifAttachDragState.startY + event.clientY - motifAttachDragState.startClientY,
  )
}

function stopMotifAttachDrag(event?: PointerEvent) {
  if (event && motifAttachDragState && event.pointerId !== motifAttachDragState.pointerId) return
  if (event && motifAttachDragState) {
    motifAttachPanelRef.value?.releasePointerCapture?.(motifAttachDragState.pointerId)
  }
  motifAttachDragState = null
  window.removeEventListener('pointermove', handleMotifAttachDrag)
  window.removeEventListener('pointerup', stopMotifAttachDrag)
  window.removeEventListener('pointercancel', stopMotifAttachDrag)
}

function addMotifAttachName(name = motifAttachQuery.value) {
  motifAttachNames.value = addUniqueMotifName(motifAttachNames.value, name)
  motifAttachQuery.value = ''
}

function removeMotifAttachName(name: string) {
  motifAttachNames.value = motifAttachNames.value.filter((item) => item !== name)
}

function handleMotifAttachQueryKeydown(event: KeyboardEvent) {
  if (event.key !== 'Enter') return
  event.preventDefault()
  const firstSuggestion = motifSuggestions.value[0]
  addMotifAttachName(firstSuggestion?.name ?? motifAttachQuery.value)
}

async function saveMotifAttachSelection() {
  const reference = store.selectedReference
  const selection = motifAttachSelection.value
  if (!reference || !selection) return
  if (!motifAttachNames.value.length && motifAttachQuery.value.trim()) {
    addMotifAttachName()
  }
  if (!motifAttachNames.value.length && !motifAttachExistingExcerptId.value) {
    motifAttachError.value = t('motifs.selectionNoMotif')
    return
  }
  motifAttachSaving.value = true
  motifAttachError.value = ''
  try {
    const saved = await flushPendingReferenceSave()
    if (!saved) return
    const wasExistingExcerpt = Boolean(motifAttachExistingExcerptId.value)
    if (motifAttachExistingExcerptId.value) {
      const result = await motifsApi.setMotifsForExcerpt(motifAttachExistingExcerptId.value, {
        motif_names: motifAttachNames.value,
        note: motifAttachNote.value,
      })
      motifAttachExistingExcerptId.value = result.excerpt?.id ?? null
    } else {
      await motifsApi.createExcerpt({
        source_kind: 'reference',
        source_id: reference.id,
        source_title_snapshot: reference.source_title || reference.content.slice(0, 24) || t('motifs.unknownSource'),
        excerpt_text: selection.text,
        note: motifAttachNote.value,
        selection_start: selection.start,
        selection_end: selection.end,
        before_context: selection.beforeContext,
        after_context: selection.afterContext,
        motif_names: motifAttachNames.value,
      })
    }
    await refreshMotifSourceExcerpts()
    motifAttachOpen.value = false
    motifAttachNotice.value = t(wasExistingExcerpt ? 'motifs.selectionUpdated' : 'motifs.selectionAdded')
    await nextTick()
    contentRef.value?.focus({ preventScroll: true })
    contentRef.value?.setSelectionRange(selection.start, selection.end)
    window.setTimeout(() => {
      motifAttachNotice.value = ''
    }, 1800)
  } catch (e) {
    motifAttachError.value = e instanceof Error ? e.message : String(e)
  } finally {
    motifAttachSaving.value = false
  }
}

function parseNumberQuery(value: unknown): number | null {
  if (typeof value !== 'string') return null
  const parsed = Number.parseInt(value, 10)
  return Number.isFinite(parsed) ? parsed : null
}

function activateMotifJumpHighlight(message: string) {
  motifHighlightActive.value = true
  motifJumpMessage.value = message
  window.setTimeout(() => {
    motifHighlightActive.value = false
  }, 1900)
  window.setTimeout(() => {
    motifJumpMessage.value = ''
  }, 3600)
}

async function focusReferenceRange(start: number, end: number, highlight = false) {
  const textarea = contentRef.value
  const reference = store.selectedReference
  if (!textarea || !reference) return false
  await nextTick()
  const safeStart = Math.max(0, Math.min(start, reference.content.length))
  const safeEnd = Math.max(safeStart, Math.min(end, reference.content.length))
  textarea.focus({ preventScroll: true })
  textarea.setSelectionRange(safeStart, safeEnd)
  const lineHeight = Number.parseFloat(window.getComputedStyle(textarea).lineHeight) || 28
  const before = reference.content.slice(0, safeStart)
  const lineCount = before.split('\n').length - 1
  textarea.scrollTop = Math.max(0, lineCount * lineHeight - textarea.clientHeight * 0.45)
  textarea.scrollIntoView({ block: 'center', behavior: 'smooth' })
  if (highlight) {
    activateMotifJumpHighlight(t('motifs.jumpHighlighted'))
  }
  return true
}

async function applyMotifRouteFocus() {
  if (typeof route.query.motif_excerpt !== 'string') return false
  const reference = store.selectedReference
  if (!reference) return false
  if (typeof route.query.ref === 'string' && reference.id !== route.query.ref) {
    return false
  }
  const jump = readMotifJumpSnapshot(window.sessionStorage)
  const jumpText = jump?.text ?? ''
  const start = parseNumberQuery(route.query.focus_start)
  const end = parseNumberQuery(route.query.focus_end)
  if (start !== null && end !== null) {
    const safeStart = Math.max(0, Math.min(start, reference.content.length))
    const safeEnd = Math.max(safeStart, Math.min(end, reference.content.length))
    const currentText = reference.content.slice(safeStart, safeEnd).trim()
    if (!jumpText.trim() || currentText === jumpText.trim()) {
      return focusReferenceRange(safeStart, safeEnd, true)
    }
  }
  const found = findMotifTextPosition(reference.content, jumpText)
  if (found) {
    return focusReferenceRange(found.start, found.end, true)
  }
  activateMotifJumpHighlight(t('motifs.sourceChanged'))
  return true
}

async function jumpToMotifSourceExcerpt(excerpt: MotifExcerpt) {
  const reference = store.selectedReference
  if (!reference) return false
  const range = resolveMotifExcerptRange(reference.content, excerpt)
  if (range.start !== null && range.end !== null) {
    const nextQuery: Record<string, string | string[]> = {
      ...route.query,
      ref: reference.id,
      group: store.groupMode,
      motif_excerpt: excerpt.id,
      focus_start: String(range.start),
      focus_end: String(range.end),
    }
    delete nextQuery.action
    await router.replace({ name: 'library', query: nextQuery })
    return focusReferenceRange(range.start, range.end, true)
  }
  activateMotifJumpHighlight(t('motifs.sourceChanged'))
  return false
}

function previewMotifExcerptText(text: string, limit = 64): string {
  const compact = text.replace(/\s+/g, ' ').trim()
  const chars = Array.from(compact)
  return chars.length > limit ? `${chars.slice(0, limit).join('')}...` : compact
}

function motifRangeStatusLabel(status: 'matched' | 'moved' | 'missing'): string {
  if (status === 'matched') return t('motifs.rangeMatched')
  if (status === 'moved') return t('motifs.rangeMoved')
  return t('motifs.rangeMissing')
}
</script>

<template>
  <div class="flex h-full overflow-hidden bg-gray-50">
    <aside class="flex w-72 shrink-0 flex-col border-r border-gray-200 bg-white">
      <div class="border-b border-gray-200 p-4">
        <div class="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 class="text-xl font-bold">{{ t('library.title') }}</h2>
            <p class="mt-1 text-sm text-gray-500">
              {{ stats ? t('library.countSummary', { count: stats.total }) : t('library.countSummary', { count: store.references.length }) }}
            </p>
          </div>
          <button
            @click="createReference"
            class="rounded-lg bg-blue-600 px-3 py-2 text-sm text-white transition-colors hover:bg-blue-700"
          >
            {{ t('library.newReference') }}
          </button>
        </div>

        <div class="mb-4 rounded-xl bg-gray-100 p-1">
          <div class="grid grid-cols-2 gap-1">
            <button
              @click="setGroupMode('source')"
              :class="[
                'rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                store.groupMode === 'source'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-900',
              ]"
            >
              {{ t('library.groupBySource') }}
            </button>
            <button
              @click="setGroupMode('usage')"
              :class="[
                'rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                store.groupMode === 'usage'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-900',
              ]"
            >
              {{ t('library.groupByUsage') }}
            </button>
          </div>
        </div>

        <input
          v-model="searchInput"
          type="text"
          :placeholder="t('library.search')"
          class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div class="flex-1 overflow-y-auto">
        <div v-if="store.loading" class="p-4 text-sm text-gray-400">{{ t('library.loading') }}</div>
        <div v-else-if="store.error" class="p-4 text-sm text-red-500">{{ store.error }}</div>
        <div v-else-if="!currentGroups.length" class="p-4 text-sm text-gray-400">{{ t('library.noReferences') }}</div>
        <div v-else class="p-2">
          <button
            v-for="group in currentGroups"
            :key="group.key"
            @click="selectGroup(store.groupMode, group.key)"
            :class="[
              'mb-2 flex w-full items-center justify-between rounded-xl px-3 py-3 text-left transition-colors',
              (store.groupMode === 'source' ? store.activeSourceGroupKey : store.activeUsageGroupKey) === group.key
                ? 'bg-blue-50 text-blue-900 ring-1 ring-blue-200'
                : 'hover:bg-gray-100',
            ]"
          >
            <div class="min-w-0">
              <div class="truncate text-sm font-semibold">
                {{ store.groupMode === 'usage' ? usageLabel(group.key) : sourceGroupLabel(group.key) }}
              </div>
              <div class="mt-1 text-xs text-gray-500">
                {{ t('library.countSummary', { count: group.count }) }}
              </div>
            </div>
            <span class="ml-3 rounded-full bg-white/80 px-2 py-1 text-xs text-gray-500">
              {{ group.count }}
            </span>
          </button>
        </div>
      </div>
    </aside>

    <section class="flex w-[28rem] shrink-0 flex-col border-r border-gray-200 bg-white">
      <div class="border-b border-gray-200 px-5 py-4">
        <div class="text-xs font-semibold uppercase tracking-[0.2em] text-gray-400">
          {{ store.groupMode === 'usage' ? t('library.groupByUsage') : t('library.groupBySource') }}
        </div>
        <div class="mt-2 flex items-start justify-between gap-3">
          <div class="min-w-0">
            <h3 class="truncate text-lg font-bold text-gray-900">
              {{ activeGroupLabel || t('library.selectOrCreate') }}
            </h3>
            <p class="mt-1 text-sm text-gray-500">
              {{ activeGroup ? t('library.countSummary', { count: activeGroup.count }) : t('library.noReferences') }}
            </p>
          </div>
          <button
            v-if="store.groupMode === 'source' && activeGroup"
            @click="createReferenceInActiveSource"
            class="shrink-0 rounded-lg bg-stone-900 px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-stone-700"
          >
            {{ t('library.newInCurrentBook') }}
          </button>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-4">
        <div v-if="store.loading && !store.visibleReferences.length" class="p-4 text-sm text-gray-400">{{ t('library.loading') }}</div>
        <div v-else-if="store.error && !store.visibleReferences.length" class="p-4 text-sm text-red-500">{{ store.error }}</div>
        <div v-else-if="!store.visibleReferences.length" class="p-4 text-sm text-gray-400">{{ t('library.noReferences') }}</div>
        <div v-else class="space-y-3">
          <article
            v-for="reference in store.visibleReferences"
            :key="reference.id"
            @click="selectReference(reference.id)"
            :class="[
              'cursor-pointer rounded-2xl border p-4 transition-all',
              store.selectedRefId === reference.id
                ? 'border-blue-500 bg-blue-50 shadow-sm'
                : 'border-gray-200 bg-white hover:border-blue-300 hover:shadow-sm',
            ]"
          >
            <p class="line-clamp-5 whitespace-pre-wrap text-sm leading-6 text-gray-800">{{ preview(reference.content) }}</p>
            <div class="mt-3 flex flex-wrap items-center gap-2 text-xs text-gray-500">
              <span class="rounded-full bg-gray-100 px-2 py-1">
                {{ sourceGroupLabel(reference.source_title.trim() || EMPTY_SOURCE_GROUP_KEY) }}
              </span>
              <span class="rounded-full bg-amber-100 px-2 py-1 text-amber-700">
                {{ usageLabel(reference.usage_kind) }}
              </span>
              <span v-if="reference.source_author" class="truncate">— {{ reference.source_author }}</span>
            </div>
          </article>
        </div>
      </div>
    </section>

    <section ref="detailScrollRef" class="flex min-w-0 flex-1 flex-col overflow-y-auto bg-white">
      <div v-if="store.selectedReference" class="mx-auto w-full max-w-3xl p-8">
        <div class="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-gray-200 bg-gray-50 p-3">
          <div
            :class="[
              'text-sm',
              saveFailed ? 'text-red-600' : (saveNotice || motifJumpMessage || motifAttachNotice) ? 'text-blue-700' : 'text-gray-500',
            ]"
          >
            {{ copyNotice || motifJumpMessage || motifAttachNotice || saveNotice || t('library.copyHint') }}
          </div>
          <div class="flex gap-2">
            <button
              @click="copyReferenceContent"
              class="rounded-lg bg-white px-3 py-2 text-sm font-medium text-gray-700 ring-1 ring-gray-200 transition-colors hover:bg-gray-100"
            >
              {{ t('library.copyContent') }}
            </button>
            <button
              @click="copyReferenceFull"
              class="rounded-lg bg-gray-900 px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-gray-700"
            >
              {{ t('library.copyFull') }}
            </button>
          </div>
        </div>
        <div class="mb-6">
          <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('library.content') }}</label>
          <textarea
            ref="contentRef"
            data-testid="library-reference-content"
            v-model="store.selectedReference.content"
            @input="scheduleSave"
            @pointerup="handleContentPointerSettled"
            @mouseup="handleContentPointerSettled"
            @contextmenu="handleContentContextMenu"
            :class="[
              'min-h-[220px] w-full resize-none rounded-lg border border-gray-200 p-4 text-lg leading-relaxed focus:outline-none focus:ring-2 focus:ring-blue-500',
              motifHighlightActive ? 'motif-source-highlight' : '',
            ]"
            :placeholder="t('library.placeholders.content')"
          />
        </div>

        <section class="mb-6 rounded-2xl border border-teal-100 bg-white p-4 shadow-sm" data-testid="library-motif-anchors">
          <div class="mb-2 flex items-center justify-between gap-2">
            <h3 class="text-sm font-semibold text-gray-700">{{ t('motifs.sourceAnchors') }}</h3>
            <span class="rounded-full bg-teal-50 px-2 py-1 text-xs font-semibold text-teal-700">
              {{ sortedMotifSourceExcerpts.length }}
            </span>
          </div>
          <p class="mb-3 text-xs leading-5 text-gray-500">{{ t('motifs.sourceAnchorsHint') }}</p>
          <div v-if="motifSourceError" class="mb-2 rounded-lg bg-red-50 p-2 text-xs text-red-700">
            {{ motifSourceError }}
          </div>
          <div v-if="motifSourceLoading" class="rounded-xl bg-gray-50 p-3 text-sm text-gray-400">
            {{ t('common.loading') }}
          </div>
          <div v-else-if="!resolvedMotifSourceExcerpts.length" class="rounded-xl bg-gray-50 p-3 text-sm text-gray-400">
            {{ t('motifs.noSourceAnchors') }}
          </div>
          <div v-else class="space-y-2">
            <button
              v-for="item in resolvedMotifSourceExcerpts"
              :key="item.excerpt.id"
              type="button"
              :disabled="item.range.status === 'missing'"
              @click="jumpToMotifSourceExcerpt(item.excerpt)"
              :class="[
                'w-full rounded-2xl border p-3 text-left transition',
                activeMotifExcerptId === item.excerpt.id
                  ? 'border-teal-300 bg-teal-50/80 shadow-sm'
                  : 'border-gray-200 bg-white hover:border-teal-200 hover:bg-teal-50/40',
                item.range.status === 'missing' ? 'cursor-not-allowed opacity-70' : '',
              ]"
            >
              <p class="motif-anchor-preview text-sm leading-6 text-gray-800">
                {{ previewMotifExcerptText(item.excerpt.excerpt_text) }}
              </p>
              <div class="mt-2 flex flex-wrap gap-1.5">
                <span
                  v-for="name in item.excerpt.motif_names"
                  :key="`${item.excerpt.id}-${name}`"
                  class="rounded-full bg-teal-50 px-2 py-0.5 text-[11px] font-medium text-teal-800 ring-1 ring-teal-100"
                >
                  {{ name }}
                </span>
              </div>
              <div class="mt-2 flex items-center justify-between gap-2 text-[11px] text-gray-400">
                <span>{{ motifRangeStatusLabel(item.range.status) }}</span>
                <span v-if="item.range.status !== 'missing'" class="font-semibold text-teal-700">{{ t('motifs.locateAnchor') }}</span>
              </div>
            </button>
          </div>
        </section>

        <div class="mb-6 grid grid-cols-2 gap-4">
          <div>
            <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('library.sourceTitle') }}</label>
            <input
              v-model="store.selectedReference.source_title"
              @input="scheduleSave"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              :placeholder="t('library.placeholders.sourceTitle')"
            />
          </div>
          <div>
            <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('library.sourceAuthor') }}</label>
            <input
              v-model="store.selectedReference.source_author"
              @input="scheduleSave"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              :placeholder="t('library.placeholders.sourceAuthor')"
            />
          </div>
        </div>

        <div class="mb-6">
          <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('library.usageKind') }}</label>
          <select
            v-model="store.selectedReference.usage_kind"
            @change="scheduleSave"
            class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="style">{{ t('library.style') }}</option>
            <option value="imagery">{{ t('library.imagery') }}</option>
            <option value="structure">{{ t('library.structure') }}</option>
            <option value="rhetoric">{{ t('library.rhetoric') }}</option>
            <option value="diction">{{ t('library.diction') }}</option>
            <option value="reflection">{{ t('library.reflection') }}</option>
            <option value="setting">{{ t('library.setting') }}</option>
            <option value="technique">{{ t('library.technique') }}</option>
            <option value="other">{{ t('library.other') }}</option>
          </select>
        </div>

        <div class="mb-6">
          <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('library.personalNote') }}</label>
          <textarea
            v-model="store.selectedReference.personal_note"
            @input="scheduleSave"
            class="min-h-[100px] w-full resize-none rounded-lg border border-gray-200 p-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
            :placeholder="t('library.placeholders.personalNote')"
          />
        </div>

        <div class="flex items-center justify-between border-t border-gray-200 pt-4">
          <div class="text-xs text-gray-400">
            {{ t('library.createdAt') }} {{ store.selectedReference.created_at?.slice(0, 10) || '—' }}
          </div>
          <button
            @click="deleteSelectedReference"
            class="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600 transition-colors hover:bg-red-100"
          >
            {{ t('library.deleteReference') }}
          </button>
        </div>
      </div>
      <div v-else class="flex h-full items-center justify-center text-gray-400">
        {{ t('library.selectOrCreate') }}
      </div>
    </section>

    <div
      v-if="motifContextMenuOpen && motifAttachSelection"
      class="fixed z-[65] w-[180px] rounded-2xl border border-amber-100 bg-[#fffdf8] p-1.5 shadow-xl shadow-stone-900/15"
      :style="{ left: `${motifContextMenuX}px`, top: `${motifContextMenuY}px` }"
      data-testid="motif-context-menu"
    >
      <button
        class="w-full rounded-xl px-3 py-2 text-left text-sm font-semibold text-stone-800 transition hover:bg-amber-50"
        @mousedown.prevent
        @click="openMotifAttachFromContextMenu"
      >
        {{ t('motifs.contextMenuAdd') }}
      </button>
    </div>

    <div
      v-if="motifAttachOpen && motifAttachSelection"
      ref="motifAttachPanelRef"
      class="fixed z-[60] flex max-h-[min(80vh,560px)] w-[min(380px,calc(100vw-32px))] flex-col overflow-hidden rounded-3xl border border-amber-100 bg-[#fffdf8]/95 shadow-2xl shadow-stone-900/15 backdrop-blur"
      :style="{ left: `${motifAttachX}px`, top: `${motifAttachY}px` }"
      data-testid="motif-attach-panel"
    >
      <div
        class="flex cursor-move select-none items-start justify-between gap-3 border-b border-amber-100/70 px-4 py-3"
        data-testid="motif-attach-drag-handle"
        @pointerdown="startMotifAttachDrag"
      >
        <div>
          <p class="text-xs font-semibold uppercase tracking-[0.22em] text-teal-700">{{ t('motifs.attachTitle') }}</p>
          <p class="mt-1 text-xs text-stone-400">{{ t('motifs.attachSourceReference') }}</p>
        </div>
        <button @pointerdown.stop @click="closeMotifAttach" class="rounded-full px-2 py-1 text-stone-400 hover:bg-stone-100 hover:text-stone-700">×</button>
      </div>
      <div class="min-h-0 flex-1 overflow-y-auto px-4 py-3">
        <blockquote class="max-h-28 overflow-y-auto rounded-2xl bg-amber-50/70 px-3 py-2 text-sm leading-6 text-stone-700">
          {{ motifAttachSelection.text }}
        </blockquote>
        <div v-if="motifAttachExistingExcerptId" class="mt-2 rounded-xl bg-teal-50 px-3 py-2 text-xs text-teal-800">
          {{ t('motifs.attachExistingHint') }}
        </div>
        <div class="mt-3">
          <input
            v-model="motifAttachQuery"
            data-testid="motif-attach-input"
            class="w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm outline-none focus:border-teal-300 focus:ring-2 focus:ring-teal-100"
            :placeholder="t('motifs.attachPlaceholder')"
            @keydown="handleMotifAttachQueryKeydown"
          />
          <div v-if="motifSuggestions.length" class="mt-2 flex flex-wrap gap-1.5">
            <button
              v-for="motif in motifSuggestions"
              :key="motif.id"
              @click="addMotifAttachName(motif.name)"
              class="rounded-full bg-white px-2.5 py-1 text-xs text-stone-600 ring-1 ring-stone-200 transition hover:bg-teal-50 hover:text-teal-800"
            >
              {{ motif.name }}
            </button>
          </div>
        </div>
        <div v-if="motifAttachNames.length" class="mt-3" data-testid="motif-attach-selected-list">
          <div class="mb-1 text-xs font-semibold text-stone-500">{{ t('motifs.selectedMotifs') }}</div>
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="name in motifAttachNames"
              :key="name"
              data-testid="motif-attach-selected-chip"
              @click="removeMotifAttachName(name)"
              class="rounded-full bg-teal-700 px-2.5 py-1 text-xs text-white transition hover:bg-teal-800"
            >
              {{ name }} ×
            </button>
          </div>
        </div>
        <textarea
          v-model="motifAttachNote"
          rows="3"
          class="mt-3 w-full resize-none rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm leading-6 outline-none focus:border-teal-300 focus:ring-2 focus:ring-teal-100"
          :placeholder="t('motifs.attachNotePlaceholder')"
        />
        <div v-if="motifAttachError" class="mt-2 rounded-xl bg-rose-50 px-3 py-2 text-xs text-rose-700">
          {{ motifAttachError }}
        </div>
      </div>
      <div class="flex shrink-0 justify-end gap-2 border-t border-amber-100/70 bg-[#fffdf8]/95 px-4 py-3">
        <button @click="closeMotifAttach" class="rounded-xl bg-stone-100 px-3 py-2 text-sm text-stone-600 hover:bg-stone-200">
          {{ t('common.cancel') }}
        </button>
        <button
          @click="saveMotifAttachSelection"
          :disabled="motifAttachSaving || (!motifAttachExistingExcerptId && !motifAttachNames.length && !motifAttachQuery.trim())"
          class="rounded-xl bg-stone-900 px-3 py-2 text-sm font-semibold text-white hover:bg-stone-700 disabled:opacity-40"
        >
          {{ motifAttachSaving ? t('common.saving') : t('motifs.saveSelection') }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.line-clamp-5 {
  display: -webkit-box;
  -webkit-line-clamp: 5;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.motif-source-highlight::selection {
  background: rgba(252, 211, 77, 0.68);
  color: inherit;
}

.motif-anchor-preview {
  text-decoration-line: underline;
  text-decoration-style: dashed;
  text-decoration-color: rgba(13, 148, 136, 0.65);
  text-decoration-thickness: 1px;
  text-underline-offset: 4px;
}
</style>
