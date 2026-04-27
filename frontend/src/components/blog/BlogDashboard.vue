<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
} from 'chart.js'
import { Doughnut } from 'vue-chartjs'
import * as blogApi from '@/api/blog'
import { channelLabel, channelColor, typeColor } from '@/utils/blogFormatters'

ChartJS.register(ArcElement, Tooltip, Legend)

const props = defineProps<{
  branchFilter?: string
  hideAuthor?: boolean
}>()

const emit = defineEmits<{
  (e: 'navigate', tab: string, filter?: Record<string, any>): void
}>()

const dashboard = ref<any>(null)
const loading = ref(false)
const syncStatus = ref<any>(null)
const branchShowAll = ref(false)
const authorShowAll = ref(false)


// 월간 토글: 지점
const branchMonthMode = ref<'all' | 'monthly'>('monthly')
const branchMonth = ref('')
const branchMonthlyData = ref<any[]>([])
const branchMonthlyLoading = ref(false)

// 월간 토글: 담당자
const authorMonthMode = ref<'all' | 'monthly'>('all')
const authorMonth = ref('')
// 월간 토글: 종류
const typeMonthMode = ref<'all' | 'monthly'>('monthly')
const typeMonth = ref('')

// 사용 가능한 월 목록 (대시보드 데이터에서 추출)
const availableMonths = computed(() => {
  if (!dashboard.value?.monthly) return []
  return dashboard.value.monthly
    .map((m: any) => m.month)
    .sort((a: string, b: string) => b.localeCompare(a))
})

// 담당자 월간 데이터
const authorMonthlyData = ref<any[]>([])
const authorMonthlyLoading = ref(false)

// 종류 월간 데이터
const typeMonthlyData = ref<any[]>([])
const typeMonthlyLoading = ref(false)

function apiParams(extra?: Record<string, string>) {
  const p: any = {}
  if (props.branchFilter) p.branch_filter = props.branchFilter
  if (extra) Object.assign(p, extra)
  return p
}

async function loadDashboard() {
  loading.value = true
  try {
    const [dashRes, statusRes] = await Promise.all([
      blogApi.getBlogDashboard(apiParams()),
      blogApi.getNotionSyncStatus(),
    ])
    dashboard.value = dashRes.data
    syncStatus.value = statusRes.data?.last_sync || null

    // 초기 월 설정
    if (availableMonths.value.length > 0) {
      if (!authorMonth.value) authorMonth.value = availableMonths.value[0]
      if (!typeMonth.value) typeMonth.value = availableMonths.value[0]
      if (!branchMonth.value) {
        branchMonth.value = availableMonths.value[0]
        loadBranchMonthly()
      }
      if (!typeMonth.value || typeMonthMode.value === 'monthly') {
        loadTypeMonthly()
      }
    }
  } catch (e) {
    console.error('대시보드 로드 실패:', e)
  } finally {
    loading.value = false
  }
}

async function loadAuthorMonthly() {
  if (!authorMonth.value) return
  authorMonthlyLoading.value = true
  try {
    const { data } = await blogApi.getBlogDashboard(apiParams({ month: authorMonth.value }))
    authorMonthlyData.value = data.by_author || []
  } catch (e) {
    console.error(e)
  } finally {
    authorMonthlyLoading.value = false
  }
}

async function loadTypeMonthly() {
  if (!typeMonth.value) return
  typeMonthlyLoading.value = true
  try {
    const { data } = await blogApi.getBlogDashboard(apiParams({ month: typeMonth.value }))
    typeMonthlyData.value = data.by_type_monthly || data.by_type || []
  } catch (e) {
    console.error(e)
  } finally {
    typeMonthlyLoading.value = false
  }
}

async function loadBranchMonthly() {
  if (!branchMonth.value) return
  branchMonthlyLoading.value = true
  try {
    const { data } = await blogApi.getBlogDashboard(apiParams({ month: branchMonth.value }))
    branchMonthlyData.value = data.by_branch || []
  } catch (e) {
    console.error(e)
  } finally {
    branchMonthlyLoading.value = false
  }
}

function shiftMonth(current: string, delta: number): string {
  const idx = availableMonths.value.indexOf(current)
  const newIdx = idx - delta // -delta because list is desc sorted
  if (newIdx >= 0 && newIdx < availableMonths.value.length) {
    return availableMonths.value[newIdx]
  }
  return current
}

function prevAuthorMonth() {
  authorMonth.value = shiftMonth(authorMonth.value, -1)
}
function nextAuthorMonth() {
  authorMonth.value = shiftMonth(authorMonth.value, 1)
}
function prevBranchMonth() {
  branchMonth.value = shiftMonth(branchMonth.value, -1)
}
function nextBranchMonth() {
  branchMonth.value = shiftMonth(branchMonth.value, 1)
}
function prevTypeMonth() {
  typeMonth.value = shiftMonth(typeMonth.value, -1)
}
function nextTypeMonth() {
  typeMonth.value = shiftMonth(typeMonth.value, 1)
}

// 표시할 담당자 데이터
const displayAuthorData = computed(() => {
  if (authorMonthMode.value === 'monthly') return authorMonthlyData.value
  return dashboard.value?.by_author || []
})
const displayAuthors = computed(() => {
  return authorShowAll.value ? displayAuthorData.value : displayAuthorData.value.slice(0, 10)
})
const maxAuthorCount = computed(() => {
  if (!displayAuthorData.value.length) return 1
  return Math.max(...displayAuthorData.value.map((a: any) => a.cnt))
})

// 표시할 종류 데이터
const displayTypeData = computed(() => {
  if (typeMonthMode.value === 'monthly') return typeMonthlyData.value
  return dashboard.value?.by_type || []
})
const displayTypeTotal = computed(() => {
  return displayTypeData.value.reduce((sum: number, t: any) => sum + t.cnt, 0) || 1
})
const maxTypeCount = computed(() => {
  if (!displayTypeData.value.length) return 1
  return Math.max(...displayTypeData.value.map((t: any) => t.cnt))
})

// Watch month changes to reload data
watch(branchMonth, () => {
  if (branchMonthMode.value === 'monthly') loadBranchMonthly()
})
watch(branchMonthMode, (mode) => {
  if (mode === 'monthly') loadBranchMonthly()
})
watch(authorMonth, () => {
  if (authorMonthMode.value === 'monthly') loadAuthorMonthly()
})
watch(typeMonth, () => {
  if (typeMonthMode.value === 'monthly') loadTypeMonthly()
})
watch(authorMonthMode, (mode) => {
  if (mode === 'monthly') loadAuthorMonthly()
})
watch(typeMonthMode, (mode) => {
  if (mode === 'monthly') loadTypeMonthly()
})

// 카드 클릭 → 목록 이동
function goToList(filter?: Record<string, any>) {
  emit('navigate', 'list', filter)
}

const displayBranchData = computed(() => {
  if (branchMonthMode.value === 'monthly') return branchMonthlyData.value
  return dashboard.value?.by_branch || []
})
const maxBranchCount = computed(() => {
  if (!displayBranchData.value.length) return 1
  return Math.max(...displayBranchData.value.map((b: any) => b.cnt))
})
const displayBranches = computed(() => {
  return branchShowAll.value ? displayBranchData.value : displayBranchData.value.slice(0, 15)
})
const maxMonthlyCount = computed(() => {
  if (!dashboard.value?.monthly?.length) return 1
  return Math.max(...dashboard.value.monthly.map((m: any) => m.cnt))
})
const sortedMonthly = computed(() => {
  if (!dashboard.value?.monthly) return []
  return [...dashboard.value.monthly].sort((a: any, b: any) => a.month.localeCompare(b.month)).slice(-6)
})
const maxWeeklyCount = computed(() => {
  if (!dashboard.value?.weekly?.length) return 1
  return Math.max(...dashboard.value.weekly.map((w: any) => w.cnt))
})
const sortedWeekly = computed(() => {
  if (!dashboard.value?.weekly) return []
  return [...dashboard.value.weekly].sort((a: any, b: any) => a.week.localeCompare(b.week)).slice(-6)
})

// 월 네비게이션 가능 여부
const canPrevBranch = computed(() => {
  const idx = availableMonths.value.indexOf(branchMonth.value)
  return idx < availableMonths.value.length - 1
})
const canNextBranch = computed(() => {
  const idx = availableMonths.value.indexOf(branchMonth.value)
  return idx > 0
})
const canPrevAuthor = computed(() => {
  const idx = availableMonths.value.indexOf(authorMonth.value)
  return idx < availableMonths.value.length - 1
})
const canNextAuthor = computed(() => {
  const idx = availableMonths.value.indexOf(authorMonth.value)
  return idx > 0
})
const canPrevType = computed(() => {
  const idx = availableMonths.value.indexOf(typeMonth.value)
  return idx < availableMonths.value.length - 1
})
const canNextType = computed(() => {
  const idx = availableMonths.value.indexOf(typeMonth.value)
  return idx > 0
})

// 도넛 차트 데이터
const TYPE_COLORS: Record<string, string> = {
  '최적': '#10b981',       // emerald-500
  '정보성글': '#3b82f6',   // blue-500
  '홍보성글': '#f59e0b',   // amber-500
  '논문글': '#14b8a6',     // teal-500
  '임상글': '#f43f5e',     // rose-500
}
const FALLBACK_COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#64748b', '#a3e635']

const doughnutChartData = computed<{ labels: string[]; datasets: [{ data: number[]; backgroundColor: string[]; borderWidth: number }] }>(() => {
  const data = displayTypeData.value
  if (!data.length) {
    return { labels: [], datasets: [{ data: [], backgroundColor: [], borderWidth: 0 }] }
  }
  const labels: string[] = data.map((t: any) => t.post_type_main)
  const counts: number[] = data.map((t: any) => t.cnt)
  const colors: string[] = data.map((t: any, i: number) =>
    TYPE_COLORS[t.post_type_main] ?? FALLBACK_COLORS[i % FALLBACK_COLORS.length]
  )
  return {
    labels,
    datasets: [{ data: counts, backgroundColor: colors, borderWidth: 0 }],
  }
})

const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '62%',
  plugins: {
    legend: { display: false },
    tooltip: { enabled: true },
  },
}

const doughnutTotal = computed(() => displayTypeTotal.value === 1 && displayTypeData.value.length === 0 ? 0 : displayTypeTotal.value)

// 도넛 범례: {label, color, cnt} 배열로 합산하여 템플릿 인덱스 접근 불필요
const doughnutLegend = computed<{ label: string; color: string; cnt: number }[]>(() => {
  const data = displayTypeData.value
  const colors = doughnutChartData.value.datasets[0].backgroundColor
  return data.map((t: any, i: number) => ({
    label: t.post_type_main,
    color: colors[i] as string,
    cnt: t.cnt,
  }))
})

const lastSyncLabel = computed(() => {
  return syncStatus.value?.synced_at?.slice(0, 10) ?? '-'
})

onMounted(() => {
  loadDashboard()
})
</script>

<template>
  <div class="flex-1 overflow-auto space-y-3">
    <div v-if="loading" class="text-center py-12 text-slate-400">로딩 중...</div>
    <template v-else-if="dashboard">

      <!-- Row 1: 1줄 통계바 -->
      <div class="flex items-center gap-5 px-4 py-2.5 bg-slate-50 rounded-lg border border-slate-200 text-sm shrink-0">
        <div class="flex items-baseline gap-1.5 cursor-pointer" @click="goToList()">
          <span class="text-slate-500 text-xs">전체 게시글</span>
          <span class="font-bold text-slate-800 tabular-nums">{{ dashboard.total?.toLocaleString() }}</span>
        </div>
        <span class="text-slate-300">·</span>
        <div class="flex items-baseline gap-1.5 cursor-pointer" @click="goToList({ channel: 'br' })">
          <span class="text-slate-500 text-xs">브랜드</span>
          <span class="font-bold text-blue-600 tabular-nums">{{ (dashboard.by_channel?.br || 0).toLocaleString() }}</span>
        </div>
        <span class="text-slate-300">·</span>
        <div class="flex items-baseline gap-1.5 cursor-pointer" @click="goToList({ channel: 'opt' })">
          <span class="text-slate-500 text-xs">최적</span>
          <span class="font-bold text-emerald-600 tabular-nums">{{ (dashboard.by_channel?.opt || 0).toLocaleString() }}</span>
        </div>
        <span class="text-slate-300">·</span>
        <div class="flex items-baseline gap-1.5 cursor-pointer" @click="goToList({ channel: 'cafe' })">
          <span class="text-slate-500 text-xs">카페</span>
          <span class="font-bold text-purple-600 tabular-nums">{{ (dashboard.by_channel?.cafe || 0).toLocaleString() }}</span>
        </div>
        <span class="text-slate-300">·</span>
        <div class="flex items-baseline gap-1.5 cursor-pointer" @click="goToList({ needs_review: 1 })">
          <span class="text-slate-500 text-xs">검토 필요</span>
          <span class="font-bold tabular-nums" :class="(dashboard.review_count || 0) > 0 ? 'text-amber-600' : 'text-slate-800'">
            {{ (dashboard.review_count || 0).toLocaleString() }}
          </span>
        </div>
        <span class="text-xs text-slate-400 ml-auto">마지막 동기화: {{ lastSyncLabel }}</span>
      </div>

      <!-- Row 2: 이번주 발행글 | 지난주 발행글 -->
      <div class="grid grid-cols-2 gap-3">
        <div class="bg-white border border-slate-200 rounded-lg p-3">
          <h3 class="text-sm font-semibold text-slate-700 mb-3">
            이번주 발행글
            <span class="text-[10px] text-slate-400 font-normal ml-1">{{ (dashboard.this_week || []).length }}건</span>
          </h3>
          <div class="max-h-[300px] overflow-auto">
            <table class="w-full text-xs table-fixed">
              <colgroup>
                <col style="width:50px" />
                <col style="width:56px" />
                <col />
                <col v-if="!hideAuthor" style="width:44px" />
                <col style="width:48px" />
              </colgroup>
              <tbody>
                <tr v-for="r in (dashboard.this_week || [])" :key="r.id"
                    class="border-b border-slate-50 hover:bg-slate-50/50">
                  <td class="py-1 pr-1">
                    <span class="text-[10px] px-1 py-0.5 rounded-full" :class="channelColor(r.blog_channel)">{{ channelLabel(r.blog_channel) }}</span>
                  </td>
                  <td class="py-1 pr-1">
                    <span v-if="r.post_type_main" class="text-[10px] px-1 py-0.5 rounded" :class="typeColor(r.post_type_main)">{{ r.post_type_main }}</span>
                  </td>
                  <td class="py-1 pr-1 text-slate-600 truncate">{{ r.clean_title || r.keyword || '-' }}</td>
                  <td v-if="!hideAuthor" class="py-1 text-slate-500 text-right whitespace-nowrap">{{ r.author_main || '-' }}</td>
                  <td class="py-1 text-slate-400 text-right whitespace-nowrap">{{ r.published_at?.slice(5) }}</td>
                </tr>
                <tr v-if="!(dashboard.this_week || []).length">
                  <td :colspan="hideAuthor ? 4 : 5" class="py-4 text-center text-slate-400">이번주 발행글 없음</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="bg-white border border-slate-200 rounded-lg p-3">
          <h3 class="text-sm font-semibold text-slate-700 mb-3">
            지난주 발행글
            <span class="text-[10px] text-slate-400 font-normal ml-1">{{ (dashboard.last_week || []).length }}건</span>
          </h3>
          <div class="max-h-[300px] overflow-auto">
            <table class="w-full text-xs table-fixed">
              <colgroup>
                <col style="width:50px" />
                <col style="width:56px" />
                <col />
                <col v-if="!hideAuthor" style="width:44px" />
                <col style="width:48px" />
              </colgroup>
              <tbody>
                <tr v-for="r in (dashboard.last_week || [])" :key="r.id"
                    class="border-b border-slate-50 hover:bg-slate-50/50">
                  <td class="py-1 pr-1">
                    <span class="text-[10px] px-1 py-0.5 rounded-full" :class="channelColor(r.blog_channel)">{{ channelLabel(r.blog_channel) }}</span>
                  </td>
                  <td class="py-1 pr-1">
                    <span v-if="r.post_type_main" class="text-[10px] px-1 py-0.5 rounded" :class="typeColor(r.post_type_main)">{{ r.post_type_main }}</span>
                  </td>
                  <td class="py-1 pr-1 text-slate-600 truncate">{{ r.clean_title || r.keyword || '-' }}</td>
                  <td v-if="!hideAuthor" class="py-1 text-slate-500 text-right whitespace-nowrap">{{ r.author_main || '-' }}</td>
                  <td class="py-1 text-slate-400 text-right whitespace-nowrap">{{ r.published_at?.slice(5) }}</td>
                </tr>
                <tr v-if="!(dashboard.last_week || []).length">
                  <td :colspan="hideAuthor ? 4 : 5" class="py-4 text-center text-slate-400">지난주 발행글 없음</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Row 3: 지점별 게시글 수 (풀폭) -->
      <div class="bg-white border border-slate-200 rounded-lg p-3">
        <div class="flex items-center gap-2 mb-3">
          <h3 class="text-sm font-semibold text-slate-700">
            지점별 게시글 수
            <span class="text-[10px] text-slate-400 font-normal ml-1">{{ displayBranchData.length }}개 지점</span>
          </h3>
          <div class="flex items-center gap-1 ml-auto">
            <button @click="branchMonthMode = 'all'"
              class="text-[10px] px-2 py-0.5 rounded transition-colors"
              :class="branchMonthMode === 'all' ? 'bg-slate-700 text-white' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'"
            >전체</button>
            <button @click="branchMonthMode = 'monthly'"
              class="text-[10px] px-2 py-0.5 rounded transition-colors"
              :class="branchMonthMode === 'monthly' ? 'bg-slate-700 text-white' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'"
            >월간</button>
            <template v-if="branchMonthMode === 'monthly'">
              <button @click="prevBranchMonth" :disabled="!canPrevBranch"
                      class="text-slate-400 hover:text-slate-600 disabled:opacity-30 px-0.5">&larr;</button>
              <span class="text-[11px] text-slate-600 min-w-[52px] text-center">{{ branchMonth?.slice(2) }}</span>
              <button @click="nextBranchMonth" :disabled="!canNextBranch"
                      class="text-slate-400 hover:text-slate-600 disabled:opacity-30 px-0.5">&rarr;</button>
            </template>
          </div>
        </div>
        <div v-if="branchMonthlyLoading && branchMonthMode === 'monthly'" class="text-center py-4 text-slate-400 text-xs">로딩...</div>
        <div v-else :class="branchShowAll ? 'max-h-[420px] overflow-y-auto overflow-x-hidden' : 'overflow-hidden'"
             class="grid gap-x-6 gap-y-1" style="grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));">
          <div v-for="b in displayBranches" :key="b.branch_name"
               class="flex items-center gap-2 cursor-pointer hover:bg-slate-50 rounded px-1 py-0.5 transition-colors"
               @click="goToList({ project_branch: b.branch_name })">
            <span class="w-24 text-right text-slate-600 truncate shrink-0 text-xs">{{ b.branch_name }}</span>
            <div class="flex-1 bg-slate-100 rounded-full h-4 min-w-0 overflow-hidden">
              <div class="bg-blue-400 h-full rounded-full transition-all"
                   :style="{ width: (b.cnt / maxBranchCount * 100) + '%' }"></div>
            </div>
            <span class="w-10 text-right text-slate-600 shrink-0 text-xs font-medium tabular-nums">{{ b.cnt }}</span>
          </div>
          <div v-if="displayBranchData.length === 0" class="text-xs text-slate-400 text-center py-3 col-span-full">데이터 없음</div>
        </div>
        <button v-if="displayBranchData.length > 15"
                @click="branchShowAll = !branchShowAll"
                class="mt-2 text-[11px] text-blue-500 hover:underline">
          {{ branchShowAll ? '상위 15개만 보기' : `전체 ${displayBranchData.length}개 지점 보기` }}
        </button>
      </div>

      <!-- Row 4: 차트 3-column (월별 추이 | 주간 추이 | 원고 종류별 도넛) -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">

        <!-- 월별 발행 추이 -->
        <div class="bg-white border border-slate-200 rounded-lg p-3">
          <h4 class="text-sm font-semibold text-slate-700 mb-3">월별 발행 추이</h4>
          <div class="flex items-end gap-1 h-20">
            <div v-for="m in sortedMonthly" :key="m.month"
                 class="flex-1 flex flex-col items-center justify-end cursor-pointer group"
                 @click="goToList({ project_month: m.month })">
              <span class="text-xs text-slate-500 mb-1 group-hover:text-indigo-600 font-semibold">{{ m.cnt.toLocaleString() }}</span>
              <div class="w-4/5 bg-indigo-300 group-hover:bg-indigo-400 rounded-t transition-all min-h-[2px]"
                   :style="{ height: (m.cnt / maxMonthlyCount * 70) + 'px' }"></div>
              <span class="text-[11px] text-slate-400 mt-1.5 whitespace-nowrap">{{ m.month.slice(2) }}</span>
            </div>
          </div>
        </div>

        <!-- 주간 발행 추이 -->
        <div class="bg-white border border-slate-200 rounded-lg p-3">
          <div class="flex items-center justify-between mb-3">
            <h4 class="text-sm font-semibold text-slate-700">주간 발행 추이</h4>
            <span class="text-xs text-slate-400">최근 6주</span>
          </div>
          <div class="flex items-end gap-1 h-20">
            <div v-for="w in sortedWeekly" :key="w.week"
                 class="flex-1 flex flex-col items-center justify-end group">
              <span class="text-xs text-slate-500 mb-1 group-hover:text-sky-600 font-semibold">{{ w.cnt }}</span>
              <div class="w-4/5 bg-sky-300 group-hover:bg-sky-400 rounded-t transition-all min-h-[2px]"
                   :style="{ height: (w.cnt / maxWeeklyCount * 70) + 'px' }"></div>
              <span class="text-[11px] text-slate-400 mt-1.5 whitespace-nowrap">{{ w.week_start?.slice(5) }}</span>
            </div>
          </div>
        </div>

        <!-- 원고 종류별 분포 (도넛) -->
        <div class="bg-white border border-slate-200 rounded-lg p-3">
          <div class="flex items-center justify-between mb-3">
            <h4 class="text-sm font-semibold text-slate-700">원고 종류별 분포</h4>
            <div class="flex items-center gap-1">
              <button @click="typeMonthMode = 'all'"
                class="text-[10px] px-2 py-0.5 rounded transition-colors"
                :class="typeMonthMode === 'all' ? 'bg-slate-700 text-white' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'"
              >전체</button>
              <button @click="typeMonthMode = 'monthly'"
                class="text-[10px] px-2 py-0.5 rounded transition-colors"
                :class="typeMonthMode === 'monthly' ? 'bg-slate-700 text-white' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'"
              >월간</button>
              <template v-if="typeMonthMode === 'monthly'">
                <button @click="prevTypeMonth" :disabled="!canPrevType"
                        class="text-slate-400 hover:text-slate-600 disabled:opacity-30 px-0.5">&larr;</button>
                <span class="text-[11px] text-slate-600 min-w-[44px] text-center">{{ typeMonth.slice(2) }}</span>
                <button @click="nextTypeMonth" :disabled="!canNextType"
                        class="text-slate-400 hover:text-slate-600 disabled:opacity-30 px-0.5">&rarr;</button>
              </template>
            </div>
          </div>
          <div v-if="typeMonthlyLoading && typeMonthMode === 'monthly'" class="text-center py-4 text-slate-400 text-xs">로딩...</div>
          <div v-else-if="displayTypeData.length === 0" class="text-xs text-slate-400 text-center py-6">데이터 없음</div>
          <div v-else class="flex items-center gap-3">
            <!-- 도넛 + 중앙 텍스트 -->
            <div class="relative shrink-0" style="width:90px;height:90px;">
              <Doughnut :data="doughnutChartData" :options="doughnutOptions" />
              <div class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span class="text-base font-bold text-slate-800 tabular-nums leading-none">{{ doughnutTotal.toLocaleString() }}</span>
                <span class="text-[10px] text-slate-400 leading-none mt-0.5">원고</span>
              </div>
            </div>
            <!-- 범례 -->
            <div class="flex flex-col gap-1 min-w-0 flex-1">
              <div v-for="item in doughnutLegend" :key="item.label"
                   class="flex items-center gap-1.5 text-xs cursor-pointer hover:bg-slate-50 rounded px-1 -mx-1 py-0.5 transition-colors"
                   @click="goToList({ post_type_main: item.label })">
                <span class="w-2 h-2 rounded-full shrink-0"
                      :style="{ backgroundColor: item.color }"></span>
                <span class="text-slate-600 truncate flex-1">{{ item.label }}</span>
                <span class="text-slate-700 font-medium tabular-nums shrink-0">{{ item.cnt.toLocaleString() }}</span>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- 담당자별 게시글 수 — 관리자만 -->
      <div v-if="!hideAuthor" class="bg-white border border-slate-200 rounded-lg p-3">
        <div class="flex items-center gap-2 mb-3">
          <h3 class="text-sm font-semibold text-slate-700">담당자별 게시글 수</h3>
          <div class="flex items-center gap-1 ml-auto">
            <button @click="authorMonthMode = 'all'"
              class="text-[10px] px-2 py-0.5 rounded transition-colors"
              :class="authorMonthMode === 'all' ? 'bg-slate-700 text-white' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'"
            >전체</button>
            <button @click="authorMonthMode = 'monthly'"
              class="text-[10px] px-2 py-0.5 rounded transition-colors"
              :class="authorMonthMode === 'monthly' ? 'bg-slate-700 text-white' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'"
            >월간</button>
            <template v-if="authorMonthMode === 'monthly'">
              <button @click="prevAuthorMonth" :disabled="!canPrevAuthor"
                      class="text-slate-400 hover:text-slate-600 disabled:opacity-30 px-0.5">&larr;</button>
              <span class="text-[11px] text-slate-600 min-w-[52px] text-center">{{ authorMonth.slice(2) }}</span>
              <button @click="nextAuthorMonth" :disabled="!canNextAuthor"
                      class="text-slate-400 hover:text-slate-600 disabled:opacity-30 px-0.5">&rarr;</button>
            </template>
          </div>
        </div>
        <div v-if="authorMonthlyLoading && authorMonthMode === 'monthly'" class="text-center py-4 text-slate-400 text-xs">로딩...</div>
        <div v-else class="grid grid-cols-2 gap-x-6 gap-y-1">
          <div v-for="a in displayAuthors" :key="a.author_main"
               class="flex items-center gap-2 text-xs cursor-pointer hover:bg-slate-50 rounded px-1 -mx-1 py-0.5 transition-colors"
               @click="goToList({ author: a.author_main })">
            <span class="w-14 text-right text-slate-600 truncate shrink-0">{{ a.author_main }}</span>
            <div class="flex-1 bg-slate-100 rounded-full h-3 overflow-hidden">
              <div class="bg-amber-300 h-full rounded-full"
                   :style="{ width: (a.cnt / maxAuthorCount * 100) + '%' }"></div>
            </div>
            <span class="w-12 text-right text-slate-500 shrink-0">{{ a.cnt.toLocaleString() }}</span>
          </div>
          <div v-if="displayAuthorData.length === 0" class="text-xs text-slate-400 text-center py-3 col-span-2">데이터 없음</div>
        </div>
        <button v-if="displayAuthorData.length > 10"
                @click="authorShowAll = !authorShowAll"
                class="mt-2 text-[11px] text-blue-500 hover:underline">
          {{ authorShowAll ? '접기' : `전체 ${displayAuthorData.length}명 보기` }}
        </button>
      </div>

    </template>
  </div>
</template>
