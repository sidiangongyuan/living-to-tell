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

async function mockWriterApi(page: Page) {
  await page.route('**/api/articles?**', async (route) => {
    await route.fulfill({ json: articles })
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
    const article = articles.find((item) => item.id === id)
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
}

test.beforeEach(async ({ page }) => {
  await mockWriterApi(page)
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
