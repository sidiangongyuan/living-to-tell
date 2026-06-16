<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { articlesApi, type Entry } from '../../api/articles'
import { aiCardApi, type AiCard } from '../../api/aiCards'
import { collectionsApi, type Collection } from '../../api/collections'
import { useI18n } from '../../i18n'
import { useAiStore } from './store'

type TaskType = 'polish' | 'rewrite' | 'expand' | 'continue' | 'style_transfer' | 'summarize' | 'outline' | 'title'
type AiTab = 'tools' | 'chat'
type ChatScopeKind = 'global' | 'article' | 'collection'

interface TaskOption {
  value: TaskType
  label: string
  desc: string
}

interface TaskGroup {
  name: string
  tasks: TaskOption[]
}

const store = useAiStore()
const route = useRoute()
const { t } = useI18n()

const activeTab = ref<AiTab>('tools')
const taskInput = ref('')
const taskType = ref<TaskType>('polish')
const taskResult = ref('')
const showComparison = ref(false)
const error = ref('')
const notice = ref('')

const aiCards = ref<AiCard[]>([])
const selectedCardIds = ref<string[]>([])
const showCardSelector = ref(false)

const scopeType = ref<'paste' | 'article'>('paste')
const selectedArticleId = ref<string | null>(null)
const articles = ref<Entry[]>([])
const collections = ref<Collection[]>([])

const chatScopeKind = ref<ChatScopeKind>('global')
const chatScopeId = ref<string | null>(null)
const chatInput = ref('')

const taskGroups = computed<TaskGroup[]>(() => [
  {
    name: t('ai.taskGroups.common'),
    tasks: [
      { value: 'polish', label: t('ai.tasks.polish.label'), desc: t('ai.tasks.polish.desc') },
      { value: 'expand', label: t('ai.tasks.expand.label'), desc: t('ai.tasks.expand.desc') },
      { value: 'continue', label: t('ai.tasks.continue.label'), desc: t('ai.tasks.continue.desc') },
      { value: 'rewrite', label: t('ai.tasks.rewrite.label'), desc: t('ai.tasks.rewrite.desc') },
    ],
  },
  {
    name: t('ai.taskGroups.advanced'),
    tasks: [
      { value: 'style_transfer', label: t('ai.tasks.styleTransfer.label'), desc: t('ai.tasks.styleTransfer.desc') },
      { value: 'outline', label: t('ai.tasks.outline.label'), desc: t('ai.tasks.outline.desc') },
      { value: 'title', label: t('ai.tasks.title.label'), desc: t('ai.tasks.title.desc') },
      { value: 'summarize', label: t('ai.tasks.summarize.label'), desc: t('ai.tasks.summarize.desc') },
    ],
  },
])

const selectedCards = computed(() =>
  aiCards.value.filter((card) => selectedCardIds.value.includes(card.id))
)

const selectedArticle = computed(() =>
  articles.value.find((article) => article.id === selectedArticleId.value) ?? null
)

const selectedChatArticle = computed(() =>
  articles.value.find((article) => article.id === chatScopeId.value) ?? null
)

const selectedChatCollection = computed(() =>
  collections.value.find((collection) => collection.id === chatScopeId.value) ?? null
)

const taskDescription = computed(() =>
  taskGroups.value.flatMap((group) => group.tasks).find((task) => task.value === taskType.value)?.desc ?? ''
)

const originalText = computed(() =>
  scopeType.value === 'article' ? selectedArticle.value?.body ?? '' : taskInput.value
)

const chatScopeLabel = computed(() => {
  if (chatScopeKind.value === 'article') {
    return selectedChatArticle.value?.title || t('articles.untitled')
  }
  if (chatScopeKind.value === 'collection') {
    return selectedChatCollection.value?.title || t('collections.untitled')
  }
  return t('ai.chatGlobal')
})

const cardTypeLabels = computed<Record<string, string>>(() => ({
  style: t('aiCards.cardTypes.style'),
  character: t('aiCards.cardTypes.character'),
  setting: t('aiCards.cardTypes.setting'),
}))

onMounted(async () => {
  await Promise.all([loadAiCards(), loadArticles(), loadCollections()])
  applyRouteScope()
  await loadChatThread()
})

watch(
  () => [route.query.tab, route.query.scope_kind, route.query.scope_id],
  async () => {
    applyRouteScope()
    await loadChatThread()
  }
)

watch([chatScopeKind, chatScopeId], async () => {
  await loadChatThread()
})

async function loadAiCards() {
  try {
    aiCards.value = await aiCardApi.listCards()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function loadArticles() {
  try {
    articles.value = await articlesApi.listArticles(500)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function loadCollections() {
  try {
    collections.value = await collectionsApi.listCollections()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

function normalizeScopeKind(value: unknown): ChatScopeKind {
  return value === 'article' || value === 'collection' || value === 'global' ? value : 'global'
}

function applyRouteScope() {
  activeTab.value = route.query.tab === 'chat' ? 'chat' : activeTab.value
  const scopeKind = normalizeScopeKind(route.query.scope_kind)
  const scopeId = typeof route.query.scope_id === 'string' ? route.query.scope_id : null
  chatScopeKind.value = scopeKind
  chatScopeId.value = scopeKind === 'global' ? null : scopeId
}

async function loadChatThread() {
  if (activeTab.value !== 'chat') return
  if (chatScopeKind.value !== 'global' && !chatScopeId.value) {
    store.selectedThreadId = null
    store.messages = []
    return
  }
  try {
    await store.loadCurrentThread(chatScopeKind.value, chatScopeId.value, true)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function handleRunTask() {
  error.value = ''
  notice.value = ''

  let fullText = originalText.value
  if (!fullText.trim()) {
    error.value = scopeType.value === 'article' ? t('ai.inputArticleRequired') : t('ai.inputTextRequired')
    return
  }

  if (selectedCards.value.length) {
    const cardContext = selectedCards.value
      .map((card) => `【${card.title}】\n${card.content}`)
      .join('\n\n')
    fullText = `${cardContext}\n\n---\n\n${fullText}`
  }

  try {
    taskResult.value = await store.runTask({
      task_type: taskType.value,
      text: fullText,
    })
    showComparison.value = true
  } catch (e) {
    taskResult.value = `${t('common.error')}: ${e instanceof Error ? e.message : String(e)}`
    showComparison.value = true
  }
}

async function sendChat() {
  const message = chatInput.value.trim()
  if (!message || store.loading) return
  chatInput.value = ''
  try {
    await store.sendMessage(message, chatScopeKind.value, chatScopeId.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function copyResult() {
  await navigator.clipboard.writeText(taskResult.value)
  notice.value = t('ai.copied')
}

async function replaceInArticle() {
  if (scopeType.value !== 'article' || !selectedArticleId.value || !taskResult.value.trim()) return
  if (!confirm(t('ai.confirmReplace'))) return
  try {
    await articlesApi.updateArticle(selectedArticleId.value, {
      body: taskResult.value,
    })
    await loadArticles()
    notice.value = t('ai.replaceSuccess')
  } catch (e) {
    error.value = `${t('ai.replaceFailed')}：${e instanceof Error ? e.message : String(e)}`
  }
}

function toggleCard(cardId: string) {
  if (selectedCardIds.value.includes(cardId)) {
    selectedCardIds.value = selectedCardIds.value.filter((id) => id !== cardId)
  } else {
    selectedCardIds.value = [...selectedCardIds.value, cardId]
  }
}
</script>

<template>
  <div class="flex h-full flex-col overflow-hidden bg-gray-50">
    <header class="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4">
      <div>
        <h1 class="text-xl font-bold">{{ t('ai.title') }}</h1>
        <p class="text-sm text-gray-500">{{ t('ai.subtitle') }}</p>
      </div>
      <div class="rounded-xl bg-gray-100 p-1">
        <button
          @click="activeTab = 'tools'"
          :class="[
            'rounded-lg px-4 py-2 text-sm font-semibold transition-colors',
            activeTab === 'tools' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-900',
          ]"
        >
          {{ t('ai.toolsTab') }}
        </button>
        <button
          @click="activeTab = 'chat'; loadChatThread()"
          :class="[
            'rounded-lg px-4 py-2 text-sm font-semibold transition-colors',
            activeTab === 'chat' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-900',
          ]"
        >
          {{ t('ai.chatTab') }}
        </button>
      </div>
    </header>

    <div v-if="activeTab === 'tools'" class="flex min-h-0 flex-1 overflow-hidden">
      <aside class="flex w-80 shrink-0 flex-col overflow-y-auto border-r border-gray-200 bg-white">
        <div class="space-y-4 p-4">
          <div v-if="error" class="rounded-lg bg-red-50 p-3 text-sm text-red-700">{{ error }}</div>
          <div v-if="notice" class="rounded-lg bg-green-50 p-3 text-sm text-green-700">{{ notice }}</div>

          <div>
            <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('ai.taskType') }}</label>
            <select
              v-model="taskType"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
            >
              <optgroup v-for="group in taskGroups" :key="group.name" :label="group.name">
                <option v-for="task in group.tasks" :key="task.value" :value="task.value">
                  {{ task.label }}
                </option>
              </optgroup>
            </select>
            <p class="mt-2 text-xs text-gray-500">{{ taskDescription }}</p>
          </div>

          <div>
            <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('ai.scope') }}</label>
            <div class="mb-2 flex gap-2">
              <button
                @click="scopeType = 'paste'"
                :class="[
                  'flex-1 rounded-lg px-3 py-2 text-sm transition-colors',
                  scopeType === 'paste' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
                ]"
              >
                {{ t('ai.scopePaste') }}
              </button>
              <button
                @click="scopeType = 'article'"
                :class="[
                  'flex-1 rounded-lg px-3 py-2 text-sm transition-colors',
                  scopeType === 'article' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
                ]"
              >
                {{ t('ai.scopeArticle') }}
              </button>
            </div>

            <textarea
              v-if="scopeType === 'paste'"
              v-model="taskInput"
              class="h-32 w-full resize-none rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
              :placeholder="t('ai.pasteText')"
            />

            <select
              v-if="scopeType === 'article'"
              v-model="selectedArticleId"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option :value="null">{{ t('ai.selectArticle') }}</option>
              <option v-for="article in articles" :key="article.id" :value="article.id">
                {{ article.title || t('articles.untitled') }}
              </option>
            </select>
          </div>

          <div>
            <div class="mb-2 flex items-center justify-between">
              <label class="text-sm font-semibold text-gray-700">{{ t('ai.aiCards') }}</label>
              <button @click="showCardSelector = !showCardSelector" class="text-xs text-blue-600 hover:text-blue-700">
                {{ showCardSelector ? t('ai.collapse') : t('ai.selectCards') }}
              </button>
            </div>

            <div v-if="selectedCards.length" class="mb-2 space-y-1">
              <div
                v-for="card in selectedCards"
                :key="card.id"
                class="flex items-center justify-between rounded border border-purple-200 bg-purple-50 p-2 text-xs"
              >
                <span class="font-semibold">{{ card.title }}</span>
                <button @click="toggleCard(card.id)" class="text-purple-600 hover:text-purple-800" :title="t('ai.removeCard')">×</button>
              </div>
            </div>

            <div v-if="showCardSelector" class="max-h-48 space-y-1 overflow-y-auto rounded-lg border border-gray-200 p-2">
              <button
                v-for="card in aiCards"
                :key="card.id"
                @click="toggleCard(card.id)"
                :class="[
                  'w-full rounded p-2 text-left text-xs transition-colors',
                  selectedCardIds.includes(card.id) ? 'border border-purple-300 bg-purple-100' : 'bg-gray-50 hover:bg-gray-100',
                ]"
              >
                <div class="font-semibold">{{ card.title }}</div>
                <div class="text-gray-500">{{ cardTypeLabels[card.card_type] }}</div>
              </button>
              <div v-if="!aiCards.length" class="py-4 text-center text-gray-400">
                {{ t('ai.noCards') }}
              </div>
            </div>

            <p class="mt-2 text-xs text-gray-400">{{ t('ai.cardHint') }}</p>
          </div>

          <button
            @click="handleRunTask"
            :disabled="store.taskRunning"
            class="w-full rounded-lg bg-blue-600 px-4 py-3 font-semibold text-white transition-colors hover:bg-blue-700 disabled:bg-gray-400"
          >
            {{ store.taskRunning ? t('ai.running') : t('ai.runTask') }}
          </button>
        </div>
      </aside>

      <main v-if="!showComparison" class="flex flex-1 items-center justify-center text-gray-400">
        <div class="text-center">
          <p class="mb-2 text-lg">{{ t('ai.selectOrCreate') }}</p>
          <p class="text-sm">{{ t('ai.comparisonHint') }}</p>
        </div>
      </main>

      <main v-else class="flex min-w-0 flex-1 flex-col">
        <div class="flex items-center justify-between border-b border-gray-200 bg-white p-4">
          <h2 class="text-lg font-bold">{{ t('ai.comparison') }}</h2>
          <div class="flex gap-2">
            <button @click="copyResult" class="rounded-lg bg-green-600 px-4 py-2 text-sm text-white transition-colors hover:bg-green-700">
              {{ t('ai.copyResult') }}
            </button>
            <button
              v-if="scopeType === 'article' && selectedArticleId"
              @click="replaceInArticle"
              :disabled="!taskResult.trim()"
              class="rounded-lg bg-orange-600 px-4 py-2 text-sm text-white transition-colors hover:bg-orange-700 disabled:opacity-40"
            >
              {{ t('ai.replaceOriginal') }}
            </button>
            <button @click="showComparison = false" class="rounded-lg bg-gray-600 px-4 py-2 text-sm text-white transition-colors hover:bg-gray-700">
              {{ t('ai.back') }}
            </button>
          </div>
        </div>

        <div class="flex flex-1 overflow-hidden">
          <section class="flex flex-1 flex-col border-r border-gray-200">
            <div class="border-b border-gray-200 bg-gray-100 p-3 text-sm font-semibold">{{ t('ai.original') }}</div>
            <div class="flex-1 overflow-y-auto p-6">
              <pre class="whitespace-pre-wrap font-sans leading-relaxed text-gray-700">{{ originalText }}</pre>
            </div>
          </section>

          <section class="flex flex-1 flex-col">
            <div class="border-b border-gray-200 bg-blue-100 p-3 text-sm font-semibold">{{ t('ai.result') }}</div>
            <div class="flex-1 overflow-y-auto bg-blue-50 p-6">
              <pre class="whitespace-pre-wrap font-sans leading-relaxed text-gray-900">{{ taskResult }}</pre>
            </div>
          </section>
        </div>
      </main>
    </div>

    <div v-else class="flex min-h-0 flex-1 overflow-hidden">
      <aside class="w-80 shrink-0 overflow-y-auto border-r border-gray-200 bg-white p-4">
        <div v-if="error" class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{{ error }}</div>
        <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('ai.chatScope') }}</label>
        <select
          v-model="chatScopeKind"
          class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="global">{{ t('ai.chatGlobal') }}</option>
          <option value="article">{{ t('ai.chatArticle') }}</option>
          <option value="collection">{{ t('ai.chatCollection') }}</option>
        </select>

        <select
          v-if="chatScopeKind === 'article'"
          v-model="chatScopeId"
          class="mt-3 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option :value="null">{{ t('ai.selectArticle') }}</option>
          <option v-for="article in articles" :key="article.id" :value="article.id">
            {{ article.title || t('articles.untitled') }}
          </option>
        </select>

        <select
          v-if="chatScopeKind === 'collection'"
          v-model="chatScopeId"
          class="mt-3 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option :value="null">{{ t('collections.selectCollection') }}</option>
          <option v-for="collection in collections" :key="collection.id" :value="collection.id">
            {{ collection.title || t('collections.untitled') }}
          </option>
        </select>

        <div class="mt-5 rounded-2xl bg-blue-50 p-4 text-sm text-blue-900">
          <div class="font-semibold">{{ t('ai.currentChatScope') }}</div>
          <p class="mt-1">{{ chatScopeLabel }}</p>
          <p class="mt-2 text-xs text-blue-700">{{ t('ai.chatScopeHint') }}</p>
        </div>
      </aside>

      <main class="flex min-w-0 flex-1 flex-col bg-[#fbfaf7]">
        <div class="border-b border-gray-200 bg-white px-6 py-4">
          <h2 class="text-lg font-bold">{{ t('ai.chatTitle') }}</h2>
          <p class="text-sm text-gray-500">{{ chatScopeLabel }}</p>
        </div>

        <div class="flex-1 overflow-y-auto p-6">
          <div v-if="store.loading && !store.messages.length" class="mt-20 text-center text-gray-400">
            {{ t('common.loading') }}
          </div>
          <div v-else-if="!store.messages.length" class="mt-20 text-center text-gray-400">
            {{ t('ai.chatEmpty') }}
          </div>
          <div v-else class="mx-auto max-w-3xl space-y-4">
            <article
              v-for="(message, index) in store.messages"
              :key="message.id ?? `${message.role}-${index}`"
              :class="[
                'rounded-3xl px-5 py-4 shadow-sm',
                message.role === 'user'
                  ? 'ml-12 bg-stone-900 text-white'
                  : 'mr-12 bg-white text-stone-800'
              ]"
            >
              <div class="mb-2 text-xs opacity-60">
                {{ message.role === 'user' ? t('ai.chatYou') : t('ai.chatAssistant') }}
              </div>
              <p class="whitespace-pre-wrap leading-7">{{ message.content }}</p>
            </article>
          </div>
        </div>

        <div class="border-t border-gray-200 bg-white p-4">
          <div class="mx-auto flex max-w-3xl gap-3">
            <textarea
              v-model="chatInput"
              rows="3"
              class="flex-1 resize-none rounded-2xl border border-gray-300 px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
              :placeholder="t('ai.chatPlaceholder')"
              @keydown.ctrl.enter.prevent="sendChat"
              @keydown.meta.enter.prevent="sendChat"
            />
            <button
              @click="sendChat"
              :disabled="store.loading || !chatInput.trim()"
              class="self-end rounded-2xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-40"
            >
              {{ store.loading ? t('ai.running') : t('ai.chatSend') }}
            </button>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>
