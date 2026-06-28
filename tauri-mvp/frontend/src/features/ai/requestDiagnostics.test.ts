import { describe, expect, it } from 'vitest'
import {
  buildAiRequestDiagnostics,
  classifyAiRequestSize,
  estimateAiTokens,
} from './requestDiagnostics'

describe('AI request diagnostics', () => {
  it('estimates mixed Chinese and English token risk without returning zero for text', () => {
    expect(estimateAiTokens('裙摆带起一阵风。')).toBeGreaterThan(1)
    expect(estimateAiTokens('A short English sentence.')).toBeGreaterThan(3)
    expect(estimateAiTokens('   ')).toBe(0)
  })

  it('classifies long text by character count and selected model count', () => {
    expect(classifyAiRequestSize('短句。', 1)).toBe('normal')
    expect(classifyAiRequestSize('段落。'.repeat(2200), 1)).toBe('long')
    expect(classifyAiRequestSize('段落。'.repeat(4200), 1)).toBe('very_long')

    const repeatedEnglish = 'word '.repeat(1800)
    expect(classifyAiRequestSize(repeatedEnglish, 1)).toBe('long')
    expect(classifyAiRequestSize(repeatedEnglish, 3)).toBe('very_long')
  })

  it('returns stable display diagnostics for UI summaries', () => {
    const diagnostics = buildAiRequestDiagnostics('第一段。\n\n第二段。', 2)

    expect(diagnostics.chars).toBe('第一段。\n\n第二段。'.length)
    expect(diagnostics.paragraphs).toBe(2)
    expect(diagnostics.profileCount).toBe(2)
    expect(diagnostics.labelKey).toBe('ai.requestSize.normal.label')
  })
})
