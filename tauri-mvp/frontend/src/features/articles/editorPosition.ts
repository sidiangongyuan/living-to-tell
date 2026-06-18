export const ARTICLE_EDITOR_POSITIONS_KEY = 'article_editor_positions'
export const LAST_SELECTED_ARTICLE_KEY = 'last_selected_article_id'
export const PARAGRAPH_INDENT = '\u3000\u3000'
export const EDITOR_LINE_HEIGHT_PX = 28
export const COMFORT_ANCHOR_RATIO = 0.58
export const TAIL_SPACE_RATIO = 0.46

export type ArticleEditorInteraction = 'edit' | 'read'

export interface ArticleEditorPosition {
  selectionStart: number
  selectionEnd: number
  scrollTop: number
  updatedAt: number
}

export interface ArticleEditorPositionSlots {
  edit?: ArticleEditorPosition
  read?: ArticleEditorPosition
  updatedAt: number
}

export interface ArticleEditorRestorePosition extends ArticleEditorPosition {
  interaction: ArticleEditorInteraction
}

type PositionMap = Record<string, ArticleEditorPositionSlots>
type RawPositionMap = Record<string, unknown>

type StorageLike = Pick<Storage, 'getItem' | 'setItem'>

function safeParsePositions(raw: string | null): RawPositionMap {
  if (!raw) return {}
  try {
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed as RawPositionMap : {}
  } catch {
    return {}
  }
}

function clampNumber(value: unknown, min = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? Math.max(min, value) : min
}

function normalizeTimestamp(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) ? Math.max(0, value) : Date.now()
}

function isLegacyPosition(value: unknown): value is Partial<ArticleEditorPosition> {
  return Boolean(
    value &&
    typeof value === 'object' &&
    (
      'selectionStart' in value ||
      'selectionEnd' in value ||
      'scrollTop' in value
    )
  )
}

function isSlotPosition(value: unknown): value is Partial<ArticleEditorPositionSlots> {
  return Boolean(
    value &&
    typeof value === 'object' &&
    ('edit' in value || 'read' in value)
  )
}

export function normalizeEditorPosition(
  position: Partial<ArticleEditorPosition>,
  textLength = Number.POSITIVE_INFINITY
): ArticleEditorPosition {
  const max = Number.isFinite(textLength) ? Math.max(0, textLength) : Number.POSITIVE_INFINITY
  const selectionStart = Math.min(clampNumber(position.selectionStart), max)
  const selectionEnd = Math.min(Math.max(selectionStart, clampNumber(position.selectionEnd)), max)
  return {
    selectionStart,
    selectionEnd,
    scrollTop: clampNumber(position.scrollTop),
    updatedAt: normalizeTimestamp(position.updatedAt),
  }
}

function normalizeSlots(value: unknown): ArticleEditorPositionSlots | null {
  if (isLegacyPosition(value)) {
    const edit = normalizeEditorPosition(value)
    return {
      edit,
      updatedAt: edit.updatedAt,
    }
  }
  if (!isSlotPosition(value)) return null

  const edit = isLegacyPosition(value.edit) ? normalizeEditorPosition(value.edit) : undefined
  const read = isLegacyPosition(value.read) ? normalizeEditorPosition(value.read) : undefined
  if (!edit && !read) return null
  return {
    ...(edit ? { edit } : {}),
    ...(read ? { read } : {}),
    updatedAt: clampNumber(value.updatedAt, Math.max(edit?.updatedAt ?? 0, read?.updatedAt ?? 0, Date.now())),
  }
}

function readPositionMap(storage: StorageLike): PositionMap {
  const raw = safeParsePositions(storage.getItem(ARTICLE_EDITOR_POSITIONS_KEY))
  const positions: PositionMap = {}
  for (const [articleId, value] of Object.entries(raw)) {
    const slots = normalizeSlots(value)
    if (slots) positions[articleId] = slots
  }
  return positions
}

function writePositionMap(storage: StorageLike, positions: PositionMap): void {
  storage.setItem(ARTICLE_EDITOR_POSITIONS_KEY, JSON.stringify(positions))
}

export function getArticleEditorPositionSlots(
  articleId: string,
  storage: StorageLike = localStorage
): ArticleEditorPositionSlots | null {
  const positions = readPositionMap(storage)
  return positions[articleId] ?? null
}

export function getPreferredArticleEditorPosition(
  articleId: string,
  storage: StorageLike = localStorage
): ArticleEditorRestorePosition | null {
  const slots = getArticleEditorPositionSlots(articleId, storage)
  if (!slots) return null
  if (slots.edit && slots.read) {
    if (slots.read.updatedAt > slots.edit.updatedAt) {
      return { ...slots.read, interaction: 'read' }
    }
    return { ...slots.edit, interaction: 'edit' }
  }
  if (slots.edit) return { ...slots.edit, interaction: 'edit' }
  if (slots.read) {
    return { ...slots.read, interaction: 'read' }
  }
  return null
}

export function getArticleEditorPosition(
  articleId: string,
  storage: StorageLike = localStorage
): ArticleEditorRestorePosition | null {
  return getPreferredArticleEditorPosition(articleId, storage)
}

export function saveArticleEditorPosition(
  articleId: string,
  position: Partial<ArticleEditorPosition>,
  interactionOrStorage: ArticleEditorInteraction | StorageLike = 'edit',
  storage: StorageLike = localStorage
): void {
  if (!articleId) return
  const interaction: ArticleEditorInteraction =
    typeof interactionOrStorage === 'string' ? interactionOrStorage : 'edit'
  const targetStorage: StorageLike =
    typeof interactionOrStorage === 'string' ? storage : interactionOrStorage
  const positions = readPositionMap(targetStorage)
  const current = positions[articleId] ?? { updatedAt: Date.now() }
  const normalized = normalizeEditorPosition({
    ...position,
    updatedAt: position.updatedAt ?? Date.now(),
  })
  const next: ArticleEditorPositionSlots = {
    ...current,
    [interaction]: normalized,
    updatedAt: normalized.updatedAt,
  }
  positions[articleId] = next
  writePositionMap(targetStorage, positions)
}

export function getLastSelectedArticleId(storage: StorageLike = localStorage): string | null {
  const value = storage.getItem(LAST_SELECTED_ARTICLE_KEY)
  return value && value.trim() ? value : null
}

export function saveLastSelectedArticleId(articleId: string, storage: StorageLike = localStorage): void {
  if (!articleId) return
  storage.setItem(LAST_SELECTED_ARTICLE_KEY, articleId)
}

export function insertIndentedParagraph(
  text: string,
  selectionStart: number,
  selectionEnd: number
): { text: string; selectionStart: number; selectionEnd: number } {
  const start = Math.max(0, Math.min(selectionStart, text.length))
  const end = Math.max(start, Math.min(selectionEnd, text.length))
  const insertion = `\n${PARAGRAPH_INDENT}`
  const nextText = `${text.slice(0, start)}${insertion}${text.slice(end)}`
  const nextSelection = start + insertion.length
  return {
    text: nextText,
    selectionStart: nextSelection,
    selectionEnd: nextSelection,
  }
}

export function isNearArticleEnd(options: {
  textLength: number
  selectionEnd: number
  scrollTop: number
  scrollHeight: number
  clientHeight: number
}): boolean {
  const textLength = Math.max(0, options.textLength)
  const selectionEnd = Math.max(0, options.selectionEnd)
  const maxScrollTop = Math.max(0, options.scrollHeight - options.clientHeight)
  const characterThreshold = Math.max(20, Math.ceil(textLength * 0.015))
  const scrollThreshold = Math.max(80, options.clientHeight * 0.18)
  return (
    textLength - selectionEnd <= characterThreshold ||
    maxScrollTop - Math.max(0, options.scrollTop) <= scrollThreshold
  )
}

export function estimateScrollTopForPosition(options: {
  text: string
  position: number
  clientHeight: number
  lineHeight?: number
  anchorRatio?: number
}): number {
  const safePosition = Math.max(0, Math.min(options.position, options.text.length))
  const lineHeight = options.lineHeight ?? EDITOR_LINE_HEIGHT_PX
  const anchorRatio = options.anchorRatio ?? 0.62
  const lineNumber = options.text.slice(0, safePosition).split('\n').length
  return Math.max(0, lineNumber * lineHeight - options.clientHeight * anchorRatio)
}

export function editorTailSpace(clientHeight: number, min = 220, max = 520): number {
  if (!Number.isFinite(clientHeight) || clientHeight <= 0) return min
  return Math.max(min, Math.min(max, Math.round(clientHeight * TAIL_SPACE_RATIO)))
}

export function shouldRecenterCaret(options: {
  caretScrollTop: number
  currentScrollTop: number
  clientHeight: number
  thresholdRatio?: number
}): boolean {
  const thresholdRatio = options.thresholdRatio ?? 0.62
  const caretY = options.caretScrollTop - Math.max(0, options.currentScrollTop)
  return caretY > Math.max(0, options.clientHeight) * thresholdRatio
}
