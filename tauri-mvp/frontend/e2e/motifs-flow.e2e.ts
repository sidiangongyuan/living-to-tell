import { expect, test, type Page } from '@playwright/test'

const article = {
  id: 'article-a',
  title: '花园',
  body: '第一段。\n\n玫瑰在夜里像血一样醒着。\n\n最后一段。',
  entry_type: 'fragment',
  created_at: null,
  updated_at: null,
  tags: [],
  archived_at: null,
  curation_status: 'active',
}

const articleB = {
  ...article,
  id: 'article-b',
  title: '另一篇',
  body: '另一篇正文。',
}

const reference = {
  id: 'ref-a',
  source_title: '夜航西飞',
  content: '天空像一块被擦亮的黑石。',
  source_author: '柏瑞尔·马卡姆',
  tags: [],
  kind: 'excerpt',
  usage_kind: 'imagery',
  personal_note: '',
  created_at: null,
  updated_at: null,
}

interface MotifNode {
  id: string
  name: string
  aliases: string[]
  note: string
  profile: {
    definition: string
    core_tension: string
    writing_functions: string[]
    scene_triggers: string[]
    character_signals: string[]
    imagery_translations: string[]
    short_examples: string[]
    misuse_warnings: string[]
    micro_exercises: string[]
    source_hints: Array<{ title: string; url?: string | null; note: string }>
  }
  tags: string[]
  pinned: boolean
  excerpt_count: number
  created_at: string | null
  updated_at: string | null
}

interface MotifExcerpt {
  id: string
  source_kind: 'article' | 'reference'
  source_id: string
  source_title_snapshot: string
  excerpt_text: string
  note: string
  selection_start: number | null
  selection_end: number | null
  before_context: string
  after_context: string
  motif_ids: string[]
  motif_names: string[]
  source_exists: boolean
  source_current_title: string
  created_at: string | null
  updated_at: string | null
}

type SourceKind = 'article' | 'reference'

function normalizeMotifName(name: string): string {
  return name.trim().toLowerCase()
}

function emptyMotifProfile(): MotifNode['profile'] {
  return {
    definition: '',
    core_tension: '',
    writing_functions: [],
    scene_triggers: [],
    character_signals: [],
    imagery_translations: [],
    short_examples: [],
    misuse_warnings: [],
    micro_exercises: [],
    source_hints: [],
  }
}

function uniqueNames(names: string[]): string[] {
  const result: string[] = []
  for (const name of names) {
    const clean = name.trim()
    if (clean && !result.some((item) => item.toLowerCase() === clean.toLowerCase())) {
      result.push(clean)
    }
  }
  return result
}

function graphFrom(motifs: MotifNode[], excerpts: MotifExcerpt[]) {
  const nodes = motifs.map((motif) => ({
    id: motif.id,
    name: motif.name,
    excerpt_count: excerpts.filter((excerpt) => excerpt.motif_ids.includes(motif.id)).length,
    pinned: motif.pinned,
    is_center: false,
  }))
  const edges = []
  for (let i = 0; i < motifs.length; i += 1) {
    for (let j = i + 1; j < motifs.length; j += 1) {
      const a = motifs[i]
      const b = motifs[j]
      const sharedExcerpts = excerpts.filter((excerpt) =>
        excerpt.motif_ids.includes(a.id) && excerpt.motif_ids.includes(b.id)
      ).length
      const sourceKeys = new Set(
        excerpts
          .filter((excerpt) => excerpt.motif_ids.includes(a.id))
          .map((excerpt) => `${excerpt.source_kind}:${excerpt.source_id}`)
      )
      const sharedSources = excerpts
        .filter((excerpt) => excerpt.motif_ids.includes(b.id))
        .filter((excerpt) => sourceKeys.has(`${excerpt.source_kind}:${excerpt.source_id}`))
        .length
      if (sharedExcerpts || sharedSources) {
        edges.push({
          source_id: a.id,
          target_id: b.id,
          weight: sharedExcerpts * 2 + sharedSources,
          shared_excerpts: sharedExcerpts,
          shared_sources: sharedSources,
        })
      }
    }
  }
  return { nodes, edges }
}

async function mockMotifFlowApi(page: Page) {
  const articlesById: Record<string, typeof article> = {
    [article.id]: { ...article },
    [articleB.id]: { ...articleB },
  }
  const referencesById: Record<string, typeof reference> = {
    [reference.id]: { ...reference },
  }
  let motifs: MotifNode[] = []
  let excerpts: MotifExcerpt[] = []
  let enrichmentDraftCalls = 0
  const enrichmentJobs = new Map<string, Record<string, unknown> & { polls_remaining?: number }>()

  await page.route('**/api/app/version', async (route) => {
    await route.fulfill({
      json: {
        app_name: 'Living to Tell',
        version: '0.1.13',
        api_version: '2.0.0',
        capabilities: ['data_location', 'ai_chat_settings', 'ai_task_presets', 'update_check', 'ai_jobs', 'motif_ai_enrichment_jobs'],
      },
    })
  })
  await page.route('**/api/app/update-check*', async (route) => {
    await route.fulfill({
      json: {
        current_version: '0.1.13',
        latest_version: '0.1.13',
        latest_tag: 'living-to-tell-v0.1.13',
        release_name: 'Living to Tell Preview 0.1.13',
        release_url: 'https://github.com/sidiangongyuan/living-to-tell/releases/tag/living-to-tell-v0.1.13',
        published_at: '2026-06-25T03:03:04Z',
        release_notes: '',
        source: 'github_releases_latest',
        status: 'up_to_date',
        message: '当前已是最新版本。',
        checked_at: '2026-06-25T03:05:06Z',
        cached: false,
        download_url: 'https://github.com/sidiangongyuan/living-to-tell/releases/download/living-to-tell-v0.1.13/LivingToTell_0.1.13_x64-setup.exe',
        download_name: 'LivingToTell_0.1.13_x64-setup.exe',
      },
    })
  })

  function getSourceText(sourceKind: SourceKind, sourceId: string) {
    return sourceKind === 'article'
      ? articlesById[sourceId]?.body ?? ''
      : referencesById[sourceId]?.content ?? ''
  }

  function getSourceTitle(sourceKind: SourceKind, sourceId: string) {
    return sourceKind === 'article'
      ? articlesById[sourceId]?.title ?? ''
      : referencesById[sourceId]?.source_title ?? ''
  }

  function allExactRanges(sourceText: string, excerptText: string): Array<[number, number]> {
    const cleanText = excerptText.trim()
    if (!sourceText || !cleanText) return []
    const ranges: Array<[number, number]> = []
    let start = 0
    while (start <= sourceText.length) {
      const found = sourceText.indexOf(cleanText, start)
      if (found < 0) break
      ranges.push([found, found + cleanText.length])
      start = found + Math.max(1, cleanText.length)
    }
    return ranges
  }

  function commonSuffixLength(left: string, right: string, limit = 90) {
    const leftTail = left.slice(-limit)
    const rightTail = right.slice(-limit)
    const total = Math.min(leftTail.length, rightTail.length)
    for (let size = total; size > 0; size -= 1) {
      if (leftTail.slice(-size) === rightTail.slice(-size)) return size
    }
    return 0
  }

  function commonPrefixLength(left: string, right: string, limit = 90) {
    const leftHead = left.slice(0, limit)
    const rightHead = right.slice(0, limit)
    const total = Math.min(leftHead.length, rightHead.length)
    for (let size = total; size > 0; size -= 1) {
      if (leftHead.slice(0, size) === rightHead.slice(0, size)) return size
    }
    return 0
  }

  function contextsForRange(sourceText: string, start: number, end: number): [string, string] {
    return [
      sourceText.slice(Math.max(0, start - 90), start),
      sourceText.slice(end, Math.min(sourceText.length, end + 90)),
    ]
  }

  function resolveCurrentRange(
    sourceText: string,
    excerptText: string,
    selectionStart?: number | null,
    selectionEnd?: number | null,
    beforeContext = '',
    afterContext = '',
    fallbackStart?: number | null,
  ): [number, number] | null {
    const cleanText = excerptText.trim()
    if (!sourceText || !cleanText) return null
    if (selectionStart != null && selectionEnd != null) {
      const safeStart = Math.max(0, Math.min(selectionStart, sourceText.length))
      const safeEnd = Math.max(safeStart, Math.min(selectionEnd, sourceText.length))
      if (sourceText.slice(safeStart, safeEnd).trim() === cleanText) return [safeStart, safeEnd]
    }
    const ranges = allExactRanges(sourceText, cleanText)
    if (!ranges.length) return null
    if (ranges.length === 1) return ranges[0]
    const scored = ranges
      .map(([start, end]) => {
        const [actualBefore, actualAfter] = contextsForRange(sourceText, start, end)
        let contextScore = 0
        if (beforeContext) contextScore += commonSuffixLength(actualBefore, beforeContext)
        if (afterContext) contextScore += commonPrefixLength(actualAfter, afterContext)
        let score = contextScore * 1000
        if (fallbackStart != null) score -= Math.min(Math.abs(start - fallbackStart), 1000)
        return { score, start, end }
      })
      .sort((a, b) => b.score - a.score)
    if (!scored.length || scored[0].score <= 0) return null
    if (scored.length > 1 && scored[0].score === scored[1].score) return null
    return [scored[0].start, scored[0].end]
  }

  function refreshMotifCounts() {
    motifs = motifs.map((motif) => ({
      ...motif,
      excerpt_count: excerpts.filter((excerpt) => excerpt.motif_ids.includes(motif.id)).length,
    }))
  }

  function ensureMotif(name: string): MotifNode {
    const existing = motifs.find((motif) => motif.name === name)
    if (existing) return existing
    const motif = {
      id: `motif-${motifs.length + 1}`,
      name,
      aliases: [],
      note: '',
      profile: emptyMotifProfile(),
      tags: [],
      pinned: false,
      excerpt_count: 0,
      created_at: null,
      updated_at: null,
    }
    motifs = [motif, ...motifs]
    return motif
  }

  function mergeExcerpts(
    candidates: MotifExcerpt[],
    selectionRange: [number, number] | null,
    beforeContext = '',
    afterContext = '',
  ): MotifExcerpt {
    const canonical = candidates.reduce((earliest, item) => {
      const earliestIndex = excerpts.findIndex((excerpt) => excerpt.id === earliest.id)
      const itemIndex = excerpts.findIndex((excerpt) => excerpt.id === item.id)
      return itemIndex >= 0 && itemIndex < earliestIndex ? item : earliest
    }, candidates[0])
    for (const item of candidates) {
      if (item.id === canonical.id) continue
      canonical.motif_ids = uniqueNames([...canonical.motif_ids, ...item.motif_ids])
      canonical.motif_names = uniqueNames([...canonical.motif_names, ...item.motif_names]).sort()
      if (item.note.trim() && !canonical.note.includes(item.note.trim())) {
        canonical.note = [canonical.note, item.note].filter((note) => note.trim()).join('\n\n')
      }
    }
    if (selectionRange) {
      canonical.selection_start = selectionRange[0]
      canonical.selection_end = selectionRange[1]
    }
    if (beforeContext) canonical.before_context = beforeContext
    if (afterContext) canonical.after_context = afterContext
    excerpts = excerpts.filter((excerpt) => excerpt.id === canonical.id || !candidates.some((item) => item.id === excerpt.id))
    refreshMotifCounts()
    return canonical
  }

  function repairSourceExcerpts(sourceKind: SourceKind, sourceId: string) {
    const sourceText = getSourceText(sourceKind, sourceId)
    const groups = new Map<string, MotifExcerpt[]>()
    for (const excerpt of excerpts.filter((item) => item.source_kind === sourceKind && item.source_id === sourceId)) {
      const range = resolveCurrentRange(
        sourceText,
        excerpt.excerpt_text,
        excerpt.selection_start,
        excerpt.selection_end,
        excerpt.before_context,
        excerpt.after_context,
        excerpt.selection_start,
      )
      if (!range) continue
      const [beforeContext, afterContext] = contextsForRange(sourceText, range[0], range[1])
      excerpt.selection_start = range[0]
      excerpt.selection_end = range[1]
      excerpt.before_context = beforeContext
      excerpt.after_context = afterContext
      const key = `${range[0]}:${range[1]}:${excerpt.excerpt_text.trim()}`
      groups.set(key, [...(groups.get(key) ?? []), excerpt])
    }
    for (const candidates of groups.values()) {
      if (candidates.length > 1) {
        const first = candidates[0]
        mergeExcerpts(candidates, [first.selection_start ?? 0, first.selection_end ?? 0], first.before_context, first.after_context)
      }
    }
  }

  function findExcerptForSelection(input: {
    source_kind: SourceKind
    source_id: string
    excerpt_text?: string
    selection_start?: number | null
    selection_end?: number | null
    before_context?: string
    after_context?: string
  }): MotifExcerpt | undefined {
    const cleanText = input.excerpt_text?.trim()
    if (!cleanText) return undefined
    const sourceText = getSourceText(input.source_kind, input.source_id)
    const requestedRange = resolveCurrentRange(
      sourceText,
      cleanText,
      input.selection_start,
      input.selection_end,
      input.before_context ?? '',
      input.after_context ?? '',
      input.selection_start,
    )
    const sameText = excerpts.filter((excerpt) =>
      excerpt.source_kind === input.source_kind &&
      excerpt.source_id === input.source_id &&
      excerpt.excerpt_text.trim() === cleanText
    )
    const rowRanges = new Map(
      sameText.map((excerpt) => [
        excerpt.id,
        resolveCurrentRange(
          sourceText,
          excerpt.excerpt_text,
          excerpt.selection_start,
          excerpt.selection_end,
          excerpt.before_context,
          excerpt.after_context,
          excerpt.selection_start,
        ),
      ]),
    )
    let candidates: MotifExcerpt[] = []
    if (requestedRange) {
      candidates = sameText.filter((excerpt) => {
        const range = rowRanges.get(excerpt.id)
        return Boolean(range && range[0] === requestedRange[0] && range[1] === requestedRange[1])
      })
      if (!candidates.length && sameText.length === 1 && allExactRanges(sourceText, cleanText).length <= 1) {
        candidates = sameText
      }
    } else if (sameText.length === 1 && allExactRanges(sourceText, cleanText).length <= 1) {
      candidates = sameText
    }
    if (!candidates.length) return undefined
    return mergeExcerpts(candidates, requestedRange ?? rowRanges.get(candidates[0].id) ?? null, input.before_context ?? '', input.after_context ?? '')
  }

  await page.addInitScript(() => {
    window.localStorage.clear()
    ;(window as Window & { __WRITER_DISABLE_AUTO_UPDATE__?: boolean }).__WRITER_DISABLE_AUTO_UPDATE__ = true
  })

  await page.route(/\/api\/app\/version$/, async (route) => {
    await route.fulfill({
      json: {
        app_name: 'Living to Tell',
        version: '0.1.13',
        api_version: '2.0.0',
        capabilities: ['motif_star_map', 'ai_jobs', 'motif_ai_enrichment_jobs'],
      },
    })
  })
  await page.route(/\/api\/settings\/ai\/profiles$/, async (route) => {
    await route.fulfill({ json: { profiles: [] } })
  })
  function makeEnrichmentDraft(concept: string, suffix: string) {
    return {
      title: `${concept}短卡 ${suffix}`,
      concept,
      aliases: [`${concept}别名`, 'das Man'],
      tags: ['哲学概念', `测试标签${suffix}`],
      note: `【一句话定义】\n定义 ${suffix}\n\n【核心张力】\n张力 ${suffix}\n\n【写作功能】\n- 功能 ${suffix}\n\n【场景触发】\n- 场景 ${suffix}\n\n【人物表现】\n- 表现 ${suffix}\n\n【意象转译】\n- 转译 ${suffix}\n\n【短例子】\n- 例子 ${suffix}\n\n【关联建议】\n建议 ${suffix}\n\n【误用提醒】\n- 提醒 ${suffix}\n\n【微练习】\n- 练习 ${suffix}\n\n【来源线索（需核对）】\n- 需核对。`,
      profile: {
        definition: `定义 ${suffix}`,
        core_tension: `张力 ${suffix}`,
        writing_functions: [`功能 ${suffix}`],
        scene_triggers: [`场景 ${suffix}`],
        character_signals: [`表现 ${suffix}`],
        imagery_translations: [`转译 ${suffix}`],
        short_examples: [`例子 ${suffix}`],
        misuse_warnings: [`提醒 ${suffix}`],
        micro_exercises: [`练习 ${suffix}`],
        source_hints: [{ title: '测试来源线索', url: null, note: '需核对。' }],
      },
      related_suggestions: ['建议一', '建议二'],
      source_hints: [{ title: '测试来源线索', url: null, note: '需核对。' }],
      reference_candidates: Array.from({ length: 18 }, (_, index) => ({
        text: `第 ${index + 1} 条候选句：这是一段很长的相关句子，用来验证小窗口中候选卡片是否能换行、滚动，并且不会遮挡底部操作按钮。`,
        source_author: `测试作者${index + 1}`,
        source_title: `测试书名${index + 1}：一个非常长的副标题用于验证断行`,
        source_note: 'AI 候选，来源需人工核对。',
        reason: '用于验证候选句卡片在紧凑窗口内仍然可读。',
      })),
      provider: 'fake',
      model: 'fake-model',
      transport: 'fake',
      elapsed_ms: 120 + enrichmentDraftCalls,
    }
  }

  function makeEnrichmentJob(
    jobId: string,
    body: { concept?: string; motif_id?: string | null; profile_id?: string },
    result: ReturnType<typeof makeEnrichmentDraft> | null,
    status = result ? 'succeeded' : 'waiting_model',
  ) {
    const now = new Date().toISOString()
    const concept = body.concept?.trim() || '测试概念'
    return {
      job_id: jobId,
      kind: 'motif_enrichment',
      status,
      stage: status,
      stage_label: status === 'succeeded' ? '已完成' : '已发送请求，等待模型返回',
      concept,
      motif_id: body.motif_id ?? null,
      profile_id: body.profile_id ?? 'default',
      started_at: now,
      updated_at: now,
      elapsed_ms: status === 'succeeded' ? result?.elapsed_ms ?? 120 : 0,
      result,
      error: '',
      provider: result?.provider ?? null,
      model: result?.model ?? null,
      transport: result?.transport ?? null,
    }
  }

  await page.route(/\/api\/ai\/jobs(?:\/|\?|$)/, async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname

    if (path === '/api/ai/jobs/motif-enrichment' && request.method() === 'POST') {
      enrichmentDraftCalls += 1
      const body = request.postDataJSON() as { concept?: string; motif_id?: string | null; profile_id?: string }
      const concept = body.concept?.trim() || '测试概念'
      const suffix = enrichmentDraftCalls === 1 ? 'A' : 'B'
      const shouldDelay = enrichmentDraftCalls === 2 || concept.includes('慢任务')
      const jobId = `job-${enrichmentDraftCalls}`
      const draft = makeEnrichmentDraft(concept, suffix)
      const job = shouldDelay
        ? { ...makeEnrichmentJob(jobId, body, null, 'waiting_model'), polls_remaining: concept.includes('慢任务') ? 20 : 1, result_after_wait: draft }
        : makeEnrichmentJob(jobId, body, draft)
      enrichmentJobs.set(jobId, job)
      await route.fulfill({ json: job })
      return
    }

    const cancelMatch = path.match(/^\/api\/ai\/jobs\/([^/]+)\/cancel$/)
    if (cancelMatch && request.method() === 'POST') {
      const job = enrichmentJobs.get(cancelMatch[1])
      if (!job) {
        await route.fulfill({ status: 404, json: { detail: '后台任务已不存在，可能是应用重启或任务已过期。' } })
        return
      }
      Object.assign(job, {
        status: 'cancelled',
        stage: 'cancelled',
        stage_label: '已中断',
        error: '已停止本地等待。若请求已经发给服务商，远端仍可能完成并计费。',
        updated_at: new Date().toISOString(),
      })
      await route.fulfill({ json: job })
      return
    }

    const jobMatch = path.match(/^\/api\/ai\/jobs\/([^/]+)$/)
    if (jobMatch && request.method() === 'GET') {
      const job = enrichmentJobs.get(jobMatch[1])
      if (!job) {
        await route.fulfill({ status: 404, json: { detail: '后台任务已不存在，可能是应用重启或任务已过期。' } })
        return
      }
      if (job.status === 'waiting_model' && typeof job.polls_remaining === 'number') {
        if (job.polls_remaining <= 0) {
          const result = job.result_after_wait as ReturnType<typeof makeEnrichmentDraft>
          Object.assign(job, {
            status: 'succeeded',
            stage: 'succeeded',
            stage_label: '已完成',
            result,
            provider: result.provider,
            model: result.model,
            transport: result.transport,
            elapsed_ms: result.elapsed_ms,
            updated_at: new Date().toISOString(),
          })
        } else {
          job.polls_remaining -= 1
          job.elapsed_ms = 1500
          job.updated_at = new Date().toISOString()
        }
      }
      await route.fulfill({ json: job })
      return
    }

    await route.fulfill({ status: 404, json: { detail: 'Not Found' } })
  })
  await page.route(/\/api\/dates\//, async (route) => route.fulfill({ json: [] }))
  await page.route(/\/api\/collections\/for-entry\//, async (route) => route.fulfill({ json: [] }))
  await page.route(/\/api\/articles(?:\/|\?|$)/, async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    if (/^\/api\/articles\/[^/]+\/notes(?:\/|\?|$)/.test(url.pathname)) {
      await route.fulfill({ json: [] })
      return
    }
    if (url.pathname === '/api/articles') {
      await route.fulfill({ json: Object.values(articlesById) })
      return
    }
    if (url.pathname === '/api/articles/search') {
      await route.fulfill({ json: [] })
      return
    }
    if (request.method() === 'PUT') {
      const body = request.postDataJSON() as Record<string, unknown>
      const id = url.pathname.split('/').pop() || article.id
      articlesById[id] = { ...(articlesById[id] ?? article), ...body }
      await route.fulfill({ json: articlesById[id] })
      return
    }
    const id = url.pathname.split('/').pop()
    await route.fulfill({ json: articlesById[id ?? article.id] ?? articlesById[article.id] })
  })

  await page.route(/\/api\/library\/stats$/, async (route) => route.fulfill({ json: { total: 1, by_usage_kind: { imagery: 1 } } }))
  await page.route(/\/api\/library\/references/, async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    if (url.pathname === '/api/library/references') {
      await route.fulfill({ json: Object.values(referencesById) })
      return
    }
    if (url.pathname === '/api/library/references/search') {
      await route.fulfill({ json: Object.values(referencesById) })
      return
    }
    if (request.method() === 'PUT') {
      const id = url.pathname.split('/').pop() || reference.id
      referencesById[id] = { ...(referencesById[id] ?? reference), ...(request.postDataJSON() as object) }
      await route.fulfill({ json: referencesById[id] })
      return
    }
    const id = url.pathname.split('/').pop()
    await route.fulfill({ json: referencesById[id ?? reference.id] ?? referencesById[reference.id] })
  })

  await page.route(/\/__e2e\/motifs\/seed-drift-duplicate$/, async (route) => {
    const body = route.request().postDataJSON() as {
      source_kind: SourceKind
      source_id: string
      excerpt_text: string
      current_start: number
      current_end: number
      motif_names: string[]
    }
    const sourceText = getSourceText(body.source_kind, body.source_id)
    const linkedMotifs = body.motif_names.map((name) => ensureMotif(name))
    const [beforeContext, afterContext] = contextsForRange(sourceText, body.current_start, body.current_end)
    excerpts = [
      {
        id: 'excerpt-drift-stale',
        source_kind: body.source_kind,
        source_id: body.source_id,
        source_title_snapshot: getSourceTitle(body.source_kind, body.source_id),
        excerpt_text: body.excerpt_text,
        note: '旧位置记录',
        selection_start: Math.max(0, body.current_start - 12),
        selection_end: Math.max(0, body.current_end - 12),
        before_context: '',
        after_context: '',
        motif_ids: [linkedMotifs[0].id],
        motif_names: [linkedMotifs[0].name],
        source_exists: true,
        source_current_title: getSourceTitle(body.source_kind, body.source_id),
        created_at: null,
        updated_at: null,
      },
      {
        id: 'excerpt-drift-current',
        source_kind: body.source_kind,
        source_id: body.source_id,
        source_title_snapshot: getSourceTitle(body.source_kind, body.source_id),
        excerpt_text: body.excerpt_text,
        note: '当前位置记录',
        selection_start: body.current_start,
        selection_end: body.current_end,
        before_context: beforeContext,
        after_context: afterContext,
        motif_ids: [linkedMotifs[1].id],
        motif_names: [linkedMotifs[1].name],
        source_exists: true,
        source_current_title: getSourceTitle(body.source_kind, body.source_id),
        created_at: null,
        updated_at: null,
      },
      ...excerpts,
    ]
    refreshMotifCounts()
    await route.fulfill({ json: { ok: true } })
  })

  await page.route(/\/api\/motifs(?:\/|\?|$)/, async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname

    if (path === '/api/motifs' && request.method() === 'GET') {
      await route.fulfill({ json: motifs })
      return
    }

    if (path === '/api/motifs' && request.method() === 'POST') {
      const body = request.postDataJSON() as Partial<MotifNode> & { name?: string }
      const name = body.name?.trim() || '未命名意象'
      const existing = motifs.find((motif) => normalizeMotifName(motif.name) === normalizeMotifName(name))
      if (existing) {
        await route.fulfill({ status: 400, json: { detail: 'Motif name already exists' } })
        return
      }
      const motif = {
        id: `motif-${motifs.length + 1}`,
        name,
        aliases: body.aliases ?? [],
        note: body.note ?? '',
        profile: body.profile ?? emptyMotifProfile(),
        tags: body.tags ?? [],
        pinned: body.pinned ?? false,
        excerpt_count: 0,
        created_at: null,
        updated_at: null,
      }
      motifs = [motif, ...motifs]
      await route.fulfill({ status: 201, json: motif })
      return
    }

    if (path === '/api/motifs/graph') {
      await route.fulfill({ json: graphFrom(motifs, excerpts) })
      return
    }

    if (path === '/api/motifs/enrich-draft' && request.method() === 'POST') {
      enrichmentDraftCalls += 1
      const body = request.postDataJSON() as { concept?: string }
      const concept = body.concept?.trim() || '测试概念'
      if (enrichmentDraftCalls === 2) {
        await new Promise((resolve) => setTimeout(resolve, 350))
      }
      const suffix = enrichmentDraftCalls === 1 ? 'A' : 'B'
      await route.fulfill({
        json: {
          title: `${concept}短卡 ${suffix}`,
          concept,
          aliases: [`${concept}别名`, 'das Man'],
          tags: ['哲学概念', `测试标签${suffix}`],
          note: `【一句话定义】\n定义 ${suffix}\n\n【核心张力】\n张力 ${suffix}\n\n【写作功能】\n- 功能 ${suffix}\n\n【场景触发】\n- 场景 ${suffix}\n\n【人物表现】\n- 表现 ${suffix}\n\n【意象转译】\n- 转译 ${suffix}\n\n【短例子】\n- 例子 ${suffix}\n\n【关联建议】\n建议 ${suffix}\n\n【误用提醒】\n- 提醒 ${suffix}\n\n【微练习】\n- 练习 ${suffix}\n\n【来源线索（需核对）】\n- 需核对。`,
          profile: {
            definition: `定义 ${suffix}`,
            core_tension: `张力 ${suffix}`,
            writing_functions: [`功能 ${suffix}`],
            scene_triggers: [`场景 ${suffix}`],
            character_signals: [`表现 ${suffix}`],
            imagery_translations: [`转译 ${suffix}`],
            short_examples: [`例子 ${suffix}`],
            misuse_warnings: [`提醒 ${suffix}`],
            micro_exercises: [`练习 ${suffix}`],
            source_hints: [{ title: '测试来源线索', url: null, note: '需核对。' }],
          },
          related_suggestions: ['建议一', '建议二'],
          source_hints: [{ title: '测试来源线索', url: null, note: '需核对。' }],
          reference_candidates: Array.from({ length: 18 }, (_, index) => ({
            text: `第 ${index + 1} 条候选句：这是一段很长的相关句子，用来验证小窗口中候选卡片是否能换行、滚动，并且不会遮挡底部操作按钮。`,
            source_author: `测试作者${index + 1}`,
            source_title: `测试书名${index + 1}：一个非常长的副标题用于验证断行`,
            source_note: 'AI 候选，来源需人工核对。',
            reason: '用于验证候选句卡片在紧凑窗口内仍然可读。',
          })),
          provider: 'fake',
          model: 'fake-model',
          transport: 'fake',
          elapsed_ms: 120 + enrichmentDraftCalls,
        },
      })
      return
    }

    const motifNodeMatch = path.match(/^\/api\/motifs\/([^/]+)$/)
    if (motifNodeMatch && request.method() === 'GET') {
      const motif = motifs.find((item) => item.id === motifNodeMatch[1])
      await route.fulfill(motif ? { json: motif } : { status: 404, json: { detail: 'Motif not found' } })
      return
    }

    if (motifNodeMatch && request.method() === 'PUT') {
      const motif = motifs.find((item) => item.id === motifNodeMatch[1])
      if (!motif) {
        await route.fulfill({ status: 404, json: { detail: 'Motif not found' } })
        return
      }
      const body = request.postDataJSON() as Partial<MotifNode>
      const nextName = body.name ?? motif.name
      const duplicate = motifs.find((item) =>
        item.id !== motif.id && normalizeMotifName(item.name) === normalizeMotifName(nextName)
      )
      if (duplicate) {
        await route.fulfill({ status: 400, json: { detail: 'Motif name already exists' } })
        return
      }
      Object.assign(motif, {
        name: nextName,
        aliases: body.aliases ?? motif.aliases,
        note: body.note ?? motif.note,
        profile: body.profile ?? motif.profile,
        tags: body.tags ?? motif.tags,
        pinned: body.pinned ?? motif.pinned,
      })
      await route.fulfill({ json: motif })
      return
    }

    const sourceExcerptsMatch = path.match(/^\/api\/motifs\/excerpts\/source\/([^/]+)\/([^/]+)$/)
    if (sourceExcerptsMatch && request.method() === 'GET') {
      const [, sourceKind, sourceId] = sourceExcerptsMatch
      repairSourceExcerpts(sourceKind as SourceKind, decodeURIComponent(sourceId))
      await route.fulfill({
        json: excerpts
          .filter((excerpt) => excerpt.source_kind === sourceKind && excerpt.source_id === decodeURIComponent(sourceId))
          .sort((a, b) => (a.selection_start ?? Number.MAX_SAFE_INTEGER) - (b.selection_start ?? Number.MAX_SAFE_INTEGER)),
      })
      return
    }

    if (path === '/api/motifs/excerpts/lookup' && request.method() === 'POST') {
      const found = findExcerptForSelection(request.postDataJSON() as {
        source_kind: SourceKind
        source_id: string
        excerpt_text?: string
        selection_start?: number | null
        selection_end?: number | null
        before_context?: string
        after_context?: string
      })
      if (!found) {
        await route.fulfill({ status: 404, json: { detail: 'Motif excerpt not found' } })
        return
      }
      await route.fulfill({ json: found })
      return
    }

    if (path === '/api/motifs/excerpts' && request.method() === 'POST') {
      const body = request.postDataJSON() as {
        source_kind: SourceKind
        source_id: string
        source_title_snapshot?: string
        excerpt_text: string
        note?: string
        selection_start?: number
        selection_end?: number
        before_context?: string
        after_context?: string
        motif_ids?: string[]
        motif_names?: string[]
      }
      const names = uniqueNames(body.motif_names ?? [])
      const linkedById = uniqueNames(body.motif_ids ?? [])
        .map((id) => motifs.find((motif) => motif.id === id))
        .filter((motif): motif is MotifNode => Boolean(motif))
      const linkedByName = names.map((name) => ensureMotif(name))
      const linkedMotifs = [...linkedById]
      for (const motif of linkedByName) {
        if (!linkedMotifs.some((item) => item.id === motif.id)) linkedMotifs.push(motif)
      }
      const sourceTitle = getSourceTitle(body.source_kind, body.source_id)
      const existing = findExcerptForSelection(body)
      if (existing) {
        existing.motif_ids = uniqueNames([...existing.motif_ids, ...linkedMotifs.map((motif) => motif.id)])
        existing.motif_names = uniqueNames([...existing.motif_names, ...linkedMotifs.map((motif) => motif.name)]).sort()
        if (body.note?.trim()) existing.note = body.note
        refreshMotifCounts()
        await route.fulfill({ status: 201, json: existing })
        return
      }
      const excerpt = {
        id: `excerpt-${excerpts.length + 1}`,
        source_kind: body.source_kind,
        source_id: body.source_id,
        source_title_snapshot: body.source_title_snapshot || sourceTitle,
        excerpt_text: body.excerpt_text,
        note: body.note ?? '',
        selection_start: body.selection_start ?? null,
        selection_end: body.selection_end ?? null,
        before_context: body.before_context ?? '',
        after_context: body.after_context ?? '',
        motif_ids: linkedMotifs.map((motif) => motif.id),
        motif_names: linkedMotifs.map((motif) => motif.name).sort(),
        source_exists: true,
        source_current_title: sourceTitle,
        created_at: null,
        updated_at: null,
      }
      excerpts = [excerpt, ...excerpts]
      refreshMotifCounts()
      await route.fulfill({ status: 201, json: excerpt })
      return
    }

    const addMotifsMatch = path.match(/^\/api\/motifs\/excerpts\/([^/]+)\/motifs$/)
    if (addMotifsMatch && request.method() === 'POST') {
      const excerpt = excerpts.find((item) => item.id === addMotifsMatch[1])
      if (!excerpt) {
        await route.fulfill({ status: 404, json: { detail: 'Motif excerpt not found' } })
        return
      }
      const body = request.postDataJSON() as { motif_names?: string[]; note?: string }
      const linkedMotifs = uniqueNames(body.motif_names ?? []).map((name) => ensureMotif(name))
      excerpt.motif_ids = uniqueNames([...excerpt.motif_ids, ...linkedMotifs.map((motif) => motif.id)])
      excerpt.motif_names = uniqueNames([...excerpt.motif_names, ...linkedMotifs.map((motif) => motif.name)]).sort()
      if (body.note?.trim()) excerpt.note = body.note
      refreshMotifCounts()
      await route.fulfill({ json: excerpt })
      return
    }

    if (addMotifsMatch && request.method() === 'PUT') {
      const excerpt = excerpts.find((item) => item.id === addMotifsMatch[1])
      if (!excerpt) {
        await route.fulfill({ status: 404, json: { detail: 'Motif excerpt not found' } })
        return
      }
      const body = request.postDataJSON() as { motif_names?: string[]; note?: string | null }
      const linkedMotifs = uniqueNames(body.motif_names ?? []).map((name) => ensureMotif(name))
      excerpt.motif_ids = linkedMotifs.map((motif) => motif.id)
      excerpt.motif_names = linkedMotifs.map((motif) => motif.name).sort()
      if (body.note !== undefined && body.note !== null) excerpt.note = body.note
      let deleted = false
      if (!excerpt.motif_ids.length) {
        excerpts = excerpts.filter((item) => item.id !== excerpt.id)
        deleted = true
      }
      refreshMotifCounts()
      await route.fulfill({ json: { excerpt: deleted ? null : excerpt, deleted } })
      return
    }

    const unlinkMotifMatch = path.match(/^\/api\/motifs\/excerpts\/([^/]+)\/motifs\/([^/]+)$/)
    if (unlinkMotifMatch && request.method() === 'DELETE') {
      const [, excerptId, motifId] = unlinkMotifMatch
      const excerpt = excerpts.find((item) => item.id === excerptId)
      if (!excerpt || !excerpt.motif_ids.includes(motifId)) {
        await route.fulfill({ status: 404, json: { detail: 'Motif excerpt link not found' } })
        return
      }
      const motif = motifs.find((item) => item.id === motifId)
      excerpt.motif_ids = excerpt.motif_ids.filter((id) => id !== motifId)
      excerpt.motif_names = excerpt.motif_names.filter((name) => name !== motif?.name)
      if (!excerpt.motif_ids.length) {
        excerpts = excerpts.filter((item) => item.id !== excerptId)
      }
      refreshMotifCounts()
      await route.fulfill({ status: 204, body: '' })
      return
    }

    const localGraphMatch = path.match(/^\/api\/motifs\/([^/]+)\/graph$/)
    if (localGraphMatch) {
      const motifId = localGraphMatch[1]
      const graph = graphFrom(motifs, excerpts)
      await route.fulfill({
        json: {
          nodes: graph.nodes.map((node) => ({ ...node, is_center: node.id === motifId })),
          edges: graph.edges.filter((edge) => edge.source_id === motifId || edge.target_id === motifId),
        },
      })
      return
    }

    const excerptsMatch = path.match(/^\/api\/motifs\/([^/]+)\/excerpts$/)
    if (excerptsMatch) {
      const motifId = excerptsMatch[1]
      await route.fulfill({ json: excerpts.filter((excerpt) => excerpt.motif_ids.includes(motifId)) })
      return
    }

    await route.fulfill({ status: 404, json: { detail: 'Not Found' } })
  })
}

test.beforeEach(async ({ page }) => {
  await mockMotifFlowApi(page)
})

test('article selection can be saved to multiple motifs and reopened from the star map', async ({ page }) => {
  await page.goto('/articles?id=article-a')
  const editor = page.getByTestId('article-body-editor')
  await expect(editor).toHaveValue(article.body, { timeout: 20000 })

  const start = article.body.indexOf('玫瑰在夜里')
  const end = start + '玫瑰在夜里像血一样醒着。'.length
  await editor.evaluate((textarea: HTMLTextAreaElement, range) => {
    textarea.focus()
    textarea.setSelectionRange(range.start, range.end)
    textarea.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, clientX: 620, clientY: 380 }))
  }, { start, end })

  await expect(page.getByTestId('motif-attach-panel')).toBeHidden()
  await editor.evaluate((textarea: HTMLTextAreaElement) => {
    textarea.dispatchEvent(new MouseEvent('contextmenu', { bubbles: true, cancelable: true, button: 2, clientX: 620, clientY: 380 }))
  })
  await expect(page.getByTestId('motif-context-menu')).toBeVisible()
  await page.getByRole('button', { name: '加入意象星图' }).click()
  await expect(page.getByTestId('motif-attach-panel')).toBeVisible()
  await page.getByTestId('motif-attach-input').fill('玫瑰花')
  await page.keyboard.press('Enter')
  await page.getByTestId('motif-attach-input').fill('血')
  await page.keyboard.press('Enter')
  await page.getByRole('button', { name: '保存摘录' }).click()
  await expect(page.getByText('已加入意象', { exact: true })).toBeVisible()
  const anchors = page.getByTestId('article-motif-anchors')
  await expect(anchors.getByText('玫瑰花')).toBeVisible()
  await expect(anchors.getByText('血')).toBeVisible()
  await expect(anchors.getByText('玫瑰在夜里像血一样醒着。')).toHaveCount(0)
  await anchors.getByRole('button', { name: '定位' }).first().click()
  await expect.poll(() => editor.evaluate((textarea: HTMLTextAreaElement) => ({
    start: textarea.selectionStart,
    end: textarea.selectionEnd,
  }))).toEqual({ start, end })

  await page.goto('/motifs')
  await expect(page.getByText('玫瑰花').first()).toBeVisible()
  await expect(page.getByText('血').first()).toBeVisible()
  await expect(page.getByText('1 条共同出现关系')).toBeVisible()

  await page.getByRole('button', { name: /玫瑰花/ }).first().click()
  await expect(page.getByText('花园')).toBeVisible()
  await expect(page.getByTestId('motifs-detail-pane').getByText('玫瑰在夜里像血一样醒着。')).toHaveCount(0)
  const detailPane = page.getByTestId('motifs-detail-pane')
  const openSourceButton = detailPane.getByRole('button', { name: '打开来源' })
  await openSourceButton.scrollIntoViewIfNeeded()
  await openSourceButton.click()

  await expect(page).toHaveURL(/\/articles\?.*id=article-a/)
  await expect(page.getByText('已回到原句。')).toBeVisible()
  await expect.poll(() => editor.evaluate((textarea: HTMLTextAreaElement) => ({
    start: textarea.selectionStart,
    end: textarea.selectionEnd,
  }))).toEqual({ start, end })
})

test('same selection reopens existing motifs and unlink only removes the current motif', async ({ page }) => {
  await page.goto('/articles?id=article-a')
  const editor = page.getByTestId('article-body-editor')
  await expect(editor).toHaveValue(article.body)

  const start = article.body.indexOf('玫瑰在夜里')
  const end = start + '玫瑰在夜里像血一样醒着。'.length
  await editor.evaluate((textarea: HTMLTextAreaElement, range) => {
    textarea.focus()
    textarea.setSelectionRange(range.start, range.end)
    textarea.dispatchEvent(new MouseEvent('contextmenu', { bubbles: true, cancelable: true, button: 2, clientX: 620, clientY: 380 }))
  }, { start, end })
  await page.getByRole('button', { name: '加入意象星图' }).click()
  await page.getByTestId('motif-attach-input').fill('岁月')
  await page.keyboard.press('Enter')
  await page.getByRole('button', { name: '保存摘录' }).click()
  await expect(page.getByText('已加入意象', { exact: true })).toBeVisible()

  await editor.evaluate((textarea: HTMLTextAreaElement, range) => {
    textarea.focus()
    textarea.setSelectionRange(range.start, range.end)
    textarea.dispatchEvent(new MouseEvent('contextmenu', { bubbles: true, cancelable: true, button: 2, clientX: 620, clientY: 520 }))
  }, { start, end })
  await page.getByRole('button', { name: '加入意象星图' }).click()
  await expect(page.getByText('这段文字已加入过意象')).toBeVisible()
  await expect(page.getByRole('button', { name: /岁月/ }).first()).toBeVisible()

  const panel = page.getByTestId('motif-attach-panel')
  const handle = page.getByTestId('motif-attach-drag-handle')
  const before = await panel.boundingBox()
  const handleBox = await handle.boundingBox()
  expect(before).not.toBeNull()
  expect(handleBox).not.toBeNull()
  await page.mouse.move(handleBox!.x + handleBox!.width / 2, handleBox!.y + handleBox!.height / 2)
  await page.mouse.down()
  await page.mouse.move(handleBox!.x + handleBox!.width / 2 + 44, handleBox!.y + handleBox!.height / 2 + 28)
  await page.mouse.up()
  const after = await panel.boundingBox()
  expect(after).not.toBeNull()
  expect(after!.x).toBeGreaterThan(before!.x + 20)
  await expect(page.getByRole('button', { name: '保存摘录' })).toBeVisible()

  await page.getByTestId('motif-attach-input').fill('城市')
  await page.keyboard.press('Enter')
  await page.getByRole('button', { name: '保存摘录' }).click()
  await expect(page.getByText('意象已更新')).toBeVisible()

  await editor.evaluate((textarea: HTMLTextAreaElement, range) => {
    textarea.focus()
    textarea.setSelectionRange(range.start, range.end)
    textarea.dispatchEvent(new MouseEvent('contextmenu', { bubbles: true, cancelable: true, button: 2, clientX: 620, clientY: 520 }))
  }, { start, end })
  await page.getByRole('button', { name: '加入意象星图' }).click()
  await expect(page.getByText('这段文字已加入过意象')).toBeVisible()
  let selectedChips = page.getByTestId('motif-attach-selected-chip')
  await expect(selectedChips.filter({ hasText: '岁月' })).toBeVisible()
  await expect(selectedChips.filter({ hasText: '城市' })).toBeVisible()
  await selectedChips.filter({ hasText: '岁月' }).click()
  selectedChips = page.getByTestId('motif-attach-selected-chip')
  await expect(selectedChips.filter({ hasText: '岁月' })).toHaveCount(0)
  await expect(selectedChips.filter({ hasText: '城市' })).toBeVisible()
  await page.getByRole('button', { name: '保存摘录' }).click()
  await expect(page.getByText('意象已更新')).toBeVisible()

  await editor.evaluate((textarea: HTMLTextAreaElement, range) => {
    textarea.focus()
    textarea.setSelectionRange(range.start, range.end)
    textarea.dispatchEvent(new MouseEvent('contextmenu', { bubbles: true, cancelable: true, button: 2, clientX: 620, clientY: 520 }))
  }, { start, end })
  await page.getByRole('button', { name: '加入意象星图' }).click()
  selectedChips = page.getByTestId('motif-attach-selected-chip')
  await expect(selectedChips.filter({ hasText: '城市' })).toBeVisible()
  await expect(selectedChips.filter({ hasText: '岁月' })).toHaveCount(0)
  await page.getByRole('button', { name: '取消' }).click()

  await page.goto('/motifs')
  await page.getByRole('button', { name: /城市/ }).first().click()
  const detailPane = page.getByTestId('motifs-detail-pane')
  await expect(detailPane.getByText('花园')).toBeVisible()
  await expect(detailPane.getByText('玫瑰在夜里像血一样醒着。')).toHaveCount(0)
  page.once('dialog', (dialog) => dialog.accept())
  await page.getByRole('button', { name: '从此意象移除' }).click()
  await expect(detailPane.getByText('花园')).toHaveCount(0)
})

test('position-drifted source anchor reopens existing motifs and collapses duplicate excerpts', async ({ page }) => {
  await page.goto('/articles?id=article-a')
  const editor = page.getByTestId('article-body-editor')
  await expect(editor).toHaveValue(article.body)

  const sentence = '玫瑰在夜里像血一样醒着。'
  const start = article.body.indexOf(sentence)
  const end = start + sentence.length
  await page.evaluate(async (payload) => {
    await fetch('/__e2e/motifs/seed-drift-duplicate', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(payload),
    })
  }, {
    source_kind: 'article',
    source_id: article.id,
    excerpt_text: sentence,
    current_start: start,
    current_end: end,
    motif_names: ['测试意象｜往事', '测试意象｜风'],
  })

  await page.goto('/articles?id=article-a')
  const anchors = page.getByTestId('article-motif-anchors')
  await expect(anchors.getByText('测试意象｜往事')).toBeVisible()
  await expect(anchors.getByText('测试意象｜风')).toBeVisible()
  await expect(anchors.getByText('玫瑰在夜里像血一样醒着。')).toHaveCount(0)
  await anchors.getByRole('button', { name: '定位' }).first().click()
  await expect.poll(() => editor.evaluate((textarea: HTMLTextAreaElement) => ({
    start: textarea.selectionStart,
    end: textarea.selectionEnd,
  }))).toEqual({ start, end })

  await editor.evaluate((textarea: HTMLTextAreaElement) => {
    textarea.dispatchEvent(new MouseEvent('contextmenu', { bubbles: true, cancelable: true, button: 2, clientX: 620, clientY: 420 }))
  })
  await page.getByRole('button', { name: '加入意象星图' }).click()
  await expect(page.getByText('这段文字已加入过意象')).toBeVisible()
  const selectedChips = page.getByTestId('motif-attach-selected-chip')
  await expect(selectedChips.filter({ hasText: '测试意象｜往事' })).toBeVisible()
  await expect(selectedChips.filter({ hasText: '测试意象｜风' })).toBeVisible()
  await page.getByRole('button', { name: '保存摘录' }).click()
  await expect(page.getByTestId('motif-attach-panel')).toBeHidden()
  await expect(anchors.getByText('测试意象｜往事')).toHaveCount(1)
  await expect(anchors.getByText('测试意象｜风')).toHaveCount(1)
  await expect(anchors.getByText('玫瑰在夜里像血一样醒着。')).toHaveCount(0)
})

test('source jump warns when the original article text changed', async ({ page }) => {
  await page.goto('/articles?id=article-a')
  const editor = page.getByTestId('article-body-editor')
  await expect(editor).toHaveValue(article.body)

  const start = article.body.indexOf('玫瑰在夜里')
  const end = start + '玫瑰在夜里像血一样醒着。'.length
  await editor.evaluate((textarea: HTMLTextAreaElement, range) => {
    textarea.focus()
    textarea.setSelectionRange(range.start, range.end)
    textarea.dispatchEvent(new MouseEvent('contextmenu', { bubbles: true, cancelable: true, button: 2, clientX: 620, clientY: 380 }))
  }, { start, end })
  await page.getByRole('button', { name: '加入意象星图' }).click()
  await page.getByTestId('motif-attach-input').fill('改动')
  await page.keyboard.press('Enter')
  await page.getByRole('button', { name: '保存摘录' }).click()
  await expect(page.getByText('已加入意象', { exact: true })).toBeVisible()

  const changedArticle = { ...article, body: '原文已经改写成另一段，旧句子不在这里。' }
  await page.route(/\/api\/articles(?:\/|\?|$)/, async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    if (url.pathname === '/api/articles') {
      await route.fulfill({ json: [changedArticle, articleB] })
      return
    }
    if (url.pathname === '/api/articles/search') {
      await route.fulfill({ json: [] })
      return
    }
    if (request.method() === 'PUT') {
      await route.fulfill({ json: { ...changedArticle, ...(request.postDataJSON() as object) } })
      return
    }
    const id = url.pathname.split('/').pop()
    await route.fulfill({ json: id === articleB.id ? articleB : changedArticle })
  })

  await page.goto('/motifs')
  await page.getByRole('button', { name: /改动/ }).first().click()
  await expect(page.getByText('花园')).toBeVisible()
  await expect(page.getByTestId('motifs-detail-pane').getByText('玫瑰在夜里像血一样醒着。')).toHaveCount(0)
  await page.getByRole('button', { name: '打开来源' }).click()

  await expect(page).toHaveURL(/\/articles\?.*id=article-a/)
  await expect(page.getByText('原文可能已改动，已打开来源，请按摘录快照核对。')).toBeVisible()
  await expect(page.getByTestId('article-body-editor')).toHaveValue(changedArticle.body)
})

test('reference selection can be saved as a motif excerpt', async ({ page }) => {
  await page.goto('/library?ref=ref-a&group=source')
  const content = page.getByTestId('library-reference-content')
  await expect(content).toHaveValue(reference.content)

  const start = reference.content.indexOf('天空')
  const end = reference.content.length
  await content.evaluate((textarea: HTMLTextAreaElement, range) => {
    textarea.focus()
    textarea.setSelectionRange(range.start, range.end)
    textarea.dispatchEvent(new MouseEvent('contextmenu', { bubbles: true, cancelable: true, button: 2, clientX: 720, clientY: 360 }))
  }, { start, end })

  await expect(page.getByTestId('motif-context-menu')).toBeVisible()
  await page.getByRole('button', { name: '加入意象星图' }).click()
  await expect(page.getByTestId('motif-attach-panel')).toBeVisible()
  await page.getByTestId('motif-attach-input').fill('天空')
  await page.keyboard.press('Enter')
  await page.getByRole('button', { name: '保存摘录' }).click()
  await expect(page.getByText('已加入意象', { exact: true })).toBeVisible()
  const anchors = page.getByTestId('library-motif-anchors')
  await expect(anchors.getByText('天空像一块被擦亮的黑石。')).toBeVisible()
  await anchors.getByRole('button', { name: /天空像/ }).click()
  await expect.poll(() => content.evaluate((textarea: HTMLTextAreaElement) => ({
    start: textarea.selectionStart,
    end: textarea.selectionEnd,
  }))).toEqual({ start, end })

  await page.goto('/motifs')
  await page.getByRole('button', { name: /天空/ }).first().click()
  await expect(page.getByText('夜航西飞')).toBeVisible()
  await expect(page.getByTestId('motifs-detail-pane').getByText('天空像一块被擦亮的黑石。')).toHaveCount(0)
})

test('motif profile reader uses chips and saves chip edits explicitly', async ({ page }) => {
  await page.goto('/motifs')
  await page.evaluate(async () => {
    await fetch('/api/motifs', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        name: '海德格尔的常人',
        aliases: ['das Man', 'the They'],
        tags: ['海德格尔', '存在主义'],
        profile: {
          definition: '人在公共意见中失去自己的判断。',
          core_tension: '自我选择与平均化生活互相拉扯。',
          writing_functions: ['制造日常压力', '表现从众'],
          scene_triggers: ['大家都这样说'],
          character_signals: ['人物不断引用别人说的话'],
          imagery_translations: ['广播', '走廊'],
          short_examples: ['他还没开口，答案已经替他说完。'],
          misuse_warnings: ['不要把常人简单写成庸俗群众。'],
          micro_exercises: ['写一个人被“大家都这样”逼退的瞬间。'],
          source_hints: [{ title: '《存在与时间》', url: null, note: '需核对。' }],
        },
      }),
    })
  })

  await page.goto('/motifs')
  await expect(page.getByText('人在公共意见中失去自己的判断。')).toBeVisible({ timeout: 20000 })
  const detail = page.getByTestId('motifs-detail-pane')
  await expect(detail.getByRole('button', { name: /海德格尔 ×/ })).toBeVisible()
  await detail.getByRole('button', { name: /海德格尔 ×/ }).click()
  await expect(page.getByText('有未保存修改')).toBeVisible()
  await page.getByRole('button', { name: '保存' }).click()
  await expect(page.getByText('意象已保存')).toBeVisible()
  await expect(detail.getByRole('button', { name: /海德格尔 ×/ })).toHaveCount(0)

  await page.getByRole('button', { name: '查看详细' }).click()
  await expect(page.getByText('写作转译')).toBeVisible()
  await expect(page.getByText('他还没开口，答案已经替他说完。')).toBeVisible()
})

test('AI enrichment keeps a draft across close and reopen, and clears it only when regenerating', async ({ page }) => {
  await page.goto('/motifs')
  await page.evaluate(async () => {
    await fetch('/api/motifs', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ name: '神话模式' }),
    })
  })

  await page.goto('/motifs')
  await expect(page.getByTestId('motifs-list-pane').getByRole('button', { name: /神话模式/ })).toBeVisible({ timeout: 20000 })
  await page.getByTestId('motifs-detail-pane').getByRole('button', { name: 'AI 丰富' }).click()
  await page.getByRole('button', { name: '生成短卡草稿' }).click()
  await expect(page.getByText('神话模式短卡 A')).toBeVisible()
  await expect(page.getByText('定义 A', { exact: true })).toBeVisible()

  await page.getByRole('button', { name: '取消' }).click()
  await expect(page.getByTestId('motif-enrichment-modal')).toHaveCount(0)
  await page.getByTestId('motifs-detail-pane').getByRole('button', { name: 'AI 丰富' }).click()
  await expect(page.getByText('神话模式短卡 A')).toBeVisible()
  await expect(page.getByText('定义 A', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: '应用到已有意象' })).toBeEnabled()

  await page.getByRole('button', { name: '生成短卡草稿' }).click()
  await expect(page.getByText('生成中...')).toBeVisible()
  await expect(page.getByText('定义 A', { exact: true })).toHaveCount(0)
  await expect(page.getByText('神话模式短卡 B')).toBeVisible()
  await expect(page.getByText('定义 B', { exact: true })).toBeVisible()
})

test('AI enrichment can keep running after the dialog is closed and can be interrupted', async ({ page }) => {
  await page.goto('/motifs')
  const listPane = page.getByTestId('motifs-list-pane')
  await listPane.getByRole('button', { name: 'AI', exact: true }).click()

  await page.getByPlaceholder('例如：神话模式、奴隶道德、常人').fill('慢任务概念')
  await page.getByRole('button', { name: '生成短卡草稿' }).click()
  const modal = page.getByTestId('motif-enrichment-modal')
  await expect(modal.getByText(/AI 正在丰富：慢任务概念/)).toBeVisible()
  await expect(modal.getByText('已发送请求，等待模型返回', { exact: true })).toBeVisible()

  await page.getByRole('button', { name: '收起界面' }).click()
  await expect(page.getByTestId('motif-enrichment-modal')).toHaveCount(0)
  const jobBar = page.getByTestId('motif-enrichment-job-bar')
  await expect(jobBar).toBeVisible()
  await expect(jobBar.getByText(/AI 正在丰富：慢任务概念/)).toBeVisible()

  await jobBar.getByRole('button', { name: '查看' }).click()
  await expect(modal).toBeVisible()
  await expect(modal.getByText('已发送请求，等待模型返回', { exact: true })).toBeVisible()
  await modal.getByRole('button', { name: '中断' }).click()
  await expect(page.getByText(/AI 已中断：慢任务概念/)).toBeVisible()
  await expect(modal.getByText(/远端仍可能完成并计费/)).toBeVisible()
})

test('AI enrichment opens without a prefilled motif name and can apply a preserved new-concept draft', async ({ page }) => {
  await page.goto('/motifs')
  const listPane = page.getByTestId('motifs-list-pane')
  await expect(listPane.getByRole('button', { name: 'AI', exact: true })).toBeEnabled()
  await listPane.getByRole('button', { name: 'AI', exact: true }).click()

  const conceptInput = page.getByPlaceholder('例如：神话模式、奴隶道德、常人')
  await expect(conceptInput).toBeVisible()
  await expect(page.getByRole('button', { name: '生成短卡草稿' })).toBeDisabled()

  await conceptInput.fill('尼采')
  await page.getByRole('button', { name: '生成短卡草稿' }).click()
  await expect(page.getByText('尼采短卡 A')).toBeVisible()
  await expect(page.getByRole('button', { name: '创建意象' })).toBeEnabled()

  await conceptInput.fill('尼采的道德奴隶')
  await page.getByRole('button', { name: '取消' }).click()
  await expect(page.getByTestId('motif-enrichment-modal')).toHaveCount(0)

  await listPane.getByRole('button', { name: 'AI', exact: true }).click()
  await expect(page.getByText('尼采短卡 A')).toBeVisible()
  await expect(conceptInput).toHaveValue('尼采的道德奴隶')
  await expect(page.getByText('这个草稿属于另一个已选意象')).toHaveCount(0)
  await expect(page.getByRole('button', { name: '创建意象' })).toBeEnabled()
  await page.getByRole('button', { name: '创建意象' }).click()

  await expect(page.getByText('AI 丰富结果已应用')).toBeVisible()
  await expect(page.getByTestId('motifs-list-pane').getByRole('button', { name: /尼采的道德奴隶/ })).toBeVisible()
  const motifsAfter = await page.evaluate(async () => {
    const response = await fetch('/api/motifs')
    return await response.json() as MotifNode[]
  })
  expect(motifsAfter.filter((motif) => motif.name === '尼采的道德奴隶')).toHaveLength(1)
})

test('AI enrichment for a new concept updates an existing same-name motif instead of creating a duplicate', async ({ page }) => {
  await page.goto('/motifs')
  await page.evaluate(async () => {
    await fetch('/api/motifs', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        name: '海德格尔的常人',
        aliases: ['旧别名'],
        tags: ['旧标签'],
        profile: {
          definition: '旧定义',
          core_tension: '',
          writing_functions: [],
          scene_triggers: [],
          character_signals: [],
          imagery_translations: [],
          short_examples: [],
          misuse_warnings: [],
          micro_exercises: [],
          source_hints: [],
        },
      }),
    })
  })

  await page.goto('/motifs')
  await page.getByPlaceholder('新意象').fill('海德格尔的常人')
  await page.getByTestId('motifs-list-pane').getByRole('button', { name: 'AI', exact: true }).click()
  await page.getByRole('button', { name: '生成短卡草稿' }).click()
  await expect(page.getByText('海德格尔的常人短卡 A')).toBeVisible()
  await expect(page.getByRole('button', { name: '应用到已有意象' })).toBeVisible()
  await page.getByRole('button', { name: '取消' }).click()
  await page.getByTestId('motifs-list-pane').getByRole('button', { name: 'AI', exact: true }).click()
  await expect(page.getByText('海德格尔的常人短卡 A')).toBeVisible()
  await expect(page.getByText('这个草稿属于另一个已选意象')).toHaveCount(0)
  await expect(page.getByRole('button', { name: '应用到已有意象' })).toBeEnabled()
  await page.getByRole('button', { name: '应用到已有意象' }).click()

  await expect(page.getByText('Motif name already exists')).toHaveCount(0)
  await expect(page.getByText('AI 丰富结果已应用')).toBeVisible()
  await expect(page.getByText('旧定义')).toBeVisible()
  await expect(page.getByText('功能 A')).toBeVisible()
  await expect(page.getByText('哲学概念')).toBeVisible()
  await expect(page.getByPlaceholder('新意象')).toHaveValue('')

  const motifsAfter = await page.evaluate(async () => {
    const response = await fetch('/api/motifs')
    return await response.json() as MotifNode[]
  })
  const sameName = motifsAfter.filter((motif) => motif.name === '海德格尔的常人')
  expect(sameName).toHaveLength(1)
  expect(sameName[0].profile.definition).toBe('旧定义')
  expect(sameName[0].profile.writing_functions).toContain('功能 A')
  expect(sameName[0].aliases).toContain('旧别名')
  expect(sameName[0].aliases).toContain('海德格尔的常人别名')
})

test('AI enrichment dialog keeps footer actions visible and candidate list scrollable in compact viewport', async ({ page }) => {
  await page.setViewportSize({ width: 820, height: 520 })
  await page.goto('/motifs')
  await page.evaluate(async () => {
    await fetch('/api/motifs', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ name: '尼采的道德奴隶' }),
    })
  })

  await page.goto('/motifs')
  await page.getByTestId('motifs-detail-pane').getByRole('button', { name: 'AI 丰富' }).click()
  await page.getByRole('button', { name: '生成短卡草稿' }).click()
  await expect(page.getByText('尼采的道德奴隶短卡 A')).toBeVisible()

  const modal = page.getByTestId('motif-enrichment-modal')
  const footer = page.getByTestId('motif-enrichment-footer')
  const candidates = page.getByTestId('motif-enrichment-candidates')
  const applyButton = page.getByRole('button', { name: '应用到已有意象' })
  const cancelButton = page.getByRole('button', { name: '取消' })

  await expect(modal).toBeVisible()
  await expect(footer).toBeVisible()
  await expect(applyButton).toBeVisible()
  await expect(cancelButton).toBeVisible()
  await expect(modal).toHaveCSS('resize', 'both')

  const [modalBox, footerBox, applyBox, cancelBox] = await Promise.all([
    modal.boundingBox(),
    footer.boundingBox(),
    applyButton.boundingBox(),
    cancelButton.boundingBox(),
  ])
  expect(modalBox).not.toBeNull()
  expect(footerBox).not.toBeNull()
  expect(applyBox).not.toBeNull()
  expect(cancelBox).not.toBeNull()
  expect(footerBox!.y + footerBox!.height).toBeLessThanOrEqual(520)
  expect(applyBox!.y + applyBox!.height).toBeLessThanOrEqual(520)
  expect(cancelBox!.y + cancelBox!.height).toBeLessThanOrEqual(520)
  expect(footerBox!.y).toBeGreaterThanOrEqual(modalBox!.y)

  const scrollState = await candidates.evaluate((element) => {
    const target = element as HTMLElement
    const before = {
      clientHeight: target.clientHeight,
      scrollHeight: target.scrollHeight,
      scrollTop: target.scrollTop,
    }
    target.scrollTop = target.scrollHeight
    return {
      ...before,
      afterScrollTop: target.scrollTop,
    }
  })
  expect(scrollState.scrollHeight).toBeGreaterThan(scrollState.clientHeight)
  expect(scrollState.afterScrollTop).toBeGreaterThan(0)
  await expect(page.getByText(/第 18 条候选句/)).toBeVisible()
})
