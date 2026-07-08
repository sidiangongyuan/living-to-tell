<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { aiCardApi, type AiCard, type AiCardDraft, type AiCardType } from '../../api/aiCards'
import { errorMessage, isHttpStatus } from '../../api/base'
import { aiJobsApi, type AiJobSnapshot } from '../../api/aiJobs'
import { settingsApi, type AiProfile } from '../../api/settings'
import { useI18n } from '../../i18n'
import TagSelector from '../../components/TagSelector.vue'
import PaneResizeHandle from '../../components/PaneResizeHandle.vue'
import ContextMenu from '../../components/ContextMenu.vue'
import { useResizablePane } from '../../composables/useResizablePane'

const { t } = useI18n()
const route = useRoute()
const CARD_TYPES: AiCardType[] = ['style', 'character', 'scene']

type DetailMode = 'read' | 'edit'
type GeneratorMode = 'new' | 'upgrade'

interface CardSection {
  title: string
  body: string
  isReference: boolean
}

interface AiProfileOption {
  id: string
  name: string
  detail: string
}

const AI_CARD_DRAFT_JOB_ID_KEY = 'living-to-tell:ai-card-draft-job-id'
const AI_CARD_JOB_TERMINAL = new Set(['succeeded', 'failed', 'cancelled'])

const CARD_TEMPLATES: Record<AiCardType, string> = {
  style: `【语言质感】

【句法节奏】

【叙述距离】

【意象偏好】

【情绪温度】

【适用场景】

【禁忌】

【可迁移写法】

【参考原文（可选）】
`,
  character: `【角色核心】

【外在身份】

【核心欲望】

【核心恐惧】

【行动模式】

【说话方式】

【关系张力】

【成长/崩塌方向】

【可替换元素】

【参考原文（可选）】
`,
  scene: `【场景原型】

【触发条件】

【核心冲突】

【关键动作】

【情绪曲线】

【叙事功能】

【场景DNA】

【可替换元素】

【参考原文（可选）】
`,
}

const TEMPLATE_HEADINGS: Record<AiCardType, string[]> = {
  style: ['【语言质感】', '【句法节奏】', '【叙述距离】', '【意象偏好】', '【情绪温度】', '【适用场景】', '【禁忌】', '【可迁移写法】', '【参考原文（可选）】'],
  character: ['【角色核心】', '【外在身份】', '【核心欲望】', '【核心恐惧】', '【行动模式】', '【说话方式】', '【关系张力】', '【成长/崩塌方向】', '【可替换元素】', '【参考原文（可选）】'],
  scene: ['【场景原型】', '【触发条件】', '【核心冲突】', '【关键动作】', '【情绪曲线】', '【叙事功能】', '【场景DNA】', '【可替换元素】', '【参考原文（可选）】'],
}

const cards = ref<AiCard[]>([])
const selectedCardId = ref<string | null>(null)
const loading = ref(false)
const error = ref('')
const notice = ref('')
const filterType = ref<'all' | AiCardType>('all')
const sortMode = ref<'recent' | 'title'>('recent')
const searchQuery = ref('')
const pendingCardSave = ref<AiCard | null>(null)
const saveNotice = ref('')
const saveFailed = ref(false)
const newCardType = ref<AiCardType>('scene')
const cardListPane = useResizablePane({
  key: 'ai-cards:list',
  defaultSize: 300,
  minSize: 260,
  maxSize: 460,
})
const contextMenuOpen = ref(false)
const contextMenuX = ref(0)
const contextMenuY = ref(0)
const contextDeleteCardId = ref<string | null>(null)

const generatorType = ref<AiCardType>('scene')
const generatorSource = ref('')
const keepSourceQuotes = ref(false)
const generatorLoading = ref(false)
const generatorError = ref('')
const draftPreview = ref<AiCardDraft | null>(null)
const draftMode = ref<'new' | 'upgrade'>('new')
const generatorMode = ref<GeneratorMode>('new')
const generatorOpen = ref(false)
const detailMode = ref<DetailMode>('read')
const copyNotice = ref('')
const generatorProfileId = ref('default')
const aiProfiles = ref<AiProfile[]>([])
const aiProfilesLoading = ref(false)
const aiProfilesSupported = ref(true)
const activeCardJobId = ref<string | null>(null)
const activeCardJob = ref<AiJobSnapshot | null>(null)
const cardJobReconnectCount = ref(0)
const cardJobReconnectMessage = ref('')
let cardJobPollingTimer: number | null = null
const draftTargetCardId = ref<string | null>(null)

const selectedCard = computed(() => cards.value.find(c => c.id === selectedCardId.value) || null)

const selectedCardSections = computed(() => selectedCard.value ? parseCardSections(selectedCard.value.content) : [])
const draftPreviewSections = computed(() => draftPreview.value ? parseCardSections(draftPreview.value.content) : [])
const selectedCardPrompt = computed(() => selectedCard.value ? formatCardPrompt(selectedCard.value) : '')

const allCardTags = computed(() =>
  Array.from(new Set(cards.value.flatMap((card) => card.tags))).sort((a, b) => a.localeCompare(b, 'zh-CN'))
)

const filteredCards = computed(() => {
  let result = cards.value.filter((card) => CARD_TYPES.includes(card.card_type))
  if (filterType.value !== 'all') {
    result = result.filter(c => c.card_type === filterType.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(c =>
      c.title.toLowerCase().includes(q) ||
      c.content.toLowerCase().includes(q) ||
      c.tags.some((tag) => tag.toLowerCase().includes(q))
    )
  }
  return [...result].sort((a, b) => {
    if (sortMode.value === 'title') {
      return (a.title || '').localeCompare(b.title || '', 'zh-CN')
    }
    const aTime = Date.parse(a.updated_at || a.created_at || '') || 0
    const bTime = Date.parse(b.updated_at || b.created_at || '') || 0
    return bTime - aTime
  })
})

const cardTypeLabels = computed<Record<AiCardType, string>>(() => ({
  style: t('aiCards.cardTypes.style'),
  character: t('aiCards.cardTypes.character'),
  scene: t('aiCards.cardTypes.scene'),
}))

const selectedCardNeedsUpgrade = computed(() => {
  const card = selectedCard.value
  return Boolean(card && !isTemplateCard(card))
})

const aiProfileOptions = computed<AiProfileOption[]>(() => [
  { id: 'default', name: t('aiCards.defaultAiProfile'), detail: t('aiCards.defaultAiProfileDetail') },
  ...aiProfiles.value
    .filter((profile) => profile.enabled)
    .map((profile) => ({
      id: profile.id,
      name: profile.name,
      detail: [profile.provider_name, profile.model].filter(Boolean).join(' / '),
    })),
])

const selectedAiProfileLabel = computed(() =>
  aiProfileOptions.value.find((profile) => profile.id === generatorProfileId.value)?.name || t('aiCards.defaultAiProfile')
)

const generatorModeHelp = computed(() => (
  generatorMode.value === 'upgrade'
    ? t('aiCards.generatorUpgradeModeHelp')
    : t('aiCards.generatorCreateModeHelp')
))

const generatorButtonLabel = computed(() => {
  if (generatorLoading.value) return t('aiCards.generating')
  return generatorMode.value === 'upgrade' ? t('aiCards.generateUpgradeDraft') : t('aiCards.generateDraft')
})

const activeCardJobIsRunning = computed(() =>
  Boolean(activeCardJob.value && !AI_CARD_JOB_TERMINAL.has(activeCardJob.value.status))
)

const canRunGenerator = computed(() =>
  !generatorLoading.value
  && !activeCardJobIsRunning.value
  && (generatorMode.value !== 'upgrade' || Boolean(selectedCard.value))
)

const activeCardJobCanClear = computed(() =>
  Boolean(activeCardJob.value && AI_CARD_JOB_TERMINAL.has(activeCardJob.value.status))
)

const activeCardJobTitle = computed(() => {
  const job = activeCardJob.value
  if (!job) return ''
  if (job.status === 'succeeded') return t('aiCards.jobDoneTitle', { concept: job.concept })
  if (job.status === 'failed') return t('aiCards.jobFailedTitle', { concept: job.concept })
  if (job.status === 'cancelled') return t('aiCards.jobCancelledTitle', { concept: job.concept })
  return t('aiCards.jobRunningTitle', { concept: job.concept })
})

const activeCardJobDetail = computed(() => {
  const job = activeCardJob.value
  if (!job) return ''
  const elapsed = formatElapsed(job.elapsed_ms)
  if (cardJobReconnectMessage.value) return cardJobReconnectMessage.value
  if (job.status === 'failed' || job.status === 'cancelled') return job.error
  const model = [job.provider, job.model].filter(Boolean).join(' / ')
  return [job.stage_label, elapsed, model].filter(Boolean).join(' · ')
})

onMounted(async () => {
  await loadCards()
  applyRouteCard()
  void loadAiProfiles()
  restoreActiveCardJob()
})

watch(
  () => route.query.id,
  () => applyRouteCard()
)

onUnmounted(() => {
  if (copyTimer) clearTimeout(copyTimer)
  stopCardJobPolling()
  void flushPendingCardSave()
})

async function loadCards() {
  loading.value = true
  error.value = ''
  try {
    cards.value = (await aiCardApi.listCards()).filter((card) => CARD_TYPES.includes(card.card_type))
    if (cards.value.length && (!selectedCardId.value || !cards.value.some((card) => card.id === selectedCardId.value))) {
      selectedCardId.value = cards.value[0].id
    }
    if (!cards.value.length) selectedCardId.value = null
  } catch (e) {
    console.error('Load cards failed:', e)
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

async function loadAiProfiles() {
  aiProfilesLoading.value = true
  try {
    const result = await settingsApi.listAiProfiles()
    aiProfiles.value = result.profiles
    aiProfilesSupported.value = true
    if (
      generatorProfileId.value !== 'default'
      && !result.profiles.some((profile) => profile.id === generatorProfileId.value && profile.enabled)
    ) {
      generatorProfileId.value = 'default'
    }
  } catch (e) {
    if (isHttpStatus(e, 404)) {
      aiProfilesSupported.value = false
      aiProfiles.value = []
      generatorProfileId.value = 'default'
    } else {
      generatorError.value = errorMessage(e)
    }
  } finally {
    aiProfilesLoading.value = false
  }
}

function applyRouteCard() {
  const cardId = typeof route.query.id === 'string' ? route.query.id : ''
  if (cardId && cards.value.some((card) => card.id === cardId)) {
    selectedCardId.value = cardId
  }
}

function templateFor(cardType: AiCardType): string {
  return CARD_TEMPLATES[cardType]
}

function parseCardSections(content: string): CardSection[] {
  const lines = (content || '').split(/\r?\n/)
  const sections: CardSection[] = []
  let currentTitle = ''
  let currentBody: string[] = []
  let foundHeading = false

  const pushCurrent = () => {
    if (!currentTitle && !currentBody.join('').trim()) return
    sections.push({
      title: currentTitle || t('aiCards.rawContent'),
      body: currentBody.join('\n').trim(),
      isReference: currentTitle.includes('参考原文') || currentTitle.toLowerCase().includes('reference'),
    })
  }

  for (const line of lines) {
    const match = line.match(/^【([^】]+)】\s*(.*)$/)
    if (match) {
      foundHeading = true
      pushCurrent()
      currentTitle = match[1].trim()
      currentBody = match[2] ? [match[2]] : []
    } else {
      currentBody.push(line)
    }
  }
  pushCurrent()

  if (!foundHeading) return []
  return sections
}

function isTemplateCard(card: AiCard): boolean {
  const headings = TEMPLATE_HEADINGS[card.card_type]
  return Boolean(headings && headings.every((heading) => card.content.includes(heading)))
}

function compactCardPreview(card: AiCard): string {
  const firstSection = parseCardSections(card.content).find((section) => section.body && !section.isReference)
  return (firstSection?.body || card.content || t('library.empty')).replace(/\s+/g, ' ').trim()
}

function formatTags(tags: string[]): string {
  return tags.length ? tags.join(' / ') : t('aiCards.noTags')
}

function formatCardPrompt(card: AiCard): string {
  const title = card.title || t('aiCards.untitled')
  const content = (card.content || '').trim() || t('library.empty')
  return [
    `【AI Card：${title}】`,
    `${t('aiCards.promptTypeLabel')}: ${cardTypeLabels.value[card.card_type]}`,
    `${t('aiCards.promptTagsLabel')}: ${formatTags(card.tags)}`,
    `${t('aiCards.promptUsageLabel')}: ${t('aiCards.promptUsage')}`,
    '',
    content,
  ].join('\n')
}

function formatDraftPrompt(draft: AiCardDraft): string {
  return [
    `【AI Card：${draft.title || t('aiCards.untitled')}】`,
    `${t('aiCards.promptTypeLabel')}: ${cardTypeLabels.value[draft.card_type]}`,
    `${t('aiCards.promptTagsLabel')}: ${formatTags(draft.tags || [])}`,
    `${t('aiCards.promptUsageLabel')}: ${t('aiCards.promptUsage')}`,
    '',
    draft.content,
  ].join('\n')
}

async function createCard(cardType = newCardType.value) {
  const saved = await flushPendingCardSave()
  if (!saved) return
  error.value = ''
  notice.value = ''
  saveNotice.value = ''
  try {
    const card = await aiCardApi.createCard({
      title: t('aiCards.untitledByType', { type: cardTypeLabels.value[cardType] }),
      content: templateFor(cardType),
      card_type: cardType,
      tags: [],
    })
    cards.value.unshift(card)
    selectedCardId.value = card.id
    detailMode.value = 'edit'
  } catch (e) {
    console.error('Create card failed:', e)
    error.value = errorMessage(e)
  }
}

let saveTimer: number | null = null
function scheduleAutoSave() {
  const snapshot = snapshotSelectedCard()
  if (!snapshot) return
  pendingCardSave.value = snapshot
  saveNotice.value = t('aiCards.savePending')
  saveFailed.value = false
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = window.setTimeout(() => {
    void flushPendingCardSave()
  }, 600)
}

function snapshotSelectedCard(): AiCard | null {
  const card = selectedCard.value
  if (!card) return null
  return {
    ...card,
    tags: [...card.tags],
  }
}

async function flushPendingCardSave(): Promise<boolean> {
  if (saveTimer) {
    clearTimeout(saveTimer)
    saveTimer = null
  }
  const snapshot = pendingCardSave.value
  if (!snapshot) return true
  pendingCardSave.value = null
  saveNotice.value = t('aiCards.savePending')
  saveFailed.value = false
  try {
    const updated = await aiCardApi.updateCard(snapshot.id, {
      title: snapshot.title,
      content: snapshot.content,
      card_type: snapshot.card_type,
      tags: snapshot.tags,
    })
    const idx = cards.value.findIndex(c => c.id === updated.id)
    if (idx !== -1) cards.value[idx] = updated
    error.value = ''
    saveNotice.value = t('aiCards.saveSuccess')
    saveFailed.value = false
    return true
  } catch (e) {
    console.error('Save card failed:', e)
    const message = errorMessage(e)
    error.value = message
    saveNotice.value = t('aiCards.saveFailed', { message })
    saveFailed.value = true
    pendingCardSave.value = snapshot
    return false
  }
}

async function persistCard(card: AiCard, message: string): Promise<boolean> {
  if (saveTimer) {
    clearTimeout(saveTimer)
    saveTimer = null
  }
  if (pendingCardSave.value?.id === card.id) pendingCardSave.value = null
  saveNotice.value = t('aiCards.savePending')
  saveFailed.value = false
  try {
    const updated = await aiCardApi.updateCard(card.id, {
      title: card.title,
      content: card.content,
      card_type: card.card_type,
      tags: card.tags,
    })
    const idx = cards.value.findIndex(c => c.id === updated.id)
    if (idx !== -1) cards.value[idx] = updated
    saveNotice.value = message
    return true
  } catch (e) {
    const detail = errorMessage(e)
    saveFailed.value = true
    saveNotice.value = t('aiCards.saveFailed', { message: detail })
    return false
  }
}

async function deleteCard(id: string) {
  if (!confirm(t('aiCards.deleteConfirm'))) return
  if (saveTimer) {
    clearTimeout(saveTimer)
    saveTimer = null
  }
  if (pendingCardSave.value?.id === id) {
    pendingCardSave.value = null
  } else {
    const saved = await flushPendingCardSave()
    if (!saved) return
  }
  try {
    error.value = ''
    notice.value = ''
    await aiCardApi.deleteCard(id)
    cards.value = cards.value.filter(c => c.id !== id)
    if (selectedCardId.value === id) {
      selectedCardId.value = cards.value.length ? cards.value[0].id : null
    }
  } catch (e) {
    console.error('Delete card failed:', e)
    error.value = errorMessage(e)
  }
}

async function selectCard(id: string) {
  const saved = await flushPendingCardSave()
  if (!saved) return
  selectedCardId.value = id
  detailMode.value = 'read'
  generatorError.value = ''
}

function insertTemplateIntoSelected() {
  const card = selectedCard.value
  if (!card) return
  card.content = templateFor(card.card_type)
  scheduleAutoSave()
}

function formatElapsed(ms: number | null | undefined): string {
  if (!ms) return '0s'
  const totalSeconds = Math.max(0, Math.floor(ms / 1000))
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  if (minutes <= 0) return `${seconds}s`
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}

function persistActiveCardJobId(jobId: string | null) {
  if (!jobId) {
    window.localStorage.removeItem(AI_CARD_DRAFT_JOB_ID_KEY)
    return
  }
  window.localStorage.setItem(AI_CARD_DRAFT_JOB_ID_KEY, jobId)
}

function restoreActiveCardJob() {
  const jobId = window.localStorage.getItem(AI_CARD_DRAFT_JOB_ID_KEY)
  if (!jobId) return
  activeCardJobId.value = jobId
  scheduleCardJobPolling(0)
}

function stopCardJobPolling() {
  if (cardJobPollingTimer) {
    window.clearTimeout(cardJobPollingTimer)
    cardJobPollingTimer = null
  }
}

function scheduleCardJobPolling(delayMs = 1500) {
  stopCardJobPolling()
  cardJobPollingTimer = window.setTimeout(() => {
    void pollActiveCardJob()
  }, delayMs)
}

function isAiCardDraft(value: unknown): value is AiCardDraft {
  return Boolean(
    value
    && typeof value === 'object'
    && 'title' in value
    && 'card_type' in value
    && 'content' in value
  )
}

function handleCardJobSnapshot(job: AiJobSnapshot) {
  activeCardJobId.value = job.job_id
  activeCardJob.value = job
  persistActiveCardJobId(job.job_id)
  generatorLoading.value = activeCardJobIsRunning.value
  if (job.motif_id) draftTargetCardId.value = job.motif_id
  if (activeCardJobIsRunning.value) return
  stopCardJobPolling()
  if (job.status === 'succeeded' && isAiCardDraft(job.result)) {
    draftPreview.value = job.result
    generatorError.value = ''
    generatorOpen.value = true
  } else if (job.status === 'failed' || job.status === 'cancelled') {
    generatorError.value = job.error
  }
}

async function pollActiveCardJob() {
  const jobId = activeCardJobId.value
  if (!jobId) return
  try {
    const job = await aiJobsApi.getJob(jobId)
    if (activeCardJobId.value !== jobId) return
    cardJobReconnectCount.value = 0
    cardJobReconnectMessage.value = ''
    handleCardJobSnapshot(job)
    if (!AI_CARD_JOB_TERMINAL.has(job.status)) {
      scheduleCardJobPolling(1500)
    }
  } catch (e) {
    if (activeCardJobId.value !== jobId) return
    if (isHttpStatus(e, 404)) {
      const message = t('aiCards.jobMissing')
      cardJobReconnectMessage.value = message
      generatorLoading.value = false
      if (activeCardJob.value) {
        activeCardJob.value = {
          ...activeCardJob.value,
          status: 'failed',
          stage: 'failed',
          stage_label: t('aiCards.jobLocalMissing'),
          error: message,
        }
      }
      persistActiveCardJobId(null)
      stopCardJobPolling()
      return
    }
    cardJobReconnectCount.value += 1
    cardJobReconnectMessage.value = t('aiCards.jobReconnecting', { count: cardJobReconnectCount.value })
    scheduleCardJobPolling(Math.min(5000, 1500 + cardJobReconnectCount.value * 700))
  }
}

function viewActiveCardJob() {
  const job = activeCardJob.value
  if (!job) return
  generatorProfileId.value = job.profile_id || 'default'
  if (job.motif_id) draftTargetCardId.value = job.motif_id
  if (job.status === 'succeeded' && isAiCardDraft(job.result)) {
    draftPreview.value = job.result
    generatorError.value = ''
  } else if (job.status === 'failed' || job.status === 'cancelled') {
    generatorError.value = job.error
  }
  generatorOpen.value = true
  if (!AI_CARD_JOB_TERMINAL.has(job.status)) {
    scheduleCardJobPolling(1500)
  }
  void loadAiProfiles()
}

async function cancelActiveCardJob() {
  const jobId = activeCardJobId.value
  if (!jobId) return
  try {
    const job = await aiJobsApi.cancelJob(jobId)
    cardJobReconnectCount.value = 0
    cardJobReconnectMessage.value = ''
    handleCardJobSnapshot(job)
  } catch (e) {
    generatorError.value = errorMessage(e)
  }
}

function clearActiveCardJob() {
  if (activeCardJobIsRunning.value) return
  stopCardJobPolling()
  activeCardJobId.value = null
  activeCardJob.value = null
  cardJobReconnectCount.value = 0
  cardJobReconnectMessage.value = ''
  persistActiveCardJobId(null)
}

function openGenerator(mode: GeneratorMode = 'new') {
  selectGeneratorMode(mode)
  generatorOpen.value = true
  void loadAiProfiles()
}

function closeGenerator() {
  generatorOpen.value = false
}

function selectGeneratorMode(mode: GeneratorMode) {
  generatorMode.value = mode
  draftPreview.value = null
  generatorError.value = ''
}

async function runGenerator() {
  await generateDraft(generatorMode.value)
}

async function generateDraft(mode: 'new' | 'upgrade') {
  const saved = await flushPendingCardSave()
  if (!saved) return
  const card = selectedCard.value
  if (activeCardJobIsRunning.value) {
    generatorError.value = t('aiCards.jobAlreadyRunning')
    return
  }
  if (mode === 'upgrade' && !card) {
    generatorError.value = t('aiCards.selectCardBeforeUpgrade')
    return
  }
  if (mode === 'new' && !generatorSource.value.trim()) {
    generatorError.value = t('aiCards.materialRequired')
    return
  }
  const cardType = mode === 'upgrade' && card ? card.card_type : generatorType.value
  const source = mode === 'upgrade' && card && !generatorSource.value.trim()
    ? `${card.title}\n\n${card.content}`
    : generatorSource.value
  generatorLoading.value = true
  generatorError.value = ''
  draftPreview.value = null
  draftMode.value = mode
  draftTargetCardId.value = mode === 'upgrade' && card ? card.id : null
  cardJobReconnectCount.value = 0
  cardJobReconnectMessage.value = ''
  try {
    const job = await aiJobsApi.createAiCardDraftJob({
      card_id: mode === 'upgrade' && card ? card.id : null,
      card_type: cardType,
      source_text: source,
      keep_source_quotes: keepSourceQuotes.value,
      cost_tier: 'strong',
      profile_id: generatorProfileId.value,
    })
    handleCardJobSnapshot(job)
    if (!AI_CARD_JOB_TERMINAL.has(job.status)) {
      scheduleCardJobPolling(1500)
    }
  } catch (e) {
    generatorError.value = isHttpStatus(e, 404) ? t('aiCards.jobsUnsupported') : errorMessage(e)
    generatorLoading.value = false
  }
}

async function saveDraftAsNew() {
  const draft = draftPreview.value
  if (!draft) return
  try {
    const card = await aiCardApi.createCard({
      title: draft.title,
      content: draft.content,
      card_type: draft.card_type,
      tags: draft.tags || [],
    })
    cards.value.unshift(card)
    selectedCardId.value = card.id
    detailMode.value = 'read'
    draftPreview.value = null
    clearActiveCardJob()
    notice.value = t('aiCards.draftSavedAsNew')
  } catch (e) {
    generatorError.value = errorMessage(e)
  }
}

async function applyDraftToCurrent() {
  const draft = draftPreview.value
  const card = (draftTargetCardId.value ? cards.value.find((item) => item.id === draftTargetCardId.value) : null) ?? selectedCard.value
  if (!draft || !card) return
  card.title = draft.title
  card.card_type = draft.card_type
  card.content = draft.content
  card.tags = Array.from(new Set([...(card.tags || []), ...(draft.tags || [])]))
  const saved = await persistCard(card, t('aiCards.draftApplied'))
  if (saved) {
    detailMode.value = 'read'
    draftPreview.value = null
    clearActiveCardJob()
  }
}

function updateSelectedTags(tags: string[]) {
  const card = selectedCard.value
  if (!card) return
  card.tags = [...tags]
  scheduleAutoSave()
}

let copyTimer: number | null = null
async function copyText(text: string, message = t('aiCards.copyDone')) {
  try {
    await navigator.clipboard.writeText(text)
    copyNotice.value = message
    if (copyTimer) clearTimeout(copyTimer)
    copyTimer = window.setTimeout(() => {
      copyNotice.value = ''
      copyTimer = null
    }, 2200)
  } catch (e) {
    copyNotice.value = t('aiCards.copyFailed', { message: e instanceof Error ? e.message : String(e) })
  }
}

async function copySelectedCardPrompt() {
  if (!selectedCardPrompt.value) return
  await copyText(selectedCardPrompt.value, t('aiCards.copyPromptDone'))
}

async function copyDraftPrompt() {
  const draft = draftPreview.value
  if (!draft) return
  await copyText(formatDraftPrompt(draft), t('aiCards.copyPromptDone'))
}

function closeContextMenu() {
  contextMenuOpen.value = false
  contextDeleteCardId.value = null
}

function openCardContextMenu(event: MouseEvent, cardId: string) {
  event.preventDefault()
  contextDeleteCardId.value = cardId
  contextMenuX.value = Math.max(12, Math.min(event.clientX + 8, window.innerWidth - 172))
  contextMenuY.value = Math.max(12, Math.min(event.clientY + 8, window.innerHeight - 56))
  contextMenuOpen.value = true
}

function handleContextMenuSelect(item: { key: string }) {
  const cardId = contextDeleteCardId.value
  closeContextMenu()
  if (item.key === 'delete' && cardId) {
    void deleteCard(cardId)
  }
}
</script>

<template>
  <div class="flex h-full overflow-hidden bg-gray-50">
    <div
      class="min-w-0 shrink-0 bg-white border-r border-gray-200 flex flex-col"
      :style="cardListPane.paneStyle.value"
      data-testid="ai-cards-list-pane"
    >
      <div class="p-4 border-b border-gray-200">
        <div class="mb-3 flex items-center justify-between gap-2">
          <h2 class="text-xl font-bold">{{ t('aiCards.title') }}</h2>
        </div>
        <div class="mb-3 grid grid-cols-[1fr_auto] gap-2">
          <select
            v-model="newCardType"
            class="rounded-lg border border-gray-300 px-3 py-2 text-xs outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option v-for="type in CARD_TYPES" :key="type" :value="type">{{ cardTypeLabels[type] }}</option>
          </select>
          <button
            @click="createCard()"
            class="rounded-lg bg-blue-600 px-3 py-2 text-sm text-white transition-colors hover:bg-blue-700"
          >
            {{ t('aiCards.newCard') }}
          </button>
        </div>
        <input
          v-model="searchQuery"
          type="text"
          :placeholder="t('aiCards.search')"
          class="mb-3 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <div class="flex flex-wrap gap-2">
          <button
            v-for="type in ['all', ...CARD_TYPES] as const"
            :key="type"
            @click="filterType = type"
            :class="[
              'rounded-lg px-3 py-1 text-xs transition-colors',
              filterType === type
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            ]"
          >
            {{ type === 'all' ? t('aiCards.filterAll') : cardTypeLabels[type] }}
          </button>
        </div>
        <div class="mt-3">
          <select
            v-model="sortMode"
            class="w-full rounded-lg border border-gray-300 px-3 py-2 text-xs outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="recent">{{ t('aiCards.sortRecent') }}</option>
            <option value="title">{{ t('aiCards.sortTitle') }}</option>
          </select>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto">
        <div v-if="notice" class="m-3 rounded-lg bg-green-50 p-3 text-sm text-green-700">{{ notice }}</div>
        <div v-if="error" class="m-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">{{ error }}</div>
        <div v-if="loading" class="p-4 text-sm text-gray-400">{{ t('common.loading') }}</div>
        <div v-else-if="!filteredCards.length" class="p-4 text-sm text-gray-400">
          {{ t('aiCards.noCards') }}
        </div>
        <button
          v-for="card in filteredCards"
          :key="card.id"
          @click="selectCard(card.id)"
          @contextmenu="openCardContextMenu($event, card.id)"
          :data-testid="`ai-card-list-item-${card.id}`"
          :class="[
            'block w-full border-b border-gray-100 p-4 text-left transition-colors',
            selectedCardId === card.id
              ? 'border-l-4 border-l-blue-600 bg-blue-50'
              : 'hover:bg-gray-50'
          ]"
        >
          <div class="mb-1 text-sm font-semibold">{{ card.title || t('aiCards.untitled') }}</div>
          <div class="line-clamp-2 text-xs text-gray-500">
            {{ compactCardPreview(card) }}
          </div>
          <div class="mt-2 flex flex-wrap gap-2">
            <span class="rounded bg-purple-100 px-2 py-0.5 text-xs text-purple-700">
              {{ cardTypeLabels[card.card_type] }}
            </span>
            <span v-if="!isTemplateCard(card)" class="rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-700">
              {{ t('aiCards.needsUpgrade') }}
            </span>
          </div>
        </button>
      </div>
    </div>
    <PaneResizeHandle data-testid="ai-cards-list-resizer" @pointerdown="cardListPane.startResize" />

    <div class="flex-1 min-w-0 overflow-y-auto bg-white">
      <div class="mx-auto w-full max-w-5xl p-8">
        <div class="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
          <div>
            <div class="text-sm font-semibold text-gray-950">{{ t('aiCards.workspaceTitle') }}</div>
            <p class="mt-1 text-xs text-gray-500">{{ t('aiCards.workspaceHelp') }}</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <button
              type="button"
              @click="openGenerator('new')"
              class="rounded-lg bg-emerald-700 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-800"
            >
              {{ t('aiCards.openGenerator') }}
            </button>
            <button
              v-if="selectedCard"
              type="button"
              @click="openGenerator('upgrade')"
              class="rounded-lg bg-gray-100 px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-200"
            >
              {{ t('aiCards.openUpgrade') }}
            </button>
          </div>
        </div>

        <div
          v-if="activeCardJob"
          class="mb-5 rounded-2xl border p-3 shadow-sm"
          :class="activeCardJob.status === 'failed'
            ? 'border-rose-200 bg-rose-50'
            : activeCardJob.status === 'succeeded'
              ? 'border-emerald-200 bg-emerald-50'
              : activeCardJob.status === 'cancelled'
                ? 'border-gray-200 bg-gray-50'
                : 'border-amber-200 bg-amber-50'"
          data-testid="ai-card-job-bar"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <div class="truncate text-sm font-semibold text-gray-900">{{ activeCardJobTitle }}</div>
              <div class="mt-1 text-xs leading-5 text-gray-600">{{ activeCardJobDetail }}</div>
              <div v-if="activeCardJobIsRunning" class="mt-2 h-1.5 overflow-hidden rounded-full bg-white/80">
                <div class="ai-pending-bar h-full w-1/3 rounded-full bg-emerald-600"></div>
              </div>
            </div>
            <div class="flex shrink-0 flex-wrap justify-end gap-2">
              <button
                @click="viewActiveCardJob"
                class="rounded-lg bg-white px-2.5 py-1.5 text-xs font-semibold text-gray-700 ring-1 ring-gray-200 hover:bg-gray-50"
              >
                {{ activeCardJob.status === 'succeeded' ? t('aiCards.viewDraft') : t('aiCards.viewJob') }}
              </button>
              <button
                v-if="activeCardJobIsRunning"
                @click="cancelActiveCardJob"
                class="rounded-lg bg-rose-600 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-rose-700"
              >
                {{ t('aiCards.cancelJob') }}
              </button>
              <button
                v-if="activeCardJobCanClear"
                @click="clearActiveCardJob"
                class="rounded-lg bg-white px-2.5 py-1.5 text-xs font-semibold text-gray-500 ring-1 ring-gray-200 hover:bg-gray-50"
              >
                {{ t('aiCards.clearJob') }}
              </button>
            </div>
          </div>
        </div>

        <section v-if="generatorOpen" class="mb-6 overflow-hidden rounded-2xl border border-emerald-100 bg-emerald-50/60" data-testid="ai-card-generator">
          <div class="border-b border-emerald-100 bg-white/70 px-5 py-4">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 class="text-sm font-semibold text-emerald-950">{{ t('aiCards.generatorTitle') }}</h3>
                <p class="mt-1 max-w-2xl text-xs leading-5 text-emerald-800">{{ t('aiCards.generatorHelp') }}</p>
              </div>
              <div class="flex flex-wrap items-center gap-2">
                <div class="inline-flex rounded-xl bg-emerald-100 p-1 text-xs font-semibold text-emerald-900">
                  <button
                    type="button"
                    @click="selectGeneratorMode('new')"
                    :class="[
                      'rounded-lg px-3 py-1.5 transition-colors',
                      generatorMode === 'new' ? 'bg-white shadow-sm' : 'hover:bg-white/60'
                    ]"
                  >
                    {{ t('aiCards.generatorCreateMode') }}
                  </button>
                  <button
                    type="button"
                    @click="selectGeneratorMode('upgrade')"
                    :disabled="!selectedCard"
                    :class="[
                      'rounded-lg px-3 py-1.5 transition-colors disabled:cursor-not-allowed disabled:opacity-50',
                      generatorMode === 'upgrade' ? 'bg-white shadow-sm' : 'hover:bg-white/60'
                    ]"
                  >
                    {{ t('aiCards.generatorUpgradeMode') }}
                  </button>
                </div>
                <button
                  type="button"
                  @click="closeGenerator"
                  class="rounded-lg bg-gray-100 px-3 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-200"
                >
                  {{ t('common.close') }}
                </button>
              </div>
            </div>
          </div>

          <div class="grid gap-5 p-5 lg:grid-cols-[minmax(0,1fr)_minmax(320px,0.9fr)]">
            <div class="space-y-4">
              <div>
                <div class="mb-2 text-xs font-semibold uppercase tracking-wide text-emerald-900">{{ t('aiCards.fields.type') }}</div>
                <div class="flex flex-wrap gap-2">
                  <button
                    v-for="type in CARD_TYPES"
                    :key="type"
                    type="button"
                    @click="generatorType = type"
                    :aria-label="t('aiCards.generatorTypeAria', { type: cardTypeLabels[type] })"
                    :class="[
                      'rounded-lg border px-3 py-2 text-xs font-semibold transition-colors',
                      generatorType === type
                        ? 'border-emerald-700 bg-emerald-700 text-white'
                        : 'border-emerald-200 bg-white text-emerald-900 hover:bg-emerald-50'
                    ]"
                  >
                    {{ cardTypeLabels[type] }}
                  </button>
                </div>
              </div>
              <label class="block">
                <span class="mb-2 block text-xs font-semibold uppercase tracking-wide text-emerald-900">{{ t('aiCards.materialLabel') }}</span>
                <textarea
                  v-model="generatorSource"
                  class="min-h-[150px] w-full resize-y rounded-xl border border-emerald-200 bg-white p-3 text-sm leading-relaxed outline-none focus:ring-2 focus:ring-emerald-500"
                  :placeholder="t('aiCards.generatorPlaceholder')"
                />
              </label>
              <label class="block">
                <span class="mb-2 block text-xs font-semibold uppercase tracking-wide text-emerald-900">{{ t('aiCards.aiProfileLabel') }}</span>
                <select
                  v-model="generatorProfileId"
                  :disabled="aiProfilesLoading || !aiProfilesSupported"
                  class="w-full rounded-xl border border-emerald-200 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500 disabled:bg-gray-50 disabled:text-gray-400"
                >
                  <option v-for="profile in aiProfileOptions" :key="profile.id" :value="profile.id">
                    {{ profile.name }}{{ profile.detail ? ` · ${profile.detail}` : '' }}
                  </option>
                </select>
                <p class="mt-1 text-xs text-emerald-700">
                  {{ aiProfilesSupported ? t('aiCards.aiProfileHelp', { profile: selectedAiProfileLabel }) : t('aiCards.aiProfilesUnsupported') }}
                </p>
              </label>
              <div class="flex flex-wrap items-center justify-between gap-3">
                <label class="flex items-center gap-2 text-xs text-emerald-900">
                  <input v-model="keepSourceQuotes" type="checkbox" class="rounded border-emerald-300" />
                  {{ t('aiCards.keepSourceQuotes') }}
                </label>
                <button
                  @click="runGenerator"
                  :disabled="!canRunGenerator"
                  class="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {{ generatorButtonLabel }}
                </button>
              </div>
              <p class="text-xs leading-5 text-emerald-800">{{ generatorModeHelp }}</p>
              <div v-if="generatorError" class="rounded-lg bg-red-50 p-3 text-sm text-red-700">{{ generatorError }}</div>
            </div>

            <div class="rounded-xl border border-emerald-100 bg-white p-4" data-testid="ai-card-draft-preview">
              <div v-if="activeCardJobIsRunning" class="mb-4 rounded-lg border border-amber-100 bg-amber-50 p-3">
                <div class="text-sm font-semibold text-amber-950">{{ activeCardJobTitle }}</div>
                <div class="mt-1 text-xs leading-5 text-amber-800">{{ activeCardJobDetail }}</div>
                <div class="mt-3 h-1.5 overflow-hidden rounded-full bg-white">
                  <div class="ai-pending-bar h-full w-1/3 rounded-full bg-emerald-600"></div>
                </div>
                <button
                  type="button"
                  @click="cancelActiveCardJob"
                  class="mt-3 rounded-lg bg-rose-600 px-3 py-2 text-xs font-semibold text-white hover:bg-rose-700"
                >
                  {{ t('aiCards.cancelJob') }}
                </button>
              </div>
              <div v-if="draftPreview" class="space-y-4">
                <div class="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div class="text-sm font-semibold text-gray-900">{{ draftPreview.title }}</div>
                    <div class="mt-1 text-xs text-gray-500">{{ cardTypeLabels[draftPreview.card_type] }}</div>
                    <div v-if="draftPreview.provider || draftPreview.model" class="mt-1 text-[11px] text-gray-400">
                      {{ [draftPreview.provider, draftPreview.model, draftPreview.elapsed_ms ? formatElapsed(draftPreview.elapsed_ms) : ''].filter(Boolean).join(' · ') }}
                    </div>
                  </div>
                  <div class="flex flex-wrap gap-2">
                    <button @click="copyDraftPrompt" class="rounded-lg bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-800 hover:bg-emerald-100">
                      {{ t('aiCards.copyPrompt') }}
                    </button>
                    <button @click="draftPreview = null" class="rounded-lg bg-gray-100 px-3 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-200">
                      {{ t('aiCards.discardDraft') }}
                    </button>
                  </div>
                </div>
                <div v-if="draftPreview.tags?.length" class="flex flex-wrap gap-2">
                  <span class="text-xs font-semibold text-gray-500">{{ t('aiCards.recommendedTags') }}</span>
                  <span v-for="tag in draftPreview.tags" :key="tag" class="rounded-full bg-purple-50 px-2 py-0.5 text-xs text-purple-700">{{ tag }}</span>
                </div>
                <div class="max-h-80 space-y-3 overflow-auto pr-1">
                  <div
                    v-for="section in draftPreviewSections"
                    :key="section.title"
                    class="rounded-lg border border-gray-100 bg-gray-50 p-3"
                  >
                    <div class="mb-1 text-xs font-semibold text-gray-700">【{{ section.title }}】</div>
                    <p class="whitespace-pre-wrap text-xs leading-5 text-gray-700">{{ section.body || t('aiCards.sectionEmpty') }}</p>
                  </div>
                  <pre v-if="!draftPreviewSections.length" class="whitespace-pre-wrap rounded-lg bg-gray-50 p-3 text-xs leading-6 text-gray-700">{{ draftPreview.content }}</pre>
                </div>
                <div class="flex flex-wrap justify-end gap-2 border-t border-gray-100 pt-3">
                  <button @click="saveDraftAsNew" class="rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700">
                    {{ t('aiCards.saveDraftAsNew') }}
                  </button>
                  <button
                    v-if="selectedCard"
                    @click="applyDraftToCurrent"
                    class="rounded-lg bg-stone-900 px-3 py-2 text-xs font-semibold text-white hover:bg-stone-700"
                  >
                    {{ t('aiCards.applyDraft') }}
                  </button>
                </div>
              </div>
              <div v-else class="flex min-h-[240px] flex-col justify-center rounded-lg border border-dashed border-emerald-200 bg-emerald-50/40 p-5 text-sm text-emerald-900">
                <div class="font-semibold">{{ t('aiCards.draftEmptyTitle') }}</div>
                <p class="mt-2 text-xs leading-5">{{ t('aiCards.draftEmptyBody') }}</p>
              </div>
            </div>
          </div>
        </section>

        <div v-if="selectedCard" class="w-full">
          <div
            v-if="saveNotice"
            :class="[
              'mb-5 rounded-lg px-3 py-2 text-sm',
              saveFailed ? 'bg-red-50 text-red-700' : 'bg-blue-50 text-blue-700',
            ]"
          >
            {{ saveNotice }}
          </div>
          <div v-if="copyNotice" class="mb-5 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
            {{ copyNotice }}
          </div>
          <div v-if="selectedCardNeedsUpgrade" class="mb-5 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
            {{ t('aiCards.oldFormatHint') }}
          </div>

          <article class="mb-6 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
            <div class="flex flex-wrap items-start justify-between gap-4">
              <div class="min-w-0">
                <div class="mb-2 flex flex-wrap items-center gap-2">
                  <span class="rounded-full bg-purple-100 px-2.5 py-1 text-xs font-semibold text-purple-700">
                    {{ cardTypeLabels[selectedCard.card_type] }}
                  </span>
                  <span v-if="selectedCardNeedsUpgrade" class="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-700">
                    {{ t('aiCards.needsUpgrade') }}
                  </span>
                </div>
                <h1 class="break-words text-2xl font-bold text-gray-950">{{ selectedCard.title || t('aiCards.untitled') }}</h1>
                <div class="mt-3 flex flex-wrap gap-2">
                  <span v-if="!selectedCard.tags.length" class="text-xs text-gray-400">{{ t('aiCards.noTags') }}</span>
                  <span v-for="tag in selectedCard.tags" :key="tag" class="rounded-full bg-gray-100 px-2.5 py-1 text-xs text-gray-600">
                    {{ tag }}
                  </span>
                </div>
              </div>
              <div class="flex flex-wrap justify-end gap-2">
                <button @click="copySelectedCardPrompt" class="rounded-lg bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-800 hover:bg-emerald-100">
                  {{ t('aiCards.copyPrompt') }}
                </button>
                <button
                  @click="detailMode = detailMode === 'read' ? 'edit' : 'read'"
                  class="rounded-lg bg-stone-900 px-3 py-2 text-xs font-semibold text-white hover:bg-stone-700"
                >
                  {{ detailMode === 'read' ? t('aiCards.editMode') : t('aiCards.readMode') }}
                </button>
              </div>
            </div>
            <div class="mt-4 text-xs text-gray-400">
              {{ t('articles.createdAt') }} {{ selectedCard.created_at?.slice(0, 10) || '—' }}
            </div>
          </article>

          <div v-if="detailMode === 'read'" class="space-y-6" data-testid="ai-card-read-view">
            <section class="rounded-2xl border border-gray-200 bg-white p-5">
              <div class="mb-4 flex items-center justify-between gap-3">
                <h3 class="text-sm font-semibold text-gray-900">{{ t('aiCards.contentSections') }}</h3>
                <button @click="detailMode = 'edit'" class="rounded-lg bg-gray-100 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-200">
                  {{ t('aiCards.editMode') }}
                </button>
              </div>
              <div v-if="selectedCardSections.length" class="grid gap-3 md:grid-cols-2">
                <div
                  v-for="section in selectedCardSections"
                  :key="section.title"
                  :class="[
                    'rounded-xl border p-4',
                    section.isReference ? 'border-amber-100 bg-amber-50/50' : 'border-gray-100 bg-gray-50'
                  ]"
                >
                  <div class="mb-2 text-sm font-semibold text-gray-900">【{{ section.title }}】</div>
                  <p class="whitespace-pre-wrap text-sm leading-6 text-gray-700">{{ section.body || t('aiCards.sectionEmpty') }}</p>
                </div>
              </div>
              <div v-else class="rounded-xl bg-gray-50 p-4">
                <pre class="whitespace-pre-wrap text-sm leading-7 text-gray-700">{{ selectedCard.content || t('aiCards.noReadableContent') }}</pre>
              </div>
            </section>
          </div>

          <div v-else class="space-y-6">
            <div>
              <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('aiCards.fields.title') }}</label>
              <input
                v-model="selectedCard.title"
                @input="scheduleAutoSave"
                class="w-full rounded-lg border border-gray-200 px-4 py-3 text-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                :placeholder="t('aiCards.placeholders.title')"
              />
            </div>

            <div class="grid gap-3 md:grid-cols-[1fr_auto]">
              <div>
                <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('aiCards.fields.type') }}</label>
                <select
                  v-model="selectedCard.card_type"
                  @change="scheduleAutoSave"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option v-for="type in CARD_TYPES" :key="type" :value="type">{{ cardTypeLabels[type] }}</option>
                </select>
              </div>
              <div class="flex items-end">
                <button
                  @click="insertTemplateIntoSelected"
                  class="rounded-lg bg-gray-100 px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-200"
                >
                  {{ t('aiCards.insertTemplate') }}
                </button>
              </div>
            </div>

            <div>
              <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('aiCards.fields.tags') }}</label>
              <TagSelector
                v-model="selectedCard.tags"
                :suggestions="allCardTags"
                :placeholder="t('aiCards.placeholders.tags')"
                @change="updateSelectedTags"
              />
            </div>

            <div>
              <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('aiCards.fields.content') }}</label>
              <textarea
                v-model="selectedCard.content"
                @input="scheduleAutoSave"
                class="min-h-[420px] w-full resize-y rounded-lg border border-gray-200 p-4 font-mono text-sm leading-relaxed focus:outline-none focus:ring-2 focus:ring-blue-500"
                :placeholder="t('aiCards.placeholders.content')"
              />
              <p class="mt-2 text-xs text-gray-500">
                {{ t('aiCards.contentHint') }}
              </p>
            </div>

            <div class="flex items-center justify-between border-t border-gray-200 pt-4">
              <div class="text-xs text-gray-400">
                {{ t('articles.createdAt') }} {{ selectedCard.created_at?.slice(0, 10) || '—' }}
              </div>
              <button
                @click="deleteCard(selectedCard.id)"
                class="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600 transition-colors hover:bg-red-100"
              >
                {{ t('aiCards.deleteCard') }}
              </button>
            </div>
          </div>
        </div>
        <div v-else class="flex h-80 items-center justify-center text-gray-400">
          {{ t('aiCards.selectOrCreate') }}
        </div>
      </div>
    </div>
    <ContextMenu
      :open="contextMenuOpen"
      :x="contextMenuX"
      :y="contextMenuY"
      :items="[{ key: 'delete', label: t('aiCards.deleteCard'), danger: true }]"
      @close="closeContextMenu"
      @select="handleContextMenuSelect"
    />
  </div>
</template>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.ai-pending-bar {
  animation: ai-pending-slide 1.4s ease-in-out infinite;
}

@keyframes ai-pending-slide {
  0% {
    transform: translateX(-120%);
  }
  50% {
    transform: translateX(90%);
  }
  100% {
    transform: translateX(240%);
  }
}
</style>
