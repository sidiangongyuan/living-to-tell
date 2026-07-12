import { describe, expect, it } from 'vitest'
import {
  ARTICLE_EDITOR_POSITIONS_KEY,
  COMFORT_ANCHOR_RATIO,
  editorTailSpace,
  estimateScrollTopForPosition,
  getLastSelectedArticleId,
  getArticleEditorPosition,
  getArticleEditorPositionSlots,
  getPreferredArticleEditorPosition,
  insertIndentedParagraph,
  isNearArticleEnd,
  LAST_SELECTED_ARTICLE_KEY,
  PARAGRAPH_INDENT,
  saveLastSelectedArticleId,
  saveArticleEditorPosition,
  shouldRecenterCaret,
} from './editorPosition'

class MemoryStorage {
  private values = new Map<string, string>()

  getItem(key: string): string | null {
    return this.values.get(key) ?? null
  }

  setItem(key: string, value: string): void {
    this.values.set(key, value)
  }
}

describe('article editor position helpers', () => {
  it('inserts a new indented paragraph at the cursor', () => {
    const result = insertIndentedParagraph('第一段。第二段。', 4, 4)

    expect(result.text).toBe(`第一段。\n${PARAGRAPH_INDENT}第二段。`)
    expect(result.selectionStart).toBe(7)
    expect(result.selectionEnd).toBe(7)
  })

  it('replaces the current selection with a new indented paragraph', () => {
    const result = insertIndentedParagraph('第一段。旧内容。第二段。', 4, 8)

    expect(result.text).toBe(`第一段。\n${PARAGRAPH_INDENT}第二段。`)
    expect(result.selectionStart).toBe(7)
    expect(result.selectionEnd).toBe(7)
  })

  it('stores and reads edit positions per article', () => {
    const storage = new MemoryStorage()

    saveArticleEditorPosition('a1', { selectionStart: 12, selectionEnd: 15, scrollTop: 320 }, 'edit', storage)
    saveArticleEditorPosition('a2', { selectionStart: 1, selectionEnd: 1, scrollTop: 20 }, storage)

    expect(getArticleEditorPosition('a1', storage)).toMatchObject({
      selectionStart: 12,
      selectionEnd: 15,
      scrollTop: 320,
      interaction: 'edit',
    })
    expect(getArticleEditorPosition('a2', storage)).toMatchObject({
      selectionStart: 1,
      selectionEnd: 1,
      scrollTop: 20,
    })
  })

  it('uses an injected storage without requiring the browser localStorage global', () => {
    const storage = new MemoryStorage()
    const descriptor = Object.getOwnPropertyDescriptor(globalThis, 'localStorage')
    Reflect.deleteProperty(globalThis, 'localStorage')

    try {
      saveArticleEditorPosition('a1', { selectionStart: 3, selectionEnd: 3, scrollTop: 40 }, storage)
      expect(getArticleEditorPosition('a1', storage)?.selectionStart).toBe(3)
    } finally {
      if (descriptor) Object.defineProperty(globalThis, 'localStorage', descriptor)
    }
  })

  it('keeps edit and read positions in separate slots', () => {
    const storage = new MemoryStorage()

    saveArticleEditorPosition('a1', { selectionStart: 50, selectionEnd: 50, scrollTop: 200 }, 'edit', storage)
    saveArticleEditorPosition('a1', { selectionStart: 0, selectionEnd: 0, scrollTop: 900 }, 'read', storage)

    const slots = getArticleEditorPositionSlots('a1', storage)
    expect(slots?.edit).toMatchObject({ selectionStart: 50, selectionEnd: 50, scrollTop: 200 })
    expect(slots?.read).toMatchObject({ selectionStart: 0, selectionEnd: 0, scrollTop: 900 })
  })

  it('restores newer read scroll while preserving the last edit cursor', () => {
    const storage = new MemoryStorage()

    saveArticleEditorPosition('a1', {
      selectionStart: 50,
      selectionEnd: 50,
      scrollTop: 200,
      updatedAt: 1000,
    }, 'edit', storage)
    saveArticleEditorPosition('a1', {
      selectionStart: 0,
      selectionEnd: 0,
      scrollTop: 900,
      updatedAt: 2000,
    }, 'read', storage)

    expect(getPreferredArticleEditorPosition('a1', storage)).toMatchObject({
      interaction: 'read',
      selectionStart: 50,
      selectionEnd: 50,
      scrollTop: 900,
    })
  })

  it('uses edit when it is the most recent position slot', () => {
    const storage = new MemoryStorage()

    saveArticleEditorPosition('a1', {
      selectionStart: 0,
      selectionEnd: 0,
      scrollTop: 900,
      updatedAt: 1000,
    }, 'read', storage)
    saveArticleEditorPosition('a1', {
      selectionStart: 50,
      selectionEnd: 50,
      scrollTop: 200,
      updatedAt: 2000,
    }, 'edit', storage)

    expect(getPreferredArticleEditorPosition('a1', storage)).toMatchObject({
      interaction: 'edit',
      selectionStart: 50,
      scrollTop: 200,
    })
  })

  it('falls back to read when no edit position exists', () => {
    const storage = new MemoryStorage()

    saveArticleEditorPosition('a1', { selectionStart: 0, selectionEnd: 0, scrollTop: 900 }, 'read', storage)

    expect(getPreferredArticleEditorPosition('a1', storage)).toMatchObject({
      interaction: 'read',
      scrollTop: 900,
    })
  })

  it('reads legacy single-slot positions as edit positions', () => {
    const storage = new MemoryStorage()
    storage.setItem(ARTICLE_EDITOR_POSITIONS_KEY, JSON.stringify({
      a1: { selectionStart: 11, selectionEnd: 12, scrollTop: 240, updatedAt: 1000 },
    }))

    expect(getArticleEditorPositionSlots('a1', storage)?.edit).toMatchObject({
      selectionStart: 11,
      selectionEnd: 12,
      scrollTop: 240,
    })
    expect(getPreferredArticleEditorPosition('a1', storage)).toMatchObject({
      interaction: 'edit',
      selectionStart: 11,
    })
  })

  it('treats invalid stored JSON as empty', () => {
    const storage = new MemoryStorage()
    storage.setItem(ARTICLE_EDITOR_POSITIONS_KEY, '{bad')

    expect(getArticleEditorPosition('a1', storage)).toBeNull()
  })

  it('stores the last selected article id', () => {
    const storage = new MemoryStorage()

    expect(getLastSelectedArticleId(storage)).toBeNull()
    saveLastSelectedArticleId('a2', storage)

    expect(storage.getItem(LAST_SELECTED_ARTICLE_KEY)).toBe('a2')
    expect(getLastSelectedArticleId(storage)).toBe('a2')
  })

  it('detects positions close to the article end', () => {
    expect(isNearArticleEnd({
      textLength: 1000,
      selectionEnd: 990,
      scrollTop: 0,
      scrollHeight: 2000,
      clientHeight: 500,
    })).toBe(true)
    expect(isNearArticleEnd({
      textLength: 1000,
      selectionEnd: 300,
      scrollTop: 1470,
      scrollHeight: 2000,
      clientHeight: 500,
    })).toBe(true)
    expect(isNearArticleEnd({
      textLength: 1000,
      selectionEnd: 300,
      scrollTop: 200,
      scrollHeight: 2000,
      clientHeight: 500,
    })).toBe(false)
  })

  it('estimates a comfortable scroll position below center', () => {
    const text = Array.from({ length: 40 }, (_, index) => `第${index + 1}行`).join('\n')
    const position = text.length

    expect(estimateScrollTopForPosition({
      text,
      position,
      clientHeight: 560,
      lineHeight: 28,
      anchorRatio: COMFORT_ANCHOR_RATIO,
    })).toBeCloseTo(795.2)
  })

  it('keeps tail breathing space within useful bounds', () => {
    expect(editorTailSpace(300)).toBe(220)
    expect(editorTailSpace(800)).toBe(368)
    expect(editorTailSpace(2000)).toBe(520)
  })

  it('only recenters when the caret passes the comfort line', () => {
    expect(shouldRecenterCaret({
      caretScrollTop: 700,
      currentScrollTop: 100,
      clientHeight: 800,
    })).toBe(true)
    expect(shouldRecenterCaret({
      caretScrollTop: 500,
      currentScrollTop: 100,
      clientHeight: 800,
    })).toBe(false)
  })
})
