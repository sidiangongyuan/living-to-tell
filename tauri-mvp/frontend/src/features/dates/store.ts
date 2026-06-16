import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { datesApi, type DailyStat, type DailyEntrySummary, type DailyQuote } from '../../api/dates'

export function formatDateKey(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
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
      error.value = e instanceof Error ? e.message : String(e)
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
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  async function goToToday() {
    const today = new Date()
    const todayStr = formatDateKey(today)
    await loadMonthStats(today.getFullYear(), today.getMonth() + 1)
    await selectDate(todayStr)
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
