/**
 * AI API client
 */
import { apiFetch, handleResponse } from './base'

export interface AiTaskRequest {
  task_type: 'polish' | 'rewrite' | 'expand' | 'continue' | 'style_transfer' | 'summarize' | 'outline' | 'title' | 'structure_diagnose' | 'consistency_check'
  text: string
  instructions?: string
  context?: string
}

export interface AiTaskResponse {
  result: string
  task_type: string
}

export interface Thread {
  id: string
  scope_kind: 'global' | 'article' | 'collection' | string
  scope_id: string | null
  title: string
  created_at: string | null
  updated_at: string | null
}

export interface ThreadCreate {
  title?: string
  scope_kind?: 'global' | 'article' | 'collection'
  scope_id?: string | null
}

export interface Message {
  id?: string | null
  thread_id?: string | null
  role: 'user' | 'assistant'
  content: string
  timestamp: string | null
  meta?: Record<string, unknown>
}

export interface ChatRequest {
  thread_id?: string | null
  message: string
  scope_kind?: 'global' | 'article' | 'collection'
  scope_id?: string | null
}

export interface ChatResponse {
  thread_id: string
  user_message: Message
  assistant_message: Message
}

export interface CurrentThreadResponse {
  thread: Thread
  messages: Message[]
}

export const aiApi = {
  async runTask(request: AiTaskRequest): Promise<AiTaskResponse> {
    const res = await apiFetch('/api/ai/task', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
      // Extended timeout for long AI operations
      signal: AbortSignal.timeout(120000),
    })
    return handleResponse(res)
  },

  async listThreads(): Promise<Thread[]> {
    const res = await apiFetch('/api/ai/threads')
    return handleResponse(res)
  },

  async createThread(data: ThreadCreate = {}): Promise<Thread> {
    const res = await apiFetch('/api/ai/threads', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async getCurrentThread(
    scopeKind: 'global' | 'article' | 'collection',
    scopeId: string | null = null,
    create = false,
  ): Promise<CurrentThreadResponse | null> {
    const params = new URLSearchParams({
      scope_kind: scopeKind,
      create: String(create),
    })
    if (scopeId) params.set('scope_id', scopeId)
    const res = await apiFetch(`/api/ai/threads/current?${params}`)
    return handleResponse(res)
  },

  async getMessages(threadId: string): Promise<Message[]> {
    const res = await apiFetch(`/api/ai/threads/${threadId}/messages`)
    return handleResponse(res)
  },

  async deleteThread(id: string): Promise<void> {
    const res = await apiFetch(`/api/ai/threads/${id}`, {
      method: 'DELETE',
    })
    return handleResponse(res)
  },

  async chat(request: ChatRequest): Promise<ChatResponse> {
    const res = await apiFetch('/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
      signal: AbortSignal.timeout(120000),
    })
    return handleResponse(res)
  },
}
