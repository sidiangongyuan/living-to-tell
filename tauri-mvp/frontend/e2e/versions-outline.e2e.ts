import { expect, test, type Page } from '@playwright/test'

interface MockArticle {
  id: string
  title: string
  body: string
  entry_type: string
  created_at: string | null
  updated_at: string | null
  tags: string[]
  archived_at: string | null
  curation_status: string
}

interface MockVersion {
  id: string
  entry_id: string
  version_type: string
  content: string
  title_snapshot: string
  tags: string[]
  label: string
  reason: string
  word_count: number
  char_count: number
  created_at: string | null
  provider: string | null
  model: string | null
}

interface MockOutlineItem {
  id: string
  collection_id: string
  parent_id: string | null
  entry_id: string | null
  title: string
  item_type: 'part' | 'chapter' | 'scene' | 'note'
  status: 'idea' | 'drafting' | 'revising' | 'done' | 'parked'
  summary: string
  notes: string
  pov: string
  setting: string
  timeline: string
  tags: string[]
  target_word_count: number | null
  sort_order: number
  created_at: string | null
  updated_at: string | null
}

async function installBaseMocks(page: Page) {
  await page.addInitScript(() => {
    window.localStorage.clear()
    window.__WRITER_API_BASE__ = 'http://backend.test'
    ;(window as Window & { __WRITER_DISABLE_AUTO_UPDATE__?: boolean }).__WRITER_DISABLE_AUTO_UPDATE__ = true
    Object.defineProperty(window, '__TAURI_INTERNALS__', {
      value: {
        invoke: async (command: string) => {
          if (command === 'get_api_base_url') return 'http://backend.test'
          if (command === 'get_close_preference') return 'ask'
          if (command.startsWith('plugin:event|')) return 1
          return null
        },
        transformCallback: () => 1,
        unregisterCallback: () => undefined,
      },
      configurable: true,
    })
  })

  await page.route('**/api/app/version', async (route) => {
    await route.fulfill({
      json: {
        app_name: 'Living to Tell',
        version: '0.1.13',
        api_version: '2.0.0',
        capabilities: [
          'data_location',
          'ai_chat_settings',
          'ai_task_presets',
          'motif_star_map',
          'update_check',
          'article_versions',
          'collection_outline',
          'collection_manuscript_structure',
        ],
      },
    })
  })
  await page.route('**/api/app/update-check*', async (route) => {
    await route.fulfill({
      json: {
        current_version: '0.1.13',
        latest_version: '0.1.13',
        latest_tag: 'living-to-tell-v0.1.13',
        release_name: 'Living to Tell Preview 0.1.13',
        release_url: 'https://github.com/sidiangongyuan/living-to-tell/releases/tag/living-to-tell-v0.1.13',
        published_at: '2026-06-25T03:03:04Z',
        release_notes: '',
        source: 'github_releases_latest',
        status: 'up_to_date',
        message: '当前已是最新版本。',
        checked_at: '2026-06-25T03:05:06Z',
        cached: false,
        download_url: '',
        download_name: '',
      },
    })
  })
}

test('article version history saves and restores the real article body', async ({ page }) => {
  await installBaseMocks(page)
  page.on('dialog', async (dialog) => {
    await dialog.accept()
  })

  const article: MockArticle = {
    id: 'article-a',
    title: '版本文章',
    body: '第一段。\n\n第二段。',
    entry_type: 'fragment',
    created_at: null,
    updated_at: null,
    tags: ['历史'],
    archived_at: null,
    curation_status: 'unsorted',
  }
  const versions: MockVersion[] = []

  await page.route('**/api/articles?*', async (route) => {
    await route.fulfill({ json: [article] })
  })
  await page.route('**/api/articles/search?*', async (route) => {
    await route.fulfill({ json: [] })
  })
  await page.route('**/api/articles/article-a/versions', async (route) => {
    if (route.request().method() === 'POST') {
      const created: MockVersion = {
        id: `version-${versions.length + 1}`,
        entry_id: article.id,
        version_type: 'manual_checkpoint',
        content: article.body,
        title_snapshot: article.title,
        tags: [...article.tags],
        label: '手动保存',
        reason: 'manual',
        word_count: article.body.length,
        char_count: article.body.length,
        created_at: '2026-06-26T09:00:00Z',
        provider: null,
        model: null,
      }
      versions.unshift(created)
      await route.fulfill({ status: 201, json: created })
      return
    }
    await route.fulfill({ json: versions })
  })
  await page.route('**/api/articles/article-a/versions/*/restore', async (route) => {
    const versionId = new URL(route.request().url()).pathname.split('/').at(-2)
    const version = versions.find((item) => item.id === versionId)
    if (!version) {
      await route.fulfill({ status: 404, json: { detail: 'Version not found' } })
      return
    }
    const snapshot: MockVersion = {
      ...version,
      id: `snapshot-${versions.length + 1}`,
      version_type: 'manual_snapshot',
      content: article.body,
      label: '',
      reason: 'pre_restore',
    }
    versions.unshift(snapshot)
    article.body = version.content
    await route.fulfill({
      json: {
        entry: article,
        snapshot_version_id: snapshot.id,
        was_noop: false,
      },
    })
  })
  await page.route('**/api/articles/article-a', async (route) => {
    if (route.request().method() === 'PUT') {
      const body = route.request().postDataJSON() as Partial<MockArticle>
      article.title = body.title ?? article.title
      article.body = body.body ?? article.body
      article.tags = body.tags ?? article.tags
    }
    await route.fulfill({ json: article })
  })
  await page.route('**/api/articles/article-a/notes?*', async (route) => route.fulfill({ json: [] }))
  await page.route('**/api/collections/for-entry/article-a', async (route) => route.fulfill({ json: [] }))
  await page.route('**/api/collections', async (route) => route.fulfill({ json: [] }))
  await page.route('**/api/motifs/excerpts/source/article/article-a', async (route) => route.fulfill({ json: [] }))

  await page.goto('/articles?id=article-a')
  const editor = page.getByTestId('article-body-editor')
  await expect(editor).toHaveValue('第一段。\n\n第二段。', { timeout: 20000 })

  const panel = page.getByTestId('article-version-history')
  await panel.getByRole('button', { name: /历史版本/ }).click()
  await panel.getByRole('button', { name: '保存当前版本' }).click()
  await expect(panel.getByText('已保存当前版本。')).toBeVisible()

  await editor.fill('第一段改动。\n\n第二段。')
  await expect.poll(() => article.body).toBe('第一段改动。\n\n第二段。')
  await panel.getByRole('button', { name: '对比' }).click()
  await expect(page.getByText('版本对比')).toBeVisible()
  await page.getByRole('button', { name: '恢复正文' }).click()
  await expect(editor).toHaveValue('第一段。\n\n第二段。')
  expect(versions.some((version) => version.version_type === 'manual_snapshot')).toBe(true)
})

test('collection outline creates a real outline item and article link', async ({ page }) => {
  await installBaseMocks(page)
  const collection = {
    id: 'collection-a',
    title: '长篇项目',
    description: '一部长篇小说',
    project_type: 'novel',
    article_count: 0,
    created_at: null,
    updated_at: null,
  }
  const articles: MockArticle[] = []
  const outline: MockOutlineItem[] = []

  await page.route('**/api/collections', async (route) => {
    await route.fulfill({ json: [collection] })
  })
  await page.route('**/api/collections/collection-a', async (route) => {
    await route.fulfill({ json: { ...collection, article_count: articles.length } })
  })
  await page.route('**/api/collections/collection-a/articles', async (route) => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON() as { entry_ids: string[] }
      collection.article_count = body.entry_ids.length
    }
    await route.fulfill({
      status: route.request().method() === 'POST' ? 201 : 200,
      json: articles.map((article, index) => ({
        ...article,
        body_preview: article.body,
        word_count: article.body.length,
        char_count: article.body.length,
        sort_order: index,
      })),
    })
  })
  await page.route('**/api/collections/collection-a/outline', async (route) => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON() as Partial<MockOutlineItem>
      const item: MockOutlineItem = {
        id: `outline-${outline.length + 1}`,
        collection_id: collection.id,
        parent_id: null,
        entry_id: body.entry_id ?? null,
        title: body.title || '新场景',
        item_type: body.item_type ?? 'scene',
        status: body.status ?? 'idea',
        summary: body.summary ?? '',
        notes: body.notes ?? '',
        pov: body.pov ?? '',
        setting: body.setting ?? '',
        timeline: body.timeline ?? '',
        tags: body.tags ?? [],
        target_word_count: body.target_word_count ?? null,
        sort_order: outline.length,
        created_at: null,
        updated_at: null,
      }
      outline.push(item)
      await route.fulfill({ status: 201, json: item })
      return
    }
    await route.fulfill({ json: outline })
  })
  await page.route('**/api/collections/collection-a/outline/*', async (route) => {
    const parts = new URL(route.request().url()).pathname.split('/')
    const itemId = parts.at(-1)
    const item = outline.find((candidate) => candidate.id === itemId)
    if (!item) {
      await route.fulfill({ status: 404, json: { detail: 'Outline item not found' } })
      return
    }
    if (route.request().method() === 'PUT') {
      Object.assign(item, route.request().postDataJSON())
      await route.fulfill({ json: item })
      return
    }
    await route.fulfill({ status: 204 })
  })
  await page.route('**/api/articles?*', async (route) => {
    await route.fulfill({ json: articles })
  })
  await page.route('**/api/articles', async (route) => {
    const body = route.request().postDataJSON() as Partial<MockArticle>
    const article: MockArticle = {
      id: `article-${articles.length + 1}`,
      title: body.title || '无标题',
      body: body.body || '',
      tags: body.tags ?? [],
      entry_type: 'fragment',
      created_at: null,
      updated_at: null,
      archived_at: null,
      curation_status: 'unsorted',
    }
    articles.unshift(article)
    await route.fulfill({ status: 201, json: article })
  })

  await page.goto('/collections')
  await expect(page.getByRole('button', { name: '书稿' })).toBeVisible({ timeout: 20000 })
  const tourInvitation = page.getByTestId('tour-invitation')
  await expect(tourInvitation).toBeVisible()
  await tourInvitation.getByRole('button', { name: '开始教程' }).click()
  await expect(page.getByTestId('guided-tour-overlay')).toBeVisible()
  await expect(page.getByText('作品集是一本文稿项目')).toBeVisible()
  await page.getByRole('button', { name: '跳过' }).click()
  await expect(page.getByTestId('guided-tour-overlay')).toHaveCount(0)

  await page.getByRole('button', { name: '选择节点类型' }).click()
  await page.getByRole('button', { name: '+ 场景' }).click()
  await expect(page.getByTestId('collection-outline-detail')).toContainText('编辑详情')

  await page.getByLabel('标题').fill('雨夜来信')
  await page.getByLabel('摘要').fill('一封信推动关系升级。')
  await page.getByRole('button', { name: '保存' }).click()
  await expect.poll(() => outline[0]?.title).toBe('雨夜来信')

  await page.getByRole('button', { name: '从节点创建文章' }).click()
  await expect.poll(() => articles[0]?.title).toBe('雨夜来信')
  await expect.poll(() => outline[0]?.entry_id).toBe('article-1')
  await expect(page.getByTestId('collection-outline-detail').locator('p').filter({ hasText: '雨夜来信' })).toBeVisible()
})
