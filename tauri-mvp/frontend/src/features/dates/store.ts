import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { datesApi, type DailyStat, type DailyEntrySummary, type DailyQuote } from '../../api/dates'
import { errorMessage } from '../../api/base'

export const DAILY_QUOTE_CACHE_KEY = 'living_to_tell_daily_quote_cache'

interface DailyQuoteCache {
  text: string
  source_title: string
  source_author: string
  date: string
  updated_at: string
}

export function formatDateKey(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function cacheDailyQuote(quote: DailyQuote | null, dateStr: string) {
  if (!quote?.text?.trim()) return
  if (typeof localStorage === 'undefined') return
  const payload: DailyQuoteCache = {
    text: quote.text.trim(),
    source_title: quote.source_title || '',
    source_author: quote.source_author || '',
    date: dateStr,
    updated_at: new Date().toISOString(),
  }
  try {
    localStorage.setItem(DAILY_QUOTE_CACHE_KEY, JSON.stringify(payload))
  } catch {
    // Optional startup display data must not affect the writing flow.
  }
}

export const useDatesStore = defineStore('dates', () => {
  const selectedDate = ref<string>(formatDateKey(new Date())) // YYYY-MM-DD
  const currentYear = ref(new Date().getFullYear())
  const currentMonth = ref(new Date().getMonth() + 1) // 1-12
  const dailyStats = ref<DailyStat[]>([])
  const entriesForSelectedDate = ref<DailyEntrySummary[]>([])
  const dailyQuote = ref<DailyQuote | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const statsMap = computed(() => {
    const map = new Map<string, DailyStat>()
    dailyStats.value.forEach((s) => map.set(s.date, s))
    return map
  })

  async function loadMonthStats(year: number, month: number) {
    currentYear.value = year
    currentMonth.value = month
    loading.value = true
    error.value = null
    try {
      dailyStats.value = await datesApi.getDailyStats(year, month)
    } catch (e) {
      error.value = errorMessage(e)
    } finally {
      loading.value = false
    }
  }

  async function selectDate(dateStr: string) {
    selectedDate.value = dateStr
    loading.value = true
    error.value = null
    try {
      const [entries, quote] = await Promise.all([
        datesApi.getEntriesByDate(dateStr),
        datesApi.getDailyQuote(dateStr),
      ])
      entriesForSelectedDate.value = entries
      dailyQuote.value = quote
      cacheDailyQuote(quote, dateStr)
    } catch (e) {
      error.value = errorMessage(e)
    } finally {
      loading.value = false
    }
  }

  async function goToToday() {
    const today = new Date()
    const todayStr = formatDateKey(today)
    const year = today.getFullYear()
    const month = today.getMonth() + 1
    selectedDate.value = todayStr
    currentYear.value = year
    currentMonth.value = month
    loading.value = true
    error.value = null
    try {
      const [stats, entries, quote] = await Promise.all([
        datesApi.getDailyStats(year, month),
        datesApi.getEntriesByDate(todayStr),
        datesApi.getDailyQuote(todayStr),
      ])
      dailyStats.value = stats
      entriesForSelectedDate.value = entries
      dailyQuote.value = quote
      cacheDailyQuote(quote, todayStr)
    } catch (e) {
      error.value = errorMessage(e)
    } finally {
      loading.value = false
    }
  }

  return {
    selectedDate,
    currentYear,
    currentMonth,
    dailyStats,
    statsMap,
    entriesForSelectedDate,
    dailyQuote,
    loading,
    error,
    loadMonthStats,
    selectDate,
    goToToday,
  }
})
