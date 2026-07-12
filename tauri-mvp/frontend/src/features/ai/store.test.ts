import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { aiApi, type ChatResponse, type CurrentThreadResponse } from '../../api/ai'
import { useAiStore } from './store'

describe('AI chat store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => vi.restoreAllMocks())

  it('does not append a late reply to a different article conversation', async () => {
    let resolveChat!: (value: ChatResponse) => void
    vi.spyOn(aiApi, 'chat').mockImplementation(() => new Promise((resolve) => {
      resolveChat = resolve
    }))
    const store = useAiStore()
    store.threads = [
      { id: 'thread-a', scope_kind: 'article', scope_id: 'article-a', title: 'A', created_at: null, updated_at: null },
      { id: 'thread-b', scope_kind: 'article', scope_id: 'article-b', title: 'B', created_at: null, updated_at: null },
    ]
    store.selectedThreadId = 'thread-a'

    const pending = store.sendMessage('A question', 'article', 'article-a', 'profile-a')
    expect(store.chatSending).toBe(true)
    store.selectThread('thread-b')
    store.messages = [{ role: 'user', content: 'B message', timestamp: null }]
    resolveChat({
      thread_id: 'thread-a',
      user_message: { role: 'user', content: 'A question', timestamp: null },
      assistant_message: { role: 'assistant', content: 'A late reply', timestamp: null },
    })
    await pending

    expect(store.selectedThreadId).toBe('thread-b')
    expect(store.messages.map((message) => message.content)).toEqual(['B message'])
    expect(store.chatSending).toBe(false)
  })

  it('ignores a late thread load after switching articles', async () => {
    let resolveA!: (value: CurrentThreadResponse) => void
    let resolveB!: (value: CurrentThreadResponse) => void
    vi.spyOn(aiApi, 'getCurrentThread').mockImplementation((_scopeKind, scopeId) => new Promise((resolve) => {
      if (scopeId === 'article-a') resolveA = resolve
      else resolveB = resolve
    }))
    const store = useAiStore()

    const pendingA = store.loadCurrentThread('article', 'article-a', true)
    const pendingB = store.loadCurrentThread('article', 'article-b', true)
    resolveB({
      thread: { id: 'thread-b', scope_kind: 'article', scope_id: 'article-b', title: 'B', created_at: null, updated_at: null },
      messages: [{ role: 'assistant', content: 'B reply', timestamp: null }],
    })
    await pendingB
    resolveA({
      thread: { id: 'thread-a', scope_kind: 'article', scope_id: 'article-a', title: 'A', created_at: null, updated_at: null },
      messages: [{ role: 'assistant', content: 'A late reply', timestamp: null }],
    })
    await pendingA

    expect(store.selectedThreadId).toBe('thread-b')
    expect(store.messages.map((message) => message.content)).toEqual(['B reply'])
  })

  it('does not expose an old article failure in the newly selected thread', async () => {
    let rejectChat!: (reason: unknown) => void
    vi.spyOn(aiApi, 'chat').mockImplementation(() => new Promise((_resolve, reject) => {
      rejectChat = reject
    }))
    const store = useAiStore()
    store.threads = [
      { id: 'thread-a', scope_kind: 'article', scope_id: 'article-a', title: 'A', created_at: null, updated_at: null },
      { id: 'thread-b', scope_kind: 'article', scope_id: 'article-b', title: 'B', created_at: null, updated_at: null },
    ]
    store.selectedThreadId = 'thread-a'

    const pending = store.sendMessage('A question', 'article', 'article-a', 'profile-a')
    store.selectThread('thread-b')
    rejectChat(new Error('A failed'))
    await expect(pending).rejects.toThrow('A failed')

    expect(store.error).toBeNull()
    expect(store.chatSending).toBe(false)
  })
})
