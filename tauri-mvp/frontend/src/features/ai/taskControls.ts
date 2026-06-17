import type { AiTaskRequest } from '../../api/ai'

export type FocusTaskType = 'polish' | 'rewrite' | 'expand' | 'continue'

export interface TaskControls {
  polishIntensity: 'light' | 'medium' | 'strong'
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
  extraInstructions: string
}

export const FOCUS_TASKS: FocusTaskType[] = ['polish', 'rewrite', 'expand', 'continue']

export function createDefaultControls(): TaskControls {
  return {
    polishIntensity: 'medium',
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
    sentenceChange: coerceOption(value.sentenceChange, ['light', 'medium', 'strong'], defaults.sentenceChange),
    expandLength: coerceOption(value.expandLength, ['short', 'medium', 'long'], defaults.expandLength),
    continueLength: coerceOption(value.continueLength, ['short', 'medium', 'long'], defaults.continueLength),
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

function joinLines(values: string[]): string {
  return values.map((value) => value.trim()).filter(Boolean).join('\n')
}
