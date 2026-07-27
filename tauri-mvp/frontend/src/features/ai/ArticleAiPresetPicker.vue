<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import type { AiTaskPreset } from '../../api/ai'
import { useI18n } from '../../i18n'
import type { FocusTaskType } from './taskControls'
import {
  presetsForTask,
  writingPresetCopy,
  type WritingPresetGenre,
  type WritingPresetTier,
} from './writingPresets'

const props = defineProps<{
  taskType: FocusTaskType
  activePresetId: string
  customPresets: AiTaskPreset[]
}>()

const emit = defineEmits<{
  selectSystem: [presetId: string]
  selectCustom: [presetId: string]
  save: [name: string]
  rename: [payload: { id: string; name: string }]
  delete: [presetId: string]
}>()

const { t, locale } = useI18n()
const tier = ref<WritingPresetTier | 'custom'>('common')
const genre = ref<WritingPresetGenre>('general')
const editorOpen = ref(false)
const editorMode = ref<'save' | 'rename'>('save')
const editorName = ref('')
const editingPresetId = ref('')
const nameInput = ref<HTMLInputElement | null>(null)

const systemPresets = computed(() => presetsForTask(props.taskType)
  .filter((item) => item.tier === tier.value)
  .filter((item) => genre.value === 'general'
    ? item.genres.includes('general')
    : item.genres.includes(genre.value)))

watch(() => props.taskType, () => {
  tier.value = 'common'
  genre.value = 'general'
  closeEditor()
})

function openSave() {
  editorMode.value = 'save'
  editorName.value = ''
  editingPresetId.value = ''
  editorOpen.value = true
  void nextTick(() => nameInput.value?.focus())
}

function openRename(preset: AiTaskPreset) {
  editorMode.value = 'rename'
  editorName.value = preset.name
  editingPresetId.value = preset.id
  editorOpen.value = true
  void nextTick(() => nameInput.value?.focus())
}

function closeEditor() {
  editorOpen.value = false
  editorName.value = ''
  editingPresetId.value = ''
}

function submitEditor() {
  const name = editorName.value.trim()
  if (!name) return
  if (editorMode.value === 'rename' && editingPresetId.value) {
    emit('rename', { id: editingPresetId.value, name })
  } else {
    emit('save', name)
  }
  closeEditor()
}

function confirmDelete(preset: AiTaskPreset) {
  if (!window.confirm(t('articleAi.presets.deleteConfirm', { name: preset.name }))) return
  emit('delete', preset.id)
}
</script>

<template>
  <section data-testid="article-ai-preset-panel" data-tour="ai-presets" class="border-y border-stone-200 py-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-sm font-semibold text-stone-900">{{ t('articleAi.presets.title') }}</h2>
        <p class="mt-1 text-sm text-stone-600">{{ t('articleAi.presets.subtitle') }}</p>
      </div>
      <button
        type="button"
        class="rounded-md border border-stone-300 bg-white px-3 py-2 text-sm font-medium text-stone-700 hover:bg-stone-50"
        @click="openSave"
      >
        {{ t('articleAi.presets.saveCurrent') }}
      </button>
    </div>

    <div class="mt-4 flex flex-wrap items-center justify-between gap-3">
      <div class="inline-flex rounded-md bg-stone-100 p-1" role="tablist" :aria-label="t('articleAi.presets.category')">
        <button
          v-for="value in (['common', 'creative', 'custom'] as const)"
          :key="value"
          type="button"
          role="tab"
          :aria-selected="tier === value"
          :class="['rounded px-3 py-1.5 text-sm font-medium', tier === value ? 'bg-white text-stone-900 shadow-sm' : 'text-stone-600 hover:text-stone-900']"
          @click="tier = value"
        >
          {{ t(`articleAi.presets.${value}`) }}
        </button>
      </div>
      <div v-if="tier !== 'custom'" class="flex flex-wrap gap-1.5" :aria-label="t('articleAi.presets.genre')">
        <button
          v-for="value in (['general', 'fiction', 'essay', 'nonfiction'] as const)"
          :key="value"
          type="button"
          :class="['rounded-md border px-2.5 py-1.5 text-xs font-medium', genre === value ? 'border-teal-700 bg-teal-50 text-teal-900' : 'border-stone-200 bg-white text-stone-600 hover:border-stone-400']"
          @click="genre = value"
        >
          {{ t(`articleAi.presets.genres.${value}`) }}
        </button>
      </div>
    </div>

    <div v-if="tier !== 'custom'" class="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
      <button
        v-for="preset in systemPresets"
        :key="preset.id"
        type="button"
        :data-testid="`article-ai-preset-${preset.id}`"
        :class="[
          'min-h-28 border p-3 text-left transition-colors',
          activePresetId === `system:${preset.id}`
            ? 'border-teal-700 bg-teal-50 text-teal-950'
            : 'border-stone-200 bg-white text-stone-800 hover:border-stone-400',
        ]"
        @click="emit('selectSystem', preset.id)"
      >
        <span class="flex items-start justify-between gap-2">
          <span class="text-sm font-semibold">{{ writingPresetCopy(preset.name, locale) }}</span>
          <span v-if="preset.tier === 'creative'" class="shrink-0 rounded bg-amber-100 px-1.5 py-0.5 text-[11px] font-medium text-amber-900">{{ t('articleAi.presets.highImpact') }}</span>
        </span>
        <span class="mt-2 block text-sm leading-5 text-stone-600">{{ writingPresetCopy(preset.description, locale) }}</span>
        <span v-if="preset.risk" class="mt-2 block text-xs leading-5 text-amber-800">{{ writingPresetCopy(preset.risk, locale) }}</span>
      </button>
    </div>
    <div v-else class="mt-4">
      <div v-if="customPresets.length" class="divide-y divide-stone-200 border-y border-stone-200">
        <div v-for="preset in customPresets" :key="preset.id" class="flex items-center gap-3 py-3">
          <button
            type="button"
            :class="['min-w-0 flex-1 text-left text-sm font-medium', activePresetId === `custom:${preset.id}` ? 'text-teal-800' : 'text-stone-800 hover:text-stone-950']"
            @click="emit('selectCustom', preset.id)"
          >
            {{ preset.name }}
          </button>
          <button type="button" class="rounded-md px-2 py-1 text-xs text-stone-600 hover:bg-stone-100" @click="openRename(preset)">{{ t('common.edit') }}</button>
          <button type="button" class="rounded-md px-2 py-1 text-xs text-red-700 hover:bg-red-50" @click="confirmDelete(preset)">{{ t('common.delete') }}</button>
        </div>
      </div>
      <p v-else class="border-y border-stone-200 py-6 text-center text-sm text-stone-500">{{ t('articleAi.presets.customEmpty') }}</p>
    </div>

    <div v-if="editorOpen" class="mt-4 flex flex-wrap items-end gap-2 border-t border-stone-200 pt-4">
      <label class="min-w-56 flex-1 text-sm text-stone-700">
        {{ editorMode === 'rename' ? t('articleAi.presets.rename') : t('articleAi.presets.name') }}
        <input
          ref="nameInput"
          v-model="editorName"
          maxlength="80"
          class="mt-1 w-full rounded-md border border-stone-300 px-3 py-2"
          @keydown.enter.prevent="submitEditor"
          @keydown.escape.prevent="closeEditor"
        />
      </label>
      <button type="button" class="rounded-md border border-stone-300 px-3 py-2 text-sm text-stone-700" @click="closeEditor">{{ t('common.cancel') }}</button>
      <button type="button" :disabled="!editorName.trim()" class="rounded-md bg-stone-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40" @click="submitEditor">{{ t('common.save') }}</button>
    </div>
  </section>
</template>
