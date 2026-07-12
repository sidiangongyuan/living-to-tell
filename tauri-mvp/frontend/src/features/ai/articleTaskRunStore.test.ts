import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { aiApi, type ArticleAiTaskRun, type ArticleAiTaskRunCreate } from '../../api/ai'
import { useArticleTaskRunStore } from './articleTaskRunStore'

function makeRun(status: ArticleAiTaskRun['status'] = 'running'): ArticleAiTaskRun {
  return {
    run_id: 'run-1',
    article_id: 'article-1',
    article_title: '测试文章',
    task_type: 'polish',
    article_hash: 'hash',
    original_text: '原文',
    selection_start: null,
    selection_end: null,
    status,
    stage: status === 'succeeded' ? 'succeeded' : 'waiting_model',
    stage_label: status === 'succeeded' ? '已完成' : '等待模型返回',
    error: '',
    profiles: [{ profile_id: 'profile-1', profile_name: '模型一', provider: 'fake', model: 'fake-model' }],
    results: [],
    created_at: '2026-07-12T00:00:00Z',
    started_at: '2026-07-12T00:00:00Z',
    updated_at: '2026-07-12T00:00:00Z',
    completed_at: status === 'succeeded' ? '2026-07-12T00:00:01Z' : null,
    elapsed_ms: status === 'succeeded' ? 1000 : 100,
    applied_profile_id: null,
    applied_at: null,
    applied_version_id: null,
  }
}

const request: ArticleAiTaskRunCreate = {
  article_id: 'article-1',
  task_type: 'polish',
  profile_ids: ['profile-1'],
}

describe('article AI task run store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('reconnects by querying the existing run without creating a duplicate provider request', async () => {
    vi.useFakeTimers()
    const create = vi.spyOn(aiApi, 'createArticleTaskRun').mockResolvedValue(makeRun())
    const get = vi.spyOn(aiApi, 'getArticleTaskRun')
      .mockRejectedValueOnce(new Error('临时无法查询状态'))
      .mockResolvedValueOnce(makeRun('succeeded'))
    const store = useArticleTaskRunStore()

    await store.create(request)
    await vi.advanceTimersByTimeAsync(1500)
    expect(store.reconnectCount).toBe(1)
    expect(create).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(2200)
    expect(get).toHaveBeenCalledTimes(2)
    expect(create).toHaveBeenCalledTimes(1)
    expect(store.run?.status).toBe('succeeded')
    expect(store.reconnectCount).toBe(0)
  })

  it('keeps a safe write-back error visible and always releases the applying state', async () => {
    const apply = vi.spyOn(aiApi, 'applyArticleTaskRun').mockRejectedValue(new Error('文章已经变化，请重新运行。'))
    const store = useArticleTaskRunStore()
    store.run = makeRun('succeeded')

    await expect(store.apply('profile-1')).rejects.toThrow('文章已经变化')

    expect(apply).toHaveBeenCalledWith('run-1', 'profile-1')
    expect(store.applying).toBe(false)
    expect(store.statusError).toBe('文章已经变化，请重新运行。')
  })
})
