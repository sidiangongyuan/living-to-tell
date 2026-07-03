<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { articlesApi } from '../../api/articles'
import { libraryApi } from '../../api/library'
import { settingsApi, type AiSettings } from '../../api/settings'
import { appApi } from '../../api/app'
import { onboardingApi, type SampleProjectState } from '../../api/onboarding'
import { errorMessage } from '../../api/base'
import { buildDailyQuoteLibraryQuery } from './quoteLink'
import { formatDateKey, useDatesStore } from './store'
import { useI18n } from '../../i18n'
import { useSettingsStore } from '../../stores/settings'

const store = useDatesStore()
const settings = useSettingsStore()
const router = useRouter()
const { t } = useI18n()
const calendarRef = ref<HTMLDivElement | null>(null)
const createError = ref('')
const onboardingLoading = ref(false)
const onboardingError = ref('')
const sampleProjectLoading = ref(false)
const sampleProjectNotice = ref('')
const sampleProjectError = ref('')
const sampleProjectSupported = ref<boolean | null>(null)
const sampleProjectState = ref<SampleProjectState>({
  installed: false,
  collection_id: null,
  entry_ids: [],
  reference_ids: [],
  ai_card_ids: [],
  note_ids: [],
  created_at: null,
  missing_ids: [],
})
const onboardingState = ref({
  hasArticle: false,
  hasReference: false,
  aiConfigured: false,
})

onMounted(() => {
  void store.goToToday()
  void loadOnboardingProgress()
})

const onboardingTasks = computed(() => {
  const hasArticle = onboardingState.value.hasArticle || store.entriesForSelectedDate.length > 0
  const hasReference = onboardingState.value.hasReference
  const aiReady = onboardingState.value.aiConfigured || settings.onboardingAiReviewed
  const storageReviewed = settings.onboardingStorageReviewed
  const chatReady = hasArticle && aiReady

  return [
    {
      id: 'article',
      title: t('welcome.firstArticle'),
      detail: t('welcome.firstArticleDetail'),
      done: hasArticle,
      actionLabel: hasArticle ? t('welcome.openArticles') : t('welcome.startNow'),
      action: startWritingForSelectedDate,
    },
    {
      id: 'reference',
      title: t('welcome.firstReference'),
      detail: t('welcome.firstReferenceDetail'),
      done: hasReference,
      actionLabel: hasReference ? t('welcome.openLibrary') : t('welcome.startNow'),
      action: createFirstReference,
    },
    {
      id: 'ai',
      title: t('welcome.aiSetup'),
      detail: t('welcome.aiSetupDetail'),
      done: aiReady,
      actionLabel: aiReady ? t('welcome.reviewAgain') : t('welcome.startNow'),
      action: openAiSettings,
    },
    {
      id: 'backup',
      title: t('welcome.backup'),
      detail: t('welcome.backupDetail'),
      done: storageReviewed,
      actionLabel: storageReviewed ? t('welcome.reviewAgain') : t('welcome.startNow'),
      action: openBackup,
    },
    {
      id: 'chat',
      title: t('welcome.articleChat'),
      detail: t('welcome.articleChatDetail'),
      done: chatReady,
      actionLabel: chatReady ? t('welcome.openChat') : t('welcome.afterArticle'),
      action: openArticleChatFromWelcome,
      disabled: !hasArticle,
    },
  ]
})

const onboardingCompletedCount = computed(() => onboardingTasks.value.filter((task) => task.done).length)

async function loadOnboardingProgress() {
  onboardingLoading.value = true
  onboardingError.value = ''
  try {
    const [articles, stats, ai, sample] = await Promise.all([
      articlesApi.listArticles(1).catch(() => []),
      libraryApi.getStats().catch(() => ({ total: 0, by_usage_kind: {} })),
      settingsApi.getAiSettings().catch(() => null),
      loadSampleProjectState().catch(() => null),
    ])
    onboardingState.value = {
      hasArticle: articles.length > 0,
      hasReference: stats.total > 0,
      aiConfigured: ai ? aiSettingsHasUsableCredential(ai) : false,
    }
    if (sample) sampleProjectState.value = sample
  } catch (e) {
    onboardingError.value = errorMessage(e)
  } finally {
    onboardingLoading.value = false
  }
}

function aiSettingsHasUsableCredential(ai: AiSettings): boolean {
  if (ai.provider_name === 'opencode') return ai.status.opencode.available
  if (ai.provider_name === 'gemini_cli') return ai.status.gemini_cli.available
  if (ai.api_key_source === 'codex') return ai.status.codex.available
  if (ai.api_key_source === 'gemini') return ai.status.gemini.available
  return ai.status.env.available
}

const calendarDays = computed(() => {
  const year = store.currentYear
  const month = store.currentMonth
  const firstDay = new Date(year, month - 1, 1)
  const lastDay = new Date(year, month, 0)
  const daysInMonth = lastDay.getDate()
  const startWeekday = firstDay.getDay()

  const days: Array<{
    date: string
    day?: number
    isEmpty: boolean
    count?: number
    hasCurated?: boolean
    isSelected?: boolean
    isToday?: boolean
  }> = []

  for (let i = 0; i < startWeekday; i++) {
    days.push({ date: '', isEmpty: true })
  }

  for (let day = 1; day <= daysInMonth; day++) {
    const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
    const stat = store.statsMap.get(dateStr)
    days.push({
      date: dateStr,
      day,
      isEmpty: false,
      count: stat?.entry_count || 0,
      hasCurated: stat?.has_curated || false,
      isSelected: dateStr === store.selectedDate,
      isToday: dateStr === formatDateKey(new Date()),
    })
  }
  return days
})

function prevMonth() {
  let y = store.currentYear
  let m = store.currentMonth - 1
  if (m < 1) {
    m = 12
    y -= 1
  }
  store.loadMonthStats(y, m)
}

function nextMonth() {
  let y = store.currentYear
  let m = store.currentMonth + 1
  if (m > 12) {
    m = 1
    y += 1
  }
  store.loadMonthStats(y, m)
}

function selectDay(dateStr: string) {
  if (dateStr) {
    store.selectDate(dateStr)
  }
}

function openArticle(entryId: string) {
  router.push({ name: 'articles', query: { id: entryId } })
}

function openDailyQuoteInLibrary() {
  if (!store.dailyQuote) return
  router.push({ name: 'library', query: buildDailyQuoteLibraryQuery(store.dailyQuote) })
}

function createFirstReference() {
  router.push({ name: 'library', query: { action: 'create_reference' } })
}

function openArticles() {
  router.push({ name: 'articles' })
}

function openArticleChatFromWelcome() {
  const firstEntry = store.entriesForSelectedDate[0]
  if (!firstEntry) {
    openArticles()
    return
  }

  router.push({
    name: 'ai',
    query: {
      tab: 'chat',
      scope_kind: 'article',
      scope_id: firstEntry.id,
    },
  })
}

function openAiSettings() {
  settings.markOnboardingAiReviewed()
  router.push({ name: 'settings' })
}

function openBackup() {
  settings.markOnboardingStorageReviewed()
  router.push({ name: 'backup' })
}

async function loadSampleProjectState(): Promise<SampleProjectState | null> {
  if (sampleProjectSupported.value === false) return null
  try {
    if (sampleProjectSupported.value === null) {
      const info = await appApi.getVersion()
      sampleProjectSupported.value = info.capabilities.includes('sample_project')
    }
    if (!sampleProjectSupported.value) return null
    const state = await onboardingApi.getSampleProject()
    sampleProjectState.value = state
    return state
  } catch {
    sampleProjectSupported.value = false
    return null
  }
}

async function createSampleProject() {
  sampleProjectLoading.value = true
  sampleProjectNotice.value = ''
  sampleProjectError.value = ''
  try {
    const result = await onboardingApi.createSampleProject()
    sampleProjectState.value = result
    sampleProjectNotice.value = result.action === 'already_installed'
      ? t('welcome.sampleProjectAlreadyInstalled')
      : t('welcome.sampleProjectCreated')
    await loadOnboardingProgress()
  } catch (e) {
    sampleProjectError.value = errorMessage(e)
  } finally {
    sampleProjectLoading.value = false
  }
}

async function deleteSampleProject() {
  if (!confirm(t('welcome.sampleProjectDeleteConfirm'))) {
    return
  }
  sampleProjectLoading.value = true
  sampleProjectNotice.value = ''
  sampleProjectError.value = ''
  try {
    const result = await onboardingApi.deleteSampleProject()
    sampleProjectState.value = result
    sampleProjectNotice.value = t('welcome.sampleProjectDeleted')
    await loadOnboardingProgress()
  } catch (e) {
    sampleProjectError.value = errorMessage(e)
  } finally {
    sampleProjectLoading.value = false
  }
}

function openSampleProject() {
  if (sampleProjectState.value.collection_id) {
    router.push({ name: 'collections' })
  }
}

async function startWritingForSelectedDate() {
  createError.value = ''
  try {
    const created = await articlesApi.create({
      title: t('dates.newArticleTitle', { date: store.selectedDate }),
      body: '',
      tags: [],
    })
    router.push({ name: 'articles', query: { id: created.id } })
  } catch (e) {
    createError.value = errorMessage(e)
  }
}
</script>

<template>
  <div class="flex h-full overflow-hidden bg-gray-50">
    <aside class="flex w-96 shrink-0 flex-col border-r border-gray-200 bg-white">
      <div class="border-b border-gray-200 p-4">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-xl font-bold">
            {{ new Date(store.currentYear, store.currentMonth - 1).toLocaleDateString('zh-CN', { month: 'long', year: 'numeric' }) }}
          </h2>
          <div class="flex gap-2">
            <button @click="prevMonth" class="rounded bg-gray-100 px-3 py-1 transition-colors hover:bg-gray-200">‹</button>
            <button @click="store.goToToday()" class="rounded bg-blue-600 px-3 py-1 text-sm text-white transition-colors hover:bg-blue-700">
              {{ t('dates.today') }}
            </button>
            <button @click="nextMonth" class="rounded bg-gray-100 px-3 py-1 transition-colors hover:bg-gray-200">›</button>
          </div>
        </div>

        <div ref="calendarRef" class="grid grid-cols-7 gap-1">
          <div v-for="day in ['日', '一', '二', '三', '四', '五', '六']" :key="day" class="py-2 text-center text-xs font-semibold text-gray-500">
            {{ day }}
          </div>
          <div
            v-for="(d, idx) in calendarDays"
            :key="idx"
            @click="selectDay(d.date)"
            :class="[
              'relative flex aspect-square cursor-pointer flex-col items-center justify-center rounded transition-colors',
              d.isEmpty ? 'pointer-events-none' : '',
              d.isSelected ? 'bg-blue-600 font-bold text-white' : d.isToday ? 'bg-blue-100 text-blue-900' : 'hover:bg-gray-100',
              (d.count ?? 0) > 0 && !d.isSelected ? 'font-semibold' : '',
            ]"
          >
            <span v-if="!d.isEmpty" class="text-sm">{{ d.day }}</span>
            <span v-if="(d.count ?? 0) > 0 && !d.isSelected" class="text-xs text-gray-500">{{ d.count }}</span>
            <div v-if="d.hasCurated && !d.isSelected" class="absolute bottom-1 h-1 w-1 rounded-full bg-green-500"></div>
          </div>
        </div>
      </div>

      <div v-if="store.dailyQuote" class="border-b border-gray-200 bg-blue-50 p-4">
        <div class="rounded-2xl border border-blue-100 bg-white/80 p-4 shadow-sm">
          <div class="max-h-56 overflow-y-auto pr-2">
            <p class="whitespace-pre-wrap text-sm italic leading-6 text-gray-700">"{{ store.dailyQuote.text }}"</p>
          </div>
          <div class="mt-4 flex items-end justify-between gap-3 border-t border-blue-100 pt-3">
            <p class="min-w-0 text-xs text-gray-500">
              — 《{{ store.dailyQuote.source_title }}》
              <span v-if="store.dailyQuote.source_author">{{ store.dailyQuote.source_author }}</span>
            </p>
            <button
              @click="openDailyQuoteInLibrary"
              class="shrink-0 rounded-lg bg-blue-600 px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-blue-700"
            >
              {{ t('nav.library') }}
            </button>
          </div>
        </div>
      </div>
    </aside>

    <div class="flex min-w-0 flex-1 flex-col overflow-hidden bg-white">
      <div class="border-b border-gray-200 p-6">
        <h2 class="text-2xl font-bold">
          {{ new Date(store.selectedDate).toLocaleDateString('zh-CN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }) }}
        </h2>
        <p class="mt-1 text-sm text-gray-500">
          {{ store.entriesForSelectedDate.length }} {{ store.entriesForSelectedDate.length === 1 ? t('dates.entry') : t('dates.entries') }}
        </p>
      </div>

      <div class="flex-1 overflow-y-auto p-6">
        <section
          v-if="!settings.welcomeChecklistDismissed"
          class="mb-6 overflow-hidden rounded-3xl border border-amber-200 bg-[#fff8ed] shadow-sm"
        >
          <div class="border-b border-amber-100 bg-white/60 p-5">
            <div class="flex items-start justify-between gap-4">
              <div class="min-w-0">
                <div class="flex flex-wrap items-center gap-3">
                  <h3 class="text-lg font-bold text-amber-950">{{ t('welcome.title') }}</h3>
                  <span class="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-900">
                    {{ t('welcome.progress', { done: onboardingCompletedCount, total: onboardingTasks.length }) }}
                  </span>
                </div>
                <p class="mt-1 max-w-3xl text-sm leading-6 text-amber-800">{{ t('welcome.subtitle') }}</p>
              </div>
              <button
                @click="settings.dismissWelcomeChecklist"
                class="rounded-xl bg-white px-3 py-2 text-xs font-semibold text-amber-800 shadow-sm hover:bg-amber-50"
              >
                {{ t('common.close') }}
              </button>
            </div>
            <div class="mt-4 h-2 overflow-hidden rounded-full bg-amber-100">
              <div
                class="h-full rounded-full bg-amber-500 transition-all"
                :style="{ width: `${Math.round((onboardingCompletedCount / onboardingTasks.length) * 100)}%` }"
              ></div>
            </div>
          </div>
          <div class="grid gap-3 p-5 lg:grid-cols-2">
            <article
              v-for="task in onboardingTasks"
              :key="task.id"
              :class="[
                'flex min-h-24 items-start gap-3 rounded-2xl border bg-white p-4 shadow-sm transition-colors',
                task.done ? 'border-emerald-100' : 'border-amber-100',
              ]"
            >
              <div
                :class="[
                  'mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold',
                  task.done ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-800',
                ]"
              >
                {{ task.done ? '✓' : '·' }}
              </div>
              <div class="min-w-0 flex-1">
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <h4 class="text-sm font-semibold text-stone-900">{{ task.title }}</h4>
                    <p class="mt-1 text-xs leading-5 text-stone-500">{{ task.detail }}</p>
                  </div>
                  <span
                    :class="[
                      'shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold',
                      task.done ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700',
                    ]"
                  >
                    {{ task.done ? t('welcome.done') : t('welcome.todo') }}
                  </span>
                </div>
                <button
                  @click="task.action"
                  :disabled="task.disabled"
                  :aria-label="task.title"
                  class="mt-3 rounded-lg bg-stone-900 px-3 py-2 text-xs font-semibold text-white hover:bg-stone-700 disabled:bg-stone-200 disabled:text-stone-500"
                >
                  {{ task.actionLabel }}
                </button>
              </div>
            </article>
          </div>
          <div v-if="onboardingLoading || onboardingError" class="border-t border-amber-100 px-5 py-3 text-xs text-amber-700">
            <span v-if="onboardingLoading">{{ t('welcome.checking') }}</span>
            <span v-else>{{ t('welcome.checkUnavailable') }}</span>
          </div>
        </section>

        <section
          v-if="!settings.welcomeChecklistDismissed"
          class="mb-6 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm"
          data-testid="sample-project-panel"
        >
          <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <h3 class="text-base font-bold text-slate-950">{{ t('welcome.sampleProjectTitle') }}</h3>
                <span
                  :class="[
                    'rounded-full px-2.5 py-1 text-xs font-semibold',
                    sampleProjectState.installed
                      ? 'bg-emerald-50 text-emerald-700'
                      : 'bg-slate-100 text-slate-600',
                  ]"
                >
                  {{ sampleProjectState.installed ? t('welcome.sampleProjectInstalled') : t('welcome.sampleProjectOptional') }}
                </span>
              </div>
              <p class="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                {{ t('welcome.sampleProjectDetail') }}
              </p>
              <div v-if="sampleProjectState.installed" class="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
                <span class="rounded-full bg-slate-50 px-2.5 py-1">{{ t('welcome.sampleProjectArticles', { count: sampleProjectState.entry_ids.length }) }}</span>
                <span class="rounded-full bg-slate-50 px-2.5 py-1">{{ t('welcome.sampleProjectReferences', { count: sampleProjectState.reference_ids.length }) }}</span>
                <span class="rounded-full bg-slate-50 px-2.5 py-1">AI Card {{ sampleProjectState.ai_card_ids.length }}</span>
                <span v-if="sampleProjectState.created_at" class="rounded-full bg-slate-50 px-2.5 py-1">
                  {{ new Date(sampleProjectState.created_at).toLocaleDateString() }}
                </span>
              </div>
            </div>
            <div class="flex shrink-0 flex-wrap gap-2">
              <button
                v-if="sampleProjectSupported !== false && !sampleProjectState.installed"
                type="button"
                class="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50"
                :disabled="sampleProjectLoading"
                @click="createSampleProject"
              >
                {{ sampleProjectLoading ? t('welcome.sampleProjectCreating') : t('welcome.sampleProjectCreate') }}
              </button>
              <button
                v-if="sampleProjectState.installed"
                type="button"
                class="rounded-xl bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200"
                @click="openSampleProject"
              >
                {{ t('welcome.sampleProjectOpenCollection') }}
              </button>
              <button
                v-if="sampleProjectState.installed"
                type="button"
                class="rounded-xl bg-red-50 px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-100 disabled:opacity-50"
                :disabled="sampleProjectLoading"
                @click="deleteSampleProject"
              >
                {{ t('welcome.sampleProjectDelete') }}
              </button>
            </div>
          </div>
          <div v-if="sampleProjectSupported === false" class="mt-3 rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-700">
            {{ t('welcome.sampleProjectUnsupported') }}
          </div>
          <div v-if="sampleProjectNotice" class="mt-3 rounded-xl bg-emerald-50 px-3 py-2 text-xs text-emerald-700">
            {{ sampleProjectNotice }}
          </div>
          <div v-if="sampleProjectError" class="mt-3 rounded-xl bg-red-50 px-3 py-2 text-xs text-red-700">
            {{ sampleProjectError }}
          </div>
        </section>

        <div v-if="store.loading" class="mt-20 text-center text-gray-400">{{ t('common.loading') }}</div>
        <div v-else-if="store.error" class="mt-20 text-center text-red-500">{{ store.error }}</div>
        <div v-else-if="!store.entriesForSelectedDate.length" class="mt-20 text-center text-gray-400">
          <p>{{ t('dates.noEntries') }}</p>
          <button
            @click="startWritingForSelectedDate"
            class="mt-5 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-blue-700"
          >
            {{ t('dates.startWriting') }}
          </button>
          <p v-if="createError" class="mt-3 text-sm text-red-500">{{ createError }}</p>
        </div>
        <div v-else class="space-y-4">
          <article
            v-for="entry in store.entriesForSelectedDate"
            :key="entry.id"
            @click="openArticle(entry.id)"
            class="cursor-pointer rounded-lg border border-gray-200 bg-white p-4 transition-all hover:border-blue-500 hover:shadow-md"
          >
            <h3 class="mb-2 text-lg font-bold">{{ entry.title }}</h3>
            <p class="mb-3 line-clamp-2 text-sm text-gray-600">{{ entry.body_preview }}</p>
            <div class="flex items-center gap-2">
              <span
                v-for="tag in entry.tags"
                :key="tag"
                class="rounded bg-blue-100 px-2 py-1 text-xs text-blue-700"
              >{{ tag }}</span>
              <span
                v-if="entry.curation_status !== 'unsorted'"
                class="rounded bg-green-100 px-2 py-1 text-xs text-green-700"
              >{{ entry.curation_status }}</span>
            </div>
          </article>
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
