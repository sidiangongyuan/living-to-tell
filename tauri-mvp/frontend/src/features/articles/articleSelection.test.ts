import { describe, expect, it } from 'vitest'
import { mapEditorSelectionToArticleBody } from './articleSelection'

describe('article editor selection mapping', () => {
  it('keeps offsets unchanged when the editor shows the full article body', () => {
    const body = '上一段。\n\n父亲不再灵敏。'
    const start = body.indexOf('父亲')

    expect(mapEditorSelectionToArticleBody(body, body, start, body.length)).toEqual({
      start,
      end: body.length,
      text: '父亲不再灵敏。',
    })
  })

  it('adds the hidden epigraph prefix before opening AI Edit', () => {
    const editorBody = '上一段。\n\n父亲不再灵敏。'
    const articleBody = `这是一段题记。\n——《测试集》 测试作者\n\n${editorBody}`
    const editorStart = editorBody.indexOf('父亲')
    const expectedStart = articleBody.indexOf('父亲')

    expect(mapEditorSelectionToArticleBody(editorBody, articleBody, editorStart, editorBody.length)).toEqual({
      start: expectedStart,
      end: articleBody.length,
      text: '父亲不再灵敏。',
    })
  })

  it('preserves browser UTF-16 offsets when text contains emoji', () => {
    const editorBody = '开头😀\n父亲不再灵敏。'
    const articleBody = `题记。\n——《测试集》 作者\n\n${editorBody}`
    const editorStart = editorBody.indexOf('父亲')
    const mapped = mapEditorSelectionToArticleBody(editorBody, articleBody, editorStart, editorBody.length)

    expect(mapped?.start).toBe(articleBody.indexOf('父亲'))
    expect(mapped?.text).toBe('父亲不再灵敏。')
  })

  it('rejects collapsed selections and bodies that no longer match', () => {
    expect(mapEditorSelectionToArticleBody('正文', '正文', 1, 1)).toBeNull()
    expect(mapEditorSelectionToArticleBody('当前正文', '已经变化的正文', 0, 2)).toBeNull()
  })
})
