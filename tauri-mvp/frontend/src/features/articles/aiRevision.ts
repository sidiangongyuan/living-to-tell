import type { AiContextAttachment, AiTaskRequest } from '../../api/ai'

export type AiRevisionScope = 'selection' | 'paragraph' | 'article'
export type AiRevisionTask = 'polish' | 'compress' | 'expand' | 'restrained' | 'logic'

export interface RevisionRange {
  start: number
  end: number
  text: string
  scope: AiRevisionScope
}

export interface RevisionTaskOption {
  id: AiRevisionTask
  label: string
  taskType: AiTaskRequest['task_type']
  style: string
  instructions: string
  costTier: AiTaskRequest['cost_tier']
}

export const AI_REVISION_TASKS: RevisionTaskOption[] = [
  {
    id: 'polish',
    label: '润色',
    taskType: 'polish',
    style: '自然、顺滑、保留原文语气',
    instructions: '只返回修订后的正文，不要解释修改理由。',
    costTier: 'balanced',
  },
  {
    id: 'compress',
    label: '压缩',
    taskType: 'rewrite',
    style: '压缩冗余，保留信息和语气',
    instructions: '压缩重复、拖沓和解释过度的表达。只返回修订后的正文，不要解释。',
    costTier: 'balanced',
  },
  {
    id: 'expand',
    label: '扩写',
    taskType: 'expand',
    style: '补足动作、感官和心理层次',
    instructions: '在不改变事实和叙述视角的前提下扩写。只返回可直接替换的正文。',
    costTier: 'balanced',
  },
  {
    id: 'restrained',
    label: '更克制',
    taskType: 'polish',
    style: '克制、干净、少修辞',
    instructions: '削弱过满的修辞和情绪判断，保留必要画面。只返回修订后的正文。',
    costTier: 'balanced',
  },
  {
    id: 'logic',
    label: '逻辑检查',
    taskType: 'consistency_check',
    style: '修正逻辑跳跃和不清楚的因果',
    instructions: '先在心里检查逻辑、因果和指代问题，然后直接输出一版修订后的正文；不要输出报告。',
    costTier: 'strong',
  },
]

export function clampRange(start: number, end: number, textLength: number): { start: number; end: number } {
  const safeStart = Math.max(0, Math.min(start, textLength))
  const safeEnd = Math.max(safeStart, Math.min(end, textLength))
  return { start: safeStart, end: safeEnd }
}

export function paragraphRangeAt(text: string, caretStart: number, caretEnd = caretStart): RevisionRange {
  const range = clampRange(caretStart, caretEnd, text.length)
  if (range.start !== range.end) {
    return {
      start: range.start,
      end: range.end,
      text: text.slice(range.start, range.end),
      scope: 'selection',
    }
  }

  let start = range.start
  let end = range.end
  while (start > 0 && text[start - 1] !== '\n') start -= 1
  while (end < text.length && text[end] !== '\n') end += 1

  return {
    start,
    end,
    text: text.slice(start, end),
    scope: 'paragraph',
  }
}

export function resolveRevisionRange(
  body: string,
  scope: AiRevisionScope,
  selectionStart: number,
  selectionEnd: number,
): RevisionRange {
  if (scope === 'article') {
    return { start: 0, end: body.length, text: body, scope: 'article' }
  }
  if (scope === 'paragraph') {
    return paragraphRangeAt(body, selectionStart, selectionEnd)
  }
  const range = clampRange(selectionStart, selectionEnd, body.length)
  return {
    start: range.start,
    end: range.end,
    text: body.slice(range.start, range.end),
    scope: 'selection',
  }
}

export function applyRevisionToBody(body: string, range: RevisionRange, proposed: string): string {
  return `${body.slice(0, range.start)}${proposed}${body.slice(range.end)}`
}

export function buildRevisionTaskRequest(options: {
  revisionTask: AiRevisionTask
  text: string
  articleId: string
  scope: AiRevisionScope
  extraInstructions?: string
  attachments?: AiContextAttachment[]
}): AiTaskRequest {
  const task = AI_REVISION_TASKS.find((item) => item.id === options.revisionTask) ?? AI_REVISION_TASKS[0]
  const extra = [task.instructions, options.extraInstructions || ''].map((value) => value.trim()).filter(Boolean).join('\n')
  return {
    task_type: task.taskType,
    text: options.text,
    target_kind: options.scope === 'article' ? 'article' : 'selection',
    target_ref_id: options.articleId,
    style: task.style,
    intensity: options.revisionTask === 'compress' ? 'strong' : 'medium',
    preserve_meaning: true,
    preserve_voice: options.revisionTask !== 'logic',
    extra_instructions: extra,
    attachments: options.attachments ?? [],
    cost_tier: task.costTier,
  }
}

export function normalizeAiRevisionResult(text: string): string {
  return (text || '')
    .replace(/^```(?:text|markdown|md)?\s*/i, '')
    .replace(/\s*```$/i, '')
    .trim()
}
