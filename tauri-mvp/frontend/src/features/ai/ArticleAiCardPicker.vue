<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { errorMessage } from '../../api/base'
import { aiCardApi, type AiCard, type AiCardType } from '../../api/aiCards'
import { useI18n } from '../../i18n'
import { trapFocus } from '../../utils/focusTrap'

const props = defineProps<{ open: boolean; selected: AiCard[] }>()
const emit = defineEmits<{ close: []; confirm: [cards: AiCard[]]; openCards: [] }>()
const { t } = useI18n()

type CardFilter = 'all' | AiCardType
const query = ref('')
const cardFilter = ref<CardFilter>('all')
const loading = ref(false)
const error = ref('')
const results = ref<AiCard[]>([])
const knownCards = ref(new Map<string, AiCard>())
const draftIds = ref<string[]>([])
const previewCard = ref<AiCard | null>(null)
const dialogRef = ref<HTMLElement | null>(null)
let requestToken = 0
let searchTimer: ReturnType<typeof setTimeout> | null = null
let returnFocus: HTMLElement | null = null

const filters = computed(() => [
  { value: 'all' as const, label: t('articleAi.cardPicker.all') },
  { value: 'style' as const, label: t('articleAi.cardPicker.style') },
  { value: 'character' as const, label: t('articleAi.cardPicker.character') },
  { value: 'scene' as const, label: t('articleAi.cardPicker.scene') },
])
const draftCards = computed(() => draftIds.value.map((id) => knownCards.value.get(id)).filter((item): item is AiCard => Boolean(item)))
const draftChars = computed(() => draftCards.value.reduce((sum, item) => sum + item.content.length, 0))

watch(() => props.open, (open) => {
  if (!open) {
    const target = returnFocus
    returnFocus = null
    void nextTick(() => target?.focus())
    return
  }
  returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
  query.value = ''
  cardFilter.value = 'all'
  error.value = ''
  previewCard.value = null
  draftIds.value = props.selected.map((item) => item.id)
  knownCards.value = new Map(props.selected.map((item) => [item.id, item]))
  scheduleLoad(0)
}, { immediate: true })

watch([query, cardFilter], () => {
  if (props.open) scheduleLoad(220)
})

function scheduleLoad(delay: number) {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => void loadCards(), delay)
}

async function loadCards() {
  const token = ++requestToken
  loading.value = true
  error.value = ''
  try {
    const type = cardFilter.value === 'all' ? undefined : cardFilter.value
    const items = query.value.trim()
      ? await aiCardApi.searchCards(query.value.trim(), type, 300)
      : await aiCardApi.listCards(type)
    if (token !== requestToken || !props.open) return
    const next = new Map(knownCards.value)
    for (const item of items) next.set(item.id, item)
    knownCards.value = next
    results.value = items
  } catch (cause) {
    if (token !== requestToken || !props.open) return
    error.value = errorMessage(cause)
    results.value = []
  } finally {
    if (token === requestToken) loading.value = false
  }
}

function toggle(id: string) {
  draftIds.value = draftIds.value.includes(id) ? draftIds.value.filter((item) => item !== id) : [...draftIds.value, id]
}

function close() {
  previewCard.value = null
  emit('close')
}

function onKeydown(event: KeyboardEvent) {
  if (!props.open) return
  if (event.key === 'Tab') {
    trapFocus(event, dialogRef.value)
    return
  }
  if (event.key !== 'Escape') return
  event.preventDefault()
  event.stopPropagation()
  if (previewCard.value) previewCard.value = null
  else close()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  if (searchTimer) clearTimeout(searchTimer)
})
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/45 p-3 sm:p-6" data-testid="article-ai-card-picker" @click.self="close">
      <section ref="dialogRef" tabindex="-1" role="dialog" aria-modal="true" aria-labelledby="article-ai-card-picker-title" class="flex max-h-[88vh] w-full max-w-[920px] flex-col overflow-hidden rounded-lg bg-white shadow-2xl">
        <header class="shrink-0 border-b border-stone-200 px-4 py-4 sm:px-5">
          <div class="flex items-start justify-between gap-4">
            <div><h2 id="article-ai-card-picker-title" class="text-lg font-semibold text-stone-950">{{ t('articleAi.cardPicker.title') }}</h2><p class="mt-1 text-sm text-stone-600">{{ t('articleAi.contextPicker.summary', { count: draftIds.length, chars: draftChars }) }}</p></div>
            <button type="button" class="h-9 w-9 rounded-md text-xl text-stone-600 hover:bg-stone-100" :aria-label="t('common.close')" @click="close">×</button>
          </div>
          <div v-if="!previewCard" class="mt-4 space-y-3">
            <div class="flex flex-col gap-2 sm:flex-row">
              <label class="relative min-w-0 flex-1"><span class="sr-only">{{ t('articleAi.cardPicker.search') }}</span><input v-model="query" autofocus class="w-full rounded-md border border-stone-300 px-3 py-2.5 pr-20 text-sm outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100" :placeholder="t('articleAi.cardPicker.search')" /><button v-if="query" type="button" class="absolute right-2 top-1.5 rounded px-2 py-1 text-sm text-stone-600 hover:bg-stone-100" @click="query = ''">{{ t('articleAi.referencePicker.clearSearch') }}</button></label>
              <button type="button" class="rounded-md border border-stone-300 px-3 py-2 text-sm font-medium text-stone-700 hover:bg-stone-50" @click="draftIds = []">{{ t('articleAi.referencePicker.clearSelection') }}</button>
            </div>
            <div class="flex flex-wrap gap-1 rounded-md bg-stone-100 p-1">
              <button v-for="filter in filters" :key="filter.value" type="button" :class="['rounded px-3 py-1.5 text-sm font-medium', cardFilter === filter.value ? 'bg-white text-stone-950 shadow-sm' : 'text-stone-600 hover:text-stone-900']" @click="cardFilter = filter.value">{{ filter.label }}</button>
            </div>
          </div>
        </header>

        <div class="min-h-0 flex-1 overflow-y-auto p-4 sm:p-5">
          <template v-if="previewCard">
            <button type="button" class="mb-4 text-sm font-medium text-stone-700 underline" @click="previewCard = null">{{ t('articleAi.referencePicker.backToList') }}</button>
            <article class="mx-auto max-w-3xl"><div class="border-b border-stone-200 pb-4"><h3 class="text-xl font-semibold text-stone-950">{{ previewCard.title }}</h3><p class="mt-1 text-sm text-stone-600">{{ t(`articleAi.cardPicker.${previewCard.card_type}`) }}</p></div><div v-if="previewCard.tags.length" class="mt-4 flex flex-wrap gap-2"><span v-for="tag in previewCard.tags" :key="tag" class="rounded bg-stone-100 px-2 py-1 text-sm text-stone-700">{{ tag }}</span></div><div class="mt-5 whitespace-pre-wrap text-[15px] leading-7 text-stone-800">{{ previewCard.content }}</div></article>
          </template>
          <div v-else-if="loading" class="py-16 text-center text-sm text-stone-600">{{ t('common.loading') }}</div>
          <div v-else-if="error" class="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800"><p>{{ error }}</p><button type="button" class="mt-3 font-medium underline" @click="loadCards">{{ t('common.refresh') }}</button></div>
          <div v-else-if="!results.length" class="py-14 text-center"><p class="text-sm text-stone-600">{{ query ? t('articleAi.cardPicker.noMatches') : t('articleAi.cardPicker.empty') }}</p><button v-if="!query" type="button" class="mt-4 rounded-md bg-stone-900 px-4 py-2 text-sm font-semibold text-white" @click="emit('openCards')">{{ t('articleAi.cardPicker.openCards') }}</button></div>
          <div v-else class="grid gap-3 md:grid-cols-2">
            <article v-for="card in results" :key="card.id" :class="['relative flex min-h-[210px] flex-col rounded-md border p-4 transition', draftIds.includes(card.id) ? 'border-emerald-500 bg-emerald-50/70 shadow-sm' : 'border-stone-200 bg-white hover:border-emerald-300']">
              <button type="button" class="absolute inset-0 z-0 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2" :aria-pressed="draftIds.includes(card.id)" :aria-label="card.title" @click="toggle(card.id)" />
              <div class="pointer-events-none relative z-10 flex items-start justify-between gap-3"><div class="min-w-0"><h3 class="truncate text-[15px] font-semibold text-stone-950">{{ card.title }}</h3><p class="mt-1 text-sm text-stone-600">{{ t(`articleAi.cardPicker.${card.card_type}`) }}</p></div><span :class="['flex h-6 w-6 shrink-0 items-center justify-center rounded border text-sm font-bold', draftIds.includes(card.id) ? 'border-emerald-600 bg-emerald-600 text-white' : 'border-stone-300 bg-white text-transparent']">✓</span></div>
              <div class="pointer-events-none relative z-10 mt-3 flex flex-wrap gap-1.5"><span v-for="tag in card.tags.slice(0, 5)" :key="tag" class="rounded bg-stone-100 px-2 py-1 text-sm text-stone-700">{{ tag }}</span></div>
              <p class="pointer-events-none relative z-10 mt-3 line-clamp-4 flex-1 whitespace-pre-wrap text-sm leading-6 text-stone-700">{{ card.content }}</p>
              <div class="pointer-events-none relative z-10 mt-3 flex items-center justify-between border-t border-stone-200 pt-3"><span class="text-sm text-stone-500">{{ card.content.length }} {{ t('articleAi.characters') }}</span><button type="button" class="pointer-events-auto relative z-20 text-sm font-medium text-stone-700 underline" @click="previewCard = card">{{ t('articleAi.referencePicker.preview') }}</button></div>
            </article>
          </div>
        </div>

        <footer class="shrink-0 border-t border-stone-200 bg-stone-50 px-4 py-3 sm:px-5"><div class="flex flex-wrap items-center justify-between gap-3"><span class="text-sm text-stone-700">{{ t('articleAi.contextPicker.summary', { count: draftIds.length, chars: draftChars }) }}</span><div class="flex gap-2"><button type="button" class="rounded-md border border-stone-300 bg-white px-4 py-2 text-sm font-medium" @click="close">{{ t('common.cancel') }}</button><button type="button" class="rounded-md bg-stone-900 px-4 py-2 text-sm font-semibold text-white" @click="emit('confirm', draftCards)">{{ t('articleAi.contextPicker.useSelected', { count: draftIds.length }) }}</button></div></div></footer>
      </section>
    </div>
  </Teleport>
</template>
