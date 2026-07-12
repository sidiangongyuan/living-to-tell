import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  aiApi,
  type Thread,
  type Message,
  type AiTaskCompareRequest,
  type AiTaskCompareResponse,
  type AiTaskCompareStreamHandlers,
  type AiTaskRequest,
} from '../../api/ai'
import { errorMessage } from '../../api/base'

type ScopedMessage = Message & {
  __scope_kind?: 'global' | 'article' | 'collection'
  __scope_id?: string | null
}

export const useAiStore = defineStore('ai', () => {
  const threads = ref<Thread[]>([])
  const selectedThreadId = ref<string | null>(null)
  const messages = ref<ScopedMessage[]>([])
  const loading = ref(false)
  const chatSending = ref(false)
  const taskRunning = ref(false)
  const error = ref<string | null>(null)
  let pendingChatRequests = 0
  let currentThreadLoadSeq = 0

  const selectedThread = computed(() =>
    threads.value.find((t) => t.id === selectedThreadId.value) ?? null
  )

  async function loadThreads() {
    loading.value = true
    error.value = null
    try {
      threads.value = await aiApi.listThreads()
      if (threads.value.length && !selectedThreadId.value) {
        selectedThreadId.value = threads.value[0].id
      }
    } catch (e) {
      error.value = errorMessage(e)
    } finally {
      loading.value = false
    }
  }

  async function createThread(title = 'New Conversation') {
    try {
      const created = await aiApi.createThread({ title })
      threads.value.unshift(created)
      selectedThreadId.value = created.id
      messages.value = []
      return created
    } catch (e) {
      error.value = errorMessage(e)
      throw e
    }
  }

  async function deleteThread(id: string) {
    try {
      await aiApi.deleteThread(id)
      threads.value = threads.value.filter((t) => t.id !== id)
      if (selectedThreadId.value === id) {
        selectedThreadId.value = threads.value.length ? threads.value[0].id : null
        messages.value = []
      }
    } catch (e) {
      error.value = errorMessage(e)
      throw e
    }
  }

  async function loadCurrentThread(
    scopeKind: 'global' | 'article' | 'collection',
    scopeId: string | null = null,
    create = true,
  ) {
    const loadSeq = ++currentThreadLoadSeq
    loading.value = true
    error.value = null
    try {
      const current = await aiApi.getCurrentThread(scopeKind, scopeId, create)
      if (loadSeq !== currentThreadLoadSeq) return null
      if (!current) {
        selectedThreadId.value = null
        messages.value = []
        return null
      }
      const existingIndex = threads.value.findIndex((thread) => thread.id === current.thread.id)
      if (existingIndex === -1) {
        threads.value.unshift(current.thread)
      } else {
        threads.value[existingIndex] = current.thread
      }
      selectedThreadId.value = current.thread.id
      messages.value = current.messages.map((message) => ({
        ...message,
        __scope_kind: scopeKind,
        __scope_id: scopeId,
      }))
      return current.thread
    } catch (e) {
      if (loadSeq === currentThreadLoadSeq) error.value = errorMessage(e)
      throw e
    } finally {
      if (loadSeq === currentThreadLoadSeq) loading.value = false
    }
  }

  async function sendMessage(
    message: string,
    scopeKind: 'global' | 'article' | 'collection' = 'global',
    scopeId: string | null = null,
    profileId: string | null = null,
  ) {
    pendingChatRequests += 1
    chatSending.value = true
    loading.value = true
    error.value = null
    let requestedThreadId: string | null = null
    try {
      const currentThread = selectedThread.value
      const threadMatchesScope = Boolean(
        currentThread
        && currentThread.scope_kind === scopeKind
        && (currentThread.scope_id ?? null) === (scopeId ?? null),
      )
      const threadId = currentThread && threadMatchesScope ? currentThread.id : null
      requestedThreadId = threadId
      const response = await aiApi.chat({
        thread_id: threadId,
        message,
        scope_kind: scopeKind,
        scope_id: scopeId,
        profile_id: profileId,
      })
      const stillShowingRequestedThread = selectedThreadId.value === response.thread_id
        || selectedThreadId.value === threadId
        || selectedThreadId.value === null
      if (!selectedThreadId.value) {
        selectedThreadId.value = response.thread_id
      }
      if (stillShowingRequestedThread) {
        messages.value.push({
          ...response.user_message,
          __scope_kind: scopeKind,
          __scope_id: scopeId,
        })
        messages.value.push({
          ...response.assistant_message,
          __scope_kind: scopeKind,
          __scope_id: scopeId,
        })
      }
    } catch (e) {
      if (selectedThreadId.value === requestedThreadId || selectedThreadId.value === null) {
        error.value = errorMessage(e)
      }
      throw e
    } finally {
      pendingChatRequests = Math.max(0, pendingChatRequests - 1)
      chatSending.value = pendingChatRequests > 0
      if (!chatSending.value) loading.value = false
    }
  }

  async function runTask(request: AiTaskRequest): Promise<string> {
    taskRunning.value = true
    error.value = null
    try {
      const response = await aiApi.runTask(request)
      return response.result
    } catch (e) {
      error.value = errorMessage(e)
      throw e
    } finally {
      taskRunning.value = false
    }
  }

  async function compareTask(request: AiTaskCompareRequest): Promise<AiTaskCompareResponse> {
    taskRunning.value = true
    error.value = null
    try {
      return await aiApi.compareTask(request)
    } catch (e) {
      error.value = errorMessage(e)
      throw e
    } finally {
      taskRunning.value = false
    }
  }

  async function compareTaskStream(
    request: AiTaskCompareRequest,
    handlers: AiTaskCompareStreamHandlers,
  ): Promise<void> {
    taskRunning.value = true
    error.value = null
    try {
      await aiApi.compareTaskStream(request, handlers)
    } catch (e) {
      error.value = errorMessage(e)
      throw e
    } finally {
      taskRunning.value = false
    }
  }

  function selectThread(id: string) {
    selectedThreadId.value = id
    messages.value = []
  }

  return {
    threads,
    selectedThreadId,
    selectedThread,
    messages,
    loading,
    chatSending,
    taskRunning,
    error,
    loadThreads,
    createThread,
    deleteThread,
    loadCurrentThread,
    sendMessage,
    runTask,
    compareTask,
    compareTaskStream,
    selectThread,
  }
})
