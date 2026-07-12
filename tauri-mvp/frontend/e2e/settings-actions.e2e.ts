import { expect, test, type Page } from '@playwright/test'

declare global {
  interface Window {
    __settingsInvokes?: Array<{ command: string; args?: Record<string, unknown> }>
    __openedUrls?: string[]
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
    opencode: {
      available: true,
      path: 'C:\\Users\\Test\\.local\\share\\opencode\\auth.json',
      reason: '',
      command: 'opencode',
      account: null,
      proxy: null,
    },
  },
  model_presets: {
    openai: ['gpt-4o-mini', 'gpt-4.1'],
    gemini: ['gemini-2.5-flash', 'gemini-2.5-pro'],
    gemini_cli: ['gemini-cli-default'],
    opencode: ['opencode/deepseek-v4-flash-free'],
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

async function mockSettingsPage(
  page: Page,
  options: {
    customDataDir?: boolean
    dataLocationCapability?: boolean
    updateAvailable?: boolean
    staleInitialProfileListDelayMs?: number
  } = {},
) {
  const dataLocationCapability = options.dataLocationCapability ?? true
  const updateAvailable = options.updateAvailable ?? false
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
    aiProfiles: [] as Array<Record<string, unknown>>,
    defaultProfileId: null as string | null,
    discoveredProfiles: [
      {
        name: 'OpenCode · DeepSeek v4 Flash Free',
        provider_name: 'opencode',
        base_url: null,
        wire_api: 'responses',
        model: 'opencode/deepseek-v4-flash-free',
        api_key_source: 'opencode',
        gemini_cli_proxy: null,
        enabled: true,
        source_key: 'local:opencode',
        source_label: 'OpenCode 本机登录',
        available: true,
        reason: '',
        existing_profile_id: null,
        live_test_supported: true,
      },
      {
        name: 'Codex / OpenAI · gpt-5.4',
        provider_name: 'openai',
        base_url: 'https://api.example.test/v1',
        wire_api: 'responses',
        model: 'gpt-5.4',
        api_key_source: 'codex',
        gemini_cli_proxy: null,
        enabled: true,
        source_key: 'local:codex',
        source_label: 'Codex 本机配置',
        available: true,
        reason: '',
        existing_profile_id: null,
        live_test_supported: true,
      },
    ] as Array<Record<string, unknown>>,
    localProfileImports: [] as Array<Record<string, unknown>>,
    localProfileDiscoveries: 0,
    profileListGets: 0,
    profileListResponses: 0,
    aiTests: [] as Array<Record<string, unknown>>,
    aiLiveTests: [] as Array<Record<string, unknown>>,
    codexImports: 0,
    geminiImports: 0,
    modelFetches: [] as Array<string>,
    migrations: [] as Array<Record<string, unknown>>,
    updateChecks: 0,
    updateDownloads: [] as Array<Record<string, unknown>>,
  }

  await page.addInitScript(() => {
    window.localStorage.clear()
    window.__WRITER_API_BASE__ = 'http://backend.test'
    ;(window as Window & { __WRITER_DISABLE_AUTO_UPDATE__?: boolean }).__WRITER_DISABLE_AUTO_UPDATE__ = true
    window.__settingsInvokes = []
    window.__openedUrls = []
    window.open = ((url?: string | URL | undefined) => {
      if (url) window.__openedUrls?.push(String(url))
      return null
    }) as Window['open']
    Object.defineProperty(window, '__TAURI_INTERNALS__', {
      value: {
        invoke: async (command: string, args?: Record<string, unknown>) => {
          window.__settingsInvokes?.push({ command, args })
          if (command === 'get_api_base_url') return 'http://backend.test'
          if (command === 'get_close_preference') return 'ask'
          if (command === 'set_close_preference') return args?.preference === 'tray' ? 'exit' : args?.preference
          if (command === 'open_external_url') {
            if (typeof args?.url === 'string') window.__openedUrls?.push(args.url)
            return null
          }
          if (command === 'install_update_and_exit') return null
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
        version: '0.1.13',
        api_version: '2.0.0',
        capabilities: dataLocationCapability
          ? ['data_location', 'ai_chat_settings', 'ai_task_presets', 'ai_profiles', 'ai_task_compare', 'update_check']
          : ['ai_chat_settings', 'ai_task_presets', 'ai_profiles', 'ai_task_compare', 'update_check'],
      },
    })
  })

  await page.route('http://backend.test/api/app/update-check*', async (route) => {
    state.updateChecks += 1
    await route.fulfill({
      json: updateAvailable
        ? {
            current_version: '0.1.13',
            latest_version: '0.1.14',
            latest_tag: 'living-to-tell-v0.1.14',
            release_name: 'Living to Tell Preview 0.1.14',
            release_url: 'https://github.com/sidiangongyuan/living-to-tell/releases/tag/living-to-tell-v0.1.14',
            published_at: '2026-06-26T01:02:03Z',
            release_notes: '## 0.1.14\n\nAdded update notifications.',
            source: 'github_releases_latest',
            status: 'update_available',
            message: '发现新版本。可以在应用内下载安装包并启动安装。',
            checked_at: '2026-06-26T01:05:06Z',
            cached: false,
            download_url: 'https://github.com/sidiangongyuan/living-to-tell/releases/download/living-to-tell-v0.1.14/LivingToTell_0.1.14_x64-setup.exe',
            download_name: 'LivingToTell_0.1.14_x64-setup.exe',
            download_sha256: 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
            network_proxy: 'https=127.0.0.1:7890',
            network_detail: null,
          }
        : {
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
            download_sha256: null,
            network_proxy: null,
            network_detail: null,
          },
    })
  })

  await page.route('http://backend.test/api/app/update-download', async (route) => {
    const body = route.request().postDataJSON() as Record<string, unknown>
    state.updateDownloads.push(body)
    await route.fulfill({
      json: {
        status: 'downloaded',
        message: '安装包已下载，准备启动安装器。',
        file_path: 'C:\\Temp\\LivingToTell_0.1.14_x64-setup.exe',
        file_name: 'LivingToTell_0.1.14_x64-setup.exe',
        size_bytes: 123456,
        sha256: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
        downloaded_at: '2026-06-26T01:06:06Z',
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

  await page.route('http://backend.test/api/settings/ai/profiles/discover', async (route) => {
    state.localProfileDiscoveries += 1
    await route.fulfill({ json: state.discoveredProfiles })
  })

  await page.route('http://backend.test/api/settings/ai/profiles/import-local', async (route) => {
    const body = route.request().postDataJSON() as { source_keys?: string[]; update_existing?: boolean }
    state.localProfileImports.push(body)
    const selected = new Set(body.source_keys?.length ? body.source_keys : state.discoveredProfiles.map((item) => String(item.source_key)))
    let imported = 0
    let updated = 0
    for (const candidate of state.discoveredProfiles) {
      if (!selected.has(String(candidate.source_key)) || candidate.available === false) continue
      const existingIndex = state.aiProfiles.findIndex((profile) => profile.source_key === candidate.source_key)
      const payload = {
        id: existingIndex >= 0 ? state.aiProfiles[existingIndex].id : `profile-${state.aiProfiles.length + 1}`,
        name: candidate.name,
        provider_name: candidate.provider_name,
        base_url: candidate.base_url ?? null,
        wire_api: candidate.wire_api ?? 'responses',
        model: candidate.model,
        api_key_source: candidate.api_key_source,
        gemini_cli_proxy: candidate.gemini_cli_proxy ?? null,
        enabled: candidate.enabled ?? true,
        source_key: candidate.source_key,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
        is_default: false,
        test_status: 'untested',
        diagnostic_code: '',
        diagnostic_message: '',
      }
      if (existingIndex >= 0) {
        state.aiProfiles[existingIndex] = payload
        updated += 1
      } else {
        state.aiProfiles.push(payload)
        imported += 1
      }
    }
    state.discoveredProfiles = state.discoveredProfiles.map((candidate) => ({
      ...candidate,
      existing_profile_id: state.aiProfiles.find((profile) => profile.source_key === candidate.source_key)?.id ?? null,
    }))
    await route.fulfill({
      json: {
        profiles: state.aiProfiles,
        imported_count: imported,
        updated_count: updated,
        skipped: [],
      },
    })
  })

  await page.route('http://backend.test/api/settings/ai/profiles', async (route) => {
    const request = route.request()
    if (request.method() === 'POST') {
      const body = request.postDataJSON() as Record<string, unknown>
      const created = {
        id: `profile-${state.aiProfiles.length + 1}`,
        name: body.name,
        provider_name: body.provider_name,
        base_url: body.base_url ?? null,
        wire_api: body.wire_api ?? 'responses',
        model: body.model,
        api_key_source: body.api_key_source,
        gemini_cli_proxy: body.gemini_cli_proxy ?? null,
        enabled: body.enabled ?? true,
        source_key: body.source_key ?? null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
        is_default: state.defaultProfileId === null,
        test_status: 'untested',
        diagnostic_code: '',
        diagnostic_message: '',
      }
      state.aiProfiles.push(created)
      if (!state.defaultProfileId) state.defaultProfileId = String(created.id)
      await route.fulfill({ status: 201, json: created })
      return
    }
    state.profileListGets += 1
    const responseProfiles = state.aiProfiles.map((profile) => ({ ...profile }))
    if (state.profileListGets === 1 && options.staleInitialProfileListDelayMs) {
      await new Promise((resolve) => setTimeout(resolve, options.staleInitialProfileListDelayMs))
    }
    state.profileListResponses += 1
    await route.fulfill({ json: { profiles: responseProfiles.map((profile) => ({ ...profile, is_default: profile.id === state.defaultProfileId })), default_profile_id: state.defaultProfileId } })
  })

  await page.route('http://backend.test/api/settings/ai/default-profile', async (route) => {
    const body = route.request().postDataJSON() as { profile_id: string }
    state.defaultProfileId = body.profile_id
    await route.fulfill({ json: { profiles: state.aiProfiles.map((profile) => ({ ...profile, is_default: profile.id === state.defaultProfileId })), default_profile_id: state.defaultProfileId } })
  })

  await page.route('http://backend.test/api/settings/ai/profiles/check', async (route) => {
    await route.fulfill({ json: { profiles: state.aiProfiles.map((profile) => ({ ...profile, is_default: profile.id === state.defaultProfileId })), default_profile_id: state.defaultProfileId } })
  })

  await page.route(/http:\/\/backend\.test\/api\/settings\/ai\/profiles\/[^/]+\/test-live$/, async (route) => {
    const profileId = new URL(route.request().url()).pathname.split('/').at(-2) ?? ''
    state.aiLiveTests.push({ profile_id: profileId })
    const index = state.aiProfiles.findIndex((profile) => profile.id === profileId)
    const updated = { ...state.aiProfiles[index], test_status: 'passed', last_tested_at: '2026-01-01T00:00:00Z', last_test_transport: 'chat_completions', last_test_elapsed_ms: 120, diagnostic_code: '', diagnostic_message: '', is_default: profileId === state.defaultProfileId }
    state.aiProfiles[index] = updated
    await route.fulfill({ json: { profile: updated, test: { ok: true, message: '真实请求已通过。', provider: 'openai', model: updated.model, transport: 'chat_completions', elapsed_ms: 120, preview: '测试通过。', cost: 0.001 } } })
  })

  await page.route('http://backend.test/api/settings/ai/local-key', async (route) => {
    await route.fulfill({ json: { api_key_source: 'env:LTT_AI_TEST_KEY', env_var: 'LTT_AI_TEST_KEY', message: '密钥已保存到本机。', persisted: true } })
  })

  await page.route('http://backend.test/api/articles*', async (route) => {
    await route.fulfill({ json: [] })
  })

  await page.route('http://backend.test/api/collections', async (route) => {
    await route.fulfill({ json: [] })
  })

  await page.route('http://backend.test/api/ai-cards', async (route) => {
    await route.fulfill({ json: [] })
  })

  await page.route('http://backend.test/api/ai/task-presets', async (route) => {
    await route.fulfill({ json: {} })
  })

  await page.route('http://backend.test/api/ai/chat-settings', async (route) => {
    await route.fulfill({ json: { system_prompt: '' } })
  })

  await page.route('http://backend.test/api/ai/threads/current*', async (route) => {
    await route.fulfill({
      json: {
        thread: {
          id: 'thread-1',
          scope_kind: 'article',
          scope_id: 'article-1',
          title: '测试对话',
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
        messages: [],
      },
    })
  })

  await page.route('http://backend.test/api/settings/ai/test', async (route) => {
    state.aiTests.push(route.request().postDataJSON() as Record<string, unknown>)
    await route.fulfill({ json: { ok: true, message: 'ok' } })
  })

  await page.route('http://backend.test/api/settings/ai/test-live', async (route) => {
    state.aiLiveTests.push(route.request().postDataJSON() as Record<string, unknown>)
    await route.fulfill({
      json: {
        ok: true,
        message: '真实 AI 请求成功。provider=gemini, model=gemini-2.5-flash, transport=gateway_compatible, elapsed=120ms',
        provider: 'gemini',
        model: 'gemini-2.5-flash',
        transport: 'gateway_compatible',
        elapsed_ms: 120,
        preview: '雨夜车站，两个人就此告别。',
      },
    })
  })

  await page.route('http://backend.test/api/settings/ai/models?*', async (route) => {
    const url = new URL(route.request().url())
    const provider = url.searchParams.get('provider') ?? ''
    state.modelFetches.push(provider)
    if (provider === 'opencode') {
      await route.fulfill({
        json: {
          provider,
          models: [
            'opencode/deepseek-v4-flash-free',
            'opencode/mimo-v2.5-free',
          ],
          source: 'live',
          message: '已从 OpenCode 真实拉取模型列表。',
        },
      })
      return
    }
    await route.fulfill({
      json: {
        provider,
        models: aiSettings.model_presets[provider as keyof typeof aiSettings.model_presets] ?? [],
        source: 'preset',
        message: '当前 provider 暂未启用真实模型拉取，已显示内置预设。',
      },
    })
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

test('settings profile hub creates a relay profile, stores its key locally, and records live health', async ({ page }) => {
  const state = await mockSettingsPage(page)
  await page.goto('/settings')
  await expect(page.getByRole('heading', { name: 'AI 配置档案' })).toBeVisible({ timeout: 15000 })
  await page.getByRole('button', { name: '新增档案' }).click()
  await expect(page.getByRole('dialog', { name: '新建 AI 配置档案' })).toBeVisible()
  await page.getByRole('button', { name: /中转站 \/ 兼容接口/ }).click()
  const dialog = page.getByRole('dialog')
  const textboxes = dialog.getByRole('textbox')
  await textboxes.nth(0).fill('DeepSeek 中转')
  await textboxes.nth(1).fill('deepseek-v4-pro')
  await textboxes.nth(2).fill('https://relay.example/v1')
  await dialog.getByLabel('API Key').fill('sk-test-only')
  await dialog.getByRole('button', { name: '保存并继续' }).click()
  await expect(dialog.getByText('档案已保存')).toBeVisible()
  await dialog.getByRole('button', { name: '发送最小真实测试' }).click()
  await expect.poll(() => state.aiLiveTests).toEqual([{ profile_id: 'profile-1' }])
  await expect(page.getByText('已通过', { exact: true })).toBeVisible()
  expect(state.defaultProfileId).toBe('profile-1')
})

test('settings data storage buttons call native commands and protect migration with confirmation', async ({ page }) => {
  const state = await mockSettingsPage(page, { customDataDir: true })

  await page.goto('/settings')
  await page.getByRole('button', { name: '数据与备份' }).click()
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
  await page.getByRole('button', { name: '数据与备份' }).click()
  await expect(page.getByText('后台服务版本过旧或安装不完整')).toBeVisible()
  await expect(page.getByText('当前后台服务不支持数据目录管理。请退出应用后重新安装最新版本；你的写作数据不会被删除。')).toBeVisible()

  await page.getByRole('button', { name: '重启应用' }).click()
  await expect(page.getByText('正在重启应用...')).toBeVisible()
  await expect.poll(() => page.evaluate(() => window.__settingsInvokes?.some((item) => item.command === 'restart_app'))).toBe(true)
})

test('settings can check for updates, download internally, and launch installer', async ({ page }) => {
  const state = await mockSettingsPage(page, { updateAvailable: true })

  await page.goto('/settings')
  await page.getByRole('button', { name: '更新与关于' }).click()
  const updateSection = page.locator('section').filter({ hasText: '关于与更新' })
  await expect(updateSection).toBeVisible({ timeout: 15000 })

  await updateSection.getByRole('button', { name: '检查更新' }).click()
  await expect.poll(() => state.updateChecks).toBe(1)
  await expect(page.getByText('发现新版本。可以在应用内下载安装包并启动安装。')).toBeVisible()
  await expect(page.getByText('Living to Tell Preview 0.1.14')).toBeVisible()
  await expect(page.getByText('LivingToTell_0.1.14_x64-setup.exe')).toBeVisible()
  await expect(page.getByText('https=127.0.0.1:7890')).toBeVisible()

  await updateSection.getByRole('button', { name: '下载并安装' }).click()
  await expect.poll(() => state.updateDownloads).toEqual([
    {
      download_url: 'https://github.com/sidiangongyuan/living-to-tell/releases/download/living-to-tell-v0.1.14/LivingToTell_0.1.14_x64-setup.exe',
      download_name: 'LivingToTell_0.1.14_x64-setup.exe',
      expected_sha256: 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    },
  ])
  await expect.poll(() => page.evaluate(() =>
    window.__settingsInvokes?.some((item) =>
      item.command === 'install_update_and_exit'
      && item.args?.installerPath === 'C:\\Temp\\LivingToTell_0.1.14_x64-setup.exe'
    )
  )).toBe(true)

  await updateSection.getByRole('button', { name: '浏览器下载' }).click()
  await expect.poll(() => page.evaluate(() => window.__openedUrls)).toContain(
    'https://github.com/sidiangongyuan/living-to-tell/releases/download/living-to-tell-v0.1.14/LivingToTell_0.1.14_x64-setup.exe',
  )
  await expect.poll(() => page.evaluate(() =>
    window.__settingsInvokes?.some((item) =>
      item.command === 'open_external_url'
      && item.args?.url === 'https://github.com/sidiangongyuan/living-to-tell/releases/download/living-to-tell-v0.1.14/LivingToTell_0.1.14_x64-setup.exe'
    )
  )).toBe(true)
})
