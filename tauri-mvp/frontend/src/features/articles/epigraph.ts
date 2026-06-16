export interface EpigraphParts {
  quote: string
  attribution: string
  body: string
  raw: string
}

const MAX_SCAN_LINES = 8
const MAX_QUOTE_LINES = 4
const MAX_TOTAL_LINES = 5
const MAX_QUOTE_CHARS = 240
const MAX_ATTRIBUTION_CHARS = 120
const BOOK_RE = /《[^《》\n]{1,40}》/
const DASH_PREFIX_RE = /^\s*[—-]{1,2}\s*/
const ATTR_LINE_RE = /^\s*(?:[—-]{1,2}\s*)?(.+?)\s*$/
const SAME_LINE_DASH_RE = /^(.+?)([—-]{1,2}\s*)(.+)$/
const SAME_LINE_SPACE_DASH_RE = /^(.+?)(?:\s{2,}|[ \t]+[—-]{1,2}[ \t]+)(.+)$/
const SAME_LINE_PUNCT_RE = /^(.+[。！？!?…]["'”’」』》〉»]*)\s+(.+)$/

export function detectEpigraph(text: string): EpigraphParts | null {
  if (!text.trim()) return null

  const lines: string[] = []
  const lineEnds: number[] = []
  let offset = 0
  while (lines.length < MAX_SCAN_LINES && offset < text.length) {
    const newline = text.indexOf('\n', offset)
    const lineEnd = newline === -1 ? text.length : newline
    const nextOffset = newline === -1 ? text.length : newline + 1
    let rawLine = text.slice(offset, lineEnd)
    if (rawLine.endsWith('\r')) rawLine = rawLine.slice(0, -1)
    lines.push(rawLine)
    lineEnds.push(nextOffset)
    if (newline === -1) break
    offset = nextOffset
  }

  for (let attrIndex = 0; attrIndex < lines.length; attrIndex += 1) {
    const attribution = parseAttribution(lines[attrIndex])
    if (attribution) {
      const candidate = makeEpigraph(text, lines.slice(0, attrIndex), attribution, lineEnds[attrIndex])
      if (candidate) return candidate
    }

    if (attrIndex === 0) {
      const sameLine = parseSameLine(lines[attrIndex])
      if (sameLine) {
        const candidate = makeEpigraph(text, [sameLine.quote], sameLine.attribution, lineEnds[attrIndex])
        if (candidate) return candidate
      }
    }
  }

  return null
}

export function composeArticleBody(parts: EpigraphParts | null, body: string): string {
  if (!parts || !parts.quote.trim() || !parts.attribution.trim()) {
    return body
  }
  return `${parts.quote.trim()}\n——${parts.attribution.trim()}\n\n${body.trimStart()}`
}

function makeEpigraph(text: string, quoteLines: string[], attribution: string, endOffset: number): EpigraphParts | null {
  const trimmedLines = trimBlankEdges(quoteLines)
  if (!trimmedLines.length || trimmedLines.length > MAX_QUOTE_LINES) return null

  const raw = text.slice(0, endOffset)
  const lineCount = countLines(raw)
  if (lineCount > MAX_TOTAL_LINES) return null

  const quote = trimmedLines.map((line) => line.trimEnd()).join('\n').trim()
  const normalizedAttribution = normalizeAttribution(attribution)
  if (!quote || !normalizedAttribution) return null
  if (quote.length > MAX_QUOTE_CHARS || normalizedAttribution.length > MAX_ATTRIBUTION_CHARS) return null
  if (!looksLikeAttribution(normalizedAttribution)) return null
  if (looksLikeBodyOpening(quote)) return null

  return {
    quote,
    attribution: normalizedAttribution,
    raw,
    body: text.slice(endOffset).trimStart(),
  }
}

function parseSameLine(line: string): { quote: string; attribution: string } | null {
  const stripped = line.trim()
  if (!stripped) return null
  const match = stripped.match(SAME_LINE_SPACE_DASH_RE)
    ?? stripped.match(SAME_LINE_DASH_RE)
    ?? stripped.match(SAME_LINE_PUNCT_RE)
  if (!match) return null
  const quote = match[1]?.trim()
  const attribution = match[match.length - 1]?.trim()
  if (!quote || !attribution || !looksLikeAttribution(attribution)) return null
  return { quote, attribution: normalizeAttribution(attribution) }
}

function parseAttribution(line: string): string | null {
  const stripped = line.trim()
  if (!stripped) return null
  const match = stripped.match(ATTR_LINE_RE)
  const content = match?.[1]?.trim()
  if (!content || !looksLikeAttribution(content)) return null
  return normalizeAttribution(content)
}

function looksLikeAttribution(text: string): boolean {
  const compact = text.trim()
  if (compact.length < 2 || compact.length > MAX_ATTRIBUTION_CHARS) return false
  if (/[。！？!?]$/.test(compact)) return false
  if (BOOK_RE.test(compact)) return true
  const parts = compact.split('，').map((part) => part.trim()).filter(Boolean)
  return parts.length === 2 && parts.some((part) => BOOK_RE.test(part))
}

function normalizeAttribution(text: string): string {
  return text.trim().replace(DASH_PREFIX_RE, '').replace(/\s+/g, ' ').trim()
}

function looksLikeBodyOpening(quote: string): boolean {
  const plain = quote.replace(/^[“”"'‘’「」『』《》〈〉]+/, '').replace(/[“”"'‘’「」『』《》〈〉]+$/, '').trim()
  if (!plain) return true
  if (/^\s*(chapter|section|part|prologue|epilogue|第[一二三四五六七八九十百千0-9]+[章节回部卷篇])/i.test(plain)) return true
  if (!plain.includes('\n') && plain.length > 90 && !/[。.]/.test(plain)) return true
  if (/[：:]$/.test(plain)) return true
  if (/^(我|我们|那天|后来|于是|首先|今天|清晨|凌晨|夜里|雨|风|门外)/.test(plain) && plain.length > 20) return true
  return false
}

function trimBlankEdges(lines: string[]): string[] {
  let start = 0
  let end = lines.length
  while (start < end && !lines[start].trim()) start += 1
  while (end > start && !lines[end - 1].trim()) end -= 1
  return lines.slice(start, end)
}

function countLines(text: string): number {
  if (!text) return 0
  const lines = text.split(/\r\n|\r|\n/)
  if (text.endsWith('\n') || text.endsWith('\r')) {
    return Math.max(0, lines.length - 1)
  }
  return lines.length
}
