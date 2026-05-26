<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import api from '@/api/client'
import PeriodSelector from '@/components/common/PeriodSelector.vue'

// ── Types ──────────────────────────────────────────────────────────
interface EquipRow {
  id: number
  name: string
  quantity: number
}

interface EquipGroup {
  device_info_id: number | null
  device_info_name: string | null
  total_qty: number
  rows: EquipRow[]
  can_merge: boolean
}

interface EventItem {
  id: number
  display_name: string
  raw_event_name: string
  event_price: number | null
}

interface CategoryData {
  id: number
  name: string
  color: string
  equipment_count: number
  equipment_groups: EquipGroup[]
  event_count: number
  event_avg_price: number | null
  top_devices: string[]
  events: EventItem[]
}

interface DashboardData {
  branch: { id: number; name: string }
  period: { id: number; label: string; year: number; start_month: number; end_month: number } | null
  summary: { equipment_total: number; events_total: number; complaints_active: number }
  categories: CategoryData[]
}

// ── Props ──────────────────────────────────────────────────────────
const props = defineProps<{
  branchId: number
  branchName: string
  onBack?: () => void
}>()

const emit = defineEmits<{
  back: []
}>()

// ── State ──────────────────────────────────────────────────────────
const periodId = ref<number | null>(null)
const dashboard = ref<DashboardData | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

// 사이드 패널
const activeCat = ref<CategoryData | null>(null)
const panelSearch = ref('')
const panelSort = ref<'price_asc' | 'price_desc' | 'name'>('price_asc')

// ── Fetch ──────────────────────────────────────────────────────────
async function fetchDashboard() {
  if (!periodId.value) return
  loading.value = true
  error.value = null
  try {
    const { data } = await api.get(`/branch-info/${props.branchId}/dashboard`, {
      params: { period_id: periodId.value },
    })
    dashboard.value = data
    // 열린 패널이 있으면 최신 데이터로 갱신
    if (activeCat.value) {
      const fresh = data.categories.find((c: CategoryData) => c.id === activeCat.value!.id)
      activeCat.value = fresh ?? null
    }
  } catch (e: any) {
    error.value = e?.response?.data?.detail ?? '데이터를 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

watch(periodId, (v) => {
  if (v) fetchDashboard()
})

// ── Side panel ─────────────────────────────────────────────────────
function openPanel(cat: CategoryData) {
  activeCat.value = cat
  panelSearch.value = ''
  panelSort.value = 'price_asc'
}

function closePanel() {
  activeCat.value = null
}

const filteredEvents = computed(() => {
  if (!activeCat.value) return []
  let list = activeCat.value.events
  if (panelSearch.value.trim()) {
    const q = panelSearch.value.toLowerCase()
    list = list.filter((e) => e.display_name.toLowerCase().includes(q))
  }
  if (panelSort.value === 'price_asc') {
    list = [...list].sort((a, b) => (a.event_price ?? 0) - (b.event_price ?? 0))
  } else if (panelSort.value === 'price_desc') {
    list = [...list].sort((a, b) => (b.event_price ?? 0) - (a.event_price ?? 0))
  } else {
    list = [...list].sort((a, b) => a.display_name.localeCompare(b.display_name))
  }
  return list
})

// ── Formatters ─────────────────────────────────────────────────────
function fmtAvgPrice(p: number | null): string {
  if (!p) return '-'
  return `~${Math.round(p / 10000)}만원`
}

function fmtPrice(p: number | null): string {
  if (!p) return '-'
  return Math.round(p / 10000) + '만원'
}

function fmtSummaryPrice(p: number | null): string {
  if (!p) return '-'
  const wan = Math.round(p / 10000)
  return `~${wan.toLocaleString()}만원`
}

// 카테고리별 bg 클래스 (dot용, hex → tailwind 쓰기 어려워 인라인 style 사용)
function dotStyle(color: string) {
  return { backgroundColor: color }
}
</script>

<template>
  <div class="h-full flex flex-col overflow-hidden">

    <!-- ── 헤더 ───────────────────────────────────────────────────── -->
    <div class="shrink-0 flex items-center gap-3 px-5 py-3 border-b border-slate-200 bg-white">
      <button
        @click="emit('back')"
        class="text-sm text-blue-600 hover:underline shrink-0"
      >&larr; 전체 지점</button>
      <h3 class="text-base font-bold text-slate-800">{{ branchName }}</h3>
      <div class="ml-auto">
        <PeriodSelector v-model:periodId="periodId" />
      </div>
    </div>

    <!-- ── Summary bar ───────────────────────────────────────────── -->
    <div
      v-if="dashboard && !loading"
      class="shrink-0 flex items-center gap-5 px-5 py-2 bg-slate-50 border-b border-slate-200 text-sm"
    >
      <div class="flex items-baseline gap-1">
        <span class="text-slate-500">보유장비</span>
        <span class="font-bold text-blue-600">{{ dashboard.summary.equipment_total }}대</span>
      </div>
      <span class="text-slate-300">·</span>
      <div class="flex items-baseline gap-1">
        <span class="text-slate-500">이벤트</span>
        <span class="font-bold text-purple-600">{{ dashboard.summary.events_total }}건</span>
      </div>
      <span class="text-slate-300">·</span>
      <div class="flex items-baseline gap-1">
        <span class="text-slate-500">진행 민원</span>
        <span class="font-bold" :class="dashboard.summary.complaints_active ? 'text-orange-600' : 'text-slate-400'">
          {{ dashboard.summary.complaints_active }}
        </span>
      </div>
      <span v-if="dashboard.period" class="ml-auto text-xs text-slate-400">
        기간: {{ dashboard.period.label }}
      </span>
    </div>

    <!-- ── Body (카드 그리드 + 사이드 패널) ─────────────────────── -->
    <div class="flex-1 min-h-0 flex flex-row overflow-hidden">

      <!-- 카드 그리드 영역 -->
      <div class="flex-1 min-h-0 overflow-y-auto p-4">

        <!-- Loading -->
        <div v-if="loading" class="flex items-center justify-center h-40 text-sm text-slate-400">
          로딩 중...
        </div>

        <!-- Error -->
        <div v-else-if="error" class="flex items-center justify-center h-40">
          <p class="text-sm text-red-500">{{ error }}</p>
        </div>

        <!-- Period not selected yet -->
        <div v-else-if="!periodId" class="flex items-center justify-center h-40 text-sm text-slate-400">
          기간을 선택하면 카테고리별 현황이 표시됩니다.
        </div>

        <!-- 카드 그리드 -->
        <div
          v-else-if="dashboard"
          class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3"
        >
          <div
            v-for="cat in dashboard.categories"
            :key="cat.id"
            @click="openPanel(cat)"
            class="bg-white border rounded-lg p-3 cursor-pointer transition-all hover:shadow-md select-none"
            :class="activeCat?.id === cat.id
              ? 'border-blue-400 shadow-md ring-1 ring-blue-400'
              : 'border-slate-200 hover:border-slate-300'"
          >
            <!-- 카테고리명 + dot -->
            <div class="flex items-center gap-1.5 mb-2">
              <span
                class="w-2.5 h-2.5 rounded-full shrink-0"
                :style="dotStyle(cat.color)"
              ></span>
              <span class="text-sm font-semibold text-slate-800">{{ cat.name }}</span>
            </div>

            <!-- 장비 / 이벤트 수 -->
            <div class="flex items-center gap-2 text-xs text-slate-500 mb-1">
              <span>
                <span class="font-medium text-slate-700">{{ cat.equipment_count }}</span>대
              </span>
              <span class="text-slate-300">·</span>
              <span>
                <span class="font-medium text-slate-700">{{ cat.event_count }}</span>건
              </span>
            </div>

            <!-- 평균가 -->
            <div class="text-xs text-slate-500 mb-1.5">
              이벤트 평균
              <span class="font-medium text-slate-700">{{ fmtSummaryPrice(cat.event_avg_price) }}</span>
            </div>

            <!-- 대표 장비 -->
            <div v-if="cat.top_devices.length" class="text-xs text-slate-400 truncate">
              {{ cat.top_devices.join(' · ') }}
            </div>
            <div v-else class="text-xs text-slate-300 italic">장비 없음</div>
          </div>
        </div>

        <!-- Empty (기간 데이터 없음) -->
        <div v-else class="flex items-center justify-center h-40 text-sm text-slate-400">
          해당 기간 데이터가 없습니다.
        </div>
      </div>

      <!-- ── 사이드 패널 ──────────────────────────────────────────── -->
      <transition name="slide">
        <div
          v-if="activeCat"
          class="shrink-0 w-[420px] h-full flex flex-col border-l border-slate-200 bg-white overflow-hidden"
        >
          <!-- 패널 헤더 -->
          <div class="shrink-0 flex items-center gap-2 px-4 py-3 border-b border-slate-200">
            <span
              class="w-3 h-3 rounded-full shrink-0"
              :style="dotStyle(activeCat.color)"
            ></span>
            <span class="text-sm font-bold text-slate-800">{{ activeCat.name }}</span>
            <span class="text-xs text-slate-400 ml-1">
              {{ activeCat.equipment_count }}대 · {{ activeCat.event_count }}건
            </span>
            <button
              @click="closePanel"
              class="ml-auto text-slate-400 hover:text-slate-600 text-lg leading-none"
            >×</button>
          </div>

          <!-- 패널 본문 (스크롤) -->
          <div class="flex-1 min-h-0 overflow-y-auto">

            <!-- 보유장비 섹션 -->
            <div class="px-4 pt-3 pb-2">
              <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                보유장비 ({{ activeCat.equipment_count }}대)
              </p>

              <div v-if="activeCat.equipment_groups.length" class="space-y-1.5">
                <div
                  v-for="grp in activeCat.equipment_groups"
                  :key="grp.device_info_id ?? 'null'"
                  class="text-sm"
                >
                  <!-- 단일 or 그룹 -->
                  <div class="flex items-start gap-2 min-w-0">
                    <span class="text-slate-400 shrink-0 mt-0.5">•</span>
                    <div class="min-w-0 flex-1">
                      <div class="flex items-center gap-1.5 flex-wrap">
                        <span class="text-slate-700 font-medium">
                          {{ grp.device_info_name ?? '미연결' }}
                        </span>
                        <span v-if="grp.total_qty > 1" class="text-xs text-slate-400">
                          (총 {{ grp.total_qty }}대)
                        </span>
                        <span
                          v-if="grp.can_merge"
                          class="text-xs px-1.5 py-0.5 bg-amber-50 text-amber-600 border border-amber-200 rounded"
                        >
                          통합 가능
                        </span>
                        <span
                          v-if="!grp.device_info_id"
                          class="text-xs px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded"
                        >
                          미매핑
                        </span>
                      </div>
                      <!-- 서브 rows (이름이 다를 때) -->
                      <div
                        v-if="grp.rows.length > 1"
                        class="mt-0.5 space-y-0.5 pl-2"
                      >
                        <div
                          v-for="row in grp.rows"
                          :key="row.id"
                          class="text-xs text-slate-500"
                        >
                          {{ row.name }}<span v-if="row.quantity > 1"> ×{{ row.quantity }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <p v-else class="text-xs text-slate-400">보유장비 없음</p>
            </div>

            <div class="border-t border-slate-100 mx-4 my-1"></div>

            <!-- 이벤트 섹션 -->
            <div class="px-4 pt-2 pb-4">
              <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                이벤트 ({{ activeCat.event_count }}건)
              </p>

              <!-- 검색 + 정렬 -->
              <div class="flex items-center gap-2 mb-2">
                <div class="relative flex-1">
                  <input
                    v-model="panelSearch"
                    type="text"
                    placeholder="이벤트명 검색"
                    class="w-full border border-slate-200 rounded px-2.5 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400 pr-6"
                  />
                  <svg
                    v-if="!panelSearch"
                    class="absolute right-2 top-2 w-3 h-3 text-slate-300"
                    fill="none" stroke="currentColor" viewBox="0 0 24 24"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                  </svg>
                  <button
                    v-else
                    @click="panelSearch = ''"
                    class="absolute right-1.5 top-1.5 text-slate-400 hover:text-slate-600 text-xs"
                  >×</button>
                </div>
                <select
                  v-model="panelSort"
                  class="border border-slate-200 rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400 bg-white"
                >
                  <option value="price_asc">가격 낮은순</option>
                  <option value="price_desc">가격 높은순</option>
                  <option value="name">이름순</option>
                </select>
              </div>

              <!-- 이벤트 리스트 -->
              <div v-if="filteredEvents.length" class="space-y-1">
                <div
                  v-for="ev in filteredEvents"
                  :key="ev.id"
                  class="flex items-start gap-2 text-xs min-w-0 py-1 border-b border-slate-50 last:border-0"
                >
                  <span class="text-slate-600 flex-1 min-w-0 leading-relaxed">
                    {{ ev.display_name }}
                  </span>
                  <span class="shrink-0 font-medium text-blue-600 text-right whitespace-nowrap pl-2">
                    {{ fmtPrice(ev.event_price) }}
                  </span>
                </div>
              </div>
              <p v-else-if="panelSearch" class="text-xs text-slate-400 py-2">
                '{{ panelSearch }}' 검색 결과 없음
              </p>
              <p v-else class="text-xs text-slate-400 py-2">이벤트 없음</p>
            </div>
          </div>
        </div>
      </transition>

    </div>
  </div>
</template>

<style scoped>
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.2s ease, opacity 0.2s ease;
}
.slide-enter-from,
.slide-leave-to {
  transform: translateX(30px);
  opacity: 0;
}
</style>
