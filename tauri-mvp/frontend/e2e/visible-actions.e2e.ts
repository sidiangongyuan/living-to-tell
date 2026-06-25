import { expect, test, type Page } from '@playwright/test'

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

async function mockVisibleActionApi(page: Page) {
  await page.addInitScript(() => {
    window.localStorage.clear()
    ;(window as Window & { __WRITER_DISABLE_AUTO_UPDATE__?: boolean }).__WRITER_DISABLE_AUTO_UPDATE__ = true
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: async (text: string) => {
          window.__copiedText = text
        },
      },
      configurable: true,
    })
  })

  await page.route('**/api/app/version', async (route) => {
    await route.fulfill({
      json: {
        app_name: 'Living to Tell',
        version: '0.1.9',
        api_version: '2.0.0',
        capabilities: ['data_location', 'ai_chat_settings', 'ai_task_presets', 'update_check'],
      },
    })
  })
  await page.route('**/api/app/update-check*', async (route) => {
    await route.fulfill({
      json: {
        current_version: '0.1.9',
        latest_version: '0.1.9',
        latest_tag: 'living-to-tell-v0.1.9',
        release_name: 'Living to Tell Preview 0.1.9',
        release_url: 'https://github.com/sidiangongyuan/living-to-tell/releases/tag/living-to-tell-v0.1.9',
        published_at: '2026-06-25T03:03:04Z',
        release_notes: '',
        source: 'github_releases_latest',
        status: 'up_to_date',
        message: '当前已是最新版本。',
        checked_at: '2026-06-25T03:05:06Z',
        cached: false,
        download_url: 'https://github.com/sidiangongyuan/living-to-tell/releases/download/living-to-tell-v0.1.9/LivingToTell_0.1.9_x64-setup.exe',
        download_name: 'LivingToTell_0.1.9_x64-setup.exe',
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
    await route.fulfill({ status: 201, json: { ...article, id: 'article-created', title: '新文章' } })
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
  await expect(page.getByTestId('article-body-editor')).toHaveValue(article.body)

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
  await expect(page.getByTestId('article-body-editor')).toHaveValue(article.body)
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
  await expect(page.getByTestId('article-body-editor')).toHaveValue(article.body)

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
  await expect(page.getByTestId('article-body-editor')).toHaveValue(article.body)

  await page.getByTestId('article-body-editor').fill('切换前未保存正文')
  await page.getByTestId('article-entry-article-b').click()
  await expect.poll(() => updates.some((body) => body.body === '切换前未保存正文')).toBe(true)
  await expect(page.getByTestId('article-body-editor')).toHaveValue(articleB.body)

  await page.goto('/articles?id=article-a')
  await page.getByTestId('article-body-editor').fill('AI 对话前未保存正文')
  await page.getByRole('button', { name: 'AI 对话', exact: true }).click()
  await expect.poll(() => updates.some((body) => body.body === 'AI 对话前未保存正文')).toBe(true)
  await expect(page).toHaveURL(/\/ai\?.*tab=chat/)
  await expect(page).toHaveURL(/scope_id=article-a/)

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
  await expect(page.getByTestId('article-body-editor')).toHaveValue(article.body)

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

  await page.getByTestId('article-body-editor').fill('自动保存正文')
  await expect.poll(() => updates.at(-1)?.body).toBe('自动保存正文')

  await page.getByRole('button', { name: 'AI 对话' }).click()
  await expect(page).toHaveURL(/\/ai\?.*tab=chat/)
  await expect(page).toHaveURL(/scope_id=article-a/)

  await page.goto('/articles?id=article-a')
  await page.getByRole('button', { name: 'AI 工具' }).click()
  await expect(page).toHaveURL(/\/ai\?.*tab=tools/)
  await expect(page).toHaveURL(/scope_id=article-a/)

  await page.goto('/articles?id=article-a')
  await page.getByRole('button', { name: '归档' }).click()
  await expect.poll(() => archiveRequests).toEqual(['POST'])

  await page.goto('/articles?id=article-a')
  await page.getByRole('button', { name: '加入作品集' }).click()
  await page.getByRole('button', { name: /测试作品集/ }).click()
  await page.getByRole('button', { name: '确认' }).click()
  await expect.poll(() => addedToCollections).toEqual([[collection.id]])
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
  await welcomePanel.getByRole('button', { name: '查看备份与数据说明' }).click()
  await expect(page).toHaveURL(/\/backup/)

  await page.goto('/dates')
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

test('date article cards open the selected article from the calendar', async ({ page }) => {
  await page.goto('/dates')

  await page.locator('article').filter({ hasText: '导出测试文章' }).click()

  await expect(page).toHaveURL(/\/articles\?.*id=article-a/)
  await expect(page.getByTestId('article-body-editor')).toHaveValue(article.body)
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
  await expect(page).toHaveURL(/\/ai\?.*tab=chat/)
  await expect(page).toHaveURL(/scope_kind=article/)
  await expect(page).toHaveURL(/scope_id=article-a/)
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

  await expect(page.getByPlaceholder(/输入命令|Type a command/)).toBeVisible()
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
  const addedRequests: string[][] = []
  let removedRequests = 0
  let deleteCollectionRequests = 0
  let reorderRequests: string[][] = []

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
    const body = route.request().postDataJSON() as { entry_ids?: string[] }
    reorderRequests.push(body.entry_ids ?? [])
    await route.fulfill({ json: [collectionArticleB, collectionArticle] })
  })
  await page.route('**/api/collections/collection-a/articles/article-a', async (route) => {
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
  await expect(page.getByText('测试作品集')).toBeVisible()

  await page.getByRole('complementary').getByRole('button', { name: '+ 新建', exact: true }).click()
  await expect(page.getByRole('heading', { name: '新建作品集' })).toBeVisible()
  await page.getByRole('button', { name: '取消' }).click()
  await expect(page.getByRole('heading', { name: '新建作品集' })).toHaveCount(0)

  for (const [buttonName, extension] of [
    ['Markdown', 'md'],
    ['TXT', 'txt'],
    ['DOCX', 'docx'],
  ] as const) {
    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: buttonName }).click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe(`测试作品集.${extension}`)
  }

  await page.getByRole('button', { name: '添加文章' }).first().click()
  await expect(page.getByRole('heading', { name: '添加文章到作品集' })).toBeVisible()
  await page.getByRole('button', { name: '取消' }).click()
  await expect(page.getByRole('heading', { name: '添加文章到作品集' })).toHaveCount(0)
  expect(addedRequests).toEqual([])

  await page.getByRole('button', { name: '添加文章' }).first().click()
  await page.getByRole('button', { name: /备选文章/ }).click()
  await page.getByRole('button', { name: /加入所选文章/ }).click()
  await expect.poll(() => addedRequests).toEqual([[articleB.id]])

  const firstCard = page.locator('article').filter({ hasText: '导出测试文章' }).first()
  await firstCard.hover()
  await firstCard.getByRole('button', { name: '↓' }).click()
  await expect.poll(() => reorderRequests).toEqual([[articleB.id, article.id]])

  await firstCard.hover()
  page.once('dialog', async (dialog) => dialog.dismiss())
  await firstCard.getByRole('button', { name: '删除' }).click()
  expect(removedRequests).toBe(0)

  await firstCard.hover()
  page.once('dialog', async (dialog) => dialog.accept())
  await firstCard.getByRole('button', { name: '删除' }).click()
  await expect.poll(() => removedRequests).toBe(1)

  page.once('dialog', async (dialog) => dialog.dismiss())
  await page.getByRole('button', { name: '删除' }).first().click()
  expect(deleteCollectionRequests).toBe(0)

  page.once('dialog', async (dialog) => dialog.accept())
  await page.getByRole('button', { name: '删除' }).first().click()
  await expect.poll(() => deleteCollectionRequests).toBe(1)
})

test('collection export flushes edited title before downloading', async ({ page }) => {
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
  await expect(page.getByText('测试作品集')).toBeVisible()
  await page.getByPlaceholder('作品集标题').fill('刚修改的作品集标题')

  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Markdown' }).click()
  const download = await downloadPromise

  await expect.poll(() => updates.some((body) => body.title === '刚修改的作品集标题')).toBe(true)
  expect(download.suggestedFilename()).toBe('刚修改的作品集标题.md')
})

test('collection reorder failures show a visible error', async ({ page }) => {
  await page.route('**/api/collections/collection-a/articles', async (route) => {
    await route.fulfill({ json: [collectionArticle, collectionArticleB] })
  })
  await page.route('**/api/collections/collection-a/articles/order', async (route) => {
    await route.fulfill({ status: 500, json: { detail: '排序保存失败' } })
  })

  await page.goto('/collections')
  await expect(page.getByText('测试作品集')).toBeVisible()

  const firstCard = page.locator('article').filter({ hasText: '导出测试文章' }).first()
  await firstCard.hover()
  await firstCard.getByRole('button', { name: '↓' }).click()

  await expect(page.getByRole('main').getByText('排序保存失败')).toBeVisible()
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

test('collection actions show validation instead of acting like no-ops when the title is empty', async ({ page }) => {
  let exportRequests = 0

  await page.route('**/api/collections/collection-a/export?**', async (route) => {
    exportRequests += 1
    await route.fulfill({ body: 'should-not-export' })
  })

  await page.goto('/collections')
  const titleInput = page.getByPlaceholder('作品集标题')
  await expect(titleInput).toHaveValue('测试作品集')
  await titleInput.fill('')

  await page.getByRole('button', { name: 'Markdown' }).click()
  await expect(page.getByText('作品集标题不能为空。')).toBeVisible()
  expect(exportRequests).toBe(0)

  await page.getByRole('button', { name: '添加文章' }).first().click()
  await expect(page.getByText('作品集标题不能为空。')).toBeVisible()
  await expect(page.getByText('可一次选择多篇文章；已加入的文章会自动标记。')).toHaveCount(0)
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
  await page.locator('textarea').first().fill('无法保存的内容')
  await expect(page.getByText('保存失败：磁盘不可写')).toBeVisible()
})

test('AI tools run tasks, attach contexts, and keep generated outputs actionable', async ({ page }) => {
  const taskBodies: Array<Record<string, unknown>> = []

  await page.route('**/api/ai/task', async (route) => {
    const body = route.request().postDataJSON() as Record<string, unknown>
    taskBodies.push(body)
    await route.fulfill({ json: { result: 'AI 生成结果', task_type: body.task_type ?? 'polish' } })
  })

  await page.goto('/ai?tab=tools&scope_kind=article&scope_id=article-a')
  await expect(page.getByRole('button', { name: '运行任务' })).toBeVisible()

  await page.getByRole('button', { name: '添加文章便签' }).click()
  await page.getByRole('button', { name: '加入全部未完成' }).click()
  await expect(page.getByText('上下文已添加')).toBeVisible()
  await expect(page.getByText('文章便签 · 1 条')).toBeVisible()
  await page.getByRole('button', { name: '完成', exact: true }).click()

  await page.getByRole('button', { name: '添加文脉标本' }).click()
  await page.getByPlaceholder('搜索标本...').fill('不存在的标本')
  await page.getByPlaceholder('搜索标本...').press('Enter')
  await expect(page.getByText('暂无标本。点击"新建"添加。')).toBeVisible()
  await page.getByPlaceholder('搜索标本...').fill('')
  await page.getByPlaceholder('搜索标本...').press('Enter')
  await page.getByRole('button', { name: /已有标本正文/ }).click()
  await page.getByRole('button', { name: /添加所选上下文/ }).click()
  await page.getByRole('button', { name: '完成', exact: true }).click()
  const referenceContext = page.locator('article').filter({ hasText: '测试书' })
  await expect(referenceContext).toBeVisible()
  await referenceContext.getByRole('button', { name: '×' }).click()
  await expect(referenceContext).toHaveCount(0)

  await page.getByRole('button', { name: '添加文脉标本' }).click()
  await page.getByRole('button', { name: /已有标本正文/ }).click()
  await page.getByRole('button', { name: /添加所选上下文/ }).click()
  await expect(page.locator('article').filter({ hasText: '测试书' })).toBeVisible()
  await page.getByRole('button', { name: '完成', exact: true }).click()

  await page.getByRole('button', { name: '运行任务' }).click()
  await expect.poll(() => taskBodies.length).toBe(1)
  expect(taskBodies[0]).toEqual(expect.objectContaining({
    task_type: 'polish',
    target_kind: 'article',
    target_ref_id: article.id,
  }))
  expect(taskBodies[0].attachments).toEqual(expect.arrayContaining([
    expect.objectContaining({ kind: 'writing_note' }),
    expect.objectContaining({ kind: 'reference' }),
  ]))
  await expect(page.getByText('AI 生成结果')).toBeVisible()

  await page.getByRole('button', { name: '复制结果' }).click()
  await expect.poll(() => page.evaluate(() => window.__copiedText)).toBe('AI 生成结果')
  await expect(page.getByText('已复制到剪贴板')).toBeVisible()

  await page.getByRole('button', { name: '返回' }).click()
  await expect(page.getByText('选择任务类型和输入内容，点击"运行任务"')).toBeVisible()
})

test('AI presets, card contexts, and clear controls update the workspace visibly', async ({ page }) => {
  let savedPresets: Record<string, unknown[]> = {}

  await page.route('**/api/ai/task-presets', async (route) => {
    if (route.request().method() === 'PUT') {
      savedPresets = route.request().postDataJSON() as Record<string, unknown[]>
      await route.fulfill({ json: savedPresets })
      return
    }
    await route.fulfill({ json: savedPresets })
  })

  await page.goto('/ai?tab=tools')
  await page.getByPlaceholder('预设名称').fill('测试预设')
  await page.getByRole('button', { name: '保存' }).click()
  await expect.poll(() => savedPresets.polish?.length ?? 0).toBe(1)
  await expect(page.getByText('预设已保存')).toBeVisible()
  await expect(page.getByRole('button', { name: '测试预设' })).toBeVisible()

  await page.getByRole('button', { name: '测试预设' }).click()
  await expect(page.getByText('预设已应用')).toBeVisible()
  await page.getByRole('button', { name: '删除' }).click()
  await expect.poll(() => savedPresets.polish?.length ?? 0).toBe(0)
  await expect(page.getByRole('button', { name: '测试预设' })).toHaveCount(0)

  await page.getByRole('button', { name: '添加 AI 卡片' }).click()
  await page.getByRole('button', { name: /克制风格/ }).click()
  await expect(page.locator('article').filter({ hasText: '克制风格' })).toBeVisible()
  await page.getByPlaceholder('搜索风格、人物、场景卡...').fill('等待')
  await page.getByRole('button', { name: /等待回应/ }).click()
  await expect(page.locator('article').filter({ hasText: '等待回应' })).toBeVisible()
  await page.getByRole('button', { name: '完成', exact: true }).click()
  await page.getByRole('button', { name: '清空上下文' }).click()
  await expect(page.locator('article').filter({ hasText: '等待回应' })).toHaveCount(0)
  await page.getByRole('button', { name: '添加 AI 卡片' }).click()
  await page.getByPlaceholder('搜索风格、人物、场景卡...').fill('')
  await expect(page.getByRole('button', { name: /克制风格/ })).toHaveCount(1)
  await expect(page.getByRole('button', { name: /等待回应/ })).toHaveCount(1)
  await page.getByRole('button', { name: '完成', exact: true }).click()
  await expect(page.getByText('尚未添加上下文。AI 只会处理原文，除非你手动加入卡片、便签或文脉标本。')).toBeVisible()

  await page.getByRole('button', { name: '粘贴文本' }).click()
  await page.getByPlaceholder('粘贴需要处理的文本...').fill('需要润色的文本')
  await page.getByRole('button', { name: '运行任务' }).click()
  await expect(page.getByText('AI 生成结果')).toBeVisible()

  await page.getByRole('button', { name: '清空结果' }).click()
  await expect(page.getByText('当前结果已清空')).toBeVisible()
  await expect(page.getByText('AI 生成结果')).toHaveCount(0)

  await page.getByPlaceholder('粘贴需要处理的文本...').fill('临时输入')
  await page.getByRole('button', { name: '清空任务' }).click()
  await expect(page.getByText('当前任务状态已清空')).toBeVisible()
  await expect(page.getByPlaceholder('粘贴需要处理的文本...')).toHaveValue('')

  await page.getByPlaceholder('粘贴需要处理的文本...').fill('准备清空全部')
  page.once('dialog', async (dialog) => dialog.dismiss())
  await page.getByRole('button', { name: '清空全部' }).click()
  await expect(page.getByPlaceholder('粘贴需要处理的文本...')).toHaveValue('准备清空全部')

  page.once('dialog', async (dialog) => dialog.accept())
  await page.getByRole('button', { name: '清空全部' }).click()
  await expect(page.getByText('全部 AI 工作区状态已清空')).toBeVisible()
  await expect(page.getByRole('button', { name: '粘贴文本' })).toBeVisible()
})

test('AI result replace cancel does not update the selected article', async ({ page }) => {
  const updates: Array<{ title?: string; body?: string; tags?: string[] }> = []

  await page.route('**/api/articles/article-a', async (route) => {
    const request = route.request()
    if (request.method() === 'PUT') {
      const body = request.postDataJSON() as { title?: string; body?: string; tags?: string[] }
      updates.push(body)
      await route.fulfill({ json: { ...article, ...body } })
      return
    }
    await route.fulfill({ json: article })
  })

  await page.goto('/ai?tab=tools&scope_kind=article&scope_id=article-a')
  await page.getByRole('button', { name: '运行任务' }).click()
  await expect(page.getByText('AI 生成结果')).toBeVisible()

  await page.evaluate(() => {
    window.__confirmMessages = []
    window.confirm = (message?: string) => {
      window.__confirmMessages?.push(String(message ?? ''))
      return false
    }
  })
  await page.getByRole('button', { name: '✏️ 替换原文' }).click()
  await expect.poll(() => page.evaluate(() => window.__confirmMessages?.length ?? 0)).toBe(1)
  await expect.poll(() => page.evaluate(() => window.__confirmMessages?.[0] ?? '')).toContain('确定要替换原文章内容吗')
  expect(updates).toEqual([])
})

test('AI result replace updates the selected article after confirmation', async ({ page }) => {
  const updates: Array<{ title?: string; body?: string; tags?: string[] }> = []

  await page.route('**/api/articles/article-a', async (route) => {
    const request = route.request()
    if (request.method() === 'PUT') {
      const body = request.postDataJSON() as { title?: string; body?: string; tags?: string[] }
      updates.push(body)
      await route.fulfill({ json: { ...article, ...body } })
      return
    }
    await route.fulfill({ json: article })
  })

  await page.goto('/ai?tab=tools&scope_kind=article&scope_id=article-a')
  await page.getByRole('button', { name: '运行任务' }).click()
  await expect(page.getByText('AI 生成结果')).toBeVisible()

  await page.evaluate(() => {
    window.__confirmMessages = []
    window.confirm = (message?: string) => {
      window.__confirmMessages?.push(String(message ?? ''))
      return true
    }
  })
  await page.getByRole('button', { name: '✏️ 替换原文' }).click()
  await expect.poll(() => page.evaluate(() => window.__confirmMessages?.length ?? 0)).toBe(1)
  await expect.poll(() => updates.length).toBe(1)
  expect(updates[0]).toEqual(expect.objectContaining({ body: 'AI 生成结果' }))
  await expect(page).toHaveURL(/\/articles\?.*id=article-a/)
  await expect(page).toHaveURL(/focus_start=/)
})

test('AI result insert appends to the selected article', async ({ page }) => {
  const updates: Array<{ title?: string; body?: string; tags?: string[] }> = []

  await page.route('**/api/articles/article-a', async (route) => {
    const request = route.request()
    if (request.method() === 'PUT') {
      const body = request.postDataJSON() as { title?: string; body?: string; tags?: string[] }
      updates.push(body)
      await route.fulfill({ json: { ...article, ...body } })
      return
    }
    await route.fulfill({ json: article })
  })

  await page.goto('/ai?tab=tools&scope_kind=article&scope_id=article-a')
  await page.getByRole('button', { name: '运行任务' }).click()
  await page.getByRole('button', { name: '插入到文末' }).click()
  await expect.poll(() => updates.length).toBe(1)
  expect(updates[0].body).toContain(article.body)
  expect(updates[0].body).toContain('AI 生成结果')
})

test('AI article chat can copy assistant replies and save them as article notes', async ({ page }) => {
  const noteBodies: string[] = []

  await page.route('**/api/articles/article-a/notes', async (route) => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON() as { body?: string }
      noteBodies.push(body.body ?? '')
      await route.fulfill({ status: 201, json: { ...openNote, id: 'note-from-chat', body: body.body ?? '' } })
      return
    }
    await route.fulfill({ json: [openNote] })
  })

  await page.goto('/ai?tab=chat&scope_kind=article&scope_id=article-a')
  await expect(page.getByRole('main').getByText('导出测试文章')).toBeVisible()
  await page.getByPlaceholder('输入你想讨论的问题，Ctrl/⌘ + Enter 发送...').fill('帮我看一下结尾。')
  await page.getByRole('button', { name: '发送' }).click()

  await expect(page.getByText('这是 AI 回复。')).toBeVisible()
  await page.getByRole('button', { name: '复制回复' }).click()
  await expect.poll(() => page.evaluate(() => window.__copiedText)).toBe('这是 AI 回复。')
  await expect(page.getByText('回复已复制')).toBeVisible()

  await page.getByRole('button', { name: '保存为文章便签' }).click()
  await expect.poll(() => noteBodies).toEqual(['这是 AI 回复。'])
  await expect(page.getByText('已保存为文章便签')).toBeVisible()
})

test('AI article chat keeps the draft message when sending fails', async ({ page }) => {
  await page.route('**/api/ai/chat', async (route) => {
    await route.fulfill({ status: 503, json: { detail: '后台服务暂时不可用' } })
  })

  await page.goto('/ai?tab=chat&scope_kind=article&scope_id=article-a')
  await expect(page.getByRole('main').getByText('导出测试文章')).toBeVisible()
  await page.getByPlaceholder('输入你想讨论的问题，Ctrl/⌘ + Enter 发送...').fill('这段问题不能因为失败而丢失。')
  await page.getByRole('button', { name: '发送' }).click()

  await expect(page.getByPlaceholder('输入你想讨论的问题，Ctrl/⌘ + Enter 发送...')).toHaveValue('这段问题不能因为失败而丢失。')
  await expect(page.getByText('后台服务暂时不可用')).toBeVisible()
})

test('AI chat standing instruction saves and back-to-article navigates to the scoped article', async ({ page }) => {
  const prompts: string[] = []

  await page.route('**/api/ai/chat-settings', async (route) => {
    if (route.request().method() === 'PUT') {
      const body = route.request().postDataJSON() as { system_prompt?: string }
      prompts.push(body.system_prompt ?? '')
      await route.fulfill({ json: { system_prompt: body.system_prompt ?? '' } })
      return
    }
    await route.fulfill({ json: { system_prompt: '' } })
  })

  await page.goto('/ai?tab=chat&scope_kind=article&scope_id=article-a')
  await page.getByPlaceholder('例如：回答要具体、克制，不要替作者做过度判断；可以提出修改建议，但不要直接覆盖原文。').fill('回答要具体、克制。')
  await page.getByRole('button', { name: '保存常驻指令' }).click()
  await expect.poll(() => prompts).toEqual(['回答要具体、克制。'])
  await expect(page.getByText('常驻指令已保存')).toBeVisible()

  await page.getByRole('button', { name: '返回文章' }).click()
  await expect(page).toHaveURL(/\/articles\?.*id=article-a/)
})

test('AI chat clears old article messages during scope switches so replies cannot save to the wrong note list', async ({ page }) => {
  let resolveArticleBThread: (() => void) | null = null

  await page.route('**/api/ai/threads**', async (route) => {
    const url = new URL(route.request().url())
    if (url.pathname !== '/api/ai/threads/current') {
      await route.fulfill({ json: [] })
      return
    }

    const scopeId = url.searchParams.get('scope_id')
    if (scopeId === articleB.id) {
      await new Promise<void>((resolve) => {
        resolveArticleBThread = resolve
      })
      await route.fulfill({ json: { thread: {
        id: 'thread-b',
        title: articleB.title,
        scope_kind: 'article',
        scope_id: articleB.id,
        created_at: null,
        updated_at: null,
      }, messages: [] } })
      return
    }

    await route.fulfill({ json: { thread: {
      id: 'thread-a',
      title: article.title,
      scope_kind: 'article',
      scope_id: article.id,
      created_at: null,
      updated_at: null,
    }, messages: [{
      id: 'message-old-assistant',
      thread_id: 'thread-a',
      role: 'assistant',
      content: 'A 文章的旧回复',
      timestamp: null,
    }] } })
  })

  await page.goto('/ai?tab=chat&scope_kind=article&scope_id=article-a')
  await expect(page.getByText('A 文章的旧回复')).toBeVisible()
  await expect(page.getByRole('button', { name: '保存为文章便签' })).toBeVisible()

  await page.getByRole('combobox').selectOption(articleB.id)
  await expect(page.getByText('A 文章的旧回复')).toHaveCount(0)
  await expect(page.getByRole('button', { name: '保存为文章便签' })).toHaveCount(0)

  resolveArticleBThread?.()
  await expect(page.getByText('还没有对话。你可以直接讨论当前文章。')).toBeVisible()
})
