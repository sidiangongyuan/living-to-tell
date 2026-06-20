import { describe, expect, it } from 'vitest'
import {
  addUniqueMotifName,
  buildMotifSelectionSnapshot,
  findMotifTextPosition,
  readMotifJumpSnapshot,
  resolveMotifExcerptRange,
} from './selection'

describe('motif selection helpers', () => {
  it('builds a trimmed excerpt snapshot with original positions and context', () => {
    const excerpt = '玫瑰在夜里像血一样醒着。'
    const text = `前文。  ${excerpt}  后文。`
    const snapshot = buildMotifSelectionSnapshot(text, 3, text.length - 3, 3)
    const expectedStart = text.indexOf(excerpt)
    const expectedEnd = expectedStart + excerpt.length

    expect(snapshot).toEqual({
      text: excerpt,
      start: expectedStart,
      end: expectedEnd,
      beforeContext: text.slice(expectedStart - 3, expectedStart),
      afterContext: text.slice(expectedEnd, expectedEnd + 3),
    })
  })

  it('deduplicates motif names case-insensitively', () => {
    expect(addUniqueMotifName(['Rose'], ' rose ')).toEqual(['Rose'])
    expect(addUniqueMotifName(['Rose'], 'Blood')).toEqual(['Rose', 'Blood'])
  })

  it('reads jump snapshots defensively', () => {
    const values = new Map<string, string>()
    const storage = {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => {
        values.set(key, value)
      },
    } as unknown as Storage
    storage.setItem('motif:lastJump', JSON.stringify({
      excerptId: 'excerpt-a',
      text: '门后有雨。',
      start: 4,
      end: 9,
    }))

    expect(readMotifJumpSnapshot(storage)).toEqual({
      excerptId: 'excerpt-a',
      text: '门后有雨。',
      start: 4,
      end: 9,
    })
  })

  it('finds excerpt text after whitespace changes', () => {
    const found = findMotifTextPosition('玫瑰在夜里\n像血一样醒着。', '玫瑰在夜里 像血一样醒着。')

    expect(found).toEqual({ start: 0, end: '玫瑰在夜里\n像血一样醒着。'.length })
  })

  it('resolves motif excerpt ranges from saved positions or text fallback', () => {
    const source = '前文。玫瑰在夜里\n像血一样醒着。后文。'
    const start = source.indexOf('玫瑰')
    const end = source.indexOf('后文')

    expect(resolveMotifExcerptRange(source, {
      excerpt_text: '玫瑰在夜里\n像血一样醒着。',
      selection_start: start,
      selection_end: end,
    })).toEqual({ status: 'matched', start, end })

    expect(resolveMotifExcerptRange(source, {
      excerpt_text: '玫瑰在夜里 像血一样醒着。',
      selection_start: 0,
      selection_end: 3,
    })).toEqual({ status: 'moved', start, end })

    expect(resolveMotifExcerptRange(source, {
      excerpt_text: '不存在的句子。',
      selection_start: 0,
      selection_end: 3,
    })).toEqual({ status: 'missing', start: null, end: null })
  })
})
