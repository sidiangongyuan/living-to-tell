<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { useLibraryStore } from './store'
import { libraryApi, type LibraryStats } from '../../api/library'
import { useI18n } from '../../i18n'

const store = useLibraryStore()
const { t } = useI18n()
const searchInput = ref('')
const saveTimer = ref<number | null>(null)
const stats = ref<LibraryStats | null>(null)
const usageFilter = ref<string>('all')

onMounted(() => {
  store.loadReferences()
  loadStats()
})

async function loadStats() {
  try {
    stats.value = await libraryApi.getStats()
  } catch (e) {
    console.error('Load stats failed:', e)
  }
}

const filteredReferences = computed(() => {
  if (usageFilter.value === 'all') {
    return store.references
  }
  return store.references.filter(r => r.usage_kind === usageFilter.value)
})

let searchTimer: number | null = null
watch(searchInput, (val) => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => store.search(val), 300)
})

function scheduleSave() {
  if (saveTimer.value) clearTimeout(saveTimer.value)
  saveTimer.value = window.setTimeout(saveNow, 600)
}

async function saveNow() {
  if (store.selectedReference) {
    await store.updateReference(store.selectedReference)
  }
}

function preview(content: string): string {
  return content.trim().slice(0, 60) || t('library.empty')
}

// 用途标签的中文显示
const usageKindLabels: Record<string, string> = {
  style: t('library.style'),
  imagery: t('library.imagery'),
  structure: t('library.structure'),
  rhetoric: t('library.rhetoric'),
  diction: t('library.diction'),
  other: t('library.other'),
}

function usageLabel(kind: string): string {
  return usageKindLabels[kind] || kind
}

async function deleteSelectedReference() {
  if (!store.selectedReference) return
  if (!confirm(t('library.deleteConfirm'))) return
  await store.deleteReference(store.selectedReference.id)
}
</script>

<template>
  <div class="flex h-full overflow-hidden bg-gray-50">
    <!-- 左：标本列表 -->
    <div class="w-80 shrink-0 bg-white border-r border-gray-200 flex flex-col">
      <div class="p-4 border-b border-gray-200">
        <div class="flex items-center justify-between mb-3">
          <div>
            <h2 class="text-xl font-bold">{{ t('library.title') }}</h2>
            <p class="text-sm text-gray-500 mt-1">
              {{ stats ? t('library.countSummary', { count: stats.total }) : t('library.countSummary', { count: store.references.length }) }}
            </p>
          </div>
          <button
            @click="store.createReference()"
            class="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm transition-colors"
          >
            {{ t('library.newReference') }}
          </button>
        </div>

        <!-- 统计卡片 -->
        <div v-if="stats && stats.by_usage_kind" class="mb-3 p-3 bg-gray-50 rounded-lg">
          <div class="text-xs font-semibold text-gray-600 mb-2">{{ t('library.statsByUsage') }}</div>
          <div class="grid grid-cols-2 gap-2 text-xs">
            <div v-for="(count, kind) in stats.by_usage_kind" :key="kind" class="flex justify-between">
              <span class="text-gray-600">{{ usageLabel(kind) }}:</span>
              <span class="font-semibold">{{ count }}</span>
            </div>
          </div>
        </div>

        <!-- 用途筛选 -->
        <div class="mb-3">
          <div class="flex flex-wrap gap-1">
            <button
              @click="usageFilter = 'all'"
              :class="[
                'px-2 py-1 text-xs rounded transition-colors',
                usageFilter === 'all'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              ]"
            >
              {{ t('library.filterAll') }}
            </button>
            <button
              v-for="kind in ['style', 'imagery', 'structure', 'rhetoric', 'diction']"
              :key="kind"
              @click="usageFilter = kind"
              :class="[
                'px-2 py-1 text-xs rounded transition-colors',
                usageFilter === kind
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              ]"
            >
              {{ usageLabel(kind) }}
            </button>
          </div>
        </div>

        <input
          v-model="searchInput"
          type="text"
          :placeholder="t('library.search')"
          class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div class="flex-1 overflow-y-auto">
        <div v-if="store.loading" class="p-4 text-sm text-gray-400">{{ t('library.loading') }}</div>
        <div v-else-if="store.error" class="p-4 text-sm text-red-500">{{ store.error }}</div>
        <div v-else-if="!filteredReferences.length" class="p-4 text-sm text-gray-400">
          {{ usageFilter === 'all' ? t('library.noReferences') : t('library.filterNone', { kind: usageLabel(usageFilter) }) }}
        </div>
        <div
          v-for="ref in filteredReferences"
          :key="ref.id"
          @click="store.selectReference(ref.id)"
          :class="[
            'p-4 border-b border-gray-100 cursor-pointer transition-colors',
            store.selectedRefId === ref.id
              ? 'bg-blue-50 border-l-4 border-l-blue-600'
              : 'hover:bg-gray-50',
          ]"
        >
          <p class="text-sm text-gray-800 line-clamp-2 mb-1">{{ preview(ref.content) }}</p>
          <div class="flex items-center gap-2 text-xs text-gray-500">
            <span v-if="ref.source_title" class="truncate">《{{ ref.source_title }}》</span>
            <span v-if="ref.source_author">— {{ ref.source_author }}</span>
          </div>
          <div v-if="ref.usage_kind" class="mt-1">
            <span class="text-xs px-2 py-0.5 bg-amber-100 text-amber-700 rounded">
              {{ usageLabel(ref.usage_kind) }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 右：标本编辑 -->
    <div class="flex-1 min-w-0 flex flex-col bg-white overflow-y-auto">
      <div v-if="store.selectedReference" class="p-8 max-w-3xl mx-auto w-full">
        <!-- 标本正文 -->
        <div class="mb-6">
          <label class="block text-sm font-semibold text-gray-700 mb-2">{{ t('library.content') }}</label>
          <textarea
            v-model="store.selectedReference.content"
            @input="scheduleSave"
            class="w-full min-h-[200px] p-4 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none leading-relaxed text-lg"
            :placeholder="t('library.placeholders.content')"
          />
        </div>

        <!-- 出处信息 -->
        <div class="grid grid-cols-2 gap-4 mb-6">
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-2">{{ t('library.sourceTitle') }}</label>
            <input
              v-model="store.selectedReference.source_title"
              @input="scheduleSave"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              :placeholder="t('library.placeholders.sourceTitle')"
            />
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-2">{{ t('library.sourceAuthor') }}</label>
            <input
              v-model="store.selectedReference.source_author"
              @input="scheduleSave"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              :placeholder="t('library.placeholders.sourceAuthor')"
            />
          </div>
        </div>

        <!-- 用途 -->
        <div class="mb-6">
          <label class="block text-sm font-semibold text-gray-700 mb-2">{{ t('library.usageKind') }}</label>
          <select
            v-model="store.selectedReference.usage_kind"
            @change="scheduleSave"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="style">{{ t('library.style') }}</option>
            <option value="imagery">{{ t('library.imagery') }}</option>
            <option value="structure">{{ t('library.structure') }}</option>
            <option value="rhetoric">{{ t('library.rhetoric') }}</option>
            <option value="diction">{{ t('library.diction') }}</option>
            <option value="other">{{ t('library.other') }}</option>
          </select>
        </div>

        <!-- 个人笔记 -->
        <div class="mb-6">
          <label class="block text-sm font-semibold text-gray-700 mb-2">{{ t('library.personalNote') }}</label>
          <textarea
            v-model="store.selectedReference.personal_note"
            @input="scheduleSave"
            class="w-full min-h-[100px] p-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            :placeholder="t('library.placeholders.personalNote')"
          />
        </div>

        <!-- 操作 -->
        <div class="flex items-center justify-between pt-4 border-t border-gray-200">
          <div class="text-xs text-gray-400">
            {{ t('library.createdAt') }} {{ store.selectedReference.created_at?.slice(0, 10) || '—' }}
          </div>
          <button
            @click="deleteSelectedReference"
            class="px-4 py-2 bg-red-50 hover:bg-red-100 text-red-600 rounded-lg text-sm transition-colors"
          >
            {{ t('library.deleteReference') }}
          </button>
        </div>
      </div>
      <div v-else class="flex items-center justify-center h-full text-gray-400">
        {{ t('library.selectOrCreate') }}
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
