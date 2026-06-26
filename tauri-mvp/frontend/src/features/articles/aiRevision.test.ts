import { describe, expect, it } from 'vitest'
import {
  applyRevisionToBody,
  buildRevisionTaskRequest,
  paragraphRangeAt,
  resolveRevisionRange,
} from './aiRevision'

describe('aiRevision helpers', () => {
  it('resolves current paragraph without requiring a text selection', () => {
    const body = '第一段。\n第二段需要修订。\n第三段。'
    const range = paragraphRangeAt(body, body.indexOf('需要'))

    expect(range.scope).toBe('paragraph')
    expect(range.text).toBe('第二段需要修订。')
    expect(applyRevisionToBody(body, range, '第二段已经修订。')).toBe('第一段。\n第二段已经修订。\n第三段。')
  })

  it('keeps explicit selection scope when text is selected', () => {
    const body = '开头。选中的句子。结尾。'
    const start = body.indexOf('选中')
    const end = body.indexOf('结尾')
    const range = resolveRevisionRange(body, 'selection', start, end)

    expect(range).toMatchObject({
      scope: 'selection',
      text: '选中的句子。',
    })
  })

  it('builds a shared AI task request with attachments and safe write-back instructions', () => {
    const request = buildRevisionTaskRequest({
      revisionTask: 'compress',
      text: '这是一段需要压缩的文字。',
      articleId: 'entry-1',
      scope: 'selection',
      extraInstructions: '保留第一人称。',
      attachments: [
        { kind: 'writing_note', ref_id: 'note-1', name: '便签', body: '不要改结尾。' },
      ],
    })

    expect(request.task_type).toBe('rewrite')
    expect(request.target_kind).toBe('selection')
    expect(request.target_ref_id).toBe('entry-1')
    expect(request.attachments).toHaveLength(1)
    expect(request.extra_instructions).toContain('只返回修订后的正文')
    expect(request.extra_instructions).toContain('保留第一人称')
  })
})
