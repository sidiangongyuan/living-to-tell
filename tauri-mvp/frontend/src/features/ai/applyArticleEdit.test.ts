import { describe, expect, it } from 'vitest'
import { applyArticleBodyEdit, selectArticleBodyText } from './applyArticleEdit'

describe('applyArticleEdit', () => {
  it('replaces only the body selection when an epigraph exists', () => {
    const fullBody = '你必须先相信某种回声。\n——《夜航西飞》 柏瑞尔·马卡姆\n\n正文第一段。正文第二段。'
    const { bodyText } = selectArticleBodyText(fullBody)
    const start = bodyText.indexOf('正文第二段')

    const result = applyArticleBodyEdit(fullBody, start, start + '正文第二段'.length, '新的第二段', 'replace')

    expect(result.body).toContain('你必须先相信某种回声。')
    expect(result.body).toContain('——《夜航西飞》 柏瑞尔·马卡姆')
    expect(result.body).toContain('正文第一段。新的第二段。')
    expect(result.body).not.toContain('正文第二段')
    expect(result.selectionStart).toBe(start)
  })

  it('inserts after the selection with paragraph spacing', () => {
    const result = applyArticleBodyEdit('第一段。第二段。', 0, '第一段。'.length, '插入段。', 'insert_after')

    expect(result.body).toBe('第一段。\n\n插入段。\n\n第二段。')
    expect(result.selectionStart).toBe(6)
    expect(result.selectionEnd).toBe(10)
  })
})
