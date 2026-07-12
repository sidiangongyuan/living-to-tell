<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  motifsApi,
  type MotifExcerpt,
  type MotifEnrichmentDraft,
  type MotifGraph,
  type MotifGraphEdge,
  type MotifGraphNode,
  type MotifNode,
  type MotifProfile,
  type MotifReferenceCandidate,
} from '../../api/motifs'
import { errorMessage, isHttpStatus } from '../../api/base'
import { aiJobsApi, type AiJobSnapshot } from '../../api/aiJobs'
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
const formProfile = ref<MotifProfile>(emptyMotifProfile())
const formPinned = ref(false)
const profileDrawerOpen = ref(false)
const profileEditorOpen = ref(false)
const chipEditorOpen = ref(false)
const chipEditorKind = ref<'tags' | 'aliases'>('tags')
const chipEditorText = ref('')
const aiProfiles = ref<AiProfile[]>([])
const defaultAiProfileId = ref<string | null>(null)
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
const enrichmentProfileMode = ref<'merge' | 'overwrite' | 'none'>('merge')
const enrichmentApplyAliases = ref(true)
const enrichmentApplyTags = ref(true)
const enrichmentApplyReferenceKeys = ref<string[]>([])
const enrichmentDraftTargetKey = ref<string | null>(null)
const activeEnrichmentJobId = ref<string | null>(null)
const activeEnrichmentJob = ref<AiJobSnapshot | null>(null)
const enrichmentReconnectCount = ref(0)
const enrichmentReconnectMessage = ref('')
let enrichmentPollingTimer: number | null = null
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
const sourceAnchorPickerGroup = ref<MotifSourceAnchorGroup | null>(null)

let searchTimer: number | null = null
let motifsLoadToken = 0
let homeGraphToken = 0
let motifDetailToken = 0

interface MotifSourceAnchorGroup {
  key: string
  sourceKind: 'article' | 'reference'
  sourceId: string
  label: string
  exists: boolean
  excerpts: MotifExcerpt[]
}

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
const sourceAnchorGroups = computed<MotifSourceAnchorGroup[]>(() => {
  const groups = new Map<string, MotifSourceAnchorGroup>()
  for (const excerpt of excerpts.value) {
    const key = `${excerpt.source_kind}:${excerpt.source_id}`
    const existing = groups.get(key)
    if (existing) {
      existing.excerpts.push(excerpt)
      existing.exists = existing.exists || excerpt.source_exists
      continue
    }
    groups.set(key, {
      key,
      sourceKind: excerpt.source_kind,
      sourceId: excerpt.source_id,
      label: sourceLabel(excerpt),
      exists: excerpt.source_exists,
      excerpts: [excerpt],
    })
  }
  return [...groups.values()]
    .map((group) => ({
      ...group,
      excerpts: [...group.excerpts].sort((a, b) => {
        const aStart = a.selection_start ?? Number.MAX_SAFE_INTEGER
        const bStart = b.selection_start ?? Number.MAX_SAFE_INTEGER
        if (aStart !== bStart) return aStart - bStart
        return a.created_at?.localeCompare(b.created_at ?? '') ?? 0
      }),
    }))
    .sort((a, b) => a.label.localeCompare(b.label))
})
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
const profileHasContent = computed(() => hasProfileContent(formProfile.value))
const formDirty = computed(() => {
  const motif = selectedMotif.value
  if (!motif) return false
  return formName.value.trim() !== motif.name
    || JSON.stringify(linesFrom(formAliases.value)) !== JSON.stringify(motif.aliases)
    || JSON.stringify(linesFrom(formTags.value)) !== JSON.stringify(motif.tags)
    || formNote.value !== motif.note
    || JSON.stringify(normalizeProfile(formProfile.value)) !== JSON.stringify(normalizeProfile(motif.profile))
    || formPinned.value !== motif.pinned
})
const aiProfileOptions = computed(() => [
  ...(defaultAiProfileId.value ? [{ id: 'default', name: t('motifs.enrichDefaultProfile'), provider: '', model: '' }] : []),
  ...aiProfiles.value
    .filter((profile) => profile.enabled)
    .map((profile) => ({
      id: profile.id,
      name: profile.name,
      provider: profile.provider_name,
      model: profile.model,
    })),
])
const enrichmentCurrentTargetKey = computed(() =>
  enrichmentTargetKey(enrichmentMotifId.value)
)
const enrichmentDraftMatchesTarget = computed(() =>
  !enrichmentDraft.value
    || !enrichmentDraftTargetKey.value
    || enrichmentDraftTargetKey.value === enrichmentCurrentTargetKey.value
)
const enrichmentApplyDisabled = computed(() =>
  !enrichmentDraft.value || enrichmentApplying.value || !enrichmentDraftMatchesTarget.value
)
const enrichmentWillApplyToExisting = computed(() =>
  Boolean(enrichmentMotifId.value || findMotifByName(enrichmentConcept.value))
)
const activeEnrichmentJobIsRunning = computed(() =>
  Boolean(activeEnrichmentJob.value && !ENRICHMENT_JOB_TERMINAL.has(activeEnrichmentJob.value.status))
)
const activeEnrichmentJobCanClear = computed(() =>
  Boolean(activeEnrichmentJob.value && ENRICHMENT_JOB_TERMINAL.has(activeEnrichmentJob.value.status))
)
const activeEnrichmentJobTitle = computed(() => {
  const job = activeEnrichmentJob.value
  if (!job) return ''
  if (job.status === 'succeeded') return t('motifs.enrichJobDone', { concept: job.concept })
  if (job.status === 'failed') return t('motifs.enrichJobFailed', { concept: job.concept })
  if (job.status === 'cancelled') return t('motifs.enrichJobCancelled', { concept: job.concept })
  return t('motifs.enrichJobRunning', { concept: job.concept })
})
const activeEnrichmentJobDetail = computed(() => {
  const job = activeEnrichmentJob.value
  if (!job) return ''
  if (enrichmentReconnectMessage.value) return enrichmentReconnectMessage.value
  if (job.status === 'failed' || job.status === 'cancelled') return job.error
  return `${job.stage_label} · ${formatElapsed(job.elapsed_ms)}`
})
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

type MotifProfileListField =
  | 'writing_functions'
  | 'scene_triggers'
  | 'character_signals'
  | 'imagery_translations'
  | 'short_examples'
  | 'misuse_warnings'
  | 'micro_exercises'

const ENRICHMENT_JOB_TERMINAL = new Set(['succeeded', 'failed', 'cancelled'])

onMounted(async () => {
  void loadAiProfiles()
  await loadMotifs()
  applyRouteMotif()
})

onUnmounted(() => {
  stopEnrichmentPolling()
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
  formProfile.value = normalizeProfile(motif?.profile)
  formPinned.value = motif?.pinned ?? false
  profileDrawerOpen.value = false
  profileEditorOpen.value = false
}

function linesFrom(text: string): string[] {
  return text.split(/\n+/).map((item) => item.trim()).filter(Boolean)
}

function emptyMotifProfile(): MotifProfile {
  return {
    definition: '',
    core_tension: '',
    writing_functions: [],
    scene_triggers: [],
    character_signals: [],
    imagery_translations: [],
    short_examples: [],
    misuse_warnings: [],
    micro_exercises: [],
    source_hints: [],
  }
}

function normalizeText(value: unknown): string {
  return String(value ?? '').trim()
}

function normalizeList(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return mergeUniqueValues([], value.map((item) => normalizeText(item)).filter(Boolean))
}

function normalizeProfile(profile: Partial<MotifProfile> | null | undefined): MotifProfile {
  const raw = profile ?? {}
  return {
    definition: normalizeText(raw.definition),
    core_tension: normalizeText(raw.core_tension),
    writing_functions: normalizeList(raw.writing_functions),
    scene_triggers: normalizeList(raw.scene_triggers),
    character_signals: normalizeList(raw.character_signals),
    imagery_translations: normalizeList(raw.imagery_translations),
    short_examples: normalizeList(raw.short_examples),
    misuse_warnings: normalizeList(raw.misuse_warnings),
    micro_exercises: normalizeList(raw.micro_exercises),
    source_hints: Array.isArray(raw.source_hints)
      ? raw.source_hints
          .map((hint) => ({
            title: normalizeText(hint?.title),
            url: normalizeText(hint?.url) || null,
            note: normalizeText(hint?.note),
          }))
          .filter((hint) => hint.title || hint.note)
      : [],
  }
}

function hasProfileContent(profile: Partial<MotifProfile> | null | undefined): boolean {
  const clean = normalizeProfile(profile)
  return Boolean(
    clean.definition
      || clean.core_tension
      || clean.writing_functions.length
      || clean.scene_triggers.length
      || clean.character_signals.length
      || clean.imagery_translations.length
      || clean.short_examples.length
      || clean.misuse_warnings.length
      || clean.micro_exercises.length
      || clean.source_hints.length
  )
}

function mergeSourceHints(current: MotifProfile['source_hints'], next: MotifProfile['source_hints']) {
  const result: MotifProfile['source_hints'] = []
  const seen = new Set<string>()
  for (const hint of [...current, ...next]) {
    const clean = {
      title: normalizeText(hint.title),
      url: normalizeText(hint.url) || null,
      note: normalizeText(hint.note),
    }
    const key = `${clean.title}|${clean.url || ''}|${clean.note}`.toLocaleLowerCase()
    if ((!clean.title && !clean.note) || seen.has(key)) continue
    seen.add(key)
    result.push(clean)
  }
  return result
}

function mergeProfiles(current: MotifProfile, next: MotifProfile, mode: 'merge' | 'overwrite' | 'none'): MotifProfile {
  if (mode === 'none') return normalizeProfile(current)
  const cleanCurrent = normalizeProfile(current)
  const cleanNext = normalizeProfile(next)
  if (mode === 'overwrite') return cleanNext
  return {
    definition: cleanCurrent.definition || cleanNext.definition,
    core_tension: cleanCurrent.core_tension || cleanNext.core_tension,
    writing_functions: mergeUniqueValues(cleanCurrent.writing_functions, cleanNext.writing_functions),
    scene_triggers: mergeUniqueValues(cleanCurrent.scene_triggers, cleanNext.scene_triggers),
    character_signals: mergeUniqueValues(cleanCurrent.character_signals, cleanNext.character_signals),
    imagery_translations: mergeUniqueValues(cleanCurrent.imagery_translations, cleanNext.imagery_translations),
    short_examples: mergeUniqueValues(cleanCurrent.short_examples, cleanNext.short_examples),
    misuse_warnings: mergeUniqueValues(cleanCurrent.misuse_warnings, cleanNext.misuse_warnings),
    micro_exercises: mergeUniqueValues(cleanCurrent.micro_exercises, cleanNext.micro_exercises),
    source_hints: mergeSourceHints(cleanCurrent.source_hints, cleanNext.source_hints),
  }
}

function normalizedMotifName(name: string): string {
  return name.trim().toLocaleLowerCase()
}

function motifNamesEqual(left: string, right: string): boolean {
  return normalizedMotifName(left) === normalizedMotifName(right)
}

function findMotifByName(name: string): MotifNode | null {
  const clean = normalizedMotifName(name)
  if (!clean) return null
  return motifs.value.find((motif) => normalizedMotifName(motif.name) === clean) ?? null
}

function upsertMotifInList(motif: MotifNode) {
  const index = motifs.value.findIndex((item) => item.id === motif.id)
  if (index >= 0) {
    motifs.value = motifs.value.map((item) => item.id === motif.id ? motif : item)
  } else {
    motifs.value = [motif, ...motifs.value]
  }
}

async function resolveMotifByName(name: string): Promise<MotifNode | null> {
  const local = findMotifByName(name)
  if (local) return local
  const clean = normalizedMotifName(name)
  if (!clean) return null
  try {
    const candidates = await motifsApi.listMotifs(name.trim(), 1000)
    return candidates.find((motif) => normalizedMotifName(motif.name) === clean) ?? null
  } catch {
    return null
  }
}

function enrichmentTargetKey(motifId: string | null): string {
  if (motifId) return `motif:${motifId}`
  return 'new'
}

function profileListText(field: MotifProfileListField): string {
  return formProfile.value[field].join('\n')
}

function inputValue(event: Event): string {
  return (event.target as HTMLInputElement | HTMLTextAreaElement).value
}

function setProfileList(field: MotifProfileListField, value: string) {
  formProfile.value = {
    ...formProfile.value,
    [field]: linesFrom(value),
  }
}

function removeChip(kind: 'tags' | 'aliases', value: string) {
  const next = (kind === 'tags' ? linesFrom(formTags.value) : linesFrom(formAliases.value))
    .filter((item) => item !== value)
  if (kind === 'tags') {
    formTags.value = next.join('\n')
  } else {
    formAliases.value = next.join('\n')
  }
}

function openChipEditor(kind: 'tags' | 'aliases') {
  chipEditorKind.value = kind
  chipEditorText.value = kind === 'tags' ? formTags.value : formAliases.value
  chipEditorOpen.value = true
}

function applyChipEditor() {
  const values = linesFrom(chipEditorText.value)
  if (chipEditorKind.value === 'tags') {
    formTags.value = values.join('\n')
  } else {
    formAliases.value = values.join('\n')
  }
  chipEditorOpen.value = false
}

function candidateKey(candidate: MotifReferenceCandidate, index: number): string {
  return `${index}:${candidate.source_author}:${candidate.source_title}:${candidate.text}`.toLocaleLowerCase()
}

function candidateCanImport(candidate: MotifReferenceCandidate): boolean {
  return Boolean(candidate.text.trim() && candidate.source_author.trim() && candidate.source_title.trim())
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
    defaultAiProfileId.value = result.default_profile_id ?? null
    if (!aiProfileOptions.value.some((profile) => profile.id === enrichmentProfileId.value)) {
      enrichmentProfileId.value = defaultAiProfileId.value ? 'default' : (result.profiles.find((profile) => profile.enabled)?.id ?? '')
    }
  } catch {
    aiProfiles.value = []
    defaultAiProfileId.value = null
    enrichmentProfileId.value = ''
  }
}

function resetEnrichmentDraft() {
  enrichmentError.value = ''
  enrichmentDraft.value = null
  enrichmentDraftTargetKey.value = null
  enrichmentProfileMode.value = 'merge'
  enrichmentApplyAliases.value = true
  enrichmentApplyTags.value = true
  enrichmentApplyReferenceKeys.value = []
}

function formatElapsed(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000))
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  if (minutes <= 0) return `${seconds}s`
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}

function stopEnrichmentPolling() {
  if (enrichmentPollingTimer) {
    window.clearTimeout(enrichmentPollingTimer)
    enrichmentPollingTimer = null
  }
}

function scheduleEnrichmentPolling(delayMs = 1500) {
  stopEnrichmentPolling()
  enrichmentPollingTimer = window.setTimeout(() => {
    void pollActiveEnrichmentJob()
  }, delayMs)
}

function handleEnrichmentJobSnapshot(job: AiJobSnapshot) {
  activeEnrichmentJobId.value = job.job_id
  activeEnrichmentJob.value = job
  const isRunning = !ENRICHMENT_JOB_TERMINAL.has(job.status)
  enrichmentGenerating.value = isRunning
  if (isRunning) return
  stopEnrichmentPolling()
  if (job.status === 'succeeded' && job.result) {
    enrichmentDraft.value = job.result
    enrichmentApplyReferenceKeys.value = []
    enrichmentError.value = ''
  } else if (job.status === 'failed' || job.status === 'cancelled') {
    enrichmentError.value = job.error
  }
}

async function pollActiveEnrichmentJob() {
  const jobId = activeEnrichmentJobId.value
  if (!jobId) return
  try {
    const job = await aiJobsApi.getJob(jobId)
    if (activeEnrichmentJobId.value !== jobId) return
    enrichmentReconnectCount.value = 0
    enrichmentReconnectMessage.value = ''
    handleEnrichmentJobSnapshot(job)
    if (!ENRICHMENT_JOB_TERMINAL.has(job.status)) {
      scheduleEnrichmentPolling(1500)
    }
  } catch (e) {
    if (activeEnrichmentJobId.value !== jobId) return
    if (isHttpStatus(e, 404)) {
      const message = t('motifs.enrichJobMissing')
      enrichmentReconnectMessage.value = message
      enrichmentGenerating.value = false
      if (activeEnrichmentJob.value) {
        activeEnrichmentJob.value = {
          ...activeEnrichmentJob.value,
          status: 'failed',
          stage: 'failed',
          stage_label: t('motifs.enrichJobLocalMissing'),
          error: message,
        }
      }
      stopEnrichmentPolling()
      return
    }
    enrichmentReconnectCount.value += 1
    enrichmentReconnectMessage.value = t('motifs.enrichReconnecting', { count: enrichmentReconnectCount.value })
    scheduleEnrichmentPolling(Math.min(5000, 1500 + enrichmentReconnectCount.value * 700))
  }
}

function viewActiveEnrichmentJob() {
  const job = activeEnrichmentJob.value
  if (!job) return
  enrichmentMotifId.value = job.motif_id ?? null
  enrichmentConcept.value = job.concept
  enrichmentProfileId.value = job.profile_id || 'default'
  enrichmentDraftTargetKey.value = enrichmentTargetKey(job.motif_id ?? null)
  if (job.status === 'succeeded' && job.result) {
    enrichmentDraft.value = job.result
    enrichmentError.value = ''
  } else if (job.status === 'failed' || job.status === 'cancelled') {
    enrichmentError.value = job.error
  } else {
    enrichmentError.value = ''
  }
  enrichmentOpen.value = true
  if (!ENRICHMENT_JOB_TERMINAL.has(job.status)) {
    scheduleEnrichmentPolling(1500)
  }
  void loadAiProfiles()
}

async function cancelActiveEnrichmentJob() {
  const jobId = activeEnrichmentJobId.value
  if (!jobId) return
  try {
    const job = await aiJobsApi.cancelJob(jobId)
    enrichmentReconnectCount.value = 0
    enrichmentReconnectMessage.value = ''
    handleEnrichmentJobSnapshot(job)
  } catch (e) {
    enrichmentError.value = errorMessage(e)
  }
}

function clearActiveEnrichmentJob() {
  if (activeEnrichmentJobIsRunning.value) return
  stopEnrichmentPolling()
  activeEnrichmentJobId.value = null
  activeEnrichmentJob.value = null
  enrichmentReconnectCount.value = 0
  enrichmentReconnectMessage.value = ''
}

function openEnrichmentForSelected() {
  const motif = selectedMotif.value
  if (!motif) return
  const nextKey = enrichmentTargetKey(motif.id)
  const sameTarget = enrichmentCurrentTargetKey.value === nextKey
  enrichmentMotifId.value = motif.id
  enrichmentConcept.value = formName.value.trim() || motif.name
  if (!sameTarget) {
    enrichmentDirection.value = ''
    enrichmentIncludeExcerpts.value = true
    enrichmentRequestWebContext.value = false
  }
  enrichmentError.value = ''
  enrichmentOpen.value = true
  void loadAiProfiles()
}

function openEnrichmentForNewConcept() {
  const concept = newMotifName.value.trim()
  const nextKey = enrichmentTargetKey(null)
  const sameTarget = enrichmentCurrentTargetKey.value === nextKey
  const hasNewDraft = Boolean(enrichmentDraft.value && enrichmentDraftTargetKey.value === nextKey)
  enrichmentMotifId.value = null
  if (concept) {
    enrichmentConcept.value = concept
  } else if (!hasNewDraft) {
    enrichmentConcept.value = ''
  }
  if (!sameTarget) {
    enrichmentDirection.value = ''
    enrichmentIncludeExcerpts.value = false
    enrichmentRequestWebContext.value = false
  }
  enrichmentError.value = ''
  enrichmentOpen.value = true
  void loadAiProfiles()
}

function closeEnrichment() {
  if (enrichmentApplying.value) return
  enrichmentOpen.value = false
}

async function generateEnrichmentDraft() {
  const concept = enrichmentConcept.value.trim()
  if (!concept) {
    enrichmentError.value = t('motifs.enrichConceptRequired')
    return
  }
  if (activeEnrichmentJobIsRunning.value) {
    enrichmentError.value = t('motifs.enrichJobAlreadyRunning')
    return
  }
  enrichmentGenerating.value = true
  enrichmentError.value = ''
  enrichmentReconnectCount.value = 0
  enrichmentReconnectMessage.value = ''
  resetEnrichmentDraft()
  const targetKey = enrichmentCurrentTargetKey.value
  try {
    const job = await aiJobsApi.createMotifEnrichmentJob({
      motif_id: enrichmentMotifId.value,
      concept,
      direction: enrichmentDirection.value,
      include_excerpts: enrichmentIncludeExcerpts.value,
      request_web_context: enrichmentRequestWebContext.value,
      profile_id: enrichmentProfileId.value,
      cost_tier: 'strong',
    })
    enrichmentDraftTargetKey.value = targetKey
    handleEnrichmentJobSnapshot(job)
    if (!ENRICHMENT_JOB_TERMINAL.has(job.status)) {
      scheduleEnrichmentPolling(1500)
    }
  } catch (e) {
    enrichmentError.value = isHttpStatus(e, 404) ? t('motifs.enrichJobsUnsupported') : friendlyMotifError(e)
    enrichmentGenerating.value = false
  }
}

async function applyEnrichmentDraft() {
  const draft = enrichmentDraft.value
  if (!draft) return
  if (!enrichmentDraftMatchesTarget.value) {
    enrichmentError.value = t('motifs.enrichDraftTargetChanged')
    return
  }
  enrichmentApplying.value = true
  enrichmentError.value = ''
  try {
    let appliedMotifId = enrichmentMotifId.value
    if (enrichmentMotifId.value) {
      const targetMotif = motifs.value.find((motif) => motif.id === enrichmentMotifId.value) ?? selectedMotif.value
      const requestedName = (formName.value.trim() || targetMotif?.name || draft.concept).trim()
      const duplicate = findMotifByName(requestedName)
      const safeName = duplicate && duplicate.id !== enrichmentMotifId.value
        ? (targetMotif?.name ?? requestedName)
        : requestedName
      const aliases = enrichmentApplyAliases.value
        ? mergeUniqueValues(linesFrom(formAliases.value), draft.aliases)
        : linesFrom(formAliases.value)
      const tags = enrichmentApplyTags.value
        ? mergeUniqueValues(linesFrom(formTags.value), draft.tags)
        : linesFrom(formTags.value)
      const payload = {
        name: safeName,
        aliases,
        tags,
        note: formNote.value,
        profile: mergeProfiles(formProfile.value, draft.profile, enrichmentProfileMode.value),
        pinned: formPinned.value,
      }
      const updated = await motifsApi.updateMotif(enrichmentMotifId.value, payload)
      upsertMotifInList(updated)
      selectedMotifId.value = updated.id
      appliedMotifId = updated.id
      formName.value = updated.name
      formAliases.value = updated.aliases.join('\n')
      formTags.value = updated.tags.join('\n')
      formNote.value = updated.note
      formProfile.value = normalizeProfile(updated.profile)
      formPinned.value = updated.pinned
    } else {
      const conceptName = enrichmentConcept.value.trim() || draft.concept
      const existing = await resolveMotifByName(conceptName)
      if (existing) {
        const updated = await motifsApi.updateMotif(existing.id, {
          name: existing.name,
          aliases: enrichmentApplyAliases.value
            ? mergeUniqueValues(existing.aliases, draft.aliases)
            : existing.aliases,
          tags: enrichmentApplyTags.value
            ? mergeUniqueValues(existing.tags, draft.tags)
            : existing.tags,
          note: existing.note,
          profile: mergeProfiles(normalizeProfile(existing.profile), draft.profile, enrichmentProfileMode.value),
          pinned: existing.pinned,
        })
        upsertMotifInList(updated)
        selectedMotifId.value = updated.id
        appliedMotifId = updated.id
        formName.value = updated.name
        formAliases.value = updated.aliases.join('\n')
        formTags.value = updated.tags.join('\n')
        formNote.value = updated.note
        formProfile.value = normalizeProfile(updated.profile)
        formPinned.value = updated.pinned
      } else {
        const created = await motifsApi.createMotif({
          name: conceptName,
          aliases: enrichmentApplyAliases.value ? draft.aliases : [],
          tags: enrichmentApplyTags.value ? draft.tags : [],
          note: '',
          profile: enrichmentProfileMode.value === 'none' ? emptyMotifProfile() : draft.profile,
          pinned: false,
        })
        await loadMotifs()
        selectedMotifId.value = created.id
        appliedMotifId = created.id
      }
      if (motifNamesEqual(newMotifName.value, conceptName)) {
        newMotifName.value = ''
      }
    }

    const selectedCandidates = draft.reference_candidates.filter((candidate, index) =>
      enrichmentApplyReferenceKeys.value.includes(candidateKey(candidate, index))
    )
    let importedCount = 0
    if (appliedMotifId && selectedCandidates.length) {
      const result = await motifsApi.applyReferenceCandidates(appliedMotifId, selectedCandidates)
      importedCount = result.imported.length
      if (result.skipped.length) {
        enrichmentError.value = result.skipped.join('\n')
      }
    }

    notice.value = importedCount
      ? t('motifs.enrichAppliedWithReferences', { count: importedCount })
      : t('motifs.enrichApplied')
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
      profile: normalizeProfile(formProfile.value),
      pinned: formPinned.value,
    })
    motifs.value = motifs.value.map((item) => item.id === updated.id ? updated : item)
    formProfile.value = normalizeProfile(updated.profile)
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

function openSourceAnchorGroup(group: MotifSourceAnchorGroup) {
  if (!group.exists) return
  const available = group.excerpts.filter((excerpt) => excerpt.source_exists)
  if (available.length === 1) {
    void jumpToSource(available[0])
    return
  }
  sourceAnchorPickerGroup.value = {
    ...group,
    excerpts: available,
  }
}

function closeSourceAnchorPicker() {
  sourceAnchorPickerGroup.value = null
}

async function selectSourceAnchor(excerpt: MotifExcerpt) {
  closeSourceAnchorPicker()
  await jumpToSource(excerpt)
}

async function removeSourceAnchorFromPicker(excerpt: MotifExcerpt) {
  closeSourceAnchorPicker()
  await removeExcerptFromSelectedMotif(excerpt)
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
            class="rounded-xl bg-teal-700 px-3 py-2 text-sm font-semibold text-white transition hover:bg-teal-800"
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
          <div class="flex items-center gap-3">
            <span v-if="notice" class="text-sm text-teal-700">{{ notice }}</span>
            <span v-if="error" class="text-sm text-red-600">{{ error }}</span>
          </div>
        </div>
      </div>

      <div class="flex min-h-0 flex-1 overflow-hidden">
        <section class="min-w-0 flex-1 overflow-hidden p-5">
          <div class="h-full rounded-[1.75rem] border border-amber-100 bg-[#fff9ed] p-3 shadow-sm" data-testid="motifs-cooccurrence-graph">
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
          <div
            v-if="activeEnrichmentJob"
            class="m-4 rounded-2xl border p-3 shadow-sm"
            :class="activeEnrichmentJob.status === 'failed'
              ? 'border-rose-200 bg-rose-50'
              : activeEnrichmentJob.status === 'succeeded'
                ? 'border-teal-200 bg-teal-50'
                : activeEnrichmentJob.status === 'cancelled'
                  ? 'border-stone-200 bg-stone-50'
                  : 'border-amber-200 bg-amber-50'"
            data-testid="motif-enrichment-job-bar"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="truncate text-sm font-semibold text-stone-900">{{ activeEnrichmentJobTitle }}</div>
                <div class="mt-1 text-xs leading-5 text-stone-600">{{ activeEnrichmentJobDetail }}</div>
                <div
                  v-if="activeEnrichmentJobIsRunning"
                  class="mt-2 h-1.5 overflow-hidden rounded-full bg-white/80"
                >
                  <div class="ai-pending-bar h-full w-1/3 rounded-full bg-teal-600"></div>
                </div>
              </div>
              <div class="flex shrink-0 flex-wrap justify-end gap-2">
                <button
                  @click="viewActiveEnrichmentJob"
                  class="rounded-lg bg-white px-2.5 py-1.5 text-xs font-semibold text-stone-700 ring-1 ring-stone-200 hover:bg-stone-50"
                >
                  {{ activeEnrichmentJob.status === 'succeeded' ? t('motifs.enrichViewDraft') : t('motifs.enrichViewJob') }}
                </button>
                <button
                  v-if="activeEnrichmentJobIsRunning"
                  @click="cancelActiveEnrichmentJob"
                  class="rounded-lg bg-rose-600 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-rose-700"
                >
                  {{ t('motifs.enrichCancelJob') }}
                </button>
                <button
                  v-if="activeEnrichmentJobCanClear"
                  @click="clearActiveEnrichmentJob"
                  class="rounded-lg bg-white px-2.5 py-1.5 text-xs font-semibold text-stone-500 ring-1 ring-stone-200 hover:bg-stone-50"
                >
                  {{ t('motifs.enrichClearJob') }}
                </button>
              </div>
            </div>
          </div>
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
              <div class="mt-4">
                <div class="mb-2 flex items-center justify-between gap-3">
                  <h3 class="text-sm font-semibold text-stone-700">{{ t('motifs.tags') }}</h3>
                  <button type="button" @click="openChipEditor('tags')" class="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800 hover:bg-amber-100">
                    {{ t('motifs.editTags') }}
                  </button>
                </div>
                <div v-if="formTagChips.length" class="flex flex-wrap gap-1.5">
                  <button
                    v-for="item in formTagChips"
                    :key="`form-tag-${item}`"
                    type="button"
                    @click="removeChip('tags', item)"
                    class="rounded-full bg-amber-50 px-2 py-1 text-xs text-amber-800 ring-1 ring-amber-100 hover:bg-amber-100"
                    :title="t('motifs.removeChip')"
                  >
                    {{ item }} <span class="ml-1 text-amber-500">×</span>
                  </button>
                </div>
                <button v-else type="button" @click="openChipEditor('tags')" class="rounded-xl border border-dashed border-stone-200 px-3 py-2 text-sm text-stone-400 hover:border-amber-200 hover:text-amber-700">
                  {{ t('motifs.addTags') }}
                </button>
              </div>
              <div class="mt-4">
                <div class="mb-2 flex items-center justify-between gap-3">
                  <h3 class="text-sm font-semibold text-stone-700">{{ t('motifs.aliases') }}</h3>
                  <button type="button" @click="openChipEditor('aliases')" class="rounded-full bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-800 hover:bg-teal-100">
                    {{ t('motifs.editAliases') }}
                  </button>
                </div>
                <div v-if="formAliasChips.length" class="flex flex-wrap gap-1.5">
                  <button
                    v-for="item in formAliasChips"
                    :key="`form-alias-${item}`"
                    type="button"
                    @click="removeChip('aliases', item)"
                    class="rounded-full bg-teal-50 px-2 py-1 text-xs text-teal-800 ring-1 ring-teal-100 hover:bg-teal-100"
                    :title="t('motifs.removeChip')"
                  >
                    {{ item }} <span class="ml-1 text-teal-500">×</span>
                  </button>
                </div>
                <button v-else type="button" @click="openChipEditor('aliases')" class="rounded-xl border border-dashed border-stone-200 px-3 py-2 text-sm text-stone-400 hover:border-teal-200 hover:text-teal-700">
                  {{ t('motifs.addAliases') }}
                </button>
              </div>
              <section class="mt-5 rounded-2xl border border-amber-100 bg-[#fffaf0] p-4">
                <div class="mb-3 flex items-center justify-between gap-3">
                  <div>
                    <h3 class="text-sm font-semibold text-stone-900">{{ t('motifs.profileOverview') }}</h3>
                    <p class="mt-1 text-xs leading-5 text-stone-500">{{ t('motifs.profileOverviewHint') }}</p>
                  </div>
                  <div class="flex shrink-0 gap-2">
                    <button type="button" @click="profileDrawerOpen = true" class="rounded-xl bg-white px-3 py-2 text-xs font-semibold text-stone-700 ring-1 ring-stone-200 hover:bg-stone-50">
                      {{ t('motifs.viewProfileDetails') }}
                    </button>
                    <button type="button" @click="profileEditorOpen = true" class="rounded-xl bg-stone-900 px-3 py-2 text-xs font-semibold text-white hover:bg-stone-700">
                      {{ t('motifs.editProfile') }}
                    </button>
                  </div>
                </div>
                <div v-if="profileHasContent" class="space-y-3">
                  <div v-if="formProfile.definition" class="rounded-xl bg-white/85 p-3">
                    <div class="mb-1 text-xs font-semibold text-teal-700">{{ t('motifs.profileDefinition') }}</div>
                    <p class="text-sm leading-7 text-stone-850">{{ formProfile.definition }}</p>
                  </div>
                  <div v-if="formProfile.core_tension" class="rounded-xl bg-white/85 p-3">
                    <div class="mb-1 text-xs font-semibold text-rose-700">{{ t('motifs.profileCoreTension') }}</div>
                    <p class="text-sm leading-7 text-stone-850">{{ formProfile.core_tension }}</p>
                  </div>
                  <div v-if="formProfile.writing_functions.length" class="flex flex-wrap gap-1.5">
                    <span v-for="item in formProfile.writing_functions.slice(0, 5)" :key="`profile-function-${item}`" class="rounded-full bg-white px-2.5 py-1 text-xs text-stone-700 ring-1 ring-amber-100">{{ item }}</span>
                  </div>
                </div>
                <div v-else class="rounded-xl border border-dashed border-amber-200 bg-white/60 p-4 text-sm leading-6 text-stone-500">
                  <p>{{ formNote.trim() ? t('motifs.legacyNoteHint') : t('motifs.profileEmpty') }}</p>
                  <p v-if="formNote.trim()" class="mt-2 line-clamp-4 whitespace-pre-wrap text-stone-600">{{ formNote }}</p>
                  <button type="button" @click="openEnrichmentForSelected" class="mt-3 rounded-xl bg-teal-700 px-3 py-2 text-xs font-semibold text-white hover:bg-teal-800">
                    {{ t('motifs.upgradeProfileWithAi') }}
                  </button>
                </div>
              </section>
              <div v-if="formDirty" class="mt-3 rounded-xl bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800">
                {{ t('motifs.unsavedChanges') }}
              </div>
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
              <div class="mb-3 flex items-start justify-between gap-3">
                <div>
                  <h3 class="text-lg font-semibold">{{ t('motifs.sourceAnchorGroups') }}</h3>
                  <p class="mt-1 text-xs leading-5 text-stone-500">{{ t('motifs.sourceAnchorGroupsHint') }}</p>
                </div>
                <span class="shrink-0 rounded-full bg-stone-100 px-2.5 py-1 text-xs text-stone-500">{{ excerpts.length }}</span>
              </div>
              <div v-if="detailError" class="mb-3 rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {{ detailError }}
              </div>
              <div v-if="detailLoading" class="rounded-xl bg-white p-4 text-sm text-stone-400">
                {{ t('common.loading') }}
              </div>
              <div v-else-if="!sourceAnchorGroups.length" class="rounded-xl border border-dashed border-stone-200 bg-white/70 p-5 text-sm leading-6 text-stone-400">
                {{ t('motifs.noExcerpts') }}
              </div>
              <div v-else class="space-y-3">
                <article
                  v-for="group in sourceAnchorGroups"
                  :key="group.key"
                  class="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm"
                  :class="group.exists ? '' : 'opacity-75'"
                >
                  <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0">
                      <div class="mb-2 flex flex-wrap items-center gap-2">
                        <span class="rounded-full bg-stone-100 px-2.5 py-1 text-xs font-medium text-stone-600">
                          {{ group.sourceKind === 'article' ? t('motifs.sourceKindArticle') : t('motifs.sourceKindReference') }}
                        </span>
                        <span class="rounded-full bg-teal-50 px-2.5 py-1 text-xs font-semibold text-teal-700">
                          {{ t('motifs.anchorCount', { count: group.excerpts.length }) }}
                        </span>
                      </div>
                      <h4 class="break-words text-sm font-semibold leading-6 text-stone-900">
                        {{ group.exists ? group.label : t('motifs.sourceMissing') }}
                      </h4>
                    </div>
                    <div class="flex shrink-0 flex-wrap justify-end gap-2">
                      <button
                        type="button"
                        @click="openSourceAnchorGroup(group)"
                        :disabled="!group.exists"
                        class="rounded-xl bg-teal-700 px-3 py-2 text-xs font-semibold text-white transition hover:bg-teal-800 disabled:bg-stone-200 disabled:text-stone-400"
                      >
                        {{ group.excerpts.length > 1 ? t('motifs.chooseAnchor') : t('motifs.openSource') }}
                      </button>
                      <button
                        v-if="group.excerpts.length === 1"
                        type="button"
                        @click="removeExcerptFromSelectedMotif(group.excerpts[0])"
                        class="rounded-xl bg-stone-100 px-3 py-2 text-xs font-semibold text-stone-600 hover:bg-stone-200"
                      >
                        {{ t('motifs.removeFromMotif') }}
                      </button>
                    </div>
                  </div>
                </article>
              </div>
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
      v-if="sourceAnchorPickerGroup"
      class="fixed inset-0 z-50 flex items-center justify-center bg-stone-950/30 px-4 py-6"
      @click.self="closeSourceAnchorPicker"
    >
      <section class="w-full max-w-lg rounded-2xl border border-stone-200 bg-[#fffdf8] p-5 shadow-2xl">
        <div class="mb-4 flex items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="text-xs font-semibold uppercase tracking-[0.18em] text-teal-700">{{ t('motifs.anchorPickerTitle') }}</p>
            <h2 class="mt-1 break-words text-lg font-semibold text-stone-950">{{ sourceAnchorPickerGroup.label }}</h2>
            <p class="mt-1 text-xs leading-5 text-stone-500">{{ t('motifs.sourceAnchorGroupsHint') }}</p>
          </div>
          <button type="button" @click="closeSourceAnchorPicker" class="rounded-full px-3 py-1 text-lg text-stone-400 hover:bg-stone-100 hover:text-stone-700">×</button>
        </div>
        <div class="grid gap-2">
          <div
            v-for="(excerpt, index) in sourceAnchorPickerGroup.excerpts"
            :key="`source-anchor-pick-${excerpt.id}`"
            class="flex items-center justify-between gap-3 rounded-xl border border-stone-200 bg-white px-3 py-2"
          >
            <div class="min-w-0">
              <div class="text-sm font-semibold text-stone-800">{{ t('motifs.anchorOrdinal', { index: index + 1 }) }}</div>
              <div class="mt-0.5 text-xs text-stone-400">{{ excerpt.selection_start !== null ? `#${excerpt.selection_start}` : t('motifs.rangeMissing') }}</div>
            </div>
            <div class="flex shrink-0 gap-2">
              <button type="button" @click="selectSourceAnchor(excerpt)" class="rounded-lg bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-800">
                {{ t('motifs.locateAnchor') }}
              </button>
              <button type="button" @click="removeSourceAnchorFromPicker(excerpt)" class="rounded-lg bg-stone-100 px-3 py-1.5 text-xs font-semibold text-stone-600 hover:bg-stone-200">
                {{ t('motifs.removeFromMotif') }}
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
    <div
      v-if="chipEditorOpen"
      class="fixed inset-0 z-50 flex items-center justify-center bg-stone-950/30 px-4 py-6"
      @click.self="chipEditorOpen = false"
    >
      <section class="w-full max-w-md rounded-2xl border border-stone-200 bg-[#fffdf8] p-5 shadow-2xl">
        <div class="mb-4 flex items-start justify-between gap-3">
          <div>
            <p class="text-xs font-semibold uppercase tracking-[0.18em] text-teal-700">
              {{ chipEditorKind === 'tags' ? t('motifs.tags') : t('motifs.aliases') }}
            </p>
            <h2 class="mt-1 text-lg font-semibold text-stone-950">{{ t('motifs.editChips') }}</h2>
            <p class="mt-1 text-xs leading-5 text-stone-500">{{ t('motifs.editChipsHint') }}</p>
          </div>
          <button type="button" @click="chipEditorOpen = false" class="rounded-full px-3 py-1 text-lg text-stone-400 hover:bg-stone-100 hover:text-stone-700">×</button>
        </div>
        <textarea
          v-model="chipEditorText"
          rows="8"
          class="min-h-[190px] w-full resize-y rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm leading-7 outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-100"
          :placeholder="t('motifs.onePerLine')"
        />
        <div class="mt-4 flex justify-end gap-2">
          <button type="button" @click="chipEditorOpen = false" class="rounded-xl bg-stone-100 px-4 py-2 text-sm font-semibold text-stone-600 hover:bg-stone-200">
            {{ t('common.cancel') }}
          </button>
          <button type="button" @click="applyChipEditor" class="rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white hover:bg-stone-700">
            {{ t('motifs.applyChipDraft') }}
          </button>
        </div>
      </section>
    </div>
    <div
      v-if="profileDrawerOpen"
      class="fixed inset-0 z-40 flex justify-end bg-stone-950/25"
      @click.self="profileDrawerOpen = false"
    >
      <aside class="flex h-full w-full max-w-2xl flex-col overflow-hidden border-l border-stone-200 bg-[#fffdf8] shadow-2xl">
        <header class="border-b border-stone-200 px-6 py-5">
          <div class="flex items-start justify-between gap-4">
            <div class="min-w-0">
              <p class="text-xs font-semibold uppercase tracking-[0.2em] text-rose-700">{{ t('motifs.profileDetails') }}</p>
              <h2 class="mt-2 truncate text-2xl font-semibold text-stone-950">{{ formName || selectedMotif?.name }}</h2>
              <p class="mt-1 text-sm leading-6 text-stone-500">{{ t('motifs.profileDetailsHint') }}</p>
            </div>
            <button type="button" @click="profileDrawerOpen = false" class="rounded-full px-3 py-1 text-lg text-stone-400 hover:bg-stone-100 hover:text-stone-700">×</button>
          </div>
        </header>
        <div class="min-h-0 flex-1 overflow-y-auto px-6 py-5">
          <div v-if="profileHasContent" class="space-y-4">
            <section class="rounded-2xl border border-amber-100 bg-white p-4">
              <h3 class="text-sm font-semibold text-stone-950">{{ t('motifs.profileConceptSection') }}</h3>
              <p v-if="formProfile.definition" class="mt-3 text-base leading-8 text-stone-850">{{ formProfile.definition }}</p>
              <p v-if="formProfile.core_tension" class="mt-3 rounded-xl bg-rose-50 px-3 py-2 text-sm leading-7 text-rose-900">{{ formProfile.core_tension }}</p>
            </section>
            <section class="rounded-2xl border border-stone-200 bg-white p-4">
              <h3 class="text-sm font-semibold text-stone-950">{{ t('motifs.profileWritingSection') }}</h3>
              <div class="mt-3 grid gap-3">
                <div v-if="formProfile.writing_functions.length">
                  <div class="text-xs font-semibold text-stone-500">{{ t('motifs.profileWritingFunctions') }}</div>
                  <ul class="mt-2 space-y-1.5 text-sm leading-6 text-stone-750">
                    <li v-for="item in formProfile.writing_functions" :key="`detail-function-${item}`">· {{ item }}</li>
                  </ul>
                </div>
                <div v-if="formProfile.scene_triggers.length">
                  <div class="text-xs font-semibold text-stone-500">{{ t('motifs.profileSceneTriggers') }}</div>
                  <ul class="mt-2 space-y-1.5 text-sm leading-6 text-stone-750">
                    <li v-for="item in formProfile.scene_triggers" :key="`detail-trigger-${item}`">· {{ item }}</li>
                  </ul>
                </div>
                <div v-if="formProfile.character_signals.length">
                  <div class="text-xs font-semibold text-stone-500">{{ t('motifs.profileCharacterSignals') }}</div>
                  <ul class="mt-2 space-y-1.5 text-sm leading-6 text-stone-750">
                    <li v-for="item in formProfile.character_signals" :key="`detail-character-${item}`">· {{ item }}</li>
                  </ul>
                </div>
                <div v-if="formProfile.imagery_translations.length">
                  <div class="text-xs font-semibold text-stone-500">{{ t('motifs.profileImageryTranslations') }}</div>
                  <ul class="mt-2 space-y-1.5 text-sm leading-6 text-stone-750">
                    <li v-for="item in formProfile.imagery_translations" :key="`detail-imagery-${item}`">· {{ item }}</li>
                  </ul>
                </div>
              </div>
            </section>
            <section v-if="formProfile.short_examples.length || formProfile.micro_exercises.length || formProfile.misuse_warnings.length" class="rounded-2xl border border-stone-200 bg-white p-4">
              <h3 class="text-sm font-semibold text-stone-950">{{ t('motifs.profileExamplesSection') }}</h3>
              <div v-if="formProfile.short_examples.length" class="mt-3 space-y-2">
                <p v-for="item in formProfile.short_examples" :key="`detail-example-${item}`" class="rounded-xl bg-[#fffaf0] px-3 py-2 text-sm leading-7 text-stone-800">{{ item }}</p>
              </div>
              <div v-if="formProfile.micro_exercises.length" class="mt-4">
                <div class="text-xs font-semibold text-stone-500">{{ t('motifs.profileMicroExercises') }}</div>
                <ul class="mt-2 space-y-1.5 text-sm leading-6 text-stone-750">
                  <li v-for="item in formProfile.micro_exercises" :key="`detail-exercise-${item}`">· {{ item }}</li>
                </ul>
              </div>
              <div v-if="formProfile.misuse_warnings.length" class="mt-4 rounded-xl bg-amber-50 px-3 py-2">
                <div class="text-xs font-semibold text-amber-800">{{ t('motifs.profileMisuseWarnings') }}</div>
                <ul class="mt-2 space-y-1.5 text-sm leading-6 text-amber-950">
                  <li v-for="item in formProfile.misuse_warnings" :key="`detail-warning-${item}`">· {{ item }}</li>
                </ul>
              </div>
            </section>
            <section v-if="formProfile.source_hints.length || formNote.trim()" class="rounded-2xl border border-stone-200 bg-white p-4">
              <h3 class="text-sm font-semibold text-stone-950">{{ t('motifs.profileSourcesAndNote') }}</h3>
              <div v-if="formProfile.source_hints.length" class="mt-3 space-y-3">
                <div v-for="hint in formProfile.source_hints" :key="`${hint.title}-${hint.url || hint.note}`" class="rounded-xl bg-stone-50 px-3 py-2">
                  <a v-if="hint.url" :href="hint.url" target="_blank" rel="noreferrer" class="text-sm font-semibold text-teal-700 hover:text-teal-900">{{ hint.title }}</a>
                  <p v-else class="text-sm font-semibold text-stone-800">{{ hint.title }}</p>
                  <p v-if="hint.note" class="mt-1 text-xs leading-5 text-stone-500">{{ hint.note }}</p>
                </div>
              </div>
              <div v-if="formNote.trim()" class="mt-4 rounded-xl bg-[#fffaf0] px-3 py-2 text-sm leading-7 text-stone-750 whitespace-pre-wrap">{{ formNote }}</div>
            </section>
          </div>
          <div v-else class="rounded-2xl border border-dashed border-stone-200 bg-white p-6 text-center text-sm leading-6 text-stone-400">
            {{ t('motifs.profileEmpty') }}
          </div>
        </div>
        <footer class="border-t border-stone-200 bg-white px-6 py-4">
          <div class="flex justify-end gap-2">
            <button type="button" @click="profileEditorOpen = true" class="rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white hover:bg-stone-700">{{ t('motifs.editProfile') }}</button>
          </div>
        </footer>
      </aside>
    </div>
    <div
      v-if="profileEditorOpen"
      class="fixed inset-0 z-50 flex justify-end bg-stone-950/30"
      @click.self="profileEditorOpen = false"
    >
      <aside class="flex h-full w-full max-w-3xl flex-col overflow-hidden border-l border-stone-200 bg-[#fffdf8] shadow-2xl">
        <header class="border-b border-stone-200 px-6 py-5">
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">{{ t('motifs.profileEditor') }}</p>
              <h2 class="mt-2 text-2xl font-semibold text-stone-950">{{ t('motifs.editProfile') }}</h2>
              <p class="mt-1 text-sm leading-6 text-stone-500">{{ t('motifs.profileEditorHint') }}</p>
            </div>
            <button type="button" @click="profileEditorOpen = false" class="rounded-full px-3 py-1 text-lg text-stone-400 hover:bg-stone-100 hover:text-stone-700">×</button>
          </div>
        </header>
        <div class="min-h-0 flex-1 overflow-y-auto px-6 py-5">
          <div class="grid gap-4">
            <label class="block text-sm font-medium text-stone-700">
              {{ t('motifs.profileDefinition') }}
              <textarea v-model="formProfile.definition" rows="3" class="mt-1 w-full resize-y rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm leading-7 outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-100" />
            </label>
            <label class="block text-sm font-medium text-stone-700">
              {{ t('motifs.profileCoreTension') }}
              <textarea v-model="formProfile.core_tension" rows="3" class="mt-1 w-full resize-y rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm leading-7 outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-100" />
            </label>
            <div class="grid gap-4 md:grid-cols-2">
              <label class="block text-sm font-medium text-stone-700">
                {{ t('motifs.profileWritingFunctions') }}
                <textarea :value="profileListText('writing_functions')" @input="setProfileList('writing_functions', inputValue($event))" rows="5" class="mt-1 w-full resize-y rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm leading-7 outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-100" :placeholder="t('motifs.onePerLine')" />
              </label>
              <label class="block text-sm font-medium text-stone-700">
                {{ t('motifs.profileSceneTriggers') }}
                <textarea :value="profileListText('scene_triggers')" @input="setProfileList('scene_triggers', inputValue($event))" rows="5" class="mt-1 w-full resize-y rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm leading-7 outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-100" :placeholder="t('motifs.onePerLine')" />
              </label>
              <label class="block text-sm font-medium text-stone-700">
                {{ t('motifs.profileCharacterSignals') }}
                <textarea :value="profileListText('character_signals')" @input="setProfileList('character_signals', inputValue($event))" rows="5" class="mt-1 w-full resize-y rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm leading-7 outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-100" :placeholder="t('motifs.onePerLine')" />
              </label>
              <label class="block text-sm font-medium text-stone-700">
                {{ t('motifs.profileImageryTranslations') }}
                <textarea :value="profileListText('imagery_translations')" @input="setProfileList('imagery_translations', inputValue($event))" rows="5" class="mt-1 w-full resize-y rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm leading-7 outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-100" :placeholder="t('motifs.onePerLine')" />
              </label>
            </div>
            <label class="block text-sm font-medium text-stone-700">
              {{ t('motifs.profileShortExamples') }}
              <textarea :value="profileListText('short_examples')" @input="setProfileList('short_examples', inputValue($event))" rows="5" class="mt-1 w-full resize-y rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm leading-7 outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-100" :placeholder="t('motifs.onePerLine')" />
            </label>
            <div class="grid gap-4 md:grid-cols-2">
              <label class="block text-sm font-medium text-stone-700">
                {{ t('motifs.profileMisuseWarnings') }}
                <textarea :value="profileListText('misuse_warnings')" @input="setProfileList('misuse_warnings', inputValue($event))" rows="5" class="mt-1 w-full resize-y rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm leading-7 outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-100" :placeholder="t('motifs.onePerLine')" />
              </label>
              <label class="block text-sm font-medium text-stone-700">
                {{ t('motifs.profileMicroExercises') }}
                <textarea :value="profileListText('micro_exercises')" @input="setProfileList('micro_exercises', inputValue($event))" rows="5" class="mt-1 w-full resize-y rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm leading-7 outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-100" :placeholder="t('motifs.onePerLine')" />
              </label>
            </div>
            <label class="block text-sm font-medium text-stone-700">
              {{ t('motifs.freeNote') }}
              <textarea v-model="formNote" rows="6" class="mt-1 w-full resize-y rounded-xl border border-stone-200 bg-[#fffaf0] px-3 py-2 text-sm leading-7 outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-100" :placeholder="t('motifs.notePlaceholder')" />
            </label>
          </div>
        </div>
        <footer class="border-t border-stone-200 bg-white px-6 py-4">
          <div class="flex items-center justify-between gap-3">
            <p class="text-xs leading-5 text-stone-500">{{ t('motifs.profileSaveHint') }}</p>
            <button type="button" @click="profileEditorOpen = false" class="rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white hover:bg-stone-700">
              {{ t('common.done') }}
            </button>
          </div>
        </footer>
      </aside>
    </div>
    <div
      v-if="enrichmentOpen"
      class="fixed inset-0 z-50 flex items-center justify-center bg-stone-950/30 p-2 sm:p-4 lg:p-6"
      @click.self="closeEnrichment"
    >
      <section
        class="flex h-[calc(100vh-1rem)] max-h-[calc(100vh-1rem)] w-[calc(100vw-1rem)] max-w-[1600px] resize flex-col overflow-hidden rounded-2xl border border-stone-200 bg-[#fffdf8] shadow-2xl sm:h-[calc(100vh-2rem)] sm:max-h-[calc(100vh-2rem)] sm:w-[calc(100vw-2rem)] lg:h-[calc(100vh-3rem)] lg:max-h-[calc(100vh-3rem)] lg:w-[calc(100vw-3rem)]"
        data-testid="motif-enrichment-modal"
        :style="{ minWidth: 'min(760px, calc(100vw - 1rem))', minHeight: 'min(560px, calc(100vh - 1rem))' }"
      >
        <header class="shrink-0 border-b border-stone-200 px-4 py-3 sm:px-5 sm:py-4">
          <div class="flex items-start justify-between gap-4">
            <div class="min-w-0">
              <p class="text-xs font-semibold uppercase tracking-[0.22em] text-teal-700">{{ t('motifs.enrichEyebrow') }}</p>
              <h2 class="mt-1 text-xl font-semibold text-stone-950">{{ t('motifs.enrichTitle') }}</h2>
              <p class="mt-1 text-sm leading-6 text-stone-500">{{ t('motifs.enrichSubtitle') }}</p>
            </div>
            <button
              @click="closeEnrichment"
              class="shrink-0 rounded-full px-3 py-1 text-lg text-stone-400 hover:bg-stone-100 hover:text-stone-700"
            >
              ×
            </button>
          </div>
        </header>

        <div class="min-h-0 flex-1 overflow-y-auto p-3 sm:p-5 xl:overflow-hidden">
          <div class="grid gap-4 xl:h-full xl:min-h-0 xl:grid-cols-[360px_minmax(0,1fr)]">
            <section class="rounded-2xl border border-stone-200 bg-white p-4 xl:min-h-0 xl:overflow-y-auto">
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
                  class="mt-1 max-h-[30vh] w-full resize-y rounded-xl border border-stone-200 px-3 py-2 leading-6 outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-100"
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
                :disabled="enrichmentGenerating || !enrichmentConcept.trim() || !enrichmentProfileId"
                class="mt-4 w-full rounded-xl bg-stone-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-stone-700 disabled:opacity-40"
              >
                {{ enrichmentGenerating ? t('motifs.enrichGenerating') : t('motifs.enrichGenerate') }}
              </button>
              <div v-if="enrichmentError" class="mt-3 rounded-xl bg-rose-50 px-3 py-2 text-sm leading-6 text-rose-700">
                {{ enrichmentError }}
              </div>
            </section>

            <section class="flex min-h-0 flex-col rounded-2xl border border-stone-200 bg-white p-3 sm:p-4">
              <div v-if="!enrichmentDraft" class="flex min-h-[220px] items-center justify-center rounded-xl border border-dashed border-stone-200 bg-stone-50 px-6 text-center text-sm leading-6 text-stone-400 sm:min-h-[300px]">
                <div v-if="activeEnrichmentJob && activeEnrichmentJobIsRunning" class="w-full max-w-lg text-left">
                  <div class="mb-4">
                    <div class="text-sm font-semibold text-stone-800">{{ activeEnrichmentJobTitle }}</div>
                    <div class="mt-1 text-xs text-stone-500">{{ activeEnrichmentJobDetail }}</div>
                  </div>
                  <div class="mb-4 h-2 overflow-hidden rounded-full bg-white">
                    <div class="ai-pending-bar h-full w-1/3 rounded-full bg-teal-600"></div>
                  </div>
                  <ol class="grid gap-2 text-xs leading-5 text-stone-600">
                    <li
                      v-for="stage in ['preparing_context', 'sending_request', 'waiting_model', 'parsing_response']"
                      :key="stage"
                      class="flex items-center gap-2"
                    >
                      <span
                        class="h-2 w-2 rounded-full"
                        :class="activeEnrichmentJob.stage === stage ? 'bg-teal-600' : 'bg-stone-300'"
                      ></span>
                      <span>{{ t(`motifs.enrichStage.${stage}`) }}</span>
                    </li>
                  </ol>
                  <p class="mt-4 rounded-xl bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800">
                    {{ t('motifs.enrichCancelCostHint') }}
                  </p>
                </div>
                <span v-else>{{ t('motifs.enrichEmptyPreview') }}</span>
              </div>
              <div v-else class="flex min-h-0 flex-1 flex-col">
                <div class="mb-3 flex shrink-0 items-start justify-between gap-3">
                  <div class="min-w-0">
                    <p class="text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">{{ t('motifs.enrichDraft') }}</p>
                    <h3 class="mt-1 truncate text-lg font-semibold text-stone-950">{{ enrichmentDraft.title }}</h3>
                    <p class="mt-1 text-xs text-stone-500">
                      {{ enrichmentDraft.provider || 'AI' }} · {{ enrichmentDraft.model || t('motifs.enrichUnknownModel') }} · {{ enrichmentDraft.elapsed_ms }}ms
                    </p>
                  </div>
                </div>
                <div
                  v-if="!enrichmentDraftMatchesTarget"
                  class="mb-3 shrink-0 rounded-xl bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800"
                >
                  {{ t('motifs.enrichDraftTargetChanged') }}
                </div>
                <div class="min-h-0 flex-1 overflow-y-auto pr-1">
                  <div class="grid min-h-0 gap-4 xl:h-full 2xl:grid-cols-[minmax(0,1fr)_minmax(460px,0.95fr)]">
                    <div class="max-h-[min(62vh,560px)] overflow-y-auto rounded-xl bg-[#fffaf0] p-3 sm:p-4 xl:min-h-0 xl:max-h-none">
                      <div class="mb-3 text-xs font-semibold text-stone-500">{{ t('motifs.enrichProfileDraft') }}</div>
                      <div class="space-y-3">
                        <div v-if="enrichmentDraft.profile.definition" class="rounded-xl bg-white/85 p-3">
                          <div class="mb-1 text-xs font-semibold text-teal-700">{{ t('motifs.profileDefinition') }}</div>
                          <p class="text-sm leading-7 text-stone-850">{{ enrichmentDraft.profile.definition }}</p>
                        </div>
                        <div v-if="enrichmentDraft.profile.core_tension" class="rounded-xl bg-white/85 p-3">
                          <div class="mb-1 text-xs font-semibold text-rose-700">{{ t('motifs.profileCoreTension') }}</div>
                          <p class="text-sm leading-7 text-stone-850">{{ enrichmentDraft.profile.core_tension }}</p>
                        </div>
                        <div v-if="enrichmentDraft.profile.writing_functions.length" class="rounded-xl bg-white/85 p-3">
                          <div class="mb-1 text-xs font-semibold text-stone-500">{{ t('motifs.profileWritingFunctions') }}</div>
                          <ul class="space-y-1 text-sm leading-6 text-stone-750">
                            <li v-for="item in enrichmentDraft.profile.writing_functions" :key="`draft-function-${item}`">· {{ item }}</li>
                          </ul>
                        </div>
                        <details class="rounded-xl bg-white/70 p-3 text-sm leading-7 text-stone-750">
                          <summary class="cursor-pointer text-xs font-semibold text-stone-600">{{ t('motifs.enrichRawNote') }}</summary>
                          <div class="mt-2 whitespace-pre-wrap">{{ enrichmentDraft.note }}</div>
                        </details>
                      </div>
                    </div>
                    <div
                      class="max-h-[min(62vh,560px)] overflow-y-auto rounded-xl border border-stone-200 bg-white p-3 sm:p-4 xl:min-h-0 xl:max-h-none"
                      data-testid="motif-enrichment-candidates"
                    >
                      <div class="mb-3 text-xs font-semibold text-stone-500">{{ t('motifs.enrichReferenceCandidates') }}</div>
                      <div v-if="enrichmentDraft.reference_candidates.length" class="grid gap-3 min-[1700px]:grid-cols-2">
                        <label
                          v-for="(candidate, index) in enrichmentDraft.reference_candidates"
                          :key="candidateKey(candidate, index)"
                          class="block rounded-xl border p-3 text-sm leading-6"
                          :class="candidateCanImport(candidate) ? 'border-teal-100 bg-teal-50/40' : 'border-stone-200 bg-stone-50 text-stone-500'"
                        >
                          <div class="flex items-start gap-2">
                            <input
                              v-model="enrichmentApplyReferenceKeys"
                              type="checkbox"
                              :value="candidateKey(candidate, index)"
                              :disabled="!candidateCanImport(candidate)"
                              class="mt-1 h-4 w-4 shrink-0 rounded border-stone-300 text-teal-700 disabled:opacity-40"
                            />
                            <div class="min-w-0">
                              <p class="break-words text-stone-850">“{{ candidate.text }}”</p>
                              <p class="mt-2 break-words text-xs text-stone-500">
                                {{ candidate.source_author || t('motifs.candidateMissingAuthor') }} · {{ candidate.source_title || t('motifs.candidateMissingTitle') }}
                              </p>
                              <p v-if="candidate.source_note" class="mt-1 break-words text-xs text-stone-500">{{ candidate.source_note }}</p>
                              <p v-if="candidate.reason" class="mt-1 break-words rounded-lg bg-white/70 px-2 py-1 text-xs text-teal-800">{{ candidate.reason }}</p>
                              <p v-if="!candidateCanImport(candidate)" class="mt-2 text-xs text-amber-700">{{ t('motifs.candidateNeedsSource') }}</p>
                            </div>
                          </div>
                        </label>
                      </div>
                      <div v-else class="rounded-xl border border-dashed border-stone-200 bg-stone-50 p-4 text-center text-sm leading-6 text-stone-400">
                        {{ t('motifs.noReferenceCandidates') }}
                      </div>
                    </div>
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
                      <a v-if="hint.url" :href="hint.url" target="_blank" rel="noreferrer" class="break-words text-sm font-medium text-teal-700 hover:text-teal-900">{{ hint.title }}</a>
                      <p v-else class="break-words text-sm font-medium text-stone-700">{{ hint.title }}</p>
                      <p v-if="hint.note" class="mt-0.5 break-words text-xs leading-5 text-stone-500">{{ hint.note }}</p>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </div>

        <footer class="shrink-0 border-t border-stone-200 bg-white px-4 py-3 sm:px-5 sm:py-4" data-testid="motif-enrichment-footer">
          <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div class="flex flex-wrap gap-3 text-sm text-stone-600">
              <label class="flex items-center gap-2">
                <input v-model="enrichmentProfileMode" type="radio" value="merge" class="text-teal-700" />
                {{ t('motifs.enrichMergeProfile') }}
              </label>
              <label class="flex items-center gap-2">
                <input v-model="enrichmentProfileMode" type="radio" value="overwrite" class="text-teal-700" />
                {{ t('motifs.enrichOverwriteProfile') }}
              </label>
              <label class="flex items-center gap-2">
                <input v-model="enrichmentProfileMode" type="radio" value="none" class="text-teal-700" />
                {{ t('motifs.enrichSkipProfile') }}
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
              <button
                v-if="activeEnrichmentJobIsRunning"
                @click="cancelActiveEnrichmentJob"
                class="rounded-xl bg-rose-600 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-700"
              >
                {{ t('motifs.enrichCancelJob') }}
              </button>
              <button @click="closeEnrichment" class="rounded-xl bg-stone-100 px-4 py-2 text-sm font-semibold text-stone-600 hover:bg-stone-200">
                {{ activeEnrichmentJobIsRunning ? t('motifs.enrichClosePanel') : t('common.cancel') }}
              </button>
              <button
                @click="applyEnrichmentDraft"
                :disabled="enrichmentApplyDisabled"
                class="rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-40"
              >
                {{ enrichmentApplying ? t('common.saving') : (enrichmentWillApplyToExisting ? t('motifs.enrichApplyExisting') : t('motifs.enrichCreateMotif')) }}
              </button>
            </div>
          </div>
        </footer>
      </section>
    </div>
  </div>
</template>

<style scoped>
.ai-pending-bar {
  animation: motif-ai-pending-slide 1.1s ease-in-out infinite;
}

@keyframes motif-ai-pending-slide {
  0% {
    transform: translateX(-120%);
  }
  100% {
    transform: translateX(320%);
  }
}
</style>
