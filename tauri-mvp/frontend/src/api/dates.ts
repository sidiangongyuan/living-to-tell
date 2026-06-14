/**
 * Dates API client - calendar view and daily statistics
 */
import { apiFetch, handleResponse } from './base'

export interface DailyStat {
  date: string // ISO format YYYY-MM-DD
  entry_count: number
  word_count: number
  has_curated: boolean
}

export interface DailyEntrySummary {
  id: string
  title: string
  body_preview: string
  created_at: string
  tags: string[]
  curation_status: string
}

export interface DailyQuote {
  id: string
  text: string
  source_title: string
  source_author: string
}

export const datesApi = {
  async getDailyStats(year: number, month: number): Promise<DailyStat[]> {
    const res = await apiFetch(`/api/dates/stats?year=${year}&month=${month}`)
    return handleResponse(res)
  },

  async getEntriesByDate(dateStr: string): Promise<DailyEntrySummary[]> {
    const res = await apiFetch(`/api/dates/entries?date_str=${dateStr}`)
    return handleResponse(res)
  },

  async getDailyQuote(dateStr: string): Promise<DailyQuote | null> {
    const res = await apiFetch(`/api/dates/quote?date_str=${dateStr}`)
    return handleResponse(res)
  },
}
