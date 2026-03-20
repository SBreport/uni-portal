import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as eventsApi from '@/api/events'

export interface EventRow {
  id: number; branch_name: string; category_name: string
  raw_event_name: string; display_name: string
  session_count: number; event_price: number; regular_price: number
  discount_rate: number; notes: string
  [key: string]: any
}

export const useEventsStore = defineStore('events', () => {
  const events = ref<EventRow[]>([])
  const branches = ref<any[]>([])
  const categories = ref<any[]>([])
  const loading = ref(false)
  const isFallback = ref(false)

  // 필터
  const filterBranch = ref('')
  const filterCategory = ref('')
  const filterSearch = ref('')

  const filteredEvents = computed(() => {
    let result = events.value
    if (filterBranch.value) result = result.filter((e: any) => e['지점명'] === filterBranch.value)
    if (filterCategory.value) result = result.filter((e: any) => e['카테고리'] === filterCategory.value)
    if (filterSearch.value) {
      const q = filterSearch.value.toLowerCase()
      result = result.filter((e: any) =>
        (e['이벤트명'] || '').toLowerCase().includes(q) ||
        (e['표시명'] || '').toLowerCase().includes(q)
      )
    }
    return result
  })

  async function loadAll() {
    loading.value = true
    try {
      const [evtRes, brRes, catRes] = await Promise.all([
        eventsApi.getEvents(), eventsApi.getBranches(), eventsApi.getCategories()
      ])
      events.value = evtRes.data.data || []
      isFallback.value = evtRes.data.is_fallback || false
      branches.value = brRes.data
      categories.value = catRes.data
    } finally {
      loading.value = false
    }
  }

  return {
    events, branches, categories, loading, isFallback,
    filterBranch, filterCategory, filterSearch, filteredEvents,
    loadAll,
  }
})
