<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from '../../i18n'
import { backupApi, type BackupInfo, type BackupStats, type CheckpointInfo } from './api'
import { settingsApi, type DataLocationInfo } from '../../api/settings'
import { articlesApi, type ArticleExportFormat } from '../../api/articles'
import { collectionsApi, type CollectionExportFormat } from '../../api/collections'
import { saveBlobWithDialog } from '../../utils/exportFile'
import { LAST_SELECTED_ARTICLE_KEY } from '../articles/editorPosition'
import ContextMenu from '../../components/ContextMenu.vue'
import { errorMessage } from '../../api/base'

const LAST_SELECTED_COLLECTION_KEY = 'living_to_tell_last_selected_collection_id'
const BACKUP_REMINDER_DAYS_KEY = 'living_to_tell_backup_reminder_days'

type RestorePointType = 'backup' | 'checkpoint'

interface RestorePoint {
  path: string
  name: string
  size: number
  created: string
  type: RestorePointType
  description: string
}

const { t } = useI18n()

const backups = ref<BackupInfo[]>([])
const checkpoints = ref<CheckpointInfo[]>([])
const stats = ref<BackupStats | null>(null)
const dataLocation = ref<DataLocationInfo | null>(null)
const loading = ref(false)
const error = ref('')
const notice = ref('')
const exportShortcutBusy = ref('')
const selectedRestorePath = ref('')
const storedReminderDays = Number(localStorage.getItem(BACKUP_REMINDER_DAYS_KEY) || '7')
const backupReminderDays = ref([1, 3, 7, 14, 30].includes(storedReminderDays) ? storedReminderDays : 7)
const articleExportFormats: ArticleExportFormat[] = ['md', 'txt', 'docx']
const collectionExportFormats: CollectionExportFormat[] = ['md', 'txt', 'docx']

const showCheckpointDialog = ref(false)
const checkpointName = ref('')
const checkpointDescription = ref('')
const creatingCheckpoint = ref(false)

const showConfirmDialog = ref(false)
const confirmAction = ref<() => void>(() => {})
const confirmMessage = ref('')
const deleteContextMenuOpen = ref(false)
const deleteContextMenuX = ref(0)
const deleteContextMenuY = ref(0)
const deleteContextTarget = ref<{
  path: string
  name: string
  type: 'backup' | 'checkpoint'
} | null>(null)

onMounted(() => {
  loadData()
})

watch(backupReminderDays, (value) => {
  localStorage.setItem(BACKUP_REMINDER_DAYS_KEY, String(value))
})

const restorePoints = computed<RestorePoint[]>(() => {
  const items: RestorePoint[] = [
    ...checkpoints.value.map((checkpoint) => ({
      path: checkpoint.path,
      name: checkpoint.name,
      size: checkpoint.size,
      created: checkpoint.created,
      type: 'checkpoint' as const,
      description: checkpoint.description,
    })),
    ...backups.value.map((backup) => ({
      path: backup.path,
      name: backup.name,
      size: backup.size,
      created: backup.created,
      type: 'backup' as const,
      description: '',
    })),
  ]
  return items.sort((a, b) => new Date(b.created).getTime() - new Date(a.created).getTime())
})

const latestRestorePoint = computed(() => restorePoints.value[0] ?? null)
const selectedRestorePoint = computed(() =>
  restorePoints.value.find((point) => point.path === selectedRestorePath.value) ?? latestRestorePoint.value
)
const daysSinceLatestRestore = computed(() => {
  if (!latestRestorePoint.value) return null
  const createdAt = new Date(latestRestorePoint.value.created).getTime()
  if (!Number.isFinite(createdAt)) return null
  return Math.max(0, Math.floor((Date.now() - createdAt) / 86400000))
})
const backupDue = computed(() =>
  daysSinceLatestRestore.value === null || daysSinceLatestRestore.value >= backupReminderDays.value
)
const latestRestoreAge = computed(() =>
  daysSinceLatestRestore.value === null
    ? t('backup.aWhile')
    : t('backup.daysCount', { count: daysSinceLatestRestore.value })
)
const protectionState = computed(() => {
  if (!restorePoints.value.length) {
    return {
      tone: 'empty',
      title: t('backup.noRestorePointTitle'),
      copy: t('backup.noRestorePointCopy'),
    }
  }
  if (backupDue.value) {
    return {
      tone: 'warn',
      title: t('backup.backupDueTitle'),
      copy: t('backup.backupDueCopy', { age: latestRestoreAge.value }),
    }
  }
  return {
    tone: 'good',
    title: t('backup.protectedTitle'),
    copy: t('backup.protectedCopy'),
  }
})

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [b, c, s, location] = await Promise.all([
      backupApi.listBackups(),
      backupApi.listCheckpoints(),
      backupApi.getStats(),
      settingsApi.getDataLocation().catch(() => null),
    ])
    backups.value = b
    checkpoints.value = c
    stats.value = s
    dataLocation.value = location
    if (!selectedRestorePath.value && (c.length || b.length)) {
      selectedRestorePath.value = [...c, ...b]
        .sort((a, b) => new Date(b.created).getTime() - new Date(a.created).getTime())[0]?.path ?? ''
    }
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

async function createBackup() {
  loading.value = true
  error.value = ''
  notice.value = ''
  try {
    await backupApi.createBackup()
    await loadData()
    notice.value = t('backup.backupCreated')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

async function createCheckpoint() {
  if (!checkpointName.value.trim()) {
    error.value = t('backup.enterCheckpointName')
    return
  }
  creatingCheckpoint.value = true
  error.value = ''
  notice.value = ''
  try {
    await backupApi.createCheckpoint({
      name: checkpointName.value.trim(),
      description: checkpointDescription.value.trim(),
    })
    showCheckpointDialog.value = false
    checkpointName.value = ''
    checkpointDescription.value = ''
    await loadData()
    notice.value = t('backup.checkpointCreated')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    creatingCheckpoint.value = false
  }
}

function confirmRestore(path: string, name: string) {
  confirmMessage.value = t('backup.restoreConfirm', { name })
  confirmAction.value = () => restore(path)
  showConfirmDialog.value = true
}

function confirmSelectedRestore() {
  const point = selectedRestorePoint.value
  if (!point) {
    error.value = t('backup.selectRestorePointFirst')
    return
  }
  confirmRestore(point.path, point.name)
}

function selectRestorePoint(path: string) {
  selectedRestorePath.value = path
}

async function restore(path: string) {
  showConfirmDialog.value = false
  loading.value = true
  error.value = ''
  notice.value = ''
  try {
    await backupApi.restore(path)
    notice.value = t('backup.restoreSuccess')
    window.setTimeout(() => {
      void import('@tauri-apps/api/core')
        .then(({ invoke }) => invoke<void>('restart_app'))
        .catch(() => location.reload())
    }, 900)
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

function confirmDelete(path: string, name: string, type: 'backup' | 'checkpoint') {
  confirmMessage.value = t('backup.deleteConfirm', { name })
  confirmAction.value = () => deleteItem(path, type)
  showConfirmDialog.value = true
}

function closeDeleteContextMenu() {
  deleteContextMenuOpen.value = false
  deleteContextTarget.value = null
}

function openDeleteContextMenu(event: MouseEvent, target: typeof deleteContextTarget.value) {
  if (!target) return
  event.preventDefault()
  deleteContextTarget.value = target
  deleteContextMenuX.value = Math.max(12, Math.min(event.clientX + 8, window.innerWidth - 172))
  deleteContextMenuY.value = Math.max(12, Math.min(event.clientY + 8, window.innerHeight - 56))
  deleteContextMenuOpen.value = true
}

function handleDeleteContextMenuSelect(item: { key: string }) {
  const target = deleteContextTarget.value
  closeDeleteContextMenu()
  if (item.key === 'delete' && target) {
    confirmDelete(target.path, target.name, target.type)
  }
}

async function deleteItem(path: string, type: 'backup' | 'checkpoint') {
  showConfirmDialog.value = false
  loading.value = true
  error.value = ''
  notice.value = ''
  try {
    if (type === 'backup') {
      await backupApi.deleteBackup(path)
    } else {
      await backupApi.deleteCheckpoint(path)
    }
    await loadData()
    notice.value = t('backup.deleted')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleString()
}

function restoreTypeLabel(type: RestorePointType): string {
  return type === 'checkpoint' ? t('backup.checkpointType') : t('backup.autoBackupType')
}

function protectionToneClass(tone: string): string {
  if (tone === 'good') return 'border-emerald-200 bg-emerald-50 text-emerald-950'
  if (tone === 'warn') return 'border-amber-200 bg-amber-50 text-amber-950'
  return 'border-slate-200 bg-slate-50 text-slate-900'
}

async function copyPath(path: string | null | undefined) {
  if (!path) return
  try {
    await navigator.clipboard.writeText(path)
    notice.value = t('backup.pathCopied')
  } catch {
    error.value = t('backup.copyPathFailed')
  }
}

function safeFilename(title: string, format: string): string {
  const safe = (title || 'export').replace(/[<>:"/\\|?*]/g, '').trim() || 'export'
  return `${safe}.${format}`
}

async function openPath(path: string | null | undefined) {
  if (!path) {
    notice.value = ''
    error.value = t('backup.pathUnavailable')
    return
  }
  error.value = ''
  try {
    const { invoke } = await import('@tauri-apps/api/core')
    await invoke('open_path', { path })
  } catch (e) {
    error.value = t('backup.openDirectoryFailed', { error: errorMessage(e) })
  }
}

async function exportLastArticle(format: ArticleExportFormat) {
  const articleId = localStorage.getItem(LAST_SELECTED_ARTICLE_KEY)
  if (!articleId) {
    notice.value = ''
    error.value = t('backup.noRecentArticle')
    return
  }
  exportShortcutBusy.value = `article-${format}`
  error.value = ''
  notice.value = ''
  try {
    const article = await articlesApi.get(articleId)
    const blob = await articlesApi.exportArticle(articleId, format)
    const result = await saveBlobWithDialog(blob, safeFilename(article.title || 'article', format), format)
    notice.value = result.status === 'cancelled' ? t('backup.articleExportCancelled') : t('backup.articleExported')
  } catch (e) {
    error.value = t('backup.articleExportFailed', { error: errorMessage(e) })
  } finally {
    exportShortcutBusy.value = ''
  }
}

async function exportLastCollection(format: CollectionExportFormat) {
  const collectionId = localStorage.getItem(LAST_SELECTED_COLLECTION_KEY)
  if (!collectionId) {
    notice.value = ''
    error.value = t('backup.noRecentCollection')
    return
  }
  exportShortcutBusy.value = `collection-${format}`
  error.value = ''
  notice.value = ''
  try {
    const collection = await collectionsApi.getCollection(collectionId)
    const blob = await collectionsApi.exportCollection(collectionId, format)
    const result = await saveBlobWithDialog(blob, safeFilename(collection.title || 'collection', format), format)
    notice.value = result.status === 'cancelled' ? t('backup.collectionExportCancelled') : t('backup.collectionExported')
  } catch (e) {
    error.value = t('backup.collectionExportFailed', { error: errorMessage(e) })
  } finally {
    exportShortcutBusy.value = ''
  }
}
</script>

<template>
  <div class="flex h-full flex-col bg-gray-50">
    <div class="border-b border-gray-200 bg-white px-6 py-4">
      <div class="flex items-center justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">{{ t('backup.title') }}</h1>
          <p class="mt-1 text-sm text-gray-500">{{ t('backup.subtitle') }}</p>
        </div>
        <div class="flex gap-3">
          <button
            @click="showCheckpointDialog = true"
            class="rounded-lg bg-green-700 px-4 py-2 font-semibold text-white transition-colors hover:bg-green-800"
          >
            {{ t('backup.createCheckpoint') }}
          </button>
          <button
            @click="createBackup"
            :disabled="loading"
            class="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white transition-colors hover:bg-blue-700 disabled:bg-gray-600"
          >
            {{ loading ? t('backup.creatingBackup') : t('backup.createBackup') }}
          </button>
        </div>
      </div>

      <div v-if="stats" class="mt-5 grid gap-4 xl:grid-cols-[1fr_1.1fr]">
        <section
          :class="[
            'rounded-3xl border p-5 shadow-sm',
            protectionToneClass(protectionState.tone),
          ]"
          data-testid="backup-safety-summary"
        >
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.22em] opacity-70">{{ t('backup.safety') }}</p>
              <h2 class="mt-1 text-xl font-bold">{{ protectionState.title }}</h2>
              <p class="mt-2 max-w-xl text-sm leading-6 opacity-80">{{ protectionState.copy }}</p>
            </div>
            <div class="rounded-2xl bg-white/70 px-4 py-3 text-right shadow-sm">
              <div class="text-xs font-semibold opacity-80">{{ t('backup.latestRestorePoint') }}</div>
              <div class="mt-1 text-2xl font-bold">
                {{ daysSinceLatestRestore === null ? '—' : latestRestoreAge }}
              </div>
            </div>
          </div>
          <div class="mt-5 grid grid-cols-4 gap-2 text-center text-xs">
            <div class="rounded-2xl bg-white/70 px-3 py-3">
              <div class="font-semibold opacity-80">{{ t('backup.autoBackups') }}</div>
              <div class="mt-1 text-xl font-bold">{{ stats.backup_count }}</div>
            </div>
            <div class="rounded-2xl bg-white/70 px-3 py-3">
              <div class="font-semibold opacity-80">{{ t('backup.checkpoints') }}</div>
              <div class="mt-1 text-xl font-bold">{{ stats.checkpoint_count }}</div>
            </div>
            <div class="rounded-2xl bg-white/70 px-3 py-3">
              <div class="font-semibold opacity-80">{{ t('backup.backupSize') }}</div>
              <div class="mt-1 text-xl font-bold">{{ formatSize(stats.total_backup_size) }}</div>
            </div>
            <div class="rounded-2xl bg-white/70 px-3 py-3">
              <div class="font-semibold opacity-80">{{ t('backup.totalSize') }}</div>
              <div class="mt-1 text-xl font-bold">{{ formatSize(stats.total_size) }}</div>
            </div>
          </div>
          <div class="mt-4 flex flex-wrap items-center gap-3 rounded-2xl bg-white/70 px-4 py-3 text-sm">
            <span class="font-semibold">{{ t('backup.reminderThreshold') }}</span>
            <select v-model.number="backupReminderDays" :aria-label="t('backup.reminderThreshold')" class="rounded-xl border border-white bg-white px-3 py-2 text-sm outline-none">
              <option :value="1">{{ t('backup.daily') }}</option>
              <option v-for="days in [3, 7, 14, 30]" :key="days" :value="days">{{ t('backup.daysCount', { count: days }) }}</option>
            </select>
            <span class="text-xs opacity-70">{{ t('backup.reminderHelp') }}</span>
          </div>
        </section>

        <section class="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm" data-testid="backup-restore-planner">
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-600">{{ t('backup.recovery') }}</p>
              <h2 class="mt-1 text-xl font-bold text-slate-950">{{ t('backup.chooseRestorePoint') }}</h2>
              <p class="mt-2 text-sm leading-6 text-slate-500">{{ t('backup.restorePlannerHelp') }}</p>
            </div>
            <button
              type="button"
              class="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-40"
              :disabled="!selectedRestorePoint || loading"
              @click="confirmSelectedRestore"
            >
              {{ t('backup.restoreSelected') }}
            </button>
          </div>
          <div v-if="restorePoints.length" class="mt-4 grid gap-2 md:grid-cols-2">
            <button
              v-for="point in restorePoints.slice(0, 4)"
              :key="point.path"
              type="button"
              :class="[
                'rounded-2xl border p-3 text-left transition-colors',
                selectedRestorePoint?.path === point.path
                  ? 'border-slate-900 bg-slate-50'
                  : 'border-slate-200 bg-white hover:bg-slate-50',
              ]"
              @click="selectRestorePoint(point.path)"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <div class="truncate text-sm font-semibold text-slate-900">{{ point.name }}</div>
                  <div class="mt-1 text-xs text-slate-500">{{ formatDate(point.created) }}</div>
                </div>
                <span class="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600">
                  {{ restoreTypeLabel(point.type) }}
                </span>
              </div>
              <div class="mt-2 text-xs text-slate-500">{{ formatSize(point.size) }}</div>
            </button>
          </div>
          <div v-else class="mt-4 rounded-2xl border border-dashed border-slate-200 p-5 text-center text-sm text-slate-400">
            {{ t('backup.noRestorePointsHelp') }}
          </div>
        </section>
      </div>

      <div class="mt-4 grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <section class="rounded-3xl border border-stone-200 bg-stone-50/70 p-5">
          <div class="mb-3 flex items-center justify-between gap-3">
            <div>
              <h2 class="text-sm font-semibold text-stone-900">{{ t('backup.dataLocation') }}</h2>
              <p class="mt-1 text-xs text-stone-500">{{ t('backup.dataLocationHelp') }}</p>
            </div>
            <button
              type="button"
              class="rounded-xl bg-white px-3 py-2 text-xs font-semibold text-stone-700 ring-1 ring-stone-200 hover:bg-stone-50"
              @click="openPath(dataLocation?.data_dir)"
            >
              {{ t('backup.openDataDirectory') }}
            </button>
          </div>
          <div v-if="dataLocation" class="space-y-2 text-xs text-stone-600">
            <div class="rounded-2xl bg-white px-3 py-2">
              <div class="flex items-center justify-between gap-3">
                <div class="font-semibold text-stone-500">{{ t('backup.database') }}</div>
                <button class="text-[11px] font-semibold text-stone-500 hover:text-stone-900" @click="copyPath(dataLocation.database_path)">{{ t('backup.copy') }}</button>
              </div>
              <div class="mt-1 break-all font-mono text-[11px] text-stone-800">{{ dataLocation.database_path }}</div>
            </div>
            <div class="grid gap-2 md:grid-cols-2">
              <button
                type="button"
                class="rounded-2xl bg-white px-3 py-2 text-left ring-1 ring-stone-200 hover:bg-stone-50"
                @click="openPath(dataLocation.backup_dir)"
              >
                <div class="font-semibold text-stone-500">{{ t('backup.backupDirectory') }}</div>
                <div class="mt-1 break-all font-mono text-[11px] text-stone-700">{{ dataLocation.backup_dir }}</div>
              </button>
              <button
                type="button"
                class="rounded-2xl bg-white px-3 py-2 text-left ring-1 ring-stone-200 hover:bg-stone-50"
                @click="openPath(dataLocation.checkpoint_dir)"
              >
                <div class="font-semibold text-stone-500">{{ t('backup.checkpointDirectory') }}</div>
                <div class="mt-1 break-all font-mono text-[11px] text-stone-700">{{ dataLocation.checkpoint_dir }}</div>
              </button>
            </div>
          </div>
          <div v-else class="rounded-xl bg-white px-3 py-3 text-sm text-stone-500">
            {{ t('backup.dataLocationUnavailable') }}
          </div>
        </section>

        <section class="rounded-3xl border border-amber-100 bg-amber-50/60 p-5">
          <h2 class="text-sm font-semibold text-stone-900">{{ t('backup.exportShortcuts') }}</h2>
          <p class="mt-1 text-xs leading-5 text-stone-600">{{ t('backup.exportShortcutsHelp') }}</p>
          <div class="mt-3 space-y-3">
            <div>
              <div class="mb-1 text-xs font-semibold text-stone-500">{{ t('backup.recentArticle') }}</div>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="format in articleExportFormats"
                  :key="`article-${format}`"
                  type="button"
                  class="rounded-xl bg-white px-3 py-2 text-xs font-semibold uppercase text-stone-700 ring-1 ring-amber-100 hover:bg-amber-50 disabled:opacity-40"
                  :disabled="Boolean(exportShortcutBusy)"
                  @click="exportLastArticle(format)"
                >
                  {{ exportShortcutBusy === `article-${format}` ? '...' : format }}
                </button>
              </div>
            </div>
            <div>
              <div class="mb-1 text-xs font-semibold text-stone-500">{{ t('backup.recentCollection') }}</div>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="format in collectionExportFormats"
                  :key="`collection-${format}`"
                  type="button"
                  class="rounded-xl bg-white px-3 py-2 text-xs font-semibold uppercase text-stone-700 ring-1 ring-amber-100 hover:bg-amber-50 disabled:opacity-40"
                  :disabled="Boolean(exportShortcutBusy)"
                  @click="exportLastCollection(format)"
                >
                  {{ exportShortcutBusy === `collection-${format}` ? '...' : format }}
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>

      <div v-if="error" class="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
        {{ error }}
      </div>
      <div v-if="notice" class="mt-4 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800">
        {{ notice }}
      </div>
    </div>

    <div class="flex-1 overflow-y-auto p-6">
      <div class="grid grid-cols-2 gap-6">
        <section>
          <h2 class="mb-3 text-lg font-bold text-gray-900">{{ t('backup.checkpointsTitle') }}</h2>
          <div class="space-y-2">
            <article
              v-for="cp in checkpoints"
              :key="cp.path"
              @contextmenu="openDeleteContextMenu($event, { path: cp.path, name: cp.name, type: 'checkpoint' })"
              class="rounded-lg border border-gray-200 bg-white p-4 transition-shadow hover:shadow-md"
            >
              <div class="flex items-start justify-between gap-4">
                <div class="min-w-0 flex-1">
                  <div class="font-semibold text-gray-900">{{ cp.name }}</div>
                  <div v-if="cp.description" class="mt-1 text-sm text-gray-600">{{ cp.description }}</div>
                  <div class="mt-2 flex items-center gap-4 text-xs text-gray-500">
                    <span>{{ formatDate(cp.created) }}</span>
                    <span>{{ formatSize(cp.size) }}</span>
                  </div>
                </div>
                <div class="flex gap-2">
                  <button @click="confirmRestore(cp.path, cp.name)" class="rounded bg-blue-600 px-3 py-1 text-sm text-white transition-colors hover:bg-blue-700">
                    {{ t('backup.restore') }}
                  </button>
                  <button @click="confirmDelete(cp.path, cp.name, 'checkpoint')" class="rounded bg-red-600 px-3 py-1 text-sm text-white transition-colors hover:bg-red-700">
                    {{ t('backup.delete') }}
                  </button>
                </div>
              </div>
            </article>
            <div v-if="!checkpoints.length" class="py-8 text-center text-gray-600">
              {{ t('backup.noCheckpoints') }}
            </div>
          </div>
        </section>

        <section>
          <h2 class="mb-3 text-lg font-bold text-gray-900">{{ t('backup.backupsTitle') }}</h2>
          <div class="space-y-2">
            <article
              v-for="backup in backups"
              :key="backup.path"
              @contextmenu="openDeleteContextMenu($event, { path: backup.path, name: backup.name, type: 'backup' })"
              class="rounded-lg border border-gray-200 bg-white p-4 transition-shadow hover:shadow-md"
            >
              <div class="flex items-start justify-between gap-4">
                <div class="min-w-0 flex-1">
                  <div class="truncate text-sm font-semibold text-gray-900">{{ backup.name }}</div>
                  <div class="mt-2 flex items-center gap-4 text-xs text-gray-500">
                    <span>{{ formatDate(backup.created) }}</span>
                    <span>{{ formatSize(backup.size) }}</span>
                  </div>
                </div>
                <div class="flex gap-2">
                  <button @click="confirmRestore(backup.path, backup.name)" class="rounded bg-blue-600 px-3 py-1 text-sm text-white transition-colors hover:bg-blue-700">
                    {{ t('backup.restore') }}
                  </button>
                  <button @click="confirmDelete(backup.path, backup.name, 'backup')" class="rounded bg-red-600 px-3 py-1 text-sm text-white transition-colors hover:bg-red-700">
                    {{ t('backup.delete') }}
                  </button>
                </div>
              </div>
            </article>
            <div v-if="!backups.length" class="py-8 text-center text-gray-600">
              {{ t('backup.noBackups') }}
            </div>
          </div>
        </section>
      </div>
    </div>

    <div v-if="showCheckpointDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div class="w-96 rounded-lg bg-white p-6 shadow-xl">
        <h3 class="mb-4 text-xl font-bold">{{ t('backup.createCheckpoint') }}</h3>
        <div class="space-y-4">
          <div>
            <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('backup.checkpointName') }}</label>
            <input
              v-model="checkpointName"
              type="text"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-green-500"
              :placeholder="t('backup.checkpointNamePlaceholder')"
            />
          </div>
          <div>
            <label class="mb-2 block text-sm font-semibold text-gray-700">{{ t('backup.checkpointDescription') }}</label>
            <textarea
              v-model="checkpointDescription"
              class="w-full resize-none rounded-lg border border-gray-300 px-3 py-2 outline-none focus:ring-2 focus:ring-green-500"
              rows="3"
              :placeholder="t('backup.checkpointDescriptionPlaceholder')"
            />
          </div>
        </div>
        <div class="mt-6 flex gap-3">
          <button @click="showCheckpointDialog = false" class="flex-1 rounded-lg bg-gray-200 px-4 py-2 font-semibold text-gray-800 transition-colors hover:bg-gray-300">
            {{ t('common.cancel') }}
          </button>
          <button
            @click="createCheckpoint"
            :disabled="!checkpointName.trim() || creatingCheckpoint"
            class="flex-1 rounded-lg bg-green-600 px-4 py-2 font-semibold text-white transition-colors hover:bg-green-700 disabled:bg-gray-400"
          >
            {{ creatingCheckpoint ? t('backup.creatingCheckpoint') : t('common.create') }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showConfirmDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div class="w-96 rounded-lg bg-white p-6 shadow-xl">
        <h3 class="mb-4 text-xl font-bold">{{ t('backup.confirmAction') }}</h3>
        <p class="mb-6 text-gray-700">{{ confirmMessage }}</p>
        <div class="flex gap-3">
          <button @click="showConfirmDialog = false" class="flex-1 rounded-lg bg-gray-200 px-4 py-2 font-semibold text-gray-800 transition-colors hover:bg-gray-300">
            {{ t('common.cancel') }}
          </button>
          <button @click="confirmAction()" class="flex-1 rounded-lg bg-red-600 px-4 py-2 font-semibold text-white transition-colors hover:bg-red-700">
            {{ t('common.confirm') }}
          </button>
        </div>
      </div>
    </div>
    <ContextMenu
      :open="deleteContextMenuOpen"
      :x="deleteContextMenuX"
      :y="deleteContextMenuY"
      :items="[{ key: 'delete', label: t('backup.delete'), danger: true }]"
      @close="closeDeleteContextMenu"
      @select="handleDeleteContextMenuSelect"
    />
  </div>
</template>
