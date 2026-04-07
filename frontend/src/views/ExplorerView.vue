<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useBranchStore } from '@/stores/branches'
import { useAuthStore } from '@/stores/auth'
import * as explorerApi from '@/api/explorer'
import TabBar from '@/components/common/TabBar.vue'
import FilterSelect from '@/components/common/FilterSelect.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ExplorerDeviceInline from '@/components/explorer/ExplorerDeviceInline.vue'

// ── 스토어 ──────────────────────────────────────────────────────────────────
const branchStore = useBranchStore()
const auth = useAuthStore()
const canSeeAuthor = computed(() => ['admin', 'editor'].includes(auth.effectiveRole))

onMounted(async () => {
  await branchStore.loadBranches()
  loadDeviceList()
  loadDevicesSummary()
})

// ── 탭 ──────────────────────────────────────────────────────────────────────
const tabs = [
  { key: 'branch',    label: '지점별' },
  { key: 'treatment', label: '시술별' },
  { key: 'device',    label: '장비별' },
  { key: 'papers',    label: '논문' },
]
const activeTab = ref('branch')

// ── 가격 포맷 헬퍼 ──────────────────────────────────────────────────────────
function formatPrice(price?: number | null): string {
  if (!price) return '-'
  return `${(price / 10000).toFixed(0)}만`
}

// ── 통합 검색창 (드롭다운 방식) ─────────────────────────────────────────────
const searchQuery = ref('')
const searchResults = ref<any>(null)
const searchLoading = ref(false)
const showDropdown = ref(false)
let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null

watch(searchQuery, (q) => {
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  if (q.trim().length < 2) {
    searchResults.value = null
    showDropdown.value = false
    return
  }
  searchDebounceTimer = setTimeout(async () => {
    searchLoading.value = true
    showDropdown.value = true
    try {
      searchResults.value = await explorerApi.search(q.trim())
    } catch (e) {
      console.error('[Explorer] 검색 실패:', e)
    } finally {
      searchLoading.value = false
    }
  }, 400)
})

function clearSearch() {
  searchQuery.value = ''
  searchResults.value = null
  showDropdown.value = false
}

function closeDropdown() {
  showDropdown.value = false
}

function goToBranch(id: number) {
  selectedBranchId.value = String(id)
  activeTab.value = 'branch'
  closeDropdown()
  clearSearch()
}

function goToDevice(id: number) {
  expandedDeviceId.value = expandedDeviceId.value === id ? null : id
  activeTab.value = 'device'
  closeDropdown()
  clearSearch()
}

function goToPaper(id: number) {
  expandedPaperId.value = expandedPaperId.value === id ? null : id
  activeTab.value = 'papers'
  closeDropdown()
  clearSearch()
}

const hasAnySearchResult = computed(() => {
  if (!searchResults.value) return false
  const r = searchResults.value
  return !!(r.branches?.length || r.devices?.length || r.events?.length ||
    r.treatments?.length || r.papers?.length || r.blog_posts?.length)
})

// 외부 클릭시 드롭다운 닫기
function handleOutsideClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (!target.closest('[data-search-container]')) {
    closeDropdown()
  }
}
onMounted(() => document.addEventListener('click', handleOutsideClick))
onBeforeUnmount(() => document.removeEventListener('click', handleOutsideClick))

// ── Tab 1: 지점별 ────────────────────────────────────────────────────────────
const branchOptions = computed(() =>
  branchStore.branches.map(b => ({ value: String(b.id), label: b.name }))
)
const selectedBranchId = ref('')
const branchSearchQuery = ref('')
const filteredBranches = computed(() => {
  const q = branchSearchQuery.value.trim().toLowerCase()
  const list = branchStore.branches
  if (!q) return list
  return list.filter(b =>
    b.name.toLowerCase().includes(q) ||
    (b.short_name?.toLowerCase().includes(q) ?? false)
  )
})
const branchLoading = ref(false)
const branchData = ref<any>(null)

// 지점별 섹션 토글 상태
const openBranch = ref<Record<string, boolean>>({
  equip: false,
  events: false,
  blogs: false,
  place: false,
})

function toggleBranch(key: string) {
  openBranch.value[key] = !openBranch.value[key]
}

// 지점별 장비 인라인 확장 (인덱스 기반 — 동일 device_info_id 장비가 여러 개일 수 있음)
const expandedEquipIdx = ref<number | null>(null)

watch(selectedBranchId, async (id) => {
  expandedEquipIdx.value = null
  branchData.value = null
  if (!id) return
  branchLoading.value = true
  try {
    branchData.value = await explorerApi.getByBranch(Number(id))
  } catch (e) {
    console.error('[Explorer] 지점 로드 실패:', e)
  } finally {
    branchLoading.value = false
  }
})

function toggleEquip(idx: number) {
  expandedEquipIdx.value = expandedEquipIdx.value === idx ? null : idx
}

// 블로그: 브블/최블 분리
const brandBlogs = computed(() =>
  (branchData.value?.recent_blogs ?? []).filter((b: any) => b.blog_channel === 'br')
)
const optimalBlogs = computed(() =>
  (branchData.value?.recent_blogs ?? []).filter((b: any) => b.blog_channel === 'opt' || b.blog_channel !== 'br')
)

// 이벤트: API가 events_by_category 딕셔너리를 직접 반환
const eventsByCategory = computed(() => branchData.value?.events_by_category ?? {})

// 플레이스 요약: 평균 순위 + 키워드 수
const placeSummary = computed(() => {
  const kws = branchData.value?.place_keywords
  if (!kws?.length) return null
  const rankedKws = kws.filter((k: any) => k.rank && k.rank > 0)
  const avgRank = rankedKws.length
    ? Math.round(rankedKws.reduce((sum: number, k: any) => sum + k.rank, 0) / rankedKws.length * 10) / 10
    : null
  return { avgRank, total: kws.length, ranked: rankedKws.length }
})

// 웹페이지 요약: 노출/미노출
const webpageSummary = computed(() => {
  const kws = branchData.value?.webpage_keywords
  if (!kws?.length) return null
  const exposed = kws.filter((k: any) => k.is_exposed).length
  const notExposed = kws.length - exposed
  return { exposed, notExposed, total: kws.length }
})

const eventCount = computed(() => {
  const bycat = branchData.value?.events_by_category
  if (!bycat) return 0
  return Object.values(bycat).reduce((sum: number, arr: any) => sum + (arr?.length ?? 0), 0)
})

// ── Tab 2: 시술별 (카테고리별) ───────────────────────────────────────────────
const CATEGORIES = [
  { id: 1,  name: '리프팅' },
  { id: 2,  name: '보톡스' },
  { id: 3,  name: '필러' },
  { id: 4,  name: '레이저' },
  { id: 5,  name: '피부관리' },
  { id: 6,  name: '실리프팅' },
  { id: 7,  name: '지방분해' },
  { id: 8,  name: '체형관리' },
  { id: 9,  name: '탈모' },
  { id: 10, name: '여드름' },
  { id: 11, name: '흉터/모공' },
  { id: 12, name: '미백/톤업' },
  { id: 13, name: '눈/코' },
  { id: 14, name: '안티에이징' },
  { id: 15, name: '제모' },
  { id: 16, name: '기타' },
]

const selectedCategoryId = ref<number | null>(null)
const categoryLoading = ref(false)
const categoryData = ref<any>(null)

async function selectCategory(catId: number) {
  if (selectedCategoryId.value === catId) {
    selectedCategoryId.value = null
    categoryData.value = null
    return
  }
  selectedCategoryId.value = catId
  categoryLoading.value = true
  categoryData.value = null
  try {
    categoryData.value = await explorerApi.getByCategory(catId)
  } catch (e) {
    console.error('[Explorer] 카테고리 로드 실패:', e)
  } finally {
    categoryLoading.value = false
  }
}

function goToDeviceFromCategory(deviceInfoId: number) {
  expandedDeviceId.value = deviceInfoId
  activeTab.value = 'device'
}

// ── Tab 3: 장비별 ────────────────────────────────────────────────────────────
const deviceSearch = ref('')
const deviceListLoading = ref(false)
const deviceList = ref<Array<{ id: number; name: string; category?: string }>>([])
const expandedDeviceId = ref<number | null>(null)

const filteredDevices = computed(() => {
  const q = deviceSearch.value.trim().toLowerCase()
  if (!q) return deviceList.value
  return deviceList.value.filter(d =>
    d.name.toLowerCase().includes(q) ||
    (d.category?.toLowerCase().includes(q) ?? false)
  )
})

async function loadDeviceList() {
  deviceListLoading.value = true
  try {
    deviceList.value = await explorerApi.listDevices()
  } catch {
    deviceList.value = []
  } finally {
    deviceListLoading.value = false
  }
}

function toggleDevice(id: number) {
  expandedDeviceId.value = expandedDeviceId.value === id ? null : id
}

// ── Tab 4: 논문 ─────────────────────────────────────────────────────────────
const paperSearch = ref('')
const paperDeviceFilter = ref('')
const paperLoading = ref(false)
const papers = ref<any[]>([])
const expandedPaperId = ref<number | null>(null)
const devicesSummary = ref<Array<{ id: number; name: string; paper_count: number }>>([])

const deviceFilterOptions = computed(() =>
  devicesSummary.value.map(d => ({ value: String(d.id), label: `${d.name} (${d.paper_count})` }))
)

async function loadDevicesSummary() {
  try {
    devicesSummary.value = await explorerApi.getDevicesSummary()
  } catch {
    devicesSummary.value = []
  }
}

let paperDebounceTimer: ReturnType<typeof setTimeout> | null = null

watch([paperSearch, paperDeviceFilter], () => {
  if (paperDebounceTimer) clearTimeout(paperDebounceTimer)
  paperDebounceTimer = setTimeout(loadPapers, 350)
})

watch(() => activeTab.value, (tab) => {
  if (tab === 'papers' && !papers.value.length) loadPapers()
})

async function loadPapers() {
  paperLoading.value = true
  try {
    papers.value = await explorerApi.listPapers({
      q: paperSearch.value.trim() || undefined,
      device_info_id: paperDeviceFilter.value ? Number(paperDeviceFilter.value) : undefined,
    })
  } catch (e) {
    console.error('[Explorer] 논문 로드 실패:', e)
  } finally {
    paperLoading.value = false
  }
}

function togglePaper(id: number) {
  expandedPaperId.value = expandedPaperId.value === id ? null : id
}
</script>

<template>
  <div class="p-5 max-w-4xl">

    <!-- 헤더 -->
    <div class="mb-5">
      <h2 class="text-xl font-bold text-slate-800">탐색기</h2>
      <p class="text-sm text-slate-400 mt-1">지점 · 시술 · 장비 · 논문을 중심으로 연결된 정보를 탐색합니다</p>
    </div>

    <!-- 통합 검색창 (드롭다운) -->
    <div class="relative mb-5" data-search-container>
      <div class="absolute inset-y-0 left-3 flex items-center pointer-events-none">
        <svg class="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24"
          stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round"
            d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
        </svg>
      </div>
      <input
        v-model="searchQuery"
        type="text"
        placeholder="장비명, 지점명, 시술명, 키워드 통합 검색... (2자 이상)"
        class="w-full pl-9 pr-10 py-2.5 border border-slate-300 rounded-lg text-sm bg-white
               focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
        @focus="showDropdown = searchResults !== null"
      />
      <button
        v-if="searchQuery"
        @click="clearSearch"
        class="absolute inset-y-0 right-3 flex items-center text-slate-400 hover:text-slate-600 transition"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      <!-- 검색 드롭다운 -->
      <div
        v-if="showDropdown && searchQuery.length >= 2"
        class="absolute top-full left-0 right-0 z-50 bg-white border border-slate-200 rounded-lg shadow-lg max-h-96 overflow-auto mt-1"
      >
        <!-- 로딩 -->
        <div v-if="searchLoading" class="px-4 py-3 text-sm text-slate-400 text-center">
          검색 중...
        </div>

        <!-- 결과 없음 -->
        <div v-else-if="searchResults && !hasAnySearchResult"
          class="px-4 py-3 text-sm text-slate-400 text-center">
          '{{ searchQuery }}' 검색 결과가 없습니다
        </div>

        <template v-else-if="searchResults">
          <!-- 지점 -->
          <template v-if="searchResults.branches?.length">
            <p class="px-3 py-1.5 text-xs font-bold text-slate-400 bg-slate-50 sticky top-0">지점</p>
            <button
              v-for="b in searchResults.branches"
              :key="b.id"
              @click="goToBranch(b.id)"
              class="w-full text-left px-4 py-2 hover:bg-blue-50 text-sm text-slate-700 flex items-center justify-between"
            >
              <span>{{ b.name }}</span>
            </button>
          </template>

          <!-- 장비 -->
          <template v-if="searchResults.devices?.length">
            <p class="px-3 py-1.5 text-xs font-bold text-slate-400 bg-slate-50 sticky top-0">장비</p>
            <button
              v-for="d in searchResults.devices"
              :key="d.id"
              @click="goToDevice(d.id)"
              class="w-full text-left px-4 py-2 hover:bg-blue-50 flex items-center gap-2"
            >
              <span class="text-sm text-slate-700">{{ d.name }}</span>
              <span v-if="d.category"
                class="text-xs px-1.5 py-0.5 bg-blue-50 text-blue-500 rounded">
                {{ d.category }}
              </span>
            </button>
          </template>

          <!-- 이벤트 -->
          <template v-if="searchResults.events?.length">
            <p class="px-3 py-1.5 text-xs font-bold text-slate-400 bg-slate-50 sticky top-0">이벤트</p>
            <div
              v-for="ev in searchResults.events"
              :key="ev.id"
              class="px-4 py-2 border-b border-slate-50 last:border-0"
            >
              <p class="text-sm text-slate-700">{{ ev.display_name }}</p>
              <div class="flex items-center gap-2 mt-0.5">
                <span v-if="ev.branch_name" class="text-xs text-slate-400">{{ ev.branch_name }}</span>
                <span v-if="ev.event_price" class="text-xs text-red-500 font-bold">{{ formatPrice(ev.event_price) }}</span>
              </div>
            </div>
          </template>

          <!-- 논문 -->
          <template v-if="searchResults.papers?.length">
            <p class="px-3 py-1.5 text-xs font-bold text-slate-400 bg-slate-50 sticky top-0">논문</p>
            <button
              v-for="p in searchResults.papers"
              :key="p.id"
              @click="goToPaper(p.id)"
              class="w-full text-left px-4 py-2 hover:bg-blue-50"
            >
              <p class="text-sm text-slate-700 leading-snug">{{ p.title_ko || p.title }}</p>
            </button>
          </template>

          <!-- 블로그 -->
          <template v-if="searchResults.blog_posts?.length">
            <p class="px-3 py-1.5 text-xs font-bold text-slate-400 bg-slate-50 sticky top-0">블로그</p>
            <div
              v-for="b in searchResults.blog_posts"
              :key="b.id"
              class="px-4 py-2 border-b border-slate-50 last:border-0"
            >
              <p class="text-sm text-slate-700 leading-snug">{{ b.title }}</p>
              <span v-if="b.keyword" class="text-xs text-blue-500">{{ b.keyword }}</span>
            </div>
          </template>
        </template>
      </div>
    </div>

    <!-- 탭 -->
    <TabBar :tabs="tabs" v-model="activeTab" />

    <!-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Tab 1: 지점별 -->
    <div v-if="activeTab === 'branch'" class="space-y-4">

      <!-- 지점 선택: 검색 + 카드 그리드 -->
      <div v-if="!selectedBranchId">
        <input
          v-model="branchSearchQuery"
          type="text"
          placeholder="지점명 검색..."
          class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-1 focus:ring-blue-500 mb-3"
        />
        <div class="grid grid-cols-6 gap-2">
          <button
            v-for="b in filteredBranches"
            :key="b.id"
            @click="selectedBranchId = String(b.id); branchSearchQuery = ''"
            class="px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm text-slate-700
                   hover:border-blue-400 hover:bg-blue-50 transition text-center truncate"
          >
            {{ b.name }}
          </button>
        </div>
        <p v-if="filteredBranches.length === 0" class="text-sm text-slate-400 mt-2">검색 결과 없음</p>
      </div>

      <!-- 선택된 지점: 뒤로가기 + 로딩 + 데이터 -->
      <template v-if="selectedBranchId">
        <div class="flex items-center gap-2 mb-3">
          <button
            @click="selectedBranchId = ''"
            class="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
          >
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
            지점 목록으로
          </button>
        </div>

        <!-- 로딩 -->
        <div v-if="branchLoading" class="flex justify-center py-10">
          <LoadingSpinner message="지점 정보 로딩 중..." />
        </div>

        <!-- 지점 데이터 -->
        <template v-else-if="branchData">

        <!-- 지점명 + 요약 카드 행 -->
        <div>
          <h3 class="text-base font-bold text-slate-800 mb-3">
            {{ branchData.branch?.name ?? '지점 정보' }}
            <span v-if="branchData.branch?.region_name"
              class="text-sm font-normal text-slate-400 ml-2">
              {{ branchData.branch.region_name }}
            </span>
          </h3>
          <div class="grid grid-cols-3 gap-3">
            <button @click="toggleBranch('equip')"
              class="bg-white border border-slate-200 rounded-lg p-3 text-center hover:border-blue-300 transition">
              <p class="text-xl font-bold text-blue-600">{{ branchData.equipment?.length ?? 0 }}</p>
              <p class="text-xs text-slate-400 mt-0.5">보유 장비</p>
            </button>
            <button @click="toggleBranch('events')"
              class="bg-white border border-slate-200 rounded-lg p-3 text-center hover:border-amber-300 transition">
              <p class="text-xl font-bold text-amber-500">{{ eventCount }}</p>
              <p class="text-xs text-slate-400 mt-0.5">이벤트</p>
            </button>
            <button @click="toggleBranch('blogs')"
              class="bg-white border border-slate-200 rounded-lg p-3 text-center hover:border-emerald-300 transition">
              <p class="text-lg font-bold text-emerald-600">{{ branchData.blog_summary?.total ?? 0 }}</p>
              <p class="text-[10px] text-slate-400 mt-0.5">
                브블 {{ branchData.blog_summary?.brand_count ?? 0 }} · 최블 {{ branchData.blog_summary?.optimal_count ?? 0 }}
              </p>
            </button>
          </div>
          <div class="grid grid-cols-3 gap-3 mt-3">
            <button @click="placeSummary ? toggleBranch('place') : null"
              :class="['bg-white border rounded-lg p-3 text-center transition',
                placeSummary ? 'border-slate-200 hover:border-sky-300 cursor-pointer' : 'border-slate-100 cursor-default']">
              <template v-if="placeSummary">
                <p class="text-xl font-bold"
                  :class="placeSummary.avgRank && placeSummary.avgRank <= 5 ? 'text-sky-600' : placeSummary.avgRank && placeSummary.avgRank <= 10 ? 'text-amber-500' : 'text-slate-400'">
                  {{ placeSummary.avgRank ?? '-' }}<span class="text-xs font-normal text-slate-400">위</span>
                </p>
                <p class="text-[10px] text-slate-400 mt-0.5">{{ placeSummary.total }}개 키워드 평균</p>
              </template>
              <template v-else>
                <p class="text-xs text-slate-300 py-1">진행하지 않음</p>
              </template>
              <p class="text-xs text-slate-400 mt-0.5">플레이스</p>
            </button>
            <button @click="webpageSummary ? toggleBranch('place') : null"
              :class="['bg-white border rounded-lg p-3 text-center transition',
                webpageSummary ? 'border-slate-200 hover:border-indigo-300 cursor-pointer' : 'border-slate-100 cursor-default']">
              <template v-if="webpageSummary">
                <p class="text-sm font-bold">
                  <span class="text-indigo-600">{{ webpageSummary.exposed }}</span>
                  <span class="text-xs text-slate-400 font-normal">노출</span>
                  <span class="text-red-400 ml-1">{{ webpageSummary.notExposed }}</span>
                  <span class="text-xs text-slate-400 font-normal">미노출</span>
                </p>
                <p class="text-[10px] text-slate-400 mt-0.5">{{ webpageSummary.total }}개 키워드</p>
              </template>
              <template v-else>
                <p class="text-xs text-slate-300 py-1">진행하지 않음</p>
              </template>
              <p class="text-xs text-slate-400 mt-0.5">웹페이지</p>
            </button>
            <div class="bg-white border border-slate-200 rounded-lg p-3 text-center">
              <p class="text-xl font-bold text-rose-500">{{ branchData.complaints_open ?? 0 }}</p>
              <p class="text-xs text-slate-400 mt-0.5">미처리 민원</p>
            </div>
          </div>
        </div>

        <!-- 보유 장비 (접이식) -->
        <section class="border border-slate-200 rounded-lg overflow-hidden">
          <button
            @click="toggleBranch('equip')"
            class="w-full flex items-center justify-between px-4 py-3 bg-white hover:bg-slate-50 transition text-left"
          >
            <span class="font-semibold text-sm text-slate-700">보유 장비</span>
            <div class="flex items-center gap-2">
              <span class="text-xs bg-blue-100 text-blue-600 font-bold px-2 py-0.5 rounded-full">
                {{ branchData.equipment?.length ?? 0 }}종
              </span>
              <svg class="w-4 h-4 text-slate-400 transition-transform"
                :class="{ 'rotate-180': openBranch.equip }"
                fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </button>
          <div v-if="openBranch.equip" class="divide-y divide-slate-100 bg-white">
            <template v-if="branchData.equipment?.length">
              <div
                v-for="(e, idx) in branchData.equipment"
                :key="idx"
                class="border-b border-slate-50 last:border-0"
              >
                <div
                  @click="e.device_info_id ? toggleEquip(idx as number) : null"
                  :class="[
                    'flex items-center justify-between px-4 py-2.5 transition',
                    e.device_info_id ? 'cursor-pointer hover:bg-blue-50' : 'cursor-default',
                    expandedEquipIdx === idx ? 'bg-blue-50' : ''
                  ]"
                >
                  <div>
                    <span class="text-sm font-medium text-slate-700">{{ e.name }}</span>
                    <span v-if="e.device_category" class="ml-2 text-xs text-slate-400">{{ e.device_category }}</span>
                  </div>
                  <div class="flex items-center gap-2 text-xs text-slate-400">
                    <span>{{ e.quantity }}대</span>
                    <svg v-if="e.device_info_id"
                      class="w-3.5 h-3.5 text-slate-300 transition-transform"
                      :class="{ 'rotate-180': expandedEquipIdx === idx }"
                      fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
                    </svg>
                  </div>
                </div>
                <!-- 인라인 확장 -->
                <div
                  v-if="e.device_info_id && expandedEquipIdx === idx"
                  class="px-4 pb-4 pt-1 bg-slate-50 border-t border-slate-100"
                >
                  <ExplorerDeviceInline :device-id="e.device_info_id" :current-branch-name="branchData?.branch?.name" />
                </div>
              </div>
            </template>
            <p v-else class="px-4 py-3 text-sm text-slate-400">보유 장비 없음</p>
          </div>
        </section>

        <!-- 이벤트 (접이식, 카테고리별) -->
        <section class="border border-slate-200 rounded-lg overflow-hidden">
          <button
            @click="toggleBranch('events')"
            class="w-full flex items-center justify-between px-4 py-3 bg-white hover:bg-slate-50 transition text-left"
          >
            <span class="font-semibold text-sm text-slate-700">이벤트</span>
            <div class="flex items-center gap-2">
              <span class="text-xs bg-amber-100 text-amber-600 font-bold px-2 py-0.5 rounded-full">
                {{ eventCount }}건
              </span>
              <svg class="w-4 h-4 text-slate-400 transition-transform"
                :class="{ 'rotate-180': openBranch.events }"
                fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </button>
          <div v-if="openBranch.events" class="bg-white px-4 pb-3">
            <template v-if="eventCount">
              <div v-for="(items, category) in eventsByCategory" :key="category" class="mt-3">
                <h4 class="text-xs font-bold text-slate-500 mb-1.5">{{ category }}</h4>
                <div class="space-y-1">
                  <div
                    v-for="(ev, idx) in items"
                    :key="idx"
                    class="flex items-center justify-between py-1.5 px-3 bg-slate-50 rounded text-sm"
                  >
                    <span class="text-slate-700 text-xs leading-snug flex-1 mr-3">{{ ev.display_name }}</span>
                    <div class="flex items-center gap-2 whitespace-nowrap">
                      <span v-if="ev.event_price" class="text-red-500 font-bold text-xs">
                        {{ formatPrice(ev.event_price) }}
                      </span>
                      <span v-if="ev.discount_rate" class="text-emerald-500 text-xs">
                        {{ ev.discount_rate }}%↓
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </template>
            <p v-else class="py-2 text-sm text-slate-400">이벤트 없음</p>
          </div>
        </section>

        <!-- 블로그 (접이식) -->
        <section class="border border-slate-200 rounded-lg overflow-hidden">
          <button
            @click="toggleBranch('blogs')"
            class="w-full flex items-center justify-between px-4 py-3 bg-white hover:bg-slate-50 transition text-left"
          >
            <span class="font-semibold text-sm text-slate-700">블로그</span>
            <div class="flex items-center gap-2">
              <span class="text-[10px] bg-emerald-50 text-emerald-600 font-medium px-1.5 py-0.5 rounded-full">
                브블 {{ branchData.blog_summary?.brand_count ?? 0 }}
              </span>
              <span class="text-[10px] bg-violet-50 text-violet-600 font-medium px-1.5 py-0.5 rounded-full">
                최블 {{ branchData.blog_summary?.optimal_count ?? 0 }}
              </span>
              <svg class="w-4 h-4 text-slate-400 transition-transform"
                :class="{ 'rotate-180': openBranch.blogs }"
                fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </button>
          <div v-if="openBranch.blogs" class="bg-white px-4 pb-3">
            <template v-if="branchData.recent_blogs?.length">
              <div class="grid grid-cols-2 gap-4">
                <!-- 좌: 브랜드블로그 -->
                <div>
                  <p class="text-[11px] font-semibold text-emerald-600 mb-2 pb-1 border-b border-emerald-100">
                    브랜드블로그 ({{ branchData.blog_summary?.brand_count ?? 0 }})
                  </p>
                  <div class="space-y-1.5">
                    <div v-for="b in brandBlogs" :key="b.id">
                      <p class="text-xs text-slate-700 leading-snug truncate">{{ b.title }}</p>
                      <div class="flex items-center gap-1.5 mt-0.5 text-[10px] text-slate-400">
                        <span v-if="b.keyword" class="text-blue-500">{{ b.keyword }}</span>
                        <span>{{ b.published_at?.slice(5, 10) }}</span>
                        <span v-if="canSeeAuthor && b.author" class="text-slate-500">{{ b.author }}</span>
                        <a v-if="b.published_url" :href="b.published_url" target="_blank"
                          class="text-blue-400 hover:text-blue-600" @click.stop>링크</a>
                      </div>
                    </div>
                    <p v-if="!brandBlogs.length" class="text-[11px] text-slate-300 py-2">없음</p>
                  </div>
                </div>
                <!-- 우: 최적블로그 -->
                <div>
                  <p class="text-[11px] font-semibold text-violet-600 mb-2 pb-1 border-b border-violet-100">
                    최적블로그 ({{ branchData.blog_summary?.optimal_count ?? 0 }})
                  </p>
                  <div class="space-y-1.5">
                    <div v-for="b in optimalBlogs" :key="b.id">
                      <p class="text-xs text-slate-700 leading-snug truncate">{{ b.title }}</p>
                      <div class="flex items-center gap-1.5 mt-0.5 text-[10px] text-slate-400">
                        <span v-if="b.keyword" class="text-blue-500">{{ b.keyword }}</span>
                        <span>{{ b.published_at?.slice(5, 10) }}</span>
                        <span v-if="canSeeAuthor && b.author" class="text-slate-500">{{ b.author }}</span>
                        <a v-if="b.published_url" :href="b.published_url" target="_blank"
                          class="text-blue-400 hover:text-blue-600" @click.stop>링크</a>
                      </div>
                    </div>
                    <p v-if="!optimalBlogs.length" class="text-[11px] text-slate-300 py-2">없음</p>
                  </div>
                </div>
              </div>
            </template>
            <p v-else class="py-2 text-sm text-slate-400">블로그 없음</p>
          </div>
        </section>

        <!-- 노출 현황 (접이식) -->
        <section class="border border-slate-200 rounded-lg overflow-hidden">
          <button
            @click="toggleBranch('place')"
            class="w-full flex items-center justify-between px-4 py-3 bg-white hover:bg-slate-50 transition text-left"
          >
            <span class="font-semibold text-sm text-slate-700">노출 현황</span>
            <svg class="w-4 h-4 text-slate-400 transition-transform"
              :class="{ 'rotate-180': openBranch.place }"
              fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          <div v-if="openBranch.place" class="bg-white px-4 pb-3 space-y-4 pt-1">

            <!-- 플레이스 -->
            <div>
              <p class="text-xs font-semibold text-sky-700 mb-2">플레이스 순위</p>
              <template v-if="branchData.place_keywords?.length">
                <div class="space-y-1">
                  <div
                    v-for="kw in branchData.place_keywords"
                    :key="'p_'+kw.keyword"
                    class="flex items-center justify-between px-3 py-2 bg-slate-50 rounded"
                  >
                    <span class="text-xs text-slate-700">{{ kw.keyword }}</span>
                    <div class="flex items-center gap-1.5">
                      <span v-if="kw.rank && kw.rank > 0" class="text-sm font-bold"
                        :class="kw.rank <= 3 ? 'text-sky-600' : kw.rank <= 5 ? 'text-sky-400' : kw.rank <= 10 ? 'text-amber-500' : 'text-slate-400'">
                        {{ kw.rank }}위
                      </span>
                      <span v-else class="text-xs text-slate-300">순위 없음</span>
                      <span v-if="kw.last_top5_date" class="text-[10px] text-slate-400">
                        (최근 5위 이내: {{ kw.last_top5_date.slice(5) }})
                      </span>
                    </div>
                  </div>
                </div>
              </template>
              <div v-else class="py-3 px-3 bg-slate-50 rounded text-center">
                <p class="text-xs text-slate-400">플레이스 마케팅을 진행하지 않는 지점입니다</p>
              </div>
            </div>

            <!-- 웹페이지 -->
            <div>
              <p class="text-xs font-semibold text-indigo-700 mb-2">웹페이지 노출 여부</p>
              <template v-if="branchData.webpage_keywords?.length">
                <div class="space-y-1">
                  <div
                    v-for="kw in branchData.webpage_keywords"
                    :key="'w_'+kw.keyword"
                    class="flex items-center justify-between px-3 py-2 bg-slate-50 rounded"
                  >
                    <span class="text-xs text-slate-700">{{ kw.keyword }}</span>
                    <span v-if="kw.is_exposed"
                      class="text-[10px] px-2 py-0.5 rounded-full font-bold bg-indigo-100 text-indigo-600">O 노출</span>
                    <span v-else
                      class="text-[10px] px-2 py-0.5 rounded-full font-bold bg-red-50 text-red-400">X 미노출</span>
                  </div>
                </div>
              </template>
              <div v-else class="py-3 px-3 bg-slate-50 rounded text-center">
                <p class="text-xs text-slate-400">웹페이지 마케팅을 진행하지 않는 지점입니다</p>
              </div>
            </div>

          </div>
        </section>

      </template>
      </template>
    </div>

    <!-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Tab 2: 시술별 -->
    <div v-else-if="activeTab === 'treatment'">

      <!-- 카테고리 카드 그리드 (4열) -->
      <div class="grid grid-cols-4 gap-3 mb-5">
        <button
          v-for="cat in CATEGORIES"
          :key="cat.id"
          @click="selectCategory(cat.id)"
          :class="[
            'p-3 border rounded-lg text-center transition text-sm font-medium',
            selectedCategoryId === cat.id
              ? 'border-blue-500 bg-blue-50 text-blue-700'
              : 'border-slate-200 bg-white text-slate-600 hover:border-blue-300 hover:bg-slate-50'
          ]"
        >
          {{ cat.name }}
        </button>
      </div>

      <!-- 선택된 카테고리 상세 -->
      <div v-if="selectedCategoryId">
        <div v-if="categoryLoading" class="flex justify-center py-8">
          <LoadingSpinner message="카테고리 정보 로딩 중..." />
        </div>

        <template v-else-if="categoryData">
          <h3 class="text-sm font-bold text-slate-700 mb-3">
            {{ CATEGORIES.find(c => c.id === selectedCategoryId)?.name }}
            <span class="text-slate-400 font-normal ml-1">탐색 결과</span>
          </h3>

          <!-- 관련 장비 칩 -->
          <div v-if="categoryData.devices?.length" class="mb-4">
            <p class="text-xs font-semibold text-slate-500 mb-2">관련 장비</p>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="d in categoryData.devices"
                :key="d.device_info_id"
                @click="goToDeviceFromCategory(d.device_info_id)"
                class="px-3 py-1.5 bg-blue-50 text-blue-700 text-xs rounded-full border border-blue-200
                       hover:bg-blue-100 transition font-medium"
              >
                {{ d.name }}
              </button>
            </div>
          </div>

          <!-- 지점별 이벤트 -->
          <div v-if="categoryData.events_by_branch?.length" class="space-y-3">
            <p class="text-xs font-semibold text-slate-500">지점별 이벤트</p>
            <div
              v-for="group in categoryData.events_by_branch"
              :key="group.branch_name"
              class="bg-white border border-slate-200 rounded-lg"
            >
              <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100">
                <span class="text-sm font-semibold text-slate-700">{{ group.branch_name }}</span>
                <span class="text-xs text-slate-400">{{ group.items?.length ?? 0 }}건</span>
              </div>
              <div class="px-4 py-2 space-y-1">
                <div
                  v-for="(ev, idx) in (group.items || []).slice(0, 5)"
                  :key="idx"
                  class="flex items-center justify-between py-1 text-xs"
                >
                  <span class="text-slate-700 flex-1 mr-3 leading-snug">{{ ev.display_name }}</span>
                  <div class="flex items-center gap-2 whitespace-nowrap">
                    <span v-if="ev.event_price" class="text-red-500 font-bold">
                      {{ formatPrice(ev.event_price) }}
                    </span>
                    <span v-if="ev.discount_rate" class="text-emerald-500">
                      {{ ev.discount_rate }}%↓
                    </span>
                  </div>
                </div>
                <p v-if="(group.items?.length ?? 0) > 5" class="text-xs text-slate-400 pt-0.5">
                  외 {{ group.items.length - 5 }}건
                </p>
              </div>
            </div>
          </div>

          <!-- 논문 수 표시 -->
          <p v-if="categoryData.papers_count" class="mt-4 text-sm text-slate-500">
            관련 논문
            <span class="font-bold text-purple-600 mx-1">{{ categoryData.papers_count }}</span>건 —
            <button
              @click="activeTab = 'papers'"
              class="text-blue-600 underline text-xs ml-1"
            >논문 탭에서 보기</button>
          </p>

          <EmptyState
            v-if="!categoryData.devices?.length && !categoryData.events_by_branch?.length"
            message="해당 카테고리에 연결된 정보가 없습니다"
          />
        </template>
      </div>

      <EmptyState
        v-else
        message="카테고리를 선택하면 관련 장비 · 이벤트를 탐색합니다"
      />
    </div>

    <!-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Tab 3: 장비별 -->
    <div v-else-if="activeTab === 'device'">

      <!-- 검색 -->
      <div class="mb-4">
        <input
          v-model="deviceSearch"
          type="text"
          placeholder="장비명 또는 카테고리 검색..."
          class="w-full px-3 py-2.5 border border-slate-300 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-1 focus:ring-blue-500 transition"
        />
      </div>

      <!-- 로딩 -->
      <div v-if="deviceListLoading" class="flex justify-center py-8">
        <LoadingSpinner message="장비 목록 로딩 중..." />
      </div>

      <EmptyState
        v-else-if="!filteredDevices.length"
        :message="deviceSearch ? `'${deviceSearch}' 검색 결과가 없습니다` : '장비 목록이 없습니다'"
      />

      <!-- 장비 목록 (인라인 확장) -->
      <div v-else class="space-y-2">
        <div v-for="d in filteredDevices" :key="d.id">
          <div
            @click="toggleDevice(d.id)"
            :class="[
              'flex items-center justify-between p-3 bg-white border rounded-lg cursor-pointer transition',
              expandedDeviceId === d.id
                ? 'border-blue-400 bg-blue-50'
                : 'border-slate-200 hover:border-blue-300'
            ]"
          >
            <div>
              <span class="text-sm font-medium text-slate-700">{{ d.name }}</span>
              <span v-if="d.category" class="ml-2 text-xs text-slate-400">{{ d.category }}</span>
            </div>
            <svg
              class="w-4 h-4 text-slate-400 transition-transform flex-shrink-0"
              :class="{ 'rotate-180': expandedDeviceId === d.id }"
              fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </div>

          <!-- 인라인 상세 확장 -->
          <div
            v-if="expandedDeviceId === d.id"
            class="mx-0 px-4 py-4 bg-slate-50 border-x border-b border-slate-200 rounded-b-lg"
          >
            <ExplorerDeviceInline :device-id="d.id" />
          </div>
        </div>
      </div>
    </div>

    <!-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Tab 4: 논문 -->
    <div v-else-if="activeTab === 'papers'">

      <!-- 검색 + 필터 -->
      <div class="flex gap-3 mb-4">
        <input
          v-model="paperSearch"
          type="text"
          placeholder="논문 제목, 키워드, 저자 검색..."
          class="flex-1 px-3 py-2.5 border border-slate-300 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-1 focus:ring-blue-500 transition"
        />
        <FilterSelect
          v-model="paperDeviceFilter"
          :options="deviceFilterOptions"
          all-label="전체 장비"
        />
      </div>

      <!-- 로딩 -->
      <div v-if="paperLoading" class="flex justify-center py-8">
        <LoadingSpinner message="논문 로딩 중..." />
      </div>

      <EmptyState
        v-else-if="!papers.length"
        :message="paperSearch || paperDeviceFilter ? '검색 결과가 없습니다' : '논문 데이터가 없습니다'"
      />

      <!-- 논문 목록 (인라인 확장) -->
      <div v-else class="space-y-2">
        <p class="text-xs text-slate-400 mb-3">총 {{ papers.length }}건</p>

        <div v-for="p in papers" :key="p.id">
          <!-- 논문 카드 -->
          <div
            @click="togglePaper(p.id)"
            :class="[
              'p-3 bg-white border rounded-lg cursor-pointer transition',
              expandedPaperId === p.id
                ? 'border-purple-400 bg-purple-50 rounded-b-none'
                : 'border-slate-200 hover:border-purple-300'
            ]"
          >
            <p class="text-sm font-medium text-slate-800 leading-snug">
              {{ p.title_ko || p.title }}
            </p>
            <div class="flex flex-wrap gap-2 text-xs text-slate-400 mt-1.5">
              <span v-if="p.device_name" class="text-blue-500">{{ p.device_name }}</span>
              <span v-if="p.pub_year">{{ p.pub_year }}년</span>
              <span v-if="p.journal">{{ p.journal }}</span>
              <span v-if="p.study_type" class="px-1.5 py-0.5 bg-slate-100 rounded">{{ p.study_type }}</span>
              <span v-if="p.evidence_level"
                :class="[
                  'px-1.5 py-0.5 rounded font-medium',
                  p.evidence_level >= 4 ? 'bg-green-100 text-green-700' :
                  p.evidence_level >= 2 ? 'bg-yellow-100 text-yellow-700' :
                  'bg-slate-100 text-slate-500'
                ]"
              >
                EL{{ p.evidence_level }}
              </span>
            </div>
          </div>

          <!-- 인라인 확장 -->
          <div
            v-if="expandedPaperId === p.id"
            class="px-4 py-4 bg-slate-50 border-x border-b border-slate-200 rounded-b-lg space-y-3"
          >
            <!-- 한줄 요약 -->
            <div v-if="p.one_line_summary">
              <h5 class="text-xs font-bold text-slate-500 mb-1">한줄 요약</h5>
              <p class="text-sm text-slate-700">{{ p.one_line_summary }}</p>
            </div>

            <!-- 주요 결과 -->
            <div v-if="p.key_findings">
              <h5 class="text-xs font-bold text-slate-500 mb-1">주요 결과</h5>
              <p class="text-sm text-slate-700 leading-relaxed">{{ p.key_findings }}</p>
            </div>

            <!-- 결론 -->
            <div v-if="p.conclusion">
              <h5 class="text-xs font-bold text-slate-500 mb-1">결론</h5>
              <p class="text-sm text-slate-700 leading-relaxed">{{ p.conclusion }}</p>
            </div>

            <!-- 인용 통계 -->
            <div v-if="p.quotable_stats">
              <h5 class="text-xs font-bold text-slate-500 mb-1">인용 가능 통계</h5>
              <p class="text-sm text-slate-700">{{ p.quotable_stats }}</p>
            </div>

            <!-- 원본 파일 -->
            <div v-if="p.source_url || p.source_file">
              <h5 class="text-xs font-bold text-slate-500 mb-1">원본</h5>
              <p v-if="p.source_url" class="text-xs text-blue-600 break-all">{{ p.source_url }}</p>
              <p v-if="p.source_file" class="text-xs text-slate-500">{{ p.source_file }}</p>
            </div>

            <!-- 저자 / 샘플 사이즈 -->
            <div class="flex gap-4 text-xs text-slate-400">
              <span v-if="p.authors">저자: {{ p.authors }}</span>
              <span v-if="p.sample_size">샘플: {{ p.sample_size }}명</span>
            </div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>
