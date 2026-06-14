/**
 * Backup API client
 */
import { apiFetch, handleResponse } from '../../api/base'

export interface BackupInfo {
  path: string
  name: string
  size: number
  created: string
}

export interface CheckpointInfo {
  path: string
  name: string
  description: string
  size: number
  created: string
}

export interface CheckpointCreate {
  name: string
  description?: string
}

export interface BackupStats {
  backup_count: number
  checkpoint_count: number
  total_backup_size: number
  total_checkpoint_size: number
  total_size: number
  backup_dir: string
  checkpoint_dir: string
}

export const backupApi = {
  async createBackup(): Promise<BackupInfo> {
    const res = await apiFetch('/api/backup/auto-backup', {
      method: 'POST',
    })
    return handleResponse(res)
  },

  async listBackups(): Promise<BackupInfo[]> {
    const res = await apiFetch('/api/backup/backups')
    return handleResponse(res)
  },

  async deleteBackup(path: string): Promise<void> {
    // Extract name from path
    const name = path.split(/[/\\]/).pop()?.replace('.sqlite3', '') || ''
    const res = await apiFetch(`/api/backup/backups/${encodeURIComponent(name)}`, {
      method: 'DELETE',
    })
    return handleResponse(res)
  },

  async createCheckpoint(data: CheckpointCreate): Promise<CheckpointInfo> {
    const res = await apiFetch('/api/backup/checkpoints', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async listCheckpoints(): Promise<CheckpointInfo[]> {
    const res = await apiFetch('/api/backup/checkpoints')
    return handleResponse(res)
  },

  async deleteCheckpoint(path: string): Promise<void> {
    // Extract name from path
    const name = path.split(/[/\\]/).pop()?.replace('.sqlite3', '') || ''
    const res = await apiFetch(`/api/backup/checkpoints/${encodeURIComponent(name)}`, {
      method: 'DELETE',
    })
    return handleResponse(res)
  },

  async restore(path: string): Promise<void> {
    const res = await apiFetch('/api/backup/restore', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ backup_path: path }),
    })
    return handleResponse(res)
  },

  async getStats(): Promise<BackupStats> {
    const res = await apiFetch('/api/backup/stats')
    return handleResponse(res)
  },
}
