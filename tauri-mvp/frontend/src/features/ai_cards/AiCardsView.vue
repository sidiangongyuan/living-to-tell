<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { aiCardApi, type AiCard } from '../../api/aiCards'
import { useI18n } from '../../i18n'

const { t } = useI18n()
const cards = ref<AiCard[]>([])
const selectedCardId = ref<string | null>(null)
const loading = ref(false)
const error = ref('')
const notice = ref('')
const filterType = ref<'all' | 'style' | 'character' | 'setting'>('all')
const filterSource = ref<'all' | 'preset' | 'user'>('all')
const sortMode = ref<'recent' | 'title'>('recent')
const searchQuery = ref('')
const presetSignatures = ref(new Set<string>())
const pendingCardSave = ref<AiCard | null>(null)
const saveNotice = ref('')
const saveFailed = ref(false)
const presetWarning = ref('')

const selectedCard = computed(() => cards.value.find(c => c.id === selectedCardId.value) || null)

const filteredCards = computed(() => {
  let result = cards.value
  if (filterType.value !== 'all') {
    result = result.filter(c => c.card_type === filterType.value)
  }
  if (filterSource.value !== 'all') {
    result = result.filter(c => cardSource(c) === filterSource.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(c =>
      c.title.toLowerCase().includes(q) ||
      c.content.toLowerCase().includes(q)
    )
  }
  return [...result].sort((a, b) => {
    if (sortMode.value === 'title') {
      return (a.title || '').localeCompare(b.title || '', 'zh-CN')
    }
    const aTime = Date.parse(a.updated_at || a.created_at || '') || 0
    const bTime = Date.parse(b.updated_at || b.created_at || '') || 0
    return bTime - aTime
  })
})

const cardTypeLabels = computed<Record<string, string>>(() => ({
  style: t('aiCards.cardTypes.style'),
  character: t('aiCards.cardTypes.character'),
  setting: t('aiCards.cardTypes.setting'),
}))

onMounted(() => {
  loadCards()
  loadPresets()
})

onUnmounted(() => {
  void flushPendingCardSave()
})

async function loadCards() {
  loading.value = true
  error.value = ''
  try {
    cards.value = await aiCardApi.listCards()
    if (cards.value.length && !selectedCardId.value) {
      selectedCardId.value = cards.value[0].id
    }
  } catch (e) {
    console.error('Load cards failed:', e)
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

async function loadPresets() {
  presetWarning.value = ''
  try {
    const presets = await aiCardApi.listPresets()
    presetSignatures.value = new Set(
      presets.map((preset) => `${String(preset.title || '').trim()}::${String(preset.card_type || 'style').trim()}`)
    )
  } catch (e) {
    console.error('Load presets failed:', e)
    presetWarning.value = t('aiCards.presetMetadataUnavailable')
  }
}

function cardSource(card: AiCard): 'preset' | 'user' {
  return presetSignatures.value.has(`${card.title.trim()}::${card.card_type}`) ? 'preset' : 'user'
}

function sourceLabel(card: AiCard): string {
  return cardSource(card) === 'preset' ? t('aiCards.sourcePreset') : t('aiCards.sourceUser')
}

async function createCard() {
  const saved = await flushPendingCardSave()
  if (!saved) return
  error.value = ''
  notice.value = ''
  saveNotice.value = ''
  try {
    const card = await aiCardApi.createCard({
      title: t('aiCards.untitled'),
      content: '',
      card_type: 'style',
      tags: [],
    })
    cards.value.unshift(card)
    selectedCardId.value = card.id
  } catch (e) {
    console.error('Create card failed:', e)
    error.value = e instanceof Error ? e.message : String(e)
  }
}

let saveTimer: number | null = null
function scheduleAutoSave() {
  const snapshot = snapshotSelectedCard()
  if (!snapshot) return
  pendingCardSave.value = snapshot
  saveNotice.value = t('aiCards.savePending')
  saveFailed.value = false
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = window.setTimeout(() => {
    void flushPendingCardSave()
  }, 600)
}

function snapshotSelectedCard(): AiCard | null {
  const card = selectedCard.value
  if (!card) return null
  return {
    ...card,
    tags: [...card.tags],
  }
}

async function flushPendingCardSave(): Promise<boolean> {
  if (saveTimer) {
    clearTimeout(saveTimer)
    saveTimer = null
  }
  const snapshot = pendingCardSave.value
  if (!snapshot) return true
  pendingCardSave.value = null
  saveNotice.value = t('aiCards.savePending')
  saveFailed.value = false
  try {
    const updated = await aiCardApi.updateCard(snapshot.id, {
      title: snapshot.title,
      content: snapshot.content,
      card_type: snapshot.card_type,
      tags: snapshot.tags,
    })
    const idx = cards.value.findIndex(c => c.id === updated.id)
    if (idx !== -1) cards.value[idx] = updated
    error.value = ''
    saveNotice.value = t('aiCards.saveSuccess')
    saveFailed.value = false
    return true
  } catch (e) {
    console.error('Save card failed:', e)
    const message = e instanceof Error ? e.message : String(e)
    error.value = message
    saveNotice.value = t('aiCards.saveFailed', { message })
    saveFailed.value = true
    pendingCardSave.value = snapshot
    return false
  }
}

async function deleteCard(id: string) {
  if (!confirm(t('aiCards.deleteConfirm'))) return
  if (saveTimer) {
    clearTimeout(saveTimer)
    saveTimer = null
  }
  if (pendingCardSave.value?.id === id) {
    pendingCardSave.value = null
  } else {
    const saved = await flushPendingCardSave()
    if (!saved) return
  }
  try {
    error.value = ''
    notice.value = ''
    await aiCardApi.deleteCard(id)
    cards.value = cards.value.filter(c => c.id !== id)
    if (selectedCardId.value === id) {
      selectedCardId.value = cards.value.length ? cards.value[0].id : null
    }
  } catch (e) {
    console.error('Delete card failed:', e)
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function generatePresets() {
  const saved = await flushPendingCardSave()
  if (!saved) return
  if (cards.value.length && !confirm(t('aiCards.confirmGenerate'))) return
  try {
    error.value = ''
    notice.value = ''
    const result = await aiCardApi.generateFromPresets()
    notice.value = t('aiCards.generateSuccess', { count: result.created })
    await loadCards()
  } catch (e) {
    console.error('Generate presets failed:', e)
    error.value = `${t('aiCards.generateFailed')}：${e instanceof Error ? e.message : String(e)}`
  }
}

async function selectCard(id: string) {
  const saved = await flushPendingCardSave()
  if (!saved) return
  selectedCardId.value = id
}
</script>

<template>
  <div class="flex h-full overflow-hidden bg-gray-50">
    <!-- 左侧：卡片列表 -->
    <div class="w-80 shrink-0 bg-white border-r border-gray-200 flex flex-col">
      <div class="p-4 border-b border-gray-200">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-xl font-bold">{{ t('aiCards.title') }}</h2>
          <div class="flex gap-2">
            <button
              @click="generatePresets"
              class="px-3 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm transition-colors"
              :title="t('aiCards.presetTooltip')"
            >
              {{ t('aiCards.generatePresets') }}
            </button>
            <button
              @click="createCard"
              class="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm transition-colors"
            >
              {{ t('aiCards.newCard') }}
            </button>
          </div>
        </div>
        <input
          v-model="searchQuery"
          type="text"
          :placeholder="t('aiCards.search')"
          class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 mb-3"
        />
        <!-- 类型过滤 -->
        <div class="flex flex-wrap gap-2">
          <button
            v-for="type in ['all', 'style', 'character', 'setting'] as const"
            :key="type"
            @click="filterType = type"
            :class="[
              'px-3 py-1 text-xs rounded-lg transition-colors',
              filterType === type
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            ]"
          >
            {{ type === 'all' ? t('aiCards.filterAll') : cardTypeLabels[type] }}
          </button>
        </div>
        <div class="mt-3 grid grid-cols-2 gap-2">
          <select
            v-model="filterSource"
            class="rounded-lg border border-gray-300 px-3 py-2 text-xs outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">{{ t('aiCards.sourceAll') }}</option>
            <option value="preset">{{ t('aiCards.sourcePreset') }}</option>
            <option value="user">{{ t('aiCards.sourceUser') }}</option>
          </select>
          <select
            v-model="sortMode"
            class="rounded-lg border border-gray-300 px-3 py-2 text-xs outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="recent">{{ t('aiCards.sortRecent') }}</option>
            <option value="title">{{ t('aiCards.sortTitle') }}</option>
          </select>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto">
        <div v-if="notice" class="m-3 rounded-lg bg-green-50 p-3 text-sm text-green-700">{{ notice }}</div>
        <div v-if="presetWarning" class="m-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">{{ presetWarning }}</div>
        <div v-if="error" class="m-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">{{ error }}</div>
        <div v-if="loading" class="p-4 text-sm text-gray-400">{{ t('common.loading') }}</div>
        <div v-else-if="!filteredCards.length" class="p-4 text-sm text-gray-400">
          {{ t('aiCards.noCards') }}
        </div>
        <div
          v-for="card in filteredCards"
          :key="card.id"
          @click="selectCard(card.id)"
          :class="[
            'p-4 border-b border-gray-100 cursor-pointer transition-colors',
            selectedCardId === card.id
              ? 'bg-blue-50 border-l-4 border-l-blue-600'
              : 'hover:bg-gray-50'
          ]"
        >
          <div class="font-semibold text-sm mb-1">{{ card.title || t('aiCards.untitled') }}</div>
          <div class="text-xs text-gray-500 line-clamp-2">
            {{ card.content || t('library.empty') }}
          </div>
          <div class="mt-2 flex flex-wrap gap-2">
            <span class="text-xs px-2 py-0.5 bg-purple-100 text-purple-700 rounded">
              {{ cardTypeLabels[card.card_type] }}
            </span>
            <span class="rounded bg-stone-100 px-2 py-0.5 text-xs text-stone-600">
              {{ sourceLabel(card) }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧：编辑区 -->
    <div class="flex-1 min-w-0 flex flex-col bg-white overflow-y-auto">
      <div v-if="selectedCard" class="p-8 max-w-3xl mx-auto w-full">
        <div
          v-if="saveNotice"
          :class="[
            'mb-5 rounded-lg px-3 py-2 text-sm',
            saveFailed ? 'bg-red-50 text-red-700' : 'bg-blue-50 text-blue-700',
          ]"
        >
          {{ saveNotice }}
        </div>
        <!-- 标题 -->
        <div class="mb-6">
          <label class="block text-sm font-semibold text-gray-700 mb-2">{{ t('aiCards.fields.title') }}</label>
          <input
            v-model="selectedCard.title"
            @input="scheduleAutoSave"
            class="w-full px-4 py-3 border border-gray-200 rounded-lg text-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
            :placeholder="t('aiCards.placeholders.title')"
          />
        </div>

        <!-- 类型 -->
        <div class="mb-6">
          <label class="block text-sm font-semibold text-gray-700 mb-2">{{ t('aiCards.fields.type') }}</label>
          <select
            v-model="selectedCard.card_type"
            @change="scheduleAutoSave"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="style">{{ t('aiCards.cardTypes.style') }}</option>
            <option value="character">{{ t('aiCards.cardTypes.character') }}</option>
            <option value="setting">{{ t('aiCards.cardTypes.setting') }}</option>
          </select>
        </div>

        <!-- 内容 -->
        <div class="mb-6">
          <label class="block text-sm font-semibold text-gray-700 mb-2">{{ t('aiCards.fields.content') }}</label>
          <textarea
            v-model="selectedCard.content"
            @input="scheduleAutoSave"
            class="w-full min-h-[300px] p-4 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none leading-relaxed"
            :placeholder="t('aiCards.placeholders.content')"
          />
          <p class="text-xs text-gray-500 mt-2">
            {{ t('aiCards.contentHint') }}
          </p>
        </div>

        <!-- 标签（暂时隐藏，未来可扩展） -->

        <!-- 操作 -->
        <div class="flex items-center justify-between pt-4 border-t border-gray-200">
          <div class="text-xs text-gray-400">
            {{ t('articles.createdAt') }} {{ selectedCard.created_at?.slice(0, 10) || '—' }}
          </div>
          <button
            @click="deleteCard(selectedCard.id)"
            class="px-4 py-2 bg-red-50 hover:bg-red-100 text-red-600 rounded-lg text-sm transition-colors"
          >
            {{ t('aiCards.deleteCard') }}
          </button>
        </div>
      </div>
      <div v-else class="flex items-center justify-center h-full text-gray-400">
        {{ t('aiCards.selectOrCreate') }}
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
