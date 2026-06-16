import { describe, expect, it } from 'vitest'
import { buildDailyQuoteLibraryQuery, getDailyQuoteReferenceId } from '../../src/features/dates/quoteLink'

describe('daily quote library deeplink', () => {
  it('prefers reference_id when available', () => {
    const quote = {
      id: 'quote-id',
      reference_id: 'reference-id',
      text: 'A full excerpt',
      source_title: 'Book',
      source_author: 'Author',
    }

    expect(getDailyQuoteReferenceId(quote)).toBe('reference-id')
    expect(buildDailyQuoteLibraryQuery(quote)).toEqual({
      ref: 'reference-id',
      group: 'source',
    })
  })

  it('falls back to quote id when the backend does not send reference_id yet', () => {
    const quote = {
      id: 'quote-id',
      text: 'A full excerpt',
      source_title: 'Book',
      source_author: 'Author',
    }

    expect(getDailyQuoteReferenceId(quote)).toBe('quote-id')
  })
})
