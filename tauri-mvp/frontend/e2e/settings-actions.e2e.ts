import { expect, test, type Page } from '@playwright/test'

declare global {
  interface Window {
    __settingsInvokes?: Array<{ command: string; args?: Record<string, unknown> }>
  }
}

const baseAiSettings = {
  provider_name: 'openai',
  base_url: 'https://api.openai.com/v1',
  wire_api: 'responses',
  model: 'gpt-4o-mini',
  api_key_source: 'env:OPENAI_API_KEY',
  gemini_cli_proxy: null,
  status: {
    env: { available: false, path: null, reason: 'OPENAI_API_KEY is not configured' },
    codex: { available: true, path: 'C:\\Users\\Test\\.codex\\auth.json', reason: '' },
    gemini: { available: true, path: 'C:\\Users\\Test\\.gemini\\config.json', reason: '' },
    gemini_cli: {
      available: true,
      path: 'C:\\Users\\Test\\.gemini',
      reason: '',
      command: 'gemini',
      account: 'writer@example.com',
      proxy: null,
    },
  },
  model_presets: {
    openai: ['gpt-4o-mini', 'gpt-4.1'],
    gemini: ['gemini-2.5-flash', 'gemini-2.5-pro'],
    gemini_cli: ['gemini-cli-default'],
  },
}

const defaultDataLocation = {
  data_dir: 'C:\\Users\\Test\\AppData\\Roaming\\LivingToTell\\LivingToTell',
  default_data_dir: 'C:\\Users\\Test\\AppData\\Roaming\\LivingToTell\\LivingToTell',
  database_path: 'C:\\Users\\Test\\AppData\\Roaming\\LivingToTell\\LivingToTell\\living-to-tell.sqlite3',
  default_database_path: 'C:\\Users\\Test\\AppData\\Roaming\\LivingToTell\\LivingToTell\\living-to-tell.sqlite3',
  backup_dir: 'C:\\Users\\Test\\AppData\\Roaming\\LivingToTell\\LivingToTell\\backups',
  checkpoint_dir: 'C:\\Users\\Test\\AppData\\Roaming\\LivingToTell\\LivingToTell\\checkpoints',
  is_custom: false,
  database_exists: true,
  warning: null,
}

async function mockSettingsPage(page: Page, options: { customDataDir?: boolean; dataLocationCapability?: boolean } = {}) {
  const dataLocationCapability = options.dataLocationCapability ?? true
  const aiSettings = { ...baseAiSettings }
  const dataLocation = {
    ...defaultDataLocation,
    ...(options.customDataDir
      ? {
          data_dir: 'D:\\WritingData',
          database_path: 'D:\\WritingData\\living-to-tell.sqlite3',
          backup_dir: 'D:\\WritingData\\backups',
          checkpoint_dir: 'D:\\WritingData\\checkpoints',
          is_custom: true,
        }
      : {}),
  }
  const state = {
    aiSaves: [] as Array<Record<string, unknown>>,
    aiTests: [] as Array<Record<string, unknown>>,
    codexImports: 0,
    geminiImports: 0,
    migrations: [] as Array<Record<string, unknown>>,
  }

  await page.addInitScript(() => {
    window.localStorage.clear()
    window.__WRITER_API_BASE__ = 'http://backend.test'
    window.__settingsInvokes = []
    Object.defineProperty(window, '__TAURI_INTERNALS__', {
      value: {
        invoke: async (command: string, args?: Record<string, unknown>) => {
          window.__settingsInvokes?.push({ command, args })
          if (command === 'get_api_base_url') return 'http://backend.test'
          if (command === 'get_close_preference') return 'ask'
          if (command === 'set_close_preference') return args?.preference === 'tray' ? 'exit' : args?.preference
          if (command === 'get_data_directory_override') {
            return { override_path: null, active_path: null, warning: null }
          }
          if (command === 'choose_data_directory') return 'D:\\WritingData'
          if (command === 'open_path') return null
          if (command === 'set_data_directory_override') return { override_path: args?.path, active_path: args?.path, warning: null }
          if (command === 'clear_data_directory_override') return { override_path: null, active_path: null, warning: null }
          if (command === 'restart_app') return null
          if (command.startsWith('plugin:event|')) return 1
          return null
        },
        transformCallback: () => 1,
        unregisterCallback: () => undefined,
      },
      configurable: true,
    })
  })

  await page.route('http://backend.test/api/app/version', async (route) => {
    await route.fulfill({
      json: {
        app_name: 'Living to Tell',
        version: '0.1.7',
        api_version: '2.0.0',
        capabilities: dataLocationCapability
          ? ['data_location', 'ai_chat_settings', 'ai_task_presets']
          : ['ai_chat_settings', 'ai_task_presets'],
      },
    })
  })

  await page.route('http://backend.test/api/settings/ai', async (route) => {
    const request = route.request()
    if (request.method() === 'PUT') {
      const body = request.postDataJSON() as Record<string, unknown>
      state.aiSaves.push(body)
      Object.assign(aiSettings, body)
      await route.fulfill({ json: aiSettings })
      return
    }
    await route.fulfill({ json: aiSettings })
  })

  await page.route('http://backend.test/api/settings/ai/test', async (route) => {
    state.aiTests.push(route.request().postDataJSON() as Record<string, unknown>)
    await route.fulfill({ json: { ok: true, message: 'ok' } })
  })

  await page.route('http://backend.test/api/settings/ai/import-codex', async (route) => {
    state.codexImports += 1
    await route.fulfill({
      json: {
        config: { ...aiSettings, api_key_source: 'codex' },
        imported: { source: 'codex' },
      },
    })
  })

  await page.route('http://backend.test/api/settings/ai/import-gemini', async (route) => {
    state.geminiImports += 1
    await route.fulfill({
      json: {
        config: {
          ...aiSettings,
          provider_name: 'gemini',
          model: 'gemini-2.5-flash',
          api_key_source: 'gemini',
          base_url: 'https://generativelanguage.googleapis.com',
        },
        imported: { source: 'gemini' },
      },
    })
  })

  await page.route('http://backend.test/api/settings/data-location', async (route) => {
    await route.fulfill({ json: dataLocation })
  })

  await page.route('http://backend.test/api/settings/data-location/migrate', async (route) => {
    const body = route.request().postDataJSON() as Record<string, unknown>
    state.migrations.push(body)
    await route.fulfill({
      json: {
        target_dir: body.target_dir,
        target_database_path: `${body.target_dir}\\living-to-tell.sqlite3`,
        restart_required: true,
        message: 'migrated',
      },
    })
  })

  return state
}

test('settings AI buttons import, test, save, and reset with visible feedback', async ({ page }) => {
  const state = await mockSettingsPage(page)

  await page.goto('/settings')
  await expect(page.getByText('AI 配置')).toBeVisible()

  await page.getByRole('button', { name: '导入 Codex 配置' }).click()
  await expect.poll(() => state.codexImports).toBe(1)
  await expect(page.getByText('已导入 Codex 配置')).toBeVisible()

  await page.locator('section').filter({ hasText: 'AI 配置' }).locator('select').first().selectOption('gemini')
  await page.getByRole('button', { name: '导入 Gemini 配置' }).click()
  await expect.poll(() => state.geminiImports).toBe(1)
  await expect(page.getByText('已导入 Gemini 配置')).toBeVisible()

  await page.getByRole('button', { name: '检查配置' }).click()
  await expect.poll(() => state.aiTests.length).toBe(1)
  expect(state.aiTests[0]).toEqual(expect.objectContaining({
    provider_name: 'gemini',
    model: 'gemini-2.5-flash',
    api_key_source: 'gemini',
  }))
  await expect(page.getByText(/本地配置检查通过/)).toBeVisible()

  await page.locator('section').filter({ hasText: '界面设置' }).locator('select').nth(1).selectOption('tray')
  await page.getByRole('button', { name: '保存设置' }).click()
  await expect.poll(() => state.aiSaves.length).toBe(1)
  await expect(page.getByText('设置已保存')).toBeVisible()
  await expect(page.getByText('当前环境无法使用系统托盘')).toBeVisible()

  await page.getByRole('button', { name: '重新显示' }).click()
  await expect(page.getByText('欢迎清单会在日期页重新显示。')).toBeVisible()
})

test('settings data storage buttons call native commands and protect migration with confirmation', async ({ page }) => {
  const state = await mockSettingsPage(page, { customDataDir: true })

  await page.goto('/settings')
  await expect(page.getByText('数据与存储')).toBeVisible()

  await page.getByRole('button', { name: '打开数据目录' }).click()
  await expect(page.getByText('已打开数据目录。')).toBeVisible()
  await expect.poll(() => page.evaluate(() => window.__settingsInvokes?.filter((item) => item.command === 'open_path').map((item) => item.args?.path))).toContain('D:\\WritingData')

  await page.getByRole('button', { name: '打开备份目录' }).click()
  await expect(page.getByText('已打开备份目录。')).toBeVisible()
  await expect.poll(() => page.evaluate(() => window.__settingsInvokes?.filter((item) => item.command === 'open_path').map((item) => item.args?.path))).toContain('D:\\WritingData\\backups')

  await page.getByRole('button', { name: '选择新位置' }).click()
  await expect(page.getByText('已选择新数据目录。确认无误后可以执行迁移。')).toBeVisible()
  await expect(page.getByPlaceholder(defaultDataLocation.default_data_dir)).toHaveValue('D:\\WritingData')

  page.once('dialog', async (dialog) => dialog.dismiss())
  await page.getByRole('button', { name: '迁移并切换' }).click()
  expect(state.migrations).toEqual([])

  page.once('dialog', async (dialog) => dialog.accept())
  await page.getByRole('button', { name: '迁移并切换' }).click()
  await expect.poll(() => state.migrations).toEqual([
    { target_dir: 'D:\\WritingData' },
  ])
  await expect(page.getByText('数据已复制到新位置，应用将自动重启。')).toBeVisible()
  await expect.poll(() => page.evaluate(() => window.__settingsInvokes?.some((item) => item.command === 'set_data_directory_override'))).toBe(true)
  await expect.poll(() => page.evaluate(() => window.__settingsInvokes?.some((item) => item.command === 'restart_app'))).toBe(true)

  page.once('dialog', async (dialog) => dialog.accept())
  await page.getByRole('button', { name: '恢复默认位置' }).click()
  await expect.poll(() => state.migrations.at(-1)).toEqual({
    target_dir: defaultDataLocation.default_data_dir,
    replace_existing: true,
  })
  await expect(page.getByText('数据已复制回默认位置，应用将自动重启。')).toBeVisible()
  await expect.poll(() => page.evaluate(() => window.__settingsInvokes?.some((item) => item.command === 'clear_data_directory_override'))).toBe(true)
})

test('settings data storage degrades cleanly when backend capability is missing', async ({ page }) => {
  await mockSettingsPage(page, { dataLocationCapability: false })

  await page.goto('/settings')
  await expect(page.getByText('后台服务版本过旧或安装不完整')).toBeVisible()
  await expect(page.getByText('当前后台服务不支持数据目录管理。请退出应用后重新安装最新版本；你的写作数据不会被删除。')).toBeVisible()

  await page.getByRole('button', { name: '重启应用' }).click()
  await expect(page.getByText('正在重启应用...')).toBeVisible()
  await expect.poll(() => page.evaluate(() => window.__settingsInvokes?.some((item) => item.command === 'restart_app'))).toBe(true)
})
