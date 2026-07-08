import { expect, test, type Page } from '@playwright/test'

declare global {
  interface Window {
    __copiedText?: string
  }
}

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

const sceneCard = {
  id: 'card-scene',
  title: '等待回应',
  content: '【场景原型】\n一方表达后等待回应。\n\n【核心冲突】\n主动表达和不确定回应之间的停顿。\n\n【参考原文（可选）】\n无',
  card_type: 'scene',
  tags: ['关系'],
  created_at: '2026-01-03T00:00:00Z',
  updated_at: '2026-01-03T00:00:00Z',
}

async function mockAiCardsApi(page: Page) {
  let cards = [userCard, characterCard, sceneCard]
  let lastAiCardJobProfile = 'default'
  let aiCardJob = {
    job_id: 'job-ai-card',
    kind: 'ai_card_draft',
    status: 'succeeded',
    stage: 'succeeded',
    stage_label: '已完成',
    concept: '场景卡草稿',
    motif_id: null as string | null,
    profile_id: 'default',
    started_at: '2026-01-05T00:00:00Z',
    updated_at: '2026-01-05T00:00:01Z',
    elapsed_ms: 800,
    error: '',
    provider: 'openai',
    model: 'gpt-test',
    transport: 'responses',
    result: {
      title: '赌注式情书',
      card_type: 'scene',
      content: '【场景原型】\n用带赌注的表达推动关系。\n\n【参考原文（可选）】\n无',
      tags: ['关系推进', '赌注'],
      provider: 'openai',
      model: 'gpt-test',
      transport: 'responses',
      elapsed_ms: 800,
    },
  }

  await page.addInitScript(() => {
    window.localStorage.clear()
    ;(window as Window & { __WRITER_API_BASE__?: string }).__WRITER_API_BASE__ = 'http://backend.test'
    ;(window as Window & { __WRITER_DISABLE_AUTO_UPDATE__?: boolean }).__WRITER_DISABLE_AUTO_UPDATE__ = true
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: async (text: string) => {
          window.__copiedText = text
        },
      },
    })
  })

  await page.route('**/api/app/version', async (route) => {
    await route.fulfill({
      json: {
        app_name: 'Living to Tell',
        version: '0.1.13',
        api_version: '2.0.0',
        capabilities: ['data_location', 'ai_chat_settings', 'ai_task_presets', 'ai_profiles', 'ai_jobs', 'ai_card_jobs', 'update_check'],
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
        download_url: 'https://github.com/sidiangongyuan/living-to-tell/releases/download/living-to-tell-v0.1.13/LivingToTell_0.1.13_x64-setup.exe',
        download_name: 'LivingToTell_0.1.13_x64-setup.exe',
      },
    })
  })

  await page.route('**/api/settings/ai/profiles', async (route) => {
    await route.fulfill({
      json: {
        profiles: [
          {
            id: 'profile-deepseek',
            name: 'DeepSeek Relay',
            provider_name: 'openai',
            base_url: 'https://elysiver.h-e.top/v1',
            wire_api: 'chat_completions',
            model: 'deepseek-v4-pro',
            api_key_source: 'env:LTT_AI_DEEPSEEK',
            gemini_cli_proxy: null,
            enabled: true,
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
          },
        ],
      },
    })
  })

  await page.route('**/api/ai/jobs**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())

    if (url.pathname === '/api/ai/jobs/ai-card-draft' && request.method() === 'POST') {
      const body = request.postDataJSON() as { profile_id?: string; card_id?: string | null }
      aiCardJob = {
        ...aiCardJob,
        job_id: `job-ai-card-${Date.now()}`,
        status: 'succeeded',
        stage: 'succeeded',
        stage_label: '已完成',
        motif_id: body.card_id ?? null,
        profile_id: body.profile_id || 'default',
      }
      lastAiCardJobProfile = body.profile_id || 'default'
      await route.fulfill({ json: aiCardJob })
      return
    }

    if (url.pathname.includes('/cancel') && request.method() === 'POST') {
      aiCardJob = {
        ...aiCardJob,
        status: 'cancelled',
        stage: 'cancelled',
        stage_label: '已中断',
        error: '已停止本地等待。若请求已经发给服务商，远端仍可能完成并计费。',
      }
      await route.fulfill({ json: aiCardJob })
      return
    }

    if (request.method() === 'GET') {
      await route.fulfill({ json: aiCardJob })
      return
    }

    await route.fallback()
  })

  await page.route('**/api/ai-cards**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())

    if (url.pathname === '/api/ai-cards/generate-draft') {
      await route.fulfill({
        json: {
          title: '赌注式情书',
          card_type: 'scene',
          content: '【场景原型】\n用带赌注的表达推动关系。\n\n【参考原文（可选）】\n无',
          tags: ['关系推进', '赌注'],
        },
      })
      return
    }

    if (url.pathname.endsWith('/upgrade-draft')) {
      await route.fulfill({
        json: {
          title: '升级后的风格',
          card_type: 'style',
          content: '【语言质感】\n具体、克制。\n\n【参考原文（可选）】\n无',
          tags: ['克制'],
        },
      })
      return
    }

    if (url.pathname === '/api/ai-cards/search') {
      const q = url.searchParams.get('q') || ''
      const cardType = url.searchParams.get('card_type')
      await route.fulfill({
        json: cards.filter((card) =>
          (!cardType || card.card_type === cardType)
          && (card.title.includes(q) || card.content.includes(q))
        ),
      })
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

  return {
    lastAiCardJobProfile: () => lastAiCardJobProfile,
    setAiCardJob: (next: typeof aiCardJob) => {
      aiCardJob = next
    },
    getAiCardJob: () => aiCardJob,
  }
}

async function expectInitialCardsVisible(page: Page) {
  const listPane = page.getByTestId('ai-cards-list-pane')
  await expect(listPane.getByText('克制风格')).toBeVisible({ timeout: 15000 })
  await expect(listPane.getByText('人物观察')).toBeVisible()
  return listPane
}

test.beforeEach(async ({ page }) => {
  await mockAiCardsApi(page)
})

test('AI Cards create, edit autosave, tags, filters, no sample restore, and delete actions work', async ({ page }) => {
  test.setTimeout(60_000)
  const createdBodies: Array<Record<string, unknown>> = []
  const updatedBodies: Array<Record<string, unknown>> = []
  let presetGenerateRequests = 0
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
    if (url.pathname === '/api/ai-cards/presets/generate') {
      presetGenerateRequests += 1
      await route.fulfill({ status: 404, json: { detail: 'removed' } })
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
  const listPane = await expectInitialCardsVisible(page)
  await expect(page.getByRole('button', { name: '恢复样例' })).toHaveCount(0)
  await expect(page.getByText('内置样例')).toHaveCount(0)
  expect(presetGenerateRequests).toBe(0)

  const paneBefore = await page.getByTestId('ai-cards-list-pane').boundingBox()
  const handleBox = await page.getByTestId('ai-cards-list-resizer').boundingBox()
  expect(paneBefore).not.toBeNull()
  expect(handleBox).not.toBeNull()
  if (paneBefore && handleBox) {
    await page.mouse.move(handleBox.x + handleBox.width / 2, handleBox.y + handleBox.height / 2)
    await page.mouse.down()
    await page.mouse.move(handleBox.x + handleBox.width / 2 + 48, handleBox.y + handleBox.height / 2)
    await page.mouse.up()
    await expect.poll(async () => {
      const next = await page.getByTestId('ai-cards-list-pane').boundingBox()
      return next?.width ?? 0
    }).toBeGreaterThan(paneBefore.width + 24)
  }

  await page.getByPlaceholder('搜索卡片...').fill('人物')
  await expect(listPane.getByText('人物观察')).toBeVisible()
  await expect(listPane.getByText('克制风格')).toHaveCount(0)
  await page.getByPlaceholder('搜索卡片...').fill('')

  await page.getByRole('button', { name: '人物卡', exact: true }).click()
  await expect(listPane.getByText('人物观察')).toBeVisible()
  await expect(listPane.getByText('克制风格')).toHaveCount(0)
  await page.getByRole('button', { name: '全部', exact: true }).click()

  await page.getByRole('button', { name: '+ 新建' }).click()
  await expect.poll(() => createdBodies.length).toBe(1)
  expect(createdBodies[0]).toEqual(expect.objectContaining({
    title: '未命名场景卡',
    content: expect.stringContaining('【场景原型】'),
    card_type: 'scene',
  }))

  const titleInput = page.getByPlaceholder('例如：海明威式简洁')
  await titleInput.click()
  await titleInput.press('Control+A')
  await titleInput.fill('新的风格卡')
  await expect(titleInput).toHaveValue('新的风格卡')
  await expect.poll(() => updatedBodies.some((body) => body.title === '新的风格卡')).toBe(true)
  await page.getByPlaceholder('按模板填写这张卡片的结构信息...').fill('句子短，动作清楚。')
  await expect.poll(() => updatedBodies.some((body) => body.content === '句子短，动作清楚。')).toBe(true)
  await expect(page.getByText('卡片已保存')).toBeVisible()

  const tagInput = page.getByPlaceholder('搜索或输入标签，回车添加')
  await tagInput.fill('节奏')
  await tagInput.press('Enter')
  await expect(page.getByText('节奏').first()).toBeVisible()
  await expect.poll(() => updatedBodies.some((body) =>
    Array.isArray(body.tags) && body.tags.includes('节奏')
  )).toBe(true)

  page.once('dialog', async (dialog) => dialog.dismiss())
  await page.getByRole('button', { name: '删除卡片' }).click()
  expect(deleted).toBe(0)

  await page.getByTestId('ai-card-list-item-card-created').click({ button: 'right' })
  await expect(page.getByTestId('context-menu')).toBeVisible()
  page.once('dialog', async (dialog) => dialog.accept())
  await page.getByTestId('context-menu').getByRole('button', { name: '删除卡片' }).click()
  await expect.poll(() => deleted).toBe(1)
})

test('AI Cards generate scene drafts and preview before saving', async ({ page }) => {
  const createdBodies: Array<Record<string, unknown>> = []

  await page.route('**/api/ai-cards', async (route) => {
    if (route.request().method() === 'POST') {
      createdBodies.push(route.request().postDataJSON() as Record<string, unknown>)
      await route.fallback()
      return
    }
    await route.fallback()
  })

  await page.goto('/ai-cards')
  await page.getByRole('button', { name: 'AI 创建' }).click()
  await page.getByPlaceholder('粘贴人物描写、风格样本、场景材料，或写下你希望这张卡记录的要点...').fill('主角写下一封带赌注的信，等待回应。')
  await page.getByRole('button', { name: '生成草稿' }).click()

  await expect(page.getByText('赌注式情书')).toBeVisible()
  await expect(page.getByText('用带赌注的表达推动关系。')).toBeVisible()
  await expect(page.getByText('关系推进')).toBeVisible()
  expect(createdBodies).toHaveLength(0)

  await page.getByRole('button', { name: '保存为新卡' }).click()
  await expect.poll(() => createdBodies.length).toBe(1)
  expect(createdBodies[0]).toEqual(expect.objectContaining({
    title: '赌注式情书',
    card_type: 'scene',
    content: expect.stringContaining('【场景原型】'),
    tags: expect.arrayContaining(['关系推进', '赌注']),
  }))
})

test('AI Cards generator uses the selected AI profile and keeps job status visible', async ({ page }) => {
  const jobRequests: Array<Record<string, unknown>> = []

  await page.route('**/api/ai/jobs/ai-card-draft', async (route) => {
    jobRequests.push(route.request().postDataJSON() as Record<string, unknown>)
    await route.fallback()
  })

  await page.goto('/ai-cards')
  await page.getByRole('button', { name: 'AI 创建' }).click()
  await page.getByLabel('AI 配置').selectOption('profile-deepseek')
  await page.getByPlaceholder('粘贴人物描写、风格样本、场景材料，或写下你希望这张卡记录的要点...').fill('主角写下一封带赌注的信，等待回应。')
  await page.getByRole('button', { name: '生成草稿' }).click()

  await expect.poll(() => jobRequests.length).toBe(1)
  expect(jobRequests[0]).toEqual(expect.objectContaining({
    profile_id: 'profile-deepseek',
    card_type: 'scene',
  }))
  await expect(page.getByTestId('ai-card-job-bar')).toBeVisible()
  await expect(page.getByText('AI 草稿已完成：场景卡草稿')).toBeVisible()
  await expect(page.getByText('赌注式情书')).toBeVisible()
})

test('AI Cards readable view exposes structured sections and prompt copy', async ({ page }) => {
  await page.goto('/ai-cards')
  await expectInitialCardsVisible(page)
  await expect(page.getByTestId('ai-card-read-view')).toBeVisible()
  await expect(page.getByRole('button', { name: '复制为提示词' }).first()).toBeVisible()
  await expect(page.getByTestId('ai-card-read-view').getByText('少用夸张表达。')).toBeVisible()

  await page.getByRole('button', { name: '复制为提示词' }).first().click()
  await expect.poll(() => page.evaluate(() => window.__copiedText || '')).toContain('【AI Card：克制风格】')
  await expect.poll(() => page.evaluate(() => window.__copiedText || '')).toContain('少用夸张表达。')

  await page.getByTestId('ai-card-list-item-card-scene').click()
  await expect(page.getByText('【场景原型】')).toBeVisible()
  await expect(page.getByTestId('ai-card-read-view').getByText('一方表达后等待回应。')).toBeVisible()
  await expect(page.getByText('【核心冲突】')).toBeVisible()
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
  await expectInitialCardsVisible(page)
  await page.getByRole('button', { name: '编辑卡片' }).first().click()
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
  await page.getByRole('button', { name: '编辑卡片' }).first().click()
  await page.getByPlaceholder('例如：海明威式简洁').fill('第一次失败')
  await expect(page.getByText('保存失败：卡片目录不可写')).toBeVisible()

  await page.getByPlaceholder('例如：海明威式简洁').fill('第二次成功')
  await expect(page.getByText('卡片已保存')).toBeVisible()
  await expect(page.getByText('卡片目录不可写')).toHaveCount(0)
})
