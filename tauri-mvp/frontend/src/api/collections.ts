/**
 * Article collections API client.
 */
import { apiFetch, handleResponse } from './base'

export interface Collection {
  id: string
  title: string
  description: string
  project_type: CollectionProjectType
  article_count: number
  created_at: string | null
  updated_at: string | null
}

export type CollectionProjectType = 'general' | 'novel' | 'essay' | 'nonfiction'

export interface CollectionCreate {
  title: string
  description?: string
  project_type?: CollectionProjectType
}

export interface CollectionUpdate {
  title: string
  description: string
  project_type: CollectionProjectType
}

export interface CollectionArticle {
  id: string
  title: string
  body: string
  body_preview: string
  tags: string[]
  word_count: number
  char_count: number
  sort_order: number
  created_at: string | null
  updated_at: string | null
}

export type OutlineItemType = 'part' | 'chapter' | 'scene' | 'note'
export type OutlineItemStatus = 'idea' | 'drafting' | 'revising' | 'done' | 'parked'

export interface CollectionOutlineItem {
  id: string
  collection_id: string
  parent_id: string | null
  entry_id: string | null
  title: string
  item_type: OutlineItemType
  status: OutlineItemStatus
  summary: string
  notes: string
  pov: string
  setting: string
  timeline: string
  tags: string[]
  target_word_count: number | null
  sort_order: number
  created_at: string | null
  updated_at: string | null
}

export interface CollectionOutlineItemInput {
  parent_id?: string | null
  entry_id?: string | null
  title: string
  item_type: OutlineItemType
  status: OutlineItemStatus
  summary?: string
  notes?: string
  pov?: string
  setting?: string
  timeline?: string
  tags?: string[]
  target_word_count?: number | null
}

export type CollectionExportFormat = 'txt' | 'md' | 'docx'

export interface CollectionAgentMemorySection {
  id: string
  title: string
  help: string
  content: string
}

export interface CollectionAgentMemory {
  collection_id: string
  sections: CollectionAgentMemorySection[]
  updated_at: string | null
}

export interface CollectionAgentSettings {
  collection_id: string
  profile_id: string
  enabled: boolean
  active_session_id: string | null
  updated_at: string | null
}

export type CollectionAgentMode = 'discuss' | 'plan' | 'draft' | 'review'

export interface CollectionAgentSession {
  id: string
  collection_id: string
  thread_id: string
  title: string
  mode: CollectionAgentMode
  summary: string
  archived: boolean
  message_count: number
  run_count: number
  draft_count: number
  created_at: string | null
  updated_at: string | null
  last_message_at: string | null
}

export interface CollectionAgentDraftBrief {
  target_scene: string
  pov: string
  tense: string
  target_length: number | null
  must_happen: string[]
  avoid: string[]
}

export interface CollectionAgentDraft {
  id: string
  collection_id: string
  session_id: string
  run_id: string | null
  parent_draft_id: string | null
  title: string
  content: string
  brief: Partial<CollectionAgentDraftBrief>
  variant_label: string
  status: 'draft' | 'applied' | string
  target_entry_id: string | null
  applied_ref_id: string | null
  content_hash: string
  created_at: string | null
  updated_at: string | null
  applied_at: string | null
}

export interface CollectionAgentDraftApplyResult {
  draft: CollectionAgentDraft
  entry_id: string
  article_title: string
  operation: 'create_article' | 'append' | 'replace_selection' | string
  version_id: string | null
}

export interface CollectionAgentStyleSample {
  id: string
  collection_id: string
  entry_id: string
  original_body: string
  final_body: string
  status: 'active' | 'completed' | string
  created_at: string | null
  completed_at: string | null
}

export interface AuthorPortrait {
  id: string
  tags: string[]
  summary: string
  evidence_count: number
  completed_style_cycles: number
  reminder_due: boolean
  created_at: string | null
  updated_at: string | null
}

export interface AuthorPortraitVersion {
  id: string
  portrait_id: string
  tags: string[]
  summary: string
  evidence_count: number
  reason: string
  created_at: string | null
}

export interface CollectionAgentReference {
  kind: 'outline' | 'article' | 'ai_card' | 'motif' | 'reference' | string
  ref_id: string
  name: string
  body_preview: string
  meta: Record<string, unknown>
}

export interface CollectionAgentMessage {
  id: string | null
  thread_id: string | null
  role: 'user' | 'assistant' | string
  content: string
  timestamp: string | null
  meta: Record<string, unknown>
}

export type CollectionAgentActionType =
  | 'update_memory'
  | 'create_outline_item'
  | 'update_outline_item'
  | 'create_article_note'
  | 'update_author_portrait'

export interface CollectionAgentAction {
  id: string
  collection_id: string
  run_id: string | null
  action_type: CollectionAgentActionType
  status: 'pending' | 'applied' | 'rejected' | 'deferred' | string
  title: string
  summary: string
  payload: Record<string, unknown>
  preview: Record<string, unknown>
  reason: string
  risk: string
  applied_ref_id: string | null
  created_at: string | null
  updated_at: string | null
  applied_at: string | null
}

export interface CollectionAgentRun {
  id: string
  collection_id: string
  thread_id: string | null
  status: 'queued' | 'preparing_context' | 'sending_request' | 'waiting_model' | 'parsing_response' | 'building_proposals' | 'succeeded' | 'failed' | 'cancelled' | string
  stage: string
  stage_label: string
  request: Record<string, unknown>
  result: Record<string, unknown>
  error: string
  profile_id: string
  provider: string | null
  model: string | null
  transport: string | null
  session_id: string | null
  mode: CollectionAgentMode
  draft_id: string | null
  created_at: string | null
  started_at: string | null
  updated_at: string | null
  completed_at: string | null
  actions: CollectionAgentAction[]
}

export interface CollectionAgentProfileOption {
  id: string
  name: string
}

export interface CollectionAgentState {
  settings: CollectionAgentSettings
  memory: CollectionAgentMemory
  thread_id: string | null
  messages: CollectionAgentMessage[]
  runs: CollectionAgentRun[]
  actions: CollectionAgentAction[]
  profiles: CollectionAgentProfileOption[]
  sessions: CollectionAgentSession[]
  active_session_id: string | null
  drafts: CollectionAgentDraft[]
  author_portrait: AuthorPortrait | null
  style_samples: CollectionAgentStyleSample[]
  active_run: CollectionAgentRun | null
}

export interface CollectionAgentRunCreate {
  message: string
  task_type?: string
  context_refs?: Array<{ kind: string; ref_id: string }>
  request_web_context?: boolean
  profile_id?: string | null
  session_id?: string | null
  mode?: CollectionAgentMode
  draft_brief?: CollectionAgentDraftBrief | null
  parent_draft_id?: string | null
}

export const collectionsApi = {
  async listCollections(): Promise<Collection[]> {
    const res = await apiFetch('/api/collections')
    return handleResponse(res)
  },

  async getCollection(id: string): Promise<Collection> {
    const res = await apiFetch(`/api/collections/${id}`)
    return handleResponse(res)
  },

  async createCollection(data: CollectionCreate): Promise<Collection> {
    const res = await apiFetch('/api/collections', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async updateCollection(id: string, data: CollectionUpdate): Promise<Collection> {
    const res = await apiFetch(`/api/collections/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async deleteCollection(id: string): Promise<void> {
    const res = await apiFetch(`/api/collections/${id}`, {
      method: 'DELETE',
    })
    return handleResponse(res)
  },

  async listArticles(collectionId: string): Promise<CollectionArticle[]> {
    const res = await apiFetch(`/api/collections/${collectionId}/articles`)
    return handleResponse(res)
  },

  async addArticles(collectionId: string, entryIds: string[]): Promise<CollectionArticle[]> {
    const res = await apiFetch(`/api/collections/${collectionId}/articles`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entry_ids: entryIds }),
    })
    return handleResponse(res)
  },

  async removeArticle(collectionId: string, entryId: string): Promise<void> {
    const res = await apiFetch(`/api/collections/${collectionId}/articles/${entryId}`, {
      method: 'DELETE',
    })
    return handleResponse(res)
  },

  async reorderArticles(collectionId: string, entryIds: string[]): Promise<CollectionArticle[]> {
    const res = await apiFetch(`/api/collections/${collectionId}/articles/order`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entry_ids: entryIds }),
    })
    return handleResponse(res)
  },

  async listCollectionsForEntry(entryId: string): Promise<Collection[]> {
    const res = await apiFetch(`/api/collections/for-entry/${entryId}`)
    return handleResponse(res)
  },

  async addEntryToCollections(entryId: string, collectionIds: string[]): Promise<Collection[]> {
    const res = await apiFetch(`/api/collections/for-entry/${entryId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ collection_ids: collectionIds }),
    })
    return handleResponse(res)
  },

  async exportCollection(collectionId: string, format: CollectionExportFormat): Promise<Blob> {
    const res = await apiFetch(`/api/collections/${collectionId}/export?format=${format}`)
    if (!res.ok) {
      await handleResponse(res)
    }
    return res.blob()
  },

  async listOutline(collectionId: string): Promise<CollectionOutlineItem[]> {
    const res = await apiFetch(`/api/collections/${collectionId}/outline`)
    return handleResponse(res)
  },

  async createOutlineItem(collectionId: string, data: CollectionOutlineItemInput): Promise<CollectionOutlineItem> {
    const res = await apiFetch(`/api/collections/${collectionId}/outline`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async updateOutlineItem(collectionId: string, itemId: string, data: CollectionOutlineItemInput): Promise<CollectionOutlineItem> {
    const res = await apiFetch(`/api/collections/${collectionId}/outline/${itemId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async deleteOutlineItem(collectionId: string, itemId: string): Promise<void> {
    const res = await apiFetch(`/api/collections/${collectionId}/outline/${itemId}`, {
      method: 'DELETE',
    })
    return handleResponse(res)
  },

  async reorderOutline(collectionId: string, itemIds: string[]): Promise<CollectionOutlineItem[]> {
    const res = await apiFetch(`/api/collections/${collectionId}/outline/order`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item_ids: itemIds }),
    })
    return handleResponse(res)
  },

  async getAgentState(collectionId: string, sessionId?: string | null): Promise<CollectionAgentState> {
    const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ''
    const res = await apiFetch(`/api/collections/${collectionId}/agent${query}`)
    return handleResponse(res)
  },

  async createAgentSession(collectionId: string, data: { title: string; mode: CollectionAgentMode }): Promise<CollectionAgentSession> {
    const res = await apiFetch(`/api/collections/${collectionId}/agent/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async updateAgentSession(collectionId: string, sessionId: string, data: { title?: string; mode?: CollectionAgentMode; archived?: boolean }): Promise<CollectionAgentSession> {
    const res = await apiFetch(`/api/collections/${collectionId}/agent/sessions/${sessionId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async activateAgentSession(collectionId: string, sessionId: string): Promise<CollectionAgentState> {
    const res = await apiFetch(`/api/collections/${collectionId}/agent/sessions/${sessionId}/activate`, { method: 'POST' })
    return handleResponse(res)
  },

  async compactAgentSession(collectionId: string, sessionId: string): Promise<CollectionAgentSession> {
    const res = await apiFetch(`/api/collections/${collectionId}/agent/sessions/${sessionId}/compact`, { method: 'POST' })
    return handleResponse(res)
  },

  async clearAgentSession(collectionId: string, sessionId: string): Promise<CollectionAgentState> {
    const res = await apiFetch(`/api/collections/${collectionId}/agent/sessions/${sessionId}/clear`, { method: 'POST' })
    return handleResponse(res)
  },

  async deleteAgentSession(collectionId: string, sessionId: string): Promise<void> {
    const res = await apiFetch(`/api/collections/${collectionId}/agent/sessions/${sessionId}`, { method: 'DELETE' })
    if (!res.ok) await handleResponse(res)
  },

  async saveAgentSettings(collectionId: string, data: { profile_id: string; enabled: boolean }): Promise<CollectionAgentSettings> {
    const res = await apiFetch(`/api/collections/${collectionId}/agent/settings`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async saveAgentMemory(collectionId: string, sections: Record<string, string>): Promise<CollectionAgentMemory> {
    const res = await apiFetch(`/api/collections/${collectionId}/agent/memory`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sections }),
    })
    return handleResponse(res)
  },

  async searchAgentReferences(collectionId: string, query = '', limit = 30): Promise<CollectionAgentReference[]> {
    const params = new URLSearchParams({ q: query, limit: String(limit) })
    const res = await apiFetch(`/api/collections/${collectionId}/agent/references?${params}`)
    return handleResponse(res)
  },

  async createAgentRun(collectionId: string, data: CollectionAgentRunCreate): Promise<CollectionAgentRun> {
    const res = await apiFetch(`/api/collections/${collectionId}/agent/runs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async getAgentRun(collectionId: string, runId: string): Promise<CollectionAgentRun> {
    const res = await apiFetch(`/api/collections/${collectionId}/agent/runs/${runId}`)
    return handleResponse(res)
  },

  async cancelAgentRun(collectionId: string, runId: string): Promise<CollectionAgentRun> {
    const res = await apiFetch(`/api/collections/${collectionId}/agent/runs/${runId}/cancel`, {
      method: 'POST',
    })
    return handleResponse(res)
  },

  async clearAgentConversation(collectionId: string): Promise<CollectionAgentState> {
    const res = await apiFetch(`/api/collections/${collectionId}/agent/clear`, {
      method: 'POST',
    })
    return handleResponse(res)
  },

  async applyAgentAction(collectionId: string, actionId: string): Promise<CollectionAgentAction> {
    const res = await apiFetch(`/api/collections/${collectionId}/agent/actions/${actionId}/apply`, {
      method: 'POST',
    })
    return handleResponse(res)
  },

  async rejectAgentAction(collectionId: string, actionId: string): Promise<CollectionAgentAction> {
    const res = await apiFetch(`/api/collections/${collectionId}/agent/actions/${actionId}/reject`, {
      method: 'POST',
    })
    return handleResponse(res)
  },

  async deferAgentAction(collectionId: string, actionId: string): Promise<CollectionAgentAction> {
    const res = await apiFetch(`/api/collections/${collectionId}/agent/actions/${actionId}/defer`, {
      method: 'POST',
    })
    return handleResponse(res)
  },

  async updateAgentDraft(collectionId: string, draftId: string, data: { title: string; content: string; brief: Partial<CollectionAgentDraftBrief> }): Promise<CollectionAgentDraft> {
    const res = await apiFetch(`/api/collections/${collectionId}/agent/drafts/${draftId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async applyAgentDraft(collectionId: string, draftId: string, data: {
    operation: 'create_article' | 'append' | 'replace_selection'
    target_entry_id?: string | null
    article_title?: string
    expected_body_hash?: string
    selection_start?: number | null
    selection_end?: number | null
    expected_selected_text?: string
  }): Promise<CollectionAgentDraftApplyResult> {
    const res = await apiFetch(`/api/collections/${collectionId}/agent/drafts/${draftId}/apply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async deleteAgentDrafts(collectionId: string, draftIds: string[], clearAll = false): Promise<{ deleted: number }> {
    const res = await apiFetch(`/api/collections/${collectionId}/agent/drafts/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ draft_ids: draftIds, clear_all: clearAll }),
    })
    return handleResponse(res)
  },

  async listAgentStyleSamples(collectionId: string): Promise<CollectionAgentStyleSample[]> {
    const res = await apiFetch(`/api/collections/${collectionId}/agent/style-samples`)
    return handleResponse(res)
  },

  async startAgentStyleSample(collectionId: string, entryId: string): Promise<CollectionAgentStyleSample> {
    const res = await apiFetch(`/api/collections/${collectionId}/agent/style-samples`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entry_id: entryId }),
    })
    return handleResponse(res)
  },

  async completeAgentStyleSample(collectionId: string, sampleId: string): Promise<CollectionAgentStyleSample> {
    const res = await apiFetch(`/api/collections/${collectionId}/agent/style-samples/${sampleId}/complete`, { method: 'POST' })
    return handleResponse(res)
  },

  async saveAuthorPortrait(collectionId: string, data: { tags: string[]; summary: string }): Promise<AuthorPortrait> {
    const res = await apiFetch(`/api/collections/${collectionId}/agent/author-portrait`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async listAuthorPortraitVersions(collectionId: string): Promise<AuthorPortraitVersion[]> {
    const res = await apiFetch(`/api/collections/${collectionId}/agent/author-portrait/versions`)
    return handleResponse(res)
  },

  async restoreAuthorPortraitVersion(collectionId: string, versionId: string): Promise<AuthorPortrait> {
    const res = await apiFetch(`/api/collections/${collectionId}/agent/author-portrait/versions/${versionId}/restore`, { method: 'POST' })
    return handleResponse(res)
  },
}
