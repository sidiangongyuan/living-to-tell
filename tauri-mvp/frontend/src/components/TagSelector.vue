<script setup lang="ts">
import { computed, ref } from 'vue'

const props = withDefaults(defineProps<{
  modelValue: string[]
  suggestions?: string[]
  placeholder?: string
  emptyHint?: string
  createLabel?: string
}>(), {
  suggestions: () => [],
  placeholder: '',
  emptyHint: '',
  createLabel: '添加 “{tag}”',
})

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
  change: [value: string[]]
}>()

const draft = ref('')
const focused = ref(false)

const selectedTags = computed(() => props.modelValue ?? [])

const filteredSuggestions = computed(() => {
  const query = draft.value.trim().toLowerCase()
  const selected = new Set(selectedTags.value.map((tag) => tag.toLowerCase()))
  return props.suggestions
    .map((tag) => tag.trim())
    .filter(Boolean)
    .filter((tag, index, all) => all.findIndex((item) => item.toLowerCase() === tag.toLowerCase()) === index)
    .filter((tag) => !selected.has(tag.toLowerCase()))
    .filter((tag) => !query || tag.toLowerCase().includes(query))
    .slice(0, 8)
})

const showSuggestions = computed(() => focused.value && filteredSuggestions.value.length > 0)

const canCreateDraftTag = computed(() => {
  const tag = draft.value.trim()
  return Boolean(tag) && !selectedTags.value.some((item) => item.toLowerCase() === tag.toLowerCase())
})

const createDraftLabel = computed(() => props.createLabel.replace('{tag}', draft.value.trim()))

function commit(value: string) {
  const tag = value.trim()
  if (!tag) return
  const exists = selectedTags.value.some((item) => item.toLowerCase() === tag.toLowerCase())
  if (exists) {
    draft.value = ''
    return
  }
  update([...selectedTags.value, tag])
  draft.value = ''
}

function commitDraft() {
  commit(draft.value)
}

function remove(tag: string) {
  update(selectedTags.value.filter((item) => item !== tag))
}

function update(value: string[]) {
  emit('update:modelValue', value)
  emit('change', value)
}

function handleBackspace() {
  if (draft.value || !selectedTags.value.length) return
  update(selectedTags.value.slice(0, -1))
}

function handleBlur() {
  commitDraft()
  window.setTimeout(() => {
    focused.value = false
  }, 120)
}

function handleDraftInput() {
  const value = draft.value
  if (!/[，,、]/.test(value)) return
  const parts = value.split(/[，,、]+/)
  for (const part of parts.slice(0, -1)) {
    commit(part)
  }
  draft.value = parts.length ? parts[parts.length - 1] : ''
}
</script>

<template>
  <div class="relative">
    <div class="flex min-h-[42px] flex-wrap items-center gap-2 rounded-lg border border-stone-300 bg-white px-2 py-2 focus-within:ring-2 focus-within:ring-amber-400">
      <button
        v-for="tag in selectedTags"
        :key="tag"
        type="button"
        class="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-1 text-xs font-medium text-amber-800"
        @click="remove(tag)"
      >
        <span>{{ tag }}</span>
        <span aria-hidden="true" class="text-amber-500">×</span>
      </button>
      <input
        v-model="draft"
        type="text"
        class="min-w-[120px] flex-1 border-none bg-transparent px-1 py-1 text-sm outline-none"
        :placeholder="selectedTags.length ? '' : placeholder"
        @input="handleDraftInput"
        @focus="focused = true"
        @blur="handleBlur"
        @keydown.enter.prevent="commit(draft)"
        @keydown.backspace="handleBackspace"
      />
    </div>
    <div
      v-if="showSuggestions || (focused && canCreateDraftTag)"
      class="absolute left-0 right-0 z-20 mt-1 max-h-56 overflow-y-auto rounded-xl border border-stone-200 bg-white p-1 shadow-lg"
    >
      <button
        v-if="canCreateDraftTag"
        type="button"
        class="mb-1 block w-full rounded-lg bg-amber-50 px-3 py-2 text-left text-sm font-semibold text-amber-800 hover:bg-amber-100"
        @mousedown.prevent="commitDraft"
      >
        {{ createDraftLabel }}
      </button>
      <button
        v-for="tag in filteredSuggestions"
        :key="tag"
        type="button"
        class="block w-full rounded-lg px-3 py-2 text-left text-sm text-stone-700 hover:bg-amber-50"
        @mousedown.prevent="commit(tag)"
      >
        {{ tag }}
      </button>
    </div>
    <p v-else-if="emptyHint && !selectedTags.length" class="mt-2 text-xs text-stone-400">
      {{ emptyHint }}
    </p>
  </div>
</template>
