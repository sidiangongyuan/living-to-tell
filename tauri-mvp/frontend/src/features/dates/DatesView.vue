<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDatesStore } from './store'
import { useI18n } from '../../i18n'

const store = useDatesStore()
const router = useRouter()
const { t } = useI18n()
const calendarRef = ref<HTMLDivElement | null>(null)

onMounted(() => {
  store.goToToday()
})

const calendarDays = computed(() => {
  const year = store.currentYear
  const month = store.currentMonth
  const firstDay = new Date(year, month - 1, 1)
  const lastDay = new Date(year, month, 0)
  const daysInMonth = lastDay.getDate()
  const startWeekday = firstDay.getDay()

  const days: Array<{
    date: string
    day?: number
    isEmpty: boolean
    count?: number
    hasCurated?: boolean
    isSelected?: boolean
    isToday?: boolean
  }> = []

  for (let i = 0; i < startWeekday; i++) {
    days.push({ date: '', isEmpty: true })
  }

  for (let day = 1; day <= daysInMonth; day++) {
    const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
    const stat = store.statsMap.get(dateStr)
    days.push({
      date: dateStr,
      day,
      isEmpty: false,
      count: stat?.entry_count || 0,
      hasCurated: stat?.has_curated || false,
      isSelected: dateStr === store.selectedDate,
      isToday: dateStr === new Date().toISOString().split('T')[0],
    })
  }
  return days
})

function prevMonth() {
  let y = store.currentYear
  let m = store.currentMonth - 1
  if (m < 1) {
    m = 12
    y -= 1
  }
  store.loadMonthStats(y, m)
}

function nextMonth() {
  let y = store.currentYear
  let m = store.currentMonth + 1
  if (m > 12) {
    m = 1
    y += 1
  }
  store.loadMonthStats(y, m)
}

function selectDay(dateStr: string) {
  if (dateStr) {
    store.selectDate(dateStr)
  }
}

function openArticle(entryId: string) {
  router.push({ name: 'articles', query: { id: entryId } })
}
</script>

<template>
  <div class="flex h-full overflow-hidden bg-gray-50">
    <aside class="flex w-96 shrink-0 flex-col border-r border-gray-200 bg-white">
      <div class="border-b border-gray-200 p-4">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-xl font-bold">
            {{ new Date(store.currentYear, store.currentMonth - 1).toLocaleDateString('zh-CN', { month: 'long', year: 'numeric' }) }}
          </h2>
          <div class="flex gap-2">
            <button @click="prevMonth" class="rounded bg-gray-100 px-3 py-1 transition-colors hover:bg-gray-200">‹</button>
            <button @click="store.goToToday()" class="rounded bg-blue-600 px-3 py-1 text-sm text-white transition-colors hover:bg-blue-700">
              {{ t('dates.today') }}
            </button>
            <button @click="nextMonth" class="rounded bg-gray-100 px-3 py-1 transition-colors hover:bg-gray-200">›</button>
          </div>
        </div>

        <div ref="calendarRef" class="grid grid-cols-7 gap-1">
          <div v-for="day in ['日', '一', '二', '三', '四', '五', '六']" :key="day" class="py-2 text-center text-xs font-semibold text-gray-500">
            {{ day }}
          </div>
          <div
            v-for="(d, idx) in calendarDays"
            :key="idx"
            @click="selectDay(d.date)"
            :class="[
              'relative flex aspect-square cursor-pointer flex-col items-center justify-center rounded transition-colors',
              d.isEmpty ? 'pointer-events-none' : '',
              d.isSelected ? 'bg-blue-600 font-bold text-white' : d.isToday ? 'bg-blue-100 text-blue-900' : 'hover:bg-gray-100',
              (d.count ?? 0) > 0 && !d.isSelected ? 'font-semibold' : '',
            ]"
          >
            <span v-if="!d.isEmpty" class="text-sm">{{ d.day }}</span>
            <span v-if="(d.count ?? 0) > 0 && !d.isSelected" class="text-xs text-gray-500">{{ d.count }}</span>
            <div v-if="d.hasCurated && !d.isSelected" class="absolute bottom-1 h-1 w-1 rounded-full bg-green-500"></div>
          </div>
        </div>
      </div>

      <div v-if="store.dailyQuote" class="border-b border-gray-200 bg-blue-50 p-4">
        <p class="mb-2 text-sm italic text-gray-700">"{{ store.dailyQuote.text }}"</p>
        <p class="text-xs text-gray-500">
          — 《{{ store.dailyQuote.source_title }}》
          <span v-if="store.dailyQuote.source_author">{{ store.dailyQuote.source_author }}</span>
        </p>
      </div>
    </aside>

    <div class="flex min-w-0 flex-1 flex-col overflow-hidden bg-white">
      <div class="border-b border-gray-200 p-6">
        <h2 class="text-2xl font-bold">
          {{ new Date(store.selectedDate).toLocaleDateString('zh-CN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }) }}
        </h2>
        <p class="mt-1 text-sm text-gray-500">
          {{ store.entriesForSelectedDate.length }} {{ store.entriesForSelectedDate.length === 1 ? t('dates.entry') : t('dates.entries') }}
        </p>
      </div>

      <div class="flex-1 overflow-y-auto p-6">
        <div v-if="store.loading" class="mt-20 text-center text-gray-400">{{ t('common.loading') }}</div>
        <div v-else-if="store.error" class="mt-20 text-center text-red-500">{{ store.error }}</div>
        <div v-else-if="!store.entriesForSelectedDate.length" class="mt-20 text-center text-gray-400">
          {{ t('dates.noEntries') }}
        </div>
        <div v-else class="space-y-4">
          <article
            v-for="entry in store.entriesForSelectedDate"
            :key="entry.id"
            @click="openArticle(entry.id)"
            class="cursor-pointer rounded-lg border border-gray-200 bg-white p-4 transition-all hover:border-blue-500 hover:shadow-md"
          >
            <h3 class="mb-2 text-lg font-bold">{{ entry.title }}</h3>
            <p class="mb-3 line-clamp-2 text-sm text-gray-600">{{ entry.body_preview }}</p>
            <div class="flex items-center gap-2">
              <span
                v-for="tag in entry.tags"
                :key="tag"
                class="rounded bg-blue-100 px-2 py-1 text-xs text-blue-700"
              >{{ tag }}</span>
              <span
                v-if="entry.curation_status !== 'unsorted'"
                class="rounded bg-green-100 px-2 py-1 text-xs text-green-700"
              >{{ entry.curation_status }}</span>
            </div>
          </article>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
