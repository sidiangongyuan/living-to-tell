import { composeArticleBody, detectEpigraph, type EpigraphParts } from '../articles/epigraph'

export interface ArticleEditResult {
  body: string
  selectionStart: number
  selectionEnd: number
}

export type ArticleEditMode = 'replace' | 'insert_after'

export function selectArticleBodyText(fullBody: string): { bodyText: string; epigraph: EpigraphParts | null } {
  const epigraph = detectEpigraph(fullBody)
  return {
    bodyText: epigraph?.body ?? fullBody,
    epigraph,
  }
}

export function applyArticleBodyEdit(
  fullBody: string,
  start: number,
  end: number,
  resultText: string,
  mode: ArticleEditMode,
): ArticleEditResult {
  const { bodyText, epigraph } = selectArticleBodyText(fullBody)
  const safeStart = clamp(Math.min(start, end), 0, bodyText.length)
  const safeEnd = clamp(Math.max(start, end), safeStart, bodyText.length)
  const insertAt = mode === 'insert_after' ? safeEnd : safeStart
  const nextBodyText = mode === 'insert_after'
    ? `${bodyText.slice(0, insertAt)}${withInsertionSpacing(bodyText, insertAt, resultText)}${bodyText.slice(insertAt)}`
    : `${bodyText.slice(0, safeStart)}${resultText}${bodyText.slice(safeEnd)}`
  const resultStart = mode === 'insert_after'
    ? insertAt + insertionPrefix(bodyText, insertAt).length
    : safeStart
  const nextFullBody = epigraph
    ? composeArticleBody({ ...epigraph, body: nextBodyText }, nextBodyText)
    : nextBodyText

  return {
    body: nextFullBody,
    selectionStart: resultStart,
    selectionEnd: resultStart + resultText.length,
  }
}

function insertionPrefix(bodyText: string, index: number): string {
  if (!bodyText.trim()) return ''
  const before = bodyText.slice(0, index)
  if (before.endsWith('\n\n')) return ''
  if (before.endsWith('\n')) return '\n'
  return '\n\n'
}

function withInsertionSpacing(bodyText: string, index: number, resultText: string): string {
  const prefix = insertionPrefix(bodyText, index)
  const suffix = bodyText.slice(index).startsWith('\n') || !bodyText.slice(index).trim() ? '' : '\n\n'
  return `${prefix}${resultText}${suffix}`
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}
