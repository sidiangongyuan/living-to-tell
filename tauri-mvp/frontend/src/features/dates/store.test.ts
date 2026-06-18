import { afterEach, describe, expect, it, vi } from 'vitest'
import { cacheDailyQuote, DAILY_QUOTE_CACHE_KEY } from './store'

describe('daily quote startup cache', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('stores successful daily quotes for the lightweight startup shell', () => {
    const setItem = vi.fn()
    vi.stubGlobal('localStorage', { setItem })

    cacheDailyQuote({
      id: 'quote-1',
      reference_id: 'ref-1',
      text: '  你必须先相信某种回声。  ',
      source_title: '夜航西飞',
      source_author: '柏瑞尔',
    }, '2026-06-18')

    expect(setItem).toHaveBeenCalledOnce()
    expect(setItem.mock.calls[0][0]).toBe(DAILY_QUOTE_CACHE_KEY)
    expect(JSON.parse(setItem.mock.calls[0][1])).toMatchObject({
      text: '你必须先相信某种回声。',
      source_title: '夜航西飞',
      source_author: '柏瑞尔',
      date: '2026-06-18',
    })
  })

  it('does not cache empty quote data', () => {
    const setItem = vi.fn()
    vi.stubGlobal('localStorage', { setItem })

    cacheDailyQuote(null, '2026-06-18')
    cacheDailyQuote({
      id: 'quote-1',
      reference_id: 'ref-1',
      text: '   ',
      source_title: '',
      source_author: '',
    }, '2026-06-18')

    expect(setItem).not.toHaveBeenCalled()
  })
})
