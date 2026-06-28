const fs = require('fs')
const path = require('path')
const { spawn, spawnSync } = require('child_process')

let chromium
try {
  ;({ chromium } = require('playwright'))
} catch {
  ;({ chromium } = require(path.resolve(__dirname, '..', 'frontend', 'node_modules', 'playwright')))
}

const baseUrl = process.env.WRITER_TUTORIAL_URL || 'http://127.0.0.1:1420'
const frontendDir = path.resolve(__dirname, '..', 'frontend')
const outDir = path.resolve(__dirname, '..', 'docs', 'assets', 'tutorials')
const frameRoot = path.join(outDir, '.frames')
const composeScript = path.resolve(__dirname, 'compose-gif.py')
const now = '2026-06-28T09:30:00'

const articleBody =
  '风从堤岸那边过来，带着一点盐和潮湿的光。\n\n' +
  '我把昨天没有写完的一段重新读了一遍，发现真正要留下的不是事件，而是那种慢慢亮起来的感觉。\n\n' +
  '如果一个段落还能让人听见脚步声、闻到雨后的石头，它就还有继续往前走的可能。'

const articles = [
  {
    id: 'demo-article-1',
    title: '清晨的海边笔记',
    body: articleBody,
    entry_type: 'article',
    created_at: '2026-06-26T08:00:00',
    updated_at: now,
    tags: ['散文', '海边', '日常'],
    archived_at: null,
    curation_status: 'draft',
  },
  {
    id: 'demo-article-2',
    title: '给远方的一封信',
    body: '我想把这封信写得慢一点，好像每一句都要经过一条长街。\n\n有些话在路上会变轻，有些话则会因为反复携带而变得更重。',
    entry_type: 'article',
    created_at: '2026-06-25T20:00:00',
    updated_at: now,
    tags: ['信', '记忆'],
    archived_at: null,
    curation_status: 'draft',
  },
]

const versions = [
  {
    id: 'demo-version-1',
    entry_id: 'demo-article-1',
    version_type: 'manual_checkpoint',
    content: articleBody.replace('慢慢亮起来的感觉', '被海风慢慢照亮的感觉'),
    title_snapshot: '清晨的海边笔记',
    tags: ['散文', '海边', '日常'],
    label: '手动保存',
    reason: '',
    word_count: 88,
    char_count: 118,
    created_at: '2026-06-28T09:10:00',
    provider: null,
    model: null,
  },
  {
    id: 'demo-version-2',
    entry_id: 'demo-article-1',
    version_type: 'ai_before_apply',
    content: articleBody,
    title_snapshot: '清晨的海边笔记',
    tags: ['散文', '海边'],
    label: 'AI 写回前快照',
    reason: '',
    word_count: 86,
    char_count: 112,
    created_at: '2026-06-28T08:50:00',
    provider: 'opencode',
    model: 'opencode/deepseek-v4-flash-free',
  },
]

const collections = [
  {
    id: 'demo-collection-1',
    title: '夏天的讲述',
    description: '收集关于日常、远方与自我确认的短文。',
    article_count: 2,
    created_at: '2026-06-24T12:00:00',
    updated_at: now,
  },
]

const collectionArticles = articles.map((article, index) => ({
  ...article,
  body_preview: article.body.slice(0, 90),
  word_count: index === 0 ? 88 : 52,
  char_count: article.body.length,
  sort_order: index + 1,
}))

const outlineItems = [
  {
    id: 'outline-1',
    collection_id: 'demo-collection-1',
    parent_id: null,
    entry_id: null,
    title: '第一部：海边的清晨',
    item_type: 'part',
    status: 'done',
    summary: '把主题落在“讲述如何让记忆变清晰”上。',
    notes: '作为整组文章的开场。',
    pov: '第一人称',
    setting: '海边小城',
    timeline: '初夏清晨',
    tags: ['主题', '开场'],
    target_word_count: 1200,
    sort_order: 1,
    created_at: now,
    updated_at: now,
  },
  {
    id: 'outline-2',
    collection_id: 'demo-collection-1',
    parent_id: null,
    entry_id: 'demo-article-1',
    title: '场景：潮湿的堤岸',
    item_type: 'scene',
    status: 'drafting',
    summary: '通过风、盐、石头和脚步声建立文章的感官底色。',
    notes: '结尾不要解释主题，让画面自己收束。',
    pov: '第一人称',
    setting: '清晨堤岸',
    timeline: '现在时',
    tags: ['海边', '感官'],
    target_word_count: 900,
    sort_order: 2,
    created_at: now,
    updated_at: now,
  },
  {
    id: 'outline-3',
    collection_id: 'demo-collection-1',
    parent_id: null,
    entry_id: 'demo-article-2',
    title: '信件：远方的回声',
    item_type: 'chapter',
    status: 'revising',
    summary: '把“远方”处理成行动距离，而不是抽象情绪。',
    notes: '需要更明确的回信动作。',
    pov: '第一人称',
    setting: '长街',
    timeline: '傍晚',
    tags: ['信', '远方'],
    target_word_count: 1100,
    sort_order: 3,
    created_at: now,
    updated_at: now,
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
    created_at: '2026-06-25T10:00:00',
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
    created_at: '2026-06-24T10:00:00',
    updated_at: now,
  },
]

const motifs = [
  { id: 'motif-wind', name: '风', aliases: [], note: '移动、消息和未说出口的话。', tags: ['自然'], pinned: true, excerpt_count: 3, created_at: now, updated_at: now },
  { id: 'motif-memory', name: '往事', aliases: [], note: '被讲述重新照亮的记忆。', tags: ['时间'], pinned: false, excerpt_count: 2, created_at: now, updated_at: now },
  { id: 'motif-sea', name: '海边', aliases: [], note: '开放空间与回声。', tags: ['空间'], pinned: false, excerpt_count: 2, created_at: now, updated_at: now },
  { id: 'motif-letter', name: '信', aliases: [], note: '迟到的表达。', tags: ['关系'], pinned: false, excerpt_count: 1, created_at: now, updated_at: now },
]

const motifExcerpts = [
  {
    id: 'excerpt-1',
    source_kind: 'article',
    source_id: 'demo-article-1',
    source_title_snapshot: '清晨的海边笔记',
    excerpt_text: '风从堤岸那边过来，带着一点盐和潮湿的光。',
    note: '开场意象。',
    selection_start: 0,
    selection_end: 22,
    before_context: '',
    after_context: '我把昨天没有写完的一段重新读了一遍',
    motif_ids: ['motif-wind', 'motif-sea'],
    motif_names: ['风', '海边'],
    source_exists: true,
    source_current_title: '清晨的海边笔记',
    created_at: now,
    updated_at: now,
  },
  {
    id: 'excerpt-2',
    source_kind: 'reference',
    source_id: 'demo-reference-1',
    source_title_snapshot: '想象的书',
    excerpt_text: '把经历讲出来，才真正知道自己曾经怎样穿过它。',
    note: '讲述与回忆。',
    selection_start: 5,
    selection_end: 28,
    before_context: '一个人只有',
    after_context: '',
    motif_ids: ['motif-memory'],
    motif_names: ['往事'],
    source_exists: true,
    source_current_title: '想象的书',
    created_at: now,
    updated_at: now,
  },
]

const aiCards = [
  {
    id: 'demo-card-style',
    title: '克制而有画面感',
    content: '【风格原型】\n句子保持清晰，减少抽象判断，多保留能被看见、听见、触摸到的细节。',
    card_type: 'style',
    tags: ['散文', '克制'],
    created_at: now,
    updated_at: now,
  },
  {
    id: 'demo-card-scene',
    title: '场景｜远方来信',
    content: '【场景原型】\n长期暧昧中的一方借远行写信推动关系变化。\n\n【核心冲突】\n我不知道你是否爱我。\n\n【场景DNA】\n暧昧关系\n+\n远距离分离\n+\n等待回应',
    card_type: 'scene',
    tags: ['场景', '关系'],
    created_at: now,
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
    source_key: 'opencode:default',
    created_at: now,
    updated_at: now,
  },
  {
    id: 'demo-profile-gemini',
    name: 'Gemini 中转',
    provider_name: 'gemini',
    base_url: 'https://demo.example/v1',
    wire_api: 'chat_completions',
    model: 'gemini-3.1-pro',
    api_key_source: 'env:GEMINI_API_KEY',
    gemini_cli_proxy: null,
    enabled: true,
    source_key: 'gemini:demo',
    created_at: now,
    updated_at: now,
  },
]

const backups = [
  { path: 'D:\\LivingToTellDemo\\Data\\backups\\auto-2026-06-28.sqlite3', name: 'auto-2026-06-28', size: 2480000, created: '2026-06-28T08:50:00' },
  { path: 'D:\\LivingToTellDemo\\Data\\backups\\auto-2026-06-27.sqlite3', name: 'auto-2026-06-27', size: 2380000, created: '2026-06-27T18:12:00' },
]

const checkpoints = [
  { path: 'D:\\LivingToTellDemo\\Data\\checkpoints\\before-outline.sqlite3', name: 'before-outline', description: '整理作品集大纲前的手动检查点。', size: 2510000, created: '2026-06-28T09:05:00' },
]

let sampleState = {
  installed: false,
  collection_id: null,
  entry_ids: [],
  reference_ids: [],
  ai_card_ids: [],
  note_ids: [],
  created_at: null,
  missing_ids: [],
}

function json(route, data, status = 200) {
  return route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(data),
  })
}

function text(route, data, contentType = 'text/plain') {
  return route.fulfill({ status: 200, contentType, body: data })
}

function graph(centerId = '') {
  return {
    nodes: motifs.map((motif) => ({
      id: motif.id,
      name: motif.name,
      excerpt_count: motif.excerpt_count,
      pinned: motif.pinned,
      is_center: motif.id === centerId,
    })),
    edges: [
      { source_id: 'motif-wind', target_id: 'motif-sea', weight: 3, shared_excerpts: 2, shared_sources: 1 },
      { source_id: 'motif-wind', target_id: 'motif-memory', weight: 2, shared_excerpts: 1, shared_sources: 1 },
      { source_id: 'motif-letter', target_id: 'motif-memory', weight: 1, shared_excerpts: 1, shared_sources: 1 },
    ],
  }
}

async function installDemoApi(page) {
  await page.addInitScript(() => {
    window.__WRITER_API_BASE__ = 'http://127.0.0.1:8000'
    localStorage.setItem('language', 'zh')
    localStorage.setItem('theme', 'light')
    localStorage.setItem('right_context_pane_collapsed', 'false')
    localStorage.setItem('living_to_tell_last_selected_entry_id', 'demo-article-1')
    localStorage.setItem('living_to_tell_last_selected_collection_id', 'demo-collection-1')
    localStorage.removeItem('living_to_tell_welcome_checklist_dismissed')
  })

  await page.route('**/*', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const pathname = url.pathname
    const method = request.method()

    if (!url.origin.startsWith('http://127.0.0.1:8000')) {
      return route.continue()
    }

    if (pathname === '/health') return json(route, { message: 'ok', version: 'demo' })
    if (pathname === '/api/app/version') {
      return json(route, {
        app_name: 'Living to Tell',
        version: '0.1.24',
        api_version: '2.0.0',
        capabilities: [
          'data_location',
          'ai_chat_settings',
          'ai_task_presets',
          'ai_profiles',
          'ai_task_compare',
          'motif_star_map',
          'article_versions',
          'collection_outline',
          'sample_project',
        ],
      })
    }

    if (pathname === '/api/onboarding/state') {
      return json(route, {
        hasArticle: true,
        hasReference: true,
        aiConfigured: true,
      })
    }
    if (pathname === '/api/onboarding/sample-project' && method === 'GET') return json(route, sampleState)
    if (pathname === '/api/onboarding/sample-project' && method === 'POST') {
      sampleState = {
        installed: true,
        collection_id: 'demo-collection-1',
        entry_ids: ['demo-article-1', 'demo-article-2'],
        reference_ids: ['demo-reference-1'],
        ai_card_ids: ['demo-card-scene'],
        note_ids: ['demo-note-1'],
        created_at: now,
        missing_ids: [],
        action: 'created',
      }
      return json(route, sampleState)
    }
    if (pathname === '/api/onboarding/sample-project' && method === 'DELETE') {
      sampleState = {
        installed: false,
        collection_id: null,
        entry_ids: [],
        reference_ids: [],
        ai_card_ids: [],
        note_ids: [],
        created_at: null,
        missing_ids: [],
        action: 'removed',
      }
      return json(route, sampleState)
    }

    if (pathname === '/api/dates/stats') return json(route, [
      { date: '2026-06-26', entry_count: 1, word_count: 88, has_curated: false },
      { date: '2026-06-27', entry_count: 1, word_count: 52, has_curated: false },
      { date: '2026-06-28', entry_count: 1, word_count: 112, has_curated: true },
    ])
    if (pathname === '/api/dates/entries') return json(route, [
      {
        id: 'demo-article-1',
        title: '清晨的海边笔记',
        body_preview: articleBody.slice(0, 90),
        created_at: now,
        tags: ['散文', '海边'],
        curation_status: 'draft',
      },
    ])
    if (pathname === '/api/dates/quote') return json(route, {
      id: 'quote-1',
      reference_id: 'demo-reference-1',
      text: references[0].content,
      source_title: references[0].source_title,
      source_author: references[0].source_author,
    })

    if (pathname === '/api/articles' && method === 'GET') return json(route, articles)
    if (pathname === '/api/articles' && method === 'POST') return json(route, { ...articles[0], id: 'demo-created-article' }, 201)
    if (pathname === '/api/articles/search') return json(route, articles)
    if (pathname === '/api/articles/demo-article-1') {
      if (method === 'PUT') {
        const body = request.postDataJSON()
        articles[0] = { ...articles[0], title: body.title ?? articles[0].title, body: body.body ?? articles[0].body, tags: body.tags ?? articles[0].tags }
      }
      return json(route, articles[0])
    }
    if (pathname === '/api/articles/demo-article-2') return json(route, articles[1])
    if (pathname === '/api/articles/demo-article-1/export') return text(route, '# 清晨的海边笔记\n\n' + articles[0].body, 'text/markdown')
    if (pathname === '/api/articles/demo-article-1/versions' && method === 'GET') return json(route, versions)
    if (pathname === '/api/articles/demo-article-1/versions' && method === 'POST') {
      const created = { ...versions[0], id: `demo-version-${versions.length + 1}`, created_at: now }
      versions.unshift(created)
      return json(route, created, 201)
    }
    if (pathname.startsWith('/api/articles/demo-article-1/versions/')) return json(route, { entry: articles[0], snapshot_version_id: null, was_noop: false })
    if (pathname === '/api/articles/demo-article-1/notes') return json(route, [
      { id: 'demo-note-1', entry_id: 'demo-article-1', body: '结尾可以回到“讲述”这一主题，但不要直接说教。', pinned: true, done_at: null, created_at: now, updated_at: now },
    ])
    if (pathname.startsWith('/api/articles/') && pathname.endsWith('/notes')) return json(route, [])

    if (pathname === '/api/collections' && method === 'GET') return json(route, collections)
    if (pathname === '/api/collections/demo-collection-1') return json(route, collections[0])
    if (pathname === '/api/collections/demo-collection-1/articles') return json(route, collectionArticles)
    if (pathname === '/api/collections/demo-collection-1/articles/order') return json(route, collectionArticles)
    if (pathname === '/api/collections/demo-collection-1/export') return text(route, '# 夏天的讲述\n\n' + articleBody, 'text/markdown')
    if (pathname === '/api/collections/demo-collection-1/outline') return json(route, outlineItems)
    if (pathname === '/api/collections/demo-collection-1/outline/order') return json(route, outlineItems)
    if (pathname.startsWith('/api/collections/demo-collection-1/outline/')) return json(route, outlineItems[0])
    if (pathname.startsWith('/api/collections/for-entry/')) return json(route, collections)

    if (pathname === '/api/library/stats') return json(route, { total: references.length, by_usage_kind: { imagery: 1, style: 1 } })
    if (pathname === '/api/library/references') return json(route, references)
    if (pathname === '/api/library/references/search') return json(route, references)
    if (pathname === '/api/library/references/demo-reference-1') return json(route, references[0])

    if (pathname === '/api/motifs') return json(route, motifs)
    if (pathname === '/api/motifs/graph') return json(route, graph())
    if (pathname === '/api/motifs/motif-wind/excerpts') return json(route, motifExcerpts.filter((excerpt) => excerpt.motif_ids.includes('motif-wind')))
    if (pathname === '/api/motifs/motif-wind/graph') return json(route, graph('motif-wind'))
    if (pathname.startsWith('/api/motifs/') && pathname.endsWith('/excerpts')) return json(route, motifExcerpts)
    if (pathname.startsWith('/api/motifs/') && pathname.endsWith('/graph')) return json(route, graph())
    if (pathname.startsWith('/api/motifs/excerpts/source/')) return json(route, motifExcerpts)
    if (pathname === '/api/motifs/excerpts/lookup') return json(route, motifExcerpts[0])

    if (pathname === '/api/ai-cards') return json(route, aiCards)
    if (pathname === '/api/ai-cards/search') return json(route, aiCards.filter((card) => !url.searchParams.get('card_type') || card.card_type === url.searchParams.get('card_type')))
    if (pathname === '/api/ai-cards/demo-card-style') return json(route, aiCards[0])
    if (pathname === '/api/ai-cards/demo-card-scene') return json(route, aiCards[1])
    if (pathname === '/api/ai-cards/presets/list') return json(route, aiCards)
    if (pathname === '/api/ai-cards/generate-draft') return json(route, {
      title: '场景｜雨夜来信',
      card_type: 'scene',
      content: '【场景原型】\n雨夜里收到一封迟来的信。\n\n【核心冲突】\n等待是否还值得。\n\n【场景DNA】\n等待\n+\n迟到的消息\n+\n关系转折',
    })

    if (pathname === '/api/ai/task-presets') return json(route, {})
    if (pathname === '/api/ai/task/compare') {
      const body = request.postDataJSON()
      const inputText = body.text || ''
      return json(route, {
        task_type: body.task_type || 'polish',
        results: [
          {
            profile_id: 'default',
            profile_name: '默认配置',
            provider: 'openai',
            model: 'gpt-4o-mini',
            transport: 'responses',
            status: 'success',
            result: '风从堤岸那边吹来，裹着盐意和潮湿的晨光。\n\n我重新读完昨天搁下的段落，才意识到真正应该留下的不是事件本身，而是它慢慢亮起来的过程。',
            error: '',
            elapsed_ms: 1280,
            input_tokens: 72,
            output_tokens: 118,
            cost: 0.0004,
            finish_reason: 'stop',
            stats: { input_chars: inputText.length, output_chars: 92, delta_chars: 14, output_ratio: 1.12, input_paragraphs: 2, output_paragraphs: 2 },
          },
          {
            profile_id: 'demo-profile-opencode',
            profile_name: 'OpenCode · DeepSeek Flash',
            provider: 'opencode',
            model: 'opencode/deepseek-v4-flash-free',
            transport: 'opencode_cli',
            status: 'success',
            result: '风越过堤岸，带来盐、潮气和一点清晨的亮。\n\n我把昨天没写完的段落又读了一遍，发现该留下的并不是发生过什么，而是那种被光一点点托起来的感觉。',
            error: '',
            elapsed_ms: 2140,
            input_tokens: 76,
            output_tokens: 109,
            cost: 0,
            finish_reason: 'stop',
            stats: { input_chars: inputText.length, output_chars: 88, delta_chars: 10, output_ratio: 1.08, input_paragraphs: 2, output_paragraphs: 2 },
          },
        ],
      })
    }
    if (pathname === '/api/ai/threads/current') return json(route, {
      thread: { id: 'demo-thread-1', scope_kind: 'global', scope_id: null, title: '全局对话', created_at: now, updated_at: now },
      messages: [],
    })
    if (pathname === '/api/ai/threads') return json(route, [])
    if (pathname === '/api/ai/chat-settings') return json(route, { system_prompt: '' })

    if (pathname === '/api/settings/ai') return json(route, {
      provider_name: 'openai',
      base_url: 'https://api.openai.com/v1',
      wire_api: 'responses',
      model: 'gpt-4o-mini',
      api_key_source: 'env:OPENAI_API_KEY',
      gemini_cli_proxy: null,
      status: {
        env: { available: false, path: null, reason: 'Demo only' },
        codex: { available: false, path: null, reason: 'Demo only' },
        gemini: { available: false, path: null, reason: 'Demo only' },
        gemini_cli: { available: false, path: null, reason: 'Demo only', account: null, command: 'gemini', proxy: null },
        opencode: { available: false, path: null, reason: 'Demo only', account: null, command: 'opencode', proxy: null },
      },
      model_presets: { openai: ['gpt-4o-mini'], gemini: ['gemini-2.5-flash'], gemini_cli: ['gemini-cli-default'], opencode: ['opencode/deepseek-v4-flash-free'] },
    })
    if (pathname === '/api/settings/ai/profiles') return json(route, { profiles: aiProfiles })
    if (pathname === '/api/settings/ai/profiles/discover') return json(route, [])
    if (pathname === '/api/settings/ai/models') return json(route, { provider: url.searchParams.get('provider') || 'openai', models: ['opencode/deepseek-v4-flash-free'], source: 'preset', message: '演示模型列表。' })
    if (pathname === '/api/settings/data-location') return json(route, {
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

    if (pathname === '/api/backup/stats') return json(route, {
      backup_count: backups.length,
      checkpoint_count: checkpoints.length,
      total_backup_size: backups.reduce((sum, item) => sum + item.size, 0),
      total_checkpoint_size: checkpoints.reduce((sum, item) => sum + item.size, 0),
      total_size: backups.reduce((sum, item) => sum + item.size, 0) + checkpoints.reduce((sum, item) => sum + item.size, 0),
      backup_dir: 'D:\\LivingToTellDemo\\Data\\backups',
      checkpoint_dir: 'D:\\LivingToTellDemo\\Data\\checkpoints',
    })
    if (pathname === '/api/backup/backups') return json(route, backups)
    if (pathname === '/api/backup/checkpoints' && method === 'GET') return json(route, checkpoints)
    if (pathname === '/api/backup/checkpoints' && method === 'POST') {
      const body = request.postDataJSON()
      const checkpoint = { path: `D:\\LivingToTellDemo\\Data\\checkpoints\\${body.name}.sqlite3`, name: body.name, description: body.description || '', size: 2520000, created: now }
      checkpoints.unshift(checkpoint)
      return json(route, checkpoint, 201)
    }
    if (pathname === '/api/backup/auto-backup') {
      const backup = { path: 'D:\\LivingToTellDemo\\Data\\backups\\auto-demo.sqlite3', name: 'auto-demo', size: 2490000, created: now }
      backups.unshift(backup)
      return json(route, backup, 201)
    }
    if (pathname === '/api/backup/restore') return json(route, { ok: true })

    return json(route, { detail: `Demo route not mocked: ${method} ${pathname}` }, 404)
  })
}

async function waitForServer() {
  const healthUrl = `${baseUrl}/`
  for (let i = 0; i < 10; i += 1) {
    try {
      const response = await fetch(healthUrl)
      if (response.ok) return { started: false, process: null }
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 250))
    }
  }
  const child = spawn('npm', ['run', 'dev', '--', '--host', '127.0.0.1', '--port', '1420'], {
    cwd: frontendDir,
    shell: true,
    stdio: 'ignore',
  })
  for (let i = 0; i < 80; i += 1) {
    try {
      const response = await fetch(healthUrl)
      if (response.ok) return { started: true, process: child }
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 500))
    }
  }
  child.kill()
  throw new Error(`Vite dev server did not start at ${baseUrl}.`)
}

async function waitForApp(page) {
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {})
  await page.waitForTimeout(500)
}

async function setCaption(page, text) {
  await page.evaluate((captionText) => {
    let el = document.getElementById('tutorial-caption')
    if (!el) {
      el = document.createElement('div')
      el.id = 'tutorial-caption'
      el.style.position = 'fixed'
      el.style.left = '50%'
      el.style.top = '18px'
      el.style.transform = 'translateX(-50%)'
      el.style.zIndex = '99999'
      el.style.maxWidth = '780px'
      el.style.padding = '10px 16px'
      el.style.borderRadius = '999px'
      el.style.background = 'rgba(20, 24, 32, 0.88)'
      el.style.color = 'white'
      el.style.font = '600 14px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
      el.style.boxShadow = '0 18px 50px rgba(15, 23, 42, 0.24)'
      el.style.pointerEvents = 'none'
      document.body.appendChild(el)
    }
    el.textContent = captionText
  }, text)
}

async function capture(page, frames, flowDir, caption, duration = 1300) {
  await setCaption(page, caption)
  await page.waitForTimeout(250)
  const file = path.join(flowDir, `${String(frames.length + 1).padStart(2, '0')}.png`)
  await page.screenshot({ path: file, fullPage: false })
  frames.push({ path: file, duration })
}

async function goto(page, route) {
  await page.goto(`${baseUrl}${route}`, { waitUntil: 'domcontentloaded' })
  await waitForApp(page)
}

async function clickText(page, text, exact = false) {
  const locator = page.getByText(text, { exact }).first()
  await locator.click({ timeout: 5000 })
  await page.waitForTimeout(500)
}

function pythonPath() {
  const candidates = [
    process.env.PYTHON,
    'D:\\anaconda\\envs\\writer\\python.exe',
    'python',
  ].filter(Boolean)
  for (const candidate of candidates) {
    const result = spawnSync(candidate, ['-c', 'import PIL'], { stdio: 'ignore', shell: false })
    if (result.status === 0) return candidate
  }
  throw new Error('Python with Pillow is required. Install Pillow or set PYTHON to the writer environment.')
}

function composeGif(frames, flowDir, filename) {
  const manifest = path.join(flowDir, 'manifest.json')
  const output = path.join(outDir, filename)
  fs.writeFileSync(manifest, JSON.stringify({ frames }, null, 2), 'utf-8')
  const result = spawnSync(
    pythonPath(),
    [composeScript, manifest, output, '--max-width', '920'],
    { cwd: path.resolve(__dirname, '..', '..'), encoding: 'utf-8' },
  )
  if (result.status !== 0) {
    throw new Error(`GIF compose failed for ${filename}\n${result.stdout}\n${result.stderr}`)
  }
}

async function recordFlow(browser, filename, run) {
  const flowDir = path.join(frameRoot, filename.replace(/\.gif$/, ''))
  fs.rmSync(flowDir, { recursive: true, force: true })
  fs.mkdirSync(flowDir, { recursive: true })
  const page = await browser.newPage({ viewport: { width: 1180, height: 720 }, deviceScaleFactor: 1 })
  await installDemoApi(page)
  const frames = []
  try {
    await run(page, frames, flowDir)
    composeGif(frames, flowDir, filename)
  } finally {
    await page.close()
    fs.rmSync(flowDir, { recursive: true, force: true })
  }
}

async function main() {
  fs.mkdirSync(outDir, { recursive: true })
  fs.rmSync(frameRoot, { recursive: true, force: true })
  const server = await waitForServer()
  const browser = await chromium.launch({ channel: 'msedge', headless: true }).catch(() => chromium.launch({ headless: true }))
  try {
    await recordFlow(browser, '01-sample-project.gif', async (page, frames, dir) => {
      await goto(page, '/dates')
      await capture(page, frames, dir, 'Step 1：日期页欢迎清单给出第一条上手路径。')
      await clickText(page, '创建示例项目')
      await capture(page, frames, dir, 'Step 2：主动创建示例项目，演示数据不会自动污染你的库。')
      await clickText(page, '打开作品集')
      await capture(page, frames, dir, 'Step 3：进入示例作品集，快速理解文章、文脉、AI Card 如何串联。')
      await goto(page, '/dates')
      page.once('dialog', (dialog) => dialog.accept())
      await clickText(page, '删除示例')
      await capture(page, frames, dir, 'Step 4：删除只清理 marker 记录的示例内容，不按标题或标签误删。')
    })

    await recordFlow(browser, '02-article-writing.gif', async (page, frames, dir) => {
      await goto(page, '/articles?id=demo-article-1')
      await capture(page, frames, dir, 'Step 1：打开文章，正文自动保存，右侧保留便签和上下文。')
      await clickText(page, '历史版本')
      await capture(page, frames, dir, 'Step 2：打开历史版本，重要修改前可以手动保存检查点。')
      await clickText(page, '保存当前版本')
      await capture(page, frames, dir, 'Step 3：检查点进入版本列表，后续可对比、复制、恢复或克隆。')
      await page.keyboard.press('F11')
      await page.waitForTimeout(700)
      await capture(page, frames, dir, 'Step 4：专注模式只保留写作表面，适合长文收束。')
    })

    await recordFlow(browser, '03-collection-planning.gif', async (page, frames, dir) => {
      await goto(page, '/collections')
      await capture(page, frames, dir, 'Step 1：作品集先管理文章顺序和阅读节奏。')
      await page.getByRole('button', { name: /^大纲$/ }).click()
      await page.waitForTimeout(500)
      await capture(page, frames, dir, 'Step 2：切到大纲，把长篇拆成分部、章节、场景和笔记。')
      await page.getByRole('button', { name: /^规划看板$/ }).click()
      await page.waitForTimeout(500)
      await capture(page, frames, dir, 'Step 3：规划看板按状态总览构思、草稿、修订、完成和暂停。')
      await clickText(page, '场景：潮湿的堤岸')
      await capture(page, frames, dir, 'Step 4：选择大纲卡片后，在右侧维护摘要、目标字数和关联文章。')
    })

    await recordFlow(browser, '04-reference-motif.gif', async (page, frames, dir) => {
      await goto(page, '/library?ref=demo-reference-1&group=source')
      await capture(page, frames, dir, 'Step 1：文脉库保存摘录、出处、用途和个人笔记。')
      await goto(page, '/articles?id=demo-article-1')
      await capture(page, frames, dir, 'Step 2：在文章或文脉中选中文字，右键加入一个或多个意象。')
      await goto(page, '/motifs?id=motif-wind')
      await capture(page, frames, dir, 'Step 3：意象星图用节点、颜色和连线呈现反复出现的意象关系。')
      await clickText(page, '风', true).catch(() => {})
      await capture(page, frames, dir, 'Step 4：意象详情保留来源摘录，可回到文章或文脉原位置。')
    })

    await recordFlow(browser, '05-ai-cards.gif', async (page, frames, dir) => {
      await goto(page, '/settings?section=ai_profiles')
      await capture(page, frames, dir, 'Step 1：设置中区分本地配置检查和真实请求测试。')
      await goto(page, '/ai?tab=tools')
      await page.getByPlaceholder('粘贴需要处理的文本...').fill(articleBody)
      await page.locator('label').filter({ hasText: 'OpenCode · DeepSeek Flash' }).click()
      await capture(page, frames, dir, 'Step 2：在 AI 工具中勾选多个配置档案，同一任务并行对比。')
      await page.getByRole('button', { name: /运行/ }).click()
      await page.getByText('风从堤岸那边吹来').waitFor({ timeout: 6000 })
      await capture(page, frames, dir, 'Step 3：逐张结果卡比较字数、段落、耗时、token 和成本。')
      await goto(page, '/ai-cards?id=demo-card-scene')
      await capture(page, frames, dir, 'Step 4：AI Card 用风格、人物、场景模板沉淀可复用写作上下文。')
    })

    await recordFlow(browser, '06-export-backup.gif', async (page, frames, dir) => {
      await goto(page, '/backup')
      await capture(page, frames, dir, 'Step 1：备份中心先回答“我现在能不能恢复”。')
      await clickText(page, '创建检查点')
      await page.getByPlaceholder('例如：完成第三章').fill('教程检查点')
      await page.getByPlaceholder('添加一些说明...').fill('录制教程前的安全恢复点')
      await capture(page, frames, dir, 'Step 2：大改前创建命名检查点，方便以后识别。')
      await page.getByRole('button', { name: /^创建$/ }).click()
      await capture(page, frames, dir, 'Step 3：检查点和自动备份一起进入恢复点列表。')
      await clickText(page, '恢复所选')
      await capture(page, frames, dir, 'Step 4：恢复前会明确确认；应用会先备份当前数据库再恢复。')
    })
  } finally {
    await browser.close()
    fs.rmSync(frameRoot, { recursive: true, force: true })
    if (server.started && server.process) server.process.kill()
  }
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
