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

export interface ApiError {
  detail: string
}

export async function getApiBaseUrl(): Promise<string> {
  if (cachedApiBaseUrl) return cachedApiBaseUrl
  if (window.__WRITER_API_BASE__) {
    cachedApiBaseUrl = window.__WRITER_API_BASE__
    return cachedApiBaseUrl
  }

  try {
    const { invoke } = await import('@tauri-apps/api/core')
    const value = await invoke<string | null>('get_api_base_url')
    if (value) {
      cachedApiBaseUrl = value
      window.__WRITER_API_BASE__ = value
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
  return fetch(`${base}${normalizedPath}`, init)
}

export async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error: ApiError = await response.json().catch(() => ({
      detail: `HTTP ${response.status}: ${response.statusText}`,
    }))
    throw new Error(error.detail)
  }
  if (response.status === 204) {
    return null as T
  }
  return response.json()
}
