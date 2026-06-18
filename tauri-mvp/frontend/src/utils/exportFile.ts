export type ExportSaveStatus = 'saved' | 'cancelled' | 'downloaded'

export interface ExportSaveResult {
  status: ExportSaveStatus
  path?: string
}

export type NativeInvoke = <T>(command: string, args?: Record<string, unknown>) => Promise<T>

export interface SaveBlobOptions {
  invoke?: NativeInvoke
  forceNative?: boolean
}

function hasTauriRuntime(): boolean {
  if (typeof window === 'undefined') return false
  const runtimeWindow = window as Window & {
    __TAURI__?: unknown
    __TAURI_INTERNALS__?: unknown
  }
  return Boolean(runtimeWindow.__TAURI__ || runtimeWindow.__TAURI_INTERNALS__)
}

async function invokeNative<T>(command: string, args?: Record<string, unknown>): Promise<T> {
  const { invoke } = await import('@tauri-apps/api/core')
  return invoke<T>(command, args)
}

function downloadInBrowser(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

async function blobToBytes(blob: Blob): Promise<number[]> {
  return Array.from(new Uint8Array(await blob.arrayBuffer()))
}

export async function saveBlobWithDialog(
  blob: Blob,
  filename: string,
  format: string,
  options: SaveBlobOptions = {}
): Promise<ExportSaveResult> {
  const shouldUseNative = options.forceNative === true || Boolean(options.invoke) || hasTauriRuntime()
  if (!shouldUseNative) {
    downloadInBrowser(blob, filename)
    return { status: 'downloaded' }
  }

  const invoke = options.invoke ?? invokeNative
  const path = await invoke<string | null>('choose_export_file', {
    defaultFilename: filename,
    format,
  })
  if (!path) {
    return { status: 'cancelled' }
  }

  await invoke<void>('write_export_file', {
    path,
    bytes: await blobToBytes(blob),
  })
  return { status: 'saved', path }
}
