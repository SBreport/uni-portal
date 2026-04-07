<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useBranchStore } from '@/stores/branches'
import * as explorerApi from '@/api/explorer'
import TabBar from '@/components/common/TabBar.vue'
import FilterSelect from '@/components/common/FilterSelect.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ExplorerDeviceDetail from '@/components/explorer/ExplorerDeviceDetail.vue'
import ExplorerBranchDetail from '@/components/explorer/ExplorerBranchDetail.vue'

// ── 스토어 ──────────────────────────────────────────────────────────────
const branchStore = useBranchStore()

onMounted(async () => {
  await branchStore.loadBranches()
  loadDeviceList()
})

// ── 탭 ───────────────────────────────────────────────────────────────────
const TABS = [
  { key: 'branch',   label: '지점별' },
  { key: 'category', label: '카테고리별' },
  { key: 'device',   label: '장비별' },
  { key: 'search',   label: '검색결과' },
]
const activeTab = ref('branch')

// ── 공통 검색창 ───────────────────────────────────────────────────────────
const searchQuery = ref('')
let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null

function onSearchInput(e: Event) {
  searchQuery.value = (e.target as HTMLInputElement).value
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  if (searchQuery.value.trim().length >= 2) {
    searchDebounceTimer = setTimeout(() => {
      activeTab.value = 'search'
      runSearch()
    }, 400)
  }
}

function clearSearch() {
  searchQuery.value = ''
  searchResults.value = null
}

// ── Tab 1: 지점별 ─────────────────────────────────────────────────────────
const branchOptions = computed(() =>
  branchStore.branches.map(b => ({ value: String(b.id), label: b.name }))
)
const selectedBranchId = ref('')

watch(selectedBranchId, () => {
  selectedDeviceIdDirect.value = null
})

function onBranchDeviceClick(deviceId: number) {
  selectedDeviceIdDirect.value = deviceId
  activeTab.value = 'device'
}

// ── Tab 2: 카테고리별 ──────────────────────────────────────────────────────
const CATEGORIES = [
  { id: 1,  label: '리프팅' },
  { id: 2,  label: '보톡스' },
  { id: 3,  label: '필러' },
  { id: 4,  label: '레이저' },
  { id: 5,  label: '피부관리' },
  { id: 6,  label: '실리프팅' },
  { id: 7,  label: '지방분해' },
  { id: 8,  label: '체형관리' },
  { id: 9,  label: '탈모' },
  { id: 10, label: '여드름' },
  { id: 11, label: '흉터/모공' },
  { id: 12, label: '미백/톤업' },
  { id: 13, label: '눈/코' },
  { id: 14, label: '안티에이징' },
  { id: 15, label: '제모' },
  { id: 16, label: '기타' },
]
const selectedCategoryId = ref<number | null>(null)
const categoryLoading = ref(false)
const categoryData = ref<any>(null)

async function onCategoryClick(catId: number) {
  selectedCategoryId.value = catId
  categoryLoading.value = true
  categoryData.value = null
  try {
    categoryData.value = await explorerApi.getByCategory(catId)
  } catch (e) {
    console.error('[Explorer] 카테고리별 로드 실패:', e)
  } finally {
    categoryLoading.value = false
  }
}

const selectedCategoryLabel = computed(
  () => CATEGORIES.find(c => c.id === selectedCategoryId.value)?.label ?? ''
)

function categoryColorClass(idx: number): string {
  const colors = [
    'bg-blue-50 text-blue-600 border-blue-200 hover:bg-blue-100',
    'bg-purple-50 text-purple-600 border-purple-200 hover:bg-purple-100',
    'bg-amber-50 text-amber-600 border-amber-200 hover:bg-amber-100',
    'bg-rose-50 text-rose-600 border-rose-200 hover:bg-rose-100',
    'bg-emerald-50 text-emerald-600 border-emerald-200 hover:bg-emerald-100',
    'bg-cyan-50 text-cyan-600 border-cyan-200 hover:bg-cyan-100',
    'bg-orange-50 text-orange-600 border-orange-200 hover:bg-orange-100',
    'bg-indigo-50 text-indigo-600 border-indigo-200 hover:bg-indigo-100',
  ]
  return colors[idx % colors.length]!
}

// ── Tab 3: 장비별 ─────────────────────────────────────────────────────────
const deviceSearchQuery = ref('')
const deviceListLoading = ref(false)
const deviceList = ref<Array<{ id: number; name: string; category?: string }>>([])
const selectedDeviceIdDirect = ref<number | null>(null)

const filteredDevices = computed(() => {
  const q = deviceSearchQuery.value.trim().toLowerCase()
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

function onDeviceSelect(deviceId: number) {
  selectedDeviceIdDirect.value = deviceId
}

// ── Tab 4: 검색결과 ───────────────────────────────────────────────────────
const searchLoading = ref(false)
const searchResults = ref<any>(null)

const hasAnySearchResult = computed(() => {
  if (!searchResults.value) return false
  const r = searchResults.value
  return (
    r.branches?.length ||
    r.devices?.length ||
    r.events?.length ||
    r.treatments?.length ||
    r.papers?.length ||
    r.blogs?.length
  )
})

async function runSearch() {
  const q = searchQuery.value.trim()
  if (!q) return
  searchLoading.value = true
  searchResults.value = null
  try {
    searchResults.value = await explorerApi.search(q)
  } catch (e) {
    console.error('[Explorer] 검색 실패:', e)
  } finally {
    searchLoading.value = false
  }
}

watch(activeTab, (tab) => {
  if (tab === 'search' && searchQuery.value.trim().length >= 2 && !searchResults.value) {
    runSearch()
  }
})

function onSearchResultDeviceClick(deviceId: number) {
  selectedDeviceIdDirect.value = deviceId
  activeTab.value = 'device'
}

function onSearchResultBranchClick(branchId: number) {
  selectedBranchId.value = String(branchId)
  activeTab.value = 'branch'
}
</script>

<template>
  <div class="p-5 max-w-5xl">

    <!-- 헤더 -->
    <div class="mb-5">
      <h2 class="text-xl font-bold text-slate-800">탐색기</h2>
      <p class="text-sm text-slate-400 mt-1">지점 · 카테고리 · 장비를 중심으로 연결된 정보를 탐색합니다</p>
    </div>

    <!-- 통합 검색창 -->
    <div class="relative mb-5">
      <div class="absolute inset-y-0 left-3 flex items-center pointer-events-none">
        <svg class="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24"
          stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round"
            d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
        </svg>
      </div>
      <input
        :value="searchQuery"
        @input="onSearchInput"
        type="text"
        placeholder="장비명, 지점명, 시술명, 키워드 통합 검색... (2자 이상)"
        class="w-full pl-9 pr-10 py-2.5 border border-slate-300 rounded-lg text-sm bg-white
               focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
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
    </div>

    <!-- 탭 -->
    <TabBar :tabs="TABS" v-model="activeTab" />

    <!-- ━━ Tab 1: 지점별 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ -->
    <div v-if="activeTab === 'branch'">
      <div class="flex items-center gap-3 mb-4">
        <FilterSelect
          v-model="selectedBranchId"
          :options="branchOptions"
          placeholder="지점 선택..."
        />
        <span v-if="branchStore.loading" class="text-xs text-slate-400">지점 목록 로딩 중...</span>
      </div>

      <EmptyState
        v-if="!selectedBranchId"
        message="지점을 선택하면 보유장비 · 이벤트 · 순위 정보를 탐색합니다"
        icon="🏥"
      />
      <ExplorerBranchDetail
        v-else
        :branch-id="Number(selectedBranchId)"
        @device-click="onBranchDeviceClick"
      />
    </div>

    <!-- ━━ Tab 2: 카테고리별 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ -->
    <div v-else-if="activeTab === 'category'">

      <!-- 카테고리 카드 그리드 -->
      <div class="grid grid-cols-4 gap-3 mb-5">
        <button
          v-for="(cat, idx) in CATEGORIES"
          :key="cat.id"
          @click="onCategoryClick(cat.id)"
          :class="[
            'px-3 py-3 text-sm font-medium rounded-lg border transition text-center',
            categoryColorClass(idx),
            selectedCategoryId === cat.id ? 'ring-2 ring-offset-1 ring-blue-400' : '',
          ]"
        >
          {{ cat.label }}
        </button>
      </div>

      <!-- 결과 영역 -->
      <div v-if="selectedCategoryId">
        <div class="flex items-center gap-2 mb-3">
          <h3 class="text-sm font-bold text-slate-700">{{ selectedCategoryLabel }}</h3>
          <span class="text-xs text-slate-400">탐색 결과</span>
        </div>

        <div v-if="categoryLoading" class="flex justify-center py-8">
          <LoadingSpinner message="카테고리 정보 로딩 중..." />
        </div>

        <template v-else-if="categoryData">
          <!-- 관련 장비 -->
          <div v-if="categoryData.devices?.length" class="mb-5">
            <h4 class="text-xs font-semibold text-slate-500 mb-2 uppercase tracking-wide">관련 장비</h4>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="d in categoryData.devices"
                :key="d.device_info_id"
                @click="onDeviceSelect(d.device_info_id); activeTab = 'device'"
                class="px-3 py-1.5 bg-blue-50 text-blue-700 text-xs rounded-full border border-blue-200
                       hover:bg-blue-100 transition font-medium"
              >
                {{ d.name }}
              </button>
            </div>
          </div>

          <!-- 지점별 이벤트 -->
          <div v-if="categoryData.events_by_branch?.length">
            <h4 class="text-xs font-semibold text-slate-500 mb-2 uppercase tracking-wide">지점별 이벤트</h4>
            <div class="space-y-2">
              <div
                v-for="group in categoryData.events_by_branch"
                :key="group.branch_name"
                class="bg-white border border-slate-200 rounded-lg px-4 py-3"
              >
                <div class="flex items-center justify-between mb-1.5">
                  <span class="text-sm font-semibold text-slate-700">{{ group.branch_name }}</span>
                  <span class="text-xs text-slate-400">{{ group.items?.length ?? 0 }}건</span>
                </div>
                <div class="space-y-0.5">
                  <p v-for="(ev, idx) in (group.items || []).slice(0, 3)" :key="idx"
                    class="text-xs text-slate-600 truncate">
                    · {{ ev.display_name }}
                    <span v-if="ev.event_price" class="text-red-500 font-medium ml-1">{{ (ev.event_price / 10000).toFixed(0) }}만</span>
                  </p>
                  <p v-if="(group.items?.length ?? 0) > 3" class="text-xs text-slate-400">
                    외 {{ group.items.length - 3 }}건
                  </p>
                </div>
              </div>
            </div>
          </div>

          <!-- 논문 수 -->
          <p v-if="categoryData.papers_count !== undefined" class="mt-4 text-sm text-slate-500">
            관련 논문
            <span class="font-bold text-purple-600">{{ categoryData.papers_count }}</span>건
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
        icon="📂"
      />
    </div>

    <!-- ━━ Tab 3: 장비별 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ -->
    <div v-else-if="activeTab === 'device'">
      <div class="mb-4">
        <input
          v-model="deviceSearchQuery"
          type="text"
          placeholder="장비명 또는 카테고리 검색..."
          class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-1 focus:ring-blue-500 transition"
        />
      </div>

      <div class="flex gap-5">
        <!-- 장비 목록 패널 -->
        <div class="w-52 flex-shrink-0">
          <div v-if="deviceListLoading" class="flex justify-center py-6">
            <LoadingSpinner size="sm" />
          </div>
          <div v-else-if="filteredDevices.length"
            class="space-y-0.5 max-h-[60vh] overflow-y-auto pr-1">
            <button
              v-for="d in filteredDevices"
              :key="d.id"
              @click="onDeviceSelect(d.id)"
              :class="[
                'w-full text-left px-3 py-2 rounded-lg text-sm transition',
                selectedDeviceIdDirect === d.id
                  ? 'bg-blue-600 text-white'
                  : 'hover:bg-slate-50 text-slate-700'
              ]"
            >
              <p class="font-medium truncate">{{ d.name }}</p>
              <p v-if="d.category"
                class="text-[11px] truncate mt-0.5"
                :class="selectedDeviceIdDirect === d.id ? 'text-blue-200' : 'text-slate-400'">
                {{ d.category }}
              </p>
            </button>
          </div>
          <div v-else class="text-center py-6 text-sm text-slate-400">
            {{ deviceSearchQuery ? '검색 결과 없음' : '장비 목록 없음' }}
          </div>
        </div>

        <!-- 장비 상세 패널 -->
        <div class="flex-1 min-w-0">
          <ExplorerDeviceDetail
            v-if="selectedDeviceIdDirect"
            :device-id="selectedDeviceIdDirect"
          />
          <EmptyState
            v-else
            message="장비를 선택하면 상세 정보를 탐색합니다"
            icon="🔬"
          />
        </div>
      </div>
    </div>

    <!-- ━━ Tab 4: 검색결과 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ -->
    <div v-else-if="activeTab === 'search'">

      <EmptyState
        v-if="!searchQuery.trim()"
        message="상단 검색창에 키워드를 입력하세요 (2자 이상)"
        icon="🔍"
      />

      <div v-else-if="searchLoading" class="flex justify-center py-10">
        <LoadingSpinner message="검색 중..." />
      </div>

      <EmptyState
        v-else-if="searchResults && !hasAnySearchResult"
        :message="`'${searchQuery}' 검색 결과가 없습니다`"
        icon="🔍"
      />

      <template v-else-if="searchResults">
        <p class="text-xs text-slate-400 mb-5">
          "<span class="font-medium text-slate-600">{{ searchQuery }}</span>" 검색 결과
        </p>

        <!-- 지점 -->
        <div v-if="searchResults.branches?.length" class="mb-5">
          <h4 class="text-xs font-semibold text-slate-500 mb-2 uppercase tracking-wide">
            지점
            <span class="text-slate-400 normal-case font-normal ml-1">{{ searchResults.branches.length }}건</span>
          </h4>
          <div class="space-y-1">
            <button
              v-for="b in searchResults.branches"
              :key="b.id"
              @click="onSearchResultBranchClick(b.id)"
              class="w-full text-left px-4 py-2.5 bg-white border border-slate-200 rounded-lg
                     hover:bg-slate-50 hover:border-blue-300 transition text-sm text-slate-700"
            >
              {{ b.name }}
              <span v-if="b.region_name" class="text-xs text-slate-400 ml-2">{{ b.region_name }}</span>
            </button>
          </div>
        </div>

        <!-- 장비 -->
        <div v-if="searchResults.devices?.length" class="mb-5">
          <h4 class="text-xs font-semibold text-slate-500 mb-2 uppercase tracking-wide">
            장비
            <span class="text-slate-400 normal-case font-normal ml-1">{{ searchResults.devices.length }}건</span>
          </h4>
          <div class="space-y-1">
            <button
              v-for="d in searchResults.devices"
              :key="d.id"
              @click="onSearchResultDeviceClick(d.id)"
              class="w-full text-left px-4 py-2.5 bg-white border border-slate-200 rounded-lg
                     hover:bg-slate-50 hover:border-blue-300 transition"
            >
              <span class="text-sm text-slate-700 font-medium">{{ d.name }}</span>
              <span v-if="d.category"
                class="ml-2 text-xs px-1.5 py-0.5 bg-blue-50 text-blue-500 rounded">
                {{ d.category }}
              </span>
            </button>
          </div>
        </div>

        <!-- 이벤트 -->
        <div v-if="searchResults.events?.length" class="mb-5">
          <h4 class="text-xs font-semibold text-slate-500 mb-2 uppercase tracking-wide">
            이벤트
            <span class="text-slate-400 normal-case font-normal ml-1">{{ searchResults.events.length }}건</span>
          </h4>
          <div class="space-y-1">
            <div
              v-for="ev in searchResults.events"
              :key="ev.id"
              class="px-4 py-2.5 bg-white border border-slate-200 rounded-lg"
            >
              <p class="text-sm text-slate-700 font-medium">{{ ev.title }}</p>
              <span v-if="ev.branch_name" class="text-xs text-slate-400">{{ ev.branch_name }}</span>
            </div>
          </div>
        </div>

        <!-- 시술 -->
        <div v-if="searchResults.treatments?.length" class="mb-5">
          <h4 class="text-xs font-semibold text-slate-500 mb-2 uppercase tracking-wide">
            시술
            <span class="text-slate-400 normal-case font-normal ml-1">{{ searchResults.treatments.length }}건</span>
          </h4>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="t in searchResults.treatments"
              :key="t.id"
              class="px-3 py-1.5 bg-rose-50 text-rose-600 text-xs rounded-full font-medium border border-rose-100"
            >
              {{ t.name }}
            </span>
          </div>
        </div>

        <!-- 논문 -->
        <div v-if="searchResults.papers?.length" class="mb-5">
          <h4 class="text-xs font-semibold text-slate-500 mb-2 uppercase tracking-wide">
            논문
            <span class="text-slate-400 normal-case font-normal ml-1">{{ searchResults.papers.length }}건</span>
          </h4>
          <div class="space-y-1">
            <div
              v-for="p in searchResults.papers"
              :key="p.id"
              class="px-4 py-2.5 bg-white border border-slate-200 rounded-lg"
            >
              <p class="text-sm text-slate-700 leading-snug">{{ p.title_ko || p.title }}</p>
              <span v-if="p.year" class="text-xs text-slate-400">{{ p.year }}년</span>
            </div>
          </div>
        </div>

        <!-- 블로그 -->
        <div v-if="searchResults.blogs?.length" class="mb-5">
          <h4 class="text-xs font-semibold text-slate-500 mb-2 uppercase tracking-wide">
            블로그
            <span class="text-slate-400 normal-case font-normal ml-1">{{ searchResults.blogs.length }}건</span>
          </h4>
          <div class="space-y-1">
            <div
              v-for="b in searchResults.blogs"
              :key="b.id"
              class="px-4 py-2.5 bg-white border border-slate-200 rounded-lg"
            >
              <p class="text-sm text-slate-700 leading-snug">{{ b.title }}</p>
              <div class="flex items-center gap-2 mt-0.5">
                <span v-if="b.keyword" class="text-xs text-blue-500">{{ b.keyword }}</span>
                <span v-if="b.published_at" class="text-xs text-slate-400">
                  {{ b.published_at.slice(0, 10) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

  </div>
</template>
