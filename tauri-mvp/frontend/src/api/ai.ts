/**
 * AI API client
 */
import { apiFetch, handleResponse, HttpError } from './base'

export interface AiTaskRequest {
  task_type: 'polish' | 'rewrite' | 'expand' | 'continue' | 'style_transfer' | 'summarize' | 'outline' | 'title' | 'structure_diagnose' | 'consistency_check'
  text: string
  instructions?: string
  context?: string
  target_kind?: 'selection' | 'article' | 'collection' | 'paste'
  target_ref_id?: string | null
  style?: string | null
  intensity?: string | null
  extra_instructions?: string | null
  max_output_chars?: number | null
  preserve_meaning?: boolean
  preserve_voice?: boolean
  forbid_terms?: string[]
  must_keep_terms?: string[]
  attachments?: AiContextAttachment[]
  cost_tier?: 'thrifty' | 'balanced' | 'strong'
}

export interface AiTaskResponse {
  result: string
  task_type: string
}

export interface AiTaskResultStats {
  input_chars: number
  output_chars: number
  delta_chars: number
  output_ratio: number | null
  input_paragraphs: number
  output_paragraphs: number
}

export interface AiTaskCompareResult {
  profile_id: string
  profile_name: string
  provider: string
  model: string
  transport?: string | null
  status: 'success' | 'error' | 'pending'
  result: string
  error: string
  elapsed_ms: number
  input_tokens?: number | null
  output_tokens?: number | null
  cost?: number | null
  finish_reason?: string | null
  stats: AiTaskResultStats
}

export interface AiTaskCompareRequest extends AiTaskRequest {
  profile_ids: string[]
}

export interface AiTaskCompareResponse {
  task_type: string
  results: AiTaskCompareResult[]
}

export interface AiTaskCompareProfileSnapshot {
  profile_id: string
  profile_name: string
  provider: string
  model: string
}

export interface AiTaskCompareStartedEvent {
  event: 'started'
  run_id: string
  profiles: AiTaskCompareProfileSnapshot[]
}

export interface AiTaskCompareResultEvent {
  event: 'result' | 'error'
  result: AiTaskCompareResult
}

export interface AiTaskCompareDoneEvent {
  event: 'done'
  run_id: string
}

export interface ArticleAiTaskRunCreate extends Omit<AiTaskRequest, 'text' | 'target_kind' | 'target_ref_id'> {
  article_id: string
  profile_ids: string[]
  selection_start?: number | null
  selection_end?: number | null
}

export interface ArticleAiTaskRun {
  run_id: string
  article_id: string
  article_title: string
  task_type: 'polish' | 'rewrite' | 'expand' | 'continue'
  article_hash: string
  original_text: string
  selection_start?: number | null
  selection_end?: number | null
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'
  stage: string
  stage_label: string
  error: string
  profiles: AiTaskCompareProfileSnapshot[]
  results: AiTaskCompareResult[]
  created_at: string
  started_at?: string | null
  updated_at: string
  completed_at?: string | null
  elapsed_ms: number
  applied_profile_id?: string | null
  applied_at?: string | null
  applied_version_id?: string | null
}

export interface ArticleAiTaskApplyResult {
  run: ArticleAiTaskRun
  entry: {
    id: string
    title: string
    body: string
    tags: string[]
    entry_type: string
    created_at: string | null
    updated_at: string | null
    archived_at: string | null
    curation_status: string
  }
  version_id: string
  was_noop: boolean
}

export type AiTaskCompareStreamEvent =
  | AiTaskCompareStartedEvent
  | AiTaskCompareResultEvent
  | AiTaskCompareDoneEvent

export interface AiTaskCompareStreamHandlers {
  onStarted?: (event: AiTaskCompareStartedEvent) => void
  onResult?: (event: AiTaskCompareResultEvent) => void
  onError?: (event: AiTaskCompareResultEvent) => void
  onDone?: (event: AiTaskCompareDoneEvent) => void
}

export interface AiContextAttachment {
  kind: string
  ref_id: string
  name: string
  body: string
}

export interface AiTaskPreset {
  id: string
  task_type: AiTaskRequest['task_type']
  name: string
  controls: Record<string, unknown>
}

export type AiTaskPresetMap = Partial<Record<AiTaskRequest['task_type'], AiTaskPreset[]>>

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
  __scope_kind?: 'global' | 'article' | 'collection'
  __scope_id?: string | null
}

export interface ChatRequest {
  thread_id?: string | null
  message: string
  scope_kind?: 'global' | 'article' | 'collection'
  scope_id?: string | null
  profile_id?: string | null
}

export interface ChatResponse {
  thread_id: string
  user_message: Message
  assistant_message: Message
}

export interface ChatSettings {
  system_prompt: string
}

export interface CurrentThreadResponse {
  thread: Thread
  messages: Message[]
}

export const aiApi = {
  async createArticleTaskRun(request: ArticleAiTaskRunCreate): Promise<ArticleAiTaskRun> {
    const res = await apiFetch('/api/ai/task-runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    })
    return handleResponse(res)
  },

  async getLatestArticleTaskRun(): Promise<ArticleAiTaskRun | null> {
    const res = await apiFetch('/api/ai/task-runs/active')
    return handleResponse(res)
  },

  async getArticleTaskRun(runId: string): Promise<ArticleAiTaskRun> {
    const res = await apiFetch(`/api/ai/task-runs/${encodeURIComponent(runId)}`)
    return handleResponse(res)
  },

  async cancelArticleTaskRun(runId: string): Promise<ArticleAiTaskRun> {
    const res = await apiFetch(`/api/ai/task-runs/${encodeURIComponent(runId)}/cancel`, {
      method: 'POST',
    })
    return handleResponse(res)
  },

  async applyArticleTaskRun(runId: string, profileId: string): Promise<ArticleAiTaskApplyResult> {
    const res = await apiFetch(`/api/ai/task-runs/${encodeURIComponent(runId)}/apply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile_id: profileId }),
    })
    return handleResponse(res)
  },

  async clearArticleTaskRun(runId: string): Promise<void> {
    const res = await apiFetch(`/api/ai/task-runs/${encodeURIComponent(runId)}`, {
      method: 'DELETE',
    })
    return handleResponse(res)
  },

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

  async compareTask(request: AiTaskCompareRequest): Promise<AiTaskCompareResponse> {
    const res = await apiFetch('/api/ai/task/compare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
      signal: AbortSignal.timeout(120000),
    })
    return handleResponse(res)
  },

  async compareTaskStream(
    request: AiTaskCompareRequest,
    handlers: AiTaskCompareStreamHandlers,
  ): Promise<void> {
    const res = await apiFetch('/api/ai/task/compare/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
      signal: AbortSignal.timeout(600000),
    })
    if (!res.ok) {
      const error = await res.json().catch(() => ({
        detail: `HTTP ${res.status}: ${res.statusText}`,
      }))
      throw new HttpError(res.status, res.statusText, error.detail)
    }

    const processLine = (line: string) => {
      const trimmed = line.trim()
      if (!trimmed) return
      const event = JSON.parse(trimmed) as AiTaskCompareStreamEvent
      if (event.event === 'started') {
        handlers.onStarted?.(event)
      } else if (event.event === 'done') {
        handlers.onDone?.(event)
      } else if (event.event === 'error') {
        handlers.onError?.(event)
      } else {
        handlers.onResult?.(event)
      }
    }

    if (!res.body) {
      const text = await res.text()
      for (const line of text.split('\n')) processLine(line)
      return
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { value, done } = await reader.read()
      if (value) {
        buffer += decoder.decode(value, { stream: !done })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''
        for (const line of lines) processLine(line)
      }
      if (done) break
    }
    buffer += decoder.decode()
    if (buffer.trim()) processLine(buffer)
  },

  async listTaskPresets(): Promise<AiTaskPresetMap> {
    const res = await apiFetch('/api/ai/task-presets')
    return handleResponse(res)
  },

  async saveTaskPresets(presets: AiTaskPresetMap): Promise<AiTaskPresetMap> {
    const res = await apiFetch('/api/ai/task-presets', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(presets),
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

  async getChatSettings(): Promise<ChatSettings> {
    const res = await apiFetch('/api/ai/chat-settings')
    return handleResponse(res)
  },

  async saveChatSettings(settings: ChatSettings): Promise<ChatSettings> {
    const res = await apiFetch('/api/ai/chat-settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
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
