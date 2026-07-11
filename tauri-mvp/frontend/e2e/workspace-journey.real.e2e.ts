import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

interface SampleProjectState {
  installed: boolean
  collection_id: string | null
  entry_ids: string[]
  reference_ids: string[]
  ai_card_ids: string[]
}

const apiBase = 'http://127.0.0.1:18080'

async function resetSampleProject(request: APIRequestContext): Promise<SampleProjectState> {
  await request.delete(`${apiBase}/api/onboarding/sample-project`)
  const response = await request.post(`${apiBase}/api/onboarding/sample-project`)
  expect(response.ok()).toBeTruthy()
  return await response.json()
}

async function prepareAuthorWorkspace(page: Page) {
  await page.addInitScript(() => {
    window.localStorage.setItem('language', 'zh')
    window.localStorage.setItem('living_to_tell_welcome_checklist_dismissed', 'true')
    window.localStorage.setItem('living_to_tell_collections_tour_dismissed', 'true')
    window.localStorage.setItem('right_context_pane_collapsed', 'false')
  })
  await page.setViewportSize({ width: 1440, height: 900 })
}

test.describe('real author workspace journey', () => {
  test('moves from an article into its collection and keeps references understandable', async ({ page, request, context }, testInfo) => {
    test.setTimeout(90_000)
    const sample = await resetSampleProject(request)
    expect(sample.collection_id).toBeTruthy()
    expect(sample.entry_ids).toHaveLength(2)
    expect(sample.reference_ids).toHaveLength(1)
    expect(sample.ai_card_ids).toHaveLength(1)

    await prepareAuthorWorkspace(page)
    await context.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: 'http://127.0.0.1:1421' })

    try {
      await page.goto(`/articles?id=${sample.entry_ids[0]}`)
      const editor = page.getByTestId('article-body-editor')
      await expect(editor).toBeVisible({ timeout: 20_000 })
      await expect(editor).toHaveValue(/雨落在旧邮局的玻璃上/)
      await expect(page.getByText('示例项目｜雨夜来信')).toBeVisible()
      await page.screenshot({ path: testInfo.outputPath('01-article-context.png'), fullPage: false })

      const collectionCard = page.getByText('示例项目｜雨夜来信').locator('..').locator('..')
      await collectionCard.getByRole('button', { name: '打开' }).click()
      await expect(page).toHaveURL(new RegExp(`/collections\\?id=${sample.collection_id}`))
      await expect(page.getByRole('heading', { name: '示例项目｜雨夜来信', exact: true })).toBeVisible()
      await expect(page.getByTestId('collection-outline-reader').getByRole('heading', { name: '雨夜来信', exact: true })).toBeVisible()
      await page.screenshot({ path: testInfo.outputPath('02-collection-structure.png'), fullPage: false })
      await page.setViewportSize({ width: 1024, height: 768 })
      await expect(page.getByTestId('collection-outline-reader')).toBeVisible()
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true)
      await page.screenshot({ path: testInfo.outputPath('02b-collection-min-window.png'), fullPage: false })
      await page.setViewportSize({ width: 1440, height: 900 })

      await page.getByRole('button', { name: '打开文章', exact: true }).click()
      await expect(page).toHaveURL(new RegExp(`/articles\\?id=${sample.entry_ids[0]}`))
      await page.goto(`/collections?id=${sample.collection_id}`)

      await page.getByRole('button', { name: '看板', exact: true }).click()
      await expect(page.getByTestId('collection-planning-board')).toBeVisible()
      await page.screenshot({ path: testInfo.outputPath('03-collection-board.png'), fullPage: false })

      await page.goto('/library')
      await expect(page.getByRole('heading', { name: '示例文脉｜雨与信', exact: true })).toBeVisible()
      await expect(page.getByPlaceholder('书名 / 篇名')).toHaveCount(0)
      await page.getByTestId('library-edit-reference').click()
      await expect(page.getByPlaceholder('书名 / 篇名')).toHaveValue('示例文脉｜雨与信')
      await page.getByTestId('library-edit-reference').click()
      await page.getByRole('button', { name: '复制完整引用', exact: true }).click()
      await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toContain('示例文脉｜雨与信')
      await page.screenshot({ path: testInfo.outputPath('04-reference-library.png'), fullPage: false })
      await page.setViewportSize({ width: 1024, height: 768 })
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true)
      await page.screenshot({ path: testInfo.outputPath('04b-reference-min-window.png'), fullPage: false })
      await page.setViewportSize({ width: 1440, height: 900 })

      await page.goto('/ai-cards')
      await expect(page.getByRole('heading', { name: '示例｜迟来的信件', exact: true })).toBeVisible()
      await page.getByRole('button', { name: '复制为提示词', exact: true }).click()
      await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toContain('示例｜迟来的信件')
      await page.screenshot({ path: testInfo.outputPath('05-ai-card-library.png'), fullPage: false })
    } finally {
      await page.goto('/dates')
      await page.waitForLoadState('networkidle')
      await page.waitForTimeout(500)
      await page.close()
      await new Promise((resolve) => setTimeout(resolve, 500))
      await request.delete(`${apiBase}/api/onboarding/sample-project`)
    }
  })
})
