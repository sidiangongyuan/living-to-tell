import { describe, expect, it } from 'vitest'
import { buildTaskRequestOptions, createDefaultControls, mergeControls } from './taskControls'

describe('taskControls', () => {
  it('builds polish controls without losing custom instructions', () => {
    const controls = createDefaultControls()
    controls.polishIntensity = 'strong'
    controls.compressRedundancy = true
    controls.extraInstructions = '保留结尾的停顿感。'

    const options = buildTaskRequestOptions('polish', controls)

    expect(options.intensity).toBe('strong')
    expect(options.preserve_voice).toBe(true)
    expect(options.extra_instructions).toContain('压缩冗余')
    expect(options.extra_instructions).toContain('保留结尾')
  })

  it('merges preset snapshots with safe defaults', () => {
    const controls = mergeControls({
      polishIntensity: 'invalid',
      continueLength: 'long',
      preserveVoice: false,
    })

    expect(controls.polishIntensity).toBe('medium')
    expect(controls.continueLength).toBe('long')
    expect(controls.preserveVoice).toBe(false)
    expect(controls.rewriteDirection).toBeTruthy()
  })
})
