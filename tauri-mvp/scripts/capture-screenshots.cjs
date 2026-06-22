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
    if (pathname.startsWith('/api/collections/for-entry/')) return json(route, collections)
    if (pathname === '/api/library/stats') {
      return json(route, { total: references.length, by_usage_kind: { imagery: 1, style: 1 } })
    }
    if (pathname === '/api/library/references') return json(route, references)
    if (pathname === '/api/library/references/search') return json(route, references)
    if (pathname === '/api/ai-cards') return json(route, aiCards)
    if (pathname === '/api/ai-cards/presets/list') return json(route, aiCards)
    if (pathname === '/api/ai/task-presets') return json(route, {})
    if (pathname === '/api/ai/threads/current') {
      return json(route, {
        thread: {
          id: 'demo-thread-1',
          scope_kind: 'global',
          scope_id: null,
          title: '全局对话',
          created_at: now,
          updated_at: now,
        },
        messages: [
          {
            id: 'demo-message-1',
            thread_id: 'demo-thread-1',
            role: 'user',
            content: '帮我把这段文字的结尾变得更有余韵。',
            timestamp: now,
            meta: {},
          },
          {
            id: 'demo-message-2',
            thread_id: 'demo-thread-1',
            role: 'assistant',
            content: '可以把结尾落在一个可感的动作上，让主题从画面里浮出来，而不是直接解释。',
            timestamp: now,
            meta: {},
          },
        ],
      })
    }
    if (pathname === '/api/ai/threads') return json(route, [])
    if (pathname === '/api/settings/ai') return json(route, aiSettings)
    if (pathname === '/api/settings/ai/models') {
      const provider = url.searchParams.get('provider') || 'openai'
      return json(route, {
        provider,
        models: aiSettings.model_presets[provider] || [],
        source: 'preset',
        message: '当前 provider 暂未启用真实模型拉取，已显示内置预设。',
      })
    }
    if (pathname === '/api/backup/stats') return json(route, { total_size: 0 })
    if (pathname === '/api/backup/backups') return json(route, [])
    if (pathname === '/api/backup/checkpoints') return json(route, [])

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
  const browser = await chromium.launch({
    channel: 'msedge',
    headless: true,
  }).catch(() => chromium.launch({ headless: true }))
  const page = await browser.newPage({
    viewport: { width: 1440, height: 920 },
    deviceScaleFactor: 1,
  })
  await installDemoApi(page)

  await shot(page, '/articles?id=demo-article-1', 'article-writing.png')
  await shot(page, '/articles?id=demo-article-1', 'focus-mode.png', {
    before: async (page) => {
      await page.keyboard.press('F11')
    },
  })
  await shot(page, '/collections', 'collections.png')
  await shot(page, '/library?ref=demo-reference-1&group=source', 'reference-library.png')
  await shot(page, '/ai?tab=chat', 'ai-workspace.png')
  await shot(page, '/settings', 'settings.png')

  await browser.close()
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
