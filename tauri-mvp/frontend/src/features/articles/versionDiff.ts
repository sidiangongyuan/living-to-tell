export type ParagraphDiffKind = 'equal' | 'changed' | 'added' | 'removed'

export interface ParagraphDiffRow {
  kind: ParagraphDiffKind
  current: string
  historical: string
}

function splitParagraphs(text: string): string[] {
  const normalized = (text || '').replace(/\r\n?/g, '\n')
  if (!normalized.trim()) return []
  return normalized
    .split(/\n{2,}/)
    .map((part) => part.trimEnd())
    .filter((part) => part.trim().length > 0)
}

function normalizeParagraph(text: string): string {
  return text.replace(/\s+/g, ' ').trim()
}

function buildLcs(a: string[], b: string[]): number[][] {
  const table = Array.from({ length: a.length + 1 }, () => Array(b.length + 1).fill(0))
  for (let i = a.length - 1; i >= 0; i -= 1) {
    for (let j = b.length - 1; j >= 0; j -= 1) {
      table[i][j] = a[i] === b[j] ? table[i + 1][j + 1] + 1 : Math.max(table[i + 1][j], table[i][j + 1])
    }
  }
  return table
}

export function buildParagraphDiff(currentText: string, historicalText: string): ParagraphDiffRow[] {
  const current = splitParagraphs(currentText)
  const historical = splitParagraphs(historicalText)
  const currentNorm = current.map(normalizeParagraph)
  const historicalNorm = historical.map(normalizeParagraph)
  const lcs = buildLcs(currentNorm, historicalNorm)
  const rows: ParagraphDiffRow[] = []
  let i = 0
  let j = 0

  while (i < current.length || j < historical.length) {
    if (i < current.length && j < historical.length && currentNorm[i] === historicalNorm[j]) {
      rows.push({ kind: 'equal', current: current[i], historical: historical[j] })
      i += 1
      j += 1
      continue
    }

    if (i < current.length && (j >= historical.length || lcs[i + 1][j] >= lcs[i][j + 1])) {
      if (
        j < historical.length
        && currentNorm[i] !== historicalNorm[j]
        && lcs[i + 1][j] === lcs[i][j + 1]
      ) {
        rows.push({ kind: 'changed', current: current[i], historical: historical[j] })
        i += 1
        j += 1
      } else {
        rows.push({ kind: 'added', current: current[i], historical: '' })
        i += 1
      }
      continue
    }

    if (j < historical.length) {
      rows.push({ kind: 'removed', current: '', historical: historical[j] })
      j += 1
    }
  }

  return rows
}
