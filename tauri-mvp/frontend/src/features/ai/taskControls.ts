import type { AiTaskRequest } from '../../api/ai'

export type FocusTaskType = 'polish' | 'rewrite' | 'expand' | 'continue'

export interface TaskControls {
  presetGuidance: string
  polishIntensity: 'light' | 'medium' | 'strong'
  polishGoal: 'clarity' | 'rhythm' | 'literary' | 'restrained'
  polishRhythm: 'balanced' | 'tight' | 'flowing'
  polishImagery: 'preserve' | 'enhance' | 'reduce'
  polishStyle: string
  preserveVoice: boolean
  compressRedundancy: boolean
  rewriteDirection: string
  narrativeTone: string
  sentenceChange: 'light' | 'medium' | 'strong'
  keepImagery: boolean
  expandLength: 'short' | 'medium' | 'long'
  expandFocus: string
  detailType: string
  sensoryDetail: boolean
  continueLength: 'short' | 'medium' | 'long'
  emotionalDirection: string
  pacing: string
  continuationMode: string
  styleTransferTarget: string
  styleTransferStrictness: 'light' | 'medium' | 'strong'
  summarizeFormat: string
  summarizeFocus: string
  outlineMode: string
  outlineDepth: 'brief' | 'standard' | 'deep'
  titleCount: 'few' | 'standard' | 'many'
  titleStyle: string
  targetViewpoint: 'keep' | 'first' | 'third_limited' | 'omniscient'
  viewpointCharacter: string
  targetTense: 'keep' | 'past' | 'present'
  argumentDirection: string
  sceneFocus: string
  extraInstructions: string
}

export const FOCUS_TASKS: FocusTaskType[] = ['polish', 'rewrite', 'expand', 'continue']

export function createDefaultControls(): TaskControls {
  return {
    presetGuidance: '',
    polishIntensity: 'medium',
    polishGoal: 'clarity',
    polishRhythm: 'balanced',
    polishImagery: 'preserve',
    polishStyle: '自然、流畅、保留原文气息',
    preserveVoice: true,
    compressRedundancy: false,
    rewriteDirection: '换一种表达方式，但保留核心意思',
    narrativeTone: '贴近原文',
    sentenceChange: 'medium',
    keepImagery: true,
    expandLength: 'medium',
    expandFocus: '氛围和心理层次',
    detailType: '动作、感官、环境',
    sensoryDetail: true,
    continueLength: 'medium',
    emotionalDirection: '顺着当前情绪自然推进',
    pacing: '适中',
    continuationMode: '承接最后一句继续写',
    styleTransferTarget: '更有文学性，但不要改变事实和叙述视角',
    styleTransferStrictness: 'medium',
    summarizeFormat: '核心摘要 + 关键事实 + 主题 + 可保留金句',
    summarizeFocus: '叙事信息、情绪变化、可继续写作的线索',
    outlineMode: '按叙事推进分层',
    outlineDepth: 'standard',
    titleCount: 'standard',
    titleStyle: '克制、有辨识度，不标题党',
    targetViewpoint: 'keep',
    viewpointCharacter: '',
    targetTense: 'keep',
    argumentDirection: '',
    sceneFocus: '',
    extraInstructions: '',
  }
}

export function isFocusTask(taskType: string): taskType is FocusTaskType {
  return FOCUS_TASKS.includes(taskType as FocusTaskType)
}

export function cloneControls(controls: TaskControls): TaskControls {
  return { ...controls }
}

export function mergeControls(raw: unknown): TaskControls {
  const defaults = createDefaultControls()
  if (!raw || typeof raw !== 'object') return defaults
  const value = raw as Partial<TaskControls>
  return {
    ...defaults,
    ...value,
    polishIntensity: coerceOption(value.polishIntensity, ['light', 'medium', 'strong'], defaults.polishIntensity),
    polishGoal: coerceOption(value.polishGoal, ['clarity', 'rhythm', 'literary', 'restrained'], defaults.polishGoal),
    polishRhythm: coerceOption(value.polishRhythm, ['balanced', 'tight', 'flowing'], defaults.polishRhythm),
    polishImagery: coerceOption(value.polishImagery, ['preserve', 'enhance', 'reduce'], defaults.polishImagery),
    sentenceChange: coerceOption(value.sentenceChange, ['light', 'medium', 'strong'], defaults.sentenceChange),
    expandLength: coerceOption(value.expandLength, ['short', 'medium', 'long'], defaults.expandLength),
    continueLength: coerceOption(value.continueLength, ['short', 'medium', 'long'], defaults.continueLength),
    styleTransferStrictness: coerceOption(value.styleTransferStrictness, ['light', 'medium', 'strong'], defaults.styleTransferStrictness),
    outlineDepth: coerceOption(value.outlineDepth, ['brief', 'standard', 'deep'], defaults.outlineDepth),
    titleCount: coerceOption(value.titleCount, ['few', 'standard', 'many'], defaults.titleCount),
    targetViewpoint: coerceOption(
      value.targetViewpoint,
      ['keep', 'first', 'third_limited', 'omniscient'],
      defaults.targetViewpoint,
    ),
    targetTense: coerceOption(value.targetTense, ['keep', 'past', 'present'], defaults.targetTense),
    preserveVoice: value.preserveVoice ?? defaults.preserveVoice,
    compressRedundancy: value.compressRedundancy ?? defaults.compressRedundancy,
    keepImagery: value.keepImagery ?? defaults.keepImagery,
    sensoryDetail: value.sensoryDetail ?? defaults.sensoryDetail,
  }
}

export function buildTaskRequestOptions(
  taskType: AiTaskRequest['task_type'],
  controls: TaskControls,
  locale: 'zh' | 'en' = 'zh',
): Pick<AiTaskRequest, 'style' | 'intensity' | 'extra_instructions' | 'max_output_chars' | 'preserve_voice' | 'preserve_meaning'> {
  if (taskType === 'polish') {
    return {
      style: controls.polishStyle,
      intensity: controls.polishIntensity,
      preserve_voice: controls.preserveVoice,
      preserve_meaning: true,
      extra_instructions: joinLines([
        controls.presetGuidance,
        polishGoalInstruction(controls.polishGoal, locale),
        polishRhythmInstruction(controls.polishRhythm, locale),
        polishImageryInstruction(controls.polishImagery, locale),
        controls.compressRedundancy
          ? localized(locale, '压缩冗余表达，让句子更紧致。', 'Compress redundant phrasing and tighten the prose.')
          : '',
        controls.extraInstructions,
      ]),
    }
  }

  if (taskType === 'rewrite') {
    return {
      style: controls.rewriteDirection,
      intensity: controls.sentenceChange,
      preserve_voice: controls.narrativeTone === '贴近原文',
      preserve_meaning: true,
      extra_instructions: joinLines([
        controls.presetGuidance,
        localized(locale, `叙述语气：${controls.narrativeTone}`, `Narrative tone: ${controls.narrativeTone}`),
        controls.keepImagery
          ? localized(
            locale,
            '保留原文关键意象和象征，不要把它们替换成普通概括。',
            'Preserve key images and symbols instead of flattening them into generic summary.',
          )
          : '',
        viewpointInstruction(controls, locale),
        controls.extraInstructions,
      ]),
    }
  }

  if (taskType === 'expand') {
    return {
      style: `扩写重点：${controls.expandFocus}`,
      intensity: controls.expandLength,
      preserve_voice: true,
      preserve_meaning: true,
      max_output_chars: lengthToChars(controls.expandLength, 1800, 3000, 5000),
      extra_instructions: joinLines([
        controls.presetGuidance,
        localized(locale, `细节类型：${controls.detailType}`, `Detail types: ${controls.detailType}`),
        controls.argumentDirection.trim()
          ? localized(locale, `论述方向：${controls.argumentDirection}`, `Argument direction: ${controls.argumentDirection}`)
          : '',
        controls.sceneFocus.trim()
          ? localized(locale, `场面重心：${controls.sceneFocus}`, `Scene focus: ${controls.sceneFocus}`)
          : '',
        controls.sensoryDetail
          ? localized(
            locale,
            '加入必要的感官描写，但不要堆砌形容词。',
            'Add only useful sensory detail and avoid piling up adjectives.',
          )
          : '',
        controls.extraInstructions,
      ]),
    }
  }

  if (taskType === 'continue') {
    return {
      style: controls.continuationMode,
      intensity: controls.continueLength,
      preserve_voice: true,
      preserve_meaning: true,
      max_output_chars: lengthToChars(controls.continueLength, 1200, 2400, 4200),
      extra_instructions: joinLines([
        controls.presetGuidance,
        localized(locale, `情绪走向：${controls.emotionalDirection}`, `Emotional direction: ${controls.emotionalDirection}`),
        localized(locale, `推进速度：${controls.pacing}`, `Pacing: ${controls.pacing}`),
        controls.extraInstructions,
      ]),
    }
  }

  if (taskType === 'style_transfer') {
    return {
      style: controls.styleTransferTarget,
      intensity: controls.styleTransferStrictness,
      preserve_voice: true,
      preserve_meaning: true,
      extra_instructions: joinLines([
        controls.presetGuidance,
        localized(
          locale,
          '把 AI 卡片作为风格、人物或场景结构参考；不要照搬卡片或文脉标本中的原句。',
          'Use AI Cards for style, character, or scene structure only. Do not copy sentences from cards or reference specimens.',
        ),
        controls.extraInstructions,
      ]),
    }
  }

  if (taskType === 'summarize') {
    return {
      style: controls.summarizeFormat,
      preserve_voice: false,
      preserve_meaning: true,
      max_output_chars: 2600,
      extra_instructions: joinLines([
        `摘要重点：${controls.summarizeFocus}`,
        '输出要便于后续写作参考，不要只做泛泛概括。',
        controls.extraInstructions,
      ]),
    }
  }

  if (taskType === 'outline') {
    return {
      style: controls.outlineMode,
      intensity: controls.outlineDepth,
      preserve_voice: false,
      preserve_meaning: true,
      max_output_chars: outlineDepthToChars(controls.outlineDepth),
      extra_instructions: joinLines([
        '标出每一层在文章中的叙事作用；不要替作者新增未出现的内容。',
        controls.extraInstructions,
      ]),
    }
  }

  if (taskType === 'title') {
    return {
      style: controls.titleStyle,
      intensity: controls.titleCount,
      preserve_voice: false,
      preserve_meaning: true,
      max_output_chars: titleCountToChars(controls.titleCount),
      extra_instructions: joinLines([
        '每个标题都说明适用气质和风险，避免空泛、鸡汤、标题党。',
        controls.extraInstructions,
      ]),
    }
  }

  return {
    extra_instructions: controls.extraInstructions,
  }
}

function coerceOption<T extends string>(value: unknown, allowed: readonly T[], fallback: T): T {
  return typeof value === 'string' && allowed.includes(value as T) ? value as T : fallback
}

function lengthToChars(value: 'short' | 'medium' | 'long', short: number, medium: number, long: number): number {
  if (value === 'short') return short
  if (value === 'long') return long
  return medium
}

function outlineDepthToChars(value: 'brief' | 'standard' | 'deep'): number {
  if (value === 'brief') return 1600
  if (value === 'deep') return 4200
  return 2800
}

function titleCountToChars(value: 'few' | 'standard' | 'many'): number {
  if (value === 'few') return 1200
  if (value === 'many') return 3000
  return 2000
}

function polishGoalInstruction(value: TaskControls['polishGoal'], locale: 'zh' | 'en'): string {
  if (value === 'rhythm') {
    return localized(locale, '润色目标：优先打磨句子节奏、停顿、长短句组织；不要改变叙事事实。', 'Polish goal: improve rhythm, pauses, and sentence-length variation without changing narrative facts.')
  }
  if (value === 'literary') {
    return localized(locale, '润色目标：提升文学质感和画面感，但不要堆砌形容词，不要新增情节信息。', 'Polish goal: improve literary texture and imagery without adjective overload or new plot information.')
  }
  if (value === 'restrained') {
    return localized(locale, '润色目标：克制、干净、少修辞；只修掉笨重和含混之处。', 'Polish goal: stay restrained and clean, removing only clumsy or unclear phrasing.')
  }
  return localized(locale, '润色目标：优先提升清晰度、准确性和顺读性，避免只做同义词替换。', 'Polish goal: improve clarity, accuracy, and readability rather than merely swapping synonyms.')
}

function polishRhythmInstruction(value: TaskControls['polishRhythm'], locale: 'zh' | 'en'): string {
  if (value === 'tight') {
    return localized(locale, '节奏偏好：句子更紧，删除拖沓转折和重复铺垫。', 'Rhythm: tighten sentences and remove slow transitions or repeated setup.')
  }
  if (value === 'flowing') {
    return localized(locale, '节奏偏好：允许更舒展的长短句交替，保留必要的余韵。', 'Rhythm: allow a more flowing alternation of long and short sentences, preserving useful resonance.')
  }
  return localized(locale, '节奏偏好：保持均衡，不刻意压缩或拉长。', 'Rhythm: stay balanced without forcing compression or expansion.')
}

function polishImageryInstruction(value: TaskControls['polishImagery'], locale: 'zh' | 'en'): string {
  if (value === 'enhance') {
    return localized(locale, '意象处理：在不新增事实的前提下增强已有意象的感官清晰度。', 'Imagery: make existing images more sensorially precise without adding facts.')
  }
  if (value === 'reduce') {
    return localized(locale, '意象处理：削弱过满或过直白的意象，保留核心画面。', 'Imagery: reduce overloaded or overly explicit images while keeping the core picture.')
  }
  return localized(locale, '意象处理：保留原有关键意象，不替换成普通概括。', 'Imagery: preserve key images instead of replacing them with generic summary.')
}

function joinLines(values: string[]): string {
  return values.map((value) => value.trim()).filter(Boolean).join('\n')
}

function viewpointInstruction(controls: TaskControls, locale: 'zh' | 'en'): string {
  const values: string[] = []
  if (controls.targetViewpoint !== 'keep') {
    const labels = {
      first: localized(locale, '第一人称', 'first person'),
      third_limited: localized(locale, '第三人称限知', 'third-person limited'),
      omniscient: localized(locale, '全知视角', 'omniscient'),
    }
    values.push(localized(locale, `目标视角：${labels[controls.targetViewpoint]}`, `Target viewpoint: ${labels[controls.targetViewpoint]}`))
  }
  if (controls.targetViewpoint === 'third_limited' && controls.viewpointCharacter.trim()) {
    values.push(localized(locale, `视角人物：${controls.viewpointCharacter}`, `Focal character: ${controls.viewpointCharacter}`))
  }
  if (controls.targetTense !== 'keep') {
    const tense = controls.targetTense === 'past'
      ? localized(locale, '过去时', 'past tense')
      : localized(locale, '现在时', 'present tense')
    values.push(localized(locale, `目标时态：${tense}`, `Target tense: ${tense}`))
  }
  return values.join('\n')
}

function localized(locale: 'zh' | 'en', zh: string, en: string): string {
  return locale === 'en' ? en : zh
}
