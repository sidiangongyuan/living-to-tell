import { afterEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { AUTO_UPDATE_CHECK_DELAY_MS, UPDATE_DISMISSED_VERSION_KEY, useAppUpdateStore } from './appUpdate'
import { appApi } from '../api/app'
import { invoke } from '@tauri-apps/api/core'

vi.mock('../api/app', () => ({
  appApi: {
    getVersion: vi.fn(),
    checkForUpdate: vi.fn(),
    downloadUpdate: vi.fn(),
  },
}))

vi.mock('@tauri-apps/api/core', () => ({
  invoke: vi.fn(),
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
      version: '0.1.13',
      api_version: '2.0.0',
      capabilities: ['update_check'],
    })
    vi.mocked(appApi.checkForUpdate).mockResolvedValue({
      current_version: '0.1.13',
      latest_version: '0.1.14',
      latest_tag: 'living-to-tell-v0.1.14',
      release_name: 'Living to Tell Preview 0.1.14',
      release_url: 'https://example.test/releases/tag/living-to-tell-v0.1.14',
      published_at: '2026-06-26T01:02:03Z',
      release_notes: 'Added update notifications.',
      source: 'github_releases_latest',
      status: 'update_available',
      message: '发现新版本。请下载最新安装包或点击下载安装包完成更新。',
      checked_at: '2026-06-26T01:05:06Z',
      cached: false,
      download_url: 'https://example.test/LivingToTell_0.1.14_x64-setup.exe',
      download_name: 'LivingToTell_0.1.14_x64-setup.exe',
      download_sha256: null,
      network_proxy: null,
      network_detail: null,
    })

    store.scheduleAutomaticCheck()
    expect(appApi.checkForUpdate).not.toHaveBeenCalled()

    await vi.advanceTimersByTimeAsync(AUTO_UPDATE_CHECK_DELAY_MS)
    await vi.runAllTicks()

    expect(appApi.getVersion).toHaveBeenCalledOnce()
    expect(appApi.checkForUpdate).toHaveBeenCalledOnce()
    expect(store.hasVisibleUpdate).toBe(true)
    expect(store.latestVersion).toBe('0.1.14')

    store.dismissUpdate()
    expect(setItem).toHaveBeenCalledWith(UPDATE_DISMISSED_VERSION_KEY, '0.1.14')
    expect(store.hasVisibleUpdate).toBe(false)
  })

  it('downloads an update and asks Tauri to launch the installer', async () => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn().mockReturnValue(null),
      setItem: vi.fn(),
    })
    setActivePinia(createPinia())
    const store = useAppUpdateStore()

    vi.mocked(appApi.checkForUpdate).mockResolvedValue({
      current_version: '0.1.18',
      latest_version: '0.1.19',
      latest_tag: 'living-to-tell-v0.1.19',
      release_name: 'Living to Tell Preview 0.1.19',
      release_url: 'https://example.test/releases/tag/living-to-tell-v0.1.19',
      published_at: '2026-06-28T01:02:03Z',
      release_notes: 'Update notes.',
      source: 'github_releases_latest',
      status: 'update_available',
      message: '发现新版本。',
      checked_at: '2026-06-28T01:05:06Z',
      cached: false,
      download_url: 'https://github.com/sidiangongyuan/living-to-tell/releases/download/living-to-tell-v0.1.19/LivingToTell_0.1.19_x64-setup.exe',
      download_name: 'LivingToTell_0.1.19_x64-setup.exe',
      download_sha256: 'abc123',
      network_proxy: 'https=127.0.0.1:7890',
      network_detail: null,
    })
    vi.mocked(appApi.downloadUpdate).mockResolvedValue({
      status: 'downloaded',
      message: '安装包已下载，准备启动安装器。',
      file_path: 'C:\\Temp\\LivingToTell_0.1.19_x64-setup.exe',
      file_name: 'LivingToTell_0.1.19_x64-setup.exe',
      size_bytes: 123,
      sha256: 'ABC123',
      downloaded_at: '2026-06-28T01:06:06Z',
    })
    vi.mocked(invoke).mockResolvedValue(undefined)

    await store.checkForUpdates({ force: true })
    await store.downloadAndInstall()

    expect(appApi.downloadUpdate).toHaveBeenCalledWith({
      download_url: 'https://github.com/sidiangongyuan/living-to-tell/releases/download/living-to-tell-v0.1.19/LivingToTell_0.1.19_x64-setup.exe',
      download_name: 'LivingToTell_0.1.19_x64-setup.exe',
      expected_sha256: 'abc123',
    })
    expect(invoke).toHaveBeenCalledWith('install_update_and_exit', {
      installerPath: 'C:\\Temp\\LivingToTell_0.1.19_x64-setup.exe',
    })
    expect(store.downloadStatus).toBe('installing')
    expect(store.downloadedSha256).toBe('ABC123')
    expect(store.networkProxy).toBe('https=127.0.0.1:7890')
  })
})
