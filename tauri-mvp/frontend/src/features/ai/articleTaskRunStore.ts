import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { aiApi, type ArticleAiTaskRun, type ArticleAiTaskRunCreate } from '../../api/ai'
import { errorMessage, isHttpStatus } from '../../api/base'

const TERMINAL = new Set(['succeeded', 'failed', 'cancelled'])

export const useArticleTaskRunStore = defineStore('article-ai-task-run', () => {
  const run = ref<ArticleAiTaskRun | null>(null)
  const reconnectCount = ref(0)
  const statusError = ref('')
  const creating = ref(false)
  const applying = ref(false)
  let timer: ReturnType<typeof setTimeout> | null = null

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
    try {
      run.value = await aiApi.getArticleTaskRun(run.value.run_id)
      reconnectCount.value = 0
      statusError.value = ''
    } catch (e) {
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
      run.value = await aiApi.getLatestArticleTaskRun()
      statusError.value = ''
      reconnectCount.value = 0
      schedulePoll()
    } catch (e) {
      statusError.value = errorMessage(e)
    }
  }

  async function create(request: ArticleAiTaskRunCreate) {
    creating.value = true
    statusError.value = ''
    try {
      run.value = await aiApi.createArticleTaskRun(request)
      reconnectCount.value = 0
      schedulePoll()
      return run.value
    } catch (e) {
      statusError.value = errorMessage(e)
      throw e
    } finally {
      creating.value = false
    }
  }

  async function cancel() {
    if (!run.value) return
    run.value = await aiApi.cancelArticleTaskRun(run.value.run_id)
    clearTimer()
  }

  async function apply(profileId: string) {
    if (!run.value) throw new Error('没有可写回的文章 AI 任务。')
    applying.value = true
    statusError.value = ''
    try {
      const result = await aiApi.applyArticleTaskRun(run.value.run_id, profileId)
      run.value = result.run
      return result
    } catch (e) {
      statusError.value = errorMessage(e)
      throw e
    } finally {
      applying.value = false
    }
  }

  async function clear() {
    if (!run.value) return
    await aiApi.clearArticleTaskRun(run.value.run_id)
    run.value = null
    statusError.value = ''
    reconnectCount.value = 0
    clearTimer()
  }

  return {
    run,
    running,
    reconnectCount,
    statusError,
    creating,
    applying,
    hydrate,
    create,
    poll,
    cancel,
    apply,
    clear,
  }
})
