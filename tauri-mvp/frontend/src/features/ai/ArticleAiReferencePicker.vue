<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { errorMessage } from '../../api/base'
import { libraryApi, type Reference } from '../../api/library'
import { useI18n } from '../../i18n'

const props = defineProps<{
  open: boolean
  selected: Reference[]
}>()

const emit = defineEmits<{
  close: []
  confirm: [references: Reference[]]
  openLibrary: []
}>()

type UsageFilter = 'all' | 'style' | 'imagery' | 'structure' | 'rhetoric' | 'technique' | 'reflection' | 'other'

const { t } = useI18n()
const query = ref('')
const usageFilter = ref<UsageFilter>('all')
const loading = ref(false)
const error = ref('')
const results = ref<Reference[]>([])
const knownReferences = ref(new Map<string, Reference>())
const draftReferenceIds = ref<string[]>([])
const previewReference = ref<Reference | null>(null)
let requestToken = 0
let searchTimer: ReturnType<typeof setTimeout> | null = null

const usageOptions = computed(() => [
  { value: 'all' as const, label: t('library.filterAll') },
  { value: 'style' as const, label: t('library.style') },
  { value: 'imagery' as const, label: t('library.imagery') },
  { value: 'structure' as const, label: t('library.structure') },
  { value: 'rhetoric' as const, label: t('library.rhetoric') },
  { value: 'technique' as const, label: t('library.technique') },
  { value: 'reflection' as const, label: t('library.reflection') },
  { value: 'other' as const, label: t('library.other') },
])

const draftReferences = computed(() => draftReferenceIds.value
  .map((id) => knownReferences.value.get(id))
  .filter((item): item is Reference => Boolean(item)))
const draftChars = computed(() => draftReferences.value.reduce((total, item) => total + item.content.length, 0))
const contextLarge = computed(() => draftChars.value > 20_000)

watch(() => props.open, (open) => {
  if (!open) return
  query.value = ''
  usageFilter.value = 'all'
  error.value = ''
  previewReference.value = null
  draftReferenceIds.value = props.selected.map((item) => item.id)
  knownReferences.value = new Map(props.selected.map((item) => [item.id, item]))
  scheduleLoad(0)
}, { immediate: true })

watch([query, usageFilter], () => {
  if (props.open) scheduleLoad(250)
})

function scheduleLoad(delay: number) {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => void loadReferences(), delay)
}

async function loadReferences() {
  const token = ++requestToken
  loading.value = true
  error.value = ''
  try {
    const trimmed = query.value.trim()
    const usage = usageFilter.value === 'all' ? undefined : usageFilter.value
    const items = trimmed
      ? await libraryApi.searchReferences(trimmed, 200, usage)
      : await libraryApi.listReferences(500, usage)
    if (token !== requestToken || !props.open) return
    const nextKnown = new Map(knownReferences.value)
    for (const item of items) nextKnown.set(item.id, item)
    knownReferences.value = nextKnown
    results.value = items
  } catch (cause) {
    if (token !== requestToken || !props.open) return
    error.value = errorMessage(cause)
    results.value = []
  } finally {
    if (token === requestToken) loading.value = false
  }
}

function toggleReference(referenceId: string) {
  draftReferenceIds.value = draftReferenceIds.value.includes(referenceId)
    ? draftReferenceIds.value.filter((id) => id !== referenceId)
    : [...draftReferenceIds.value, referenceId]
}

function confirmSelection() {
  emit('confirm', draftReferences.value)
}

function cancelSelection() {
  previewReference.value = null
  emit('close')
}

function clearSearch() {
  query.value = ''
}

function referenceTitle(reference: Reference): string {
  const title = reference.source_title.trim()
  return title ? `《${title}》` : t('articleAi.referencePicker.untitled')
}

function usageLabel(reference: Reference): string {
  const key = `library.${reference.usage_kind || 'other'}`
  const translated = t(key)
  return translated === key ? t('library.other') : translated
}

function onKeydown(event: KeyboardEvent) {
  if (!props.open || event.key !== 'Escape') return
  event.preventDefault()
  event.stopPropagation()
  if (previewReference.value) {
    previewReference.value = null
    return
  }
  cancelSelection()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  if (searchTimer) clearTimeout(searchTimer)
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-[60] flex items-center justify-center bg-black/45 p-3 sm:p-6"
      data-testid="article-ai-reference-picker"
      @click.self="cancelSelection"
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="article-ai-reference-picker-title"
        class="flex max-h-[88vh] w-full max-w-[920px] flex-col overflow-hidden rounded-lg bg-white shadow-2xl"
      >
        <header class="shrink-0 border-b border-stone-200 px-4 py-4 sm:px-5">
          <div class="flex items-start justify-between gap-4">
            <div>
              <h2 id="article-ai-reference-picker-title" class="text-lg font-semibold text-stone-950">
                {{ t('articleAi.referencePicker.title') }}
              </h2>
              <p class="mt-1 text-sm text-stone-600">{{ t('articleAi.referencePicker.selectedSummary', { count: draftReferenceIds.length, chars: draftChars }) }}</p>
            </div>
            <button type="button" class="h-9 w-9 rounded-md text-xl text-stone-600 hover:bg-stone-100" :aria-label="t('common.close')" @click="cancelSelection">×</button>
          </div>

          <div v-if="!previewReference" class="mt-4 space-y-3">
            <div class="flex flex-col gap-2 sm:flex-row">
              <label class="relative min-w-0 flex-1">
                <span class="sr-only">{{ t('articleAi.referencePicker.search') }}</span>
                <input
                  v-model="query"
                  autofocus
                  class="w-full rounded-md border border-stone-300 px-3 py-2.5 pr-20 text-sm text-stone-900 outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
                  :placeholder="t('articleAi.referencePicker.search')"
                />
                <button v-if="query" type="button" class="absolute right-2 top-1.5 rounded px-2 py-1 text-sm text-stone-600 hover:bg-stone-100" @click="clearSearch">
                  {{ t('articleAi.referencePicker.clearSearch') }}
                </button>
              </label>
              <button type="button" class="rounded-md border border-stone-300 px-3 py-2 text-sm font-medium text-stone-700 hover:bg-stone-50" @click="draftReferenceIds = []">
                {{ t('articleAi.referencePicker.clearSelection') }}
              </button>
            </div>
            <div class="flex flex-wrap gap-1 rounded-md bg-stone-100 p-1" :aria-label="t('articleAi.referencePicker.usageFilter')">
              <button
                v-for="option in usageOptions"
                :key="option.value"
                type="button"
                :class="['rounded px-3 py-1.5 text-sm font-medium', usageFilter === option.value ? 'bg-white text-stone-950 shadow-sm' : 'text-stone-600 hover:text-stone-900']"
                @click="usageFilter = option.value"
              >
                {{ option.label }}
              </button>
            </div>
          </div>
        </header>

        <div class="min-h-0 flex-1 overflow-y-auto p-4 sm:p-5">
          <template v-if="previewReference">
            <button type="button" class="mb-4 text-sm font-medium text-stone-700 underline" @click="previewReference = null">
              {{ t('articleAi.referencePicker.backToList') }}
            </button>
            <article class="mx-auto max-w-3xl">
              <div class="flex flex-wrap items-start justify-between gap-3 border-b border-stone-200 pb-4">
                <div>
                  <h3 class="text-xl font-semibold text-stone-950">{{ referenceTitle(previewReference) }}</h3>
                  <p v-if="previewReference.source_author" class="mt-1 text-sm text-stone-600">{{ previewReference.source_author }}</p>
                </div>
                <span class="rounded bg-emerald-50 px-2 py-1 text-sm font-medium text-emerald-800">{{ usageLabel(previewReference) }}</span>
              </div>
              <div v-if="previewReference.tags.length" class="mt-4 flex flex-wrap gap-2">
                <span v-for="tag in previewReference.tags" :key="tag" class="rounded bg-stone-100 px-2 py-1 text-sm text-stone-700">{{ tag }}</span>
              </div>
              <section v-if="previewReference.personal_note" class="mt-5 border-l-2 border-amber-400 bg-amber-50 px-4 py-3">
                <h4 class="text-sm font-semibold text-amber-900">{{ t('library.personalNote') }}</h4>
                <p class="mt-1 whitespace-pre-wrap text-sm leading-6 text-amber-950">{{ previewReference.personal_note }}</p>
              </section>
              <div class="mt-5 whitespace-pre-wrap text-[15px] leading-7 text-stone-800">{{ previewReference.content }}</div>
              <p v-if="previewReference.content.length > 40_000" class="mt-4 rounded-md bg-amber-50 p-3 text-sm text-amber-900">
                {{ t('articleAi.referencePicker.itemTruncated') }}
              </p>
            </article>
          </template>

          <template v-else>
            <div v-if="loading" class="py-16 text-center text-sm text-stone-600">{{ t('common.loading') }}</div>
            <div v-else-if="error" class="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800">
              <p>{{ error }}</p>
              <button type="button" class="mt-3 font-medium underline" @click="loadReferences">{{ t('common.refresh') }}</button>
            </div>
            <div v-else-if="!results.length" class="py-14 text-center">
              <p class="text-sm text-stone-600">{{ query ? t('articleAi.referencePicker.noMatches') : t('articleAi.referencePicker.empty') }}</p>
              <button v-if="!query" type="button" class="mt-4 rounded-md bg-stone-900 px-4 py-2 text-sm font-semibold text-white hover:bg-stone-700" @click="emit('openLibrary')">
                {{ t('articleAi.referencePicker.openLibrary') }}
              </button>
            </div>
            <div v-else class="grid gap-3 md:grid-cols-2">
              <article
                v-for="reference in results"
                :key="reference.id"
                :class="['relative flex min-h-[220px] flex-col rounded-md border p-4 transition', draftReferenceIds.includes(reference.id) ? 'border-emerald-500 bg-emerald-50/70 shadow-sm' : 'border-stone-200 bg-white hover:border-emerald-300']"
                data-testid="article-ai-reference-card"
              >
                <button
                  type="button"
                  class="absolute inset-0 z-0 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2"
                  :aria-label="t(draftReferenceIds.includes(reference.id) ? 'articleAi.referencePicker.deselect' : 'articleAi.referencePicker.select', { name: referenceTitle(reference) })"
                  :aria-pressed="draftReferenceIds.includes(reference.id)"
                  @click="toggleReference(reference.id)"
                />
                <div class="pointer-events-none relative z-10 flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <h3 class="truncate text-[15px] font-semibold text-stone-950">{{ referenceTitle(reference) }}</h3>
                    <p v-if="reference.source_author" class="mt-1 truncate text-sm text-stone-600">{{ reference.source_author }}</p>
                  </div>
                  <span :class="['flex h-6 w-6 shrink-0 items-center justify-center rounded border text-sm font-bold', draftReferenceIds.includes(reference.id) ? 'border-emerald-600 bg-emerald-600 text-white' : 'border-stone-300 bg-white text-transparent']" aria-hidden="true">✓</span>
                </div>
                <div class="pointer-events-none relative z-10 mt-3 flex flex-wrap gap-1.5">
                  <span class="rounded bg-emerald-100 px-2 py-1 text-sm font-medium text-emerald-900">{{ usageLabel(reference) }}</span>
                  <span v-for="tag in reference.tags.slice(0, 4)" :key="tag" class="rounded bg-stone-100 px-2 py-1 text-sm text-stone-700">{{ tag }}</span>
                </div>
                <p class="pointer-events-none relative z-10 mt-3 line-clamp-4 flex-1 whitespace-pre-wrap text-sm leading-6 text-stone-700">{{ reference.content }}</p>
                <div class="pointer-events-none relative z-10 mt-3 flex items-center justify-between gap-3 border-t border-stone-200 pt-3">
                  <span :class="['text-sm', reference.content.length > 40_000 ? 'font-medium text-amber-800' : 'text-stone-500']">
                    {{ reference.content.length }} {{ t('articleAi.characters') }}
                  </span>
                  <button type="button" class="pointer-events-auto relative z-20 rounded px-1 py-0.5 text-sm font-medium text-stone-700 underline hover:bg-stone-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500" @click="previewReference = reference">
                    {{ t('articleAi.referencePicker.preview') }}
                  </button>
                </div>
              </article>
            </div>
          </template>
        </div>

        <footer class="shrink-0 border-t border-stone-200 bg-stone-50 px-4 py-3 sm:px-5">
          <div v-if="contextLarge" class="mb-3 rounded-md bg-amber-100 px-3 py-2 text-sm text-amber-950">
            {{ t('articleAi.referencePicker.largeContext') }}
          </div>
          <div class="flex flex-wrap items-center justify-between gap-3">
            <span class="text-sm text-stone-700">{{ t('articleAi.referencePicker.selectedSummary', { count: draftReferenceIds.length, chars: draftChars }) }}</span>
            <div class="flex gap-2">
              <button type="button" class="rounded-md border border-stone-300 bg-white px-4 py-2 text-sm font-medium text-stone-700 hover:bg-stone-100" @click="cancelSelection">
                {{ t('common.cancel') }}
              </button>
              <button type="button" class="rounded-md bg-stone-900 px-4 py-2 text-sm font-semibold text-white hover:bg-stone-700" @click="confirmSelection">
                {{ t('articleAi.referencePicker.useSelected', { count: draftReferenceIds.length }) }}
              </button>
            </div>
          </div>
        </footer>
      </section>
    </div>
  </Teleport>
</template>
