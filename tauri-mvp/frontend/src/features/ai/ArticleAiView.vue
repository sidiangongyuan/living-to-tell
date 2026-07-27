<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { articlesApi, type Entry } from '../../api/articles'
import { aiApi, type AiContextAttachment, type AiTaskPreset, type AiTaskPresetMap } from '../../api/ai'
import type { AiCard } from '../../api/aiCards'
import type { Reference } from '../../api/library'
import { notesApi, type WritingNote } from '../../api/notes'
import { errorMessage } from '../../api/base'
import { settingsApi, type AiProfile } from '../../api/settings'
import { useI18n } from '../../i18n'
import ArticleAiReferencePicker from './ArticleAiReferencePicker.vue'
import ArticleAiCardPicker from './ArticleAiCardPicker.vue'
import ArticleAiNotePicker from './ArticleAiNotePicker.vue'
import ArticleAiPresetPicker from './ArticleAiPresetPicker.vue'
import GuidedTourOverlay, { type GuidedTourStep } from '../../components/GuidedTourOverlay.vue'
import TourInvitation from '../../components/TourInvitation.vue'
import { useSettingsStore } from '../../stores/settings'
import { buildTaskRequestOptions, cloneControls, createDefaultControls, type FocusTaskType } from './taskControls'
import { useArticleTaskRunStore } from './articleTaskRunStore'
import { toggleAiTaskProfileSelection } from './profileSelection'
import { utf16OffsetToCodePointOffset } from './selectionOffsets'
import {
  BUILT_IN_WRITING_PRESETS,
  controlsForBuiltInPreset,
  customPresetControls,
  defaultPresetForTask,
  missingPresetRequirements,
  type WritingPresetDefinition,
} from './writingPresets'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const taskRun = useArticleTaskRunStore()
const settings = useSettingsStore()

const articles = ref<Entry[]>([])
const selectedArticleId = ref('')
const selectionStart = ref<number | null>(null)
const selectionEnd = ref<number | null>(null)
const profiles = ref<AiProfile[]>([])
const defaultProfileId = ref<string | null>(null)
const selectedProfileIds = ref<string[]>([])
const profilePickerOpen = ref(false)
const taskType = ref<FocusTaskType>('polish')
const controls = ref(createDefaultControls())
const moreOpen = ref(false)
const error = ref('')
const notice = ref('')

const presets = ref<AiTaskPresetMap>({})
const selectedPresetId = ref(`system:${defaultPresetForTask('polish').id}`)
const notes = ref<WritingNote[]>([])
const selectedCards = ref<AiCard[]>([])
const selectedNotes = ref<WritingNote[]>([])
const selectedReferences = ref<Reference[]>([])
const referencePickerOpen = ref(false)
const cardPickerOpen = ref(false)
const notePickerOpen = ref(false)
const contextLoading = ref(false)
let articleContextToken = 0
const tourInviteOpen = ref(false)
const tourOpen = ref(false)
const tourStepIndex = ref(0)
const tourMoreOpenSnapshot = ref(false)

const tasks = computed(() => [
  { id: 'polish' as const, title: t('articleAi.tasks.polish'), help: t('articleAi.tasks.polishHelp') },
  { id: 'rewrite' as const, title: t('articleAi.tasks.rewrite'), help: t('articleAi.tasks.rewriteHelp') },
  { id: 'expand' as const, title: t('articleAi.tasks.expand'), help: t('articleAi.tasks.expandHelp') },
  { id: 'continue' as const, title: t('articleAi.tasks.continue'), help: t('articleAi.tasks.continueHelp') },
])

const selectedArticle = computed(() => articles.value.find((item) => item.id === selectedArticleId.value) ?? null)
const selectedText = computed(() => {
  const article = selectedArticle.value
  if (!article) return ''
  if (selectionStart.value !== null && selectionEnd.value !== null && selectionEnd.value > selectionStart.value) {
    return article.body.slice(selectionStart.value, selectionEnd.value)
  }
  return article.body
})
const hasSelection = computed(() => selectionStart.value !== null && selectionEnd.value !== null && selectionEnd.value > selectionStart.value)
const enabledProfiles = computed(() => profiles.value.filter((item) => item.enabled))
const selectedProfiles = computed(() => enabledProfiles.value.filter((item) => selectedProfileIds.value.includes(item.id)))
const selectedReferenceChars = computed(() => selectedReferences.value.reduce((total, item) => total + item.content.length, 0))
const selectedCardChars = computed(() => selectedCards.value.reduce((total, item) => total + item.content.length, 0))
const selectedNoteChars = computed(() => selectedNotes.value.reduce((total, item) => total + item.body.length, 0))
const currentRun = computed(() => taskRun.run)
const taskPresets = computed(() => presets.value[taskType.value] ?? [])
const activeSystemPreset = computed<WritingPresetDefinition | null>(() => {
  if (!selectedPresetId.value.startsWith('system:')) return null
  const id = selectedPresetId.value.slice('system:'.length)
  return BUILT_IN_WRITING_PRESETS.find((item) => item.id === id && item.taskType === taskType.value) ?? null
})
const missingRequirements = computed(() => missingPresetRequirements(activeSystemPreset.value, controls.value))
const canRun = computed(() => Boolean(
  selectedArticle.value?.body.trim()
  && selectedProfileIds.value.length
  && !taskRun.running
  && !taskRun.creating
  && !missingRequirements.value.length,
))
const showViewpointControls = computed(() => activeSystemPreset.value?.requirements?.includes('viewpoint_or_tense') ?? false)
const showArgumentDirection = computed(() => activeSystemPreset.value?.requirements?.includes('argument_direction') ?? false)
const showSceneFocus = computed(() => activeSystemPreset.value?.requirements?.includes('scene_focus') ?? false)
const tourSteps = computed<GuidedTourStep[]>(() => [
  { id: 'target', title: t('articleAiTour.targetTitle'), body: t('articleAiTour.targetBody'), target: '[data-tour="ai-target"]' },
  { id: 'task', title: t('articleAiTour.taskTitle'), body: t('articleAiTour.taskBody'), target: '[data-tour="ai-tasks"]' },
  { id: 'presets', title: t('articleAiTour.presetsTitle'), body: t('articleAiTour.presetsBody'), target: '[data-tour="ai-presets"]' },
  { id: 'context', title: t('articleAiTour.contextTitle'), body: t('articleAiTour.contextBody'), target: '[data-tour="ai-context-sources"]' },
  { id: 'picker', title: t('articleAiTour.pickerTitle'), body: t('articleAiTour.pickerBody'), target: '[data-testid="article-ai-reference-picker"]', onEnter: () => { referencePickerOpen.value = true } },
  { id: 'models', title: t('articleAiTour.modelsTitle'), body: t('articleAiTour.modelsBody'), target: '[data-tour="ai-model-run"]', onEnter: () => { referencePickerOpen.value = false } },
  { id: 'results', title: t('articleAiTour.resultsTitle'), body: t('articleAiTour.resultsBody'), target: '[data-tour="ai-model-run"]' },
  { id: 'apply', title: t('articleAiTour.applyTitle'), body: t('articleAiTour.applyBody'), target: '[data-tour="ai-model-run"]' },
])
const tourProgress = computed(() => t('guidedTours.progress', { current: tourStepIndex.value + 1, total: tourSteps.value.length }))

watch(selectedArticleId, () => {
  if (selectedArticleId.value !== route.query.scope_id) {
    selectionStart.value = null
    selectionEnd.value = null
  }
  notes.value = []
  selectedNotes.value = []
  notePickerOpen.value = false
})

watch(taskType, (value) => selectSystemPreset(defaultPresetForTask(value).id))

function parseQueryNumber(value: unknown): number | null {
  if (typeof value !== 'string' || !/^\d+$/.test(value)) return null
  return Number(value)
}

async function loadInitial() {
  error.value = ''
  try {
    const [articleList, profileList, presetList] = await Promise.all([
      articlesApi.listArticles(500),
      settingsApi.listAiProfiles(),
      aiApi.listTaskPresets().catch(() => ({})),
    ])
    articles.value = articleList
    profiles.value = profileList.profiles
    defaultProfileId.value = profileList.default_profile_id ?? null
    presets.value = presetList
    const routedId = typeof route.query.scope_id === 'string'
      ? route.query.scope_id
      : typeof route.query.article_id === 'string'
        ? route.query.article_id
        : ''
    selectedArticleId.value = articleList.some((item) => item.id === routedId) ? routedId : articleList[0]?.id ?? ''
    const start = parseQueryNumber(route.query.selection_start)
    const end = parseQueryNumber(route.query.selection_end)
    const article = articleList.find((item) => item.id === selectedArticleId.value)
    if (article && start !== null && end !== null && start >= 0 && end > start && end <= article.body.length) {
      selectionStart.value = start
      selectionEnd.value = end
    }
    const routedTask = String(route.query.task || '')
    if (['polish', 'rewrite', 'expand', 'continue'].includes(routedTask)) taskType.value = routedTask as FocusTaskType
    selectSystemPreset(defaultPresetForTask(taskType.value).id)
    selectedProfileIds.value = defaultProfileId.value ? [defaultProfileId.value] : []
    await taskRun.hydrate()
  } catch (e) {
    error.value = errorMessage(e)
  }
}

function startAiTour() {
  tourMoreOpenSnapshot.value = moreOpen.value
  moreOpen.value = false
  referencePickerOpen.value = false
  cardPickerOpen.value = false
  notePickerOpen.value = false
  profilePickerOpen.value = false
  tourInviteOpen.value = false
  tourStepIndex.value = 0
  tourOpen.value = true
}

function finishAiTour() {
  tourOpen.value = false
  referencePickerOpen.value = false
  cardPickerOpen.value = false
  notePickerOpen.value = false
  moreOpen.value = tourMoreOpenSnapshot.value
  settings.completeTour('ai-edit')
  void clearAiTourQuery()
}

function dismissAiTour() {
  tourInviteOpen.value = false
  settings.dismissTour('ai-edit')
}

async function clearAiTourQuery() {
  if (!route.query.tour) return
  const query = { ...route.query }
  delete query.tour
  await router.replace({ name: 'ai', query })
}

async function loadArticleContext() {
  if (!selectedArticleId.value) return
  const articleId = selectedArticleId.value
  const token = ++articleContextToken
  contextLoading.value = true
  try {
    const items = await notesApi.listNotes(articleId, true)
    if (token !== articleContextToken || selectedArticleId.value !== articleId) return
    notes.value = items
  } catch (e) {
    if (token !== articleContextToken || selectedArticleId.value !== articleId) return
    error.value = errorMessage(e)
  } finally {
    if (token === articleContextToken) contextLoading.value = false
  }
}

function toggleProfile(profileId: string) {
  selectedProfileIds.value = toggleAiTaskProfileSelection(
    selectedProfileIds.value,
    profileId,
    defaultProfileId.value ?? '',
  )
}

function selectSystemPreset(presetId: string) {
  const preset = BUILT_IN_WRITING_PRESETS.find((item) => item.id === presetId && item.taskType === taskType.value)
  if (!preset) return
  selectedPresetId.value = `system:${preset.id}`
  controls.value = controlsForBuiltInPreset(preset, locale.value)
}

function selectCustomPreset(presetId: string) {
  const preset = taskPresets.value.find((item) => item.id === presetId)
  if (!preset) return
  selectedPresetId.value = `custom:${preset.id}`
  controls.value = customPresetControls(preset)
}

async function saveCustomPreset(name: string) {
  const normalized = name.trim()
  if (!normalized) return
  if (taskPresets.value.some((item) => item.name.toLocaleLowerCase() === normalized.toLocaleLowerCase())) {
    error.value = t('articleAi.presets.duplicateName')
    return
  }
  const preset: AiTaskPreset = {
    id: globalThis.crypto?.randomUUID?.() ?? `preset-${Date.now()}`,
    task_type: taskType.value,
    name: normalized,
    controls: cloneControls(controls.value) as unknown as Record<string, unknown>,
  }
  const next = { ...presets.value, [taskType.value]: [...taskPresets.value, preset] }
  if (!await persistCustomPresets(next)) return
  selectedPresetId.value = `custom:${preset.id}`
  notice.value = t('articleAi.presets.saved')
}

async function renameCustomPreset(payload: { id: string; name: string }) {
  const normalized = payload.name.trim()
  if (!normalized) return
  if (taskPresets.value.some((item) => item.id !== payload.id && item.name.toLocaleLowerCase() === normalized.toLocaleLowerCase())) {
    error.value = t('articleAi.presets.duplicateName')
    return
  }
  const next = {
    ...presets.value,
    [taskType.value]: taskPresets.value.map((item) => item.id === payload.id ? { ...item, name: normalized } : item),
  }
  if (!await persistCustomPresets(next)) return
  notice.value = t('articleAi.presets.renamed')
}

async function deleteCustomPreset(presetId: string) {
  const next = {
    ...presets.value,
    [taskType.value]: taskPresets.value.filter((item) => item.id !== presetId),
  }
  if (!await persistCustomPresets(next)) return
  if (selectedPresetId.value === `custom:${presetId}`) {
    selectSystemPreset(defaultPresetForTask(taskType.value).id)
  }
  notice.value = t('articleAi.presets.deleted')
}

async function persistCustomPresets(next: AiTaskPresetMap): Promise<boolean> {
  error.value = ''
  try {
    presets.value = await aiApi.saveTaskPresets(next)
    return true
  } catch (e) {
    error.value = errorMessage(e)
    return false
  }
}

function attachments(): AiContextAttachment[] {
  return [
    ...selectedCards.value.map((item) => ({ kind: 'ai_card', ref_id: item.id, name: item.title, body: item.content })),
    ...selectedNotes.value.map((item) => ({ kind: 'writing_note', ref_id: item.id, name: noteName(item), body: item.body })),
    ...selectedReferences.value.map((item) => ({
      kind: 'style_specimen',
      ref_id: item.id,
      name: referenceName(item),
      body: referenceAttachmentBody(item),
    })),
  ]
}

function noteName(note: WritingNote): string {
  return note.body.trim().split(/\r?\n/)[0]?.slice(0, 48) || t('articleAi.notePicker.untitled')
}

function referenceName(reference: Reference): string {
  const title = reference.source_title.trim()
    ? `《${reference.source_title.trim()}》`
    : t('articleAi.referencePicker.untitled')
  return reference.source_author.trim() ? `${title} · ${reference.source_author.trim()}` : title
}

function referenceUsageLabel(reference: Reference): string {
  const key = `library.${reference.usage_kind || 'other'}`
  const translated = t(key)
  return translated === key ? t('library.other') : translated
}

function referenceAttachmentBody(reference: Reference): string {
  const tags = reference.tags.length ? reference.tags.join('、') : t('articleAi.referenceMeta.none')
  const note = reference.personal_note.trim() || t('articleAi.referenceMeta.none')
  return [
    `${t('articleAi.referenceMeta.usage')}：${referenceUsageLabel(reference)}`,
    `${t('articleAi.referenceMeta.tags')}：${tags}`,
    `${t('articleAi.referenceMeta.note')}：${note}`,
    `${t('articleAi.referenceMeta.text')}：`,
    reference.content,
  ].join('\n')
}

function confirmReferences(references: Reference[]) {
  selectedReferences.value = references
  referencePickerOpen.value = false
}

function removeReference(referenceId: string) {
  selectedReferences.value = selectedReferences.value.filter((item) => item.id !== referenceId)
}

function clearReferences() {
  selectedReferences.value = []
}

function confirmCards(cards: AiCard[]) {
  selectedCards.value = cards
  cardPickerOpen.value = false
}

function confirmNotes(items: WritingNote[]) {
  selectedNotes.value = items
  notePickerOpen.value = false
}

async function openNotePicker() {
  notePickerOpen.value = true
  await loadArticleContext()
}

function openCardsLibrary() {
  cardPickerOpen.value = false
  void router.push({ name: 'ai-cards' })
}

function openCurrentArticle() {
  notePickerOpen.value = false
  void router.push({ name: 'articles', query: { id: selectedArticleId.value } })
}

function openReferenceLibrary() {
  referencePickerOpen.value = false
  void router.push({ name: 'library' })
}

async function runTask() {
  if (!selectedArticle.value) return
  error.value = ''
  notice.value = ''
  const options = buildTaskRequestOptions(taskType.value, controls.value, locale.value)
  try {
    const run = await taskRun.create({
      article_id: selectedArticle.value.id,
      task_type: taskType.value,
      profile_ids: [...selectedProfileIds.value],
      selection_start: hasSelection.value && selectionStart.value !== null
        ? utf16OffsetToCodePointOffset(selectedArticle.value.body, selectionStart.value)
        : null,
      selection_end: hasSelection.value && selectionEnd.value !== null
        ? utf16OffsetToCodePointOffset(selectedArticle.value.body, selectionEnd.value)
        : null,
      attachments: attachments(),
      preset_snapshot: {
        id: selectedPresetId.value,
        name: activeSystemPreset.value
          ? (locale.value === 'en' ? activeSystemPreset.value.name.en : activeSystemPreset.value.name.zh)
          : taskPresets.value.find((item) => `custom:${item.id}` === selectedPresetId.value)?.name ?? '',
        tier: activeSystemPreset.value?.tier ?? 'custom',
        genre: activeSystemPreset.value?.genres[0] ?? 'custom',
        built_in: Boolean(activeSystemPreset.value),
      },
      control_snapshot: cloneControls(controls.value) as unknown as Record<string, unknown>,
      ...options,
    })
    await router.push({ name: 'ai-results', params: { runId: run.run_id } })
  } catch (e) {
    error.value = errorMessage(e)
  }
}

async function cancelRun() {
  if (!window.confirm(t('articleAi.cancelConfirm'))) return
  try {
    await taskRun.cancel()
  } catch (e) {
    error.value = errorMessage(e)
  }
}

async function clearRun() {
  if (!window.confirm(t('articleAi.clearConfirm'))) return
  try {
    await taskRun.clear()
  } catch (e) {
    error.value = errorMessage(e)
  }
}

function formatElapsed(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`
}

function openArticle() {
  const id = currentRun.value?.article_id || selectedArticleId.value
  if (id) void router.push({ name: 'articles', query: { id } })
}

function openResults() {
  if (currentRun.value) void router.push({ name: 'ai-results', params: { runId: currentRun.value.run_id } })
}

function onKeydown(event: KeyboardEvent) {
  if (event.key !== 'Escape') return
  if (referencePickerOpen.value) return
  if (profilePickerOpen.value) profilePickerOpen.value = false
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  void loadInitial()
  if (route.query.tour === 'ai-edit') {
    startAiTour()
    void clearAiTourQuery()
  } else if (settings.tourStatus('ai-edit') === 'unseen') {
    tourInviteOpen.value = true
  }
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

watch(() => route.query.tour, (value) => {
  if (value === 'ai-edit') {
    startAiTour()
    void clearAiTourQuery()
  }
})
</script>

<template>
  <div class="flex h-full min-h-0 bg-stone-50">
    <main class="min-w-0 flex-1 overflow-y-auto">
      <div class="mx-auto max-w-5xl p-5 lg:p-7">
        <header class="flex flex-wrap items-start justify-between gap-4 border-b border-stone-200 pb-5">
          <div>
            <h1 class="text-xl font-semibold text-stone-900">{{ t('articleAi.title') }}</h1>
            <p class="mt-1 text-sm text-stone-500">{{ t('articleAi.subtitle') }}</p>
          </div>
          <button type="button" class="rounded-md border border-stone-300 bg-white px-3 py-2 text-sm text-stone-700 hover:bg-stone-50" @click="openArticle">{{ t('articleAi.backToArticle') }}</button>
        </header>

        <div v-if="error || taskRun.statusError" class="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{{ error || taskRun.statusError }}</div>
        <div v-if="notice" class="mt-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{{ notice }}</div>

        <section class="grid gap-5 py-5 lg:grid-cols-[minmax(0,1fr)_280px]">
          <div class="min-w-0 space-y-5">
            <div class="border-b border-stone-200 pb-5" data-tour="ai-target">
              <label class="text-xs font-semibold uppercase text-stone-500">{{ t('articleAi.article') }}</label>
              <select v-model="selectedArticleId" :aria-label="t('articleAi.article')" :disabled="taskRun.running" class="mt-2 w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-sm">
                <option value="">{{ t('articleAi.selectArticle') }}</option>
                <option v-for="article in articles" :key="article.id" :value="article.id">{{ article.title || t('articles.untitled') }}</option>
              </select>
              <div v-if="selectedArticle" class="mt-3 bg-white p-3 ring-1 ring-stone-200">
                <div class="flex items-center justify-between gap-3"><span class="text-sm font-medium text-stone-800">{{ hasSelection ? t('articleAi.selection') : t('articleAi.fullArticle') }}</span><span class="text-xs text-stone-600">{{ selectedText.length }} {{ t('articleAi.characters') }}</span></div>
                <p data-testid="article-ai-target-preview" class="mt-2 line-clamp-4 whitespace-pre-wrap text-sm leading-6 text-stone-600">{{ selectedText || t('articleAi.emptyArticle') }}</p>
              </div>
            </div>

            <div data-tour="ai-tasks">
              <h2 class="text-sm font-semibold text-stone-800">{{ t('articleAi.chooseTask') }}</h2>
              <div class="mt-3 grid gap-2 sm:grid-cols-2">
                <button v-for="task in tasks" :key="task.id" type="button" :class="['border p-3 text-left', taskType === task.id ? 'border-stone-900 bg-stone-900 text-white' : 'border-stone-200 bg-white text-stone-800 hover:border-stone-400']" @click="taskType = task.id">
                  <span class="block text-sm font-semibold">{{ task.title }}</span><span :class="['mt-1 block text-xs leading-5', taskType === task.id ? 'text-stone-300' : 'text-stone-500']">{{ task.help }}</span>
                </button>
              </div>
            </div>

            <ArticleAiPresetPicker
              :task-type="taskType"
              :active-preset-id="selectedPresetId"
              :custom-presets="taskPresets"
              @select-system="selectSystemPreset"
              @select-custom="selectCustomPreset"
              @save="saveCustomPreset"
              @rename="renameCustomPreset"
              @delete="deleteCustomPreset"
            />

            <div
              v-if="showViewpointControls || showArgumentDirection || showSceneFocus"
              class="grid gap-4 border-b border-stone-200 pb-5 md:grid-cols-2"
              data-testid="article-ai-structured-controls"
            >
              <template v-if="showViewpointControls">
                <label class="text-sm text-stone-700">
                  {{ t('articleAi.presets.targetViewpoint') }}
                  <select v-model="controls.targetViewpoint" class="mt-2 w-full rounded-md border border-stone-300 bg-white px-3 py-2">
                    <option value="keep">{{ t('articleAi.presets.keepCurrent') }}</option>
                    <option value="first">{{ t('articleAi.presets.firstPerson') }}</option>
                    <option value="third_limited">{{ t('articleAi.presets.thirdLimited') }}</option>
                    <option value="omniscient">{{ t('articleAi.presets.omniscient') }}</option>
                  </select>
                </label>
                <label class="text-sm text-stone-700">
                  {{ t('articleAi.presets.targetTense') }}
                  <select v-model="controls.targetTense" class="mt-2 w-full rounded-md border border-stone-300 bg-white px-3 py-2">
                    <option value="keep">{{ t('articleAi.presets.keepCurrent') }}</option>
                    <option value="past">{{ t('articleAi.presets.pastTense') }}</option>
                    <option value="present">{{ t('articleAi.presets.presentTense') }}</option>
                  </select>
                </label>
                <label v-if="controls.targetViewpoint === 'third_limited'" class="text-sm text-stone-700 md:col-span-2">
                  {{ t('articleAi.presets.viewpointCharacter') }}
                  <input v-model="controls.viewpointCharacter" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2" :placeholder="t('articleAi.presets.viewpointCharacterPlaceholder')" />
                </label>
              </template>
              <label v-if="showArgumentDirection" class="text-sm text-stone-700 md:col-span-2">
                {{ t('articleAi.presets.argumentDirection') }}
                <input v-model="controls.argumentDirection" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2" :placeholder="t('articleAi.presets.argumentDirectionPlaceholder')" />
              </label>
              <label v-if="showSceneFocus" class="text-sm text-stone-700 md:col-span-2">
                {{ t('articleAi.presets.sceneFocus') }}
                <input v-model="controls.sceneFocus" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2" :placeholder="t('articleAi.presets.sceneFocusPlaceholder')" />
              </label>
              <p v-if="missingRequirements.length" class="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900 md:col-span-2">{{ t('articleAi.presets.completeRequired') }}</p>
            </div>

            <div class="grid gap-4 border-b border-stone-200 pb-5 md:grid-cols-2">
              <template v-if="taskType === 'polish'"><label class="text-sm text-stone-700">{{ t('articleAi.intensity') }}<select v-model="controls.polishIntensity" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2"><option value="light">{{ t('articleAi.light') }}</option><option value="medium">{{ t('articleAi.medium') }}</option><option value="strong">{{ t('articleAi.strong') }}</option></select></label><label class="text-sm text-stone-700">{{ t('articleAi.goal') }}<select v-model="controls.polishGoal" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2"><option value="clarity">{{ t('articleAi.clarity') }}</option><option value="rhythm">{{ t('articleAi.rhythm') }}</option><option value="literary">{{ t('articleAi.literary') }}</option><option value="restrained">{{ t('articleAi.restrained') }}</option></select></label><label class="flex items-center gap-2 text-sm text-stone-700"><input v-model="controls.preserveVoice" type="checkbox" />{{ t('articleAi.preserveVoice') }}</label></template>
              <template v-else-if="taskType === 'rewrite'"><label class="text-sm text-stone-700 md:col-span-2">{{ t('articleAi.direction') }}<input v-model="controls.rewriteDirection" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2" /></label><label class="text-sm text-stone-700">{{ t('articleAi.changeLevel') }}<select v-model="controls.sentenceChange" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2"><option value="light">{{ t('articleAi.light') }}</option><option value="medium">{{ t('articleAi.medium') }}</option><option value="strong">{{ t('articleAi.strong') }}</option></select></label><label class="flex items-center gap-2 text-sm text-stone-700"><input v-model="controls.keepImagery" type="checkbox" />{{ t('articleAi.keepImagery') }}</label></template>
              <template v-else-if="taskType === 'expand'"><label class="text-sm text-stone-700">{{ t('articleAi.length') }}<select v-model="controls.expandLength" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2"><option value="short">{{ t('articleAi.short') }}</option><option value="medium">{{ t('articleAi.medium') }}</option><option value="long">{{ t('articleAi.long') }}</option></select></label><label class="text-sm text-stone-700">{{ t('articleAi.focus') }}<input v-model="controls.expandFocus" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2" /></label><label class="flex items-center gap-2 text-sm text-stone-700"><input v-model="controls.sensoryDetail" type="checkbox" />{{ t('articleAi.sensory') }}</label></template>
              <template v-else><label class="text-sm text-stone-700">{{ t('articleAi.length') }}<select v-model="controls.continueLength" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2"><option value="short">{{ t('articleAi.short') }}</option><option value="medium">{{ t('articleAi.medium') }}</option><option value="long">{{ t('articleAi.long') }}</option></select></label><label class="text-sm text-stone-700">{{ t('articleAi.emotion') }}<input v-model="controls.emotionalDirection" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2" /></label><label class="text-sm text-stone-700">{{ t('articleAi.pacing') }}<input v-model="controls.pacing" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2" /></label></template>
            </div>

            <section class="border-b border-stone-200 pb-5" data-testid="article-ai-context-section" data-tour="ai-context-sources">
              <div><h2 class="text-sm font-semibold text-stone-900">{{ t('articleAi.contextSources.title') }}</h2><p class="mt-1 text-sm text-stone-600">{{ t('articleAi.contextSources.help') }}</p></div>
              <div class="mt-4 grid overflow-hidden rounded-lg border border-stone-200 bg-white lg:grid-cols-3 lg:divide-x lg:divide-stone-200">
                <div class="border-b border-stone-200 p-4 lg:border-b-0" data-testid="article-ai-reference-section">
                  <div><h3 class="text-sm font-semibold text-stone-900">{{ t('articleAi.contextSources.references') }}</h3><p class="mt-1 text-sm text-stone-600">{{ t('articleAi.contextPicker.summary', { count: selectedReferences.length, chars: selectedReferenceChars }) }}</p><button type="button" class="mt-3 min-h-10 w-full rounded-md border border-stone-300 px-3 py-2 text-sm font-medium text-stone-700 hover:bg-stone-50" @click="referencePickerOpen = true">{{ selectedReferences.length ? t('articleAi.referenceSection.reselect') : t('articleAi.referenceSection.choose') }}</button></div>
                  <div v-if="selectedReferences.length" class="mt-3 space-y-1.5"><div v-for="reference in selectedReferences.slice(0, 3)" :key="reference.id" class="flex items-center gap-2 text-sm text-stone-700"><span class="min-w-0 flex-1 truncate">{{ referenceName(reference) }}</span><button type="button" class="h-7 w-7 rounded-md text-lg text-stone-500 hover:bg-stone-100" :aria-label="t('articleAi.referenceSection.remove', { name: referenceName(reference) })" @click="removeReference(reference.id)">×</button></div><p v-if="selectedReferences.length > 3" class="text-sm text-stone-500">+{{ selectedReferences.length - 3 }}</p><button type="button" class="text-sm font-medium text-stone-600 underline" @click="clearReferences">{{ t('articleAi.referenceSection.clear') }}</button></div><p v-else class="mt-3 text-sm text-stone-500">{{ t('articleAi.referenceSection.empty') }}</p>
                </div>
                <div class="border-b border-stone-200 p-4 lg:border-b-0" data-testid="article-ai-card-section">
                  <div><h3 class="text-sm font-semibold text-stone-900">AI Cards</h3><p class="mt-1 text-sm text-stone-600">{{ t('articleAi.contextPicker.summary', { count: selectedCards.length, chars: selectedCardChars }) }}</p><button type="button" class="mt-3 min-h-10 w-full rounded-md border border-stone-300 px-3 py-2 text-sm font-medium text-stone-700 hover:bg-stone-50" @click="cardPickerOpen = true">{{ selectedCards.length ? t('articleAi.referenceSection.reselect') : t('articleAi.contextSources.chooseCards') }}</button></div>
                  <div v-if="selectedCards.length" class="mt-3 space-y-1.5"><div v-for="card in selectedCards.slice(0, 3)" :key="card.id" class="flex items-center gap-2 text-sm text-stone-700"><span class="min-w-0 flex-1 truncate">{{ card.title }}</span><button type="button" class="h-7 w-7 rounded-md text-lg text-stone-500 hover:bg-stone-100" :aria-label="t('articleAi.referenceSection.remove', { name: card.title })" @click="selectedCards = selectedCards.filter((item) => item.id !== card.id)">×</button></div><p v-if="selectedCards.length > 3" class="text-sm text-stone-500">+{{ selectedCards.length - 3 }}</p><button type="button" class="text-sm font-medium text-stone-600 underline" @click="selectedCards = []">{{ t('articleAi.referenceSection.clear') }}</button></div><p v-else class="mt-3 text-sm text-stone-500">{{ t('articleAi.contextSources.cardEmpty') }}</p>
                </div>
                <div class="p-4" data-testid="article-ai-note-section">
                  <div><h3 class="text-sm font-semibold text-stone-900">{{ t('articleAi.notes') }}</h3><p class="mt-1 text-sm text-stone-600">{{ t('articleAi.contextPicker.summary', { count: selectedNotes.length, chars: selectedNoteChars }) }}</p><button type="button" :disabled="!selectedArticleId" class="mt-3 min-h-10 w-full rounded-md border border-stone-300 px-3 py-2 text-sm font-medium text-stone-700 hover:bg-stone-50 disabled:opacity-40" @click="openNotePicker">{{ selectedNotes.length ? t('articleAi.referenceSection.reselect') : t('articleAi.contextSources.chooseNotes') }}</button></div>
                  <div v-if="selectedNotes.length" class="mt-3 space-y-1.5"><div v-for="note in selectedNotes.slice(0, 3)" :key="note.id" class="flex items-center gap-2 text-sm text-stone-700"><span class="min-w-0 flex-1 truncate">{{ noteName(note) }}</span><button type="button" class="h-7 w-7 rounded-md text-lg text-stone-500 hover:bg-stone-100" :aria-label="t('articleAi.referenceSection.remove', { name: noteName(note) })" @click="selectedNotes = selectedNotes.filter((item) => item.id !== note.id)">×</button></div><p v-if="selectedNotes.length > 3" class="text-sm text-stone-500">+{{ selectedNotes.length - 3 }}</p><button type="button" class="text-sm font-medium text-stone-600 underline" @click="selectedNotes = []">{{ t('articleAi.referenceSection.clear') }}</button></div><p v-else class="mt-3 text-sm text-stone-500">{{ t('articleAi.contextSources.noteEmpty') }}</p>
                </div>
              </div>
              <p v-if="selectedReferenceChars + selectedCardChars + selectedNoteChars > 20_000" class="mt-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900">{{ t('articleAi.referencePicker.largeContext') }}</p>
            </section>

            <details :open="moreOpen" @toggle="moreOpen = ($event.target as HTMLDetailsElement).open" class="border-b border-stone-200 pb-5">
              <summary class="cursor-pointer text-sm font-semibold text-stone-700">{{ t('articleAi.more') }}</summary>
              <div class="mt-4 space-y-4">
                <label class="block text-sm text-stone-700">{{ t('articleAi.extra') }}<textarea v-model="controls.extraInstructions" rows="3" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2" /></label>
              </div>
            </details>

            <div class="flex flex-wrap items-center justify-between gap-3" data-tour="ai-model-run">
              <button type="button" class="text-sm font-medium text-stone-700 underline" @click="profilePickerOpen = true">{{ t('articleAi.modelsSelected', { count: selectedProfileIds.length }) }}</button>
              <button type="button" :disabled="!canRun" class="rounded-md bg-stone-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-stone-700 disabled:opacity-40" @click="runTask">{{ taskRun.creating ? t('common.loading') : t('articleAi.run') }}</button>
            </div>
          </div>

          <aside class="border-l border-stone-200 pl-5">
            <h2 class="text-sm font-semibold text-stone-800">{{ t('articleAi.models') }}</h2>
            <p v-if="!selectedProfiles.length" class="mt-3 text-xs leading-5 text-amber-700">{{ t('articleAi.noModel') }}</p>
            <div v-else class="mt-3 space-y-2"><div v-for="profile in selectedProfiles" :key="profile.id" class="text-xs text-stone-600"><span class="font-medium text-stone-800">{{ profile.name }}</span><br />{{ profile.model }}</div></div>
            <div v-if="currentRun" class="mt-6 border-t border-stone-200 pt-4">
              <div class="flex items-center justify-between gap-2"><span class="text-xs font-semibold text-stone-700">{{ currentRun.stage_label }}</span><span class="text-xs text-stone-400">{{ formatElapsed(currentRun.elapsed_ms) }}</span></div>
              <p v-if="taskRun.reconnectCount" class="mt-2 text-xs text-amber-700">{{ t('articleAi.reconnecting', { count: taskRun.reconnectCount }) }}</p>
              <button class="mt-3 block text-xs font-medium text-teal-800 underline" @click="openResults">{{ t('articleAi.openResults') }}</button>
              <button v-if="taskRun.running" class="mt-3 text-xs font-medium text-red-700 underline" @click="cancelRun">{{ t('articleAi.cancel') }}</button>
              <button v-else class="mt-3 text-xs font-medium text-stone-600 underline" @click="clearRun">{{ t('articleAi.clear') }}</button>
            </div>
          </aside>
        </section>
      </div>
    </main>

    <ArticleAiReferencePicker
      :open="referencePickerOpen"
      :selected="selectedReferences"
      @close="referencePickerOpen = false"
      @confirm="confirmReferences"
      @open-library="openReferenceLibrary"
    />
    <ArticleAiCardPicker
      :open="cardPickerOpen"
      :selected="selectedCards"
      @close="cardPickerOpen = false"
      @confirm="confirmCards"
      @open-cards="openCardsLibrary"
    />
    <ArticleAiNotePicker
      :open="notePickerOpen"
      :notes="notes"
      :selected="selectedNotes"
      :loading="contextLoading"
      :article-title="selectedArticle?.title || t('articles.untitled')"
      @close="notePickerOpen = false"
      @confirm="confirmNotes"
      @open-article="openCurrentArticle"
    />

    <Teleport to="body">
      <div v-if="profilePickerOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" @click.self="profilePickerOpen = false"><div role="dialog" aria-modal="true" aria-labelledby="article-ai-model-picker-title" class="max-h-[75vh] w-full max-w-lg overflow-y-auto rounded-lg bg-white p-5 shadow-2xl"><div class="flex items-center justify-between"><h3 id="article-ai-model-picker-title" class="font-semibold text-stone-900">{{ t('articleAi.chooseModels') }}</h3><button class="h-8 w-8 rounded-md hover:bg-stone-100" :aria-label="t('common.close')" @click="profilePickerOpen = false">×</button></div><p class="mt-1 text-xs leading-5 text-stone-500">{{ t('articleAi.modelHint') }}</p><div class="mt-4 divide-y divide-stone-200"><label v-for="profile in enabledProfiles" :key="profile.id" class="flex cursor-pointer items-start gap-3 py-3"><input :checked="selectedProfileIds.includes(profile.id)" type="checkbox" class="mt-1 h-4 w-4" @change="toggleProfile(profile.id)" /><span><span class="text-sm font-semibold text-stone-800">{{ profile.name }}<span v-if="profile.id === defaultProfileId" class="ml-2 text-xs text-stone-400">{{ t('settings.profileHub.default') }}</span></span><span class="mt-1 block text-xs text-stone-500">{{ profile.model }}</span></span></label></div><div class="mt-4 flex justify-end"><button class="rounded-md bg-stone-900 px-4 py-2 text-sm font-semibold text-white" @click="profilePickerOpen = false">{{ t('common.done') }}</button></div></div></div>

    </Teleport>
    <TourInvitation :open="tourInviteOpen" :title="t('articleAiTour.inviteTitle')" :body="t('articleAiTour.inviteBody')" :start-label="t('guidedTours.start')" :later-label="t('guidedTours.later')" :dismiss-label="t('guidedTours.dismiss')" @start="startAiTour" @later="tourInviteOpen = false" @dismiss="dismissAiTour" />
    <GuidedTourOverlay :open="tourOpen" :steps="tourSteps" :step-index="tourStepIndex" :previous-label="t('collectionsTour.previous')" :next-label="t('collectionsTour.next')" :skip-label="t('collectionsTour.skip')" :finish-label="t('collectionsTour.finish')" :progress-label="tourProgress" :close-label="t('common.close')" @previous="tourStepIndex = Math.max(0, tourStepIndex - 1)" @next="tourStepIndex = Math.min(tourSteps.length - 1, tourStepIndex + 1)" @close="finishAiTour" @finish="finishAiTour" />
  </div>
</template>
