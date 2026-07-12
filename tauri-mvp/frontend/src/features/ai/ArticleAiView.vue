<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { articlesApi, type Entry } from '../../api/articles'
import { aiApi, type AiContextAttachment, type AiTaskCompareResult, type AiTaskPresetMap } from '../../api/ai'
import { aiCardApi, type AiCard } from '../../api/aiCards'
import type { Reference } from '../../api/library'
import { notesApi, type WritingNote } from '../../api/notes'
import { errorMessage } from '../../api/base'
import { settingsApi, type AiProfile } from '../../api/settings'
import { useI18n } from '../../i18n'
import { buildParagraphDiff } from '../articles/versionDiff'
import ArticleAiReferencePicker from './ArticleAiReferencePicker.vue'
import { buildTaskRequestOptions, createDefaultControls, mergeControls, type FocusTaskType } from './taskControls'
import { useArticleTaskRunStore } from './articleTaskRunStore'
import { toggleAiTaskProfileSelection } from './profileSelection'
import { utf16OffsetToCodePointOffset } from './selectionOffsets'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const taskRun = useArticleTaskRunStore()

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
const selectedResultProfileId = ref<string | null>(null)
const readerMode = ref<'result' | 'diff'>('result')
const applyPreviewOpen = ref(false)

const presets = ref<AiTaskPresetMap>({})
const selectedPresetId = ref('')
const aiCards = ref<AiCard[]>([])
const notes = ref<WritingNote[]>([])
const selectedCardIds = ref<string[]>([])
const selectedNoteIds = ref<string[]>([])
const selectedReferences = ref<Reference[]>([])
const referencePickerOpen = ref(false)
const contextLoading = ref(false)

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
const selectedReferenceIds = computed(() => selectedReferences.value.map((item) => item.id))
const selectedReferenceChars = computed(() => selectedReferences.value.reduce((total, item) => total + item.content.length, 0))
const currentRun = computed(() => taskRun.run)
const runReferenceSnapshots = computed(() => currentRun.value?.attachment_snapshots?.filter((item) => item.kind === 'style_specimen') ?? [])
const successfulResults = computed(() => currentRun.value?.results.filter((item) => item.status === 'success') ?? [])
const selectedResult = computed<AiTaskCompareResult | null>(() => {
  return currentRun.value?.results.find((item) => item.profile_id === selectedResultProfileId.value) ?? successfulResults.value[0] ?? null
})
const diffRows = computed(() => selectedResult.value ? buildParagraphDiff(currentRun.value?.results.length ? selectedTextForRun.value : '', selectedResult.value.result) : [])
const selectedTextForRun = computed(() => {
  const run = currentRun.value
  if (!run) return selectedText.value
  return run.original_text
})
const canRun = computed(() => Boolean(selectedArticle.value?.body.trim() && selectedProfileIds.value.length && !taskRun.running && !taskRun.creating))
const taskPresets = computed(() => presets.value[taskType.value] ?? [])

watch(() => currentRun.value?.results, (results) => {
  if (!results?.length) return
  const selectedStillValid = results.some((item) => item.profile_id === selectedResultProfileId.value && item.status === 'success')
  if (!selectedStillValid) selectedResultProfileId.value = results.find((item) => item.status === 'success')?.profile_id ?? null
}, { deep: true, immediate: true })

watch(selectedArticleId, () => {
  if (selectedArticleId.value !== route.query.scope_id) {
    selectionStart.value = null
    selectionEnd.value = null
  }
  notes.value = []
  selectedNoteIds.value = []
  if (moreOpen.value) void loadArticleContext()
})

watch(moreOpen, (open) => {
  if (open) void loadContext()
})

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
    selectedProfileIds.value = defaultProfileId.value ? [defaultProfileId.value] : []
    await taskRun.hydrate()
  } catch (e) {
    error.value = errorMessage(e)
  }
}

async function loadContext() {
  if (contextLoading.value) return
  contextLoading.value = true
  try {
    const cards = await (aiCards.value.length ? Promise.resolve(aiCards.value) : aiCardApi.listCards())
    aiCards.value = cards
    await loadArticleContext()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    contextLoading.value = false
  }
}

async function loadArticleContext() {
  if (!selectedArticleId.value) return
  try {
    notes.value = await notesApi.listNotes(selectedArticleId.value, false)
  } catch (e) {
    error.value = errorMessage(e)
  }
}

function toggleProfile(profileId: string) {
  selectedProfileIds.value = toggleAiTaskProfileSelection(
    selectedProfileIds.value,
    profileId,
    defaultProfileId.value ?? '',
  )
}

function applyPreset(presetId: string) {
  selectedPresetId.value = presetId
  const preset = taskPresets.value.find((item) => item.id === presetId)
  if (preset) controls.value = mergeControls(preset.controls)
}

function attachments(): AiContextAttachment[] {
  return [
    ...aiCards.value.filter((item) => selectedCardIds.value.includes(item.id)).map((item) => ({ kind: 'ai_card', ref_id: item.id, name: item.title, body: item.content })),
    ...notes.value.filter((item) => selectedNoteIds.value.includes(item.id)).map((item) => ({ kind: 'writing_note', ref_id: item.id, name: t('articleAi.writingNote'), body: item.body })),
    ...selectedReferences.value.map((item) => ({
      kind: 'style_specimen',
      ref_id: item.id,
      name: referenceName(item),
      body: referenceAttachmentBody(item),
    })),
  ]
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

function openReferenceLibrary() {
  referencePickerOpen.value = false
  void router.push({ name: 'library' })
}

async function runTask() {
  if (!selectedArticle.value) return
  error.value = ''
  notice.value = ''
  const options = buildTaskRequestOptions(taskType.value, controls.value)
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
      ...options,
    })
    selectedResultProfileId.value = run.results.find((item) => item.status === 'success')?.profile_id ?? null
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
    selectedResultProfileId.value = null
  } catch (e) {
    error.value = errorMessage(e)
  }
}

async function copyResult() {
  if (!selectedResult.value) return
  try {
    await navigator.clipboard.writeText(selectedResult.value.result)
    notice.value = t('articleAi.copied')
  } catch (e) {
    error.value = errorMessage(e)
  }
}

async function applyResult() {
  if (!selectedResult.value) return
  error.value = ''
  try {
    const applied = await taskRun.apply(selectedResult.value.profile_id)
    const index = articles.value.findIndex((item) => item.id === applied.entry.id)
    if (index >= 0) articles.value[index] = applied.entry as Entry
    notice.value = applied.was_noop ? t('articleAi.alreadyApplied') : t('articleAi.applied')
    applyPreviewOpen.value = false
  } catch (e) {
    error.value = errorMessage(e)
  }
}

function formatElapsed(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`
}

function resultStatus(result: AiTaskCompareResult): string {
  if (result.status === 'success') return t('articleAi.status.success')
  if (result.status === 'error') return t('articleAi.status.error')
  return t('articleAi.status.pending')
}

function openArticle() {
  const id = currentRun.value?.article_id || selectedArticleId.value
  if (id) void router.push({ name: 'articles', query: { id } })
}

function onKeydown(event: KeyboardEvent) {
  if (event.key !== 'Escape') return
  if (referencePickerOpen.value) return
  if (applyPreviewOpen.value) applyPreviewOpen.value = false
  else if (profilePickerOpen.value) profilePickerOpen.value = false
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  void loadInitial()
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
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
            <div class="border-b border-stone-200 pb-5">
              <label class="text-xs font-semibold uppercase text-stone-500">{{ t('articleAi.article') }}</label>
              <select v-model="selectedArticleId" :aria-label="t('articleAi.article')" :disabled="taskRun.running" class="mt-2 w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-sm">
                <option value="">{{ t('articleAi.selectArticle') }}</option>
                <option v-for="article in articles" :key="article.id" :value="article.id">{{ article.title || t('articles.untitled') }}</option>
              </select>
              <div v-if="selectedArticle" class="mt-3 bg-white p-3 ring-1 ring-stone-200">
                <div class="flex items-center justify-between gap-3"><span class="text-sm font-medium text-stone-800">{{ hasSelection ? t('articleAi.selection') : t('articleAi.fullArticle') }}</span><span class="text-xs text-stone-600">{{ selectedText.length }} {{ t('articleAi.characters') }}</span></div>
                <p class="mt-2 line-clamp-4 whitespace-pre-wrap text-sm leading-6 text-stone-600">{{ selectedText || t('articleAi.emptyArticle') }}</p>
              </div>
            </div>

            <div>
              <h2 class="text-sm font-semibold text-stone-800">{{ t('articleAi.chooseTask') }}</h2>
              <div class="mt-3 grid gap-2 sm:grid-cols-2">
                <button v-for="task in tasks" :key="task.id" type="button" :class="['border p-3 text-left', taskType === task.id ? 'border-stone-900 bg-stone-900 text-white' : 'border-stone-200 bg-white text-stone-800 hover:border-stone-400']" @click="taskType = task.id">
                  <span class="block text-sm font-semibold">{{ task.title }}</span><span :class="['mt-1 block text-xs leading-5', taskType === task.id ? 'text-stone-300' : 'text-stone-500']">{{ task.help }}</span>
                </button>
              </div>
            </div>

            <div class="grid gap-4 border-y border-stone-200 py-5 md:grid-cols-2">
              <template v-if="taskType === 'polish'"><label class="text-sm text-stone-700">{{ t('articleAi.intensity') }}<select v-model="controls.polishIntensity" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2"><option value="light">{{ t('articleAi.light') }}</option><option value="medium">{{ t('articleAi.medium') }}</option><option value="strong">{{ t('articleAi.strong') }}</option></select></label><label class="text-sm text-stone-700">{{ t('articleAi.goal') }}<select v-model="controls.polishGoal" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2"><option value="clarity">{{ t('articleAi.clarity') }}</option><option value="rhythm">{{ t('articleAi.rhythm') }}</option><option value="literary">{{ t('articleAi.literary') }}</option><option value="restrained">{{ t('articleAi.restrained') }}</option></select></label><label class="flex items-center gap-2 text-sm text-stone-700"><input v-model="controls.preserveVoice" type="checkbox" />{{ t('articleAi.preserveVoice') }}</label></template>
              <template v-else-if="taskType === 'rewrite'"><label class="text-sm text-stone-700 md:col-span-2">{{ t('articleAi.direction') }}<input v-model="controls.rewriteDirection" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2" /></label><label class="text-sm text-stone-700">{{ t('articleAi.changeLevel') }}<select v-model="controls.sentenceChange" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2"><option value="light">{{ t('articleAi.light') }}</option><option value="medium">{{ t('articleAi.medium') }}</option><option value="strong">{{ t('articleAi.strong') }}</option></select></label><label class="flex items-center gap-2 text-sm text-stone-700"><input v-model="controls.keepImagery" type="checkbox" />{{ t('articleAi.keepImagery') }}</label></template>
              <template v-else-if="taskType === 'expand'"><label class="text-sm text-stone-700">{{ t('articleAi.length') }}<select v-model="controls.expandLength" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2"><option value="short">{{ t('articleAi.short') }}</option><option value="medium">{{ t('articleAi.medium') }}</option><option value="long">{{ t('articleAi.long') }}</option></select></label><label class="text-sm text-stone-700">{{ t('articleAi.focus') }}<input v-model="controls.expandFocus" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2" /></label><label class="flex items-center gap-2 text-sm text-stone-700"><input v-model="controls.sensoryDetail" type="checkbox" />{{ t('articleAi.sensory') }}</label></template>
              <template v-else><label class="text-sm text-stone-700">{{ t('articleAi.length') }}<select v-model="controls.continueLength" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2"><option value="short">{{ t('articleAi.short') }}</option><option value="medium">{{ t('articleAi.medium') }}</option><option value="long">{{ t('articleAi.long') }}</option></select></label><label class="text-sm text-stone-700">{{ t('articleAi.emotion') }}<input v-model="controls.emotionalDirection" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2" /></label><label class="text-sm text-stone-700">{{ t('articleAi.pacing') }}<input v-model="controls.pacing" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2" /></label></template>
            </div>

            <section class="border-b border-stone-200 pb-5" data-testid="article-ai-reference-section">
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 class="text-sm font-semibold text-stone-900">{{ t('articleAi.referenceSection.title') }}</h2>
                  <p class="mt-1 text-sm text-stone-600">
                    {{ selectedReferenceIds.length
                      ? t('articleAi.referenceSection.summary', { count: selectedReferenceIds.length, chars: selectedReferenceChars })
                      : t('articleAi.referenceSection.empty') }}
                  </p>
                </div>
                <div class="flex flex-wrap gap-2">
                  <button v-if="selectedReferenceIds.length" type="button" class="rounded-md border border-stone-300 px-3 py-2 text-sm font-medium text-stone-700 hover:bg-stone-50" @click="clearReferences">
                    {{ t('articleAi.referenceSection.clear') }}
                  </button>
                  <button type="button" class="rounded-md bg-emerald-800 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700" @click="referencePickerOpen = true">
                    {{ selectedReferenceIds.length ? t('articleAi.referenceSection.reselect') : t('articleAi.referenceSection.choose') }}
                  </button>
                </div>
              </div>

              <div v-if="selectedReferences.length" class="mt-4 grid gap-2 md:grid-cols-2">
                <article v-for="reference in selectedReferences" :key="reference.id" class="rounded-md border border-stone-200 bg-white p-3">
                  <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0">
                      <h3 class="truncate text-sm font-semibold text-stone-900">{{ referenceName(reference) }}</h3>
                      <div class="mt-2 flex flex-wrap gap-1.5">
                        <span class="rounded bg-emerald-50 px-2 py-1 text-sm font-medium text-emerald-800">{{ referenceUsageLabel(reference) }}</span>
                        <span v-for="tag in reference.tags.slice(0, 4)" :key="tag" class="rounded bg-stone-100 px-2 py-1 text-sm text-stone-700">{{ tag }}</span>
                      </div>
                    </div>
                    <button type="button" class="h-8 w-8 shrink-0 rounded-md text-lg text-stone-600 hover:bg-stone-100" :aria-label="t('articleAi.referenceSection.remove', { name: referenceName(reference) })" @click="removeReference(reference.id)">×</button>
                  </div>
                  <p v-if="reference.content.length > 40_000" class="mt-2 text-sm font-medium text-amber-800">{{ t('articleAi.referencePicker.itemTruncated') }}</p>
                </article>
              </div>

              <div v-else class="mt-4 rounded-md border border-dashed border-stone-300 bg-white px-4 py-5 text-center text-sm text-stone-600">
                {{ t('articleAi.referenceSection.empty') }}
              </div>
              <p v-if="selectedReferenceChars > 20_000" class="mt-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900">{{ t('articleAi.referencePicker.largeContext') }}</p>
            </section>

            <details :open="moreOpen" @toggle="moreOpen = ($event.target as HTMLDetailsElement).open" class="border-b border-stone-200 pb-5">
              <summary class="cursor-pointer text-sm font-semibold text-stone-700">{{ t('articleAi.more') }}</summary>
              <div class="mt-4 space-y-4">
                <label class="block text-sm text-stone-700">{{ t('articleAi.preset') }}<select :value="selectedPresetId" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2" @change="applyPreset(($event.target as HTMLSelectElement).value)"><option value="">{{ t('articleAi.noPreset') }}</option><option v-for="preset in taskPresets" :key="preset.id" :value="preset.id">{{ preset.name }}</option></select></label>
                <label class="block text-sm text-stone-700">{{ t('articleAi.extra') }}<textarea v-model="controls.extraInstructions" rows="3" class="mt-2 w-full rounded-md border border-stone-300 px-3 py-2" /></label>
                <div v-if="contextLoading" class="text-xs text-stone-500">{{ t('common.loading') }}</div>
                <div v-else class="grid gap-4 md:grid-cols-2">
                  <fieldset><legend class="text-xs font-semibold text-stone-600">AI Cards</legend><label v-for="item in aiCards.slice(0, 20)" :key="item.id" class="mt-2 flex gap-2 text-xs text-stone-600"><input v-model="selectedCardIds" :value="item.id" type="checkbox" />{{ item.title }}</label></fieldset>
                  <fieldset><legend class="text-xs font-semibold text-stone-600">{{ t('articleAi.notes') }}</legend><label v-for="item in notes.slice(0, 20)" :key="item.id" class="mt-2 flex gap-2 text-xs text-stone-600"><input v-model="selectedNoteIds" :value="item.id" type="checkbox" /><span class="line-clamp-2">{{ item.body }}</span></label></fieldset>
                </div>
              </div>
            </details>

            <div class="flex flex-wrap items-center justify-between gap-3">
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
              <button v-if="taskRun.running" class="mt-3 text-xs font-medium text-red-700 underline" @click="cancelRun">{{ t('articleAi.cancel') }}</button>
              <button v-else class="mt-3 text-xs font-medium text-stone-600 underline" @click="clearRun">{{ t('articleAi.clear') }}</button>
            </div>
          </aside>
        </section>

        <section v-if="currentRun" class="border-t border-stone-300 pt-6">
          <div class="mb-4 flex flex-wrap items-center justify-between gap-2">
            <h2 class="text-sm font-semibold text-stone-800">{{ t('articleAi.runFor', { title: currentRun.article_title }) }}</h2>
            <span class="text-xs text-stone-500">{{ currentRun.stage_label }} · {{ formatElapsed(currentRun.elapsed_ms) }}</span>
          </div>
          <div v-if="runReferenceSnapshots.length" class="mb-4 flex flex-wrap items-center gap-2" data-testid="article-ai-run-references">
            <span class="text-sm font-medium text-stone-700">{{ t('articleAi.referenceSection.runReferences') }}</span>
            <span v-for="item in runReferenceSnapshots" :key="`${item.kind}:${item.ref_id}`" class="rounded bg-emerald-50 px-2 py-1 text-sm text-emerald-900">{{ item.name }}</span>
          </div>
          <div class="grid min-h-[360px] gap-5 lg:grid-cols-[240px_minmax(0,1fr)]">
            <div class="space-y-2">
              <button v-for="result in currentRun.results" :key="result.profile_id" type="button" :disabled="result.status !== 'success'" :class="['w-full border p-3 text-left', selectedResult?.profile_id === result.profile_id ? 'border-stone-900 bg-stone-900 text-white' : 'border-stone-200 bg-white text-stone-700', result.status !== 'success' ? 'cursor-default opacity-75' : 'hover:border-stone-500']" @click="selectedResultProfileId = result.profile_id">
                <span class="block text-sm font-semibold">{{ result.profile_name }}</span><span class="mt-1 block text-xs">{{ resultStatus(result) }}<template v-if="result.elapsed_ms"> · {{ formatElapsed(result.elapsed_ms) }}</template></span><span v-if="result.status === 'success'" class="mt-1 block text-xs opacity-75">{{ result.output_tokens ?? '-' }} tokens<template v-if="result.cost !== null && result.cost !== undefined"> · {{ result.cost }}</template> · {{ result.transport || '-' }}</span><span v-if="result.error" class="mt-2 block text-xs text-red-600">{{ result.error }}</span>
              </button>
            </div>
            <article class="min-w-0 bg-white p-5 ring-1 ring-stone-200">
              <div v-if="selectedResult" class="flex h-full min-h-0 flex-col">
                <div class="flex flex-wrap items-center justify-between gap-3 border-b border-stone-200 pb-3"><div class="inline-flex rounded-md bg-stone-100 p-1"><button :class="['rounded px-3 py-1.5 text-xs font-medium', readerMode === 'result' ? 'bg-white text-stone-900 shadow-sm' : 'text-stone-500']" @click="readerMode = 'result'">{{ t('articleAi.result') }}</button><button :class="['rounded px-3 py-1.5 text-xs font-medium', readerMode === 'diff' ? 'bg-white text-stone-900 shadow-sm' : 'text-stone-500']" @click="readerMode = 'diff'">{{ t('articleAi.diff') }}</button></div><div class="flex gap-2"><button class="rounded-md border border-stone-300 px-3 py-1.5 text-xs" @click="copyResult">{{ t('articleAi.copy') }}</button><button :disabled="Boolean(currentRun.applied_profile_id)" class="rounded-md bg-stone-900 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40" @click="applyPreviewOpen = true">{{ t('articleAi.apply') }}</button></div></div>
                <div v-if="readerMode === 'result'" class="mt-4 whitespace-pre-wrap text-[15px] leading-7 text-stone-800">{{ selectedResult.result }}</div>
                <div v-else class="mt-4 space-y-3"><div v-for="(row, index) in diffRows" :key="index" class="grid gap-2 border-b border-stone-100 pb-3 md:grid-cols-2"><div :class="['whitespace-pre-wrap p-2 text-sm leading-6', row.kind === 'removed' || row.kind === 'changed' ? 'bg-red-50 text-red-800' : 'text-stone-500']">{{ row.current || '∅' }}</div><div :class="['whitespace-pre-wrap p-2 text-sm leading-6', row.kind === 'added' || row.kind === 'changed' ? 'bg-emerald-50 text-emerald-900' : 'text-stone-700']">{{ row.historical || '∅' }}</div></div></div>
              </div>
              <div v-else class="flex h-full items-center justify-center text-sm text-stone-500">{{ taskRun.running ? t('articleAi.waiting') : t('articleAi.noSuccess') }}</div>
            </article>
          </div>
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

    <Teleport to="body">
      <div v-if="profilePickerOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" @click.self="profilePickerOpen = false"><div role="dialog" aria-modal="true" aria-labelledby="article-ai-model-picker-title" class="max-h-[75vh] w-full max-w-lg overflow-y-auto rounded-lg bg-white p-5 shadow-2xl"><div class="flex items-center justify-between"><h3 id="article-ai-model-picker-title" class="font-semibold text-stone-900">{{ t('articleAi.chooseModels') }}</h3><button class="h-8 w-8 rounded-md hover:bg-stone-100" :aria-label="t('common.close')" @click="profilePickerOpen = false">×</button></div><p class="mt-1 text-xs leading-5 text-stone-500">{{ t('articleAi.modelHint') }}</p><div class="mt-4 divide-y divide-stone-200"><label v-for="profile in enabledProfiles" :key="profile.id" class="flex cursor-pointer items-start gap-3 py-3"><input :checked="selectedProfileIds.includes(profile.id)" type="checkbox" class="mt-1 h-4 w-4" @change="toggleProfile(profile.id)" /><span><span class="text-sm font-semibold text-stone-800">{{ profile.name }}<span v-if="profile.id === defaultProfileId" class="ml-2 text-xs text-stone-400">{{ t('settings.profileHub.default') }}</span></span><span class="mt-1 block text-xs text-stone-500">{{ profile.model }}</span></span></label></div><div class="mt-4 flex justify-end"><button class="rounded-md bg-stone-900 px-4 py-2 text-sm font-semibold text-white" @click="profilePickerOpen = false">{{ t('common.done') }}</button></div></div></div>

      <div v-if="applyPreviewOpen && selectedResult" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" @click.self="applyPreviewOpen = false"><div role="dialog" aria-modal="true" aria-labelledby="article-ai-apply-preview-title" class="max-h-[88vh] w-full max-w-4xl overflow-y-auto rounded-lg bg-white p-5 shadow-2xl"><div class="flex items-start justify-between gap-3"><div><h3 id="article-ai-apply-preview-title" class="font-semibold text-stone-900">{{ t('articleAi.applyPreview') }}</h3><p class="mt-1 text-xs text-stone-500">{{ t('articleAi.applySafety') }}</p></div><button class="h-8 w-8 rounded-md hover:bg-stone-100" :aria-label="t('common.close')" @click="applyPreviewOpen = false">×</button></div><div class="mt-4 grid gap-3 md:grid-cols-2"><div><h4 class="mb-2 text-xs font-semibold text-red-700">{{ t('articleAi.before') }}</h4><div class="max-h-80 overflow-y-auto whitespace-pre-wrap bg-red-50 p-3 text-sm leading-6 text-red-900">{{ selectedTextForRun }}</div></div><div><h4 class="mb-2 text-xs font-semibold text-emerald-700">{{ t('articleAi.after') }}</h4><div class="max-h-80 overflow-y-auto whitespace-pre-wrap bg-emerald-50 p-3 text-sm leading-6 text-emerald-900">{{ selectedResult.result }}</div></div></div><div class="mt-5 flex justify-end gap-2"><button class="rounded-md border border-stone-300 px-3 py-2 text-sm" @click="applyPreviewOpen = false">{{ t('common.cancel') }}</button><button :disabled="taskRun.applying" class="rounded-md bg-stone-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40" @click="applyResult">{{ taskRun.applying ? t('common.saving') : t('articleAi.confirmApply') }}</button></div></div></div>
    </Teleport>
  </div>
</template>
