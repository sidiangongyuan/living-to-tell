import { describe, expect, it } from 'vitest'
import { utf16OffsetToCodePointOffset } from './selectionOffsets'

describe('article AI selection offsets', () => {
  it('converts browser UTF-16 offsets to Python-compatible code point offsets', () => {
    const text = '开头😀选中内容'
    const browserStart = text.indexOf('选')
    const browserEnd = text.length

    expect(browserStart).toBe(4)
    expect(utf16OffsetToCodePointOffset(text, browserStart)).toBe(3)
    expect(utf16OffsetToCodePointOffset(text, browserEnd)).toBe(Array.from(text).length)
  })

  it('clamps invalid offsets to the text bounds', () => {
    expect(utf16OffsetToCodePointOffset('正文', -10)).toBe(0)
    expect(utf16OffsetToCodePointOffset('正文', 99)).toBe(2)
  })
})
