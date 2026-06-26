<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { aiCardApi, type AiCard, type AiCardDraft, type AiCardType } from '../../api/aiCards'
import { aiApi } from '../../api/ai'
import { articlesApi, type Entry } from '../../api/articles'
import { notesApi } from '../../api/notes'
import { errorMessage } from '../../api/base'
import { useI18n } from '../../i18n'
import TagSelector from '../../components/TagSelector.vue'
import PaneResizeHandle from '../../components/PaneResizeHandle.vue'
import ContextMenu from '../../components/ContextMenu.vue'
import { useResizablePane } from '../../composables/useResizablePane'
import {
  CARD_COMBINATION_TARGETS,
  buildCardCombinationTaskRequest,
  type CardCombinationTarget,
} from './cardCombination'

const { t } = useI18n()
const route = useRoute()
const CARD_TYPES: AiCardType[] = ['style', 'character', 'scene']

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
const combinationStyleId = ref('')
const combinationCharacterId = ref('')
const combinationSceneId = ref('')
const combinationTarget = ref<CardCombinationTarget>('scene_draft')
const combinationBrief = ref('')
const combinationResult = ref('')
const combinationLoading = ref(false)
const combinationError = ref('')
const combinationNotice = ref('')
const combinationArticles = ref<Entry[]>([])
const combinationNoteArticleId = ref('')
const combinationSaveCardType = ref<AiCardType>('scene')

const selectedCard = computed(() => cards.value.find(c => c.id === selectedCardId.value) || null)
const styleCards = computed(() => cards.value.filter((card) => card.card_type === 'style'))
const characterCards = computed(() => cards.value.filter((card) => card.card_type === 'character'))
const sceneCards = computed(() => cards.value.filter((card) => card.card_type === 'scene'))
const combinationSelectedStyle = computed(() => cards.value.find((card) => card.id === combinationStyleId.value) ?? null)
const combinationSelectedCharacter = computed(() => cards.value.find((card) => card.id === combinationCharacterId.value) ?? null)
const combinationSelectedScene = computed(() => cards.value.find((card) => card.id === combinationSceneId.value) ?? null)

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

onMounted(async () => {
  await loadCards()
  applyRouteCard()
})

watch(
  () => route.query.id,
  () => applyRouteCard()
)

onUnmounted(() => {
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
    syncCombinationDefaults()
  } catch (e) {
    console.error('Load cards failed:', e)
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

function syncCombinationDefaults() {
  if (combinationStyleId.value && !styleCards.value.some((card) => card.id === combinationStyleId.value)) {
    combinationStyleId.value = ''
  }
  if (combinationCharacterId.value && !characterCards.value.some((card) => card.id === combinationCharacterId.value)) {
    combinationCharacterId.value = ''
  }
  if (combinationSceneId.value && !sceneCards.value.some((card) => card.id === combinationSceneId.value)) {
    combinationSceneId.value = ''
  }
  combinationStyleId.value ||= styleCards.value[0]?.id ?? ''
  combinationCharacterId.value ||= characterCards.value[0]?.id ?? ''
  combinationSceneId.value ||= sceneCards.value[0]?.id ?? ''
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

function isTemplateCard(card: AiCard): boolean {
  const headings = TEMPLATE_HEADINGS[card.card_type]
  return Boolean(headings && headings.every((heading) => card.content.includes(heading)))
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
  draftPreview.value = null
  generatorError.value = ''
}

function insertTemplateIntoSelected() {
  const card = selectedCard.value
  if (!card) return
  card.content = templateFor(card.card_type)
  scheduleAutoSave()
}

async function generateDraft(mode: 'new' | 'upgrade') {
  const saved = await flushPendingCardSave()
  if (!saved) return
  const card = selectedCard.value
  const cardType = mode === 'upgrade' && card ? card.card_type : generatorType.value
  const source = mode === 'upgrade' && card && !generatorSource.value.trim()
    ? `${card.title}\n\n${card.content}`
    : generatorSource.value
  generatorLoading.value = true
  generatorError.value = ''
  draftPreview.value = null
  draftMode.value = mode
  try {
    draftPreview.value = mode === 'upgrade' && card
      ? await aiCardApi.upgradeDraft(card.id, {
        card_type: cardType,
        source_text: source,
        keep_source_quotes: keepSourceQuotes.value,
        cost_tier: 'strong',
      })
      : await aiCardApi.generateDraft({
        card_type: cardType,
        source_text: source,
        keep_source_quotes: keepSourceQuotes.value,
        cost_tier: 'strong',
      })
  } catch (e) {
    generatorError.value = errorMessage(e)
  } finally {
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
      tags: [],
    })
    cards.value.unshift(card)
    selectedCardId.value = card.id
    draftPreview.value = null
    notice.value = t('aiCards.draftSavedAsNew')
  } catch (e) {
    generatorError.value = errorMessage(e)
  }
}

async function applyDraftToCurrent() {
  const draft = draftPreview.value
  const card = selectedCard.value
  if (!draft || !card) return
  card.title = draft.title
  card.card_type = draft.card_type
  card.content = draft.content
  const saved = await persistCard(card, t('aiCards.draftApplied'))
  if (saved) draftPreview.value = null
}

function friendlyCombinationError(e: unknown): string {
  const raw = errorMessage(e)
  if (/failed to fetch|backend|connect/i.test(raw)) {
    return '后台服务正在启动或连接中，请稍后重试；如果持续出现，请重启应用。'
  }
  if (/<html|<!doctype/i.test(raw)) {
    return 'AI 服务返回了网页错误页，请检查当前 AI 配置和模型权限。'
  }
  return raw ? `AI 卡片组合生成失败：${raw.replace(/^AI task failed:\s*/i, '')}` : 'AI 卡片组合生成失败，请稍后重试。'
}

function combinationTitle(): string {
  const target = CARD_COMBINATION_TARGETS.find((item) => item.id === combinationTarget.value)?.label ?? 'AI 组合生成'
  const scene = combinationSelectedScene.value?.title || ''
  return scene ? `${target}｜${scene}` : `AI ${target}`
}

async function runCardCombination() {
  combinationLoading.value = true
  combinationError.value = ''
  combinationNotice.value = ''
  combinationResult.value = ''
  try {
    const request = buildCardCombinationTaskRequest({
      target: combinationTarget.value,
      userBrief: combinationBrief.value,
      selection: {
        style: combinationSelectedStyle.value,
        character: combinationSelectedCharacter.value,
        scene: combinationSelectedScene.value,
      },
    })
    if (!request.attachments?.length) {
      combinationError.value = '请至少选择一张风格、人物或场景卡。'
      return
    }
    const response = await aiApi.runTask(request)
    combinationResult.value = response.result.trim()
    if (!combinationResult.value) {
      combinationError.value = 'AI 没有返回可预览的组合结果。'
      return
    }
    combinationNotice.value = '已生成组合预览，尚未写入任何位置。'
  } catch (e) {
    combinationError.value = friendlyCombinationError(e)
  } finally {
    combinationLoading.value = false
  }
}

async function copyCombinationResult() {
  if (!combinationResult.value.trim()) return
  try {
    await navigator.clipboard.writeText(combinationResult.value)
    combinationNotice.value = '已复制组合结果。'
  } catch {
    combinationError.value = '复制失败，请手动选择预览内容复制。'
  }
}

async function saveCombinationAsArticle() {
  if (!combinationResult.value.trim()) return
  try {
    const article = await articlesApi.create({
      title: combinationTitle(),
      body: combinationResult.value,
      tags: ['AI组合生成'],
    })
    combinationNotice.value = `已保存为新文章：《${article.title || '无标题'}》。`
  } catch (e) {
    combinationError.value = e instanceof Error ? `保存为文章失败：${e.message}` : `保存为文章失败：${String(e)}`
  }
}

async function ensureCombinationArticles() {
  if (combinationArticles.value.length) return
  combinationArticles.value = await articlesApi.listArticles(200)
  combinationNoteArticleId.value ||= combinationArticles.value[0]?.id ?? ''
}

async function saveCombinationAsNote() {
  if (!combinationResult.value.trim()) return
  try {
    await ensureCombinationArticles()
    if (!combinationNoteArticleId.value) {
      combinationError.value = '没有可保存便签的文章，请先创建或选择文章。'
      return
    }
    await notesApi.createNote(
      combinationNoteArticleId.value,
      `【AI 卡片组合生成】\n${combinationTitle()}\n\n${combinationResult.value}`,
      false,
    )
    combinationNotice.value = '已保存为文章便签。'
  } catch (e) {
    combinationError.value = e instanceof Error ? `保存为便签失败：${e.message}` : `保存为便签失败：${String(e)}`
  }
}

async function saveCombinationAsCard() {
  if (!combinationResult.value.trim()) return
  try {
    const card = await aiCardApi.createCard({
      title: combinationTitle(),
      content: combinationResult.value,
      card_type: combinationSaveCardType.value,
      tags: ['AI组合生成'],
    })
    cards.value.unshift(card)
    selectedCardId.value = card.id
    combinationNotice.value = '已保存为新 AI 卡片。'
  } catch (e) {
    combinationError.value = e instanceof Error ? `保存为 AI 卡片失败：${e.message}` : `保存为 AI 卡片失败：${String(e)}`
  }
}

function updateSelectedTags(tags: string[]) {
  const card = selectedCard.value
  if (!card) return
  card.tags = [...tags]
  scheduleAutoSave()
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
            {{ card.content || t('library.empty') }}
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
        <section class="mb-6 rounded-xl border border-emerald-100 bg-emerald-50/60 p-5">
          <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 class="text-sm font-semibold text-emerald-950">{{ t('aiCards.generatorTitle') }}</h3>
              <p class="mt-1 text-xs text-emerald-800">{{ t('aiCards.generatorHelp') }}</p>
            </div>
            <label class="flex items-center gap-2 text-xs text-emerald-900">
              <input v-model="keepSourceQuotes" type="checkbox" class="rounded border-emerald-300" />
              {{ t('aiCards.keepSourceQuotes') }}
            </label>
          </div>
          <div class="grid gap-3 md:grid-cols-[180px_1fr]">
            <select
              v-model="generatorType"
              class="rounded-lg border border-emerald-200 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option v-for="type in CARD_TYPES" :key="type" :value="type">{{ cardTypeLabels[type] }}</option>
            </select>
            <textarea
              v-model="generatorSource"
              class="min-h-[96px] rounded-lg border border-emerald-200 bg-white p-3 text-sm leading-relaxed outline-none focus:ring-2 focus:ring-emerald-500"
              :placeholder="t('aiCards.generatorPlaceholder')"
            />
          </div>
          <div class="mt-3 flex flex-wrap items-center gap-2">
            <button
              @click="generateDraft('new')"
              :disabled="generatorLoading"
              class="rounded-lg bg-emerald-700 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50"
            >
              {{ generatorLoading && draftMode === 'new' ? t('aiCards.generating') : t('aiCards.generateDraft') }}
            </button>
            <button
              v-if="selectedCardNeedsUpgrade"
              @click="generateDraft('upgrade')"
              :disabled="generatorLoading"
              class="rounded-lg bg-amber-600 px-3 py-2 text-sm font-semibold text-white hover:bg-amber-700 disabled:opacity-50"
            >
              {{ generatorLoading && draftMode === 'upgrade' ? t('aiCards.generating') : t('aiCards.upgradeDraft') }}
            </button>
            <span v-if="selectedCardNeedsUpgrade" class="text-xs text-amber-800">{{ t('aiCards.upgradeHint') }}</span>
          </div>
          <div v-if="generatorError" class="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">{{ generatorError }}</div>
          <div v-if="draftPreview" class="mt-4 rounded-xl border border-emerald-200 bg-white p-4">
            <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
              <div>
                <div class="text-sm font-semibold text-gray-900">{{ draftPreview.title }}</div>
                <div class="text-xs text-gray-500">{{ cardTypeLabels[draftPreview.card_type] }}</div>
              </div>
              <div class="flex gap-2">
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
                <button @click="draftPreview = null" class="rounded-lg bg-gray-100 px-3 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-200">
                  {{ t('common.cancel') }}
                </button>
              </div>
            </div>
            <pre class="max-h-72 overflow-auto whitespace-pre-wrap rounded-lg bg-gray-50 p-3 text-xs leading-6 text-gray-700">{{ draftPreview.content }}</pre>
          </div>
        </section>

        <section class="mb-6 rounded-xl border border-indigo-100 bg-indigo-50/60 p-5" data-testid="ai-card-combination-panel">
          <div class="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 class="text-sm font-semibold text-indigo-950">AI 卡片组合生成</h3>
              <p class="mt-1 text-xs leading-5 text-indigo-800">手动选择风格、人物、场景卡，生成结果先进入预览，确认后再保存到文章、便签或卡片。</p>
            </div>
            <select
              v-model="combinationTarget"
              class="rounded-lg border border-indigo-200 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-400"
            >
              <option v-for="target in CARD_COMBINATION_TARGETS" :key="target.id" :value="target.id">{{ target.label }}</option>
            </select>
          </div>
          <div class="grid gap-3 md:grid-cols-3">
            <label>
              <span class="mb-1 block text-xs font-semibold text-indigo-700">风格卡</span>
              <select v-model="combinationStyleId" class="w-full rounded-lg border border-indigo-200 bg-white px-3 py-2 text-sm outline-none">
                <option value="">不使用</option>
                <option v-for="card in styleCards" :key="card.id" :value="card.id">{{ card.title || t('aiCards.untitled') }}</option>
              </select>
            </label>
            <label>
              <span class="mb-1 block text-xs font-semibold text-indigo-700">人物卡</span>
              <select v-model="combinationCharacterId" class="w-full rounded-lg border border-indigo-200 bg-white px-3 py-2 text-sm outline-none">
                <option value="">不使用</option>
                <option v-for="card in characterCards" :key="card.id" :value="card.id">{{ card.title || t('aiCards.untitled') }}</option>
              </select>
            </label>
            <label>
              <span class="mb-1 block text-xs font-semibold text-indigo-700">场景卡</span>
              <select v-model="combinationSceneId" class="w-full rounded-lg border border-indigo-200 bg-white px-3 py-2 text-sm outline-none">
                <option value="">不使用</option>
                <option v-for="card in sceneCards" :key="card.id" :value="card.id">{{ card.title || t('aiCards.untitled') }}</option>
              </select>
            </label>
          </div>
          <textarea
            v-model="combinationBrief"
            rows="3"
            class="mt-3 w-full resize-none rounded-lg border border-indigo-200 bg-white p-3 text-sm leading-6 outline-none focus:ring-2 focus:ring-indigo-400"
            placeholder="写下这次想生成什么，例如：写一场久别重逢后的克制对话，主角试探对方是否还记得过去。"
          />
          <div class="mt-3 flex flex-wrap items-center gap-2">
            <button
              type="button"
              class="rounded-lg bg-indigo-700 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-800 disabled:opacity-50"
              :disabled="combinationLoading"
              @click="runCardCombination"
            >
              {{ combinationLoading ? '生成中…' : '生成组合预览' }}
            </button>
            <span class="text-xs text-indigo-800">未勾选/选择的卡片不会进入本次 AI 上下文。</span>
          </div>
          <div v-if="combinationError" class="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">{{ combinationError }}</div>
          <div v-if="combinationNotice" class="mt-3 rounded-lg bg-blue-50 p-3 text-sm text-blue-700">{{ combinationNotice }}</div>
          <div v-if="combinationResult" class="mt-4 rounded-xl border border-indigo-200 bg-white p-4">
            <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
              <div>
                <div class="text-sm font-semibold text-gray-900">{{ combinationTitle() }}</div>
                <div class="text-xs text-gray-500">组合结果预览</div>
              </div>
              <div class="flex flex-wrap gap-2">
                <button type="button" class="rounded-lg bg-gray-100 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-200" @click="copyCombinationResult">
                  复制
                </button>
                <button type="button" class="rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700" @click="saveCombinationAsArticle">
                  存为新文章
                </button>
                <button type="button" class="rounded-lg bg-amber-600 px-3 py-2 text-xs font-semibold text-white hover:bg-amber-700" @click="ensureCombinationArticles">
                  选择文章便签
                </button>
                <select v-model="combinationSaveCardType" class="rounded-lg border border-gray-200 px-2 py-2 text-xs outline-none">
                  <option v-for="type in CARD_TYPES" :key="type" :value="type">{{ cardTypeLabels[type] }}</option>
                </select>
                <button type="button" class="rounded-lg bg-stone-900 px-3 py-2 text-xs font-semibold text-white hover:bg-stone-700" @click="saveCombinationAsCard">
                  存为新卡
                </button>
              </div>
            </div>
            <div v-if="combinationArticles.length" class="mb-3 flex flex-wrap items-center gap-2 rounded-lg bg-amber-50 p-2 text-xs">
              <span class="font-semibold text-amber-800">保存到便签：</span>
              <select v-model="combinationNoteArticleId" class="min-w-[220px] rounded-lg border border-amber-200 bg-white px-2 py-1 outline-none">
                <option v-for="article in combinationArticles" :key="article.id" :value="article.id">{{ article.title || t('articles.untitled') }}</option>
              </select>
              <button type="button" class="rounded-lg bg-amber-600 px-3 py-1.5 font-semibold text-white hover:bg-amber-700" @click="saveCombinationAsNote">
                保存便签
              </button>
            </div>
            <pre class="max-h-96 overflow-auto whitespace-pre-wrap rounded-lg bg-gray-50 p-3 text-sm leading-7 text-gray-800">{{ combinationResult }}</pre>
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
          <div v-if="selectedCardNeedsUpgrade" class="mb-5 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
            {{ t('aiCards.oldFormatHint') }}
          </div>

          <div class="mb-6">
            <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('aiCards.fields.title') }}</label>
            <input
              v-model="selectedCard.title"
              @input="scheduleAutoSave"
              class="w-full rounded-lg border border-gray-200 px-4 py-3 text-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
              :placeholder="t('aiCards.placeholders.title')"
            />
          </div>

          <div class="mb-6 grid gap-3 md:grid-cols-[1fr_auto]">
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

          <div class="mb-6">
            <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('aiCards.fields.tags') }}</label>
            <TagSelector
              v-model="selectedCard.tags"
              :suggestions="allCardTags"
              :placeholder="t('aiCards.placeholders.tags')"
              @change="updateSelectedTags"
            />
          </div>

          <div class="mb-6">
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
</style>
