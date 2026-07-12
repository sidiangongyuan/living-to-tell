/**
 * API client base configuration with dynamic backend URL.
 *
 * Release builds launch the Python backend as a Tauri sidecar on a free port.
 * API calls resolve that port lazily through a Tauri command. Browser/dev mode
 * still falls back to VITE_API_BASE_URL or 127.0.0.1:8000.
 */

declare global {
  interface Window {
    __WRITER_API_BASE__?: string
  }
}

export const FALLBACK_API_BASE_URL =
  String(import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000')

let cachedApiBaseUrl: string | null = null
const BACKEND_UNAVAILABLE_MESSAGE = '后台服务正在启动或连接中，请稍后重试；如果持续出现，请重启应用。'

export interface ApiError {
  detail: string
}

export class HttpError extends Error {
  status: number
  statusText: string
  detail: string

  constructor(status: number, statusText: string, detail: string) {
    super(detail)
    this.name = 'HttpError'
    this.status = status
    this.statusText = statusText
    this.detail = detail
  }
}

export class BackendUnavailableError extends Error {
  cause?: unknown

  constructor(cause?: unknown) {
    super(BACKEND_UNAVAILABLE_MESSAGE)
    this.name = 'BackendUnavailableError'
    this.cause = cause
  }
}

export function isHttpStatus(error: unknown, status: number): boolean {
  return error instanceof HttpError && error.status === status
}

export function errorMessage(error: unknown): string {
  const raw = (error instanceof Error ? error.message : String(error ?? '')).trim()
  if (!raw) return '操作失败，请稍后重试。'
  const lowered = raw.toLowerCase()
  if (lowered.includes('<!doctype html') || lowered.includes('<html')) {
    return '后台或 AI 服务返回了网页错误页，请检查服务状态、接口地址或稍后重试。'
  }
  if (lowered.includes('traceback') || lowered.includes('stack trace')) {
    return '后台返回了异常信息，请重试；如果持续出现，请保留操作步骤用于排查。'
  }
  if (lowered.includes('missing_var') || lowered.includes('environment variable') && lowered.includes('empty')) {
    return '未找到所需的本机 API Key，请到设置中重新保存密钥。'
  }
  if (lowered.includes('missing_login')) {
    return '未找到可复用的本机登录，请先在对应命令行工具中登录。'
  }
  if (lowered.includes('auth_list_timeout')) {
    return '读取本机登录状态超时，请确认对应命令行工具可以正常启动。'
  }
  if (/\b401\b/.test(lowered) || lowered.includes('unauthorized')) {
    return '认证失败，请检查 API Key、账号状态和接口地址。'
  }
  if (/\b403\b/.test(lowered) || lowered.includes('forbidden')) {
    return '服务拒绝了请求，请检查密钥权限、模型权限和接口协议。'
  }
  if (/\b429\b/.test(lowered) || lowered.includes('rate limit')) {
    return '请求过于频繁或额度不足，请稍后重试并检查账户额度。'
  }
  if (lowered.includes('timeout') || lowered.includes('timed out')) {
    return '请求超时。若这是 AI 请求，远端仍可能继续生成并计费，请先检查服务商记录再决定是否重试。'
  }
  if (lowered === 'not found' || lowered === 'http 404: not found') {
    return '请求的内容不存在或已被刷新，请返回后重试。'
  }
  if (lowered.startsWith('collection not found')) {
    return '当前作品集已不存在，请刷新后重新选择。'
  }
  if (lowered.includes('unknown agent memory section')) {
    return '无法识别这条提案要更新的项目圣经栏目，请拒绝后重新生成。'
  }
  if (lowered === 'failed to fetch') {
    return BACKEND_UNAVAILABLE_MESSAGE
  }
  return raw
    .replace(/sk-[A-Za-z0-9]{12,}/g, 'sk-***')
    .replace(/[A-Z]:\\Users\\[^\\\s]+\\[^\s"']+/gi, '[本机路径]')
}

function apiBaseFromWindow(): string | null {
  if (typeof window === 'undefined') return null
  return window.__WRITER_API_BASE__ ?? null
}

function setApiBaseOnWindow(value: string | null) {
  if (typeof window === 'undefined') return
  if (value) {
    window.__WRITER_API_BASE__ = value
  } else {
    delete window.__WRITER_API_BASE__
  }
}

function hasTauriRuntime(): boolean {
  if (typeof window === 'undefined') return false
  const runtimeWindow = window as Window & {
    __TAURI__?: unknown
    __TAURI_INTERNALS__?: unknown
  }
  return Boolean(runtimeWindow.__TAURI__ || runtimeWindow.__TAURI_INTERNALS__)
}

function isNetworkFailure(error: unknown): boolean {
  if (typeof DOMException !== 'undefined' && error instanceof DOMException && error.name === 'AbortError') return false
  if (error instanceof Error && error.name === 'AbortError') return false
  return error instanceof TypeError
}

export function clearCachedApiBaseUrl() {
  cachedApiBaseUrl = null
  setApiBaseOnWindow(null)
}

export async function getApiBaseUrl(forceRefresh = false): Promise<string> {
  if (forceRefresh) clearCachedApiBaseUrl()
  if (cachedApiBaseUrl) return cachedApiBaseUrl
  const windowBase = apiBaseFromWindow()
  if (windowBase) {
    cachedApiBaseUrl = windowBase
    return cachedApiBaseUrl
  }

  const runningInTauri = hasTauriRuntime()
  try {
    const { invoke } = await import('@tauri-apps/api/core')
    const value = await invoke<string | null>('get_api_base_url')
    if (value) {
      cachedApiBaseUrl = value
      setApiBaseOnWindow(value)
      return value
    }
    if (runningInTauri) throw new BackendUnavailableError()
  } catch (e) {
    if (runningInTauri) throw new BackendUnavailableError(e)
    // Browser/dev mode has no Tauri runtime.
  }

  cachedApiBaseUrl = String(FALLBACK_API_BASE_URL)
  return cachedApiBaseUrl
}

export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const base = await getApiBaseUrl()
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  try {
    return await fetch(`${base}${normalizedPath}`, init)
  } catch (error) {
    if (!isNetworkFailure(error)) throw error
    const refreshedBase = await getApiBaseUrl(true)
    try {
      return await fetch(`${refreshedBase}${normalizedPath}`, init)
    } catch (retryError) {
      if (isNetworkFailure(retryError)) {
        throw new BackendUnavailableError(retryError)
      }
      throw retryError
    }
  }
}

export async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error: ApiError = await response.json().catch(() => ({
      detail: `HTTP ${response.status}: ${response.statusText}`,
    }))
    throw new HttpError(response.status, response.statusText, error.detail)
  }
  if (response.status === 204) {
    return null as T
  }
  return response.json()
}
