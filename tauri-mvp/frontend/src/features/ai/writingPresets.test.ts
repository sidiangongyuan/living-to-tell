import { describe, expect, it } from 'vitest'
import { createDefaultControls } from './taskControls'
import {
  BUILT_IN_WRITING_PRESETS,
  controlsForBuiltInPreset,
  defaultPresetForTask,
  missingPresetRequirements,
  presetsForTask,
  writingPresetCopy,
} from './writingPresets'

describe('writing presets', () => {
  it('provides the complete 25-preset catalog and one neutral default per task', () => {
    expect(BUILT_IN_WRITING_PRESETS).toHaveLength(25)
    expect(presetsForTask('polish')).toHaveLength(6)
    expect(presetsForTask('rewrite')).toHaveLength(6)
    expect(presetsForTask('expand')).toHaveLength(6)
    expect(presetsForTask('continue')).toHaveLength(7)

    for (const task of ['polish', 'rewrite', 'expand', 'continue'] as const) {
      expect(defaultPresetForTask(task).isDefault).toBe(true)
      expect(defaultPresetForTask(task).taskType).toBe(task)
    }
  })

  it('keeps Chinese and English guidance available for every built-in preset', () => {
    for (const preset of BUILT_IN_WRITING_PRESETS) {
      expect(writingPresetCopy(preset.name, 'zh')).toBeTruthy()
      expect(writingPresetCopy(preset.name, 'en')).toBeTruthy()
      expect(writingPresetCopy(preset.guidance, 'zh').length).toBeGreaterThan(20)
      expect(writingPresetCopy(preset.guidance, 'en').length).toBeGreaterThan(20)
      if (preset.tier === 'creative') {
        expect(writingPresetCopy(preset.risk, 'zh')).toBeTruthy()
      }
    }
  })

  it('applies localized guidance and validates structured creative controls', () => {
    const viewpoint = BUILT_IN_WRITING_PRESETS.find((item) => item.id === 'rewrite-viewpoint')!
    const controls = controlsForBuiltInPreset(viewpoint, 'en')
    expect(controls.presetGuidance).toContain('viewpoint')
    expect(missingPresetRequirements(viewpoint, controls)).toEqual(['viewpoint_or_tense'])

    controls.targetTense = 'past'
    expect(missingPresetRequirements(viewpoint, controls)).toEqual([])

    const argument = BUILT_IN_WRITING_PRESETS.find((item) => item.id === 'expand-argument')!
    const argumentControls = createDefaultControls()
    expect(missingPresetRequirements(argument, argumentControls)).toEqual(['argument_direction'])
    argumentControls.argumentDirection = '先解释原因，再处理反例'
    expect(missingPresetRequirements(argument, argumentControls)).toEqual([])
  })
})
