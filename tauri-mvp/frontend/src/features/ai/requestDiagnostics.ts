import { countParagraphs } from '../articles/articleList'

export type AiRequestSizeLevel = 'normal' | 'long' | 'very_long'

export interface AiRequestDiagnostics {
  chars: number
  paragraphs: number
  estimatedTokens: number
  profileCount: number
  level: AiRequestSizeLevel
  labelKey: string
  messageKey: string
}

export function estimateAiTokens(text: string): number {
  const trimmed = text.trim()
  if (!trimmed) return 0

  const cjkMatches = trimmed.match(/[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]/g)
  const cjkCount = cjkMatches?.length ?? 0
  const otherCount = Math.max(0, trimmed.length - cjkCount)
  const wordMatches = trimmed.match(/[A-Za-z0-9_]+(?:['-][A-Za-z0-9_]+)*/g)
  const wordCount = wordMatches?.length ?? 0

  return Math.max(1, Math.ceil(cjkCount * 0.65 + wordCount * 1.25 + otherCount * 0.2))
}

export function classifyAiRequestSize(
  text: string,
  profileCount = 1,
): AiRequestSizeLevel {
  const chars = text.trim().length
  const paragraphs = countParagraphs(text)
  const estimatedTokens = estimateAiTokens(text)
  const multiplier = Math.max(1, profileCount)
  const totalEstimatedTokens = estimatedTokens * multiplier

  if (
    chars >= 12000
    || paragraphs >= 50
    || totalEstimatedTokens >= 12000
  ) {
    return 'very_long'
  }

  if (
    chars >= 6000
    || paragraphs >= 24
    || totalEstimatedTokens >= 6000
  ) {
    return 'long'
  }

  return 'normal'
}

export function buildAiRequestDiagnostics(
  text: string,
  profileCount = 1,
): AiRequestDiagnostics {
  const chars = text.length
  const paragraphs = countParagraphs(text)
  const estimatedTokens = estimateAiTokens(text)
  const level = classifyAiRequestSize(text, profileCount)

  return {
    chars,
    paragraphs,
    estimatedTokens,
    profileCount: Math.max(1, profileCount),
    level,
    labelKey: `ai.requestSize.${level}.label`,
    messageKey: `ai.requestSize.${level}.message`,
  }
}
