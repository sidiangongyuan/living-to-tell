import { expect, test, type Page } from '@playwright/test'

const userCard = {
  id: 'card-user',
  title: '克制风格',
  content: '少用夸张表达。',
  card_type: 'style',
  tags: [],
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-03T00:00:00Z',
}

const characterCard = {
  id: 'card-character',
  title: '人物观察',
  content: '记录角色的动作习惯。',
  card_type: 'character',
  tags: [],
  created_at: '2026-01-02T00:00:00Z',
  updated_at: '2026-01-02T00:00:00Z',
}

const presetCard = {
  id: 'card-preset',
  title: '加缪式冷峻',
  content: '短句，冷静，保持距离。',
  card_type: 'style',
  tags: [],
  created_at: '2026-01-04T00:00:00Z',
  updated_at: '2026-01-04T00:00:00Z',
}

async function mockAiCardsApi(page: Page) {
  let cards = [userCard, characterCard]

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

  await page.route('**/api/ai-cards**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())

    if (url.pathname === '/api/ai-cards/presets/list') {
      await route.fulfill({ json: [presetCard] })
      return
    }

    if (url.pathname === '/api/ai-cards/presets/generate') {
      if (request.method() === 'POST') {
        cards = [presetCard, ...cards.filter((card) => card.id !== presetCard.id)]
        await route.fulfill({ json: { created: 1, cards: [presetCard] } })
        return
      }
      await route.fallback()
      return
    }

    if (url.pathname === '/api/ai-cards') {
      if (request.method() === 'POST') {
        const body = request.postDataJSON() as Partial<typeof userCard>
        const created = {
          ...userCard,
          ...body,
          id: 'card-created',
          created_at: '2026-01-05T00:00:00Z',
          updated_at: '2026-01-05T00:00:00Z',
        }
        cards = [created, ...cards]
        await route.fulfill({ status: 201, json: created })
        return
      }
      await route.fulfill({ json: cards })
      return
    }

    const cardId = url.pathname.split('/').pop()
    const existing = cards.find((card) => card.id === cardId) ?? userCard
    if (request.method() === 'PUT') {
      const body = request.postDataJSON() as Partial<typeof userCard>
      const updated = { ...existing, ...body, updated_at: '2026-01-06T00:00:00Z' }
      cards = cards.map((card) => card.id === updated.id ? updated : card)
      await route.fulfill({ json: updated })
      return
    }
    if (request.method() === 'DELETE') {
      cards = cards.filter((card) => card.id !== cardId)
      await route.fulfill({ status: 204 })
      return
    }
    await route.fulfill({ json: existing })
  })
}

test.beforeEach(async ({ page }) => {
  await mockAiCardsApi(page)
})

test('AI Cards create, edit autosave, filter, generate samples, and delete actions work', async ({ page }) => {
  const createdBodies: Array<Record<string, unknown>> = []
  const updatedBodies: Array<Record<string, unknown>> = []
  let generated = 0
  let deleted = 0

  await page.route('**/api/ai-cards**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())

    if (url.pathname === '/api/ai-cards' && request.method() === 'POST') {
      const body = request.postDataJSON() as Record<string, unknown>
      createdBodies.push(body)
      await route.fallback()
      return
    }
    if (url.pathname === '/api/ai-cards/presets/generate' && request.method() === 'POST') {
      generated += 1
      await route.fallback()
      return
    }
    if (request.method() === 'PUT') {
      updatedBodies.push(request.postDataJSON() as Record<string, unknown>)
      await route.fallback()
      return
    }
    if (request.method() === 'DELETE') {
      deleted += 1
      await route.fallback()
      return
    }
    await route.fallback()
  })

  await page.goto('/ai-cards')
  await expect(page.getByText('克制风格')).toBeVisible()
  await expect(page.getByText('人物观察')).toBeVisible()

  await page.getByPlaceholder('搜索卡片...').fill('人物')
  await expect(page.getByText('人物观察')).toBeVisible()
  await expect(page.getByText('克制风格')).toHaveCount(0)
  await page.getByPlaceholder('搜索卡片...').fill('')

  await page.getByRole('button', { name: '角色卡' }).click()
  await expect(page.getByText('人物观察')).toBeVisible()
  await expect(page.getByText('克制风格')).toHaveCount(0)
  await page.getByRole('button', { name: '全部' }).click()

  await page.getByRole('button', { name: '+ 新建' }).click()
  await expect.poll(() => createdBodies.length).toBe(1)
  expect(createdBodies[0]).toEqual(expect.objectContaining({
    title: '未命名卡片',
    content: '',
    card_type: 'style',
  }))

  await page.getByPlaceholder('例如：海明威式简洁').fill('新的风格卡')
  await page.getByPlaceholder('描述风格特征、典型句式、适用场景...').fill('句子短，动作清楚。')
  await expect.poll(() => updatedBodies.length).toBeGreaterThanOrEqual(1)
  expect(updatedBodies.at(-1)).toEqual(expect.objectContaining({
    title: '新的风格卡',
    content: '句子短，动作清楚。',
  }))
  await expect(page.getByText('卡片已保存')).toBeVisible()

  page.once('dialog', async (dialog) => dialog.dismiss())
  await page.getByRole('button', { name: '恢复样例' }).click()
  expect(generated).toBe(0)

  page.once('dialog', async (dialog) => dialog.accept())
  await page.getByRole('button', { name: '恢复样例' }).click()
  await expect.poll(() => generated).toBe(1)
  await expect(page.getByText('成功生成 1 张预设风格卡！')).toBeVisible()
  await expect(page.getByText('加缪式冷峻')).toBeVisible()

  page.once('dialog', async (dialog) => dialog.dismiss())
  await page.getByRole('button', { name: '删除卡片' }).click()
  expect(deleted).toBe(0)

  page.once('dialog', async (dialog) => dialog.accept())
  await page.getByRole('button', { name: '删除卡片' }).click()
  await expect.poll(() => deleted).toBe(1)
})

test('AI Cards autosave failures show a visible unsaved-state error', async ({ page }) => {
  await page.route('**/api/ai-cards/card-user', async (route) => {
    if (route.request().method() === 'PUT') {
      await route.fulfill({ status: 500, json: { detail: '卡片目录不可写' } })
      return
    }
    await route.fallback()
  })

  await page.goto('/ai-cards')
  await expect(page.getByText('克制风格')).toBeVisible()
  await page.getByPlaceholder('例如：海明威式简洁').fill('保存失败的卡片')
  await expect(page.getByText('保存失败：卡片目录不可写')).toBeVisible()
})

test('AI Cards recover visibly after an autosave failure', async ({ page }) => {
  let attempts = 0

  await page.route('**/api/ai-cards/card-user', async (route) => {
    if (route.request().method() === 'PUT') {
      attempts += 1
      if (attempts === 1) {
        await route.fulfill({ status: 500, json: { detail: '卡片目录不可写' } })
        return
      }
      const body = route.request().postDataJSON() as Partial<typeof userCard>
      await route.fulfill({ json: { ...userCard, ...body } })
      return
    }
    await route.fallback()
  })

  await page.goto('/ai-cards')
  await page.getByPlaceholder('例如：海明威式简洁').fill('第一次失败')
  await expect(page.getByText('保存失败：卡片目录不可写')).toBeVisible()

  await page.getByPlaceholder('例如：海明威式简洁').fill('第二次成功')
  await expect(page.getByText('卡片已保存')).toBeVisible()
  await expect(page.getByText('卡片目录不可写')).toHaveCount(0)
})

test('AI Cards show a visible warning when preset metadata cannot load', async ({ page }) => {
  await page.route('**/api/ai-cards/presets/list', async (route) => {
    await route.fulfill({ status: 500, json: { detail: 'preset metadata unavailable' } })
  })

  await page.goto('/ai-cards')
  await expect(page.getByText('样例卡片来源信息暂时不可用，卡片仍可正常编辑和使用。')).toBeVisible()
  await expect(page.getByText('克制风格')).toBeVisible()
})
