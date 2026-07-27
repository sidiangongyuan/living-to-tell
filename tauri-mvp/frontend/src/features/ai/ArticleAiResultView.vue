<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { AiTaskCompareResult, ArticleAiTaskRun } from '../../api/ai'
import { errorMessage } from '../../api/base'
import { useI18n } from '../../i18n'
import { buildParagraphDiff } from '../articles/versionDiff'
import { useArticleTaskRunStore } from './articleTaskRunStore'

type ReaderMode = 'compare' | 'dual' | 'diff'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const taskRun = useArticleTaskRunStore()

const selectedProfileId = ref('')
const secondaryProfileId = ref('')
const readerMode = ref<ReaderMode>('compare')
const editing = ref(false)
const draftText = ref('')
const draftDirty = ref(false)
const localError = ref('')
const notice = ref('')
let draftTimer: ReturnType<typeof setTimeout> | null = null
let draftSaveToken = 0

const run = computed(() => taskRun.run)
const successfulResults = computed(() => run.value?.results.filter((item) => item.status === 'success') ?? [])
const selectedResult = computed(() => resultForProfile(selectedProfileId.value) ?? successfulResults.value[0] ?? null)
const secondaryResult = computed(() => resultForProfile(secondaryProfileId.value)
  ?? successfulResults.value.find((item) => item.profile_id !== selectedResult.value?.profile_id)
  ?? null)
const candidateText = computed(() => {
  if (!selectedResult.value) return ''
  if (editing.value) return draftText.value
  return savedCandidate(selectedResult.value)
})
const secondaryText = computed(() => secondaryResult.value ? savedCandidate(secondaryResult.value) : '')
const diffRows = computed(() => buildParagraphDiff(run.value?.original_text ?? '', candidateText.value))
const referenceSnapshots = computed(() => groupSnapshots(run.value))
const articleState = computed(() => run.value?.article_state ?? 'ready')
const canApply = computed(() => Boolean(
  selectedResult.value
  && articleState.value === 'ready'
  && !run.value?.applied_profile_id
  && !taskRun.applying
  && !taskRun.draftSaving,
))

watch(successfulResults, (results) => {
  if (!results.length) return
  if (!results.some((item) => item.profile_id === selectedProfileId.value)) {
    selectedProfileId.value = results[0].profile_id
  }
  if (!results.some((item) => item.profile_id === secondaryProfileId.value && item.profile_id !== selectedProfileId.value)) {
    secondaryProfileId.value = results.find((item) => item.profile_id !== selectedProfileId.value)?.profile_id ?? ''
  }
}, { deep: true, immediate: true })

watch(selectedProfileId, () => {
  editing.value = false
  draftDirty.value = false
  clearDraftTimer()
  draftText.value = selectedResult.value ? savedCandidate(selectedResult.value) : ''
  if (secondaryProfileId.value === selectedProfileId.value) {
    secondaryProfileId.value = successfulResults.value.find((item) => item.profile_id !== selectedProfileId.value)?.profile_id ?? ''
  }
})

watch(draftText, () => {
  if (!editing.value) return
  draftDirty.value = true
  clearDraftTimer()
  draftTimer = globalThis.setTimeout(() => void saveDraftNow(), 600)
})

watch(() => route.params.runId, (value) => {
  if (typeof value === 'string' && value) void loadRun(value)
})

onMounted(() => {
  const runId = String(route.params.runId || '')
  if (runId) void loadRun(runId)
})

onBeforeUnmount(() => {
  clearDraftTimer()
  if (editing.value && draftDirty.value) void saveDraftNow()
})

async function loadRun(runId: string) {
  localError.value = ''
  notice.value = ''
  editing.value = false
  const loaded = await taskRun.open(runId)
  await taskRun.refreshHistory()
  if (!loaded) return
  selectInitialModels(loaded)
}

function selectInitialModels(value: ArticleAiTaskRun) {
  const success = value.results.filter((item) => item.status === 'success')
  selectedProfileId.value = success[0]?.profile_id ?? value.results[0]?.profile_id ?? ''
  secondaryProfileId.value = success[1]?.profile_id ?? ''
}

function resultForProfile(profileId: string): AiTaskCompareResult | null {
  return run.value?.results.find((item) => item.profile_id === profileId) ?? null
}

function rawCandidate(result: AiTaskCompareResult): string {
  return result.raw_result ?? result.result ?? ''
}

function savedCandidate(result: AiTaskCompareResult): string {
  return result.draft_result ?? rawCandidate(result)
}

function groupSnapshots(value: ArticleAiTaskRun | null) {
  const groups = [
    { kind: 'style_specimen', label: t('articleAi.contextSources.references'), items: [] as NonNullable<ArticleAiTaskRun['attachment_snapshots']> },
    { kind: 'ai_card', label: 'AI Cards', items: [] as NonNullable<ArticleAiTaskRun['attachment_snapshots']> },
    { kind: 'writing_note', label: t('articleAi.notes'), items: [] as NonNullable<ArticleAiTaskRun['attachment_snapshots']> },
  ]
  for (const item of value?.attachment_snapshots ?? []) {
    groups.find((group) => group.kind === item.kind)?.items.push(item)
  }
  return groups.filter((group) => group.items.length)
}

function formatElapsed(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`
}

function resultStatus(result: AiTaskCompareResult): string {
  if (result.status === 'success') return t('articleAi.status.success')
  if (result.status === 'error') return t('articleAi.status.error')
  return t('articleAi.status.pending')
}

function taskLabel(task: ArticleAiTaskRun['task_type']): string {
  return t(`articleAi.tasks.${task}`)
}

function historySummary(item: ArticleAiTaskRun): string {
  return `${taskLabel(item.task_type)} · ${new Date(item.created_at).toLocaleString()}`
}

function articleStateLabel(): string {
  return t(`articleAiResults.articleState.${articleState.value}`)
}

function beginEdit() {
  if (!selectedResult.value) return
  draftText.value = savedCandidate(selectedResult.value)
  draftDirty.value = false
  editing.value = true
}

async function saveDraftNow() {
  clearDraftTimer()
  if (!editing.value || !draftDirty.value || !selectedResult.value || !run.value) return
  const token = ++draftSaveToken
  const profileId = selectedResult.value.profile_id
  const value = draftText.value
  localError.value = ''
  try {
    await taskRun.saveDraft(
      profileId,
      value,
      selectedResult.value.draft_fingerprint ?? selectedResult.value.raw_fingerprint,
    )
    if (token === draftSaveToken) {
      draftDirty.value = false
      notice.value = t('articleAiResults.draftSaved')
    }
  } catch (e) {
    if (token === draftSaveToken) localError.value = errorMessage(e)
  }
}

async function resetDraft() {
  if (!selectedResult.value || !window.confirm(t('articleAiResults.resetDraftConfirm'))) return
  clearDraftTimer()
  try {
    await taskRun.resetDraft(selectedResult.value.profile_id)
    draftText.value = rawCandidate(selectedResult.value)
    draftDirty.value = false
    editing.value = false
    notice.value = t('articleAiResults.draftReset')
  } catch (e) {
    localError.value = errorMessage(e)
  }
}

async function copyCandidate() {
  try {
    await navigator.clipboard.writeText(candidateText.value)
    notice.value = t('articleAi.copied')
  } catch (e) {
    localError.value = errorMessage(e)
  }
}

async function applyCandidate() {
  if (!selectedResult.value || !run.value) return
  localError.value = ''
  try {
    if (editing.value && draftDirty.value) await saveDraftNow()
    const refreshedResult = resultForProfile(selectedResult.value.profile_id)
    const kind = refreshedResult?.draft_result !== null && refreshedResult?.draft_result !== undefined ? 'draft' : 'raw'
    const fingerprint = kind === 'draft'
      ? refreshedResult?.draft_fingerprint
      : refreshedResult?.raw_fingerprint
    const applied = await taskRun.apply(selectedResult.value.profile_id, kind, fingerprint)
    notice.value = applied.was_noop ? t('articleAi.alreadyApplied') : t('articleAi.applied')
  } catch (e) {
    localError.value = errorMessage(e)
  }
}

async function cancelRun() {
  if (!window.confirm(t('articleAi.cancelConfirm'))) return
  try {
    await taskRun.cancel()
  } catch (e) {
    localError.value = errorMessage(e)
  }
}

async function deleteCurrentRun() {
  if (!window.confirm(t('articleAi.clearConfirm'))) return
  try {
    await taskRun.clear()
    await router.replace({ name: 'ai' })
  } catch (e) {
    localError.value = errorMessage(e)
  }
}

async function clearHistory() {
  if (!window.confirm(t('articleAiResults.clearHistoryConfirm'))) return
  try {
    await taskRun.clearHistory()
    await router.replace({ name: 'ai' })
  } catch (e) {
    localError.value = errorMessage(e)
  }
}

function openHistory(item: ArticleAiTaskRun) {
  if (item.run_id === run.value?.run_id) return
  void router.push({ name: 'ai-results', params: { runId: item.run_id } })
}

function openArticle() {
  if (run.value?.article_id) void router.push({ name: 'articles', query: { id: run.value.article_id } })
}

function clearDraftTimer() {
  if (draftTimer !== null) globalThis.clearTimeout(draftTimer)
  draftTimer = null
}
</script>

<template>
  <div class="flex h-full min-h-0 bg-stone-100" data-testid="article-ai-results-workspace">
    <aside class="hidden w-64 shrink-0 overflow-y-auto border-r border-stone-200 bg-white p-4 lg:block">
      <div class="flex items-center justify-between gap-2">
        <h2 class="text-sm font-semibold text-stone-900">{{ t('articleAiResults.history') }}</h2>
        <button type="button" class="rounded-md px-2 py-1 text-xs text-stone-500 hover:bg-stone-100" @click="clearHistory">{{ t('articleAiResults.clearHistory') }}</button>
      </div>
      <div class="mt-3 space-y-1">
        <button
          v-for="item in taskRun.history"
          :key="item.run_id"
          type="button"
          :class="['w-full border-l-2 px-3 py-2 text-left', item.run_id === run?.run_id ? 'border-teal-700 bg-teal-50' : 'border-transparent hover:bg-stone-50']"
          @click="openHistory(item)"
        >
          <span class="block truncate text-sm font-medium text-stone-800">{{ item.article_title }}</span>
          <span class="mt-1 block text-xs leading-5 text-stone-500">{{ historySummary(item) }}</span>
        </button>
      </div>
    </aside>

    <main class="min-w-0 flex-1 overflow-y-auto">
      <div class="mx-auto max-w-[1500px] p-4 md:p-6">
        <header class="flex flex-wrap items-start justify-between gap-4 border-b border-stone-300 pb-4">
          <div>
            <p class="text-xs font-semibold uppercase text-teal-800">{{ t('articleAiResults.kicker') }}</p>
            <h1 class="mt-1 text-xl font-semibold text-stone-950">{{ run?.article_title || t('articleAiResults.title') }}</h1>
            <p v-if="run" class="mt-1 text-sm text-stone-600">{{ taskLabel(run.task_type) }} · {{ run.stage_label }} · {{ formatElapsed(run.elapsed_ms) }}</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <button type="button" class="rounded-md border border-stone-300 bg-white px-3 py-2 text-sm text-stone-700 hover:bg-stone-50" @click="router.push({ name: 'ai' })">{{ t('articleAiResults.newRun') }}</button>
            <button type="button" class="rounded-md border border-stone-300 bg-white px-3 py-2 text-sm text-stone-700 hover:bg-stone-50" @click="openArticle">{{ t('articleAi.backToArticle') }}</button>
          </div>
        </header>

        <div v-if="localError || taskRun.statusError" class="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{{ localError || taskRun.statusError }}</div>
        <div v-if="notice" class="mt-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{{ notice }}</div>

        <div v-if="taskRun.loading" class="py-20 text-center text-sm text-stone-500">{{ t('common.loading') }}</div>
        <div v-else-if="!run" class="py-20 text-center">
          <h2 class="text-lg font-semibold text-stone-800">{{ t('articleAiResults.expiredTitle') }}</h2>
          <p class="mx-auto mt-2 max-w-xl text-sm leading-6 text-stone-600">{{ taskRun.statusError || t('articleAiResults.expiredBody') }}</p>
          <button type="button" class="mt-5 rounded-md bg-stone-900 px-4 py-2 text-sm font-semibold text-white" @click="router.push({ name: 'ai' })">{{ t('articleAiResults.returnSetup') }}</button>
        </div>

        <template v-else>
          <section class="mt-5 grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">
            <div class="space-y-3">
              <div class="border-y border-stone-300 py-3">
                <div class="flex items-center justify-between gap-3">
                  <span class="text-sm font-semibold text-stone-800">{{ run.stage_label }}</span>
                  <span class="text-xs text-stone-500">{{ formatElapsed(run.elapsed_ms) }}</span>
                </div>
                <p v-if="taskRun.reconnectCount" class="mt-2 text-xs text-amber-800">{{ t('articleAi.reconnecting', { count: taskRun.reconnectCount }) }}</p>
                <div class="mt-3 flex flex-wrap gap-3">
                  <button v-if="taskRun.running" type="button" class="text-xs font-medium text-red-700 underline" @click="cancelRun">{{ t('articleAi.cancel') }}</button>
                  <button v-else type="button" class="text-xs font-medium text-stone-600 underline" @click="deleteCurrentRun">{{ t('articleAi.clear') }}</button>
                </div>
              </div>

              <div class="space-y-2">
                <button
                  v-for="result in run.results"
                  :key="result.profile_id"
                  type="button"
                  :class="[
                    'w-full border p-3 text-left',
                    selectedResult?.profile_id === result.profile_id ? 'border-stone-900 bg-stone-900 text-white' : 'border-stone-300 bg-white text-stone-700 hover:border-stone-500',
                  ]"
                  @click="selectedProfileId = result.profile_id"
                >
                  <span class="block text-sm font-semibold">{{ result.profile_name }}</span>
                  <span class="mt-1 block text-xs">{{ resultStatus(result) }}<template v-if="result.elapsed_ms"> · {{ formatElapsed(result.elapsed_ms) }}</template></span>
                  <span v-if="result.status === 'success'" class="mt-1 block text-xs opacity-75">{{ result.output_tokens ?? '-' }} tokens · {{ result.transport || '-' }}</span>
                  <span v-if="result.draft_result !== null && result.draft_result !== undefined" class="mt-2 inline-block rounded bg-amber-100 px-1.5 py-0.5 text-[11px] font-medium text-amber-900">{{ t('articleAiResults.editedDraft') }}</span>
                  <span v-if="result.error" class="mt-2 block text-xs text-red-600">{{ result.error }}</span>
                </button>
              </div>
            </div>

            <div class="min-w-0">
              <div class="flex flex-wrap items-center justify-between gap-3 border-b border-stone-300 pb-3">
                <div class="inline-flex rounded-md bg-stone-200 p-1">
                  <button v-for="mode in (['compare', 'dual', 'diff'] as const)" :key="mode" type="button" :class="['rounded px-3 py-1.5 text-xs font-medium', readerMode === mode ? 'bg-white text-stone-900 shadow-sm' : 'text-stone-600']" @click="readerMode = mode">{{ t(`articleAiResults.modes.${mode}`) }}</button>
                </div>
                <div class="flex flex-wrap gap-2">
                  <button type="button" class="rounded-md border border-stone-300 bg-white px-3 py-1.5 text-xs text-stone-700" @click="copyCandidate">{{ t('articleAi.copy') }}</button>
                  <button v-if="!editing" type="button" :disabled="!selectedResult || selectedResult.status !== 'success'" class="rounded-md border border-stone-300 bg-white px-3 py-1.5 text-xs text-stone-700 disabled:opacity-40" @click="beginEdit">{{ t('articleAiResults.editCopy') }}</button>
                  <button v-else type="button" class="rounded-md border border-stone-300 bg-white px-3 py-1.5 text-xs text-stone-700" @click="saveDraftNow">{{ taskRun.draftSaving ? t('common.saving') : t('common.save') }}</button>
                  <button v-if="selectedResult?.draft_result !== null && selectedResult?.draft_result !== undefined" type="button" class="rounded-md border border-stone-300 bg-white px-3 py-1.5 text-xs text-stone-700" @click="resetDraft">{{ t('articleAiResults.resetDraft') }}</button>
                </div>
              </div>

              <div v-if="selectedResult && selectedResult.status === 'success'" class="mt-4">
                <div v-if="readerMode === 'compare'" class="grid gap-3 xl:grid-cols-2">
                  <article class="min-w-0 border border-stone-300 bg-white">
                    <h2 class="border-b border-stone-200 px-4 py-3 text-sm font-semibold text-stone-700">{{ t('articleAi.before') }}</h2>
                    <div class="max-h-[62vh] overflow-y-auto whitespace-pre-wrap p-5 text-[15px] leading-7 text-stone-700">{{ run.original_text }}</div>
                  </article>
                  <article class="min-w-0 border border-stone-300 bg-white">
                    <h2 class="flex items-center justify-between gap-3 border-b border-stone-200 px-4 py-3 text-sm font-semibold text-stone-800">
                      <span>{{ selectedResult.profile_name }}</span>
                      <span v-if="editing" class="text-xs font-normal text-amber-800">{{ draftDirty ? t('articleAiResults.draftUnsaved') : t('articleAiResults.draftSaved') }}</span>
                    </h2>
                    <textarea v-if="editing" v-model="draftText" class="min-h-[62vh] w-full resize-y border-0 p-5 text-[15px] leading-7 text-stone-800 outline-none" :aria-label="t('articleAiResults.editCopy')" />
                    <div v-else class="max-h-[62vh] overflow-y-auto whitespace-pre-wrap p-5 text-[15px] leading-7 text-stone-800">{{ candidateText }}</div>
                  </article>
                </div>

                <div v-else-if="readerMode === 'dual'" class="grid gap-3 xl:grid-cols-2">
                  <article class="min-w-0 border border-stone-300 bg-white">
                    <select v-model="selectedProfileId" class="m-3 rounded-md border border-stone-300 bg-white px-3 py-2 text-sm">
                      <option v-for="result in successfulResults" :key="result.profile_id" :value="result.profile_id">{{ result.profile_name }}</option>
                    </select>
                    <div class="max-h-[62vh] overflow-y-auto whitespace-pre-wrap border-t border-stone-200 p-5 text-[15px] leading-7 text-stone-800">{{ candidateText }}</div>
                  </article>
                  <article class="min-w-0 border border-stone-300 bg-white">
                    <select v-model="secondaryProfileId" class="m-3 rounded-md border border-stone-300 bg-white px-3 py-2 text-sm">
                      <option v-for="result in successfulResults.filter((item) => item.profile_id !== selectedProfileId)" :key="result.profile_id" :value="result.profile_id">{{ result.profile_name }}</option>
                    </select>
                    <div class="max-h-[62vh] overflow-y-auto whitespace-pre-wrap border-t border-stone-200 p-5 text-[15px] leading-7 text-stone-800">{{ secondaryText || t('articleAiResults.chooseSecondModel') }}</div>
                  </article>
                </div>

                <div v-else class="space-y-3">
                  <div v-for="(row, index) in diffRows" :key="index" class="grid gap-2 border-b border-stone-200 pb-3 md:grid-cols-2">
                    <div :class="['whitespace-pre-wrap p-3 text-sm leading-6', row.kind === 'removed' || row.kind === 'changed' ? 'bg-red-50 text-red-800' : 'bg-white text-stone-500']">{{ row.current || '∅' }}</div>
                    <div :class="['whitespace-pre-wrap p-3 text-sm leading-6', row.kind === 'added' || row.kind === 'changed' ? 'bg-emerald-50 text-emerald-900' : 'bg-white text-stone-700']">{{ row.historical || '∅' }}</div>
                  </div>
                </div>
              </div>
              <div v-else class="flex min-h-80 items-center justify-center border border-stone-300 bg-white text-sm text-stone-500">{{ taskRun.running ? t('articleAi.waiting') : t('articleAi.noSuccess') }}</div>
            </div>
          </section>

          <section class="mt-6 grid gap-5 border-t border-stone-300 pt-5 xl:grid-cols-[minmax(0,1fr)_360px]">
            <div data-testid="article-ai-run-references">
              <div v-if="run.preset_snapshot?.name" class="flex flex-wrap items-center gap-2 text-sm text-stone-700">
                <span class="font-semibold">{{ t('articleAiResults.presetUsed') }}</span>
                <span>{{ run.preset_snapshot.name }}</span>
              </div>
              <div v-for="group in referenceSnapshots" :key="group.kind" class="mt-3 flex flex-wrap items-center gap-2">
                <span class="text-sm font-semibold text-stone-700">{{ group.label }}</span>
                <span v-for="item in group.items" :key="`${item.kind}:${item.ref_id}`" class="rounded bg-white px-2 py-1 text-sm text-stone-700 ring-1 ring-stone-200">{{ item.name }}</span>
              </div>
            </div>

            <aside class="border-l-4 border-stone-800 bg-white p-4" data-testid="article-ai-writeback-panel">
              <div class="flex items-center justify-between gap-3">
                <h2 class="text-sm font-semibold text-stone-900">{{ t('articleAiResults.writeBack') }}</h2>
                <span :class="['rounded px-2 py-1 text-xs font-medium', articleState === 'ready' ? 'bg-emerald-100 text-emerald-900' : articleState === 'changed' ? 'bg-amber-100 text-amber-900' : 'bg-red-100 text-red-900']">{{ articleStateLabel() }}</span>
              </div>
              <p class="mt-2 text-sm leading-6 text-stone-600">{{ t(`articleAiResults.articleStateHelp.${articleState}`) }}</p>
              <p class="mt-2 text-xs leading-5 text-stone-500">{{ t('articleAi.applySafety') }}</p>
              <button type="button" :disabled="!canApply" class="mt-4 w-full rounded-md bg-stone-900 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-40" @click="applyCandidate">{{ taskRun.applying ? t('common.saving') : t('articleAi.confirmApply') }}</button>
              <p v-if="run.applied_profile_id" class="mt-3 text-sm text-emerald-800">{{ t('articleAiResults.appliedCandidate') }}</p>
            </aside>
          </section>
        </template>
      </div>
    </main>
  </div>
</template>
