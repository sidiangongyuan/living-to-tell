const fs = require('fs')
const path = require('path')

let chromium
try {
  ;({ chromium } = require('playwright'))
} catch {
  ;({ chromium } = require(path.resolve(__dirname, '..', 'frontend', 'node_modules', 'playwright')))
}

const baseUrl = process.env.WRITER_SCREENSHOT_URL || 'http://127.0.0.1:1420'
const outDir = path.resolve(__dirname, '..', 'docs', 'assets', 'screenshots')

const now = '2026-06-18T09:30:00'

const articles = [
  {
    id: 'demo-article-1',
    title: '清晨的海边笔记',
    body:
      '风从堤岸那边过来，带着一点盐和潮湿的光。\n\n' +
      '我把昨天没有写完的一段重新读了一遍，发现真正要留下的不是事件，而是那种慢慢亮起来的感觉。\n\n' +
      '如果一个段落还能让人听见脚步声、闻到雨后的石头，它就还有继续往前走的可能。',
    entry_type: 'article',
    created_at: '2026-06-16T08:00:00',
    updated_at: now,
    tags: ['散文', '海边', '日常'],
    archived_at: null,
    curation_status: 'draft',
  },
  {
    id: 'demo-article-2',
    title: '给远方的一封信',
    body:
      '我想把这封信写得慢一点，好像每一句都要经过一条长街。\n\n' +
      '有些话在路上会变轻，有些话则会因为反复携带而变得更重。',
    entry_type: 'article',
    created_at: '2026-06-12T20:00:00',
    updated_at: '2026-06-17T21:10:00',
    tags: ['信', '记忆'],
    archived_at: null,
    curation_status: 'draft',
  },
]

const collections = [
  {
    id: 'demo-collection-1',
    title: '夏天的讲述',
    description: '收集关于日常、远方与自我确认的短文。',
    article_count: 2,
    created_at: '2026-06-10T12:00:00',
    updated_at: now,
  },
]

const collectionArticles = [
  {
    ...articles[0],
    body_preview: articles[0].body.slice(0, 80),
    word_count: 88,
    char_count: articles[0].body.length,
    sort_order: 1,
  },
  {
    ...articles[1],
    body_preview: articles[1].body.slice(0, 80),
    word_count: 52,
    char_count: articles[1].body.length,
    sort_order: 2,
  },
]

const references = [
  {
    id: 'demo-reference-1',
    source_title: '想象的书',
    content: '一个人只有把经历讲出来，才真正知道自己曾经怎样穿过它。',
    source_author: '匿名作者',
    tags: ['讲述', '记忆'],
    kind: 'excerpt',
    usage_kind: 'imagery',
    personal_note: '适合作为“讲述”主题的灵感标本。',
    created_at: '2026-06-15T10:00:00',
    updated_at: now,
  },
  {
    id: 'demo-reference-2',
    source_title: '海边札记',
    content: '潮水退去以后，沙滩像一页还没有写完的纸。',
    source_author: '示例作者',
    tags: ['海', '纸页'],
    kind: 'excerpt',
    usage_kind: 'style',
    personal_note: '可用于描写空间和留白。',
    created_at: '2026-06-14T10:00:00',
    updated_at: now,
  },
]

const aiCards = [
  {
    id: 'demo-card-1',
    title: '克制而有画面感',
    content: '句子保持清晰，减少抽象判断，多保留能被看见、听见、触摸到的细节。',
    card_type: 'style',
    tags: ['散文', '克制'],
    created_at: '2026-06-11T09:00:00',
    updated_at: now,
  },
]

const aiProfiles = [
  {
    id: 'demo-profile-opencode',
    name: 'OpenCode · DeepSeek Flash',
    provider_name: 'opencode',
    base_url: null,
    wire_api: 'opencode_cli',
    model: 'opencode/deepseek-v4-flash-free',
    api_key_source: 'opencode',
    gemini_cli_proxy: null,
    enabled: true,
    is_default: true,
    test_status: 'passed',
    last_tested_at: now,
    last_test_transport: 'opencode_cli',
    last_test_elapsed_ms: 1860,
    diagnostic_code: '',
    diagnostic_message: '',
    source_key: 'opencode:default',
    created_at: '2026-06-18T09:00:00',
    updated_at: now,
  },
  {
    id: 'demo-profile-codex',
    name: 'Codex 本地登录',
    provider_name: 'openai',
    base_url: 'https://api.openai.com/v1',
    wire_api: 'responses',
    model: 'gpt-4o-mini',
    api_key_source: 'codex',
    gemini_cli_proxy: null,
    enabled: true,
    is_default: false,
    test_status: 'passed',
    last_tested_at: now,
    last_test_transport: 'openai_responses',
    last_test_elapsed_ms: 1420,
    diagnostic_code: '',
    diagnostic_message: '',
    source_key: 'codex:default',
    created_at: '2026-06-18T09:05:00',
    updated_at: now,
  },
]

const aiSettings = {
  provider_name: 'openai',
  base_url: 'https://api.openai.com/v1',
  wire_api: 'responses',
  model: 'gpt-4o-mini',
  api_key_source: 'env:OPENAI_API_KEY',
  gemini_cli_proxy: null,
  status: {
    env: { available: false, path: null, reason: 'Not configured in this demo' },
    codex: { available: false, path: null, reason: 'Not configured in this demo' },
    gemini: { available: false, path: null, reason: 'Not configured in this demo' },
    gemini_cli: {
      available: false,
      path: null,
      reason: 'Not configured in this demo',
      account: null,
      command: 'gemini',
      proxy: null,
    },
    opencode: {
      available: false,
      path: null,
      reason: 'Not configured in this demo',
      account: null,
      command: 'opencode',
      proxy: null,
    },
  },
  model_presets: {
    openai: ['gpt-4o-mini', 'gpt-4.1-mini'],
    gemini: ['gemini-2.5-flash', 'gemini-2.5-pro'],
    gemini_cli: ['gemini-cli-default'],
    opencode: ['opencode/deepseek-v4-flash-free'],
  },
}

let articleTaskRun = null

function json(route, data, status = 200) {
  return route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(data),
  })
}

async function installDemoApi(page) {
  await page.addInitScript(() => {
    window.__WRITER_API_BASE__ = 'http://127.0.0.1:8000'
    localStorage.setItem('language', 'zh')
    localStorage.setItem('theme', 'light')
    localStorage.setItem('right_context_pane_collapsed', 'false')
  })

  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url())
    const pathname = url.pathname
    const method = route.request().method()
    if (!url.origin.startsWith('http://127.0.0.1:8000')) {
      return route.continue()
    }

    if (pathname === '/health') return json(route, { message: 'ok', version: 'demo' })
    if (pathname === '/api/app/version') {
      return json(route, {
        app_name: 'Living to Tell',
        version: '0.1.48',
        api_version: '2.0.0',
        capabilities: [
          'data_location',
          'ai_chat_settings',
          'ai_task_presets',
          'ai_profiles',
          'ai_profile_defaults',
          'ai_profile_health',
          'ai_task_compare',
          'article_ai_task_runs',
          'article_ai_chat_drawer',
          'motif_star_map',
          'update_check',
          'article_versions',
          'collection_outline',
        ],
      })
    }

    if (pathname === '/api/articles' && method === 'GET') return json(route, articles)
    if (pathname === '/api/articles/search') return json(route, articles)
    if (pathname === '/api/articles/demo-article-1') return json(route, articles[0])
    if (pathname === '/api/articles/demo-article-2') return json(route, articles[1])
    if (pathname === '/api/articles/demo-article-1/notes') {
      return json(route, [
        {
          id: 'demo-note-1',
          entry_id: 'demo-article-1',
          body: '结尾可以回到“讲述”这一主题，但不要直接说教。',
          pinned: true,
          done_at: null,
          created_at: now,
          updated_at: now,
        },
      ])
    }
    if (pathname.startsWith('/api/articles/') && pathname.endsWith('/notes')) return json(route, [])
    if (pathname === '/api/collections') return json(route, collections)
    if (pathname === '/api/collections/demo-collection-1') return json(route, collections[0])
    if (pathname === '/api/collections/demo-collection-1/articles') return json(route, collectionArticles)
    if (pathname === '/api/collections/demo-collection-1/outline') return json(route, [])
    if (pathname.startsWith('/api/collections/for-entry/')) return json(route, collections)
    if (pathname === '/api/library/stats') {
      return json(route, { total: references.length, by_usage_kind: { imagery: 1, style: 1 } })
    }
    if (pathname === '/api/library/references' || pathname === '/api/library/references/search') {
      const usageKind = url.searchParams.get('usage_kind')
      const query = (url.searchParams.get('q') || '').trim().toLocaleLowerCase()
      const matches = references.filter((reference) => {
        if (usageKind && reference.usage_kind !== usageKind) return false
        if (!query) return true
        return [
          reference.source_title,
          reference.source_author,
          reference.content,
          reference.personal_note,
          ...reference.tags,
        ].join('\n').toLocaleLowerCase().includes(query)
      })
      return json(route, matches)
    }
    if (pathname === '/api/ai-cards') return json(route, aiCards)
    if (pathname === '/api/ai-cards/presets/list') return json(route, aiCards)
    if (pathname === '/api/ai/task-presets') return json(route, {})
    if (pathname === '/api/ai/task-runs/active' && method === 'GET') return json(route, articleTaskRun)
    if (pathname === '/api/ai/task-runs' && method === 'POST') {
      const request = route.request().postDataJSON()
      const selected = aiProfiles.filter((profile) => (request.profile_ids || []).includes(profile.id))
      const results = selected.map((profile, index) => ({
        profile_id: profile.id,
        profile_name: profile.name,
        provider: profile.provider_name,
        model: profile.model,
        transport: profile.id === 'demo-profile-opencode' ? 'opencode_cli' : 'openai_responses',
        status: 'success',
        result: index === 0
          ? '风越过堤岸，带来盐、潮气和一点清晨的亮。\n\n我把昨天没写完的段落又读了一遍，发现该留下的并不是发生过什么，而是那种被光一点点托起来的感觉。'
          : '风从堤岸吹来，裹着盐意和潮湿的晨光。\n\n重读昨天搁下的段落时，我才意识到真正应该留下的不是事件本身，而是它一点点亮起来的过程。',
        error: '', elapsed_ms: index === 0 ? 1860 : 2380, input_tokens: 76, output_tokens: index === 0 ? 109 : 114,
        cost: index === 0 ? 0 : 0.0005, finish_reason: 'stop',
        stats: { input_chars: articles[0].body.length, output_chars: 88, delta_chars: 10, output_ratio: 1.08, input_paragraphs: 3, output_paragraphs: 2 },
      }))
      articleTaskRun = {
        run_id: 'demo-run', article_id: articles[0].id, article_title: articles[0].title, task_type: request.task_type || 'polish',
        article_hash: 'demo-hash', original_text: articles[0].body, selection_start: null, selection_end: null,
        status: 'succeeded', stage: 'succeeded', stage_label: '已完成', error: '',
        profiles: selected.map((profile) => ({ profile_id: profile.id, profile_name: profile.name, provider: profile.provider_name, model: profile.model })),
        attachment_snapshots: (request.attachments || []).map((attachment) => ({
          kind: attachment.kind,
          ref_id: attachment.ref_id,
          name: attachment.name,
          size_chars: Math.min((attachment.body || '').trim().length, 40000),
        })),
        results, created_at: now, started_at: now, updated_at: now, completed_at: now, elapsed_ms: 2380,
        applied_profile_id: null, applied_at: null, applied_version_id: null,
      }
      return json(route, articleTaskRun, 202)
    }
    if (pathname === '/api/ai/task-runs/demo-run' && method === 'GET') return json(route, articleTaskRun)
    if (pathname === '/api/ai/task-runs/demo-run' && method === 'DELETE') { articleTaskRun = null; return route.fulfill({ status: 204 }) }
    if (pathname === '/api/ai/task/compare' && method === 'POST') {
      const request = route.request().postDataJSON()
      const inputText = request.text || ''
      const inputParagraphs = inputText.split(/\n\s*\n/).filter(Boolean).length || 1
      return json(route, {
        task_type: request.task_type || 'polish',
        results: [
          {
            profile_id: 'default',
            profile_name: '默认配置',
            provider: 'openai',
            model: 'gpt-4o-mini',
            transport: 'responses',
            status: 'success',
            result:
              '风从堤岸那边吹来，裹着盐意和潮湿的晨光。\n\n' +
              '我重新读完昨天搁下的段落，才意识到真正应该留下的不是事件本身，而是它慢慢亮起来的过程。\n\n' +
              '只要一个段落还能让人听见脚步、闻到雨后石头的气味，它就还值得继续往前写。',
            error: '',
            elapsed_ms: 1280,
            input_tokens: 72,
            output_tokens: 118,
            cost: 0.0004,
            finish_reason: 'stop',
            stats: {
              input_chars: inputText.length,
              output_chars: 112,
              delta_chars: 24,
              output_ratio: inputText.length ? 112 / inputText.length : null,
              input_paragraphs: inputParagraphs,
              output_paragraphs: 3,
            },
          },
          {
            profile_id: 'demo-profile-opencode',
            profile_name: 'OpenCode · DeepSeek Flash',
            provider: 'opencode',
            model: 'opencode/deepseek-v4-flash-free',
            transport: 'opencode_cli',
            status: 'success',
            result:
              '风越过堤岸，带来盐、潮气和一点清晨的亮。\n\n' +
              '我把昨天没写完的段落又读了一遍，发现该留下的并不是发生过什么，而是那种被光一点点托起来的感觉。\n\n' +
              '如果一段文字仍能留下脚步声和雨后石头的气味，它就还有继续生长的余地。',
            error: '',
            elapsed_ms: 2140,
            input_tokens: 76,
            output_tokens: 109,
            cost: 0,
            finish_reason: 'stop',
            stats: {
              input_chars: inputText.length,
              output_chars: 106,
              delta_chars: 18,
              output_ratio: inputText.length ? 106 / inputText.length : null,
              input_paragraphs: inputParagraphs,
              output_paragraphs: 3,
            },
          },
          {
            profile_id: 'demo-profile-codex',
            profile_name: 'Codex 本地登录',
            provider: 'openai',
            model: 'gpt-4o-mini',
            transport: 'responses',
            status: 'error',
            result: '',
            error: '演示环境未连接真实账户；实际使用时只会影响这一张结果卡。',
            elapsed_ms: 930,
            input_tokens: null,
            output_tokens: null,
            cost: null,
            finish_reason: null,
            stats: {
              input_chars: inputText.length,
              output_chars: 0,
              delta_chars: -inputText.length,
              output_ratio: null,
              input_paragraphs: inputParagraphs,
              output_paragraphs: 0,
            },
          },
        ],
      })
    }
    if (pathname === '/api/ai/threads/current') {
      return json(route, {
        thread: {
          id: 'demo-thread-1',
          scope_kind: 'article',
          scope_id: 'demo-article-1',
          title: articles[0].title,
          created_at: now,
          updated_at: now,
        },
        messages: [
          {
            id: 'demo-message-1',
            thread_id: 'demo-thread-1',
            role: 'user',
            content: '这个开头的节奏哪里可以再克制一点？',
            timestamp: now,
            meta: {},
          },
          {
            id: 'demo-message-2',
            thread_id: 'demo-thread-1',
            role: 'assistant',
            content: '第二句已经承担了回望和判断，可以先删去解释，让盐、潮气和亮起来的动作自己完成收束。',
            timestamp: now,
            meta: { provider: 'opencode', model: 'opencode/deepseek-v4-flash-free', transport: 'opencode_cli' },
          },
        ],
      })
    }
    if (pathname === '/api/ai/threads') return json(route, [])
    if (pathname === '/api/ai/chat-settings') return json(route, { system_prompt: '' })
    if (pathname === '/api/settings/ai') return json(route, aiSettings)
    if (pathname === '/api/settings/ai/profiles') return json(route, { profiles: aiProfiles, default_profile_id: 'demo-profile-opencode' })
    if (pathname === '/api/settings/ai/profiles/discover') return json(route, [])
    if (pathname === '/api/settings/ai/models') {
      const provider = url.searchParams.get('provider') || 'openai'
      return json(route, {
        provider,
        models: aiSettings.model_presets[provider] || [],
        source: 'preset',
        message: '当前 provider 暂未启用真实模型拉取，已显示内置预设。',
      })
    }
    if (pathname === '/api/settings/data-location') {
      return json(route, {
        data_dir: 'D:\\LivingToTellDemo\\Data',
        default_data_dir: 'D:\\LivingToTellDemo\\Data',
        database_path: 'D:\\LivingToTellDemo\\Data\\living-to-tell.sqlite3',
        default_database_path: 'D:\\LivingToTellDemo\\Data\\living-to-tell.sqlite3',
        backup_dir: 'D:\\LivingToTellDemo\\Data\\backups',
        checkpoint_dir: 'D:\\LivingToTellDemo\\Data\\checkpoints',
        is_custom: false,
        database_exists: true,
        warning: null,
      })
    }
    if (pathname === '/api/backup/stats') return json(route, { total_size: 0 })
    if (pathname === '/api/backup/backups') return json(route, [])
    if (pathname === '/api/backup/checkpoints') return json(route, [])
    if (pathname.startsWith('/api/motifs/excerpts/source/')) return json(route, [])

    return json(route, { detail: `Demo route not mocked: ${method} ${pathname}` }, 404)
  })
}

async function waitForApp(page) {
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {})
  await page.waitForTimeout(1200)
}

async function shot(page, route, filename, options = {}) {
  await page.goto(`${baseUrl}${route}`, { waitUntil: 'domcontentloaded' })
  await waitForApp(page)
  if (options.before) {
    await options.before(page)
    await page.waitForTimeout(800)
  }
  await page.screenshot({
    path: path.join(outDir, filename),
    fullPage: false,
  })
}

async function main() {
  fs.mkdirSync(outDir, { recursive: true })
  const aiOnly = process.argv.includes('--ai-only')
  const browser = await chromium.launch({
    channel: 'msedge',
    headless: true,
  }).catch(() => chromium.launch({ headless: true }))
  const page = await browser.newPage({
    viewport: { width: 1440, height: aiOnly ? 1150 : 920 },
    deviceScaleFactor: 1,
  })
  await installDemoApi(page)

  if (!aiOnly) {
    await shot(page, '/articles?id=demo-article-1', 'article-writing.png')
    await shot(page, '/articles?id=demo-article-1', 'focus-mode.png', {
      before: async (page) => {
        await page.keyboard.press('F11')
      },
    })
    await shot(page, '/collections', 'collections.png')
    await shot(page, '/library?ref=demo-reference-1&group=source', 'reference-library.png')
  }
  await shot(page, '/ai?scope_kind=article&scope_id=demo-article-1', 'ai-workspace.png', {
    before: async (page) => {
      await page.getByRole('button', { name: /^改写/ }).click()
      await page.getByRole('button', { name: '选择文脉标本' }).click()
      const dialog = page.getByRole('dialog', { name: '选择文脉标本' })
      for (const title of ['想象的书', '海边札记']) {
        const card = dialog.getByTestId('article-ai-reference-card').filter({ hasText: title })
        await card.getByRole('button', { name: new RegExp(`选择\\s+《${title}》`) }).click()
      }
      await dialog.getByRole('button', { name: '使用 2 条标本' }).click()
      await page.getByRole('heading', { name: 'AI 修改' }).scrollIntoViewIfNeeded()
    },
  })
  await shot(page, '/ai?scope_kind=article&scope_id=demo-article-1', 'ai-reference-picker.png', {
    before: async (page) => {
      await page.getByRole('button', { name: '选择文脉标本' }).click()
      const dialog = page.getByRole('dialog', { name: '选择文脉标本' })
      const card = dialog.getByTestId('article-ai-reference-card').filter({ hasText: '海边札记' })
      await card.getByRole('button', { name: /选择\s+《海边札记》/ }).click()
    },
  })
  if (!aiOnly) {
    await shot(page, '/settings?section=ai_profiles', 'settings.png')
    await shot(page, '/settings?section=ai_profiles', 'settings-wizard.png', {
      before: async (page) => {
        await page.getByRole('button', { name: '新增档案' }).click()
        await page.getByRole('button', { name: /中转站 \/ 兼容接口/ }).click()
      },
    })
    await shot(page, '/articles?id=demo-article-1&chat=1', 'article-ai-chat.png')
  }

  await browser.close()
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
