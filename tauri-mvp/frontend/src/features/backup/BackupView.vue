<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from '../../i18n'
import { backupApi, type BackupInfo, type BackupStats, type CheckpointInfo } from './api'
import { settingsApi, type DataLocationInfo } from '../../api/settings'
import { articlesApi, type ArticleExportFormat } from '../../api/articles'
import { collectionsApi, type CollectionExportFormat } from '../../api/collections'
import { saveBlobWithDialog } from '../../utils/exportFile'
import { LAST_SELECTED_ARTICLE_KEY } from '../articles/editorPosition'
import ContextMenu from '../../components/ContextMenu.vue'

const LAST_SELECTED_COLLECTION_KEY = 'living_to_tell_last_selected_collection_id'

const { t } = useI18n()

const backups = ref<BackupInfo[]>([])
const checkpoints = ref<CheckpointInfo[]>([])
const stats = ref<BackupStats | null>(null)
const dataLocation = ref<DataLocationInfo | null>(null)
const loading = ref(false)
const error = ref('')
const notice = ref('')
const exportShortcutBusy = ref('')
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
  } catch (e) {
    error.value = e instanceof Error ? e.message : t('common.error')
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
    error.value = e instanceof Error ? e.message : t('common.error')
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
    error.value = e instanceof Error ? e.message : t('common.error')
  } finally {
    creatingCheckpoint.value = false
  }
}

function confirmRestore(path: string, name: string) {
  confirmMessage.value = t('backup.restoreConfirm', { name })
  confirmAction.value = () => restore(path)
  showConfirmDialog.value = true
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
    error.value = e instanceof Error ? e.message : t('common.error')
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
    error.value = e instanceof Error ? e.message : t('common.error')
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

function safeFilename(title: string, format: string): string {
  const safe = (title || 'export').replace(/[<>:"/\\|?*]/g, '').trim() || 'export'
  return `${safe}.${format}`
}

async function openPath(path: string | null | undefined) {
  if (!path) {
    notice.value = ''
    error.value = '路径不存在，无法打开。'
    return
  }
  error.value = ''
  try {
    const { invoke } = await import('@tauri-apps/api/core')
    await invoke('open_path', { path })
  } catch (e) {
    error.value = e instanceof Error ? `无法打开目录：${e.message}` : `无法打开目录：${String(e)}`
  }
}

async function exportLastArticle(format: ArticleExportFormat) {
  const articleId = localStorage.getItem(LAST_SELECTED_ARTICLE_KEY)
  if (!articleId) {
    notice.value = ''
    error.value = '还没有最近使用的文章。请先在文章页选中一篇文章，再回到这里导出。'
    return
  }
  exportShortcutBusy.value = `article-${format}`
  error.value = ''
  notice.value = ''
  try {
    const article = await articlesApi.get(articleId)
    const blob = await articlesApi.exportArticle(articleId, format)
    const result = await saveBlobWithDialog(blob, safeFilename(article.title || 'article', format), format)
    notice.value = result.status === 'cancelled' ? '已取消文章导出。' : '已导出最近文章。'
  } catch (e) {
    error.value = e instanceof Error ? `导出最近文章失败：${e.message}` : `导出最近文章失败：${String(e)}`
  } finally {
    exportShortcutBusy.value = ''
  }
}

async function exportLastCollection(format: CollectionExportFormat) {
  const collectionId = localStorage.getItem(LAST_SELECTED_COLLECTION_KEY)
  if (!collectionId) {
    notice.value = ''
    error.value = '还没有最近使用的作品集。请先在作品集页选中一个作品集，再回到这里导出。'
    return
  }
  exportShortcutBusy.value = `collection-${format}`
  error.value = ''
  notice.value = ''
  try {
    const collection = await collectionsApi.getCollection(collectionId)
    const blob = await collectionsApi.exportCollection(collectionId, format)
    const result = await saveBlobWithDialog(blob, safeFilename(collection.title || 'collection', format), format)
    notice.value = result.status === 'cancelled' ? '已取消作品集导出。' : '已导出最近作品集。'
  } catch (e) {
    error.value = e instanceof Error ? `导出最近作品集失败：${e.message}` : `导出最近作品集失败：${String(e)}`
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
            class="rounded-lg bg-green-600 px-4 py-2 font-semibold text-white transition-colors hover:bg-green-700"
          >
            {{ t('backup.createCheckpoint') }}
          </button>
          <button
            @click="createBackup"
            :disabled="loading"
            class="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white transition-colors hover:bg-blue-700 disabled:bg-gray-400"
          >
            {{ loading ? t('backup.creatingBackup') : t('backup.createBackup') }}
          </button>
        </div>
      </div>

      <div v-if="stats" class="mt-4 grid grid-cols-4 gap-4">
        <div class="rounded-lg bg-blue-50 p-3">
          <div class="text-sm font-semibold text-blue-600">{{ t('backup.autoBackups') }}</div>
          <div class="text-2xl font-bold text-blue-900">{{ stats.backup_count }}</div>
        </div>
        <div class="rounded-lg bg-green-50 p-3">
          <div class="text-sm font-semibold text-green-600">{{ t('backup.checkpoints') }}</div>
          <div class="text-2xl font-bold text-green-900">{{ stats.checkpoint_count }}</div>
        </div>
        <div class="rounded-lg bg-purple-50 p-3">
          <div class="text-sm font-semibold text-purple-600">{{ t('backup.backupSize') }}</div>
          <div class="text-2xl font-bold text-purple-900">{{ formatSize(stats.total_backup_size) }}</div>
        </div>
        <div class="rounded-lg bg-orange-50 p-3">
          <div class="text-sm font-semibold text-orange-600">{{ t('backup.totalSize') }}</div>
          <div class="text-2xl font-bold text-orange-900">{{ formatSize(stats.total_size) }}</div>
        </div>
      </div>

      <div class="mt-4 grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <section class="rounded-2xl border border-stone-200 bg-stone-50/70 p-4">
          <div class="mb-3 flex items-center justify-between gap-3">
            <div>
              <h2 class="text-sm font-semibold text-stone-900">数据位置</h2>
              <p class="mt-1 text-xs text-stone-500">这里显示真实数据库、备份和检查点目录；打开目录不会修改数据。</p>
            </div>
            <button
              type="button"
              class="rounded-xl bg-white px-3 py-2 text-xs font-semibold text-stone-700 ring-1 ring-stone-200 hover:bg-stone-50"
              @click="openPath(dataLocation?.data_dir)"
            >
              打开数据目录
            </button>
          </div>
          <div v-if="dataLocation" class="space-y-2 text-xs text-stone-600">
            <div class="rounded-xl bg-white px-3 py-2">
              <div class="font-semibold text-stone-500">数据库</div>
              <div class="mt-1 break-all font-mono text-[11px] text-stone-800">{{ dataLocation.database_path }}</div>
            </div>
            <div class="grid gap-2 md:grid-cols-2">
              <button
                type="button"
                class="rounded-xl bg-white px-3 py-2 text-left ring-1 ring-stone-200 hover:bg-stone-50"
                @click="openPath(dataLocation.backup_dir)"
              >
                <div class="font-semibold text-stone-500">备份目录</div>
                <div class="mt-1 break-all font-mono text-[11px] text-stone-700">{{ dataLocation.backup_dir }}</div>
              </button>
              <button
                type="button"
                class="rounded-xl bg-white px-3 py-2 text-left ring-1 ring-stone-200 hover:bg-stone-50"
                @click="openPath(dataLocation.checkpoint_dir)"
              >
                <div class="font-semibold text-stone-500">检查点目录</div>
                <div class="mt-1 break-all font-mono text-[11px] text-stone-700">{{ dataLocation.checkpoint_dir }}</div>
              </button>
            </div>
          </div>
          <div v-else class="rounded-xl bg-white px-3 py-3 text-sm text-stone-500">
            当前后台暂时无法读取数据路径；备份和检查点功能仍可按列表使用。
          </div>
        </section>

        <section class="rounded-2xl border border-amber-100 bg-amber-50/60 p-4">
          <h2 class="text-sm font-semibold text-stone-900">导出快捷操作</h2>
          <p class="mt-1 text-xs leading-5 text-stone-600">基于最近打开的文章或作品集。没有上下文时会提示你先去对应页面选择。</p>
          <div class="mt-3 space-y-3">
            <div>
              <div class="mb-1 text-xs font-semibold text-stone-500">最近文章</div>
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
              <div class="mb-1 text-xs font-semibold text-stone-500">最近作品集</div>
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
            <div v-if="!checkpoints.length" class="py-8 text-center text-gray-400">
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
            <div v-if="!backups.length" class="py-8 text-center text-gray-400">
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
