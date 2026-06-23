import { describe, expect, it } from 'vitest'
import { buildTaskRequestOptions, createDefaultControls, mergeControls } from './taskControls'

describe('taskControls', () => {
  it('builds polish controls without losing custom instructions', () => {
    const controls = createDefaultControls()
    controls.polishIntensity = 'strong'
    controls.polishGoal = 'rhythm'
    controls.polishRhythm = 'flowing'
    controls.polishImagery = 'enhance'
    controls.compressRedundancy = true
    controls.extraInstructions = '保留结尾的停顿感。'

    const options = buildTaskRequestOptions('polish', controls)

    expect(options.intensity).toBe('strong')
    expect(options.preserve_voice).toBe(true)
    expect(options.extra_instructions).toContain('句子节奏')
    expect(options.extra_instructions).toContain('更舒展')
    expect(options.extra_instructions).toContain('增强已有意象')
    expect(options.extra_instructions).toContain('压缩冗余')
    expect(options.extra_instructions).toContain('保留结尾')
  })

  it('merges preset snapshots with safe defaults', () => {
    const controls = mergeControls({
      polishIntensity: 'invalid',
      polishGoal: 'invalid',
      polishRhythm: 'invalid',
      polishImagery: 'invalid',
      continueLength: 'long',
      outlineDepth: 'invalid',
      preserveVoice: false,
    })

    expect(controls.polishIntensity).toBe('medium')
    expect(controls.polishGoal).toBe('clarity')
    expect(controls.polishRhythm).toBe('balanced')
    expect(controls.polishImagery).toBe('preserve')
    expect(controls.continueLength).toBe('long')
    expect(controls.outlineDepth).toBe('standard')
    expect(controls.preserveVoice).toBe(false)
    expect(controls.rewriteDirection).toBeTruthy()
  })

  it('builds advanced task controls into the AI request options', () => {
    const controls = createDefaultControls()
    controls.summarizeFocus = '人物关系和情绪转折'
    controls.extraInstructions = '不要泛泛概括。'

    const summaryOptions = buildTaskRequestOptions('summarize', controls)

    expect(summaryOptions.style).toContain('核心摘要')
    expect(summaryOptions.extra_instructions).toContain('人物关系')
    expect(summaryOptions.extra_instructions).toContain('不要泛泛概括')

    controls.outlineDepth = 'deep'
    const outlineOptions = buildTaskRequestOptions('outline', controls)
    expect(outlineOptions.intensity).toBe('deep')
    expect(outlineOptions.max_output_chars).toBe(4200)
  })
})
