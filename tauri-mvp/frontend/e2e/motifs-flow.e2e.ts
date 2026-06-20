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
  })

  await page.route(/\/api\/app\/version$/, async (route) => {
    await route.fulfill({
      json: {
        app_name: 'Living to Tell',
        version: '0.1.7',
        api_version: '2.0.0',
        capabilities: ['motif_star_map'],
      },
    })
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
      const body = request.postDataJSON() as { name?: string }
      const name = body.name?.trim() || '未命名意象'
      const existing = motifs.find((motif) => motif.name === name)
      if (existing) {
        await route.fulfill({ status: 400, json: { detail: 'Motif name already exists' } })
        return
      }
      const motif = {
        id: `motif-${motifs.length + 1}`,
        name,
        aliases: [],
        note: '',
        tags: [],
        pinned: false,
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
        motif_names?: string[]
      }
      const names = uniqueNames(body.motif_names ?? [])
      const linkedMotifs = names.map((name) => ensureMotif(name))
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
  await expect(editor).toHaveValue(article.body)

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
  await expect(page.getByText('已加入意象')).toBeVisible()
  const anchors = page.getByTestId('article-motif-anchors')
  await expect(anchors.getByText('玫瑰在夜里像血一样醒着。')).toBeVisible()
  await anchors.getByRole('button', { name: /玫瑰在夜里/ }).click()
  await expect.poll(() => editor.evaluate((textarea: HTMLTextAreaElement) => ({
    start: textarea.selectionStart,
    end: textarea.selectionEnd,
  }))).toEqual({ start, end })

  await page.goto('/motifs')
  await expect(page.getByText('玫瑰花').first()).toBeVisible()
  await expect(page.getByText('血').first()).toBeVisible()
  await expect(page.getByText('1 条共同出现关系')).toBeVisible()

  await page.getByRole('button', { name: /玫瑰花/ }).first().click()
  await expect(page.getByText('玫瑰在夜里像血一样醒着。')).toBeVisible()
  await page.getByRole('button', { name: '打开来源' }).click()

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
  await expect(page.getByText('已加入意象')).toBeVisible()

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
  await expect(page.getByText('玫瑰在夜里像血一样醒着。')).toBeVisible()
  page.once('dialog', (dialog) => dialog.accept())
  await page.getByRole('button', { name: '从此意象移除' }).click()
  await expect(page.getByText('玫瑰在夜里像血一样醒着。')).toHaveCount(0)
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
  await expect(anchors.getByRole('button', { name: /玫瑰在夜里/ })).toHaveCount(1)
  await anchors.getByRole('button', { name: /玫瑰在夜里/ }).click()
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
  await expect(anchors.getByRole('button', { name: /玫瑰在夜里/ })).toHaveCount(1)
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
  await expect(page.getByText('已加入意象')).toBeVisible()

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
  await expect(page.getByText('玫瑰在夜里像血一样醒着。')).toBeVisible()
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
  await expect(page.getByText('已加入意象')).toBeVisible()
  const anchors = page.getByTestId('library-motif-anchors')
  await expect(anchors.getByText('天空像一块被擦亮的黑石。')).toBeVisible()
  await anchors.getByRole('button', { name: /天空像/ }).click()
  await expect.poll(() => content.evaluate((textarea: HTMLTextAreaElement) => ({
    start: textarea.selectionStart,
    end: textarea.selectionEnd,
  }))).toEqual({ start, end })

  await page.goto('/motifs')
  await page.getByRole('button', { name: /天空/ }).first().click()
  await expect(page.getByText('天空像一块被擦亮的黑石。')).toBeVisible()
})
