<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from '../i18n'

const props = defineProps<{
  show: boolean
  text: string
}>()

const emit = defineEmits<{
  close: []
  replace: [findText: string, replaceText: string, replaceAll: boolean]
  navigate: [direction: 'prev' | 'next', query: string, caseSensitive: boolean]
  queryChange: [query: string, caseSensitive: boolean]
}>()

const { t } = useI18n()

const findText = ref('')
const replaceText = ref('')
const caseSensitive = ref(false)
const showReplace = ref(false)
const currentIndex = ref(0)

const matches = computed(() => {
  if (!findText.value || !props.text) return []
  const pattern = findText.value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const flags = caseSensitive.value ? 'g' : 'gi'
  const regex = new RegExp(pattern, flags)
  const results: number[] = []
  let match: RegExpExecArray | null
  while ((match = regex.exec(props.text)) !== null) {
    results.push(match.index)
    if (match.index === regex.lastIndex) {
      regex.lastIndex += 1
    }
  }
  return results
})

const counter = computed(() =>
  matches.value.length ? t('findReplace.counter', { current: currentIndex.value + 1, total: matches.value.length }) : t('findReplace.noMatches')
)

function go(direction: 'prev' | 'next') {
  if (!findText.value.trim()) return
  emit('navigate', direction, findText.value, caseSensitive.value)
}

function handleReplace() {
  if (!findText.value.trim()) return
  emit('replace', findText.value, replaceText.value, false)
}

function handleReplaceAll() {
  if (!findText.value.trim()) return
  emit('replace', findText.value, replaceText.value, true)
}

function handleClose() {
  findText.value = ''
  replaceText.value = ''
  caseSensitive.value = false
  showReplace.value = false
  currentIndex.value = 0
  emit('close')
}

watch(
  () => [findText.value, props.text, caseSensitive.value],
  () => {
    currentIndex.value = 0
    emit('queryChange', findText.value, caseSensitive.value)
  }
)
</script>

<template>
  <div
    v-if="show"
    class="absolute top-0 right-0 z-10 m-4 w-96 rounded-2xl border border-stone-200 bg-white p-4 shadow-lg"
  >
    <div class="mb-3 flex items-center justify-between gap-3">
      <h3 class="text-sm font-semibold text-stone-900">
        {{ showReplace ? t('findReplace.titleWithReplace') : t('findReplace.title') }}
      </h3>
      <div class="flex items-center gap-2">
        <button
          @click="showReplace = !showReplace"
          class="text-xs text-amber-700 hover:text-amber-900"
        >
          {{ showReplace ? t('findReplace.hideReplace') : t('findReplace.showReplace') }}
        </button>
        <button @click="handleClose" class="text-stone-400 hover:text-stone-600">
          {{ t('findReplace.close') }}
        </button>
      </div>
    </div>

    <div class="space-y-3">
      <div class="flex items-center gap-2">
        <input
          v-model="findText"
          @keydown.enter.prevent="go('next')"
          @keydown.esc.prevent="handleClose"
          :placeholder="t('findReplace.findPlaceholder')"
          class="flex-1 rounded-lg border border-stone-300 px-3 py-2 text-sm outline-none focus:border-amber-400"
          autofocus
        />
        <span class="whitespace-nowrap text-xs text-stone-500">{{ counter }}</span>
      </div>

      <div v-if="showReplace" class="flex items-center gap-2">
        <input
          v-model="replaceText"
          @keydown.enter.prevent="handleReplace"
          @keydown.esc.prevent="handleClose"
          :placeholder="t('findReplace.replacePlaceholder')"
          class="flex-1 rounded-lg border border-stone-300 px-3 py-2 text-sm outline-none focus:border-amber-400"
        />
      </div>

      <div class="flex items-center justify-between gap-3">
        <label class="flex items-center gap-2 text-xs text-stone-600">
          <input v-model="caseSensitive" type="checkbox" class="rounded border-stone-300" />
          {{ t('findReplace.caseSensitive') }}
        </label>
        <div class="flex items-center gap-2">
          <button
            @click="go('prev')"
            :disabled="!matches.length"
            class="rounded-lg bg-stone-100 px-3 py-1.5 text-sm text-stone-700 transition-colors hover:bg-stone-200 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {{ t('findReplace.previousMatch') }}
          </button>
          <button
            @click="go('next')"
            :disabled="!matches.length"
            class="rounded-lg bg-stone-100 px-3 py-1.5 text-sm text-stone-700 transition-colors hover:bg-stone-200 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {{ t('findReplace.nextMatch') }}
          </button>
          <button
            v-if="showReplace"
            @click="handleReplace"
            :disabled="!matches.length"
            class="rounded-lg bg-stone-900 px-3 py-1.5 text-sm text-white transition-colors hover:bg-stone-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {{ t('findReplace.replace') }}
          </button>
          <button
            v-if="showReplace"
            @click="handleReplaceAll"
            :disabled="!matches.length"
            class="rounded-lg bg-amber-600 px-3 py-1.5 text-sm text-white transition-colors hover:bg-amber-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {{ t('findReplace.replaceAll') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
