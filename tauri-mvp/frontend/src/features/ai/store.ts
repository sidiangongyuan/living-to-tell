import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { aiApi, type Thread, type Message, type AiTaskRequest } from '../../api/ai'

export const useAiStore = defineStore('ai', () => {
  const threads = ref<Thread[]>([])
  const selectedThreadId = ref<string | null>(null)
  const messages = ref<Message[]>([])
  const loading = ref(false)
  const taskRunning = ref(false)
  const error = ref<string | null>(null)

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
      error.value = e instanceof Error ? e.message : String(e)
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
      error.value = e instanceof Error ? e.message : String(e)
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
      error.value = e instanceof Error ? e.message : String(e)
      throw e
    }
  }

  async function loadCurrentThread(
    scopeKind: 'global' | 'article' | 'collection',
    scopeId: string | null = null,
    create = true,
  ) {
    loading.value = true
    error.value = null
    try {
      const current = await aiApi.getCurrentThread(scopeKind, scopeId, create)
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
      messages.value = current.messages
      return current.thread
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function sendMessage(
    message: string,
    scopeKind: 'global' | 'article' | 'collection' = 'global',
    scopeId: string | null = null,
  ) {
    loading.value = true
    error.value = null
    try {
      const currentThread = selectedThread.value
      const threadMatchesScope = Boolean(
        currentThread
        && currentThread.scope_kind === scopeKind
        && (currentThread.scope_id ?? null) === (scopeId ?? null),
      )
      const threadId = currentThread && threadMatchesScope ? currentThread.id : null
      const response = await aiApi.chat({
        thread_id: threadId,
        message,
        scope_kind: scopeKind,
        scope_id: scopeId,
      })
      if (!selectedThreadId.value) {
        selectedThreadId.value = response.thread_id
      }
      messages.value.push(response.user_message)
      messages.value.push(response.assistant_message)
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function runTask(request: AiTaskRequest): Promise<string> {
    taskRunning.value = true
    error.value = null
    try {
      const response = await aiApi.runTask(request)
      return response.result
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
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
    taskRunning,
    error,
    loadThreads,
    createThread,
    deleteThread,
    loadCurrentThread,
    sendMessage,
    runTask,
    selectThread,
  }
})
