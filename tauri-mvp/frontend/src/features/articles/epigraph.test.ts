import { describe, expect, it } from 'vitest'
import { composeArticleBody, detectEpigraph } from './epigraph'

describe('article epigraph helpers', () => {
  it('preserves first body paragraph indentation when composing with an epigraph', () => {
    const body = '　　第一段。\n\n第二段。'

    expect(composeArticleBody({
      quote: '你必须先相信某种回声。',
      attribution: '《夜航西飞》 柏瑞尔·马卡姆',
      body,
      raw: '',
    }, body)).toBe('你必须先相信某种回声。\n——《夜航西飞》 柏瑞尔·马卡姆\n\n　　第一段。\n\n第二段。')
  })

  it('preserves first body paragraph indentation when detecting an existing epigraph', () => {
    const fullBody = '你必须先相信某种回声。\n——《夜航西飞》 柏瑞尔·马卡姆\n\n　　第一段。\n\n第二段。'
    const epigraph = detectEpigraph(fullBody)

    expect(epigraph?.body).toBe('　　第一段。\n\n第二段。')
  })
})
