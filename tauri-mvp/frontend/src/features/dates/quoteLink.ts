import type { DailyQuote } from '../../api/dates'

export function getDailyQuoteReferenceId(quote: DailyQuote): string {
  return quote.reference_id || quote.id
}

export function buildDailyQuoteLibraryQuery(quote: DailyQuote) {
  return {
    ref: getDailyQuoteReferenceId(quote),
    group: 'source' as const,
  }
}
