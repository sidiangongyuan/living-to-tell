import { afterEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { AUTO_UPDATE_CHECK_DELAY_MS, UPDATE_DISMISSED_VERSION_KEY, useAppUpdateStore } from './appUpdate'
import { appApi } from '../api/app'

vi.mock('../api/app', () => ({
  appApi: {
    getVersion: vi.fn(),
    checkForUpdate: vi.fn(),
  },
}))

describe('app update store', () => {
  afterEach(() => {
    vi.clearAllMocks()
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('checks for updates automatically and supports dismissing the current release', async () => {
    const setItem = vi.fn()
    const getItem = vi.fn().mockReturnValue(null)
    vi.stubGlobal('localStorage', {
      getItem,
      setItem,
    })
    setActivePinia(createPinia())
    const store = useAppUpdateStore()

    vi.useFakeTimers()
    vi.mocked(appApi.getVersion).mockResolvedValue({
      app_name: 'Living to Tell',
      version: '0.1.12',
      api_version: '2.0.0',
      capabilities: ['update_check'],
    })
    vi.mocked(appApi.checkForUpdate).mockResolvedValue({
      current_version: '0.1.12',
      latest_version: '0.1.13',
      latest_tag: 'living-to-tell-v0.1.13',
      release_name: 'Living to Tell Preview 0.1.13',
      release_url: 'https://example.test/releases/tag/living-to-tell-v0.1.13',
      published_at: '2026-06-26T01:02:03Z',
      release_notes: 'Added update notifications.',
      source: 'github_releases_latest',
      status: 'update_available',
      message: '发现新版本。请下载最新安装包或点击下载安装包完成更新。',
      checked_at: '2026-06-26T01:05:06Z',
      cached: false,
      download_url: 'https://example.test/LivingToTell_0.1.13_x64-setup.exe',
      download_name: 'LivingToTell_0.1.13_x64-setup.exe',
    })

    store.scheduleAutomaticCheck()
    expect(appApi.checkForUpdate).not.toHaveBeenCalled()

    await vi.advanceTimersByTimeAsync(AUTO_UPDATE_CHECK_DELAY_MS)
    await vi.runAllTicks()

    expect(appApi.getVersion).toHaveBeenCalledOnce()
    expect(appApi.checkForUpdate).toHaveBeenCalledOnce()
    expect(store.hasVisibleUpdate).toBe(true)
    expect(store.latestVersion).toBe('0.1.13')

    store.dismissUpdate()
    expect(setItem).toHaveBeenCalledWith(UPDATE_DISMISSED_VERSION_KEY, '0.1.13')
    expect(store.hasVisibleUpdate).toBe(false)
  })
})
