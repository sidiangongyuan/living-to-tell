import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { aiApi, type ArticleAiTaskRun, type ArticleAiTaskRunCreate } from '../../api/ai'
import { errorMessage, isHttpStatus } from '../../api/base'

const TERMINAL = new Set(['succeeded', 'failed', 'cancelled'])

export const useArticleTaskRunStore = defineStore('article-ai-task-run', () => {
  const run = ref<ArticleAiTaskRun | null>(null)
  const history = ref<ArticleAiTaskRun[]>([])
  const reconnectCount = ref(0)
  const statusError = ref('')
  const creating = ref(false)
  const loading = ref(false)
  const applying = ref(false)
  const draftSaving = ref(false)
  let timer: ReturnType<typeof setTimeout> | null = null
  let requestToken = 0

  const running = computed(() => Boolean(run.value && !TERMINAL.has(run.value.status)))

  function clearTimer() {
    if (timer !== null) globalThis.clearTimeout(timer)
    timer = null
  }

  function schedulePoll() {
    clearTimer()
    if (!run.value || TERMINAL.has(run.value.status)) return
    const delay = Math.min(5000, 1500 + reconnectCount.value * 700)
    timer = globalThis.setTimeout(() => void poll(), delay)
  }

  async function poll() {
    if (!run.value) return
    const runId = run.value.run_id
    const token = ++requestToken
    try {
      const next = await aiApi.getArticleTaskRun(runId)
      if (token !== requestToken || run.value?.run_id !== runId) return
      setRun(next)
      reconnectCount.value = 0
      statusError.value = ''
    } catch (e) {
      if (token !== requestToken || run.value?.run_id !== runId) return
      reconnectCount.value += 1
      statusError.value = isHttpStatus(e, 404)
        ? '后台任务已不存在，可能是应用已经重启或结果已清空。'
        : errorMessage(e)
      if (isHttpStatus(e, 404)) {
        clearTimer()
        return
      }
    }
    schedulePoll()
  }

  async function hydrate() {
    try {
      const [latest, runs] = await Promise.all([
        aiApi.getLatestArticleTaskRun(),
        aiApi.listArticleTaskRuns().catch(() => []),
      ])
      history.value = runs
      run.value = latest
      if (latest) setRun(latest)
      statusError.value = ''
      reconnectCount.value = 0
      schedulePoll()
    } catch (e) {
      statusError.value = errorMessage(e)
    }
  }

  async function open(runId: string) {
    const token = ++requestToken
    loading.value = true
    statusError.value = ''
    clearTimer()
    try {
      const next = await aiApi.getArticleTaskRun(runId)
      if (token !== requestToken) return null
      setRun(next)
      reconnectCount.value = 0
      schedulePoll()
      return next
    } catch (e) {
      if (token !== requestToken) return null
      run.value = null
      statusError.value = isHttpStatus(e, 404)
        ? '这轮 AI 修改结果已过期，可能是应用已经重启或历史已清空。'
        : errorMessage(e)
      return null
    } finally {
      if (token === requestToken) loading.value = false
    }
  }

  async function refreshHistory() {
    try {
      history.value = await aiApi.listArticleTaskRuns()
    } catch (e) {
      statusError.value = errorMessage(e)
    }
  }

  async function create(request: ArticleAiTaskRunCreate) {
    creating.value = true
    statusError.value = ''
    try {
      setRun(await aiApi.createArticleTaskRun(request))
      reconnectCount.value = 0
      schedulePoll()
      return run.value!
    } catch (e) {
      statusError.value = errorMessage(e)
      throw e
    } finally {
      creating.value = false
    }
  }

  async function cancel() {
    if (!run.value) return
    setRun(await aiApi.cancelArticleTaskRun(run.value.run_id))
    clearTimer()
  }

  async function apply(
    profileId: string,
    candidate: 'raw' | 'draft' = 'raw',
    expectedFingerprint?: string | null,
  ) {
    if (!run.value) throw new Error('没有可写回的文章 AI 任务。')
    applying.value = true
    statusError.value = ''
    try {
      const result = await aiApi.applyArticleTaskRun(
        run.value.run_id,
        profileId,
        candidate,
        expectedFingerprint,
      )
      setRun(result.run)
      return result
    } catch (e) {
      statusError.value = errorMessage(e)
      throw e
    } finally {
      applying.value = false
    }
  }

  async function saveDraft(profileId: string, value: string, expectedFingerprint?: string | null) {
    if (!run.value) throw new Error('没有可编辑的文章 AI 任务。')
    const runId = run.value.run_id
    draftSaving.value = true
    try {
      const next = await aiApi.saveArticleTaskDraft(runId, profileId, value, expectedFingerprint)
      if (run.value?.run_id === runId) setRun(next)
      return next
    } finally {
      draftSaving.value = false
    }
  }

  async function resetDraft(profileId: string) {
    if (!run.value) return
    setRun(await aiApi.resetArticleTaskDraft(run.value.run_id, profileId))
  }

  async function clear() {
    if (!run.value) return
    const runId = run.value.run_id
    await aiApi.clearArticleTaskRun(runId)
    history.value = history.value.filter((item) => item.run_id !== runId)
    run.value = null
    statusError.value = ''
    reconnectCount.value = 0
    requestToken += 1
    clearTimer()
  }

  async function clearHistory() {
    await aiApi.clearArticleTaskRunHistory()
    history.value = history.value.filter((item) => !TERMINAL.has(item.status))
    if (run.value && TERMINAL.has(run.value.status)) {
      run.value = null
      clearTimer()
    }
  }

  function setRun(next: ArticleAiTaskRun) {
    run.value = next
    const index = history.value.findIndex((item) => item.run_id === next.run_id)
    if (index >= 0) {
      history.value[index] = next
    } else {
      history.value = [next, ...history.value].slice(0, 20)
    }
    history.value.sort((left, right) => right.created_at.localeCompare(left.created_at))
  }

  return {
    run,
    history,
    running,
    reconnectCount,
    statusError,
    creating,
    loading,
    applying,
    draftSaving,
    hydrate,
    open,
    refreshHistory,
    create,
    poll,
    cancel,
    apply,
    saveDraft,
    resetDraft,
    clear,
    clearHistory,
  }
})
