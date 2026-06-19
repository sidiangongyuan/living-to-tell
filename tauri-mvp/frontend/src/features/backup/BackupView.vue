<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from '../../i18n'
import { backupApi, type BackupInfo, type BackupStats, type CheckpointInfo } from './api'

const { t } = useI18n()

const backups = ref<BackupInfo[]>([])
const checkpoints = ref<CheckpointInfo[]>([])
const stats = ref<BackupStats | null>(null)
const loading = ref(false)
const error = ref('')
const notice = ref('')

const showCheckpointDialog = ref(false)
const checkpointName = ref('')
const checkpointDescription = ref('')
const creatingCheckpoint = ref(false)

const showConfirmDialog = ref(false)
const confirmAction = ref<() => void>(() => {})
const confirmMessage = ref('')

onMounted(() => {
  loadData()
})

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [b, c, s] = await Promise.all([
      backupApi.listBackups(),
      backupApi.listCheckpoints(),
      backupApi.getStats(),
    ])
    backups.value = b
    checkpoints.value = c
    stats.value = s
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
  </div>
</template>
