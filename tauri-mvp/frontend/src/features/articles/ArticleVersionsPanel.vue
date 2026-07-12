<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { articlesApi, type Entry, type EntryVersion } from '../../api/articles'
import { errorMessage, isHttpStatus } from '../../api/base'
import { useI18n } from '../../i18n'
import { buildParagraphDiff, type ParagraphDiffRow } from './versionDiff'

const props = defineProps<{
  entry: Entry
}>()

const emit = defineEmits<{
  restored: [entry: Entry]
  cloned: [entry: Entry]
}>()

const { t } = useI18n()
const expanded = ref(false)
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')
const versions = ref<EntryVersion[]>([])
const selectedVersion = ref<EntryVersion | null>(null)

const diffRows = computed<ParagraphDiffRow[]>(() =>
  selectedVersion.value
    ? buildParagraphDiff(props.entry.body || '', selectedVersion.value.content || '')
    : []
)

watch(
  () => props.entry.id,
  () => {
    selectedVersion.value = null
    void loadVersions()
  }
)

onMounted(() => {
  void loadVersions()
})

function formatDate(value: string | null): string {
  if (!value) return ''
  return new Date(value).toLocaleString()
}

function versionTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    manual_checkpoint: t('articleVersions.typeManual'),
    manual_snapshot: t('articleVersions.typePreRestore'),
    ai_before_apply: t('articleVersions.typeAiBefore'),
    original: t('articleVersions.typeOriginal'),
    ai_polish: t('articleVersions.typeAiPolish'),
    ai_expand: t('articleVersions.typeAiExpand'),
    ai_continue: t('articleVersions.typeAiContinue'),
    ai_other: t('articleVersions.typeAiOther'),
  }
  return labels[type] ?? type
}

function compactPreview(text: string): string {
  return text.replace(/\s+/g, ' ').trim().slice(0, 76) || t('articleVersions.emptyBody')
}

async function loadVersions() {
  loading.value = true
  error.value = ''
  try {
    versions.value = await articlesApi.listVersions(props.entry.id)
  } catch (e) {
    error.value = isHttpStatus(e, 404)
      ? t('articleVersions.unsupported')
      : errorMessage(e)
  } finally {
    loading.value = false
  }
}

async function saveManualVersion() {
  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    await articlesApi.createVersion(props.entry.id, {
      version_type: 'manual_checkpoint',
      label: t('articleVersions.manualLabel'),
    })
    notice.value = t('articleVersions.saved')
    await loadVersions()
  } catch (e) {
    error.value = isHttpStatus(e, 404)
      ? t('articleVersions.unsupported')
      : errorMessage(e)
  } finally {
    saving.value = false
  }
}

async function restoreSelectedVersion() {
  const version = selectedVersion.value
  if (!version) return
  if (!confirm(t('articleVersions.restoreConfirm'))) return
  error.value = ''
  notice.value = ''
  try {
    const result = await articlesApi.restoreVersion(props.entry.id, version.id)
    emit('restored', result.entry)
    notice.value = result.was_noop ? t('articleVersions.restoreNoop') : t('articleVersions.restored')
    selectedVersion.value = null
    await loadVersions()
  } catch (e) {
    error.value = isHttpStatus(e, 404)
      ? t('articleVersions.versionMissing')
      : errorMessage(e)
  }
}

async function cloneSelectedVersion() {
  const version = selectedVersion.value
  if (!version) return
  error.value = ''
  notice.value = ''
  try {
    const entry = await articlesApi.cloneVersion(props.entry.id, version.id)
    emit('cloned', entry)
    notice.value = t('articleVersions.cloned')
    selectedVersion.value = null
  } catch (e) {
    error.value = isHttpStatus(e, 404)
      ? t('articleVersions.versionMissing')
      : errorMessage(e)
  }
}

async function deleteVersion(version: EntryVersion) {
  if (!confirm(t('articleVersions.deleteConfirm'))) return
  error.value = ''
  notice.value = ''
  try {
    await articlesApi.deleteVersion(props.entry.id, version.id)
    if (selectedVersion.value?.id === version.id) selectedVersion.value = null
    await loadVersions()
  } catch (e) {
    error.value = isHttpStatus(e, 404)
      ? t('articleVersions.versionMissing')
      : errorMessage(e)
  }
}

async function copySelectedVersion() {
  const version = selectedVersion.value
  if (!version) return
  await navigator.clipboard.writeText(version.content)
  notice.value = t('articleVersions.copied')
}
</script>

<template>
  <section data-testid="article-version-history">
    <button
      type="button"
      class="mb-2 flex w-full items-center justify-between gap-2 rounded-xl px-2 py-1 text-left hover:bg-stone-50"
      @click="expanded = !expanded"
    >
      <span class="text-sm font-semibold text-stone-700">
        {{ expanded ? '⌄' : '›' }} {{ t('articleVersions.title') }}
      </span>
      <span class="rounded-full bg-indigo-50 px-2 py-1 text-xs font-semibold text-indigo-700">
        {{ versions.length }}
      </span>
    </button>

    <div v-show="expanded" class="space-y-3">
      <div class="flex gap-2">
        <button
          type="button"
          class="flex-1 rounded-xl bg-stone-900 px-3 py-2 text-xs font-semibold text-white hover:bg-stone-700 disabled:opacity-40"
          :disabled="saving"
          @click="saveManualVersion"
        >
          {{ saving ? t('common.saving') : t('articleVersions.saveCurrent') }}
        </button>
        <button
          type="button"
          class="rounded-xl bg-stone-100 px-3 py-2 text-xs text-stone-600 hover:bg-stone-200"
          :disabled="loading"
          @click="loadVersions"
        >
          {{ t('common.refresh') }}
        </button>
      </div>

      <p class="text-xs leading-5 text-stone-500">{{ t('articleVersions.hint') }}</p>
      <div v-if="notice" class="rounded-lg bg-emerald-50 p-2 text-xs text-emerald-700">{{ notice }}</div>
      <div v-if="error" class="rounded-lg bg-red-50 p-2 text-xs text-red-700">{{ error }}</div>
      <div v-if="loading" class="rounded-xl bg-stone-50 p-3 text-sm text-stone-400">
        {{ t('common.loading') }}
      </div>
      <div v-else-if="!versions.length" class="rounded-xl bg-stone-50 p-3 text-sm text-stone-400">
        {{ t('articleVersions.empty') }}
      </div>
      <div v-else class="space-y-2">
        <article
          v-for="version in versions"
          :key="version.id"
          class="rounded-2xl border border-stone-200 bg-white p-3 shadow-sm"
        >
          <button type="button" class="w-full text-left" @click="selectedVersion = version">
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <div class="text-sm font-semibold text-stone-800">
                  {{ version.label || versionTypeLabel(version.version_type) }}
                </div>
                <div class="mt-1 text-[11px] text-stone-400">
                  {{ versionTypeLabel(version.version_type) }} · {{ formatDate(version.created_at) }}
                </div>
              </div>
              <span class="shrink-0 rounded-full bg-stone-100 px-2 py-1 text-[11px] text-stone-500">
                {{ version.word_count }}
              </span>
            </div>
            <p class="mt-2 text-xs leading-5 text-stone-500">{{ compactPreview(version.content) }}</p>
          </button>
          <div class="mt-3 flex justify-end gap-2">
            <button class="rounded-lg bg-stone-100 px-2.5 py-1 text-xs text-stone-600" @click="selectedVersion = version">
              {{ t('articleVersions.compare') }}
            </button>
            <button class="rounded-lg bg-red-50 px-2.5 py-1 text-xs text-red-600" @click="deleteVersion(version)">
              {{ t('common.delete') }}
            </button>
          </div>
        </article>
      </div>
    </div>

    <div v-if="selectedVersion" class="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-5">
      <div class="flex max-h-[88vh] w-[1120px] max-w-full flex-col overflow-hidden rounded-3xl bg-white shadow-2xl">
        <div class="border-b border-stone-200 px-6 py-5">
          <div class="flex items-start justify-between gap-4">
            <div>
              <h3 class="text-xl font-semibold text-stone-900">{{ t('articleVersions.compareTitle') }}</h3>
              <p class="mt-1 text-sm text-stone-500">
                {{ selectedVersion.label || versionTypeLabel(selectedVersion.version_type) }} · {{ formatDate(selectedVersion.created_at) }}
              </p>
            </div>
            <button class="rounded-xl bg-stone-100 px-3 py-2 text-sm text-stone-600" @click="selectedVersion = null">
              {{ t('common.close') }}
            </button>
          </div>
        </div>
        <div class="grid min-h-0 flex-1 grid-cols-2 gap-0 overflow-y-auto bg-stone-50">
          <div class="border-r border-stone-200 p-5">
            <h4 class="mb-3 text-sm font-semibold text-stone-600">{{ t('articleVersions.currentDraft') }}</h4>
            <div class="space-y-3">
              <p
                v-for="(row, index) in diffRows"
                :key="`current-${index}`"
                :class="[
                  'min-h-[42px] whitespace-pre-wrap rounded-xl border px-3 py-2 text-sm leading-6',
                  row.kind === 'equal' ? 'border-transparent bg-white text-stone-700' : '',
                  row.kind === 'changed' ? 'border-amber-200 bg-amber-50 text-stone-900' : '',
                  row.kind === 'added' ? 'border-emerald-200 bg-emerald-50 text-stone-900' : '',
                  row.kind === 'removed' ? 'border-transparent bg-transparent text-stone-300' : '',
                ]"
              >{{ row.current || ' ' }}</p>
            </div>
          </div>
          <div class="p-5">
            <h4 class="mb-3 text-sm font-semibold text-stone-600">{{ t('articleVersions.historicalDraft') }}</h4>
            <div class="space-y-3">
              <p
                v-for="(row, index) in diffRows"
                :key="`historical-${index}`"
                :class="[
                  'min-h-[42px] whitespace-pre-wrap rounded-xl border px-3 py-2 text-sm leading-6',
                  row.kind === 'equal' ? 'border-transparent bg-white text-stone-700' : '',
                  row.kind === 'changed' ? 'border-sky-200 bg-sky-50 text-stone-900' : '',
                  row.kind === 'removed' ? 'border-red-200 bg-red-50 text-stone-900' : '',
                  row.kind === 'added' ? 'border-transparent bg-transparent text-stone-300' : '',
                ]"
              >{{ row.historical || ' ' }}</p>
            </div>
          </div>
        </div>
        <div class="flex flex-wrap items-center justify-between gap-3 border-t border-stone-200 bg-white px-6 py-4">
          <div class="flex flex-wrap gap-2 text-xs text-stone-500">
            <span class="rounded-full bg-emerald-50 px-2 py-1 text-emerald-700">{{ t('articleVersions.legendAdded') }}</span>
            <span class="rounded-full bg-amber-50 px-2 py-1 text-amber-700">{{ t('articleVersions.legendChanged') }}</span>
            <span class="rounded-full bg-red-50 px-2 py-1 text-red-700">{{ t('articleVersions.legendRemoved') }}</span>
          </div>
          <div class="flex flex-wrap justify-end gap-2">
            <button class="rounded-xl bg-stone-100 px-4 py-2 text-sm text-stone-700" @click="copySelectedVersion">
              {{ t('articleVersions.copyVersion') }}
            </button>
            <button class="rounded-xl bg-white px-4 py-2 text-sm text-stone-700 ring-1 ring-stone-200" @click="cloneSelectedVersion">
              {{ t('articleVersions.cloneVersion') }}
            </button>
            <button class="rounded-xl bg-stone-900 px-4 py-2 text-sm font-semibold text-white" @click="restoreSelectedVersion">
              {{ t('articleVersions.restoreVersion') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
