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
  return error instanceof Error ? error.message : String(error)
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

  try {
    const { invoke } = await import('@tauri-apps/api/core')
    const value = await invoke<string | null>('get_api_base_url')
    if (value) {
      cachedApiBaseUrl = value
      setApiBaseOnWindow(value)
      return value
    }
  } catch {
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
