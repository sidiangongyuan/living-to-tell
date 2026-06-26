import { describe, expect, it } from 'vitest'
import { buildParagraphDiff } from './versionDiff'

describe('buildParagraphDiff', () => {
  it('keeps equal paragraphs aligned and marks changes', () => {
    const rows = buildParagraphDiff('第一段。\n\n第二段新。\n\n第三段。', '第一段。\n\n第二段旧。\n\n第三段。')

    expect(rows).toEqual([
      { kind: 'equal', current: '第一段。', historical: '第一段。' },
      { kind: 'changed', current: '第二段新。', historical: '第二段旧。' },
      { kind: 'equal', current: '第三段。', historical: '第三段。' },
    ])
  })

  it('marks added and removed paragraphs without hard-coded content', () => {
    const rows = buildParagraphDiff('A\n\nB\n\nC', 'A\n\nC\n\nD')

    expect(rows.map((row) => row.kind)).toEqual(['equal', 'added', 'equal', 'removed'])
  })
})
