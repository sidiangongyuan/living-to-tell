import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiFetch, BackendUnavailableError, clearCachedApiBaseUrl, errorMessage, handleResponse, HttpError, isHttpStatus } from './base'

const invokeMock = vi.fn()

vi.mock('@tauri-apps/api/core', () => ({
  invoke: invokeMock,
}))

afterEach(() => {
  clearCachedApiBaseUrl()
  invokeMock.mockReset()
  vi.unstubAllGlobals()
})

describe('api base errors', () => {
  it('preserves HTTP status for failed responses', async () => {
    const response = new Response(JSON.stringify({ detail: 'Not Found' }), {
      status: 404,
      statusText: 'Not Found',
      headers: { 'Content-Type': 'application/json' },
    })

    await expect(handleResponse(response)).rejects.toMatchObject({
      name: 'HttpError',
      status: 404,
      message: 'Not Found',
    })
  })

  it('recognizes structured HTTP status errors', () => {
    const error = new HttpError(404, 'Not Found', 'Not Found')

    expect(isHttpStatus(error, 404)).toBe(true)
    expect(isHttpStatus(error, 500)).toBe(false)
    expect(isHttpStatus(new Error('Not Found'), 404)).toBe(false)
  })

  it('sanitizes raw technical errors for user-facing messages', () => {
    expect(errorMessage(new HttpError(404, 'Not Found', 'Not Found'))).toContain('请求的内容不存在')
    expect(errorMessage(new HttpError(404, 'Not Found', 'Collection not found'))).toContain('当前作品集已不存在')
    expect(errorMessage(new Error('Unknown agent memory section'))).toContain('项目圣经栏目')
    expect(errorMessage(new TypeError('Failed to fetch'))).toContain('后台服务正在启动或连接中')
    expect(errorMessage(new Error('<!doctype html><html><title>403</title></html>'))).not.toContain('<html')
    expect(errorMessage(new Error('Traceback (most recent call last): boom'))).not.toContain('Traceback')
    const fakeKey = `sk-${'1234567890abcdefghijkl'}`
    expect(errorMessage(new Error(`provider rejected ${fakeKey}`))).toBe('provider rejected sk-***')
  })

  it('refreshes the backend URL and retries once after a network failure', async () => {
    vi.stubGlobal('window', { __WRITER_API_BASE__: 'http://stale.example' })
    invokeMock.mockResolvedValue('http://fresh.example')
    const fetchMock = vi.fn()
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true })))
    vi.stubGlobal('fetch', fetchMock)

    const response = await apiFetch('/health')

    expect(response.ok).toBe(true)
    expect(fetchMock).toHaveBeenNthCalledWith(1, 'http://stale.example/health', undefined)
    expect(fetchMock).toHaveBeenNthCalledWith(2, 'http://fresh.example/health', undefined)
    expect(invokeMock).toHaveBeenCalledWith('get_api_base_url')
  })

  it('throws a user-facing backend unavailable error after retry failure', async () => {
    vi.stubGlobal('window', { __WRITER_API_BASE__: 'http://stale.example' })
    invokeMock.mockResolvedValue('http://fresh.example')
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    await expect(apiFetch('/health')).rejects.toBeInstanceOf(BackendUnavailableError)
    await expect(apiFetch('/health')).rejects.toThrow('后台服务正在启动或连接中')
  })

  it('does not fall back to port 8000 inside the Tauri runtime', async () => {
    vi.stubGlobal('window', { __TAURI_INTERNALS__: {} })
    invokeMock.mockResolvedValue(null)
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiFetch('/health')).rejects.toBeInstanceOf(BackendUnavailableError)
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
