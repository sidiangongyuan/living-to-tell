export interface MotifSelectionSnapshot {
  text: string
  start: number
  end: number
  beforeContext: string
  afterContext: string
}

export interface MotifJumpSnapshot {
  excerptId: string
  text: string
  start: number | null
  end: number | null
}

export interface MotifExcerptRangeInput {
  excerpt_text: string
  selection_start: number | null
  selection_end: number | null
}

export type MotifExcerptRangeStatus = 'matched' | 'moved' | 'missing'

export interface ResolvedMotifExcerptRange {
  status: MotifExcerptRangeStatus
  start: number | null
  end: number | null
}

export function buildMotifSelectionSnapshot(
  sourceText: string,
  selectionStart: number,
  selectionEnd: number,
  contextSize = 90,
): MotifSelectionSnapshot | null {
  const safeStart = Math.max(0, Math.min(selectionStart, sourceText.length))
  const safeEnd = Math.max(0, Math.min(selectionEnd, sourceText.length))
  const rawStart = Math.min(safeStart, safeEnd)
  const rawEnd = Math.max(safeStart, safeEnd)
  if (rawEnd <= rawStart) return null

  const rawText = sourceText.slice(rawStart, rawEnd)
  const leadingTrim = rawText.length - rawText.trimStart().length
  const trailingTrim = rawText.length - rawText.trimEnd().length
  const start = rawStart + leadingTrim
  const end = rawEnd - trailingTrim
  if (end <= start) return null

  return {
    text: sourceText.slice(start, end),
    start,
    end,
    beforeContext: sourceText.slice(Math.max(0, start - contextSize), start),
    afterContext: sourceText.slice(end, Math.min(sourceText.length, end + contextSize)),
  }
}

export function addUniqueMotifName(names: string[], nextName: string): string[] {
  const cleanName = nextName.trim()
  if (!cleanName) return names
  if (names.some((name) => name.toLowerCase() === cleanName.toLowerCase())) return names
  return [...names, cleanName]
}

export function readMotifJumpSnapshot(storage: Storage): MotifJumpSnapshot | null {
  try {
    const parsed = JSON.parse(storage.getItem('motif:lastJump') || 'null')
    if (!parsed || typeof parsed !== 'object') return null
    const excerptId = typeof parsed.excerptId === 'string' ? parsed.excerptId : ''
    const text = typeof parsed.text === 'string' ? parsed.text : ''
    if (!excerptId && !text) return null
    const start = Number.isFinite(parsed.start) ? Number(parsed.start) : null
    const end = Number.isFinite(parsed.end) ? Number(parsed.end) : null
    return { excerptId, text, start, end }
  } catch {
    return null
  }
}

export function findMotifTextPosition(sourceText: string, excerptText: string): { start: number; end: number } | null {
  const cleanText = excerptText.trim()
  if (!cleanText) return null
  const exactIndex = sourceText.indexOf(cleanText)
  if (exactIndex !== -1) {
    return { start: exactIndex, end: exactIndex + cleanText.length }
  }

  const compactNeedle = cleanText.replace(/\s+/g, ' ')
  if (!compactNeedle) return null
  let compactSource = ''
  const indexMap: number[] = []
  let previousWasSpace = false
  for (let index = 0; index < sourceText.length; index += 1) {
    const char = sourceText[index]
    if (/\s/.test(char)) {
      if (!previousWasSpace) {
        compactSource += ' '
        indexMap.push(index)
      }
      previousWasSpace = true
    } else {
      compactSource += char
      indexMap.push(index)
      previousWasSpace = false
    }
  }
  const compactIndex = compactSource.indexOf(compactNeedle)
  if (compactIndex !== -1) {
    const start = indexMap[compactIndex] ?? 0
    const endSourceIndex = indexMap[compactIndex + compactNeedle.length - 1] ?? start
    return { start, end: endSourceIndex + 1 }
  }
  return null
}

export function resolveMotifExcerptRange(sourceText: string, excerpt: MotifExcerptRangeInput): ResolvedMotifExcerptRange {
  const start = excerpt.selection_start
  const end = excerpt.selection_end
  if (start !== null && end !== null) {
    const safeStart = Math.max(0, Math.min(start, sourceText.length))
    const safeEnd = Math.max(safeStart, Math.min(end, sourceText.length))
    if (sourceText.slice(safeStart, safeEnd).trim() === excerpt.excerpt_text.trim()) {
      return { status: 'matched', start: safeStart, end: safeEnd }
    }
  }
  const found = findMotifTextPosition(sourceText, excerpt.excerpt_text)
  if (found) return { status: 'moved', ...found }
  return { status: 'missing', start: null, end: null }
}
