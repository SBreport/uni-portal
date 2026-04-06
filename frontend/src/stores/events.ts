import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as eventsApi from '@/api/events'
import { useBranchStore } from '@/stores/branches'

export interface EventRow {
  id: number; branch_name: string; category_name: string
  raw_event_name: string; display_name: string
  session_count: number; event_price: number; regular_price: number
  discount_rate: number; notes: string
  [key: string]: any
}

export const useEventsStore = defineStore('events', () => {
  const branchStore = useBranchStore()
  const events = ref<EventRow[]>([])
  // Expose branches from shared store for backwards compatibility
  const branches = computed(() => branchStore.branches)
  const categories = ref<any[]>([])
  const loading = ref(false)
  const isFallback = ref(false)

  // 필터
  const filterBranch = ref('')
  const filterCategory = ref('')
  const filterSearch = ref('')
  const filterGlobal = ref('')
  const filterPriceMin = ref<number | null>(null)
  const filterPriceMax = ref<number | null>(null)

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
    // 가격대 필터
    if (filterPriceMin.value != null && filterPriceMin.value > 0) {
      const min = filterPriceMin.value * 10000
      result = result.filter((e: any) => (e['이벤트가'] || 0) >= min)
    }
    if (filterPriceMax.value != null && filterPriceMax.value > 0) {
      const max = filterPriceMax.value * 10000
      result = result.filter((e: any) => (e['이벤트가'] || 0) <= max)
    }
    // 테이블 전체 검색
    if (filterGlobal.value) {
      const q = filterGlobal.value.toLowerCase()
      result = result.filter((e: any) =>
        Object.values(e).some(v => String(v ?? '').toLowerCase().includes(q))
      )
    }
    return result
  })

  async function loadAll() {
    loading.value = true
    try {
      const [evtRes, catRes] = await Promise.all([
        eventsApi.getEvents(), eventsApi.getCategories(),
        branchStore.loadBranches(),
      ])
      events.value = evtRes.data.data || []
      isFallback.value = evtRes.data.is_fallback || false
      categories.value = catRes.data
    } finally {
      loading.value = false
    }
  }

  return {
    events, branches, categories, loading, isFallback,
    filterBranch, filterCategory, filterSearch, filterGlobal,
    filterPriceMin, filterPriceMax, filteredEvents,
    loadAll,
  }
})
