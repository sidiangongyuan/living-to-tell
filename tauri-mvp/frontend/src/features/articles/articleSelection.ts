export interface ArticleBodySelection {
  start: number
  end: number
  text: string
}

export function mapEditorSelectionToArticleBody(
  editorBody: string,
  articleBody: string,
  selectionStart: number,
  selectionEnd: number,
): ArticleBodySelection | null {
  const start = Math.max(0, Math.min(Math.trunc(selectionStart), editorBody.length))
  const end = Math.max(start, Math.min(Math.trunc(selectionEnd), editorBody.length))
  if (end <= start || !articleBody.endsWith(editorBody)) return null

  const bodyOffset = articleBody.length - editorBody.length
  const mapped = {
    start: bodyOffset + start,
    end: bodyOffset + end,
    text: editorBody.slice(start, end),
  }
  return articleBody.slice(mapped.start, mapped.end) === mapped.text ? mapped : null
}
