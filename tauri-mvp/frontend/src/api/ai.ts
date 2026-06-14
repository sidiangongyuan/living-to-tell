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
  title: string
  created_at: string | null
  updated_at: string | null
}

export interface ThreadCreate {
  title?: string
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: string | null
}

export interface ChatRequest {
  thread_id: string
  message: string
}

export interface ChatResponse {
  thread_id: string
  user_message: Message
  assistant_message: Message
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
