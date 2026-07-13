<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { WritingNote } from '../../api/notes'
import { useI18n } from '../../i18n'
import { trapFocus } from '../../utils/focusTrap'

const props = defineProps<{ open: boolean; notes: WritingNote[]; selected: WritingNote[]; loading?: boolean; articleTitle?: string }>()
const emit = defineEmits<{ close: []; confirm: [notes: WritingNote[]]; openArticle: [] }>()
const { t } = useI18n()
type StatusFilter = 'all' | 'open' | 'done'
const query = ref('')
const statusFilter = ref<StatusFilter>('all')
const draftIds = ref<string[]>([])
const previewNote = ref<WritingNote | null>(null)
const dialogRef = ref<HTMLElement | null>(null)
let returnFocus: HTMLElement | null = null

const filters = computed(() => [
  { value: 'all' as const, label: t('articleAi.notePicker.all') },
  { value: 'open' as const, label: t('articleAi.notePicker.open') },
  { value: 'done' as const, label: t('articleAi.notePicker.done') },
])
const sortedNotes = computed(() => [...props.notes].sort((a, b) => Number(b.pinned) - Number(a.pinned) || a.sort_order - b.sort_order))
const results = computed(() => sortedNotes.value.filter((note) => {
  if (statusFilter.value !== 'all' && note.status !== statusFilter.value) return false
  return !query.value.trim() || note.body.toLocaleLowerCase().includes(query.value.trim().toLocaleLowerCase())
}))
const draftNotes = computed(() => draftIds.value.map((id) => props.notes.find((note) => note.id === id)).filter((item): item is WritingNote => Boolean(item)))
const draftChars = computed(() => draftNotes.value.reduce((sum, item) => sum + item.body.length, 0))

watch(() => props.open, (open) => {
  if (!open) {
    const target = returnFocus
    returnFocus = null
    void nextTick(() => target?.focus())
    return
  }
  returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
  query.value = ''
  statusFilter.value = 'all'
  previewNote.value = null
  draftIds.value = props.selected.map((item) => item.id)
}, { immediate: true })

function toggle(id: string) {
  draftIds.value = draftIds.value.includes(id) ? draftIds.value.filter((item) => item !== id) : [...draftIds.value, id]
}
function close() { previewNote.value = null; emit('close') }
function noteTitle(note: WritingNote) { return note.body.trim().split(/\r?\n/)[0]?.slice(0, 48) || t('articleAi.notePicker.untitled') }
function onKeydown(event: KeyboardEvent) {
  if (!props.open) return
  if (event.key === 'Tab') {
    trapFocus(event, dialogRef.value)
    return
  }
  if (event.key !== 'Escape') return
  event.preventDefault(); event.stopPropagation()
  if (previewNote.value) previewNote.value = null
  else close()
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/45 p-3 sm:p-6" data-testid="article-ai-note-picker" @click.self="close">
      <section ref="dialogRef" tabindex="-1" role="dialog" aria-modal="true" aria-labelledby="article-ai-note-picker-title" class="flex max-h-[88vh] w-full max-w-[920px] flex-col overflow-hidden rounded-lg bg-white shadow-2xl">
        <header class="shrink-0 border-b border-stone-200 px-4 py-4 sm:px-5">
          <div class="flex items-start justify-between gap-4"><div><h2 id="article-ai-note-picker-title" class="text-lg font-semibold text-stone-950">{{ t('articleAi.notePicker.title') }}</h2><p class="mt-1 text-sm text-stone-600">{{ articleTitle }} · {{ t('articleAi.contextPicker.summary', { count: draftIds.length, chars: draftChars }) }}</p></div><button type="button" class="h-9 w-9 rounded-md text-xl text-stone-600 hover:bg-stone-100" :aria-label="t('common.close')" @click="close">×</button></div>
          <div v-if="!previewNote" class="mt-4 space-y-3"><div class="flex flex-col gap-2 sm:flex-row"><label class="relative min-w-0 flex-1"><span class="sr-only">{{ t('articleAi.notePicker.search') }}</span><input v-model="query" autofocus class="w-full rounded-md border border-stone-300 px-3 py-2.5 pr-20 text-sm outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100" :placeholder="t('articleAi.notePicker.search')" /><button v-if="query" type="button" class="absolute right-2 top-1.5 rounded px-2 py-1 text-sm text-stone-600 hover:bg-stone-100" @click="query = ''">{{ t('articleAi.referencePicker.clearSearch') }}</button></label><button type="button" class="rounded-md border border-stone-300 px-3 py-2 text-sm font-medium" @click="draftIds = []">{{ t('articleAi.referencePicker.clearSelection') }}</button></div><div class="flex flex-wrap gap-1 rounded-md bg-stone-100 p-1"><button v-for="filter in filters" :key="filter.value" type="button" :class="['rounded px-3 py-1.5 text-sm font-medium', statusFilter === filter.value ? 'bg-white text-stone-950 shadow-sm' : 'text-stone-600']" @click="statusFilter = filter.value">{{ filter.label }}</button></div></div>
        </header>
        <div class="min-h-0 flex-1 overflow-y-auto p-4 sm:p-5">
          <template v-if="previewNote"><button type="button" class="mb-4 text-sm font-medium text-stone-700 underline" @click="previewNote = null">{{ t('articleAi.referencePicker.backToList') }}</button><article class="mx-auto max-w-3xl"><div class="border-b border-stone-200 pb-4"><h3 class="text-xl font-semibold text-stone-950">{{ noteTitle(previewNote) }}</h3><p class="mt-1 text-sm text-stone-600">{{ t(`articleAi.notePicker.${previewNote.status}`) }}<span v-if="previewNote.pinned"> · {{ t('articleAi.notePicker.pinned') }}</span></p></div><div class="mt-5 whitespace-pre-wrap text-[15px] leading-7 text-stone-800">{{ previewNote.body }}</div></article></template>
          <div v-else-if="loading" class="py-16 text-center text-sm text-stone-600">{{ t('common.loading') }}</div>
          <div v-else-if="!results.length" class="py-14 text-center"><p class="text-sm text-stone-600">{{ query ? t('articleAi.notePicker.noMatches') : t('articleAi.notePicker.empty') }}</p><button v-if="!query" type="button" class="mt-4 rounded-md bg-stone-900 px-4 py-2 text-sm font-semibold text-white" @click="emit('openArticle')">{{ t('articleAi.notePicker.openArticle') }}</button></div>
          <div v-else class="grid gap-3 md:grid-cols-2">
            <article v-for="note in results" :key="note.id" :class="['relative flex min-h-[190px] flex-col rounded-md border p-4 transition', draftIds.includes(note.id) ? 'border-emerald-500 bg-emerald-50/70 shadow-sm' : 'border-stone-200 bg-white hover:border-emerald-300']"><button type="button" class="absolute inset-0 z-0 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2" :aria-pressed="draftIds.includes(note.id)" :aria-label="noteTitle(note)" @click="toggle(note.id)" /><div class="pointer-events-none relative z-10 flex items-start justify-between gap-3"><div class="min-w-0"><h3 class="truncate text-[15px] font-semibold text-stone-950">{{ noteTitle(note) }}</h3><p class="mt-1 text-sm text-stone-600">{{ t(`articleAi.notePicker.${note.status}`) }}<span v-if="note.pinned"> · {{ t('articleAi.notePicker.pinned') }}</span></p></div><span :class="['flex h-6 w-6 shrink-0 items-center justify-center rounded border text-sm font-bold', draftIds.includes(note.id) ? 'border-emerald-600 bg-emerald-600 text-white' : 'border-stone-300 bg-white text-transparent']">✓</span></div><p class="pointer-events-none relative z-10 mt-3 line-clamp-4 flex-1 whitespace-pre-wrap text-sm leading-6 text-stone-700">{{ note.body }}</p><div class="pointer-events-none relative z-10 mt-3 flex items-center justify-between border-t border-stone-200 pt-3"><span class="text-sm text-stone-500">{{ note.body.length }} {{ t('articleAi.characters') }}</span><button type="button" class="pointer-events-auto relative z-20 text-sm font-medium text-stone-700 underline" @click="previewNote = note">{{ t('articleAi.referencePicker.preview') }}</button></div></article>
          </div>
        </div>
        <footer class="shrink-0 border-t border-stone-200 bg-stone-50 px-4 py-3 sm:px-5"><div class="flex flex-wrap items-center justify-between gap-3"><span class="text-sm text-stone-700">{{ t('articleAi.contextPicker.summary', { count: draftIds.length, chars: draftChars }) }}</span><div class="flex gap-2"><button type="button" class="rounded-md border border-stone-300 bg-white px-4 py-2 text-sm font-medium" @click="close">{{ t('common.cancel') }}</button><button type="button" class="rounded-md bg-stone-900 px-4 py-2 text-sm font-semibold text-white" @click="emit('confirm', draftNotes)">{{ t('articleAi.contextPicker.useSelected', { count: draftIds.length }) }}</button></div></div></footer>
      </section>
    </div>
  </Teleport>
</template>
