import { expect, test, type Page } from '@playwright/test'

declare global {
  interface Window {
    __copiedText?: string
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
        version: '0.1.7',
        api_version: '2.0.0',
        capabilities: ['data_location', 'ai_chat_settings', 'ai_task_presets'],
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

  await page.route('**/api/ai-cards**', async (route) => route.fulfill({ json: [{
    id: 'card-a',
    title: '克制风格',
    content: '少用夸张表达。',
    card_type: 'style',
    tags: [],
    created_at: null,
    updated_at: null,
  }] }))
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
  await page.getByRole('button', { name: '删除' }).last().click()
  expect(deleteRequests).toBe(0)

  page.once('dialog', async (dialog) => dialog.accept())
  await page.getByRole('button', { name: '删除' }).last().click()
  await expect.poll(() => deleteRequests).toBe(1)
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
  await page.getByRole('button', { name: /意象/ }).click()
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
  await expect(page.getByText('上下文已添加')).toBeVisible()
  await expect(page.getByText('文章便签 · 1 条')).toBeVisible()

  await page.getByRole('button', { name: '添加文脉标本' }).click()
  await page.getByRole('button', { name: /已有标本正文/ }).click()
  await page.getByRole('button', { name: /添加所选上下文/ }).click()
  await expect(page.getByText('测试书')).toBeVisible()

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
  await page.getByRole('button', { name: '清空上下文' }).click()
  await expect(page.getByText('克制风格')).toHaveCount(1)
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

test('AI result write-back buttons confirm and update the selected article', async ({ page }) => {
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

  const dismissDialog = page.waitForEvent('dialog')
  await page.getByRole('button', { name: '✏️ 替换原文' }).click()
  await (await dismissDialog).dismiss()
  expect(updates).toEqual([])

  await page.goto('/ai?tab=tools&scope_kind=article&scope_id=article-a')
  await page.getByRole('button', { name: '运行任务' }).click()
  await expect(page.getByText('AI 生成结果')).toBeVisible()

  const acceptDialog = page.waitForEvent('dialog')
  await page.getByRole('button', { name: '✏️ 替换原文' }).click()
  await (await acceptDialog).accept()
  await expect.poll(() => updates.length).toBe(1)
  expect(updates[0]).toEqual(expect.objectContaining({ body: 'AI 生成结果' }))
  await expect(page).toHaveURL(/\/articles\?.*id=article-a/)
  await expect(page).toHaveURL(/focus_start=/)

  await page.goto('/ai?tab=tools&scope_kind=article&scope_id=article-a')
  await page.getByRole('button', { name: '运行任务' }).click()
  await page.getByRole('button', { name: '插入到文末' }).click()
  await expect.poll(() => updates.length).toBe(2)
  expect(updates[1].body).toContain(article.body)
  expect(updates[1].body).toContain('AI 生成结果')
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
