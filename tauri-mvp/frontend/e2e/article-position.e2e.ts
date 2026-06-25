import { expect, test, type Page } from '@playwright/test'

const longBodyA = Array.from({ length: 120 }, (_, index) => `文章 A 第 ${index + 1} 行：这里是一段用于测试滚动恢复的长文本。`).join('\n')
const longBodyB = Array.from({ length: 80 }, (_, index) => `文章 B 第 ${index + 1} 行：切换回来后不应该影响文章 A 的位置。`).join('\n')

const articles = [
  {
    id: 'article-a',
    title: '文章 A',
    body: longBodyA,
    entry_type: 'fragment',
    created_at: null,
    updated_at: null,
    tags: [],
    archived_at: null,
    curation_status: 'active',
  },
  {
    id: 'article-b',
    title: '文章 B',
    body: longBodyB,
    entry_type: 'fragment',
    created_at: null,
    updated_at: null,
    tags: [],
    archived_at: null,
    curation_status: 'active',
  },
]

type MockArticle = typeof articles[number]
type MockedPage = Page & { __writerArticles?: MockArticle[] }

async function mockWriterApi(page: MockedPage) {
  const pageArticles = articles.map((article) => ({ ...article, tags: [...article.tags] }))
  page.__writerArticles = pageArticles
  await page.addInitScript(() => {
    ;(window as Window & { __WRITER_DISABLE_AUTO_UPDATE__?: boolean }).__WRITER_DISABLE_AUTO_UPDATE__ = true
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
  await page.route('**/api/articles?**', async (route) => {
    await route.fulfill({ json: pageArticles })
  })
  await page.route('**/api/articles/search?**', async (route) => {
    await route.fulfill({ json: [] })
  })
  await page.route('**/api/articles/*/notes?**', async (route) => {
    await route.fulfill({ json: [] })
  })
  await page.route('**/api/articles/*', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const id = url.pathname.split('/').pop()
    const article = pageArticles.find((item) => item.id === id)
    if (request.method() === 'PUT' && article) {
      const body = request.postDataJSON() as { title?: string; body?: string; tags?: string[] }
      Object.assign(article, {
        title: body.title ?? article.title,
        body: body.body ?? article.body,
        tags: body.tags ?? article.tags,
      })
      await route.fulfill({ json: article })
      return
    }
    await route.fulfill(article ? { json: article } : { status: 404, json: { detail: 'not found' } })
  })
  await page.route('**/api/collections/for-entry/*', async (route) => {
    await route.fulfill({ json: [] })
  })
  await page.route('**/api/collections', async (route) => {
    await route.fulfill({ json: [] })
  })
  await page.route('**/api/motifs/excerpts/source/article/*', async (route) => {
    await route.fulfill({ json: [] })
  })
}

async function expectArticleBody(page: Page, body: string) {
  await expect(page.getByTestId('article-body-editor')).toHaveValue(body, { timeout: 20000 })
}

test.beforeEach(async ({ page }) => {
  await mockWriterApi(page as MockedPage)
})

test('keeps epigraph editor open while typing and autosaving', async ({ page }) => {
  await page.goto('/articles?id=article-a')
  await expectArticleBody(page, longBodyA)

  await page.getByTestId('article-add-epigraph').click()
  const quote = page.getByTestId('article-epigraph-quote')
  await expect(quote).toBeVisible()

  await quote.fill('这是一段还没有填写出处的题记')
  await expect(quote).toBeVisible()
  await expect(quote).toHaveValue('这是一段还没有填写出处的题记')

  await page.waitForTimeout(850)
  await expect(quote).toBeVisible()
  await expect(quote).toHaveValue('这是一段还没有填写出处的题记')
})

test('keeps an incomplete epigraph draft when switching articles', async ({ page }) => {
  await page.goto('/articles?id=article-a')
  await page.getByTestId('article-add-epigraph').click()
  const quote = page.getByTestId('article-epigraph-quote')
  await quote.fill('这是一段还没写出处的题记草稿')

  await page.getByTestId('article-entry-article-b').click()
  await expect(page.getByTestId('article-body-editor')).toHaveValue(longBodyB)

  await page.getByTestId('article-entry-article-a').click()
  await expect(quote).toBeVisible()
  await expect(quote).toHaveValue('这是一段还没写出处的题记草稿')
  await expect(page.getByTestId('article-body-editor')).toHaveValue(longBodyA)
})

test('moves an epigraph back into the article body and saves it', async ({ page }) => {
  const mockedPage = page as MockedPage
  await page.goto('/articles?id=article-a')
  await expectArticleBody(page, longBodyA)

  await page.getByTestId('article-add-epigraph').click()
  await page.getByTestId('article-epigraph-quote').fill('题记会回到正文')
  await page.getByTestId('article-epigraph-attribution').fill('《测试书》 作者')
  await page.getByRole('button', { name: '转回正文' }).click()

  const expectedBody = `题记会回到正文\n——《测试书》 作者\n\n${longBodyA}`
  await expect(page.getByTestId('article-epigraph-quote')).toHaveCount(0)
  await expect(page.getByTestId('article-body-editor')).toHaveValue(expectedBody)
  await expect.poll(() => mockedPage.__writerArticles?.find((article) => article.id === 'article-a')?.body).toBe(expectedBody)
})

test('flushes pending article edits before switching articles', async ({ page }) => {
  const mockedPage = page as MockedPage
  await page.goto('/articles?id=article-a')
  const editor = page.getByTestId('article-body-editor')
  await expectArticleBody(page, longBodyA)

  const changedBody = `${longBodyA}\n快速切换前新增的一句。`
  await editor.fill(changedBody)
  await page.getByTestId('article-entry-article-b').click()
  await expect(editor).toHaveValue(longBodyB)

  expect(mockedPage.__writerArticles?.find((article) => article.id === 'article-a')?.body).toBe(changedBody)
})

test('ignores stale side-panel not found responses after switching articles', async ({ page }) => {
  await page.unroute('**/api/articles/*/notes?**')
  await page.unroute('**/api/collections/for-entry/*')
  await page.unroute('**/api/motifs/excerpts/source/article/*')

  const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))
  const noteForB = {
    id: 'note-b',
    entry_id: 'article-b',
    body: 'B 的便签',
    status: 'open',
    pinned: false,
    sort_order: 0,
    created_at: null,
    updated_at: null,
    completed_at: null,
  }

  await page.route('**/api/articles/*/notes?**', async (route) => {
    const parts = new URL(route.request().url()).pathname.split('/')
    const articleId = parts.at(-2)
    if (articleId === 'article-a') {
      await delay(450)
      await route.fulfill({ status: 404, json: { detail: 'Article not found' } })
      return
    }
    await route.fulfill({ json: articleId === 'article-b' ? [noteForB] : [] })
  })
  await page.route('**/api/collections/for-entry/*', async (route) => {
    const articleId = new URL(route.request().url()).pathname.split('/').pop()
    if (articleId === 'article-a') {
      await delay(420)
      await route.fulfill({ status: 404, json: { detail: 'Article not found' } })
      return
    }
    await route.fulfill({ json: [] })
  })
  await page.route('**/api/motifs/excerpts/source/article/*', async (route) => {
    const articleId = new URL(route.request().url()).pathname.split('/').pop()
    if (articleId === 'article-a') {
      await delay(400)
      await route.fulfill({ status: 404, json: { detail: 'Source not found' } })
      return
    }
    await route.fulfill({ json: [] })
  })

  await page.goto('/articles?id=article-a')
  await page.getByTestId('article-entry-article-b').click()
  await expect(page.getByTestId('article-body-editor')).toHaveValue(longBodyB)
  await expect(page.getByText('B 的便签')).toBeVisible()

  await page.waitForTimeout(700)
  await expect(page.getByText('Article not found')).toHaveCount(0)
  await expect(page.getByText('Source not found')).toHaveCount(0)
  await expect(page.getByText('这篇文章已不存在，已刷新文章列表。')).toHaveCount(0)
  await expect(page.getByText('B 的便签')).toBeVisible()
})

test('restores editor scroll position after switching articles', async ({ page }) => {
  await page.goto('/articles?id=article-a')
  const editor = page.getByTestId('article-body-editor')
  const scrollArea = page.getByTestId('article-editor-scroll')
  await expect(editor).toHaveValue(longBodyA)
  await page.waitForTimeout(520)

  const savedScrollTop = await scrollArea.evaluate((container: HTMLDivElement) => {
    container.scrollTop = Math.min(900, container.scrollHeight - container.clientHeight)
    container.dispatchEvent(new Event('scroll', { bubbles: true }))
    return container.scrollTop
  })
  expect(savedScrollTop).toBeGreaterThan(100)

  await page.waitForTimeout(180)
  await page.getByTestId('article-entry-article-b').click()
  await expect(editor).toHaveValue(longBodyB)

  await page.getByTestId('article-entry-article-a').click()
  await expect(editor).toHaveValue(longBodyA)
  await expect.poll(async () => scrollArea.evaluate((container: HTMLDivElement) => container.scrollTop)).toBeGreaterThan(100)
})

test('prefers a newer read position over a stale top edit position', async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('article_editor_positions', JSON.stringify({
      'article-a': {
        edit: { selectionStart: 0, selectionEnd: 0, scrollTop: 0, updatedAt: 1000 },
        updatedAt: 1000,
      },
    }))
  })

  await page.goto('/articles?id=article-a')
  const editor = page.getByTestId('article-body-editor')
  const scrollArea = page.getByTestId('article-editor-scroll')
  await expect(editor).toHaveValue(longBodyA)
  await page.waitForTimeout(520)

  const savedScrollTop = await scrollArea.evaluate((container: HTMLDivElement) => {
    container.scrollTop = Math.min(1400, container.scrollHeight - container.clientHeight)
    container.dispatchEvent(new Event('scroll', { bubbles: true }))
    return container.scrollTop
  })
  expect(savedScrollTop).toBeGreaterThan(100)
  await page.waitForTimeout(180)

  await page.getByTestId('article-entry-article-b').click()
  await expect(editor).toHaveValue(longBodyB)

  await page.getByTestId('article-entry-article-a').click()
  await expect(editor).toHaveValue(longBodyA)
  await expect.poll(async () => scrollArea.evaluate((container: HTMLDivElement) => container.scrollTop)).toBeGreaterThan(100)
})

test('restores edit cursor position even after scrolling', async ({ page }) => {
  await page.goto('/articles?id=article-a')
  const editor = page.getByTestId('article-body-editor')
  const scrollArea = page.getByTestId('article-editor-scroll')
  await expect(editor).toHaveValue(longBodyA)

  const cursorPosition = longBodyA.indexOf('文章 A 第 60 行')
  await editor.evaluate((textarea: HTMLTextAreaElement, position) => {
    textarea.focus()
    textarea.setSelectionRange(position, position)
    textarea.dispatchEvent(new Event('select', { bubbles: true }))
  }, cursorPosition)
  const editScrollTop = await scrollArea.evaluate((container: HTMLDivElement) => {
    container.scrollTop = Math.min(700, container.scrollHeight - container.clientHeight)
    container.dispatchEvent(new Event('scroll', { bubbles: true }))
    return container.scrollTop
  })
  expect(editScrollTop).toBeGreaterThan(100)
  await page.waitForTimeout(180)

  await scrollArea.evaluate((container: HTMLDivElement) => {
    container.scrollTop = Math.min(1100, container.scrollHeight - container.clientHeight)
    container.dispatchEvent(new Event('scroll', { bubbles: true }))
  })
  await page.waitForTimeout(180)

  await page.getByTestId('article-entry-article-b').click()
  await expect(editor).toHaveValue(longBodyB)

  await page.getByTestId('article-entry-article-a').click()
  await expect(editor).toHaveValue(longBodyA)
  await expect.poll(async () => editor.evaluate((textarea: HTMLTextAreaElement) => textarea.selectionStart)).toBe(cursorPosition)
  await expect.poll(async () => scrollArea.evaluate((container: HTMLDivElement) => container.scrollTop)).toBeGreaterThan(100)
})

test('uses last selected article when the route has no article id', async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('last_selected_article_id', 'article-b')
  })

  await page.goto('/articles')
  await expect(page.getByTestId('article-body-editor')).toHaveValue(longBodyB)
  await expect(page).toHaveURL(/\/articles\?id=article-b/)
})
