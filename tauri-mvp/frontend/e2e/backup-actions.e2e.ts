import { expect, test, type Page } from '@playwright/test'

const backup = {
  path: 'C:\\Data\\backups\\auto_backup_20260619.sqlite3',
  name: 'auto_backup_20260619',
  size: 2048,
  created: '2026-06-19T08:00:00Z',
}

const checkpoint = {
  path: 'C:\\Data\\checkpoints\\chapter-three.sqlite3',
  name: 'chapter-three',
  description: '第三章完成',
  size: 4096,
  created: '2026-06-19T09:00:00Z',
}

async function mockBackupApi(page: Page) {
  let backups = [backup]
  let checkpoints = [checkpoint]

  await page.addInitScript(() => {
    window.localStorage.clear()
    window.__WRITER_API_BASE__ = 'http://backend.test'
    ;(window as Window & { __WRITER_DISABLE_AUTO_UPDATE__?: boolean }).__WRITER_DISABLE_AUTO_UPDATE__ = true
    Object.defineProperty(window, '__TAURI_INTERNALS__', {
      value: {
        invoke: (command: string) => Promise.resolve(command === 'get_api_base_url' ? 'http://backend.test' : null),
        transformCallback: () => 1,
      },
      configurable: true,
    })
  })

  await page.route('http://backend.test/api/app/version', async (route) => {
    await route.fulfill({
      json: {
        app_name: 'Living to Tell',
        version: '0.1.12',
        api_version: '2.0.0',
        capabilities: ['data_location', 'ai_chat_settings', 'ai_task_presets', 'update_check'],
      },
    })
  })
  await page.route('http://backend.test/api/app/update-check*', async (route) => {
    await route.fulfill({
      json: {
        current_version: '0.1.12',
        latest_version: '0.1.12',
        latest_tag: 'living-to-tell-v0.1.12',
        release_name: 'Living to Tell Preview 0.1.12',
        release_url: 'https://github.com/sidiangongyuan/living-to-tell/releases/tag/living-to-tell-v0.1.12',
        published_at: '2026-06-25T03:03:04Z',
        release_notes: '',
        source: 'github_releases_latest',
        status: 'up_to_date',
        message: '当前已是最新版本。',
        checked_at: '2026-06-25T03:05:06Z',
        cached: false,
        download_url: 'https://github.com/sidiangongyuan/living-to-tell/releases/download/living-to-tell-v0.1.12/LivingToTell_0.1.12_x64-setup.exe',
        download_name: 'LivingToTell_0.1.12_x64-setup.exe',
      },
    })
  })

  await page.route('http://backend.test/api/backup/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())

    if (url.pathname === '/api/backup/backups') {
      await route.fulfill({ json: backups })
      return
    }
    if (url.pathname === '/api/backup/checkpoints') {
      if (request.method() === 'POST') {
        const body = request.postDataJSON() as { name?: string; description?: string }
        const created = {
          ...checkpoint,
          path: `C:\\Data\\checkpoints\\${body.name}.sqlite3`,
          name: body.name ?? '',
          description: body.description ?? '',
        }
        checkpoints = [created, ...checkpoints]
        await route.fulfill({ status: 201, json: created })
        return
      }
      await route.fulfill({ json: checkpoints })
      return
    }
    if (url.pathname === '/api/backup/stats') {
      await route.fulfill({
        json: {
          backup_count: backups.length,
          checkpoint_count: checkpoints.length,
          total_backup_size: backups.reduce((total, item) => total + item.size, 0),
          total_checkpoint_size: checkpoints.reduce((total, item) => total + item.size, 0),
          total_size: [...backups, ...checkpoints].reduce((total, item) => total + item.size, 0),
          backup_dir: 'C:\\Data\\backups',
          checkpoint_dir: 'C:\\Data\\checkpoints',
        },
      })
      return
    }
    if (url.pathname === '/api/backup/auto-backup') {
      const created = {
        ...backup,
        path: 'C:\\Data\\backups\\auto_backup_created.sqlite3',
        name: 'auto_backup_created',
      }
      backups = [created, ...backups]
      await route.fulfill({ status: 201, json: created })
      return
    }
    if (url.pathname.startsWith('/api/backup/backups/') && request.method() === 'DELETE') {
      backups = []
      await route.fulfill({ status: 204 })
      return
    }
    if (url.pathname.startsWith('/api/backup/checkpoints/') && request.method() === 'DELETE') {
      checkpoints = []
      await route.fulfill({ status: 204 })
      return
    }
    if (url.pathname === '/api/backup/restore') {
      await route.fulfill({ json: { message: 'Database restored successfully' } })
      return
    }
    await route.fallback()
  })
}

test.beforeEach(async ({ page }) => {
  await mockBackupApi(page)
})

test('backup page create, delete, and restore actions call real APIs with confirmations', async ({ page }) => {
  const checkpointCreates: Array<Record<string, unknown>> = []
  let backupCreates = 0
  let backupDeletes = 0
  let checkpointDeletes = 0
  let restores = 0

  await page.route('http://backend.test/api/backup/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    if (url.pathname === '/api/backup/checkpoints' && request.method() === 'POST') {
      checkpointCreates.push(request.postDataJSON() as Record<string, unknown>)
      await route.fallback()
      return
    }
    if (url.pathname === '/api/backup/auto-backup' && request.method() === 'POST') {
      backupCreates += 1
      await route.fallback()
      return
    }
    if (url.pathname.startsWith('/api/backup/backups/') && request.method() === 'DELETE') {
      backupDeletes += 1
      await route.fallback()
      return
    }
    if (url.pathname.startsWith('/api/backup/checkpoints/') && request.method() === 'DELETE') {
      checkpointDeletes += 1
      await route.fallback()
      return
    }
    if (url.pathname === '/api/backup/restore' && request.method() === 'POST') {
      restores += 1
      await route.fallback()
      return
    }
    await route.fallback()
  })

  await page.goto('/backup')
  await expect(page.getByText('chapter-three')).toBeVisible()
  await expect(page.getByText('auto_backup_20260619')).toBeVisible()

  await page.getByRole('button', { name: '创建检查点' }).click()
  const createCheckpointButton = page.getByRole('button', { name: '创建', exact: true })
  await expect(createCheckpointButton).toBeDisabled()
  await page.getByPlaceholder('例如：完成第三章').fill('   ')
  await expect(createCheckpointButton).toBeDisabled()
  await page.getByPlaceholder('例如：完成第三章').fill('新检查点')
  await expect(createCheckpointButton).toBeEnabled()
  await page.getByPlaceholder('添加一些说明...').fill('保留当前进度')
  await createCheckpointButton.click()
  await expect.poll(() => checkpointCreates).toEqual([
    { name: '新检查点', description: '保留当前进度' },
  ])
  await expect(page.getByText('检查点已创建。')).toBeVisible()

  await page.getByRole('button', { name: '创建备份' }).click()
  await expect.poll(() => backupCreates).toBe(1)
  await expect(page.getByText('备份已创建。')).toBeVisible()

  const checkpointCard = page.locator('article').filter({ hasText: 'chapter-three' }).first()
  await checkpointCard.getByRole('button', { name: '删除' }).click()
  await page.getByRole('button', { name: '取消' }).click()
  expect(checkpointDeletes).toBe(0)

  await checkpointCard.getByRole('button', { name: '删除' }).click()
  await page.getByRole('button', { name: '确认' }).click()
  await expect.poll(() => checkpointDeletes).toBe(1)
  await expect(page.getByText('已删除。')).toBeVisible()

  await page.locator('article').filter({ hasText: 'auto_backup_20260619' }).first().getByRole('button', { name: '恢复' }).click()
  await page.getByRole('button', { name: '取消' }).click()
  expect(restores).toBe(0)

  await page.locator('article').filter({ hasText: 'auto_backup_20260619' }).first().getByRole('button', { name: '恢复' }).click()
  await page.getByRole('button', { name: '确认' }).click()
  await expect.poll(() => restores).toBe(1)
  await expect(page.getByText('恢复成功。应用将重启以重新加载数据库。')).toBeVisible()

  const backupCard = page.locator('article').filter({ hasText: 'auto_backup_20260619' }).first()
  await backupCard.getByRole('button', { name: '删除' }).click()
  await page.getByRole('button', { name: '取消' }).click()
  expect(backupDeletes).toBe(0)

  await backupCard.getByRole('button', { name: '删除' }).click()
  await page.getByRole('button', { name: '确认' }).click()
  await expect.poll(() => backupDeletes).toBe(1)
})
