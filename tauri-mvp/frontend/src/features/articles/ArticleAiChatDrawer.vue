<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { articlesApi, type Entry } from '../../api/articles'
import { libraryApi } from '../../api/library'
import { notesApi } from '../../api/notes'
import { errorMessage } from '../../api/base'
import { settingsApi, type AiProfile } from '../../api/settings'
import { useI18n } from '../../i18n'
import { useAiStore } from '../ai/store'

const props = defineProps<{ open: boolean; article: Entry | null }>()
const emit = defineEmits<{ close: []; articleCreated: [entry: Entry] }>()
const { t } = useI18n()
const store = useAiStore()
const profiles = ref<AiProfile[]>([])
const selectedProfileId = ref('')
const drafts = ref<Record<string, string>>({})
const error = ref('')
const notice = ref('')
const captureOpen = ref(false)
const captureKind = ref<'reference' | 'article'>('reference')
const captureTitle = ref('')
const captureContent = ref('')
let articleLoadToken = 0

const input = computed({
  get: () => props.article ? drafts.value[props.article.id] ?? '' : '',
  set: (value: string) => {
    if (props.article) drafts.value = { ...drafts.value, [props.article.id]: value }
  },
})
async function loadForArticle() {
  const token = ++articleLoadToken
  const article = props.article
  if (!props.open || !article) return
  error.value = ''
  try {
    const result = await settingsApi.listAiProfiles()
    if (token !== articleLoadToken || !props.open || props.article?.id !== article.id) return
    profiles.value = result.profiles.filter((item) => item.enabled)
    if (!profiles.value.some((item) => item.id === selectedProfileId.value)) {
      selectedProfileId.value = result.default_profile_id ?? profiles.value[0]?.id ?? ''
    }
    store.selectedThreadId = null
    store.messages = []
    await store.loadCurrentThread('article', article.id, true)
  } catch (e) {
    if (token === articleLoadToken && props.open && props.article?.id === article.id) {
      error.value = errorMessage(e)
    }
  }
}

async function send() {
  if (!props.article || !input.value.trim() || store.chatSending) return
  const articleId = props.article.id
  const message = input.value.trim()
  input.value = ''
  error.value = ''
  notice.value = ''
  try {
    await store.sendMessage(message, 'article', articleId, selectedProfileId.value || null)
  } catch (e) {
    drafts.value = { ...drafts.value, [articleId]: message }
    if (props.article?.id === articleId) error.value = errorMessage(e)
  }
}

async function clearConversation() {
  if (!store.selectedThreadId || !window.confirm(t('articleChat.clearConfirm'))) return
  error.value = ''
  try {
    await store.deleteThread(store.selectedThreadId)
    if (props.article) await store.loadCurrentThread('article', props.article.id, true)
    notice.value = t('articleChat.cleared')
  } catch (e) {
    error.value = errorMessage(e)
  }
}

async function copy(content: string) {
  try {
    await navigator.clipboard.writeText(content)
    notice.value = t('articleChat.copied')
  } catch (e) {
    error.value = errorMessage(e)
  }
}

async function saveNote(content: string) {
  if (!props.article) return
  try {
    await notesApi.createNote(props.article.id, content)
    notice.value = t('articleChat.noteSaved')
  } catch (e) {
    error.value = errorMessage(e)
  }
}

function openCapture(kind: 'reference' | 'article', content: string) {
  captureKind.value = kind
  captureContent.value = content
  captureTitle.value = kind === 'reference'
    ? t('articleChat.referenceTitle', { title: props.article?.title || '' })
    : t('articleChat.articleTitle', { title: props.article?.title || '' })
  captureOpen.value = true
}

async function confirmCapture() {
  if (!captureTitle.value.trim() || !captureContent.value.trim()) return
  try {
    if (captureKind.value === 'reference') {
      await libraryApi.createReference({
        source_title: captureTitle.value.trim(),
        source_author: 'AI',
        content: captureContent.value.trim(),
        tags: ['AI'],
        usage_kind: 'other',
        personal_note: t('articleChat.reviewedCapture'),
      })
      notice.value = t('articleChat.referenceSaved')
    } else {
      const entry = await articlesApi.create({ title: captureTitle.value.trim(), body: captureContent.value.trim(), tags: ['AI'] })
      emit('articleCreated', entry)
      notice.value = t('articleChat.articleSaved')
    }
    captureOpen.value = false
  } catch (e) {
    error.value = errorMessage(e)
  }
}

function onKeydown(event: KeyboardEvent) {
  if (event.key !== 'Escape') return
  if (captureOpen.value) captureOpen.value = false
  else if (props.open) emit('close')
}

watch(() => [props.open, props.article?.id], () => void loadForArticle(), { immediate: true })
watch(() => props.open, (open) => {
  if (open) window.addEventListener('keydown', onKeydown)
  else window.removeEventListener('keydown', onKeydown)
}, { immediate: true })
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-50 bg-black/20" @click.self="emit('close')">
      <aside role="dialog" aria-modal="true" aria-labelledby="article-ai-chat-title" class="absolute inset-y-0 right-0 flex w-full max-w-[460px] flex-col border-l border-stone-200 bg-white shadow-2xl" data-testid="article-ai-chat-drawer">
        <header class="flex items-start justify-between gap-3 border-b border-stone-200 px-4 py-3">
          <div class="min-w-0"><h2 id="article-ai-chat-title" class="text-sm font-semibold text-stone-900">{{ t('articleChat.title') }}</h2><p class="mt-1 truncate text-xs text-stone-500">{{ article?.title || t('articleChat.noArticle') }}</p></div>
          <div class="flex items-center gap-2"><button type="button" class="rounded-md border border-stone-300 px-2 py-1 text-xs text-stone-600" @click="clearConversation">{{ t('articleChat.clear') }}</button><button type="button" class="h-8 w-8 rounded-md text-stone-500 hover:bg-stone-100" :aria-label="t('common.close')" @click="emit('close')">×</button></div>
        </header>
        <div class="border-b border-stone-200 px-4 py-3"><label class="text-xs font-medium text-stone-600">{{ t('articleChat.model') }}<select v-model="selectedProfileId" class="mt-1 w-full rounded-md border border-stone-300 px-2 py-1.5 text-xs"><option v-for="profile in profiles" :key="profile.id" :value="profile.id">{{ profile.name }} · {{ profile.model }}</option></select></label></div>
        <div v-if="error || store.error" class="m-3 rounded-md bg-red-50 p-2 text-xs text-red-700">{{ error || store.error }}</div>
        <div v-if="notice" class="m-3 rounded-md bg-emerald-50 p-2 text-xs text-emerald-700">{{ notice }}</div>
        <div class="min-h-0 flex-1 overflow-y-auto px-4 py-4">
          <p v-if="!store.messages.length" class="py-12 text-center text-sm leading-6 text-stone-500">{{ t('articleChat.empty') }}</p>
          <div v-else class="space-y-4">
            <article v-for="(message, index) in store.messages" :key="message.id || index" :class="message.role === 'user' ? 'ml-8' : 'mr-3'">
              <div :class="['whitespace-pre-wrap rounded-md px-3 py-2 text-sm leading-6', message.role === 'user' ? 'bg-stone-900 text-white' : 'bg-stone-100 text-stone-800']">{{ message.content }}</div>
              <div v-if="message.role === 'assistant'" class="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-stone-400"><span>{{ message.meta?.provider || 'AI' }} · {{ message.meta?.model || '-' }} · {{ message.meta?.transport || '-' }}</span><button class="underline" @click="copy(message.content)">{{ t('articleChat.copy') }}</button><button class="underline" @click="saveNote(message.content)">{{ t('articleChat.saveNote') }}</button><button class="underline" @click="openCapture('reference', message.content)">{{ t('articleChat.saveReference') }}</button><button class="underline" @click="openCapture('article', message.content)">{{ t('articleChat.saveArticle') }}</button></div>
            </article>
          </div>
        </div>
        <footer class="border-t border-stone-200 p-4"><textarea v-model="input" rows="4" :disabled="!article" class="w-full resize-none rounded-md border border-stone-300 px-3 py-2 text-sm leading-6" :placeholder="t('articleChat.placeholder')" @keydown.ctrl.enter.prevent="send" /><div class="mt-2 flex items-center justify-between gap-3"><p class="text-[11px] text-stone-400">{{ t('articleChat.contextHint') }}</p><button :disabled="!input.trim() || !selectedProfileId || store.chatSending" class="rounded-md bg-stone-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40" @click="send">{{ store.chatSending ? t('common.loading') : t('articleChat.send') }}</button></div></footer>
      </aside>
    </div>

    <div v-if="captureOpen" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 p-4" @click.self="captureOpen = false"><div role="dialog" aria-modal="true" aria-labelledby="article-ai-capture-title" class="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white p-5 shadow-2xl"><h3 id="article-ai-capture-title" class="font-semibold text-stone-900">{{ captureKind === 'reference' ? t('articleChat.previewReference') : t('articleChat.previewArticle') }}</h3><p class="mt-1 text-xs text-stone-500">{{ t('articleChat.previewHelp') }}</p><label class="mt-4 block text-sm text-stone-700">{{ t('articleChat.captureTitle') }}<input v-model="captureTitle" class="mt-1 w-full rounded-md border border-stone-300 px-3 py-2" /></label><label class="mt-4 block text-sm text-stone-700">{{ t('articleChat.captureContent') }}<textarea v-model="captureContent" rows="12" class="mt-1 w-full rounded-md border border-stone-300 px-3 py-2 text-sm leading-6" /></label><div class="mt-4 flex justify-end gap-2"><button class="rounded-md border border-stone-300 px-3 py-2 text-sm" @click="captureOpen = false">{{ t('common.cancel') }}</button><button class="rounded-md bg-stone-900 px-4 py-2 text-sm font-semibold text-white" @click="confirmCapture">{{ t('common.confirm') }}</button></div></div></div>
  </Teleport>
</template>
