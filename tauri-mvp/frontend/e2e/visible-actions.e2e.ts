import { expect, test, type Page } from '@playwright/test'

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
  await page.route('**/api/dates/entries?**', async (route) => route.fulfill({ json: [article] }))
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
  await page.route('**/api/articles?**', async (route) => route.fulfill({ json: [article] }))
  await page.route('**/api/articles/search?**', async (route) => route.fulfill({ json: [] }))
  await page.route('**/api/articles/*/notes?**', async (route) => route.fulfill({ json: [] }))
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
    await route.fulfill({ json: article })
  })
  await page.route('**/api/articles', async (route) => {
    await route.fulfill({ status: 201, json: { ...article, id: 'article-created', title: '新文章' } })
  })

  await page.route('**/api/collections/for-entry/*', async (route) => route.fulfill({ json: [] }))
  await page.route('**/api/collections', async (route) => route.fulfill({ json: [] }))

  await page.route('**/api/library/stats', async (route) => {
    await route.fulfill({ json: { total: 0, by_usage_kind: {} } })
  })
  await page.route('**/api/library/references?**', async (route) => route.fulfill({ json: [] }))
  await page.route('**/api/library/references/search?**', async (route) => route.fulfill({ json: [] }))
  await page.route('**/api/library/references', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({ status: 201, json: reference })
      return
    }
    await route.fallback()
  })
  await page.route('**/api/library/references/*', async (route) => {
    await route.fulfill({ json: reference })
  })

  await page.route('**/api/ai-cards**', async (route) => route.fulfill({ json: [] }))
  await page.route('**/api/ai/task-presets', async (route) => route.fulfill({ json: {} }))
  await page.route('**/api/ai/chat-settings', async (route) => {
    await route.fulfill({ json: { system_prompt: '' } })
  })
  await page.route('**/api/ai/threads/current?**', async (route) => {
    await route.fulfill({ json: { thread: {
      id: 'thread-a',
      title: '导出测试文章',
      scope_kind: 'article',
      scope_id: article.id,
      created_at: null,
      updated_at: null,
    }, messages: [] } })
  })
  await page.route('**/api/ai/threads**', async (route) => route.fulfill({ json: [] }))
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
  await page.getByRole('button', { name: '删除' }).click()
  expect(deleteRequests).toBe(0)

  page.once('dialog', async (dialog) => dialog.accept())
  await page.getByRole('button', { name: '删除' }).click()
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
  await expect(page.getByText('开始使用活着为了讲述')).toBeVisible()
  await page.locator('body').click()
  await page.keyboard.down('Control')
  await page.keyboard.press('KeyK')
  await page.keyboard.up('Control')

  await expect(page.getByPlaceholder(/输入命令|Type a command/)).toBeVisible()
  await expect(page.getByText('新建文章')).toBeVisible()
  await expect(page.getByText('搜索文章')).toHaveCount(0)
  await expect(page.getByText('重新加载应用')).toHaveCount(0)
})
