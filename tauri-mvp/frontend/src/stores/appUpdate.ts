import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { appApi, type AppUpdateInfo, type AppUpdateStatus } from '../api/app'
import { openExternalUrl } from '../utils/openExternal'

export const UPDATE_DISMISSED_VERSION_KEY = 'living_to_tell_dismissed_update_version'
export const UPDATE_LAST_CHECKED_AT_KEY = 'living_to_tell_update_last_checked_at'
export const AUTO_UPDATE_CHECK_DELAY_MS = 5000
export const AUTO_UPDATE_CHECK_INTERVAL_MS = 12 * 60 * 60 * 1000
const AUTO_UPDATE_DISABLED_FLAG = '__WRITER_DISABLE_AUTO_UPDATE__'

type UpdateCheckSource = 'auto' | 'manual'

export const useAppUpdateStore = defineStore('appUpdate', () => {
  const status = ref<AppUpdateStatus | 'idle' | 'checking'>('idle')
  const currentVersion = ref('')
  const latestVersion = ref('')
  const latestTag = ref('')
  const releaseName = ref('')
  const releaseUrl = ref('')
  const publishedAt = ref('')
  const releaseNotes = ref('')
  const message = ref('')
  const checkedAt = ref('')
  const cached = ref(false)
  const downloadUrl = ref('')
  const downloadName = ref('')
  const downloadSha256 = ref('')
  const networkProxy = ref('')
  const networkDetail = ref('')
  const downloadStatus = ref<'idle' | 'downloading' | 'installing' | 'downloaded'>('idle')
  const downloadMessage = ref('')
  const downloadedFilePath = ref('')
  const downloadedSha256 = ref('')
  const dismissedVersion = ref(localStorage.getItem(UPDATE_DISMISSED_VERSION_KEY) || '')
  const automaticCheckScheduled = ref(false)

  let automaticCheckTimer: ReturnType<typeof setTimeout> | null = null

  const hasVisibleUpdate = computed(
    () =>
      status.value === 'update_available'
      && !!latestVersion.value
      && dismissedVersion.value !== latestVersion.value,
  )

  async function ensureVersionLoaded() {
    if (currentVersion.value) return
    try {
      const info = await appApi.getVersion()
      currentVersion.value = info.version
    } catch {
      // Keep the update UI usable even when the local version endpoint is not ready yet.
    }
  }

  function shouldAutoCheck() {
    if (typeof window !== 'undefined' && Boolean((window as Window & { __WRITER_DISABLE_AUTO_UPDATE__?: boolean })[AUTO_UPDATE_DISABLED_FLAG])) {
      return false
    }
    const lastCheckedAt = Number(localStorage.getItem(UPDATE_LAST_CHECKED_AT_KEY) || '0')
    if (!lastCheckedAt) return true
    return Date.now() - lastCheckedAt >= AUTO_UPDATE_CHECK_INTERVAL_MS
  }

  function applyResult(result: AppUpdateInfo) {
    currentVersion.value = result.current_version || currentVersion.value
    latestVersion.value = result.latest_version || ''
    latestTag.value = result.latest_tag || ''
    releaseName.value = result.release_name || ''
    releaseUrl.value = result.release_url || ''
    publishedAt.value = result.published_at || ''
    releaseNotes.value = result.release_notes || ''
    message.value = result.message
    checkedAt.value = result.checked_at
    cached.value = result.cached
    downloadUrl.value = result.download_url || ''
    downloadName.value = result.download_name || ''
    downloadSha256.value = result.download_sha256 || ''
    networkProxy.value = result.network_proxy || ''
    networkDetail.value = result.network_detail || ''
    status.value = result.status
    if (result.status !== 'error') {
      localStorage.setItem(UPDATE_LAST_CHECKED_AT_KEY, String(Date.now()))
    }
  }

  async function checkForUpdates(options: {
    force?: boolean
    source?: UpdateCheckSource
  } = {}) {
    const force = options.force === true
    const source = options.source ?? 'manual'
    if (source === 'auto' && !force && !shouldAutoCheck()) return

    const previous = {
      status: status.value,
      message: message.value,
      cached: cached.value,
    }
    if (source !== 'auto') {
      status.value = 'checking'
    }
    try {
      const result = await appApi.checkForUpdate(force)
      applyResult(result)
    } catch (error) {
      if (source === 'auto') {
        status.value = previous.status
        message.value = previous.message
        cached.value = previous.cached
        return
      }
      status.value = 'error'
      message.value = error instanceof Error ? error.message : String(error)
      cached.value = false
    }
  }

  function scheduleAutomaticCheck() {
    if (automaticCheckScheduled.value) return
    automaticCheckScheduled.value = true
    if (typeof window !== 'undefined' && Boolean((window as Window & { __WRITER_DISABLE_AUTO_UPDATE__?: boolean })[AUTO_UPDATE_DISABLED_FLAG])) {
      return
    }
    void ensureVersionLoaded()
    automaticCheckTimer = globalThis.setTimeout(() => {
      automaticCheckTimer = null
      void checkForUpdates({ source: 'auto' })
    }, AUTO_UPDATE_CHECK_DELAY_MS)
  }

  function dismissUpdate() {
    if (!latestVersion.value) return
    dismissedVersion.value = latestVersion.value
    localStorage.setItem(UPDATE_DISMISSED_VERSION_KEY, latestVersion.value)
  }

  async function openDownload() {
    const target = downloadUrl.value || releaseUrl.value
    if (!target) throw new Error('No release download URL is available.')
    await openExternalUrl(target)
  }

  async function downloadAndInstall() {
    if (!downloadUrl.value) throw new Error('No release download URL is available.')
    downloadStatus.value = 'downloading'
    downloadMessage.value = '正在下载安装包…'
    downloadedFilePath.value = ''
    downloadedSha256.value = ''
    try {
      const downloaded = await appApi.downloadUpdate({
        download_url: downloadUrl.value,
        download_name: downloadName.value || null,
        expected_sha256: downloadSha256.value || null,
      })
      downloadedFilePath.value = downloaded.file_path
      downloadedSha256.value = downloaded.sha256
      downloadStatus.value = 'installing'
      downloadMessage.value = downloaded.message || '安装包已下载，正在启动安装器…'
      const { invoke } = await import('@tauri-apps/api/core')
      await invoke('install_update_and_exit', { installerPath: downloaded.file_path })
    } catch (error) {
      downloadStatus.value = 'idle'
      downloadMessage.value = error instanceof Error ? error.message : String(error)
      throw error
    }
  }

  async function openReleasePage() {
    const target = releaseUrl.value || downloadUrl.value
    if (!target) throw new Error('No release page URL is available.')
    await openExternalUrl(target)
  }

  function resetForTests() {
    if (automaticCheckTimer) {
      clearTimeout(automaticCheckTimer)
      automaticCheckTimer = null
    }
    automaticCheckScheduled.value = false
    status.value = 'idle'
    currentVersion.value = ''
    latestVersion.value = ''
    latestTag.value = ''
    releaseName.value = ''
    releaseUrl.value = ''
    publishedAt.value = ''
    releaseNotes.value = ''
    message.value = ''
    checkedAt.value = ''
    cached.value = false
    downloadUrl.value = ''
    downloadName.value = ''
    downloadSha256.value = ''
    networkProxy.value = ''
    networkDetail.value = ''
    downloadStatus.value = 'idle'
    downloadMessage.value = ''
    downloadedFilePath.value = ''
    downloadedSha256.value = ''
    dismissedVersion.value = localStorage.getItem(UPDATE_DISMISSED_VERSION_KEY) || ''
  }

  return {
    status,
    currentVersion,
    latestVersion,
    latestTag,
    releaseName,
    releaseUrl,
    publishedAt,
    releaseNotes,
    message,
    checkedAt,
    cached,
    downloadUrl,
    downloadName,
    downloadSha256,
    networkProxy,
    networkDetail,
    downloadStatus,
    downloadMessage,
    downloadedFilePath,
    downloadedSha256,
    dismissedVersion,
    hasVisibleUpdate,
    ensureVersionLoaded,
    checkForUpdates,
    scheduleAutomaticCheck,
    dismissUpdate,
    downloadAndInstall,
    openDownload,
    openReleasePage,
    resetForTests,
  }
})
