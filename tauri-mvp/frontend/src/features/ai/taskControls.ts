import type { AiTaskRequest } from '../../api/ai'

export type FocusTaskType = 'polish' | 'rewrite' | 'expand' | 'continue'

export interface TaskControls {
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
  extraInstructions: string
}

export const FOCUS_TASKS: FocusTaskType[] = ['polish', 'rewrite', 'expand', 'continue']

export function createDefaultControls(): TaskControls {
  return {
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
    preserveVoice: value.preserveVoice ?? defaults.preserveVoice,
    compressRedundancy: value.compressRedundancy ?? defaults.compressRedundancy,
    keepImagery: value.keepImagery ?? defaults.keepImagery,
    sensoryDetail: value.sensoryDetail ?? defaults.sensoryDetail,
  }
}

export function buildTaskRequestOptions(
  taskType: AiTaskRequest['task_type'],
  controls: TaskControls,
): Pick<AiTaskRequest, 'style' | 'intensity' | 'extra_instructions' | 'max_output_chars' | 'preserve_voice' | 'preserve_meaning'> {
  if (taskType === 'polish') {
    return {
      style: controls.polishStyle,
      intensity: controls.polishIntensity,
      preserve_voice: controls.preserveVoice,
      preserve_meaning: true,
      extra_instructions: joinLines([
        polishGoalInstruction(controls.polishGoal),
        polishRhythmInstruction(controls.polishRhythm),
        polishImageryInstruction(controls.polishImagery),
        controls.compressRedundancy ? '压缩冗余表达，让句子更紧致。' : '',
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
        `叙述语气：${controls.narrativeTone}`,
        controls.keepImagery ? '保留原文关键意象和象征，不要把它们替换成普通概括。' : '',
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
        `细节类型：${controls.detailType}`,
        controls.sensoryDetail ? '加入必要的感官描写，但不要堆砌形容词。' : '',
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
        `情绪走向：${controls.emotionalDirection}`,
        `推进速度：${controls.pacing}`,
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
        '把 AI 卡片作为风格、人物或场景结构参考；不要照搬卡片或文脉标本中的原句。',
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
        '输出要便于后续写作调用，不要只做泛泛概括。',
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

function polishGoalInstruction(value: TaskControls['polishGoal']): string {
  if (value === 'rhythm') return '润色目标：优先打磨句子节奏、停顿、长短句组织；不要改变叙事事实。'
  if (value === 'literary') return '润色目标：提升文学质感和画面感，但不要堆砌形容词，不要新增情节信息。'
  if (value === 'restrained') return '润色目标：克制、干净、少修辞；只修掉笨重和含混之处。'
  return '润色目标：优先提升清晰度、准确性和顺读性，避免只做同义词替换。'
}

function polishRhythmInstruction(value: TaskControls['polishRhythm']): string {
  if (value === 'tight') return '节奏偏好：句子更紧，删除拖沓转折和重复铺垫。'
  if (value === 'flowing') return '节奏偏好：允许更舒展的长短句交替，保留必要的余韵。'
  return '节奏偏好：保持均衡，不刻意压缩或拉长。'
}

function polishImageryInstruction(value: TaskControls['polishImagery']): string {
  if (value === 'enhance') return '意象处理：在不新增事实的前提下增强已有意象的感官清晰度。'
  if (value === 'reduce') return '意象处理：削弱过满或过直白的意象，保留核心画面。'
  return '意象处理：保留原有关键意象，不替换成普通概括。'
}

function joinLines(values: string[]): string {
  return values.map((value) => value.trim()).filter(Boolean).join('\n')
}
