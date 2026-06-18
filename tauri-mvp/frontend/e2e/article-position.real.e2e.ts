import { expect, test, type APIRequestContext } from '@playwright/test'

interface Article {
  id: string
  title: string
  body: string
  tags: string[]
}

const apiBase = 'http://127.0.0.1:18080'

function longBody(prefix: string, lines: number): string {
  return Array.from(
    { length: lines },
    (_, index) => `${prefix} 第 ${index + 1} 行：这是一段真实后端长文位置恢复测试文本，用来验证超过一页后的切换恢复。`
  ).join('\n')
}

async function createRealArticle(
  apiRequest: APIRequestContext,
  title: string,
  body: string
): Promise<Article> {
  const response = await apiRequest.post(`${apiBase}/api/articles`, {
    data: { title, body, tags: ['codex-position-test'] },
  })
  expect(response.ok()).toBeTruthy()
  return await response.json()
}

async function deleteRealArticle(
  apiRequest: APIRequestContext,
  articleId: string
) {
  const response = await apiRequest.delete(`${apiBase}/api/articles/${articleId}`)
  expect([204, 404]).toContain(response.status())
}

test.describe('article position restore against real backend', () => {
  test('restores real long article edit cursor and read scroll after switching articles', async ({ page, request }) => {
    const bodyA = longBody('真实文章 A', 180)
    const bodyB = longBody('真实文章 B', 120)
    const articleA = await createRealArticle(request, `位置恢复测试 A ${Date.now()}`, bodyA)
    const articleB = await createRealArticle(request, `位置恢复测试 B ${Date.now()}`, bodyB)

    try {
      await page.addInitScript(() => {
        window.localStorage.setItem('article_editor_position_debug_enabled', '1')
        window.localStorage.removeItem('article_editor_positions')
        window.localStorage.removeItem('last_selected_article_id')
        window.localStorage.removeItem('article_editor_position_debug')
      })

      await page.goto(`/articles?id=${articleA.id}`)
      const editor = page.getByTestId('article-body-editor')
      const scrollArea = page.getByTestId('article-editor-scroll')
      await expect(editor).toHaveValue(bodyA)

      const readScrollTop = await scrollArea.evaluate((container: HTMLDivElement) => {
        container.scrollTop = Math.min(900, container.scrollHeight - container.clientHeight)
        container.dispatchEvent(new Event('scroll', { bubbles: true }))
        return container.scrollTop
      })
      expect(readScrollTop).toBeGreaterThan(100)
      await page.waitForTimeout(250)

      await page.getByTestId(`article-entry-${articleB.id}`).click()
      await expect(editor).toHaveValue(bodyB)
      await page.getByTestId(`article-entry-${articleA.id}`).click()
      await expect(editor).toHaveValue(bodyA)
      await expect.poll(async () => scrollArea.evaluate((container: HTMLDivElement) => container.scrollTop)).toBeGreaterThan(100)
      await page.waitForTimeout(320)

      const cursorPosition = bodyA.indexOf('真实文章 A 第 120 行')
      expect(cursorPosition).toBeGreaterThan(0)
      await editor.evaluate((textarea: HTMLTextAreaElement, position) => {
        textarea.focus({ preventScroll: true })
        textarea.setSelectionRange(position, position)
        textarea.dispatchEvent(new Event('select', { bubbles: true }))
        textarea.dispatchEvent(new PointerEvent('pointerup', { bubbles: true }))
        textarea.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }))
      }, cursorPosition)
      const editScrollTop = await scrollArea.evaluate((container: HTMLDivElement) => {
        container.scrollTop = Math.min(1500, container.scrollHeight - container.clientHeight)
        container.dispatchEvent(new Event('scroll', { bubbles: true }))
        return container.scrollTop
      })
      expect(editScrollTop).toBeGreaterThan(100)
      await expect.poll(async () => page.evaluate((articleId) => {
        const raw = window.localStorage.getItem('article_editor_positions')
        const parsed = raw ? JSON.parse(raw) : {}
        return parsed[articleId]?.edit?.selectionStart ?? null
      }, articleA.id)).toBe(cursorPosition)

      await scrollArea.evaluate((container: HTMLDivElement) => {
        container.scrollTop = Math.min(2200, container.scrollHeight - container.clientHeight)
        container.dispatchEvent(new Event('scroll', { bubbles: true }))
      })
      await page.waitForTimeout(250)

      await page.getByTestId(`article-entry-${articleB.id}`).click()
      await expect(editor).toHaveValue(bodyB)
      await page.getByTestId(`article-entry-${articleA.id}`).click()
      await expect(editor).toHaveValue(bodyA)

      await expect.poll(async () => editor.evaluate((textarea: HTMLTextAreaElement) => textarea.selectionStart)).toBe(cursorPosition)
      await expect.poll(async () => scrollArea.evaluate((container: HTMLDivElement) => container.scrollTop)).toBeGreaterThan(100)

      const debugLog = await page.evaluate(() => JSON.parse(window.localStorage.getItem('article_editor_position_debug') || '[]'))
      expect(debugLog.some((item: { event: string }) => item.event === 'save-edit')).toBeTruthy()
      expect(debugLog.some((item: { event: string }) => item.event === 'restore-edit')).toBeTruthy()
    } finally {
      await deleteRealArticle(request, articleA.id)
      await deleteRealArticle(request, articleB.id)
    }
  })
})
