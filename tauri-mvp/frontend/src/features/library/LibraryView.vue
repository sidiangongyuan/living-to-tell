<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useLibraryStore } from './store'
import { libraryApi, type LibraryStats } from '../../api/library'
import { type LibraryGroupMode, EMPTY_SOURCE_GROUP_KEY } from './grouping'
import { useI18n } from '../../i18n'

const store = useLibraryStore()
const route = useRoute()
const { t } = useI18n()
const searchInput = ref('')
const saveTimer = ref<number | null>(null)
const stats = ref<LibraryStats | null>(null)
const initialized = ref(false)
const applyingRouteState = ref(false)
const copyNotice = ref('')

onMounted(async () => {
  await Promise.all([store.loadReferences(), loadStats()])
  initialized.value = true
  await applyRouteState()
})

async function loadStats() {
  try {
    stats.value = await libraryApi.getStats()
  } catch (e) {
    console.error('Load stats failed:', e)
  }
}

const currentGroups = computed(() =>
  store.groupMode === 'usage'
    ? store.usageGroups
    : store.sourceGroups
)

const activeGroup = computed(() =>
  store.groupMode === 'usage'
    ? store.activeUsageGroup
    : store.activeSourceGroup
)

const activeGroupLabel = computed(() => {
  const group = activeGroup.value
  if (!group) return ''

  return store.groupMode === 'usage'
    ? usageLabel(group.key)
    : sourceGroupLabel(group.key)
})

let searchTimer: number | null = null
watch(searchInput, (value) => {
  if (searchTimer) window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => {
    void store.search(value)
  }, 300)
})

watch(
  () => [route.query.ref, route.query.group],
  async () => {
    if (!initialized.value || applyingRouteState.value) return
    await applyRouteState()
  }
)

function scheduleSave() {
  if (saveTimer.value) window.clearTimeout(saveTimer.value)
  saveTimer.value = window.setTimeout(() => {
    void saveNow()
  }, 600)
}

async function saveNow() {
  if (store.selectedReference) {
    await store.updateReference(store.selectedReference)
  }
}

function preview(content: string): string {
  return content.trim().slice(0, 140) || t('library.empty')
}

function usageLabel(kind: string): string {
  switch (kind) {
    case 'style':
      return t('library.style')
    case 'imagery':
      return t('library.imagery')
    case 'structure':
      return t('library.structure')
    case 'rhetoric':
      return t('library.rhetoric')
    case 'diction':
      return t('library.diction')
    case 'reflection':
      return t('library.reflection')
    case 'setting':
      return t('library.setting')
    case 'technique':
      return t('library.technique')
    case 'other':
      return t('library.other')
    default:
      return kind || t('library.other')
  }
}

function sourceGroupLabel(key: string): string {
  return key === EMPTY_SOURCE_GROUP_KEY ? t('library.empty') : key
}

function selectGroup(mode: LibraryGroupMode, key: string) {
  if (mode === 'usage') {
    store.selectUsageGroup(key)
    return
  }

  store.selectSourceGroup(key)
}

function setGroupMode(mode: LibraryGroupMode) {
  store.setGroupMode(mode)
}

function getRouteGroupMode(): LibraryGroupMode | null {
  const group = route.query.group
  return group === 'source' || group === 'usage' ? group : null
}

async function applyRouteState() {
  const refId = typeof route.query.ref === 'string' ? route.query.ref : null
  const groupMode = getRouteGroupMode()

  if (!refId && !groupMode) {
    return
  }

  applyingRouteState.value = true
  try {
    if (refId) {
      await store.selectReferenceFromDeepLink(refId, groupMode)
    } else if (groupMode) {
      store.setGroupMode(groupMode)
    }
  } catch (e) {
    console.error('Apply library deep link failed:', e)
  } finally {
    applyingRouteState.value = false
  }
}

async function deleteSelectedReference() {
  if (!store.selectedReference) return
  if (!confirm(t('library.deleteConfirm'))) return
  await store.deleteReference(store.selectedReference.id)
  await loadStats()
}

async function createReference() {
  await store.createReference()
  await loadStats()
}

async function createReferenceInActiveSource() {
  const sourceReference = store.activeSourceGroup?.references[0]
  await store.createReference({
    source_title: sourceReference?.source_title ?? '',
    source_author: sourceReference?.source_author ?? '',
  })
  store.setGroupMode('source')
  await loadStats()
}

function formatFullReferenceCopy(): string {
  const reference = store.selectedReference
  if (!reference) return ''
  const content = reference.content.trim()
  const title = reference.source_title.trim()
  const author = reference.source_author.trim()
  const sourceParts = [
    title ? `《${title}》` : '',
    author,
  ].filter(Boolean)
  if (!sourceParts.length) return content
  return [content, `——${sourceParts.join(' ')}`].filter(Boolean).join('\n\n')
}

async function copyText(text: string, noticeKey: string) {
  if (!text.trim()) return
  try {
    await navigator.clipboard.writeText(text)
    copyNotice.value = t(noticeKey)
  } catch (e) {
    copyNotice.value = e instanceof Error ? e.message : String(e)
  }
  window.setTimeout(() => {
    copyNotice.value = ''
  }, 1800)
}

async function copyReferenceContent() {
  await copyText(store.selectedReference?.content ?? '', 'library.copyContentDone')
}

async function copyReferenceFull() {
  await copyText(formatFullReferenceCopy(), 'library.copyFullDone')
}
</script>

<template>
  <div class="flex h-full overflow-hidden bg-gray-50">
    <aside class="flex w-72 shrink-0 flex-col border-r border-gray-200 bg-white">
      <div class="border-b border-gray-200 p-4">
        <div class="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 class="text-xl font-bold">{{ t('library.title') }}</h2>
            <p class="mt-1 text-sm text-gray-500">
              {{ stats ? t('library.countSummary', { count: stats.total }) : t('library.countSummary', { count: store.references.length }) }}
            </p>
          </div>
          <button
            @click="createReference"
            class="rounded-lg bg-blue-600 px-3 py-2 text-sm text-white transition-colors hover:bg-blue-700"
          >
            {{ t('library.newReference') }}
          </button>
        </div>

        <div class="mb-4 rounded-xl bg-gray-100 p-1">
          <div class="grid grid-cols-2 gap-1">
            <button
              @click="setGroupMode('source')"
              :class="[
                'rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                store.groupMode === 'source'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-900',
              ]"
            >
              {{ t('library.groupBySource') }}
            </button>
            <button
              @click="setGroupMode('usage')"
              :class="[
                'rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                store.groupMode === 'usage'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-900',
              ]"
            >
              {{ t('library.groupByUsage') }}
            </button>
          </div>
        </div>

        <input
          v-model="searchInput"
          type="text"
          :placeholder="t('library.search')"
          class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div class="flex-1 overflow-y-auto">
        <div v-if="store.loading" class="p-4 text-sm text-gray-400">{{ t('library.loading') }}</div>
        <div v-else-if="store.error" class="p-4 text-sm text-red-500">{{ store.error }}</div>
        <div v-else-if="!currentGroups.length" class="p-4 text-sm text-gray-400">{{ t('library.noReferences') }}</div>
        <div v-else class="p-2">
          <button
            v-for="group in currentGroups"
            :key="group.key"
            @click="selectGroup(store.groupMode, group.key)"
            :class="[
              'mb-2 flex w-full items-center justify-between rounded-xl px-3 py-3 text-left transition-colors',
              (store.groupMode === 'source' ? store.activeSourceGroupKey : store.activeUsageGroupKey) === group.key
                ? 'bg-blue-50 text-blue-900 ring-1 ring-blue-200'
                : 'hover:bg-gray-100',
            ]"
          >
            <div class="min-w-0">
              <div class="truncate text-sm font-semibold">
                {{ store.groupMode === 'usage' ? usageLabel(group.key) : sourceGroupLabel(group.key) }}
              </div>
              <div class="mt-1 text-xs text-gray-500">
                {{ t('library.countSummary', { count: group.count }) }}
              </div>
            </div>
            <span class="ml-3 rounded-full bg-white/80 px-2 py-1 text-xs text-gray-500">
              {{ group.count }}
            </span>
          </button>
        </div>
      </div>
    </aside>

    <section class="flex w-[28rem] shrink-0 flex-col border-r border-gray-200 bg-white">
      <div class="border-b border-gray-200 px-5 py-4">
        <div class="text-xs font-semibold uppercase tracking-[0.2em] text-gray-400">
          {{ store.groupMode === 'usage' ? t('library.groupByUsage') : t('library.groupBySource') }}
        </div>
        <div class="mt-2 flex items-start justify-between gap-3">
          <div class="min-w-0">
            <h3 class="truncate text-lg font-bold text-gray-900">
              {{ activeGroupLabel || t('library.selectOrCreate') }}
            </h3>
            <p class="mt-1 text-sm text-gray-500">
              {{ activeGroup ? t('library.countSummary', { count: activeGroup.count }) : t('library.noReferences') }}
            </p>
          </div>
          <button
            v-if="store.groupMode === 'source' && activeGroup"
            @click="createReferenceInActiveSource"
            class="shrink-0 rounded-lg bg-stone-900 px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-stone-700"
          >
            {{ t('library.newInCurrentBook') }}
          </button>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-4">
        <div v-if="store.loading && !store.visibleReferences.length" class="p-4 text-sm text-gray-400">{{ t('library.loading') }}</div>
        <div v-else-if="store.error && !store.visibleReferences.length" class="p-4 text-sm text-red-500">{{ store.error }}</div>
        <div v-else-if="!store.visibleReferences.length" class="p-4 text-sm text-gray-400">{{ t('library.noReferences') }}</div>
        <div v-else class="space-y-3">
          <article
            v-for="reference in store.visibleReferences"
            :key="reference.id"
            @click="store.selectReference(reference.id)"
            :class="[
              'cursor-pointer rounded-2xl border p-4 transition-all',
              store.selectedRefId === reference.id
                ? 'border-blue-500 bg-blue-50 shadow-sm'
                : 'border-gray-200 bg-white hover:border-blue-300 hover:shadow-sm',
            ]"
          >
            <p class="line-clamp-5 whitespace-pre-wrap text-sm leading-6 text-gray-800">{{ preview(reference.content) }}</p>
            <div class="mt-3 flex flex-wrap items-center gap-2 text-xs text-gray-500">
              <span class="rounded-full bg-gray-100 px-2 py-1">
                {{ sourceGroupLabel(reference.source_title.trim() || EMPTY_SOURCE_GROUP_KEY) }}
              </span>
              <span class="rounded-full bg-amber-100 px-2 py-1 text-amber-700">
                {{ usageLabel(reference.usage_kind) }}
              </span>
              <span v-if="reference.source_author" class="truncate">— {{ reference.source_author }}</span>
            </div>
          </article>
        </div>
      </div>
    </section>

    <section class="flex min-w-0 flex-1 flex-col overflow-y-auto bg-white">
      <div v-if="store.selectedReference" class="mx-auto w-full max-w-3xl p-8">
        <div class="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-gray-200 bg-gray-50 p-3">
          <div class="text-sm text-gray-500">
            {{ copyNotice || t('library.copyHint') }}
          </div>
          <div class="flex gap-2">
            <button
              @click="copyReferenceContent"
              class="rounded-lg bg-white px-3 py-2 text-sm font-medium text-gray-700 ring-1 ring-gray-200 transition-colors hover:bg-gray-100"
            >
              {{ t('library.copyContent') }}
            </button>
            <button
              @click="copyReferenceFull"
              class="rounded-lg bg-gray-900 px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-gray-700"
            >
              {{ t('library.copyFull') }}
            </button>
          </div>
        </div>
        <div class="mb-6">
          <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('library.content') }}</label>
          <textarea
            v-model="store.selectedReference.content"
            @input="scheduleSave"
            class="min-h-[220px] w-full resize-none rounded-lg border border-gray-200 p-4 text-lg leading-relaxed focus:outline-none focus:ring-2 focus:ring-blue-500"
            :placeholder="t('library.placeholders.content')"
          />
        </div>

        <div class="mb-6 grid grid-cols-2 gap-4">
          <div>
            <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('library.sourceTitle') }}</label>
            <input
              v-model="store.selectedReference.source_title"
              @input="scheduleSave"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              :placeholder="t('library.placeholders.sourceTitle')"
            />
          </div>
          <div>
            <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('library.sourceAuthor') }}</label>
            <input
              v-model="store.selectedReference.source_author"
              @input="scheduleSave"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              :placeholder="t('library.placeholders.sourceAuthor')"
            />
          </div>
        </div>

        <div class="mb-6">
          <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('library.usageKind') }}</label>
          <select
            v-model="store.selectedReference.usage_kind"
            @change="scheduleSave"
            class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="style">{{ t('library.style') }}</option>
            <option value="imagery">{{ t('library.imagery') }}</option>
            <option value="structure">{{ t('library.structure') }}</option>
            <option value="rhetoric">{{ t('library.rhetoric') }}</option>
            <option value="diction">{{ t('library.diction') }}</option>
            <option value="reflection">{{ t('library.reflection') }}</option>
            <option value="setting">{{ t('library.setting') }}</option>
            <option value="technique">{{ t('library.technique') }}</option>
            <option value="other">{{ t('library.other') }}</option>
          </select>
        </div>

        <div class="mb-6">
          <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('library.personalNote') }}</label>
          <textarea
            v-model="store.selectedReference.personal_note"
            @input="scheduleSave"
            class="min-h-[100px] w-full resize-none rounded-lg border border-gray-200 p-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
            :placeholder="t('library.placeholders.personalNote')"
          />
        </div>

        <div class="flex items-center justify-between border-t border-gray-200 pt-4">
          <div class="text-xs text-gray-400">
            {{ t('library.createdAt') }} {{ store.selectedReference.created_at?.slice(0, 10) || '—' }}
          </div>
          <button
            @click="deleteSelectedReference"
            class="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600 transition-colors hover:bg-red-100"
          >
            {{ t('library.deleteReference') }}
          </button>
        </div>
      </div>
      <div v-else class="flex h-full items-center justify-center text-gray-400">
        {{ t('library.selectOrCreate') }}
      </div>
    </section>
  </div>
</template>

<style scoped>
.line-clamp-5 {
  display: -webkit-box;
  -webkit-line-clamp: 5;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
