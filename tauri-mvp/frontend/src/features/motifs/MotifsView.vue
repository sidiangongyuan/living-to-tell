<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  motifsApi,
  type MotifExcerpt,
  type MotifEnrichmentDraft,
  type MotifGraph,
  type MotifGraphEdge,
  type MotifGraphNode,
  type MotifNode,
} from '../../api/motifs'
import { errorMessage, isHttpStatus } from '../../api/base'
import { settingsApi, type AiProfile } from '../../api/settings'
import { useI18n } from '../../i18n'
import ContextMenu from '../../components/ContextMenu.vue'
import PaneResizeHandle from '../../components/PaneResizeHandle.vue'
import { useResizablePane } from '../../composables/useResizablePane'
import { densityToLimit, filterMotifGraphByLimit, layoutMotifGraph } from './graphLayout'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const motifs = ref<MotifNode[]>([])
const homeGraph = ref<MotifGraph>({ nodes: [], edges: [] })
const localGraph = ref<MotifGraph>({ nodes: [], edges: [] })
const selectedMotifId = ref<string | null>(null)
const excerpts = ref<MotifExcerpt[]>([])
const query = ref('')
const density = ref(34)
const loading = ref(false)
const detailLoading = ref(false)
const error = ref('')
const notice = ref('')
const newMotifName = ref('')
const savingMotif = ref(false)
const detailError = ref('')
const formName = ref('')
const formAliases = ref('')
const formTags = ref('')
const formNote = ref('')
const formPinned = ref(false)
const aiProfiles = ref<AiProfile[]>([])
const enrichmentOpen = ref(false)
const enrichmentMotifId = ref<string | null>(null)
const enrichmentConcept = ref('')
const enrichmentDirection = ref('')
const enrichmentProfileId = ref('default')
const enrichmentIncludeExcerpts = ref(true)
const enrichmentRequestWebContext = ref(false)
const enrichmentGenerating = ref(false)
const enrichmentApplying = ref(false)
const enrichmentError = ref('')
const enrichmentDraft = ref<MotifEnrichmentDraft | null>(null)
const enrichmentNoteMode = ref<'append' | 'overwrite' | 'none'>('append')
const enrichmentApplyAliases = ref(true)
const enrichmentApplyTags = ref(true)
const motifListPane = useResizablePane({
  key: 'motifs:list',
  defaultSize: 260,
  minSize: 240,
  maxSize: 420,
})
const motifDetailPane = useResizablePane({
  key: 'motifs:detail',
  defaultSize: 440,
  minSize: 360,
  maxSize: 680,
  edge: 'start',
})
const deleteContextMenuOpen = ref(false)
const deleteContextMenuX = ref(0)
const deleteContextMenuY = ref(0)
const deleteContextTarget = ref<
  | { kind: 'motif'; id: string }
  | { kind: 'excerpt'; excerpt: MotifExcerpt }
  | null
>(null)

let searchTimer: number | null = null
let motifsLoadToken = 0
let homeGraphToken = 0
let motifDetailToken = 0

const selectedMotif = computed(() =>
  motifs.value.find((motif) => motif.id === selectedMotifId.value) ?? null
)

const homeLimit = computed(() => densityToLimit(density.value, motifs.value.length))
const visibleHomeGraph = computed(() =>
  filterMotifGraphByLimit(homeGraph.value, homeLimit.value, selectedMotifId.value)
)
const positionedHomeGraph = computed(() => layoutMotifGraph(visibleHomeGraph.value, { width: 1080, height: 620 }))
const positionedLocalGraph = computed(() => layoutMotifGraph(localGraph.value, { width: 620, height: 300 }))
const graphCountLabel = computed(() =>
  motifs.value.length
    ? t('motifs.graphShowing', { visible: visibleHomeGraph.value.nodes.length, total: motifs.value.length })
    : t('motifs.noGraphNodes')
)
const filteredMotifs = computed(() => motifs.value)
const localRelatedNodes = computed(() =>
  localGraph.value.nodes
    .filter((node) => !node.is_center)
    .map((node) => ({
      node,
      weight: localGraph.value.edges
        .filter((edge) => edge.source_id === node.id || edge.target_id === node.id)
        .reduce((total, edge) => total + edge.weight, 0),
    }))
    .sort((a, b) => b.weight - a.weight || b.node.excerpt_count - a.node.excerpt_count || a.node.name.localeCompare(b.node.name))
    .slice(0, 10)
)
const formAliasChips = computed(() => linesFrom(formAliases.value).slice(0, 8))
const formTagChips = computed(() => linesFrom(formTags.value).slice(0, 8))
const aiProfileOptions = computed(() => [
  { id: 'default', name: t('motifs.enrichDefaultProfile'), provider: '', model: '' },
  ...aiProfiles.value
    .filter((profile) => profile.enabled)
    .map((profile) => ({
      id: profile.id,
      name: profile.name,
      provider: profile.provider_name,
      model: profile.model,
    })),
])
const deleteContextMenuItems = computed(() => [{
  key: 'delete',
  label: deleteContextTarget.value?.kind === 'excerpt' ? t('motifs.removeFromMotif') : t('common.delete'),
  danger: true,
}])

const motifPalette = [
  { fill: '#f5d7b8', stroke: '#c4774e', halo: '#f7b47b', text: '#633018' },
  { fill: '#cfe6dd', stroke: '#2f7f72', halo: '#88d4c7', text: '#16463f' },
  { fill: '#d9ddf2', stroke: '#6874b8', halo: '#aeb8ee', text: '#2f376d' },
  { fill: '#f2c9d0', stroke: '#b05269', halo: '#ef9faf', text: '#642737' },
  { fill: '#e6dfbb', stroke: '#9a7c28', halo: '#e6c76d', text: '#514114' },
  { fill: '#d8d2ea', stroke: '#7f619e', halo: '#c3a8e5', text: '#49325f' },
  { fill: '#cddfe8', stroke: '#45758b', halo: '#93cadc', text: '#234657' },
  { fill: '#ded7ce', stroke: '#8a7160', halo: '#d2b39d', text: '#4f3b31' },
]

onMounted(async () => {
  void loadAiProfiles()
  await loadMotifs()
  applyRouteMotif()
})

watch(
  () => route.query.id,
  () => {
    applyRouteMotif()
  }
)

watch(query, () => {
  if (searchTimer) window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => {
    void loadMotifs()
  }, 220)
})

watch(selectedMotifId, async () => {
  syncFormFromSelected()
  await loadSelectedMotifDetail()
})

function applyRouteMotif() {
  const motifId = typeof route.query.id === 'string' ? route.query.id : ''
  if (motifId && motifs.value.some((motif) => motif.id === motifId)) {
    selectedMotifId.value = motifId
  }
}

function hashText(text: string): number {
  let hash = 0
  for (const char of text) {
    hash = (hash * 31 + char.charCodeAt(0)) >>> 0
  }
  return hash
}

function motifForNode(node: MotifGraphNode): MotifNode | undefined {
  return motifs.value.find((motif) => motif.id === node.id)
}

function paletteForNode(node: MotifGraphNode) {
  const motif = motifForNode(node)
  const key = motif?.tags[0] || motif?.aliases[0] || node.name
  return motifPalette[hashText(key) % motifPalette.length]
}

function edgeTouchesSelected(edge: MotifGraphEdge): boolean {
  return Boolean(selectedMotifId.value && (edge.source_id === selectedMotifId.value || edge.target_id === selectedMotifId.value))
}

function friendlyMotifError(e: unknown): string {
  if (isHttpStatus(e, 404)) return t('motifs.motifMissing')
  return errorMessage(e)
}

async function loadMotifs() {
  const token = ++motifsLoadToken
  loading.value = true
  error.value = ''
  detailError.value = ''
  try {
    const nextMotifs = await motifsApi.listMotifs(query.value, 1000)
    if (token !== motifsLoadToken) return
    motifs.value = nextMotifs
    if (!selectedMotifId.value || !motifs.value.some((motif) => motif.id === selectedMotifId.value)) {
      selectedMotifId.value = motifs.value[0]?.id ?? null
    } else {
      syncFormFromSelected()
    }
    await loadHomeGraph()
    await loadSelectedMotifDetail()
  } catch (e) {
    if (token !== motifsLoadToken) return
    error.value = friendlyMotifError(e)
  } finally {
    if (token === motifsLoadToken) {
      loading.value = false
    }
  }
}

async function loadHomeGraph() {
  const token = ++homeGraphToken
  try {
    const graph = await motifsApi.graph(query.value, Math.max(1, motifs.value.length || 80))
    if (token !== homeGraphToken) return
    homeGraph.value = graph
  } catch (e) {
    if (token !== homeGraphToken) return
    error.value = friendlyMotifError(e)
  }
}

async function loadSelectedMotifDetail() {
  const motifId = selectedMotifId.value
  const token = ++motifDetailToken
  if (!motifId) {
    excerpts.value = []
    localGraph.value = { nodes: [], edges: [] }
    detailLoading.value = false
    return
  }
  detailLoading.value = true
  detailError.value = ''
  try {
    const nextExcerpts = await motifsApi.listExcerpts(motifId)
    if (token !== motifDetailToken || selectedMotifId.value !== motifId) return
    const nextGraph = await motifsApi.localGraph(motifId)
    if (token !== motifDetailToken || selectedMotifId.value !== motifId) return
    excerpts.value = nextExcerpts
    localGraph.value = nextGraph
  } catch (e) {
    if (token !== motifDetailToken || selectedMotifId.value !== motifId) return
    excerpts.value = []
    localGraph.value = { nodes: [], edges: [] }
    if (isHttpStatus(e, 404)) {
      if (selectedMotifId.value === motifId) {
        selectedMotifId.value = motifs.value.find((motif) => motif.id !== motifId)?.id ?? null
      }
      notice.value = t('motifs.motifMissing')
      window.setTimeout(() => {
        if (notice.value === t('motifs.motifMissing')) notice.value = ''
      }, 2200)
    } else {
      detailError.value = friendlyMotifError(e)
    }
  } finally {
    if (token === motifDetailToken && selectedMotifId.value === motifId) {
      detailLoading.value = false
    }
  }
}

function syncFormFromSelected() {
  const motif = selectedMotif.value
  formName.value = motif?.name ?? ''
  formAliases.value = motif?.aliases.join('\n') ?? ''
  formTags.value = motif?.tags.join('\n') ?? ''
  formNote.value = motif?.note ?? ''
  formPinned.value = motif?.pinned ?? false
}

function linesFrom(text: string): string[] {
  return text.split(/\n+/).map((item) => item.trim()).filter(Boolean)
}

function mergeUniqueValues(current: string[], next: string[]): string[] {
  const result: string[] = []
  const seen = new Set<string>()
  for (const value of [...current, ...next]) {
    const clean = value.trim()
    const key = clean.toLocaleLowerCase()
    if (!clean || seen.has(key)) continue
    seen.add(key)
    result.push(clean)
  }
  return result
}

async function loadAiProfiles() {
  try {
    const result = await settingsApi.listAiProfiles()
    aiProfiles.value = result.profiles
    if (!aiProfileOptions.value.some((profile) => profile.id === enrichmentProfileId.value)) {
      enrichmentProfileId.value = 'default'
    }
  } catch {
    aiProfiles.value = []
  }
}

function resetEnrichmentDraft() {
  enrichmentDraft.value = null
  enrichmentError.value = ''
  enrichmentNoteMode.value = 'append'
  enrichmentApplyAliases.value = true
  enrichmentApplyTags.value = true
}

function openEnrichmentForSelected() {
  const motif = selectedMotif.value
  if (!motif) return
  enrichmentMotifId.value = motif.id
  enrichmentConcept.value = formName.value.trim() || motif.name
  enrichmentDirection.value = ''
  enrichmentIncludeExcerpts.value = true
  enrichmentRequestWebContext.value = false
  resetEnrichmentDraft()
  enrichmentOpen.value = true
  void loadAiProfiles()
}

function openEnrichmentForNewConcept() {
  const concept = newMotifName.value.trim()
  if (!concept) return
  enrichmentMotifId.value = null
  enrichmentConcept.value = concept
  enrichmentDirection.value = ''
  enrichmentIncludeExcerpts.value = false
  enrichmentRequestWebContext.value = false
  resetEnrichmentDraft()
  enrichmentOpen.value = true
  void loadAiProfiles()
}

function closeEnrichment() {
  if (enrichmentGenerating.value || enrichmentApplying.value) return
  enrichmentOpen.value = false
}

async function generateEnrichmentDraft() {
  const concept = enrichmentConcept.value.trim()
  if (!concept) {
    enrichmentError.value = t('motifs.enrichConceptRequired')
    return
  }
  enrichmentGenerating.value = true
  enrichmentError.value = ''
  enrichmentDraft.value = null
  try {
    enrichmentDraft.value = await motifsApi.generateEnrichmentDraft({
      motif_id: enrichmentMotifId.value,
      concept,
      direction: enrichmentDirection.value,
      include_excerpts: enrichmentIncludeExcerpts.value,
      request_web_context: enrichmentRequestWebContext.value,
      profile_id: enrichmentProfileId.value,
      cost_tier: 'strong',
    })
  } catch (e) {
    enrichmentError.value = friendlyMotifError(e)
  } finally {
    enrichmentGenerating.value = false
  }
}

function noteFromEnrichmentDraft(draft: MotifEnrichmentDraft): string {
  if (enrichmentNoteMode.value === 'none') return formNote.value
  if (enrichmentNoteMode.value === 'overwrite') return draft.note
  const current = formNote.value.trimEnd()
  return current ? `${current}\n\n${draft.note}` : draft.note
}

async function applyEnrichmentDraft() {
  const draft = enrichmentDraft.value
  if (!draft) return
  enrichmentApplying.value = true
  enrichmentError.value = ''
  try {
    if (enrichmentMotifId.value) {
      const aliases = enrichmentApplyAliases.value
        ? mergeUniqueValues(linesFrom(formAliases.value), draft.aliases)
        : linesFrom(formAliases.value)
      const tags = enrichmentApplyTags.value
        ? mergeUniqueValues(linesFrom(formTags.value), draft.tags)
        : linesFrom(formTags.value)
      const payload = {
        name: (formName.value.trim() || draft.concept).trim(),
        aliases,
        tags,
        note: noteFromEnrichmentDraft(draft),
        pinned: formPinned.value,
      }
      const updated = await motifsApi.updateMotif(enrichmentMotifId.value, payload)
      motifs.value = motifs.value.map((item) => item.id === updated.id ? updated : item)
      selectedMotifId.value = updated.id
      formName.value = updated.name
      formAliases.value = updated.aliases.join('\n')
      formTags.value = updated.tags.join('\n')
      formNote.value = updated.note
      formPinned.value = updated.pinned
    } else {
      const conceptName = enrichmentConcept.value.trim() || draft.concept
      const created = await motifsApi.createMotif({
        name: conceptName,
        aliases: enrichmentApplyAliases.value ? draft.aliases : [],
        tags: enrichmentApplyTags.value ? draft.tags : [],
        note: enrichmentNoteMode.value === 'none' ? '' : draft.note,
        pinned: false,
      })
      newMotifName.value = ''
      await loadMotifs()
      selectedMotifId.value = created.id
    }

    notice.value = t('motifs.enrichApplied')
    enrichmentOpen.value = false
    await loadHomeGraph()
    await loadSelectedMotifDetail()
  } catch (e) {
    enrichmentError.value = friendlyMotifError(e)
  } finally {
    enrichmentApplying.value = false
  }
}

async function createMotif() {
  const name = newMotifName.value.trim()
  if (!name) return
  error.value = ''
  try {
    const created = await motifsApi.createMotif({ name })
    newMotifName.value = ''
    await loadMotifs()
    selectedMotifId.value = created.id
    notice.value = t('motifs.created')
  } catch (e) {
    error.value = friendlyMotifError(e)
  }
}

async function saveSelectedMotif() {
  const motif = selectedMotif.value
  if (!motif || !formName.value.trim()) return
  savingMotif.value = true
  error.value = ''
  try {
    const updated = await motifsApi.updateMotif(motif.id, {
      name: formName.value,
      aliases: linesFrom(formAliases.value),
      tags: linesFrom(formTags.value),
      note: formNote.value,
      pinned: formPinned.value,
    })
    motifs.value = motifs.value.map((item) => item.id === updated.id ? updated : item)
    notice.value = t('motifs.saved')
    await loadHomeGraph()
  } catch (e) {
    error.value = friendlyMotifError(e)
  } finally {
    savingMotif.value = false
  }
}

async function deleteSelectedMotif() {
  const motif = selectedMotif.value
  if (!motif) return
  if (!confirm(t('motifs.deleteConfirm', { name: motif.name }))) return
  try {
    await motifsApi.deleteMotif(motif.id)
    selectedMotifId.value = null
    await loadMotifs()
  } catch (e) {
    error.value = friendlyMotifError(e)
  }
}

async function removeExcerptFromSelectedMotif(excerpt: MotifExcerpt) {
  const motif = selectedMotif.value
  if (!motif) return
  if (!confirm(t('motifs.removeFromMotifConfirm', { name: motif.name }))) return
  try {
    await motifsApi.unlinkMotifFromExcerpt(excerpt.id, motif.id)
    await loadMotifs()
  } catch (e) {
    detailError.value = friendlyMotifError(e)
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
  deleteContextMenuX.value = Math.max(12, Math.min(event.clientX + 8, window.innerWidth - 190))
  deleteContextMenuY.value = Math.max(12, Math.min(event.clientY + 8, window.innerHeight - 56))
  deleteContextMenuOpen.value = true
}

function handleDeleteContextMenuSelect(item: { key: string }) {
  const target = deleteContextTarget.value
  closeDeleteContextMenu()
  if (item.key !== 'delete' || !target) return
  if (target.kind === 'excerpt') {
    void removeExcerptFromSelectedMotif(target.excerpt)
    return
  }
  if (selectedMotifId.value === target.id) {
    void deleteSelectedMotif()
    return
  }
  selectedMotifId.value = target.id
  void deleteSelectedMotif()
}

function selectMotif(id: string) {
  selectedMotifId.value = id
}

function sourceLabel(excerpt: MotifExcerpt): string {
  return excerpt.source_current_title || excerpt.source_title_snapshot || t('motifs.unknownSource')
}

function relationLabel(edgeCount: number): string {
  return t('motifs.relationCount', { count: edgeCount })
}

function storeJumpExcerpt(excerpt: MotifExcerpt) {
  const payload = {
    excerptId: excerpt.id,
    text: excerpt.excerpt_text,
    start: excerpt.selection_start,
    end: excerpt.selection_end,
  }
  window.sessionStorage.setItem('motif:lastJump', JSON.stringify(payload))
}

async function jumpToSource(excerpt: MotifExcerpt) {
  if (!excerpt.source_exists) return
  storeJumpExcerpt(excerpt)
  if (excerpt.source_kind === 'article') {
    await router.push({
      name: 'articles',
      query: {
        id: excerpt.source_id,
        motif_excerpt: excerpt.id,
        ...(excerpt.selection_start !== null && excerpt.selection_end !== null
          ? {
              focus_start: String(excerpt.selection_start),
              focus_end: String(excerpt.selection_end),
            }
          : {}),
      },
    })
    return
  }
  await router.push({
    name: 'library',
    query: {
      ref: excerpt.source_id,
      motif_excerpt: excerpt.id,
      ...(excerpt.selection_start !== null && excerpt.selection_end !== null
        ? {
            focus_start: String(excerpt.selection_start),
            focus_end: String(excerpt.selection_end),
          }
        : {}),
    },
  })
}

function previewExcerpt(text: string): string {
  return text.trim().replace(/\s+/g, ' ')
}
</script>

<template>
  <div class="flex h-full overflow-hidden bg-[#f6f2ea] text-stone-900">
    <aside
      class="flex shrink-0 flex-col border-r border-stone-200 bg-[#fffdf8]"
      :style="motifListPane.paneStyle.value"
      data-testid="motifs-list-pane"
    >
      <div class="border-b border-stone-200 p-5">
        <div class="mb-4">
          <p class="text-xs font-semibold uppercase tracking-[0.22em] text-teal-700">{{ t('motifs.eyebrow') }}</p>
          <h1 class="mt-2 text-2xl font-semibold text-stone-950">{{ t('motifs.title') }}</h1>
        </div>
        <input
          v-model="query"
          class="w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm outline-none transition focus:border-teal-400 focus:ring-2 focus:ring-teal-100"
          :placeholder="t('motifs.search')"
        />
        <div class="mt-4 rounded-xl border border-stone-200 bg-white/80 p-3">
          <div class="mb-2 flex items-center justify-between text-xs text-stone-500">
            <span>{{ t('motifs.density') }}</span>
            <span>{{ graphCountLabel }}</span>
          </div>
          <input
            v-model.number="density"
            type="range"
            min="0"
            max="100"
            class="w-full accent-teal-700"
          />
        </div>
        <div class="mt-4 flex gap-2">
          <input
            v-model="newMotifName"
            class="min-w-0 flex-1 rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm outline-none focus:border-rose-300 focus:ring-2 focus:ring-rose-100"
            :placeholder="t('motifs.newPlaceholder')"
            @keydown.enter.prevent="createMotif"
          />
          <button
            @click="createMotif"
            :disabled="!newMotifName.trim()"
            class="rounded-xl bg-stone-900 px-3 py-2 text-sm font-semibold text-white transition hover:bg-stone-700 disabled:opacity-40"
          >
            {{ t('motifs.add') }}
          </button>
          <button
            @click="openEnrichmentForNewConcept"
            :disabled="!newMotifName.trim()"
            class="rounded-xl bg-teal-700 px-3 py-2 text-sm font-semibold text-white transition hover:bg-teal-800 disabled:opacity-40"
          >
            {{ t('motifs.enrichShort') }}
          </button>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-3">
        <div v-if="loading" class="p-4 text-sm text-stone-400">{{ t('common.loading') }}</div>
        <div v-else-if="!filteredMotifs.length" class="p-4 text-sm leading-6 text-stone-400">
          {{ t('motifs.empty') }}
        </div>
        <button
          v-for="motif in filteredMotifs"
          :key="motif.id"
          @click="selectMotif(motif.id)"
          @contextmenu="openDeleteContextMenu($event, { kind: 'motif', id: motif.id })"
          :class="[
            'mb-2 w-full rounded-xl border px-3 py-3 text-left transition',
            selectedMotifId === motif.id
              ? 'border-teal-300 bg-teal-50/80 shadow-sm'
              : 'border-transparent bg-white/70 hover:border-stone-200 hover:bg-white',
          ]"
        >
          <div class="flex items-center justify-between gap-3">
            <div class="truncate text-sm font-semibold text-stone-900">{{ motif.name }}</div>
            <span class="rounded-full bg-stone-100 px-2 py-1 text-xs text-stone-500">
              {{ motif.excerpt_count }}
            </span>
          </div>
          <div v-if="motif.aliases.length || motif.tags.length" class="mt-2 flex flex-wrap gap-1.5">
            <span
              v-for="label in [...motif.aliases, ...motif.tags].slice(0, 3)"
              :key="label"
              class="rounded-full bg-white px-2 py-0.5 text-xs text-stone-500 ring-1 ring-stone-100"
            >
              {{ label }}
            </span>
          </div>
        </button>
      </div>
    </aside>
    <PaneResizeHandle data-testid="motifs-list-resizer" @pointerdown="motifListPane.startResize" />

    <main class="flex min-w-0 flex-1 flex-col overflow-hidden">
      <div class="border-b border-stone-200 bg-[#fffdf8]/90 px-6 py-4">
        <div class="flex items-center justify-between gap-4">
          <div>
            <p class="text-sm text-stone-500">{{ t('motifs.subtitle') }}</p>
            <p class="mt-1 text-xs text-stone-400">{{ relationLabel(visibleHomeGraph.edges.length) }}</p>
          </div>
          <div class="flex items-center gap-2">
            <span v-if="notice" class="text-sm text-teal-700">{{ notice }}</span>
            <span v-if="error" class="text-sm text-red-600">{{ error }}</span>
          </div>
        </div>
      </div>

      <div class="flex min-h-0 flex-1 overflow-hidden">
        <section class="min-w-0 flex-1 overflow-hidden p-5">
          <div class="h-full rounded-[1.75rem] border border-amber-100 bg-[#fff9ed] p-3 shadow-sm">
            <svg viewBox="0 0 1080 620" class="h-full min-h-[520px] w-full overflow-visible" role="img" :aria-label="t('motifs.graphAria')">
              <defs>
                <linearGradient id="motif-paper-bg" x1="0" x2="1" y1="0" y2="1">
                  <stop offset="0%" stop-color="#fffaf0" />
                  <stop offset="58%" stop-color="#f6efdf" />
                  <stop offset="100%" stop-color="#efe5d3" />
                </linearGradient>
                <filter id="motif-soft-shadow" x="-30%" y="-30%" width="160%" height="160%">
                  <feDropShadow dx="0" dy="10" stdDeviation="10" flood-color="#3f3427" flood-opacity="0.14" />
                </filter>
              </defs>
              <rect width="1080" height="620" fill="url(#motif-paper-bg)" rx="26" />
              <g opacity="0.34">
                <circle cx="130" cy="96" r="1.5" fill="#b78257" />
                <circle cx="246" cy="168" r="1" fill="#5b8f84" />
                <circle cx="892" cy="112" r="1.6" fill="#b86c78" />
                <circle cx="808" cy="478" r="1.3" fill="#987bb2" />
                <circle cx="178" cy="505" r="1.1" fill="#557b93" />
                <circle cx="520" cy="80" r="1" fill="#9b7c29" />
                <circle cx="975" cy="332" r="1.1" fill="#557b93" />
              </g>
              <g opacity="0.18">
                <path d="M95 350 C265 230 388 420 538 300 S790 174 996 268" fill="none" stroke="#a9854e" stroke-width="1" />
                <path d="M118 190 C320 106 440 154 578 214 S770 378 966 168" fill="none" stroke="#6e938a" stroke-width="0.8" />
              </g>
              <line
                v-for="edge in positionedHomeGraph.edges"
                :key="`${edge.source_id}:${edge.target_id}`"
                :x1="edge.x1"
                :y1="edge.y1"
                :x2="edge.x2"
                :y2="edge.y2"
                :stroke-width="Math.min(6, 0.9 + edge.weight * 0.45)"
                :stroke="edgeTouchesSelected(edge) ? '#25756b' : '#b79b5f'"
                :stroke-opacity="edgeTouchesSelected(edge) ? 0.58 : 0.28"
                stroke-linecap="round"
              />
              <g
                v-for="node in positionedHomeGraph.nodes"
                :key="node.id"
                class="cursor-pointer"
                @click="selectMotif(node.id)"
              >
                <line
                  :x1="node.labelConnectorX1"
                  :y1="node.labelConnectorY1"
                  :x2="node.labelConnectorX2"
                  :y2="node.labelConnectorY2"
                  :stroke="selectedMotifId === node.id ? paletteForNode(node).stroke : '#cdbf9f'"
                  :stroke-opacity="selectedMotifId === node.id ? 0.55 : 0.28"
                  stroke-width="1"
                />
                <circle
                  :cx="node.x"
                  :cy="node.y"
                  :r="node.radius + 13"
                  :fill="paletteForNode(node).halo"
                  :opacity="selectedMotifId === node.id ? 0.28 : 0.08"
                />
                <circle
                  :cx="node.x"
                  :cy="node.y"
                  :r="node.radius"
                  :fill="paletteForNode(node).fill"
                  :stroke="selectedMotifId === node.id ? '#1d5c55' : paletteForNode(node).stroke"
                  :stroke-width="selectedMotifId === node.id ? 3 : 1.5"
                  filter="url(#motif-soft-shadow)"
                />
                <circle
                  :cx="node.x - node.radius * 0.25"
                  :cy="node.y - node.radius * 0.28"
                  :r="Math.max(4, node.radius * 0.22)"
                  fill="#fffdf8"
                  opacity="0.42"
                />
                <rect
                  :x="node.labelBoxX"
                  :y="node.labelBoxY"
                  :width="node.labelBoxWidth"
                  :height="node.labelBoxHeight"
                  rx="10"
                  fill="#fffdf8"
                  :fill-opacity="selectedMotifId === node.id ? 0.96 : 0.84"
                  :stroke="selectedMotifId === node.id ? paletteForNode(node).stroke : '#eadfcb'"
                  :stroke-opacity="selectedMotifId === node.id ? 0.8 : 0.55"
                />
                <text
                  :x="node.labelTextX"
                  :y="node.labelFirstLineY"
                  text-anchor="middle"
                  class="select-none text-[12px] font-semibold"
                  :fill="paletteForNode(node).text"
                >
                  <tspan
                    v-for="(line, index) in node.labelLines"
                    :key="`${node.id}-label-${index}`"
                    :x="node.labelTextX"
                    :dy="index === 0 ? 0 : 16"
                  >
                    {{ line }}
                  </tspan>
                </text>
              </g>
              <text
                v-if="!positionedHomeGraph.nodes.length"
                x="540"
                y="310"
                text-anchor="middle"
                class="fill-stone-400 text-sm"
              >
                {{ t('motifs.emptyGraph') }}
              </text>
            </svg>
          </div>
        </section>

        <PaneResizeHandle data-testid="motifs-detail-resizer" @pointerdown="motifDetailPane.startResize" />
        <aside
          class="min-w-0 shrink-0 overflow-y-auto border-l border-stone-200 bg-[#fffdf8]"
          :style="motifDetailPane.paneStyle.value"
          data-testid="motifs-detail-pane"
        >
          <div v-if="selectedMotif" class="p-6">
            <div class="mb-5">
              <div class="flex items-start justify-between gap-4">
                <div class="min-w-0">
                  <p class="text-xs font-semibold uppercase tracking-[0.2em] text-rose-700">{{ t('motifs.archive') }}</p>
                  <h2 class="mt-2 break-words text-2xl font-semibold leading-tight text-stone-950">{{ selectedMotif.name }}</h2>
                  <div class="mt-3 flex flex-wrap gap-2 text-xs text-stone-600">
                    <span class="rounded-full bg-stone-100 px-2.5 py-1">{{ t('motifs.excerptCount', { count: selectedMotif.excerpt_count }) }}</span>
                    <span class="rounded-full bg-stone-100 px-2.5 py-1">{{ t('motifs.localRelationCount', { count: localGraph.edges.length }) }}</span>
                    <span v-if="selectedMotif.tags.length" class="rounded-full bg-amber-50 px-2.5 py-1 text-amber-800">{{ selectedMotif.tags.length }} {{ t('motifs.tags') }}</span>
                  </div>
                </div>
                <div class="flex shrink-0 flex-col items-end gap-2">
                  <label class="flex items-center gap-2 rounded-full bg-stone-100 px-3 py-2 text-xs text-stone-600">
                    <input v-model="formPinned" type="checkbox" class="h-4 w-4 rounded border-stone-300 text-teal-700" />
                    {{ t('motifs.pinned') }}
                  </label>
                  <button
                    @click="openEnrichmentForSelected"
                    class="rounded-xl bg-teal-700 px-3 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-teal-800"
                  >
                    {{ t('motifs.enrichAction') }}
                  </button>
                </div>
              </div>
            </div>

            <div class="mb-5 rounded-2xl border border-amber-100 bg-[#fffaf0] p-4" data-testid="motifs-local-graph-card">
              <div class="mb-3 flex items-center justify-between gap-3">
                <div>
                  <h3 class="text-sm font-semibold text-stone-900">{{ t('motifs.localGraph') }}</h3>
                  <p class="mt-1 text-xs text-stone-500">{{ t('motifs.localGraphHint') }}</p>
                </div>
                <span class="shrink-0 rounded-full bg-white/80 px-2.5 py-1 text-xs text-stone-500">{{ localRelatedNodes.length }}</span>
              </div>
              <svg viewBox="0 0 620 300" class="h-[260px] w-full">
                <rect width="620" height="300" fill="#f8f1e4" rx="14" />
                <line
                  v-for="edge in positionedLocalGraph.edges"
                  :key="`local-${edge.source_id}:${edge.target_id}`"
                  :x1="edge.x1"
                  :y1="edge.y1"
                  :x2="edge.x2"
                  :y2="edge.y2"
                  :stroke-width="Math.min(4, 0.8 + edge.weight * 0.35)"
                  :stroke="edgeTouchesSelected(edge) ? '#25756b' : '#b79b5f'"
                  :stroke-opacity="edgeTouchesSelected(edge) ? 0.5 : 0.25"
                  stroke-linecap="round"
                />
                <g
                  v-for="node in positionedLocalGraph.nodes"
                  :key="`local-node-${node.id}`"
                  class="cursor-pointer"
                  @click="selectMotif(node.id)"
                >
                  <line
                    :x1="node.labelConnectorX1"
                    :y1="node.labelConnectorY1"
                    :x2="node.labelConnectorX2"
                    :y2="node.labelConnectorY2"
                    :stroke="node.is_center ? '#2f7f72' : '#cdbf9f'"
                    :stroke-opacity="node.is_center ? 0.5 : 0.32"
                    stroke-width="1"
                  />
                  <circle
                    :cx="node.x"
                    :cy="node.y"
                    :r="node.radius + 8"
                    :fill="paletteForNode(node).halo"
                    :opacity="node.is_center ? 0.24 : 0.1"
                  />
                  <circle
                    :cx="node.x"
                    :cy="node.y"
                    :r="node.radius"
                    :fill="node.is_center ? '#24625c' : paletteForNode(node).fill"
                    :stroke="node.is_center ? '#174b45' : paletteForNode(node).stroke"
                    :stroke-width="node.is_center ? 2.2 : 1.4"
                  />
                  <rect
                    :x="node.labelBoxX"
                    :y="node.labelBoxY"
                    :width="node.labelBoxWidth"
                    :height="node.labelBoxHeight"
                    rx="9"
                    fill="#fffdf8"
                    fill-opacity="0.88"
                    :stroke="node.is_center ? '#8ec9be' : '#eadfcb'"
                    stroke-opacity="0.7"
                  />
                  <text
                    :x="node.labelTextX"
                    :y="node.labelFirstLineY"
                    text-anchor="middle"
                    class="select-none text-[11px] font-semibold"
                    :fill="node.is_center ? '#174b45' : paletteForNode(node).text"
                  >
                    <tspan
                      v-for="(line, index) in node.labelLines"
                      :key="`local-label-${node.id}-${index}`"
                      :x="node.labelTextX"
                      :dy="index === 0 ? 0 : 15"
                    >
                      {{ line }}
                    </tspan>
                  </text>
                </g>
                <text
                  v-if="positionedLocalGraph.nodes.length <= 1"
                  x="310"
                  y="250"
                  text-anchor="middle"
                  class="fill-stone-400 text-xs"
                >
                  {{ t('motifs.noRelations') }}
                </text>
              </svg>
              <div v-if="localRelatedNodes.length" class="mt-3 flex flex-wrap gap-2">
                <button
                  v-for="item in localRelatedNodes"
                  :key="`local-chip-${item.node.id}`"
                  type="button"
                  @click="selectMotif(item.node.id)"
                  class="max-w-full rounded-full bg-white px-3 py-1.5 text-left text-xs font-medium text-stone-700 ring-1 ring-amber-100 transition hover:bg-teal-50 hover:text-teal-800"
                >
                  <span class="break-all">{{ item.node.name }}</span>
                  <span class="ml-1 text-stone-400">×{{ item.weight || 1 }}</span>
                </button>
              </div>
            </div>

            <div class="mb-5 rounded-2xl border border-stone-200 bg-white p-5" data-testid="motifs-detail-form">
              <label class="block text-sm font-medium text-stone-700">
                {{ t('motifs.name') }}
                <input v-model="formName" class="mt-1 w-full rounded-xl border border-stone-200 px-3 py-2.5 text-base outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-100" />
              </label>
              <label class="mt-4 block text-sm font-medium text-stone-700">
                {{ t('motifs.tags') }}
                <textarea v-model="formTags" rows="4" class="mt-1 min-h-[96px] w-full resize-y rounded-xl border border-stone-200 px-3 py-2 leading-6 outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-100" :placeholder="t('motifs.onePerLine')" />
              </label>
              <div v-if="formTagChips.length" class="mt-2 flex flex-wrap gap-1.5">
                <span v-for="item in formTagChips" :key="`form-tag-${item}`" class="rounded-full bg-amber-50 px-2 py-1 text-xs text-amber-800">{{ item }}</span>
              </div>
              <label class="mt-4 block text-sm font-medium text-stone-700">
                {{ t('motifs.aliases') }}
                <textarea v-model="formAliases" rows="4" class="mt-1 min-h-[96px] w-full resize-y rounded-xl border border-stone-200 px-3 py-2 leading-6 outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-100" :placeholder="t('motifs.onePerLine')" />
              </label>
              <div v-if="formAliasChips.length" class="mt-2 flex flex-wrap gap-1.5">
                <span v-for="item in formAliasChips" :key="`form-alias-${item}`" class="rounded-full bg-teal-50 px-2 py-1 text-xs text-teal-800">{{ item }}</span>
              </div>
              <label class="mt-4 block text-sm font-medium text-stone-700">
                {{ t('motifs.note') }}
                <textarea v-model="formNote" rows="14" class="mt-1 min-h-[320px] w-full resize-y rounded-xl border border-stone-200 bg-[#fffdf8] px-3 py-3 text-sm leading-7 outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-100" :placeholder="t('motifs.notePlaceholder')" />
              </label>
              <div class="mt-4 flex justify-between gap-3">
                <button
                  @click="deleteSelectedMotif"
                  @contextmenu="openDeleteContextMenu($event, { kind: 'motif', id: selectedMotif.id })"
                  class="rounded-xl bg-rose-50 px-4 py-2 text-sm font-semibold text-rose-700 hover:bg-rose-100"
                >
                  {{ t('common.delete') }}
                </button>
                <button
                  @click="saveSelectedMotif"
                  :disabled="savingMotif || !formName.trim()"
                  class="rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white hover:bg-stone-700 disabled:opacity-40"
                >
                  {{ savingMotif ? t('common.saving') : t('common.save') }}
                </button>
              </div>
            </div>

            <section>
              <div class="mb-3 flex items-center justify-between">
                <h3 class="text-lg font-semibold">{{ t('motifs.excerpts') }}</h3>
                <span class="text-sm text-stone-400">{{ excerpts.length }}</span>
              </div>
              <div v-if="detailError" class="mb-3 rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {{ detailError }}
              </div>
              <div v-if="detailLoading" class="rounded-xl bg-white p-4 text-sm text-stone-400">
                {{ t('common.loading') }}
              </div>
              <div v-else-if="!excerpts.length" class="rounded-xl border border-dashed border-stone-200 bg-white/70 p-5 text-sm leading-6 text-stone-400">
                {{ t('motifs.noExcerpts') }}
              </div>
              <article
                v-for="excerpt in excerpts"
                :key="excerpt.id"
                @contextmenu="openDeleteContextMenu($event, { kind: 'excerpt', excerpt })"
                class="mb-3 rounded-2xl border border-stone-200 bg-white p-4 shadow-sm"
              >
                <p class="whitespace-pre-wrap text-base leading-8 text-stone-850">{{ previewExcerpt(excerpt.excerpt_text) }}</p>
                <p v-if="excerpt.note" class="mt-3 rounded-xl bg-teal-50/70 px-3 py-2 text-sm leading-6 text-teal-900">{{ excerpt.note }}</p>
                <div class="mt-3 flex flex-wrap gap-1.5">
                  <span
                    v-for="name in excerpt.motif_names"
                    :key="`${excerpt.id}-${name}`"
                    class="rounded-full bg-stone-100 px-2 py-1 text-xs text-stone-600"
                  >
                    {{ name }}
                  </span>
                </div>
                <div class="mt-4 flex items-center justify-between gap-3 border-t border-stone-100 pt-3">
                  <div class="min-w-0 text-xs text-stone-500">
                    <span :class="excerpt.source_exists ? 'text-stone-500' : 'text-rose-600'">
                      {{ excerpt.source_exists ? sourceLabel(excerpt) : t('motifs.sourceMissing') }}
                    </span>
                  </div>
                  <div class="flex gap-2">
                    <button
                      @click="jumpToSource(excerpt)"
                      :disabled="!excerpt.source_exists"
                      class="rounded-xl bg-teal-700 px-3 py-2 text-xs font-semibold text-white transition hover:bg-teal-800 disabled:bg-stone-200 disabled:text-stone-400"
                    >
                      {{ t('motifs.openSource') }}
                    </button>
                    <button @click="removeExcerptFromSelectedMotif(excerpt)" class="rounded-xl bg-stone-100 px-3 py-2 text-xs font-semibold text-stone-600 hover:bg-stone-200">
                      {{ t('motifs.removeFromMotif') }}
                    </button>
                  </div>
                </div>
              </article>
            </section>
          </div>

          <div v-else class="flex h-full items-center justify-center p-8 text-center text-sm leading-6 text-stone-400">
            {{ t('motifs.selectHint') }}
          </div>
        </aside>
      </div>
    </main>
    <ContextMenu
      :open="deleteContextMenuOpen"
      :x="deleteContextMenuX"
      :y="deleteContextMenuY"
      :items="deleteContextMenuItems"
      @close="closeDeleteContextMenu"
      @select="handleDeleteContextMenuSelect"
    />
    <div
      v-if="enrichmentOpen"
      class="fixed inset-0 z-50 flex items-center justify-center bg-stone-950/30 px-4 py-6"
      @click.self="closeEnrichment"
    >
      <section class="flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-stone-200 bg-[#fffdf8] shadow-2xl">
        <header class="border-b border-stone-200 px-5 py-4">
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.22em] text-teal-700">{{ t('motifs.enrichEyebrow') }}</p>
              <h2 class="mt-1 text-xl font-semibold text-stone-950">{{ t('motifs.enrichTitle') }}</h2>
              <p class="mt-1 text-sm leading-6 text-stone-500">{{ t('motifs.enrichSubtitle') }}</p>
            </div>
            <button
              @click="closeEnrichment"
              class="rounded-full px-3 py-1 text-lg text-stone-400 hover:bg-stone-100 hover:text-stone-700"
            >
              ×
            </button>
          </div>
        </header>

        <div class="min-h-0 flex-1 overflow-y-auto p-5">
          <div class="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
            <section class="rounded-2xl border border-stone-200 bg-white p-4">
              <label class="block text-sm font-medium text-stone-700">
                {{ t('motifs.enrichConcept') }}
                <input
                  v-model="enrichmentConcept"
                  class="mt-1 w-full rounded-xl border border-stone-200 px-3 py-2 outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-100"
                  :placeholder="t('motifs.enrichConceptPlaceholder')"
                />
              </label>
              <label class="mt-3 block text-sm font-medium text-stone-700">
                {{ t('motifs.enrichDirection') }}
                <textarea
                  v-model="enrichmentDirection"
                  rows="3"
                  class="mt-1 w-full resize-none rounded-xl border border-stone-200 px-3 py-2 leading-6 outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-100"
                  :placeholder="t('motifs.enrichDirectionPlaceholder')"
                />
              </label>
              <label class="mt-3 block text-sm font-medium text-stone-700">
                {{ t('motifs.enrichProfile') }}
                <select
                  v-model="enrichmentProfileId"
                  class="mt-1 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-100"
                >
                  <option v-for="profile in aiProfileOptions" :key="profile.id" :value="profile.id">
                    {{ profile.name }}{{ profile.model ? ` · ${profile.model}` : '' }}
                  </option>
                </select>
              </label>
              <div class="mt-4 space-y-3 rounded-xl bg-stone-50 p-3">
                <label class="flex items-start gap-2 text-sm text-stone-700">
                  <input v-model="enrichmentIncludeExcerpts" type="checkbox" class="mt-1 h-4 w-4 rounded border-stone-300 text-teal-700" />
                  <span>
                    <span class="font-medium">{{ t('motifs.enrichIncludeExcerpts') }}</span>
                    <span class="block text-xs leading-5 text-stone-500">{{ t('motifs.enrichIncludeExcerptsHint') }}</span>
                  </span>
                </label>
                <label class="flex items-start gap-2 text-sm text-stone-700">
                  <input v-model="enrichmentRequestWebContext" type="checkbox" class="mt-1 h-4 w-4 rounded border-stone-300 text-teal-700" />
                  <span>
                    <span class="font-medium">{{ t('motifs.enrichRequestWeb') }}</span>
                    <span class="block text-xs leading-5 text-stone-500">{{ t('motifs.enrichRequestWebHint') }}</span>
                  </span>
                </label>
              </div>
              <button
                @click="generateEnrichmentDraft"
                :disabled="enrichmentGenerating || !enrichmentConcept.trim()"
                class="mt-4 w-full rounded-xl bg-stone-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-stone-700 disabled:opacity-40"
              >
                {{ enrichmentGenerating ? t('motifs.enrichGenerating') : t('motifs.enrichGenerate') }}
              </button>
              <div v-if="enrichmentError" class="mt-3 rounded-xl bg-rose-50 px-3 py-2 text-sm leading-6 text-rose-700">
                {{ enrichmentError }}
              </div>
            </section>

            <section class="rounded-2xl border border-stone-200 bg-white p-4">
              <div v-if="!enrichmentDraft" class="flex min-h-[360px] items-center justify-center rounded-xl border border-dashed border-stone-200 bg-stone-50 px-6 text-center text-sm leading-6 text-stone-400">
                {{ t('motifs.enrichEmptyPreview') }}
              </div>
              <div v-else>
                <div class="mb-3 flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <p class="text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">{{ t('motifs.enrichDraft') }}</p>
                    <h3 class="mt-1 truncate text-lg font-semibold text-stone-950">{{ enrichmentDraft.title }}</h3>
                    <p class="mt-1 text-xs text-stone-500">
                      {{ enrichmentDraft.provider || 'AI' }} · {{ enrichmentDraft.model || t('motifs.enrichUnknownModel') }} · {{ enrichmentDraft.elapsed_ms }}ms
                    </p>
                  </div>
                </div>
                <div class="max-h-[420px] overflow-y-auto rounded-xl bg-[#fffaf0] p-4 text-sm leading-7 text-stone-800 whitespace-pre-wrap">
                  {{ enrichmentDraft.note }}
                </div>
                <div v-if="enrichmentDraft.aliases.length || enrichmentDraft.tags.length" class="mt-4 grid gap-3 sm:grid-cols-2">
                  <div>
                    <div class="mb-1 text-xs font-semibold text-stone-500">{{ t('motifs.aliases') }}</div>
                    <div class="flex flex-wrap gap-1.5">
                      <span v-for="item in enrichmentDraft.aliases" :key="`alias-${item}`" class="rounded-full bg-teal-50 px-2 py-1 text-xs text-teal-800">{{ item }}</span>
                    </div>
                  </div>
                  <div>
                    <div class="mb-1 text-xs font-semibold text-stone-500">{{ t('motifs.tags') }}</div>
                    <div class="flex flex-wrap gap-1.5">
                      <span v-for="item in enrichmentDraft.tags" :key="`tag-${item}`" class="rounded-full bg-amber-50 px-2 py-1 text-xs text-amber-800">{{ item }}</span>
                    </div>
                  </div>
                </div>
                <div v-if="enrichmentDraft.related_suggestions.length" class="mt-4">
                  <div class="mb-1 text-xs font-semibold text-stone-500">{{ t('motifs.enrichRelatedSuggestions') }}</div>
                  <div class="flex flex-wrap gap-1.5">
                    <span v-for="item in enrichmentDraft.related_suggestions" :key="`related-${item}`" class="rounded-full bg-stone-100 px-2 py-1 text-xs text-stone-600">{{ item }}</span>
                  </div>
                  <p class="mt-2 text-xs leading-5 text-stone-400">{{ t('motifs.enrichRelatedHint') }}</p>
                </div>
                <div v-if="enrichmentDraft.source_hints.length" class="mt-4 rounded-xl bg-stone-50 p-3">
                  <div class="mb-2 text-xs font-semibold text-stone-500">{{ t('motifs.enrichSourceHints') }}</div>
                  <div v-for="hint in enrichmentDraft.source_hints" :key="`${hint.title}-${hint.url || hint.note}`" class="mb-2 last:mb-0">
                    <a v-if="hint.url" :href="hint.url" target="_blank" rel="noreferrer" class="text-sm font-medium text-teal-700 hover:text-teal-900">{{ hint.title }}</a>
                    <p v-else class="text-sm font-medium text-stone-700">{{ hint.title }}</p>
                    <p v-if="hint.note" class="mt-0.5 text-xs leading-5 text-stone-500">{{ hint.note }}</p>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </div>

        <footer class="border-t border-stone-200 bg-white px-5 py-4">
          <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div class="flex flex-wrap gap-3 text-sm text-stone-600">
              <label class="flex items-center gap-2">
                <input v-model="enrichmentNoteMode" type="radio" value="append" class="text-teal-700" />
                {{ t('motifs.enrichAppendNote') }}
              </label>
              <label class="flex items-center gap-2">
                <input v-model="enrichmentNoteMode" type="radio" value="overwrite" class="text-teal-700" />
                {{ t('motifs.enrichOverwriteNote') }}
              </label>
              <label class="flex items-center gap-2">
                <input v-model="enrichmentNoteMode" type="radio" value="none" class="text-teal-700" />
                {{ t('motifs.enrichSkipNote') }}
              </label>
              <label class="flex items-center gap-2">
                <input v-model="enrichmentApplyAliases" type="checkbox" class="rounded border-stone-300 text-teal-700" />
                {{ t('motifs.enrichMergeAliases') }}
              </label>
              <label class="flex items-center gap-2">
                <input v-model="enrichmentApplyTags" type="checkbox" class="rounded border-stone-300 text-teal-700" />
                {{ t('motifs.enrichMergeTags') }}
              </label>
            </div>
            <div class="flex justify-end gap-2">
              <button @click="closeEnrichment" class="rounded-xl bg-stone-100 px-4 py-2 text-sm font-semibold text-stone-600 hover:bg-stone-200">
                {{ t('common.cancel') }}
              </button>
              <button
                @click="applyEnrichmentDraft"
                :disabled="!enrichmentDraft || enrichmentApplying"
                class="rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-40"
              >
                {{ enrichmentApplying ? t('common.saving') : (enrichmentMotifId ? t('motifs.enrichApplyExisting') : t('motifs.enrichCreateMotif')) }}
              </button>
            </div>
          </div>
        </footer>
      </section>
    </div>
  </div>
</template>
