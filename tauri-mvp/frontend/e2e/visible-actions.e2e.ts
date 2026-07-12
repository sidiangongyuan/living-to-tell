import path from 'node:path'
import { expect, test, type Page, type Route } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

declare global {
  interface Window {
    __copiedText?: string
    __confirmMessages?: string[]
    __closeInvokes?: Array<{ command: string; args?: Record<string, unknown> }>
    __tauriEventHandlers?: Record<number, (event: { event: string; id: number; payload: unknown }) => void>
  }
}

const article = {
  id: 'article-a',
  title: '导出测试文章',
  body: '第一段正文。\n\n第二段正文。',
  entry_type: 'fragment',
  created_at: null,
  updated_at: null,
  tags: ['测试'],
  archived_at: null,
  curation_status: 'active',
}

const articleB = {
  ...article,
  id: 'article-b',
  title: '备选文章',
  body: '第三段正文。',
  tags: ['备选'],
}

const collection = {
  id: 'collection-a',
  title: '测试作品集',
  description: '用于检查作品集按钮',
  project_type: 'novel',
  article_count: 1,
  created_at: null,
  updated_at: null,
}

const collectionArticle = {
  ...article,
  body_preview: article.body,
  word_count: 12,
  char_count: article.body.length,
  sort_order: 0,
}

const collectionArticleB = {
  ...articleB,
  body_preview: articleB.body,
  word_count: 6,
  char_count: articleB.body.length,
  sort_order: 1,
}

const existingReference = {
  id: 'ref-existing',
  source_title: '测试书',
  content: '已有标本正文',
  source_author: '测试作者',
  tags: [],
  kind: 'excerpt',
  usage_kind: 'style',
  personal_note: '',
  created_at: null,
  updated_at: null,
}

const imageryReference = {
  ...existingReference,
  id: 'ref-imagery',
  source_title: '另一本书',
  content: '意象标本正文',
  source_author: '另一作者',
  usage_kind: 'imagery',
}

const openNote = {
  id: 'note-a',
  entry_id: article.id,
  body: '请加强结尾的余韵。',
  status: 'open',
  pinned: true,
  sort_order: 0,
  created_at: null,
  updated_at: null,
  completed_at: null,
}

const reference = {
  id: 'ref-created',
  source_title: '',
  content: '新标本',
  source_author: '',
  tags: [],
  kind: 'excerpt',
  usage_kind: 'style',
  personal_note: '',
  created_at: null,
  updated_at: null,
}

function compareProfileSnapshot(profileId: string) {
  return {
    profile_id: profileId,
    profile_name: profileId === 'default' ? '默认配置' : 'Gemini 测试',
    provider: profileId === 'default' ? 'openai' : 'gemini',
    model: profileId === 'default' ? 'gpt-4o-mini' : 'gemini-test-model',
  }
}

function compareProfileResult(profileId: string, text: string, resultText?: string) {
  const output = resultText ?? (profileId === 'default' ? 'AI 生成结果' : 'Gemini 生成结果')
  const snapshot = compareProfileSnapshot(profileId)
  return {
    ...snapshot,
    transport: 'fake',
    status: 'success',
    result: output,
    error: '',
    elapsed_ms: 120,
    input_tokens: 10,
    output_tokens: 20,
    cost: null,
    finish_reason: 'stop',
    stats: {
      input_chars: text.length,
      output_chars: output.length,
      delta_chars: output.length - text.length,
      output_ratio: text.length ? output.length / text.length : null,
      input_paragraphs: 1,
      output_paragraphs: 1,
    },
  }
}

function compareStreamBody(body: { task_type?: string; text?: string; profile_ids?: string[] }, resultForProfile?: (profileId: string) => string) {
  const text = body.text ?? ''
  const profileIds = body.profile_ids?.length ? body.profile_ids : ['default']
  const events = [
    {
      event: 'started',
      run_id: 'e2e-run',
      profiles: profileIds.map(compareProfileSnapshot),
    },
    ...profileIds.map((profileId) => ({
      event: 'result',
      result: compareProfileResult(profileId, text, resultForProfile?.(profileId)),
    })),
    {
      event: 'done',
      run_id: 'e2e-run',
    },
  ]
  return `${events.map((event) => JSON.stringify(event)).join('\n')}\n`
}

async function fulfillCompareStream(route: Route, resultForProfile?: (profileId: string) => string) {
  const body = route.request().postDataJSON() as { task_type?: string; text?: string; profile_ids?: string[] }
  await route.fulfill({
    contentType: 'application/x-ndjson',
    body: compareStreamBody(body, resultForProfile),
  })
}

const outlineItems = [
  {
    id: 'outline-part-a',
    collection_id: collection.id,
    parent_id: null,
    entry_id: null,
    title: '第一部：回到旧城',
    item_type: 'part',
    status: 'drafting',
    summary: '主角回到旧城，故事从私人记忆转向现实追索。',
    notes: '这个部分负责建立气氛和核心悬念。',
    pov: '',
    setting: '旧城',
    timeline: '现在时',
    tags: ['长篇', '结构'],
    target_word_count: 8000,
    sort_order: 0,
    created_at: null,
    updated_at: null,
  },
  {
    id: 'outline-chapter-a',
    collection_id: collection.id,
    parent_id: 'outline-part-a',
    entry_id: article.id,
    title: '雨夜来信',
    item_type: 'chapter',
    status: 'drafting',
    summary: '一封迟来的信打破日常，把主角推向已经封存的往事。',
    notes: '需要保留信件带来的不安，不要太早解释真相。',
    pov: '林澄',
    setting: '旧邮局',
    timeline: '第一晚',
    tags: ['开端', '悬念'],
    target_word_count: 3500,
    sort_order: 1,
    created_at: null,
    updated_at: null,
  },
  {
    id: 'outline-scene-a',
    collection_id: collection.id,
    parent_id: 'outline-chapter-a',
    entry_id: null,
    title: '河岸清单',
    item_type: 'scene',
    status: 'idea',
    summary: '主角把谜团拆成三件可执行的事，开始从被动等待转为行动。',
    notes: '',
    pov: '林澄',
    setting: '河岸',
    timeline: '次日清晨',
    tags: ['行动', '线索'],
    target_word_count: 1800,
    sort_order: 2,
    created_at: null,
    updated_at: null,
  },
  {
    id: 'outline-note-a',
    collection_id: collection.id,
    parent_id: null,
    entry_id: null,
    title: '结尾余韵备忘',
    item_type: 'note',
    status: 'done',
    summary: '结尾要落回人物选择，而不是只落在谜底。',
    notes: '',
    pov: '',
    setting: '',
    timeline: '',
    tags: ['修订'],
    target_word_count: null,
    sort_order: 3,
    created_at: null,
    updated_at: null,
  },
]

const backupItems = [
  {
    path: 'D:\\LivingToTellData\\backups\\auto-20260628-090000.sqlite3',
    name: 'auto-20260628-090000.sqlite3',
    size: 245760,
    created: '2026-06-28T09:00:00Z',
  },
]

const checkpointItems = [
  {
    path: 'D:\\LivingToTellData\\checkpoints\\大修前检查点.sqlite3',
    name: '大修前检查点',
    description: '准备重排长篇结构之前保存。',
    size: 251904,
    created: '2026-06-28T08:30:00Z',
  },
]

async function updatePublicScreenshot(page: Page, name: string) {
  if (process.env.UPDATE_PUBLIC_SCREENSHOTS !== '1') return
  await page.setViewportSize({ width: 1440, height: 960 })
  await page.screenshot({
    path: path.resolve(process.cwd(), '..', 'docs', 'assets', 'screenshots', name),
    fullPage: true,
  })
}

async function expectArticleEditorBody(page: Page, body: string) {
  await expect(page.getByTestId('article-body-editor')).toHaveValue(body, { timeout: 20000 })
}

async function mockVisibleActionApi(page: Page, language: 'zh' | 'en' = 'zh') {
  let currentArticleTaskRun: Record<string, any> | null = null
  let articleTaskRunGetCount = 0
  let sampleProjectInstalled = false
  const sampleProjectState = () => ({
    installed: sampleProjectInstalled,
    collection_id: sampleProjectInstalled ? 'collection-a' : null,
    entry_ids: sampleProjectInstalled ? [article.id, articleB.id] : [],
    reference_ids: sampleProjectInstalled ? [existingReference.id] : [],
    ai_card_ids: sampleProjectInstalled ? ['card-scene'] : [],
    note_ids: sampleProjectInstalled ? [openNote.id] : [],
    created_at: sampleProjectInstalled ? '2026-06-28T09:00:00.000Z' : null,
    missing_ids: [],
  })

  await page.addInitScript((initialLanguage) => {
    window.localStorage.clear()
    window.localStorage.setItem('language', initialLanguage)
    window.localStorage.setItem('living_to_tell_collections_tour_dismissed', 'true')
    ;(window as Window & {
      __WRITER_API_BASE__?: string
      __WRITER_DISABLE_AUTO_UPDATE__?: boolean
    }).__WRITER_API_BASE__ = 'http://backend.test'
    ;(window as Window & { __WRITER_DISABLE_AUTO_UPDATE__?: boolean }).__WRITER_DISABLE_AUTO_UPDATE__ = true
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: async (text: string) => {
          window.__copiedText = text
        },
      },
      configurable: true,
    })
  }, language)

  await page.route('**/api/app/version', async (route) => {
    await route.fulfill({
      json: {
        app_name: 'Living to Tell',
        version: '0.1.13',
        api_version: '2.0.0',
        capabilities: [
          'data_location',
          'ai_chat_settings',
          'ai_task_presets',
          'ai_profiles',
          'ai_task_compare',
          'update_check',
          'article_versions',
          'collection_outline',
          'collection_manuscript_structure',
          'sample_project',
        ],
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
  await page.route('**/api/onboarding/sample-project', async (route) => {
    if (route.request().method() === 'POST') {
      const action = sampleProjectInstalled ? 'already_installed' : 'created'
      sampleProjectInstalled = true
      await route.fulfill({ status: 201, json: { ...sampleProjectState(), action } })
      return
    }
    if (route.request().method() === 'DELETE') {
      sampleProjectInstalled = false
      await route.fulfill({ json: { ...sampleProjectState(), action: 'removed' } })
      return
    }
    await route.fulfill({ json: sampleProjectState() })
  })
  await page.route('**/api/backup/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    if (url.pathname === '/api/backup/backups') {
      await route.fulfill({ json: backupItems })
      return
    }
    if (url.pathname === '/api/backup/checkpoints') {
      if (request.method() === 'POST') {
        const body = request.postDataJSON() as { name?: string; description?: string }
        await route.fulfill({
          status: 201,
          json: {
            path: `D:\\LivingToTellData\\checkpoints\\${body.name ?? '新检查点'}.sqlite3`,
            name: body.name ?? '新检查点',
            description: body.description ?? '',
            size: 260096,
            created: '2026-06-28T10:00:00Z',
          },
        })
        return
      }
      await route.fulfill({ json: checkpointItems })
      return
    }
    if (url.pathname === '/api/backup/stats') {
      await route.fulfill({
        json: {
          backup_count: backupItems.length,
          checkpoint_count: checkpointItems.length,
          total_backup_size: backupItems.reduce((total, item) => total + item.size, 0),
          total_checkpoint_size: checkpointItems.reduce((total, item) => total + item.size, 0),
          total_size: [...backupItems, ...checkpointItems].reduce((total, item) => total + item.size, 0),
          backup_dir: 'D:\\LivingToTellData\\backups',
          checkpoint_dir: 'D:\\LivingToTellData\\checkpoints',
        },
      })
      return
    }
    if (url.pathname === '/api/backup/auto-backup') {
      await route.fulfill({
        status: 201,
        json: {
          path: 'D:\\LivingToTellData\\backups\\auto-20260628-100000.sqlite3',
          name: 'auto-20260628-100000.sqlite3',
          size: 262144,
          created: '2026-06-28T10:00:00Z',
        },
      })
      return
    }
    if (url.pathname === '/api/backup/restore') {
      await route.fulfill({ json: { ok: true } })
      return
    }
    if (request.method() === 'DELETE') {
      await route.fulfill({ status: 204 })
      return
    }
    await route.fallback()
  })
  await page.route('**/api/settings/data-location', async (route) => {
    await route.fulfill({
      json: {
        data_dir: 'D:\\LivingToTellData',
        default_data_dir: 'D:\\LivingToTellData',
        database_path: 'D:\\LivingToTellData\\writer.db',
        default_database_path: 'D:\\LivingToTellData\\writer.db',
        backup_dir: 'D:\\LivingToTellData\\backups',
        checkpoint_dir: 'D:\\LivingToTellData\\checkpoints',
        is_custom: false,
        database_exists: true,
        warning: null,
      },
    })
  })
  await page.route('**/api/dates/stats?**', async (route) => route.fulfill({ json: [] }))
  await page.route('**/api/dates/entries?**', async (route) => route.fulfill({ json: [article, articleB] }))
  await page.route('**/api/dates/quote?**', async (route) => route.fulfill({ json: null }))

  await page.route('**/api/articles/*/export?**', async (route) => {
    const format = new URL(route.request().url()).searchParams.get('format') || 'txt'
    const body = format === 'docx' ? 'fake-docx-bytes' : `exported ${format}`
    await route.fulfill({
      body,
      headers: {
        'Content-Type': format === 'docx'
          ? 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
          : 'text/plain; charset=utf-8',
      },
    })
  })
  await page.route('**/api/articles?**', async (route) => route.fulfill({ json: [article, articleB] }))
  await page.route('**/api/articles/search?**', async (route) => route.fulfill({ json: [] }))
  await page.route('**/api/articles/*/notes?**', async (route) => route.fulfill({ json: [openNote] }))
  await page.route('**/api/articles/*/notes', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 201,
        json: {
          ...openNote,
          id: 'note-created',
          body: (route.request().postDataJSON() as { body?: string }).body ?? '',
          pinned: false,
        },
      })
      return
    }
    await route.fulfill({ json: [openNote] })
  })
  await page.route('**/api/articles/*/versions', async (route) => {
    const request = route.request()
    const entryId = new URL(request.url()).pathname.split('/')[3] ?? article.id
    if (request.method() === 'POST') {
      const body = request.postDataJSON() as { version_type?: string; label?: string | null }
      await route.fulfill({
        status: 201,
        json: {
          id: `version-${Date.now()}`,
          entry_id: entryId,
          version_type: body.version_type ?? 'manual_checkpoint',
          content: entryId === articleB.id ? articleB.body : article.body,
          title_snapshot: entryId === articleB.id ? articleB.title : article.title,
          tags: entryId === articleB.id ? articleB.tags : article.tags,
          label: body.label ?? '',
          reason: '',
          word_count: 2,
          char_count: (entryId === articleB.id ? articleB.body : article.body).length,
          created_at: null,
          provider: null,
          model: null,
        },
      })
      return
    }
    await route.fulfill({ json: [] })
  })
  await page.route('**/api/articles/*/versions/*', async (route) => {
    const request = route.request()
    if (request.method() === 'DELETE') {
      await route.fulfill({ status: 204 })
      return
    }
    if (request.method() === 'POST') {
      await route.fulfill({ json: { entry: article, snapshot_version_id: 'snapshot-a', was_noop: false } })
      return
    }
    await route.fulfill({ json: [] })
  })
  await page.route('**/api/articles/*', async (route) => {
    const request = route.request()
    if (request.method() === 'PUT') {
      await route.fulfill({ json: { ...article, ...(request.postDataJSON() as object) } })
      return
    }
    if (request.method() === 'DELETE') {
      await route.fulfill({ status: 204 })
      return
    }
    const id = route.request().url().split('/').pop()
    await route.fulfill({ json: id === articleB.id ? articleB : article })
  })
  await page.route('**/api/articles', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({ status: 201, json: { ...article, id: 'article-created', title: '新文章' } })
      return
    }
    await route.fulfill({ json: [article, articleB] })
  })

  await page.route('**/api/collections/for-entry/*', async (route) => route.fulfill({ json: [] }))
  await page.route('**/api/collections/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    if (url.pathname === '/api/collections/collection-a/export') {
      const format = url.searchParams.get('format') || 'txt'
      await route.fulfill({
        body: format === 'docx' ? 'fake-collection-docx' : `collection ${format}`,
        headers: {
          'Content-Type': format === 'docx'
            ? 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            : 'text/plain; charset=utf-8',
        },
      })
      return
    }
    if (url.pathname === '/api/collections/collection-a/articles') {
      if (request.method() === 'POST') {
        await route.fulfill({ json: [collectionArticle, collectionArticleB] })
        return
      }
      await route.fulfill({ json: [collectionArticle] })
      return
    }
    if (url.pathname === '/api/collections/collection-a/articles/order') {
      await route.fulfill({ json: [collectionArticleB, collectionArticle] })
      return
    }
    if (url.pathname === '/api/collections/collection-a/articles/article-a') {
      await route.fulfill({ status: 204 })
      return
    }
    if (url.pathname === '/api/collections/collection-a/outline') {
      if (request.method() === 'POST') {
        const body = request.postDataJSON() as Record<string, unknown>
        await route.fulfill({
          status: 201,
          json: {
            id: 'outline-created',
            collection_id: collection.id,
            title: body.title ?? '新大纲项',
            item_type: body.item_type ?? 'scene',
            status: body.status ?? 'idea',
            summary: body.summary ?? '',
            pov: body.pov ?? '',
            timeline: body.timeline ?? '',
            setting: body.setting ?? '',
            tags: body.tags ?? [],
            notes: body.notes ?? '',
            target_word_count: body.target_word_count ?? null,
            entry_id: body.entry_id ?? null,
            parent_id: body.parent_id ?? null,
            sort_order: 0,
            created_at: null,
            updated_at: null,
          },
        })
        return
      }
      await route.fulfill({ json: outlineItems })
      return
    }
    if (url.pathname === '/api/collections/collection-a/outline/order') {
      await route.fulfill({ json: outlineItems })
      return
    }
    if (url.pathname.startsWith('/api/collections/collection-a/outline/')) {
      if (request.method() === 'DELETE') {
        await route.fulfill({ status: 204 })
        return
      }
      const itemId = url.pathname.split('/').pop() ?? 'outline-created'
      const existing = outlineItems.find((item) => item.id === itemId) ?? outlineItems[0]
      await route.fulfill({
        json: {
          ...existing,
          ...(request.method() === 'PUT' ? request.postDataJSON() as Record<string, unknown> : {}),
        },
      })
      return
    }
    if (url.pathname === '/api/collections/collection-a') {
      if (request.method() === 'PUT') {
        await route.fulfill({ json: { ...collection, ...(request.postDataJSON() as object) } })
        return
      }
      if (request.method() === 'DELETE') {
        await route.fulfill({ status: 204 })
        return
      }
      await route.fulfill({ json: collection })
      return
    }
    await route.fallback()
  })
  await page.route('**/api/collections', async (route) => {
    const request = route.request()
    if (request.method() === 'POST') {
      await route.fulfill({ status: 201, json: { ...collection, id: 'collection-created', ...(request.postDataJSON() as object), article_count: 0 } })
      return
    }
    await route.fulfill({ json: [collection] })
  })

  await page.route('**/api/library/stats', async (route) => {
    await route.fulfill({ json: { total: 1, by_usage_kind: { style: 1 } } })
  })
  await page.route('**/api/library/references?**', async (route) => route.fulfill({ json: [existingReference] }))
  await page.route('**/api/library/references/search?**', async (route) => route.fulfill({ json: [existingReference] }))
  await page.route('**/api/library/references', async (route) => {
    if (route.request().method() === 'POST') {
      const data = route.request().postDataJSON() as Partial<typeof reference>
      await route.fulfill({ status: 201, json: { ...reference, ...data } })
      return
    }
    await route.fallback()
  })
  await page.route('**/api/library/references/*', async (route) => {
    const request = route.request()
    if (request.method() === 'DELETE') {
      await route.fulfill({ status: 204 })
      return
    }
    if (request.method() === 'PUT') {
      await route.fulfill({ json: { ...existingReference, ...(request.postDataJSON() as object) } })
      return
    }
    await route.fulfill({ json: existingReference })
  })

  const visualMotif = {
    id: 'motif-visual',
    name: language === 'zh' ? '旧信' : 'Old letter',
    aliases: [],
    note: '',
    profile: {
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
    },
    tags: [],
    pinned: false,
    excerpt_count: 0,
    created_at: null,
    updated_at: null,
  }
  await page.route(/\/api\/motifs(?:\/|\?|$)/, async (route) => {
    const url = new URL(route.request().url())
    if (url.pathname === '/api/motifs') {
      await route.fulfill({ json: [visualMotif] })
      return
    }
    if (url.pathname === '/api/motifs/graph' || url.pathname === `/api/motifs/${visualMotif.id}/graph`) {
      await route.fulfill({
        json: {
          nodes: [{ id: visualMotif.id, name: visualMotif.name, excerpt_count: 0, pinned: false, is_center: true }],
          edges: [],
        },
      })
      return
    }
    if (url.pathname === `/api/motifs/${visualMotif.id}/excerpts`) {
      await route.fulfill({ json: [] })
      return
    }
    await route.fulfill({ json: [] })
  })

  await page.route('**/api/ai-cards**', async (route) => {
    const url = new URL(route.request().url())
    const cards = [
      {
        id: 'card-a',
        title: '克制风格',
        content: '少用夸张表达。',
        card_type: 'style',
        tags: [],
        created_at: null,
        updated_at: null,
      },
      {
        id: 'scene-a',
        title: '等待回应',
        content: '【场景原型】\n一方表达后等待回应。\n\n【参考原文（可选）】\n第一句\n第二句\n第三句\n第四句',
        card_type: 'scene',
        tags: [],
        created_at: null,
        updated_at: null,
      },
    ]
    if (url.pathname === '/api/ai-cards/search') {
      const cardType = url.searchParams.get('card_type')
      const q = url.searchParams.get('q') || ''
      await route.fulfill({
        json: cards.filter((card) =>
          (!cardType || card.card_type === cardType)
          && (card.title.includes(q) || card.content.includes(q))
        ),
      })
      return
    }
    await route.fulfill({ json: cards })
  })
  await page.route('**/api/ai/task-presets', async (route) => route.fulfill({ json: {} }))
  await page.route('**/api/settings/ai/profiles', async (route) => {
    await route.fulfill({
      json: {
        profiles: [
          {
            id: 'profile-gemini',
            name: 'Gemini 测试',
            provider_name: 'gemini',
            base_url: 'https://relay.example',
            wire_api: 'responses',
            model: 'gemini-test-model',
            api_key_source: 'env:GEMINI_API_KEY',
            gemini_cli_proxy: null,
            enabled: true,
            is_default: true,
            test_status: 'passed',
            diagnostic_code: '',
            diagnostic_message: '',
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
          },
          {
            id: 'profile-deepseek',
            name: 'DeepSeek 测试',
            provider_name: 'openai',
            base_url: 'https://relay.example/v1',
            wire_api: 'chat_completions',
            model: 'deepseek-test-model',
            api_key_source: 'env:DEEPSEEK_API_KEY',
            gemini_cli_proxy: null,
            enabled: true,
            is_default: false,
            test_status: 'passed',
            diagnostic_code: '',
            diagnostic_message: '',
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
          },
        ],
        default_profile_id: 'profile-gemini',
      },
    })
  })
  await page.route('**/api/ai/task-runs**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    if (url.pathname === '/api/ai/task-runs/active') {
      await route.fulfill({ json: currentArticleTaskRun })
      return
    }
    if (url.pathname === '/api/ai/task-runs' && request.method() === 'POST') {
      const body = request.postDataJSON() as { article_id: string; task_type: string; profile_ids: string[]; selection_start?: number | null; selection_end?: number | null }
      articleTaskRunGetCount = 0
      currentArticleTaskRun = {
        run_id: 'article-run-1', article_id: body.article_id, article_title: article.title,
        task_type: body.task_type, article_hash: 'hash', original_text: article.body, selection_start: body.selection_start ?? null,
        selection_end: body.selection_end ?? null, status: 'queued', stage: 'queued', stage_label: '排队中', error: '',
        profiles: body.profile_ids.map((id) => ({ profile_id: id, profile_name: id === 'profile-gemini' ? 'Gemini 测试' : 'DeepSeek 测试', provider: id === 'profile-gemini' ? 'gemini' : 'openai', model: id === 'profile-gemini' ? 'gemini-test-model' : 'deepseek-test-model' })),
        results: body.profile_ids.map((id) => ({ profile_id: id, profile_name: id === 'profile-gemini' ? 'Gemini 测试' : 'DeepSeek 测试', provider: id === 'profile-gemini' ? 'gemini' : 'openai', model: id === 'profile-gemini' ? 'gemini-test-model' : 'deepseek-test-model', transport: null, status: 'pending', result: '', error: '', elapsed_ms: 0, input_tokens: null, output_tokens: null, cost: null, finish_reason: null, stats: { input_chars: article.body.length, output_chars: 0, delta_chars: -article.body.length, output_ratio: 0, input_paragraphs: 1, output_paragraphs: 0 } })),
        created_at: '2026-01-01T00:00:00Z', started_at: null, updated_at: '2026-01-01T00:00:00Z', completed_at: null, elapsed_ms: 0,
        applied_profile_id: null, applied_at: null, applied_version_id: null,
      }
      await route.fulfill({ status: 202, json: currentArticleTaskRun })
      return
    }
    if (!currentArticleTaskRun) {
      await route.fulfill({ status: 404, json: { detail: '任务不存在' } })
      return
    }
    if (url.pathname.endsWith('/cancel') && request.method() === 'POST') {
      currentArticleTaskRun = { ...currentArticleTaskRun, status: 'cancelled', stage: 'cancelled', stage_label: '已中断本地等待', error: '已停止本地等待。' }
      await route.fulfill({ json: currentArticleTaskRun })
      return
    }
    if (url.pathname.endsWith('/apply') && request.method() === 'POST') {
      const profileId = (request.postDataJSON() as { profile_id: string }).profile_id
      const result = (currentArticleTaskRun.results as Array<Record<string, any>>).find((item) => item.profile_id === profileId)
      currentArticleTaskRun = { ...currentArticleTaskRun, applied_profile_id: profileId, applied_at: '2026-01-01T00:00:02Z', applied_version_id: 'version-before-ai' }
      await route.fulfill({ json: { run: currentArticleTaskRun, entry: { ...article, body: result?.result || article.body }, version_id: 'version-before-ai', was_noop: false } })
      return
    }
    if (request.method() === 'DELETE') {
      currentArticleTaskRun = null
      await route.fulfill({ status: 204 })
      return
    }
    articleTaskRunGetCount += 1
    const results = (currentArticleTaskRun.results as Array<Record<string, any>>).map((item, index) => {
      if (articleTaskRunGetCount === 1 && index > 0) return item
      const output = item.profile_id === 'profile-gemini' ? 'Gemini 增量结果' : 'DeepSeek 增量结果'
      return { ...item, status: 'success', result: output, transport: item.profile_id === 'profile-gemini' ? 'gemini_native' : 'chat_completions', elapsed_ms: index ? 240 : 80, input_tokens: 8, output_tokens: 12, cost: 0.001, stats: { ...item.stats, output_chars: output.length, delta_chars: output.length - article.body.length, output_ratio: 0.5, output_paragraphs: 1 } }
    })
    const done = results.every((item) => item.status === 'success')
    currentArticleTaskRun = { ...currentArticleTaskRun, results, status: done ? 'succeeded' : 'running', stage: done ? 'succeeded' : 'collecting_results', stage_label: done ? '已完成' : '正在收集模型结果', elapsed_ms: done ? 240 : 80 }
    await route.fulfill({ json: currentArticleTaskRun })
  })
  await page.route('**/api/ai/task/compare/stream', async (route) => fulfillCompareStream(route))
  await page.route('**/api/ai/task', async (route) => {
    await route.fulfill({ json: { result: 'AI 生成结果', task_type: (route.request().postDataJSON() as { task_type?: string }).task_type ?? 'polish' } })
  })
  await page.route('**/api/ai/chat', async (route) => {
    await route.fulfill({
      json: {
        thread_id: 'thread-a',
        user_message: {
          id: 'message-user',
          thread_id: 'thread-a',
          role: 'user',
          content: (route.request().postDataJSON() as { message?: string }).message ?? '',
          timestamp: null,
        },
        assistant_message: {
          id: 'message-assistant',
          thread_id: 'thread-a',
          role: 'assistant',
          content: '这是 AI 回复。',
          timestamp: null,
          meta: { provider: 'fake', model: 'fake-model', transport: 'chat_completions' },
        },
      },
    })
  })
  await page.route('**/api/ai/chat-settings', async (route) => {
    await route.fulfill({ json: { system_prompt: '' } })
  })
  await page.route('**/api/ai/threads**', async (route) => {
    const url = new URL(route.request().url())
    if (url.pathname === '/api/ai/threads/current') {
      await route.fulfill({ json: { thread: {
        id: 'thread-a',
        title: '导出测试文章',
        scope_kind: 'article',
        scope_id: article.id,
        created_at: null,
        updated_at: null,
      }, messages: [] } })
      return
    }
    await route.fulfill({ json: [] })
  })
}

test.beforeEach(async ({ page }) => {
  await mockVisibleActionApi(page)
})

test('article export buttons trigger downloads for MD, TXT, and DOCX', async ({ page }) => {
  await page.goto('/articles?id=article-a')
  await expectArticleEditorBody(page, article.body)

  for (const format of ['md', 'txt', 'docx']) {
    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: format }).click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe(`导出测试文章.${format}`)
  }
})

test('article delete asks for confirmation before calling the destructive API', async ({ page }) => {
  let deleteRequests = 0
  await page.route('**/api/articles/article-a', async (route) => {
    if (route.request().method() === 'DELETE') {
      deleteRequests += 1
      await route.fulfill({ status: 204 })
      return
    }
    await route.fallback()
  })

  await page.goto('/articles?id=article-a')
  page.once('dialog', async (dialog) => dialog.dismiss())
  await page.getByTestId('article-action-delete').click()
  expect(deleteRequests).toBe(0)

  await page.getByTestId('article-entry-article-a').click({ button: 'right' })
  await expect(page.getByTestId('context-menu')).toBeVisible()
  page.once('dialog', async (dialog) => dialog.accept())
  await page.getByTestId('context-menu').getByRole('button', { name: '删除' }).click()
  await expect.poll(() => deleteRequests).toBe(1)
})

test('article delete failures show a visible error', async ({ page }) => {
  await page.route('**/api/articles/article-a', async (route) => {
    if (route.request().method() === 'DELETE') {
      await route.fulfill({ status: 500, json: { detail: '删除文章失败' } })
      return
    }
    await route.fulfill({ json: article })
  })

  await page.goto('/articles?id=article-a')
  page.once('dialog', async (dialog) => dialog.accept())
  await page.getByTestId('article-action-delete').click()

  await expect(page.getByText('删除文章失败')).toBeVisible()
  await expectArticleEditorBody(page, article.body)
})

test('article sidebar new button shows a visible error when creation fails', async ({ page }) => {
  await page.route('**/api/articles', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({ status: 500, json: { detail: '磁盘不可写' } })
      return
    }
    await route.fulfill({ json: [article, articleB] })
  })

  await page.goto('/articles?id=article-a')
  await page.getByRole('button', { name: '+ 新建', exact: true }).click()

  await expect(page.getByText('磁盘不可写')).toBeVisible()
})

test('quick capture can save a real article and protects dirty cancel', async ({ page }) => {
  const createdArticles: Array<Record<string, unknown>> = []

  await page.route('**/api/articles', async (route) => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON() as Record<string, unknown>
      createdArticles.push(body)
      await route.fulfill({ status: 201, json: { ...article, ...body, id: 'quick-capture-created' } })
      return
    }
    await route.fulfill({ json: [article, articleB] })
  })

  await page.goto('/dates')
  await page.keyboard.down('Control')
  await page.keyboard.down('Shift')
  await page.keyboard.press('KeyN')
  await page.keyboard.up('Shift')
  await page.keyboard.up('Control')
  await expect(page.getByRole('heading', { name: '快速捕获' })).toBeVisible()

  await page.getByPlaceholder('开始输入你的想法...').fill('未保存的灵感')
  page.once('dialog', async (dialog) => dialog.dismiss())
  await page.getByRole('button', { name: '取消' }).click()
  await expect(page.getByRole('heading', { name: '快速捕获' })).toBeVisible()

  await page.getByPlaceholder('标题（可选）').fill('快速标题')
  await page.getByPlaceholder('开始输入你的想法...').fill('快速正文第一行\n第二行')
  await page.getByRole('button', { name: '保存' }).click()
  await expect.poll(() => createdArticles).toEqual([
    {
      title: '快速标题',
      body: '快速正文第一行\n第二行',
      tags: ['quick-capture'],
    },
  ])
  await expect(page.getByRole('heading', { name: '快速捕获' })).toHaveCount(0)
})

test('quick capture save failures stay in the dialog and keep the draft', async ({ page }) => {
  await page.route('**/api/articles', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({ status: 500, json: { detail: '磁盘已满' } })
      return
    }
    await route.fulfill({ json: [article, articleB] })
  })

  await page.goto('/dates')
  await page.keyboard.down('Control')
  await page.keyboard.down('Shift')
  await page.keyboard.press('KeyN')
  await page.keyboard.up('Shift')
  await page.keyboard.up('Control')

  await expect(page.getByRole('heading', { name: '快速捕获' })).toBeVisible()
  await page.getByPlaceholder('标题（可选）').fill('失败标题')
  await page.getByPlaceholder('开始输入你的想法...').fill('失败后仍应保留的正文')
  await page.getByRole('button', { name: '保存' }).click()

  await expect(page.getByText('磁盘已满')).toBeVisible()
  await expect(page.getByPlaceholder('标题（可选）')).toHaveValue('失败标题')
  await expect(page.getByPlaceholder('开始输入你的想法...')).toHaveValue('失败后仍应保留的正文')
  await expect(page.getByRole('heading', { name: '快速捕获' })).toBeVisible()
})

test('article find and replace updates the editor and autosaves the change', async ({ page }) => {
  const updates: Array<{ body?: string }> = []

  await page.route('**/api/articles/article-a', async (route) => {
    const request = route.request()
    if (request.method() === 'PUT') {
      const body = request.postDataJSON() as { body?: string }
      updates.push(body)
      await route.fulfill({ json: { ...article, ...body } })
      return
    }
    await route.fulfill({ json: article })
  })

  await page.goto('/articles?id=article-a')
  await expectArticleEditorBody(page, article.body)

  await page.getByTitle('查找与替换 (Ctrl+F)').click()
  await page.getByPlaceholder('查找').fill('正文')
  await expect(page.getByText('1/2')).toBeVisible()
  await page.getByRole('button', { name: '下一处' }).click()
  await expect.poll(() => page.getByTestId('article-body-editor').evaluate((textarea: HTMLTextAreaElement) => textarea.selectionStart)).toBe(11)
  await page.getByRole('button', { name: '上一处' }).click()
  await expect.poll(() => page.getByTestId('article-body-editor').evaluate((textarea: HTMLTextAreaElement) => textarea.selectionStart)).toBe(3)
  await page.getByRole('button', { name: '显示替换' }).click()
  await page.getByPlaceholder('替换为').fill('文本')
  await page.getByRole('button', { name: '全部替换' }).click()

  const expectedBody = '第一段文本。\n\n第二段文本。'
  await expect(page.getByTestId('article-body-editor')).toHaveValue(expectedBody)
  await expect.poll(() => updates.at(-1)?.body).toBe(expectedBody)
})

test('article find replace respects case sensitivity and replaces the active match', async ({ page }) => {
  const updates: Array<{ body?: string }> = []
  const latinArticle = {
    ...article,
    body: 'Alpha Alpha alpha',
  }

  await page.route('**/api/articles?**', async (route) => {
    await route.fulfill({ json: [latinArticle, articleB] })
  })
  await page.route('**/api/articles/article-a', async (route) => {
    const request = route.request()
    if (request.method() === 'PUT') {
      const body = request.postDataJSON() as { body?: string }
      updates.push(body)
      await route.fulfill({ json: { ...latinArticle, ...body } })
      return
    }
    await route.fulfill({ json: latinArticle })
  })

  await page.goto('/articles?id=article-a')
  const editor = page.getByTestId('article-body-editor')
  await expect(editor).toHaveValue('Alpha Alpha alpha')

  await page.getByTitle('查找与替换 (Ctrl+F)').click()
  await page.getByPlaceholder('查找').fill('Alpha')
  await page.getByRole('button', { name: '下一处' }).click()
  await expect.poll(() => editor.evaluate((textarea: HTMLTextAreaElement) => textarea.selectionStart)).toBe(6)
  await page.getByRole('button', { name: '显示替换' }).click()
  await page.getByPlaceholder('替换为').fill('Beta')
  await page.getByRole('button', { name: '替换', exact: true }).click()
  await expect(editor).toHaveValue('Alpha Beta alpha')

  await page.getByPlaceholder('查找').fill('alpha')
  await page.getByLabel('区分大小写').check()
  await page.getByPlaceholder('替换为').fill('gamma')
  await page.getByRole('button', { name: '全部替换' }).click()

  const expectedBody = 'Alpha Beta gamma'
  await expect(editor).toHaveValue(expectedBody)
  await expect.poll(() => updates.at(-1)?.body).toBe(expectedBody)
})

test('article pending edits are flushed before switching, AI chat, and archive actions', async ({ page }) => {
  const updates: Array<Record<string, unknown>> = []
  const archiveRequests: string[] = []

  await page.route('**/api/articles/article-a/archive', async (route) => {
    archiveRequests.push(route.request().method())
    await route.fulfill({ json: { ...article, archived_at: '2026-06-19T00:00:00Z' } })
  })
  await page.route('**/api/articles/article-a', async (route) => {
    const request = route.request()
    if (request.method() === 'PUT') {
      const body = request.postDataJSON() as Record<string, unknown>
      updates.push(body)
      await route.fulfill({ json: { ...article, ...body } })
      return
    }
    await route.fulfill({ json: article })
  })

  await page.goto('/articles?id=article-a')
  await expectArticleEditorBody(page, article.body)

  await page.getByTestId('article-body-editor').fill('切换前未保存正文')
  await page.getByTestId('article-entry-article-b').click()
  await expect.poll(() => updates.some((body) => body.body === '切换前未保存正文')).toBe(true)
  await expect(page.getByTestId('article-body-editor')).toHaveValue(articleB.body)

  await page.goto('/articles?id=article-a')
  await page.getByTestId('article-body-editor').fill('AI 对话前未保存正文')
  await page.getByRole('button', { name: 'AI 对话', exact: true }).click()
  await expect.poll(() => updates.some((body) => body.body === 'AI 对话前未保存正文')).toBe(true)
  await expect(page.getByTestId('article-ai-chat-drawer')).toBeVisible()
  await expect(page).toHaveURL(/\/articles\?.*id=article-a/)

  await page.goto('/articles?id=article-a')
  await page.getByTestId('article-body-editor').fill('归档前未保存正文')
  await page.getByRole('button', { name: '归档', exact: true }).click()
  await expect.poll(() => updates.some((body) => body.body === '归档前未保存正文')).toBe(true)
  await expect.poll(() => archiveRequests).toEqual(['POST'])
})

test('article writing notes can be added, pinned, edited, completed, restored, and deleted', async ({ page }) => {
  const requests = {
    created: [] as Array<Record<string, unknown>>,
    updated: [] as Array<Record<string, unknown>>,
    pinned: [] as Array<Record<string, unknown>>,
    done: [] as Array<Record<string, unknown>>,
    deleted: 0,
  }
  let notes = [
    { ...openNote },
    {
      ...openNote,
      id: 'note-done',
      body: '已经完成的便签',
      status: 'done',
      pinned: false,
      sort_order: 1,
      completed_at: '2026-06-19T00:00:00Z',
    },
  ]

  await page.route('**/api/articles/article-a/notes**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const parts = url.pathname.split('/')
    const noteId = parts[5]

    if (url.pathname === '/api/articles/article-a/notes') {
      if (request.method() === 'POST') {
        const body = request.postDataJSON() as { body?: string; pinned?: boolean }
        requests.created.push(body)
        const created = {
          ...openNote,
          id: 'note-created',
          body: body.body ?? '',
          pinned: body.pinned ?? false,
          sort_order: 0,
        }
        notes = [created, ...notes]
        await route.fulfill({ status: 201, json: created })
        return
      }
      await route.fulfill({ json: notes })
      return
    }

    const existing = notes.find((note) => note.id === noteId) ?? notes[0]
    if (url.pathname.endsWith('/pinned') && request.method() === 'PUT') {
      const body = request.postDataJSON() as { pinned?: boolean }
      requests.pinned.push(body)
      const updated = { ...existing, pinned: Boolean(body.pinned) }
      notes = notes.map((note) => note.id === noteId ? updated : note)
      await route.fulfill({ json: updated })
      return
    }
    if (url.pathname.endsWith('/done') && request.method() === 'PUT') {
      const body = request.postDataJSON() as { done?: boolean }
      requests.done.push(body)
      const updated = {
        ...existing,
        status: body.done ? 'done' : 'open',
        completed_at: body.done ? '2026-06-19T01:00:00Z' : null,
      }
      notes = notes.map((note) => note.id === noteId ? updated : note)
      await route.fulfill({ json: updated })
      return
    }
    if (request.method() === 'PUT') {
      const body = request.postDataJSON() as { body?: string }
      requests.updated.push(body)
      const updated = { ...existing, body: body.body ?? existing.body }
      notes = notes.map((note) => note.id === noteId ? updated : note)
      await route.fulfill({ json: updated })
      return
    }
    if (request.method() === 'DELETE') {
      requests.deleted += 1
      notes = notes.filter((note) => note.id !== noteId)
      await route.fulfill({ status: 204 })
      return
    }
    await route.fulfill({ json: existing })
  })

  await page.goto('/articles?id=article-a')
  await expect(page.getByText('文章便签')).toBeVisible()

  await page.getByPlaceholder('记下接下来怎么写、要保留的意象或需要提醒自己的想法…').fill('新的写作提醒')
  await page.getByRole('button', { name: '添加便签' }).click()
  await expect.poll(() => requests.created).toEqual([{ body: '新的写作提醒', pinned: false }])
  await expect(page.getByText('新的写作提醒')).toBeVisible()

  const createdCard = page.locator('article').filter({ hasText: '新的写作提醒' }).first()
  await createdCard.getByRole('button', { name: '置顶' }).click()
  await expect.poll(() => requests.pinned.at(-1)).toEqual({ pinned: true })
  await expect(createdCard.getByRole('button', { name: '取消置顶' })).toBeVisible()

  await createdCard.getByRole('button', { name: '编辑' }).click()
  const editingCard = page.locator('article').filter({ has: page.locator('textarea') }).first()
  await editingCard.locator('textarea').fill('修改后的写作提醒')
  await editingCard.getByRole('button', { name: '保存' }).click()
  await expect.poll(() => requests.updated).toEqual([{ body: '修改后的写作提醒' }])
  await expect(page.getByText('修改后的写作提醒')).toBeVisible()

  const updatedCard = page.locator('article').filter({ hasText: '修改后的写作提醒' }).first()
  await updatedCard.getByRole('button', { name: '完成' }).click()
  await expect.poll(() => requests.done.at(-1)).toEqual({ done: true })
  await expect(page.getByRole('button', { name: /显示已完成/ })).toBeVisible()

  await page.getByRole('button', { name: /显示已完成/ }).click()
  await expect(page.getByText('修改后的写作提醒')).toBeVisible()
  const completedCard = page.locator('article').filter({ hasText: '修改后的写作提醒' }).first()
  await completedCard.getByRole('button', { name: '恢复' }).click()
  await expect.poll(() => requests.done.at(-1)).toEqual({ done: false })

  const restoredCard = page.locator('article').filter({ hasText: '修改后的写作提醒' }).first()
  page.once('dialog', async (dialog) => dialog.dismiss())
  await restoredCard.getByRole('button', { name: '删除' }).click()
  expect(requests.deleted).toBe(0)

  await restoredCard.click({ button: 'right' })
  await expect(page.getByTestId('context-menu')).toBeVisible()
  page.once('dialog', async (dialog) => dialog.accept())
  await page.getByTestId('context-menu').getByRole('button', { name: '删除' }).click()
  await expect.poll(() => requests.deleted).toBe(1)
})

test('article motif anchors show linked motifs without exposing source sentences and can jump to the motif', async ({ page }) => {
  const motif = {
    id: 'motif-anchor',
    name: '海德格尔的常人',
    aliases: ['das Man'],
    note: '',
    profile: {
      definition: '人在公共意见中失去自己的判断。',
      core_tension: '自我判断和公共意见之间的拉扯。',
      writing_functions: ['制造日常压迫感'],
      scene_triggers: ['公共场合'],
      character_signals: ['用大家都这么说替代判断'],
      imagery_translations: [],
      short_examples: [],
      misuse_warnings: [],
      micro_exercises: [],
      source_hints: [],
    },
    tags: ['哲学'],
    pinned: false,
    excerpt_count: 1,
    created_at: null,
    updated_at: null,
  }
  const anchorStart = article.body.indexOf('第二段正文')
  const excerpt = {
    id: 'excerpt-anchor',
    source_kind: 'article',
    source_id: article.id,
    source_title_snapshot: article.title,
    excerpt_text: '第二段正文。',
    note: '',
    selection_start: anchorStart,
    selection_end: anchorStart + '第二段正文。'.length,
    before_context: '第一段正文。',
    after_context: '',
    motif_ids: [motif.id],
    motif_names: [motif.name],
    source_exists: true,
    source_current_title: article.title,
    created_at: null,
    updated_at: null,
  }

  await page.route(/\/api\/motifs(?:\/|\?|$)/, async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    if (url.pathname === '/api/motifs') {
      await route.fulfill({ json: [motif] })
      return
    }
    if (url.pathname === '/api/motifs/graph' || url.pathname === `/api/motifs/${motif.id}/graph`) {
      await route.fulfill({
        json: {
          nodes: [{ id: motif.id, name: motif.name, excerpt_count: 1, pinned: false, is_center: true }],
          edges: [],
        },
      })
      return
    }
    if (url.pathname === `/api/motifs/${motif.id}/excerpts`) {
      await route.fulfill({ json: [excerpt] })
      return
    }
    if (url.pathname === '/api/motifs/excerpts/source/article/article-a') {
      await route.fulfill({ json: [excerpt] })
      return
    }
    await route.fulfill({ json: [] })
  })
  await page.route('**/api/articles/article-a', async (route) => {
    await route.fulfill({ json: article })
  })

  await page.goto('/articles?id=article-a')
  const editor = page.getByTestId('article-body-editor')
  await expect(editor).toHaveValue(article.body, { timeout: 20000 })

  const anchors = page.getByTestId('article-motif-anchors')
  await expect(anchors.getByText('海德格尔的常人')).toBeVisible()
  await expect(anchors.getByText('1 处')).toBeVisible()
  await expect(anchors.getByText('第二段正文。')).toHaveCount(0)

  await anchors.getByRole('button', { name: '定位' }).click()
  await expect(page).toHaveURL(/motif_excerpt=excerpt-anchor/)
  await expect.poll(async () => editor.evaluate((node) => (node as HTMLTextAreaElement).selectionStart)).toBe(anchorStart)

  await anchors.getByRole('button', { name: '打开意象' }).click()
  await expect(page).toHaveURL(/\/motifs\?.*id=motif-anchor/)
})

test('article list filters, context pane, save, AI navigation, archive, and collection picker actions work', async ({ page }) => {
  const updates: Array<Record<string, unknown>> = []
  const archiveRequests: string[] = []
  const addedToCollections: string[][] = []

  await page.route('**/api/articles/search?**', async (route) => {
    const query = new URL(route.request().url()).searchParams.get('q')
    await route.fulfill({ json: query === '备选' ? [articleB] : [] })
  })
  await page.route('**/api/articles/article-a/archive', async (route) => {
    archiveRequests.push(route.request().method())
    await route.fulfill({ json: { ...article, archived_at: '2026-06-19T00:00:00Z' } })
  })
  await page.route('**/api/articles/article-a', async (route) => {
    const request = route.request()
    if (request.method() === 'PUT') {
      const body = request.postDataJSON() as Record<string, unknown>
      updates.push(body)
      await route.fulfill({ json: { ...article, ...body } })
      return
    }
    await route.fulfill({ json: article })
  })
  await page.route('**/api/collections/for-entry/article-a', async (route) => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON() as { collection_ids?: string[] }
      addedToCollections.push(body.collection_ids ?? [])
      await route.fulfill({ json: [collection] })
      return
    }
    await route.fulfill({ json: [] })
  })

  await page.goto('/articles?id=article-a')
  await expectArticleEditorBody(page, article.body)

  await page.getByPlaceholder('搜索文章...').fill('备选')
  await expect(page.getByText('备选文章')).toBeVisible()
  await expect(page.getByText('导出测试文章')).toHaveCount(0)
  await page.locator('div').filter({ has: page.getByPlaceholder('搜索文章...') }).getByRole('button', { name: '×' }).click()
  await expect(page.getByPlaceholder('搜索文章...')).toHaveValue('')
  await expect(page.getByText('导出测试文章')).toBeVisible()

  await page.getByRole('button', { name: '备选' }).first().click()
  await expect(page.getByText('备选文章')).toBeVisible()
  await expect(page.getByText('导出测试文章')).toHaveCount(0)
  await page.getByRole('button', { name: '全部标签' }).click()
  await expect(page.getByText('导出测试文章')).toBeVisible()

  await page.getByRole('button', { name: '收起上下文' }).click()
  await expect(page.getByRole('button', { name: '显示上下文' })).toBeVisible()
  await page.getByRole('button', { name: '显示上下文' }).click()
  await expect(page.getByRole('button', { name: '收起上下文' })).toBeVisible()

  const saveRequestPromise = page.waitForRequest((request) =>
    request.method() === 'PUT' && new URL(request.url()).pathname === '/api/articles/article-a'
  )
  await page.getByTestId('article-body-editor').fill('自动保存正文')
  const saveRequest = await saveRequestPromise
  expect((saveRequest.postDataJSON() as Record<string, unknown>).body).toBe('自动保存正文')

  await page.getByRole('button', { name: 'AI 对话' }).click()
  await expect(page.getByTestId('article-ai-chat-drawer')).toBeVisible()
  await page.getByTestId('article-ai-chat-drawer').getByRole('button', { name: '关闭' }).click()

  await page.getByRole('main').getByRole('button', { name: 'AI 修改' }).click()
  await expect(page).toHaveURL(/\/ai\?/)
  await expect(page).toHaveURL(/scope_id=article-a/)

  await page.goto('/articles?id=article-a')
  await page.getByRole('button', { name: '归档' }).click()
  await expect.poll(() => archiveRequests).toEqual(['POST'])

  await page.goto('/articles?id=article-a')
  await page.getByRole('button', { name: '加入作品集' }).click()
  await page.getByRole('button', { name: /测试作品集/ }).click()
  await page.getByRole('button', { name: '确认' }).click()
  await expect.poll(() => addedToCollections).toEqual([[collection.id]])
  await page.getByRole('button', { name: '打开' }).click()
  await expect(page).toHaveURL(/\/collections\?.*id=collection-a/)
  await expect(page).toHaveURL(/article=article-a/)
})

test('dates calendar buttons, daily quote, welcome close, and start writing actions work', async ({ page }) => {
  const statsQueries: Array<{ year: string | null; month: string | null }> = []
  const createdArticles: Array<Record<string, unknown>> = []

  await page.route('**/api/dates/stats?**', async (route) => {
    const url = new URL(route.request().url())
    statsQueries.push({
      year: url.searchParams.get('year'),
      month: url.searchParams.get('month'),
    })
    await route.fulfill({ json: [] })
  })
  await page.route('**/api/dates/entries?**', async (route) => {
    await route.fulfill({ json: [] })
  })
  await page.route('**/api/dates/quote?**', async (route) => {
    await route.fulfill({
      json: {
        id: 'quote-a',
        reference_id: 'ref-existing',
        text: '今天的精句',
        source_title: '测试书',
        source_author: '测试作者',
      },
    })
  })
  await page.route('**/api/articles', async (route) => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON() as Record<string, unknown>
      createdArticles.push(body)
      await route.fulfill({ status: 201, json: { ...article, ...body, id: 'article-from-date' } })
      return
    }
    await route.fulfill({ json: [] })
  })

  await page.goto('/dates')
  await expect(page.getByText('今天的精句')).toBeVisible()

  await page.locator('aside').getByRole('button', { name: '文脉库' }).click()
  await expect(page).toHaveURL(/\/library\?.*ref=ref-existing/)
  await expect(page).toHaveURL(/group=source/)

  await page.goto('/dates')
  await page.getByRole('button', { name: '›' }).click()
  await page.getByRole('button', { name: '‹' }).click()
  await page.getByRole('button', { name: '今天' }).click()
  await expect.poll(() => statsQueries.length).toBeGreaterThanOrEqual(4)

  const welcomePanel = page.locator('section').filter({ hasText: '开始使用活着为了讲述' }).first()
  await expect(welcomePanel.getByText(/\/5 已完成/)).toBeVisible()
  await expect(welcomePanel.getByText('待完成').first()).toBeVisible()
  await updatePublicScreenshot(page, 'dates-onboarding.png')
  await welcomePanel.getByRole('button', { name: '查看备份与数据说明' }).click()
  await expect(page).toHaveURL(/\/backup/)

  await page.goto('/dates')
  const samplePanel = page.getByTestId('sample-project-panel')
  await expect(samplePanel.getByText('示例项目', { exact: true })).toBeVisible()
  await samplePanel.getByRole('button', { name: '创建示例项目' }).click()
  await expect(samplePanel.getByText('已安装')).toBeVisible()
  await expect(samplePanel.getByText('文章 2')).toBeVisible()
  await samplePanel.getByRole('button', { name: '打开作品集' }).click()
  await expect(page).toHaveURL(/\/collections/)

  await page.goto('/dates')
  page.once('dialog', async (dialog) => {
    expect(dialog.message()).toContain('只会删除应用为示例项目记录')
    await dialog.accept()
  })
  await page.getByTestId('sample-project-panel').getByRole('button', { name: '删除示例' }).click()
  await expect(page.getByTestId('sample-project-panel').getByText('可选')).toBeVisible()

  await welcomePanel.getByRole('button', { name: '关闭' }).click()
  await expect(page.getByText('开始使用活着为了讲述')).toHaveCount(0)

  await page.getByRole('button', { name: '开始写作' }).click()
  await expect.poll(() => createdArticles.length).toBe(1)
  expect(createdArticles[0]).toEqual(expect.objectContaining({
    body: '',
    tags: [],
  }))
  expect(String(createdArticles[0].title)).toContain('记录')
  await expect(page).toHaveURL(/\/articles\?.*id=article-from-date/)
})

test('backup center surfaces restore points, data paths, and safe restore confirmation', async ({ page }) => {
  await page.goto('/backup')

  const safety = page.getByTestId('backup-safety-summary')
  const planner = page.getByTestId('backup-restore-planner')
  await expect(safety.getByText(/当前有可用恢复点|建议更新备份/)).toBeVisible()
  await expect(safety.getByText('自动备份', { exact: true })).toBeVisible()
  await expect(safety.getByText('检查点', { exact: true })).toBeVisible()
  await expect(planner.getByText('选择恢复点')).toBeVisible()
  await expect(planner.getByText('大修前检查点')).toBeVisible()
  await expect(planner.getByText('auto-20260628-090000.sqlite3')).toBeVisible()
  await updatePublicScreenshot(page, 'backup-center.png')

  await safety.locator('select').selectOption('14')
  await expect.poll(() => page.evaluate(() => localStorage.getItem('living_to_tell_backup_reminder_days'))).toBe('14')

  await page.getByRole('button', { name: '复制' }).first().click()
  await expect.poll(() => page.evaluate(() => window.__copiedText)).toBe('D:\\LivingToTellData\\writer.db')
  await expect(page.getByText('路径已复制。')).toBeVisible()

  await planner.getByRole('button', { name: /大修前检查点/ }).click()
  await planner.getByRole('button', { name: '恢复所选' }).click()
  await expect(page.getByRole('heading', { name: '确认操作' })).toBeVisible()
  await expect(page.getByText('确定要从"大修前检查点"恢复吗？当前数据库会先自动备份，恢复后应用将重启。')).toBeVisible()
  await page.getByRole('button', { name: '取消' }).click()
  await expect(page.getByRole('heading', { name: '确认操作' })).toHaveCount(0)
})

test('date article cards open the selected article from the calendar', async ({ page }) => {
  await page.goto('/dates')

  await page.locator('article').filter({ hasText: '导出测试文章' }).click()

  await expect(page).toHaveURL(/\/articles\?.*id=article-a/)
  await expectArticleEditorBody(page, article.body)
})

test('command palette groups commands and searches local writing content', async ({ page }) => {
  await page.unroute('**/api/articles/search?**')
  await page.route('**/api/articles/search?**', async (route) => route.fulfill({ json: [article] }))

  await page.goto('/dates')

  await page.keyboard.press('Control+K')
  await expect(page.getByPlaceholder('搜索命令、文章、作品集、文脉、意象或 AI 卡片...')).toBeVisible()
  await expect(page.getByText('常用命令', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: /今天写作/ })).toBeVisible()
  await expect(page.getByRole('button', { name: /新建文脉标本/ })).toBeVisible()

  await page.getByPlaceholder('搜索命令、文章、作品集、文脉、意象或 AI 卡片...').fill('导出测试')
  await expect(page.getByText('文章').first()).toBeVisible()
  await expect(page.getByRole('button', { name: /导出测试文章/ })).toBeVisible()

  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/articles\?.*id=article-a/)
  await expectArticleEditorBody(page, article.body)
})

test('welcome checklist creates a real reference and opens article chat with article scope', async ({ page }) => {
  await page.goto('/dates')

  const createReferenceRequest = page.waitForRequest((request) =>
    request.method() === 'POST' && request.url().includes('/api/library/references')
  )
  await page.getByRole('button', { name: '建立第一条文脉标本' }).click()
  await createReferenceRequest
  await expect(page).toHaveURL(/\/library\?.*ref=ref-created/)

  await page.goto('/dates')
  await page.getByRole('button', { name: '从文章进入 AI 对话' }).click()
  await expect(page).toHaveURL(/\/articles\?.*id=article-a/)
  await expect(page.getByTestId('article-ai-chat-drawer')).toBeVisible()
})

test('runtime close dialog controls call the native close action', async ({ page }) => {
  await page.addInitScript(() => {
    window.__closeInvokes = []
    window.__tauriEventHandlers = {}
    let nextEventId = 0
    Object.defineProperty(window, '__TAURI_INTERNALS__', {
      value: {
        metadata: { currentWindow: { label: 'main' } },
        invoke: async (command: string, args?: Record<string, unknown>) => {
          window.__closeInvokes?.push({ command, args })
          if (command === 'get_api_base_url') return 'http://backend.test'
          if (command === 'get_close_preference') return 'ask'
          if (command === 'set_close_preference') return args?.preference
          if (command === 'plugin:event|listen') return args?.handler
          if (command === 'plugin:event|unlisten') return null
          if (command === 'resolve_close_action') return args?.action
          return null
        },
        transformCallback: (callback: (event: { event: string; id: number; payload: unknown }) => void) => {
          nextEventId += 1
          window.__tauriEventHandlers![nextEventId] = callback
          return nextEventId
        },
        unregisterCallback: () => undefined,
      },
      configurable: true,
    })
  })

  const triggerCloseDialog = async () => {
    await page.evaluate(() => {
      const handlers = Object.values(window.__tauriEventHandlers ?? {})
      for (const [index, handler] of handlers.entries()) {
        handler({ event: 'writer-confirm-close', id: index + 1, payload: null })
      }
    })
  }

  await page.goto('/dates')
  await expect.poll(async () => page.evaluate(() => Object.keys(window.__tauriEventHandlers ?? {}).length)).toBeGreaterThan(0)

  await triggerCloseDialog()
  await expect(page.getByRole('heading', { name: '关闭活着为了讲述' })).toBeVisible()
  await page.getByRole('button', { name: '取消' }).click()
  await expect(page.getByRole('heading', { name: '关闭活着为了讲述' })).toHaveCount(0)

  await triggerCloseDialog()
  await page.getByRole('button', { name: '直接退出' }).click()
  await page.getByLabel('记住我的选择').check()
  await page.getByRole('button', { name: '确认' }).click()

  await expect.poll(async () => page.evaluate(() =>
    window.__closeInvokes?.some((item) =>
      item.command === 'resolve_close_action'
      && item.args?.action === 'exit'
      && item.args?.remember === true
    ) ?? false
  )).toBe(true)
})

test('command palette does not expose misleading search or unsafe reload commands', async ({ page }) => {
  await page.goto('/dates')
  await expect(page.getByRole('button', { name: '日期' })).toBeVisible()
  await page.locator('body').click()
  await page.keyboard.down('Control')
  await page.keyboard.press('KeyK')
  await page.keyboard.up('Control')

  await expect(page.getByPlaceholder(/搜索命令|Search commands/)).toBeVisible()
  await expect(page.getByText('新建文章')).toBeVisible()
  await expect(page.getByText('搜索文章')).toHaveCount(0)
  await expect(page.getByText('重新加载应用')).toHaveCount(0)
})

test('app shell navigation, language, focus mode, and command palette actions work', async ({ page }) => {
  const createdArticles: Array<Record<string, unknown>> = []
  const createdCollections: Array<Record<string, unknown>> = []

  await page.route('**/api/articles', async (route) => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON() as Record<string, unknown>
      createdArticles.push(body)
      await route.fulfill({ status: 201, json: { ...article, ...body, id: 'article-shell-created' } })
      return
    }
    await route.fulfill({ json: [article, articleB] })
  })
  await page.route('**/api/collections', async (route) => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON() as Record<string, unknown>
      createdCollections.push(body)
      await route.fulfill({ status: 201, json: { ...collection, ...body, id: 'collection-shell-created', article_count: 0 } })
      return
    }
    await route.fulfill({ json: [collection] })
  })

  await page.goto('/dates')
  await page.getByRole('button', { name: '文章' }).click()
  await expect(page).toHaveURL(/\/articles/)
  await page.getByRole('button', { name: '设置' }).click()
  await expect(page).toHaveURL(/\/settings/)

  await page.getByRole('button', { name: '中', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Articles' })).toBeVisible()
  await page.getByRole('button', { name: 'EN', exact: true }).click()
  await expect(page.getByRole('button', { name: '文章' })).toBeVisible()

  await page.getByTitle('专注模式 (F11)').click()
  await expect(page.getByRole('button', { name: '退出专注模式 (F11)' })).toBeVisible()
  await page.getByRole('button', { name: '退出专注模式 (F11)' }).click()
  await expect(page.getByRole('button', { name: '日期' })).toBeVisible()

  await page.locator('body').click()
  await page.keyboard.down('Control')
  await page.keyboard.press('KeyK')
  await page.keyboard.up('Control')
  await page.getByText('新建文章').click()
  await expect.poll(() => createdArticles.length).toBe(1)
  await expect(page).toHaveURL(/\/articles/)

  await page.locator('body').click()
  await page.keyboard.down('Control')
  await page.keyboard.press('KeyK')
  await page.keyboard.up('Control')
  await page.getByText('新建作品集').click()
  await expect.poll(() => createdCollections.length).toBe(1)
  await expect(page).toHaveURL(/\/collections/)
})

test('collection export buttons trigger downloads and article management actions call real APIs', async ({ page }) => {
  test.setTimeout(60_000)
  const addedRequests: string[][] = []
  let removedRequests = 0
  let deleteCollectionRequests = 0
  const outlineCreateRequests: Array<Record<string, unknown>> = []

  await page.route('**/api/collections/collection-a/articles', async (route) => {
    const request = route.request()
    if (request.method() === 'POST') {
      const body = request.postDataJSON() as { entry_ids?: string[] }
      addedRequests.push(body.entry_ids ?? [])
      await route.fulfill({ json: [collectionArticle, collectionArticleB] })
      return
    }
    await route.fulfill({ json: [collectionArticle] })
  })
  await page.route('**/api/collections/collection-a/articles/order', async (route) => {
    await route.fulfill({ json: [collectionArticleB, collectionArticle] })
  })
  await page.route('**/api/collections/collection-a/outline', async (route) => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON() as Record<string, unknown>
      outlineCreateRequests.push(body)
      await route.fulfill({
        status: 201,
        json: {
          id: `outline-created-${outlineCreateRequests.length}`,
          collection_id: collection.id,
          parent_id: body.parent_id ?? null,
          entry_id: body.entry_id ?? null,
          title: body.title ?? '新结构节点',
          item_type: body.item_type ?? 'scene',
          status: body.status ?? 'idea',
          summary: body.summary ?? '',
          notes: body.notes ?? '',
          pov: body.pov ?? '',
          setting: body.setting ?? '',
          timeline: body.timeline ?? '',
          tags: body.tags ?? [],
          target_word_count: body.target_word_count ?? null,
          sort_order: outlineItems.length + outlineCreateRequests.length,
          created_at: null,
          updated_at: null,
        },
      })
      return
    }
    await route.fulfill({ json: outlineItems })
  })
  await page.route('**/api/collections/collection-a/articles/article-b', async (route) => {
    if (route.request().method() === 'DELETE') {
      removedRequests += 1
      await route.fulfill({ status: 204 })
      return
    }
    await route.fallback()
  })
  await page.route('**/api/collections/collection-a', async (route) => {
    if (route.request().method() === 'DELETE') {
      deleteCollectionRequests += 1
      await route.fulfill({ status: 204 })
      return
    }
    await route.fulfill({ json: collection })
  })

  await page.goto('/collections')
  await expect(page.getByRole('heading', { name: '测试作品集', exact: true })).toBeVisible({ timeout: 20000 })

  await page.getByRole('complementary').getByRole('button', { name: '+ 新建', exact: true }).click()
  await expect(page.getByRole('heading', { name: '新建作品集' })).toBeVisible()
  await page.getByRole('button', { name: '取消' }).click()
  await expect(page.getByRole('heading', { name: '新建作品集' })).toHaveCount(0)

  await page.getByRole('button', { name: '导出', exact: true }).click()
  for (const [buttonName, extension] of [
    ['Markdown', 'md'],
    ['TXT', 'txt'],
    ['DOCX', 'docx'],
  ] as const) {
    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: buttonName, exact: true }).click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe(`测试作品集.${extension}`)
  }

  await page.getByRole('button', { name: '书稿' }).click()
  await page.getByRole('button', { name: '添加文章' }).first().click()
  await expect(page.getByRole('heading', { name: '添加文章到作品集' })).toBeVisible()
  await page.getByRole('button', { name: '取消' }).click()
  await expect(page.getByRole('heading', { name: '添加文章到作品集' })).toHaveCount(0)
  expect(addedRequests).toEqual([])

  await page.getByRole('button', { name: '添加文章' }).first().click()
  await page.getByRole('button', { name: /备选文章/ }).click()
  await page.getByRole('button', { name: /加入所选文章/ }).click()
  await expect.poll(() => addedRequests).toEqual([[articleB.id]])

  const unplannedCard = page.locator('article').filter({ hasText: '备选文章' }).first()
  await unplannedCard.hover()
  page.once('dialog', async (dialog) => dialog.dismiss())
  await unplannedCard.getByRole('button', { name: '移出作品集' }).click()
  expect(removedRequests).toBe(0)

  await unplannedCard.hover()
  page.once('dialog', async (dialog) => dialog.accept())
  await unplannedCard.getByRole('button', { name: '移出作品集' }).click()
  await expect.poll(() => removedRequests).toBe(1)

  await page.getByRole('button', { name: '添加文章' }).first().click()
  await page.getByRole('button', { name: /备选文章/ }).click()
  await page.getByRole('button', { name: /加入所选文章/ }).click()
  await expect.poll(() => addedRequests).toEqual([[articleB.id], [articleB.id]])
  await page.locator('article').filter({ hasText: '备选文章' }).getByRole('button', { name: '放到当前节点下' }).click()
  await expect.poll(() => outlineCreateRequests.at(-1)?.entry_id).toBe(articleB.id)
  expect(outlineCreateRequests.at(-1)?.parent_id).toBe('outline-part-a')

  page.once('dialog', async (dialog) => dialog.dismiss())
  await page.getByRole('button', { name: '更多操作' }).click()
  await page.getByRole('button', { name: '删除作品集' }).click()
  expect(deleteCollectionRequests).toBe(0)

  page.once('dialog', async (dialog) => dialog.accept())
  await page.getByRole('button', { name: '更多操作' }).click()
  await page.getByRole('button', { name: '删除作品集' }).click()
  await expect.poll(() => deleteCollectionRequests).toBe(1)
})

test('rapid collection switching ignores a late 404 from the previous collection', async ({ page }) => {
  const collectionB = {
    ...collection,
    id: 'collection-b',
    title: '第二个作品集',
    description: '当前应保持选中的作品集',
  }
  const articleForB = {
    ...collectionArticleB,
    id: 'article-b-current',
    title: '第二部正文',
  }
  const outlineForB = {
    ...outlineItems[1],
    id: 'outline-b-current',
    collection_id: collectionB.id,
    entry_id: articleForB.id,
    parent_id: null,
    title: '第二部章节',
  }
  let articleARequests = 0
  let outlineARequests = 0

  await page.route('**/api/collections', async (route) => {
    await route.fulfill({ json: [collection, collectionB] })
  })
  await page.route('**/api/collections/collection-a/articles', async (route) => {
    articleARequests += 1
    if (articleARequests > 1) {
      await new Promise((resolve) => setTimeout(resolve, 350))
      await route.fulfill({ status: 404, json: { detail: 'Collection not found' } })
      return
    }
    await route.fulfill({ json: [collectionArticle] })
  })
  await page.route('**/api/collections/collection-a/outline', async (route) => {
    outlineARequests += 1
    if (outlineARequests > 1) {
      await new Promise((resolve) => setTimeout(resolve, 300))
    }
    await route.fulfill({ json: outlineItems })
  })
  await page.route(/\/api\/collections\/collection-b(?:\/.*)?$/, async (route) => {
    const url = new URL(route.request().url())
    if (url.pathname === '/api/collections/collection-b/articles') {
      await route.fulfill({ json: [articleForB] })
      return
    }
    if (url.pathname === '/api/collections/collection-b/outline') {
      await route.fulfill({ json: [outlineForB] })
      return
    }
    if (url.pathname === '/api/collections/collection-b') {
      await route.fulfill({ json: collectionB })
      return
    }
    await route.fallback()
  })

  await page.goto('/collections')
  await expect(page.getByRole('heading', { name: collection.title, exact: true })).toBeVisible({ timeout: 20000 })

  await page.getByRole('button', { name: new RegExp(collectionB.title) }).click()
  await expect(page.getByRole('heading', { name: collectionB.title, exact: true })).toBeVisible()
  await page.getByRole('button', { name: new RegExp(collection.title) }).click()
  await expect(page.getByRole('heading', { name: collection.title, exact: true })).toBeVisible()
  await page.getByRole('button', { name: new RegExp(collectionB.title) }).click()

  await expect(page.getByRole('heading', { name: collectionB.title, exact: true })).toBeVisible()
  await expect(page.getByTestId('collection-outline-reader').getByRole('heading', { name: outlineForB.title, exact: true })).toBeVisible()
  await page.waitForTimeout(500)
  await expect(page.getByText('Collection not found', { exact: true })).toHaveCount(0)
  await expect(page.getByText('当前作品集已不存在，请重新选择。', { exact: true })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: collectionB.title, exact: true })).toBeVisible()
  expect(articleARequests).toBeGreaterThan(1)
  expect(outlineARequests).toBeGreaterThan(1)
})

test('collection agent reference picker, quick task confirmation, prompt index, and clear are usable', async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 900 })
  const longAnswer = `这本书已经有一个有效的开端：旧信不是外部危险，而是迫使林澄重新解释自己记忆的证据。

我建议先保留三种可能，不急着把任何一种写成 canon：

1. 信封上的错别字只有她和失踪的姐姐知道，让“必须拆开”来自私人经验，而不是情节命令。
2. 邮票下压着一小块旧墙纸，把线索落在能触摸的物件上，也自然带出童年空间。
3. 寄信人使用林澄从未告诉任何人的旧名，让威胁与亲密同时出现。

如果第一章负责建立悬念，真正要确认的不是“信里写了什么”，而是林澄为什么愿意冒险相信它。她越想证明自己早已离开雾港，拆信这个动作就越有重量。

下一步可以只写一个很小的场景：她把信放在桌上，去做三件无关紧要的事，却每一次都回到桌边。最后促使她拆信的，不是新的外部事件，而是一个只有她能认出的细节。

这里有一个连续性风险：如果后文仍要保留姐姐生死未明，就不要让旧信直接证明寄信人的身份。它更适合确认“有人知道过去”，而不是确认“谁还活着”。

等你决定采用哪一种细节后，我再把它整理成项目圣经提案；在那之前，这些方向都只留在对话里。

从结构上看，这一章可以维持“停顿、靠近、再次停顿、终于拆开”的节奏。每一次停顿都应透露一点人物，而不是重复制造悬念：第一次是她害怕，第二次是她试图维持日常，第三次是她意识到不拆信也是一种选择。这样，动作会逐渐从情节机关变成人物决定。

还可以让环境承担一部分压力。雾港的潮声、走廊里坏掉的感应灯、桌面上慢慢洇开的水痕，都比突然响起的电话更克制。它们不提供答案，只让她无法继续假装这封信与自己无关。

我暂时不会替你确定姐姐、寄信人或旧案真相。现在最值得由作者回答的问题只有一个：林澄拆信以后，最害怕失去的是平静、现在的关系，还是她一直依赖的自我解释？这个答案会决定旧信究竟是线索、诱饵，还是一次迟到的亲密。`
  const baseMemory = {
    collection_id: collection.id,
    updated_at: null,
    sections: [
      { id: 'project_core', title: '项目核心', help: '题材、核心命题、主要冲突、叙事承诺。', content: '' },
      { id: 'characters', title: '人物与关系', help: '主要人物、欲望、矛盾、关系变化。', content: '' },
      { id: 'open_questions', title: '未解决问题', help: '还没定下来的设定、人物、结构问题。', content: '' },
    ],
  }
  const makeRun = (id: string, message: string, taskType: string, answer = longAnswer) => ({
    id,
    collection_id: collection.id,
    thread_id: 'thread-agent',
    status: 'succeeded',
    stage: 'succeeded',
    stage_label: '已完成',
    request: {
      message,
      task_type: taskType,
      context_refs: [],
      request_web_context: false,
      profile_id: 'default',
    },
    result: { answer, evidence: [], next_steps: [] },
    error: '',
    profile_id: 'default',
    provider: 'demo',
    model: 'demo-coauthor',
    transport: 'demo',
    session_id: 'session-agent',
    mode: 'discuss',
    draft_id: null,
    created_at: '2026-07-07T08:00:00Z',
    started_at: '2026-07-07T08:00:01Z',
    updated_at: '2026-07-07T08:00:02Z',
    completed_at: '2026-07-07T08:00:03Z',
    actions: [],
  })
  let agentRuns = [
    makeRun('agent-run-a', '我不想马上解释旧信的来历。先和我讨论：怎样让读者相信林澄必须拆开它？', 'free_chat'),
  ]
  let runRequests = 0
  let clearRequests = 0
  const session: any = {
    id: 'session-agent',
    collection_id: collection.id,
    thread_id: 'thread-agent',
    title: '共同构思',
    mode: 'discuss',
    summary: '',
    archived: false,
    message_count: 2,
    run_count: 1,
    draft_count: 0,
    created_at: null,
    updated_at: null,
    last_message_at: null,
  }
  const agentState = () => ({
    settings: {
      collection_id: collection.id,
      profile_id: 'default',
      enabled: true,
      active_session_id: session.id,
      updated_at: null,
    },
    memory: baseMemory,
    thread_id: 'thread-agent',
    messages: [],
    runs: agentRuns,
    actions: [],
    profiles: [{ id: 'default', name: '默认配置' }],
    sessions: [session],
    active_session_id: session.id,
    drafts: [],
    style_samples: [],
    author_portrait: {
      id: 'global',
      tags: [],
      summary: '',
      evidence_count: 0,
      completed_style_cycles: 0,
      reminder_due: false,
      created_at: null,
      updated_at: null,
    },
    active_run: null,
  })

  await page.route(/\/api\/collections\/collection-a\/agent(?:\/.*)?(?:\?.*)?$/, async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    if (url.pathname === '/api/collections/collection-a/agent/references') {
      await route.fulfill({
        json: [
          {
            kind: 'outline',
            ref_id: 'outline-chapter-a',
            name: '旧信',
            body_preview: '主角收到旧信。',
            meta: { type: 'chapter', status: 'drafting' },
          },
          {
            kind: 'article',
            ref_id: article.id,
            name: article.title,
            body_preview: article.body,
            meta: {},
          },
        ],
      })
      return
    }
    if (url.pathname === '/api/collections/collection-a/agent/runs' && request.method() === 'POST') {
      runRequests += 1
      const body = request.postDataJSON() as { message?: string; task_type?: string }
      const run = makeRun(
        'agent-run-new',
        body.message ?? '',
        body.task_type ?? 'free_chat',
        '连续性检查已完成：没有发现会自动改正文的动作。',
      )
      agentRuns = [run, ...agentRuns.filter((item) => item.id !== run.id)]
      await route.fulfill({ status: 202, json: run })
      return
    }
    if (url.pathname === '/api/collections/collection-a/agent/runs/agent-run-new') {
      await route.fulfill({ json: agentRuns[0] })
      return
    }
    if (url.pathname === '/api/collections/collection-a/agent/clear' && request.method() === 'POST') {
      clearRequests += 1
      agentRuns = []
      await route.fulfill({ json: agentState() })
      return
    }
    if (url.pathname === '/api/collections/collection-a/agent/settings' && request.method() === 'PUT') {
      await route.fulfill({
        json: {
          collection_id: collection.id,
          profile_id: 'default',
          enabled: true,
          active_session_id: session.id,
          updated_at: null,
        },
      })
      return
    }
    if (url.pathname === '/api/collections/collection-a/agent') {
      await route.fulfill({ json: agentState() })
      return
    }
    await route.fallback()
  })

  const showcaseCollection = {
    ...collection,
    title: '雾港来信',
    description: '一部关于记忆、失踪与归返的长篇小说',
  }
  await page.route('**/api/collections', async (route) => {
    await route.fulfill({ json: [showcaseCollection] })
  })
  await page.route('**/api/collections/collection-a', async (route) => {
    await route.fulfill({ json: showcaseCollection })
  })

  await page.goto('/collections?id=collection-a&tab=agent')
  await expect(page.getByTestId('collection-agent-panel')).toBeVisible({ timeout: 20000 })
  await expect(page.getByText('共创工作台')).toBeVisible()
  await expect(page.getByText('展开完整回答')).toBeVisible()

  const conversation = page.getByTestId('agent-conversation-scroll')
  const initialConversationWidth = (await conversation.boundingBox())?.width ?? 0
  await expect(page.getByTestId('agent-left-panel')).toBeVisible()
  await expect(page.getByTestId('agent-right-panel')).toBeHidden()
  await expect(page.getByTestId('agent-right-toggle')).toHaveText('工作栏')
  await expect(page.getByTestId('agent-right-toggle')).toHaveAttribute('title', '打开上下文、草稿、提案和项目圣经')

  await page.getByTestId('agent-left-toggle').click()
  await expect(page.getByTestId('agent-left-panel')).toBeHidden()
  await expect.poll(async () => (await conversation.boundingBox())?.width ?? 0).toBeGreaterThan(initialConversationWidth + 180)
  await page.getByTestId('agent-left-toggle').click()
  await expect(page.getByTestId('agent-left-panel')).toBeVisible()

  await page.getByTestId('agent-right-toggle').click()
  await expect(page.getByTestId('agent-right-panel')).toBeVisible()
  await expect.poll(async () => (await conversation.boundingBox())?.width ?? 0).toBeGreaterThanOrEqual(initialConversationWidth - 2)
  await page.getByTestId('agent-right-panel').getByRole('button', { name: '关闭' }).click()
  await expect(page.getByTestId('agent-right-panel')).toBeHidden()
  await updatePublicScreenshot(page, 'collection-agent.png')

  await page.getByRole('button', { name: '@ 引用' }).click()
  await expect(page.getByPlaceholder('搜索结构、文章、卡片、意象或文脉')).toBeVisible()
  await page.getByRole('button', { name: '结构 旧信 主角收到旧信。' }).click()
  await expect(page.getByText(/结构 · 旧信 ×/)).toBeVisible()
  await expect(page.getByPlaceholder('搜索结构、文章、卡片、意象或文脉')).toHaveCount(0)

  const agentPromptBox = page.getByPlaceholder(/输入 @ 加引用/)
  await agentPromptBox.fill('@旧信')
  await expect(page.getByPlaceholder('搜索结构、文章、卡片、意象或文脉')).toBeVisible()
  await page.getByRole('button', { name: '结构 旧信 主角收到旧信。' }).click()
  await expect(agentPromptBox).toHaveValue('')

  await agentPromptBox.fill('/')
  await expect(page.getByTestId('agent-slash-menu')).toBeVisible()
  await expect(page.getByRole('button', { name: /\/init/ })).toBeVisible()
  await page.getByRole('button', { name: /\/init/ }).click()
  await expect(page.getByText('准备运行：初始化 Agent')).toBeVisible()
  expect(runRequests).toBe(0)
  await page.getByRole('button', { name: '取消' }).click()

  await page.getByRole('button', { name: /检查连续性/ }).click()
  expect(runRequests).toBe(0)
  await expect(page.getByText('准备运行：检查连续性')).toBeVisible()
  await page.getByRole('button', { name: '确认', exact: true }).click()
  await expect.poll(() => runRequests).toBe(1)
  await expect(page.getByText('连续性检查已完成')).toBeVisible()

  const promptIndex = page.locator('aside').filter({ hasText: '本会话 Prompt' })
  await promptIndex.getByPlaceholder('查找我问过的问题').fill('连续性')
  await promptIndex.getByRole('button', { name: /检查连续性/ }).first().click()
  await expect(page.locator('#collection-agent-run-agent-run-new')).toHaveClass(/ring-2/)

  await agentPromptBox.fill('/init')
  await page.getByRole('button', { name: '发送', exact: true }).click()
  await expect(page.getByText('准备运行：初始化 Agent')).toBeVisible()
  expect(runRequests).toBe(1)
  await page.getByRole('button', { name: '取消' }).click()

  await agentPromptBox.fill('/clear')
  await page.getByRole('button', { name: '发送', exact: true }).click()
  await expect(page.getByRole('heading', { name: '清空 Agent 会话？' })).toBeVisible()
  await page.getByRole('button', { name: '取消' }).click()

  await promptIndex.getByRole('button', { name: '清空' }).click()
  await expect(page.getByRole('heading', { name: '清空 Agent 会话？' })).toBeVisible()
  await page.getByRole('button', { name: '确认清空' }).click()
  await expect.poll(() => clearRequests).toBe(1)
  await expect(page.getByText('从一句还没成形的想法开始')).toBeVisible()
})

test('collection agent draft mode keeps a local draft and previews article writeback', async ({ page }) => {
  const session = {
    id: 'session-draft',
    collection_id: collection.id,
    thread_id: 'thread-draft',
    title: '第一章共创',
    mode: 'discuss',
    summary: '',
    archived: false,
    message_count: 0,
    run_count: 0,
    draft_count: 0,
    created_at: null,
    updated_at: null,
    last_message_at: null,
  }
  const draft: any = {
    id: 'draft-a',
    collection_id: collection.id,
    session_id: session.id,
    run_id: 'run-draft',
    parent_draft_id: null,
    title: '雨夜拆信',
    content: '她把信封翻到背面，雨声盖住纸张裂开的轻响。',
    brief: { target_scene: '雨夜拆信', pov: '第三人称限知', tense: '', target_length: 1200, must_happen: [], avoid: [] },
    variant_label: '',
    status: 'draft',
    target_entry_id: null,
    applied_ref_id: null,
    content_hash: 'hash',
    created_at: null,
    updated_at: null,
    applied_at: null,
  }
  const run: any = {
    id: 'run-draft',
    collection_id: collection.id,
    thread_id: session.thread_id,
    status: 'succeeded',
    stage: 'succeeded',
    stage_label: '已完成',
    request: { message: '写这个场景。', task_type: 'free_chat', mode: 'draft' },
    result: { answer: '候选草稿已保存。', evidence: [], next_steps: [], draft_id: draft.id },
    error: '',
    profile_id: 'default',
    provider: 'fake',
    model: 'fake-draft-model',
    transport: 'fake',
    session_id: session.id,
    mode: 'draft',
    draft_id: draft.id,
    created_at: null,
    started_at: null,
    updated_at: null,
    completed_at: null,
    actions: [],
  }
  let drafts: any[] = []
  let runPayload: Record<string, unknown> | null = null
  let applyRequests = 0
  const state = () => ({
    settings: { collection_id: collection.id, profile_id: 'default', enabled: true, active_session_id: session.id, updated_at: null },
    memory: { collection_id: collection.id, updated_at: null, sections: [] },
    thread_id: session.thread_id,
    messages: [],
    runs: runPayload ? [run] : [],
    actions: [],
    profiles: [{ id: 'default', name: '默认配置' }],
    sessions: [session],
    active_session_id: session.id,
    drafts,
    style_samples: [],
    author_portrait: { id: 'global', tags: [], summary: '', evidence_count: 0, completed_style_cycles: 0, reminder_due: false, created_at: null, updated_at: null },
    active_run: null,
  })

  await page.route(/\/api\/collections\/collection-a\/agent(?:\/.*)?(?:\?.*)?$/, async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    if (url.pathname === `/api/collections/${collection.id}/agent/sessions/${session.id}` && request.method() === 'PUT') {
      const body = request.postDataJSON() as { mode?: string }
      if (body.mode) session.mode = body.mode
      await route.fulfill({ json: session })
      return
    }
    if (url.pathname === `/api/collections/${collection.id}/agent/runs` && request.method() === 'POST') {
      runPayload = request.postDataJSON() as Record<string, unknown>
      drafts = [draft]
      await route.fulfill({ status: 202, json: run })
      return
    }
    if (url.pathname === `/api/collections/${collection.id}/agent/runs/${run.id}`) {
      await route.fulfill({ json: run })
      return
    }
    if (url.pathname === `/api/collections/${collection.id}/agent/drafts/${draft.id}/apply` && request.method() === 'POST') {
      applyRequests += 1
      draft.status = 'applied'
      draft.target_entry_id = article.id
      draft.applied_ref_id = `create_article:${article.id}`
      await route.fulfill({ json: { draft, entry_id: article.id, article_title: draft.title, operation: 'create_article', version_id: null } })
      return
    }
    if (url.pathname === `/api/collections/${collection.id}/agent`) {
      await route.fulfill({ json: state() })
      return
    }
    await route.fallback()
  })

  await page.goto('/collections?id=collection-a&tab=agent')
  await expect(page.getByTestId('collection-agent-panel')).toBeVisible({ timeout: 20000 })
  await page.getByRole('button', { name: '草稿', exact: true }).click()
  await expect(page.getByText('场景简报')).toBeVisible()
  await page.getByPlaceholder('目标场景，例如：雨夜收到旧信').fill('雨夜拆信')
  await page.getByPlaceholder(/描述这一场/).fill('写这个场景。')
  await page.getByRole('button', { name: '生成草稿' }).click()
  await expect.poll(() => runPayload?.mode).toBe('draft')
  expect((runPayload?.draft_brief as { target_scene?: string }).target_scene).toBe('雨夜拆信')
  await expect(page.getByText('草稿库')).toBeVisible()
  await expect(page.getByText('雨夜拆信').last()).toBeVisible()
  await page.getByRole('button', { name: '写入文章...' }).click()
  await expect(page.getByRole('heading', { name: '将草稿写入文章' })).toBeVisible()
  await page.getByRole('button', { name: '确认写入' }).click()
  await expect.poll(() => applyRequests).toBe(1)
})

test('collection planning board groups outline items and opens the selected outline detail', async ({ page }) => {
  await page.goto('/collections')
  await expect(page.getByRole('heading', { name: '测试作品集', exact: true })).toBeVisible({ timeout: 20000 })

  await page.getByRole('button', { name: '看板' }).click()
  const board = page.getByTestId('collection-planning-board')
  await expect(board.getByRole('heading', { name: '看板' })).toBeVisible()
  await expect(board.locator('div').filter({ hasText: /^构思$/ })).toBeVisible()
  await expect(board.locator('div').filter({ hasText: /^草稿$/ })).toBeVisible()
  await expect(board.locator('div').filter({ hasText: /^完成$/ })).toBeVisible()
  await expect(board.locator('article').filter({ hasText: '雨夜来信' })).toBeVisible()
  await expect(board.locator('article').filter({ hasText: '河岸清单' })).toBeVisible()
  await updatePublicScreenshot(page, 'collections.png')

  await board.locator('article').filter({ hasText: '河岸清单' }).click()
  const detail = page.getByTestId('collection-outline-detail')
  await expect(detail).toBeVisible()
  await expect(detail.getByTestId('collection-outline-reader')).toContainText('河岸清单')
  await detail.getByTestId('outline-edit-details').click()
  await expect(detail.locator('input').first()).toHaveValue('河岸清单')
  await expect(detail.getByLabel(/视角/)).toHaveValue('林澄')
})

test('collection article route highlight does not override manual outline selection', async ({ page }) => {
  await page.goto('/collections?id=collection-a&article=article-a')
  const chapterCard = page.locator('[data-outline-item-id="outline-chapter-a"]')
  const partCard = page.locator('[data-outline-item-id="outline-part-a"]')

  await expect(chapterCard).toHaveClass(/ring-2/, { timeout: 20000 })
  await partCard.click()

  await expect(partCard).toHaveClass(/ring-2/)
  await expect(chapterCard).not.toHaveClass(/ring-2/)
  await expect(page.getByTestId('collection-outline-reader')).toContainText('第一部：回到旧城')
})

test('collection metadata saves before exporting with the updated title', async ({ page }) => {
  const updates: Array<Record<string, unknown>> = []
  let currentCollection = { ...collection }

  await page.route('**/api/collections/collection-a/export?**', async (route) => {
    await route.fulfill({
      body: 'collection md',
      headers: { 'Content-Type': 'text/markdown; charset=utf-8' },
    })
  })
  await page.route('**/api/collections/collection-a', async (route) => {
    const request = route.request()
    if (request.method() === 'PUT') {
      const body = request.postDataJSON() as Record<string, unknown>
      updates.push(body)
      currentCollection = { ...currentCollection, ...body }
      await route.fulfill({ json: currentCollection })
      return
    }
    await route.fulfill({ json: currentCollection })
  })

  await page.goto('/collections')
  await expect(page.getByRole('heading', { name: '测试作品集', exact: true })).toBeVisible({ timeout: 20000 })
  await page.getByTestId('collection-edit-meta').click()
  await page.getByPlaceholder('作品集标题').fill('刚修改的作品集标题')
  await page.getByRole('button', { name: '保存', exact: true }).click()
  await expect(page.getByRole('heading', { name: '刚修改的作品集标题', exact: true })).toBeVisible()

  await page.getByRole('button', { name: '导出', exact: true }).click()
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Markdown', exact: true }).click()
  const download = await downloadPromise

  await expect.poll(() => updates.some((body) => body.title === '刚修改的作品集标题')).toBe(true)
  expect(download.suggestedFilename()).toBe('刚修改的作品集标题.md')
})

test('collection reorder failures show a visible error', async ({ page }) => {
  await page.route('**/api/collections/collection-a/outline/order', async (route) => {
    await route.fulfill({ status: 500, json: { detail: '排序保存失败' } })
  })

  await page.goto('/collections')
  await expect(page.getByRole('heading', { name: '测试作品集', exact: true })).toBeVisible({ timeout: 20000 })

  const firstCard = page.locator('article').filter({ hasText: '第一部：回到旧城' }).first()
  await firstCard.hover()
  await firstCard.getByRole('button', { name: '↓' }).click()

  await expect(page.getByTestId('collection-outline-pane').getByText('排序保存失败')).toBeVisible()
})

test('collection create failures show a visible dialog error', async ({ page }) => {
  await page.route('**/api/collections', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({ status: 500, json: { detail: '作品集目录不可写' } })
      return
    }
    await route.fulfill({ json: [collection] })
  })

  await page.goto('/collections')
  await page.getByRole('complementary').getByRole('button', { name: '+ 新建', exact: true }).click()
  await page.getByPlaceholder('作品集标题').last().fill('无法创建的作品集')
  await page.getByRole('button', { name: '创建', exact: true }).click()

  await expect(page.getByText('作品集目录不可写').last()).toBeVisible()
  await expect(page.getByPlaceholder('作品集标题').last()).toHaveValue('无法创建的作品集')
})

test('collection metadata edit keeps invalid changes local and shows validation', async ({ page }) => {
  let exportRequests = 0

  await page.route('**/api/collections/collection-a/export?**', async (route) => {
    exportRequests += 1
    await route.fulfill({ body: 'should-not-export' })
  })

  await page.goto('/collections')
  await page.getByTestId('collection-edit-meta').click()
  const titleInput = page.getByPlaceholder('作品集标题')
  await expect(titleInput).toHaveValue('测试作品集')
  await titleInput.fill('')

  await page.getByRole('button', { name: '保存', exact: true }).click()
  await expect(page.getByText('作品集标题不能为空。')).toBeVisible()
  expect(exportRequests).toBe(0)
  await expect(titleInput).toHaveValue('')
})

test('library copy, create-in-book, and delete actions have visible effects and confirmations', async ({ page }) => {
  const createBodies: Array<Record<string, unknown>> = []
  let deleteRequests = 0

  await page.route('**/api/library/references', async (route) => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON() as Record<string, unknown>
      createBodies.push(body)
      await route.fulfill({ status: 201, json: { ...reference, ...body, id: 'ref-created-in-book' } })
      return
    }
    await route.fallback()
  })
  await page.route('**/api/library/references/ref-existing', async (route) => {
    if (route.request().method() === 'DELETE') {
      deleteRequests += 1
      await route.fulfill({ status: 204 })
      return
    }
    await route.fulfill({ json: existingReference })
  })

  await page.goto('/library')
  await expect(page.getByText('已有标本正文')).toBeVisible()

  await page.getByRole('button', { name: '复制正文' }).click()
  await expect.poll(() => page.evaluate(() => window.__copiedText)).toBe('已有标本正文')
  await expect(page.getByText('正文已复制')).toBeVisible()

  await page.getByRole('button', { name: '复制完整引用' }).click()
  await expect.poll(() => page.evaluate(() => window.__copiedText)).toBe('已有标本正文\n\n——《测试书》 测试作者')
  await expect(page.getByText('完整引用已复制')).toBeVisible()

  await page.getByRole('button', { name: '在本书中新建' }).click()
  await expect.poll(() => createBodies).toEqual([
    expect.objectContaining({
      source_title: '测试书',
      source_author: '测试作者',
      content: '新标本',
    }),
  ])

  await page.getByText('已有标本正文').click()
  await page.getByTestId('library-edit-reference').click()
  page.once('dialog', async (dialog) => dialog.dismiss())
  await page.getByRole('button', { name: '删除标本' }).click()
  expect(deleteRequests).toBe(0)

  page.once('dialog', async (dialog) => dialog.accept())
  await page.getByRole('button', { name: '删除标本' }).click()
  await expect.poll(() => deleteRequests).toBe(1)
})

test('library create, grouping, search, and autosave actions are real and visible', async ({ page }) => {
  const createBodies: Array<Record<string, unknown>> = []
  const updateBodies: Array<Record<string, unknown>> = []
  const searchQueries: string[] = []

  await page.route('**/api/library/stats', async (route) => {
    await route.fulfill({ json: { total: 2, by_usage_kind: { style: 1, imagery: 1 } } })
  })
  await page.route('**/api/library/references?**', async (route) => route.fulfill({ json: [existingReference, imageryReference] }))
  await page.route('**/api/library/references/search?**', async (route) => {
    const url = new URL(route.request().url())
    searchQueries.push(url.searchParams.get('q') ?? '')
    await route.fulfill({ json: [imageryReference] })
  })
  await page.route('**/api/library/references', async (route) => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON() as Record<string, unknown>
      createBodies.push(body)
      await route.fulfill({ status: 201, json: { ...reference, ...body, id: 'ref-new-from-top' } })
      return
    }
    await route.fallback()
  })
  await page.route('**/api/library/references/ref-existing', async (route) => {
    if (route.request().method() === 'PUT') {
      const body = route.request().postDataJSON() as Record<string, unknown>
      updateBodies.push(body)
      await route.fulfill({ json: { ...existingReference, ...body } })
      return
    }
    await route.fulfill({ json: existingReference })
  })

  await page.goto('/library')
  await expect(page.getByText('已有标本正文')).toBeVisible()
  const overview = page.getByTestId('library-overview')
  await expect(overview.getByText('标本')).toBeVisible()
  await expect(overview.getByText('来源')).toBeVisible()
  await expect(overview.getByText('疑似重复')).toBeVisible()
  await expect(page.getByTestId('library-active-group-summary').getByText('当前分组字数')).toBeVisible()
  await updatePublicScreenshot(page, 'reference-library.png')

  await page.getByRole('button', { name: '按用途' }).click()
  await page.getByRole('button', { name: /意象\s+共 1 条/ }).click()
  await expect(page.getByText('意象标本正文')).toBeVisible()

  await page.getByRole('button', { name: '按书籍' }).click()
  await page.getByRole('button', { name: /测试书/ }).click()
  await expect(page.getByText('已有标本正文')).toBeVisible()

  await page.getByRole('button', { name: '+ 新建' }).click()
  await expect.poll(() => createBodies).toEqual([
    expect.objectContaining({
      source_title: '',
      content: '新标本',
    }),
  ])

  await page.getByPlaceholder('搜索标本...').fill('意象')
  await expect.poll(() => searchQueries).toEqual(['意象'])
  await expect(page.getByText('意象标本正文')).toBeVisible()

  await page.getByPlaceholder('搜索标本...').fill('')
  await page.getByRole('button', { name: '按书籍' }).click()
  await page.getByRole('button', { name: /测试书/ }).click()
  await expect(page.getByText('已有标本正文')).toBeVisible()
  await page.getByTestId('library-edit-reference').click()
  await page.locator('textarea').first().fill('改过的标本正文')
  await expect.poll(() => updateBodies.length).toBe(1)
  expect(updateBodies[0]).toEqual(expect.objectContaining({ content: '改过的标本正文' }))
  await expect(page.getByText('修改已保存')).toBeVisible()

  await page.locator('select').selectOption('rhetoric')
  await expect.poll(() => updateBodies.some((body) => body.usage_kind === 'rhetoric')).toBe(true)
  await expect(page.locator('select')).toHaveValue('rhetoric')
  await page.getByRole('button', { name: '按用途' }).click()
  await expect(page.getByRole('button', { name: /修辞/ })).toBeVisible()
  await expect(page.getByText('改过的标本正文')).toBeVisible()
})

test('library pending edits are flushed before selecting another reference', async ({ page }) => {
  const updateBodies: Array<Record<string, unknown>> = []

  await page.route('**/api/library/stats', async (route) => {
    await route.fulfill({ json: { total: 2, by_usage_kind: { style: 1, imagery: 1 } } })
  })
  await page.route('**/api/library/references?**', async (route) => route.fulfill({ json: [existingReference, imageryReference] }))
  await page.route('**/api/library/references/ref-existing', async (route) => {
    if (route.request().method() === 'PUT') {
      const body = route.request().postDataJSON() as Record<string, unknown>
      updateBodies.push(body)
      await route.fulfill({ json: { ...existingReference, ...body } })
      return
    }
    await route.fulfill({ json: existingReference })
  })
  await page.route('**/api/library/references/ref-imagery', async (route) => {
    await route.fulfill({ json: imageryReference })
  })

  await page.goto('/library')
  await expect(page.getByText('已有标本正文')).toBeVisible()
  await page.getByTestId('library-edit-reference').click()
  await page.locator('textarea').first().fill('切换前未保存标本正文')
  await page.getByRole('button', { name: '按用途' }).click()
  await page.getByRole('button', { name: /意象\s+共 1 条/ }).click()
  await page.getByText('意象标本正文').click()

  await expect.poll(() => updateBodies.some((body) => body.content === '切换前未保存标本正文')).toBe(true)
  await expect(page.locator('textarea').first()).toHaveValue('意象标本正文')
})

test('library autosave failures show a visible unsaved-state error', async ({ page }) => {
  await page.route('**/api/library/references/ref-existing', async (route) => {
    if (route.request().method() === 'PUT') {
      await route.fulfill({ status: 500, json: { detail: '磁盘不可写' } })
      return
    }
    await route.fulfill({ json: existingReference })
  })

  await page.goto('/library')
  await expect(page.getByText('已有标本正文')).toBeVisible()
  await page.getByTestId('library-edit-reference').click()
  await page.locator('textarea').first().fill('无法保存的内容')
  await expect(page.getByText('保存失败：磁盘不可写')).toBeVisible()
})

test('article AI runs only selected profiles, reveals incremental results, previews apply, and clears explicitly', async ({ page }) => {
  const runRequests: Array<Record<string, unknown>> = []
  page.on('request', (request) => {
    if (request.method() === 'POST' && new URL(request.url()).pathname === '/api/ai/task-runs') {
      runRequests.push(request.postDataJSON() as Record<string, unknown>)
    }
  })
  await page.goto('/ai?scope_kind=article&scope_id=article-a')
  await expect(page.getByRole('heading', { name: 'AI 修改' })).toBeVisible({ timeout: 15000 })
  await expect(page.getByText('已选择 1 个模型')).toBeVisible()
  await page.getByText('已选择 1 个模型').click()
  await expect(page.getByRole('dialog', { name: '选择 AI 配置档案' })).toBeVisible()
  await page.locator('label').filter({ hasText: 'DeepSeek 测试' }).locator('input').check()
  await expect(page.getByText('已选择 1 个模型')).toBeVisible()
  await page.locator('label').filter({ hasText: 'Gemini 测试' }).locator('input').check()
  await page.getByRole('button', { name: '完成', exact: true }).click()
  await expect(page.getByText('已选择 2 个模型')).toBeVisible()

  await page.getByRole('button', { name: '运行 AI 修改' }).click()
  await expect.poll(() => runRequests.length).toBe(1)
  expect(runRequests[0].profile_ids).toEqual(['profile-deepseek', 'profile-gemini'])
  expect(runRequests[0]).toEqual(expect.objectContaining({ article_id: 'article-a', task_type: 'polish' }))
  await expect(page.getByText('DeepSeek 增量结果')).toBeVisible({ timeout: 10000 })
  await page.getByRole('button', { name: /Gemini 测试.*已完成/ }).click()
  await expect(page.getByText('Gemini 增量结果')).toBeVisible({ timeout: 10000 })

  await page.getByRole('button', { name: '预览写回' }).click()
  await expect(page.getByRole('dialog', { name: '确认写回文章' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '确认写回文章' })).toBeVisible()
  await expect(page.getByText('AI_BEFORE_APPLY')).toBeVisible()
  await page.getByRole('button', { name: '创建版本并写回' }).click()
  await expect(page.getByText('已写回文章，并创建写回前版本。')).toBeVisible()

  page.once('dialog', async (dialog) => dialog.accept())
  await page.getByRole('button', { name: '清空本轮结果' }).click()
  await expect(page.getByText('DeepSeek 增量结果')).toHaveCount(0)
})

test('article AI background run survives navigation and is recovered without resending', async ({ page }) => {
  let creates = 0
  page.on('request', (request) => {
    if (request.method() === 'POST' && new URL(request.url()).pathname === '/api/ai/task-runs') creates += 1
  })
  await page.goto('/ai?scope_kind=article&scope_id=article-a')
  await page.getByRole('button', { name: '运行 AI 修改' }).click()
  await expect.poll(() => creates).toBe(1)
  await page.goto('/dates')
  await page.goto('/ai')
  await expect(page.getByText('Gemini 增量结果')).toBeVisible({ timeout: 10000 })
  expect(creates).toBe(1)
})

test('article chat drawer preserves its draft when closed and records the actual model metadata', async ({ page }) => {
  await page.goto('/articles?id=article-a')
  await page.getByRole('button', { name: 'AI 对话' }).click()
  const drawer = page.getByTestId('article-ai-chat-drawer')
  await expect(drawer).toBeVisible()
  await expect(page.getByRole('dialog', { name: '文章 AI 对话' })).toBeVisible()
  const input = drawer.getByPlaceholder('输入问题，Ctrl+Enter 发送')
  await input.fill('关闭抽屉后不要丢失。')
  await drawer.getByRole('button', { name: '关闭' }).click()
  await expect(drawer).toBeHidden()
  await page.getByRole('button', { name: 'AI 对话' }).click()
  await expect(input).toHaveValue('关闭抽屉后不要丢失。')
  await drawer.getByRole('button', { name: '发送' }).click()
  await expect(drawer.getByText('这是 AI 回复。')).toBeVisible()
  await expect(drawer.getByText('fake · fake-model · chat_completions')).toBeVisible()
  await drawer.getByRole('button', { name: '存为便签' }).click()
  await expect(drawer.getByText('已保存为当前文章便签。')).toBeVisible()
  await drawer.getByRole('button', { name: '预览后存为文脉' }).click()
  await expect(page.getByRole('dialog', { name: '预览并保存为文脉' })).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog', { name: '预览并保存为文脉' })).toBeHidden()
})

test('primary settings, article, collection, AI, and backup surfaces have no serious accessibility violations', async ({ page }) => {
  const routes = ['/settings', '/articles?id=article-a', '/collections?id=collection-a', '/ai?scope_kind=article&scope_id=article-a', '/backup']
  for (const path of routes) {
    await page.goto(path)
    await page.waitForLoadState('domcontentloaded')
    const results = await new AxeBuilder({ page }).analyze()
    const serious = results.violations.filter((item) => item.impact === 'serious' || item.impact === 'critical')
    expect(serious, `${path}: ${serious.map((item) => `${item.id} (${item.nodes.length})`).join(', ')}`).toEqual([])
  }
})

test('all primary surfaces avoid horizontal overflow at release viewports in both languages', async ({ browser }) => {
  const viewports = [
    { width: 1024, height: 768 },
    { width: 1400, height: 900 },
    { width: 1920, height: 1080 },
  ]
  const routes = [
    ['/dates', 'dates'],
    ['/articles?id=article-a', 'articles'],
    ['/collections?id=collection-a', 'collections'],
    ['/library', 'library'],
    ['/motifs', 'motifs'],
    ['/ai-cards', 'ai-cards'],
    ['/ai?scope_kind=article&scope_id=article-a', 'article-ai'],
    ['/backup', 'backup'],
    ['/settings', 'settings'],
  ] as const

  for (const language of ['zh', 'en'] as const) {
    for (const viewport of viewports) {
      const context = await browser.newContext({ viewport })
      const page = await context.newPage()
      await mockVisibleActionApi(page, language)
      try {
        for (const [route, name] of routes) {
          await page.goto(route)
          await page.waitForLoadState('domcontentloaded')
          await page.waitForTimeout(400)
          const dimensions = await page.evaluate(() => ({
            viewport: window.innerWidth,
            html: document.documentElement.scrollWidth,
            body: document.body.scrollWidth,
          }))
          expect(
            Math.max(dimensions.html, dimensions.body),
            `${language} ${viewport.width}x${viewport.height} ${route}`,
          ).toBeLessThanOrEqual(dimensions.viewport + 1)
          if (process.env.CAPTURE_VISUAL_AUDIT === '1') {
            await page.screenshot({
              path: path.resolve(process.cwd(), 'test-results', 'visual-audit', `${language}-${viewport.width}x${viewport.height}-${name}.png`),
              fullPage: false,
            })
          }
        }
      } finally {
        await context.close()
      }
    }
  }
})
