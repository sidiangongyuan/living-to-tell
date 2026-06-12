<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { apiClient, type Entry } from './api/client'

const entries = ref<Entry[]>([])
const selectedId = ref<string | null>(null)
const showContextPane = ref(true)
const loading = ref(false)
const error = ref<string | null>(null)
const saving = ref(false)
const saveTimer = ref<number | null>(null)

const selectedEntry = computed(
  () => entries.value.find((e) => e.id === selectedId.value) ?? null,
)

async function loadEntries() {
  loading.value = true
  error.value = null
  try {
    entries.value = await apiClient.listEntries()
    if (entries.value.length && selectedId.value === null) {
      selectedId.value = entries.value[0].id
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

function selectEntry(entry: Entry) {
  selectedId.value = entry.id
}

function toggleContextPane() {
  showContextPane.value = !showContextPane.value
}

async function createEntry() {
  try {
    const created = await apiClient.createEntry({
      title: 'Untitled',
      body: '',
    })
    entries.value.unshift(created)
    selectedId.value = created.id
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

function scheduleSave() {
  if (saveTimer.value !== null) {
    clearTimeout(saveTimer.value)
  }
  saveTimer.value = window.setTimeout(saveSelected, 600)
}

async function saveSelected() {
  const entry = selectedEntry.value
  if (!entry) return
  saving.value = true
  try {
    const updated = await apiClient.updateEntry(entry.id, {
      title: entry.title,
      body: entry.body,
      tags: entry.tags,
    })
    const idx = entries.value.findIndex((e) => e.id === updated.id)
    if (idx !== -1) entries.value[idx] = updated
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    saving.value = false
  }
}

async function deleteSelected() {
  const entry = selectedEntry.value
  if (!entry) return
  try {
    await apiClient.deleteEntry(entry.id)
    entries.value = entries.value.filter((e) => e.id !== entry.id)
    selectedId.value = entries.value.length ? entries.value[0].id : null
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

const wordCount = computed(() => {
  const body = selectedEntry.value?.body ?? ''
  const trimmed = body.trim()
  return trimmed ? trimmed.split(/\s+/).length : 0
})
const charCount = computed(() => selectedEntry.value?.body.length ?? 0)
const lineCount = computed(() => selectedEntry.value?.body.split('\n').length ?? 0)

function preview(body: string): string {
  return body.trim().slice(0, 80) || 'No content yet'
}

onMounted(loadEntries)
</script>

<template>
  <div class="flex h-screen bg-gray-50 text-gray-900">
    <!-- Left nav rail (80px) -->
    <div class="w-20 shrink-0 bg-gray-900 flex flex-col items-center py-4 gap-4">
      <button
        class="w-12 h-12 rounded-lg bg-blue-600 hover:bg-blue-700 text-white flex items-center justify-center transition-colors"
        title="Articles"
      >
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      </button>
    </div>

    <!-- Center: list + editor (flex-1, the shrinkable column) -->
    <div class="flex-1 min-w-0 flex overflow-hidden">
      <!-- Article list (320px, fixed) -->
      <div class="w-80 shrink-0 bg-white border-r border-gray-200 flex flex-col">
        <div class="p-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h2 class="text-xl font-bold">Articles</h2>
            <p class="text-sm text-gray-500 mt-1">{{ entries.length }} total</p>
          </div>
          <button
            @click="createEntry"
            class="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm transition-colors"
          >
            + New
          </button>
        </div>
        <div class="flex-1 overflow-y-auto">
          <div v-if="loading" class="p-4 text-sm text-gray-400">Loading…</div>
          <div v-else-if="error" class="p-4 text-sm text-red-500">{{ error }}</div>
          <div v-else-if="!entries.length" class="p-4 text-sm text-gray-400">
            No articles yet. Click “+ New”.
          </div>
          <div
            v-for="entry in entries"
            :key="entry.id"
            @click="selectEntry(entry)"
            :class="[
              'p-4 border-b border-gray-100 cursor-pointer transition-colors',
              selectedId === entry.id
                ? 'bg-blue-50 border-l-4 border-l-blue-600'
                : 'hover:bg-gray-50',
            ]"
          >
            <h3 class="font-semibold mb-1 truncate">{{ entry.title || 'Untitled' }}</h3>
            <p class="text-sm text-gray-500 line-clamp-2">{{ preview(entry.body) }}</p>
            <div v-if="entry.tags.length" class="flex flex-wrap gap-1 mt-2">
              <span
                v-for="tag in entry.tags"
                :key="tag"
                class="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded"
              >{{ tag }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Editor -->
      <div class="flex-1 min-w-0 flex flex-col bg-white overflow-hidden">
        <div class="flex items-center justify-between gap-4 p-4 border-b border-gray-200">
          <input
            v-if="selectedEntry"
            v-model="selectedEntry.title"
            @input="scheduleSave"
            class="text-2xl font-bold flex-1 min-w-0 focus:outline-none"
            placeholder="Title"
          />
          <div v-else class="text-gray-400">No article selected</div>
          <div class="flex items-center gap-3 shrink-0">
            <span class="text-xs text-gray-400">{{ saving ? 'Saving…' : 'Saved' }}</span>
            <button
              @click="toggleContextPane"
              class="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors flex items-center gap-2"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
              {{ showContextPane ? 'Hide' : 'Show' }} Context
            </button>
          </div>
        </div>
        <div class="flex-1 overflow-y-auto p-6">
          <textarea
            v-if="selectedEntry"
            v-model="selectedEntry.body"
            @input="scheduleSave"
            class="w-full h-full min-h-[500px] max-w-3xl mx-auto block p-4 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none leading-relaxed"
            placeholder="Start writing…"
          />
          <div v-else class="text-center text-gray-400 mt-20">
            Select or create an article to start writing.
          </div>
        </div>
      </div>
    </div>

    <!-- Right context pane (280px, toggleable). v-show keeps it mounted; the
         flex layout reflows the center column automatically — no manual width
         math, so it can never be pushed off-screen the way the Qt splitter was. -->
    <div
      v-show="showContextPane"
      class="w-72 shrink-0 bg-white border-l border-gray-200 flex flex-col"
    >
      <div class="p-4 border-b border-gray-200">
        <h2 class="text-lg font-bold">Context</h2>
      </div>
      <div class="flex-1 overflow-y-auto p-4 space-y-6">
        <template v-if="selectedEntry">
          <div>
            <h3 class="text-sm font-semibold text-gray-700 mb-2">Statistics</h3>
            <div class="space-y-2 text-sm text-gray-600">
              <div class="flex justify-between"><span>Words</span><span class="font-medium">{{ wordCount }}</span></div>
              <div class="flex justify-between"><span>Characters</span><span class="font-medium">{{ charCount }}</span></div>
              <div class="flex justify-between"><span>Lines</span><span class="font-medium">{{ lineCount }}</span></div>
            </div>
          </div>
          <div>
            <h3 class="text-sm font-semibold text-gray-700 mb-2">Actions</h3>
            <div class="space-y-2">
              <button
                @click="saveSelected"
                class="w-full px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm transition-colors"
              >Save now</button>
              <button
                @click="deleteSelected"
                class="w-full px-3 py-2 bg-red-50 hover:bg-red-100 text-red-600 rounded-lg text-sm transition-colors"
              >Delete</button>
            </div>
          </div>
        </template>
        <div v-else class="text-sm text-gray-400">No article selected.</div>
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
