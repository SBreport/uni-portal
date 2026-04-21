<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useAgencyVisibility } from '@/composables/useAgencyVisibility'
import { getWebpageRankingDaily, syncWebpageToDB, getWebpageLastSync, getWebpageBranchDetail } from '@/api/webpage'
import { fetchAgencyMap } from '@/api/branches'
import { shortName } from '@/utils/branchName'

const auth = useAuthStore()
const isBranch = computed(() => auth.role === 'branch')
const { canSeeAgency } = useAgencyVisibility()
const isEditor = computed(() => ['admin', 'editor'].includes(auth.role))

interface DailyData {
  day: number
  exposed: number
  mark: string  // ㅇ, x, 빈값
}

interface BranchRanking {
  branch: string
  branch_id: number
  short_name?: string | null
  keyword: string
  nosul_count: number
  total_exposed: number
  today_exposed: boolean
  streak: number
  status: 'active' | 'fail' | '미달' | 'stopped'
  work_days: number
  daily: DailyData[]
  last_success_date?: string | null
  recovery_date?: string | null
  recovery_gap?: number | null
}

interface WebpageData {
  date: string
  branches: BranchRanking[]
  summary: { total: number; success_today: number; fail_today: number; midal: number }
}

// ── 실행사 매핑 (API에서 로드) ──
const agencyMap = ref<Record<string, string>>({})

function getAgency(branch: string): string {
  return agencyMap.value[branch] || '-'
}

const loading = ref(true)
const error = ref('')
const data = ref<WebpageData | null>(null)
const syncing = ref<'current' | 'specific' | false>(false)
const showMonthPicker = ref(false)
const pickerYear = ref(new Date().getFullYear())
const pickerMonth = ref<number | null>(null)
const lastSync = ref<string | null>(null)

const today = new Date()
const selectedDate = ref(today.toISOString().slice(0, 10))

function goDay(offset: number) {
  const d = new Date(selectedDate.value)
  d.setDate(d.getDate() + offset)
  selectedDate.value = d.toISOString().slice(0, 10)
}

const displayDate = computed(() => {
  const d = new Date(selectedDate.value)
  return `${d.getFullYear()}.${d.getMonth() + 1}.${d.getDate()} (${['일','월','화','수','목','금','토'][d.getDay()]})`
})

const isAdmin = computed(() => auth.role === 'admin')

// 검색 + 정렬
const searchQuery = ref('')
type SortKey = 'branch' | 'keyword' | 'today_exposed' | 'streak' | 'work_days' | 'nosul_count' | 'total_exposed' | 'status' | 'agency'
const sortKey = ref<SortKey>('nosul_count')
const sortAsc = ref(false)

function toggleSort(key: SortKey) {
  if (sortKey.value === key) {
    sortAsc.value = !sortAsc.value
  } else {
    sortKey.value = key
    sortAsc.value = key === 'branch' || key === 'keyword' || key === 'agency'
  }
}

function sortIcon(key: SortKey): string {
  if (sortKey.value !== key) return '↕'
  return sortAsc.value ? '↑' : '↓'
}

const filteredBranches = computed(() => {
  if (!data.value) return []
  let list = [...data.value.branches]

  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    list = list.filter(b =>
      b.branch.toLowerCase().includes(q) ||
      b.keyword.toLowerCase().includes(q) ||
      shortName(b).toLowerCase().includes(q)
    )
  }

  const dir = sortAsc.value ? 1 : -1
  list.sort((a, b) => {
    let av: any, bv: any
    switch (sortKey.value) {
      case 'branch': av = shortName(a); bv = shortName(b); break
      case 'keyword': av = a.keyword; bv = b.keyword; break
      case 'today_exposed': av = a.today_exposed ? 0 : 1; bv = b.today_exposed ? 0 : 1; break
      case 'streak': av = a.streak; bv = b.streak; break
      case 'nosul_count': av = a.nosul_count; bv = b.nosul_count; break
      case 'total_exposed': av = a.total_exposed; bv = b.total_exposed; break
      case 'work_days': av = a.work_days; bv = b.work_days; break
      case 'agency': av = getAgency(a.branch); bv = getAgency(b.branch); break
      case 'status':
        const order: Record<string, number> = { 'active': 0, 'fail': 1, '미달': 2, 'stopped': 3 }
        av = order[a.status] ?? 9; bv = order[b.status] ?? 9; break
    }
    if (av < bv) return -1 * dir
    if (av > bv) return 1 * dir
    return 0
  })

  return list
})

const failedBranches = computed(() =>
  data.value?.branches.filter(b => b.status === 'fail') ?? []
)

const sortedByNosul = computed(() => {
  if (!data.value) return []
  return [...data.value.branches]
    .filter(b => b.status !== '미달')
    .sort((a, b) => b.nosul_count - a.nosul_count)
})

const midalBranches = computed(() =>
  data.value?.branches.filter(b => b.status === '미달') ?? []
)

const allFailed = computed(() => {
  if (!data.value?.branches.length) return false
  // 성공(노출)이 단 한 건도 없을 때 (미노출 + 미점유 전부 포함)
  return data.value.branches.every((b: BranchRanking) => !b.today_exposed)
})

// 실행사별 성과 집계
interface AgencyStat {
  name: string
  total: number
  success: number
  fail: number
  midal: number
  avgNosul: number
  notUpdated: boolean
}
const agencyStats = computed<AgencyStat[]>(() => {
  if (!data.value) return []
  const names = [...new Set(Object.values(agencyMap.value))].filter(Boolean)
  if (names.length === 0) return []
  return names.map(name => {
    const branches = data.value!.branches.filter(b => getAgency(b.branch) === name)
    const total = branches.length
    const success = branches.filter(b => b.status === 'active').length
    const midal = branches.filter(b => b.status === '미달').length
    const fail = total - success - midal
    const sumNosul = branches.reduce((s, b) => s + b.nosul_count, 0)
    const notUpdated = total > 0 && success === 0
    return { name, total, success, fail, midal, avgNosul: total > 0 ? Math.round(sumNosul / total) : 0, notUpdated }
  })
})

function pct(count: number, total: number): string {
  if (total === 0) return '0'
  return Math.round((count / total) * 100).toString()
}

function recentDays(b: BranchRanking): { day: number; exposed: number; mark: string }[] {
  return b.daily || []
}

function getRecoveryInfo(b: BranchRanking): { show: boolean; label: string } {
  if (!b.today_exposed) return { show: false, label: '' }
  if (b.recovery_date == null) return { show: false, label: '' }

  // 복귀 후 7일이 지나면 녹색 불 OFF
  const recovery = new Date(b.recovery_date)
  const ref = new Date(selectedDate.value)
  const daysSinceRecovery = Math.floor((ref.getTime() - recovery.getTime()) / (1000 * 60 * 60 * 24))
  if (daysSinceRecovery > 7) return { show: false, label: '' }

  const recoveryPart = b.recovery_gap == null ? '첫 성공' : `${b.recovery_gap}일 만에 회복`
  const holdPart = (b.streak && b.streak > 1) ? ` · ${b.streak}일째 유지` : ''
  return { show: true, label: recoveryPart + holdPart }
}

// YY-MM-DD 형식으로 날짜 변환 (YYYY-MM-DD 또는 기타 형식 입력 허용)
function fmtDate(raw: string | null | undefined): string {
  if (!raw) return ''
  // YYYY-MM-DD → YY-MM-DD
  const m = raw.match(/^(\d{4})-(\d{2}-\d{2})$/)
  if (m) return m[1].slice(2) + '-' + m[2]
  // 이미 YY-MM-DD 이하면 그대로
  return raw
}

function barWidth(count: number): number {
  if (count <= 0) return 0
  return Math.min(100, (count / 25) * 100)
}

function barColor(count: number): string {
  if (count >= 23) return 'bg-red-400'
  if (count >= 15) return 'bg-amber-400'
  if (count >= 1) return 'bg-blue-400'
  return 'bg-slate-300'
}

function statusBadge(status: string): { text: string; cls: string } {
  switch (status) {
    case 'active': return { text: '노출', cls: 'bg-blue-100 text-blue-700' }
    case 'fail': return { text: '미노출', cls: 'bg-red-100 text-red-600' }
    case '미달': return { text: '미점유', cls: 'bg-slate-100 text-slate-400' }
    default: return { text: status, cls: 'bg-yellow-100 text-yellow-700' }
  }
}


// ── 확장 행 토글 ──
const expandedBranch = ref<string | null>(null)
const detailData = ref<any>(null)
const detailLoading = ref(false)
const detailError = ref('')

async function toggleBranch(b: BranchRanking) {
  if (!isEditor.value) return
  if (expandedBranch.value === b.branch) {
    expandedBranch.value = null
    detailData.value = null
    detailError.value = ''
    return
  }
  expandedBranch.value = b.branch
  detailLoading.value = true
  detailData.value = null
  detailError.value = ''
  try {
    const { data: res } = await getWebpageBranchDetail(b.branch, b.keyword, selectedDate.value)
    detailData.value = res
  } catch (e: any) {
    detailError.value = e.response?.data?.detail || '데이터를 불러올 수 없습니다'
  } finally {
    detailLoading.value = false
  }
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const { data: res } = await getWebpageRankingDaily(selectedDate.value)
    data.value = res
  } catch (e: any) {
    error.value = e.response?.data?.detail || '데이터를 불러올 수 없습니다'
    data.value = null
  } finally {
    loading.value = false
  }
}

async function handleSyncCurrentMonth() {
  if (!confirm('이번 달 데이터를 동기화합니다. 시간이 걸릴 수 있습니다.')) return
  syncing.value = 'current'
  error.value = ''
  try {
    const { data: res } = await syncWebpageToDB()
    let msg = `동기화 완료: ${res.sheets_processed}개 시트, ${res.records_saved?.toLocaleString()}건 저장`
    if (res.agency_changes?.length) {
      msg += `\n\n실행사 변경 ${res.agency_changes.length}건:`
      for (const c of res.agency_changes) {
        msg += `\n  ${c.branch}: ${c.from} → ${c.to}`
      }
    }
    alert(msg)
    await loadData()
    await loadLastSync()
  } catch (e: any) {
    error.value = e.response?.data?.detail || '동기화 실패'
  } finally {
    syncing.value = false
  }
}

async function handleSyncSpecificMonth() {
  if (pickerMonth.value === null) return
  const ym = `${pickerYear.value}-${String(pickerMonth.value).padStart(2, '0')}`
  if (!confirm(`${pickerYear.value}년 ${pickerMonth.value}월 데이터를 동기화합니다. 시간이 걸릴 수 있습니다.`)) return
  showMonthPicker.value = false
  syncing.value = 'specific'
  error.value = ''
  try {
    const { data: res } = await syncWebpageToDB(ym)
    let msg = `동기화 완료 (${ym}): ${res.sheets_processed}개 시트, ${res.records_saved?.toLocaleString()}건 저장`
    if (res.agency_changes?.length) {
      msg += `\n\n실행사 변경 ${res.agency_changes.length}건:`
      for (const c of res.agency_changes) {
        msg += `\n  ${c.branch}: ${c.from} → ${c.to}`
      }
    }
    alert(msg)
    await loadData()
    await loadLastSync()
  } catch (e: any) {
    error.value = e.response?.data?.detail || '동기화 실패'
  } finally {
    syncing.value = false
  }
}

async function loadLastSync() {
  try {
    const { data: res } = await getWebpageLastSync()
    lastSync.value = res.synced_at || null
  } catch { /* ignore */ }
}

watch(selectedDate, () => loadData())

onMounted(async () => {
  loadData()
  loadLastSync()
  try {
    const data = await fetchAgencyMap('webpage')
    agencyMap.value = data
  } catch {}
})
</script>

<template>
  <div class="webpage-page flex flex-col overflow-hidden" style="height: calc(100vh - 48px)">

    <!-- ─── ROW 1: 타이틀 + 년/월 + 동기화 + 오늘 요약 숫자 ─── -->
    <div class="flex flex-wrap items-center gap-x-4 gap-y-1 px-5 pt-3 pb-2 shrink-0">
      <h2 class="text-lg font-bold text-slate-800 shrink-0">웹페이지</h2>

      <div class="flex items-center gap-1 shrink-0">
        <button @click="goDay(-1)"
          class="w-7 h-7 flex items-center justify-center rounded-md border border-slate-200 text-slate-400 hover:bg-slate-50 transition text-xs">&lt;</button>
        <label class="relative cursor-pointer">
          <span class="px-2 text-sm font-medium text-slate-700 min-w-[120px] text-center">{{ displayDate }}</span>
          <input type="date" v-model="selectedDate"
            class="absolute inset-0 opacity-0 cursor-pointer" />
        </label>
        <button @click="goDay(1)"
          class="w-7 h-7 flex items-center justify-center rounded-md border border-slate-200 text-slate-400 hover:bg-slate-50 transition text-xs">&gt;</button>
      </div>

      <!-- 오늘 동기화 (primary) -->
      <button v-if="isAdmin" @click="handleSyncCurrentMonth" :disabled="!!syncing"
        class="text-xs px-3 py-1 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 shrink-0 font-medium">
        {{ syncing === 'current' ? '동기화 중...' : '오늘 동기화' }}
      </button>

      <!-- 선택 동기화 (secondary) -->
      <button v-if="isAdmin" @click="showMonthPicker = true; pickerMonth = null; pickerYear = new Date().getFullYear()" :disabled="!!syncing"
        class="text-xs px-3 py-1 rounded border border-slate-300 hover:bg-slate-50 disabled:opacity-50 shrink-0 text-slate-600">
        {{ syncing === 'specific' ? '동기화 중...' : '선택 동기화' }}
      </button>

      <!-- 월 선택 모달 -->
      <Teleport to="body">
        <div v-if="showMonthPicker" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          @click.self="showMonthPicker = false">
          <div class="bg-white rounded-lg shadow-xl p-4 w-64">
            <!-- 연도 네비게이션 -->
            <div class="flex items-center justify-between mb-3">
              <button @click="pickerYear--" class="w-7 h-7 flex items-center justify-center rounded hover:bg-slate-100 text-slate-500">&lt;</button>
              <span class="text-sm font-semibold text-slate-700">{{ pickerYear }}년</span>
              <button @click="pickerYear++" :disabled="pickerYear >= new Date().getFullYear()"
                class="w-7 h-7 flex items-center justify-center rounded hover:bg-slate-100 text-slate-500 disabled:opacity-30">&gt;</button>
            </div>

            <!-- 월 그리드 (3×4) -->
            <div class="grid grid-cols-3 gap-1.5 mb-4">
              <button
                v-for="m in 12" :key="m"
                @click="pickerMonth = m"
                :disabled="pickerYear === new Date().getFullYear() && m > new Date().getMonth() + 1"
                :class="[
                  'py-1.5 text-sm rounded border transition',
                  pickerMonth === m
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'border-slate-200 hover:bg-slate-50 text-slate-700',
                  pickerYear === new Date().getFullYear() && m > new Date().getMonth() + 1
                    ? 'opacity-30 cursor-not-allowed' : ''
                ]">
                {{ m }}월
              </button>
            </div>

            <!-- 하단 버튼 -->
            <div class="flex gap-2 justify-end">
              <button @click="showMonthPicker = false"
                class="text-xs px-3 py-1.5 rounded border border-slate-300 hover:bg-slate-50 text-slate-600">취소</button>
              <button @click="handleSyncSpecificMonth" :disabled="pickerMonth === null"
                class="text-xs px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40">갱신</button>
            </div>
          </div>
        </div>
      </Teleport>
      <span v-if="lastSync" class="text-[10px] text-slate-400 shrink-0">최종 동기화: {{ lastSync }}</span>
      <!-- 노출/미노출/미점유 큰 숫자 -->
      <template v-if="data">
        <div class="flex items-center gap-2 shrink-0">
          <div class="flex items-baseline gap-1 px-2 py-1 bg-blue-50 rounded-lg whitespace-nowrap">
            <span class="text-2xl font-bold text-blue-600">{{ data.summary.success_today }}</span>
            <span class="text-xs text-blue-400">노출 ({{ pct(data.summary.success_today, data.summary.total) }}%)</span>
          </div>
          <div class="flex items-baseline gap-1 px-2 py-1 bg-red-50 rounded-lg whitespace-nowrap">
            <span class="text-2xl font-bold text-red-500">{{ data.summary.fail_today }}</span>
            <span class="text-xs text-red-400">미노출 ({{ pct(data.summary.fail_today, data.summary.total) }}%)</span>
          </div>
          <div class="flex items-baseline gap-1 px-2 py-1 bg-slate-100 rounded-lg whitespace-nowrap">
            <span class="text-2xl font-bold text-slate-500">{{ data.summary.midal }}</span>
            <span class="text-xs text-slate-400">미점유 ({{ pct(data.summary.midal, data.summary.total) }}%)</span>
          </div>
        </div>
        <!-- 검색 -->
        <div class="shrink-0">
          <input v-model="searchQuery" type="text" placeholder="지점 · 키워드 검색"
            class="w-40 px-2.5 py-1 border border-slate-200 rounded-md text-xs bg-white focus:outline-none focus:ring-1 focus:ring-blue-400 placeholder:text-slate-400" />
        </div>
      </template>
    </div>

    <!-- 에러 -->
    <div v-if="error" class="mx-5 mb-2 p-2 bg-red-50 border border-red-200 rounded-lg text-xs text-red-600 shrink-0">{{ error }}</div>

    <!-- 로딩 -->
    <div v-if="loading" class="flex items-center justify-center flex-1">
      <div class="text-slate-400 text-sm">데이터를 불러오는 중...</div>
    </div>

    <template v-else-if="data">
      <!-- ─── 전체 실패: 중앙 안내 오버레이 ─── -->
      <div v-if="allFailed" class="flex flex-col items-center justify-center flex-1">
        <div class="text-center">
          <p class="text-lg font-semibold text-slate-600 mb-1">금일 데이터는 아직 갱신되지 않았습니다</p>
          <p class="text-sm text-slate-400">다른 날짜를 선택하여 이전 데이터를 확인할 수 있습니다</p>
        </div>
      </div>

      <template v-else>
      <!-- ─── ROW 2: 미노출 · 미점유 태그 ─── -->
      <div class="px-5 pb-1.5 shrink-0">
        <div class="bg-white border border-slate-200 rounded-lg px-3 py-2">
          <div class="flex flex-wrap items-center gap-1">
            <span class="text-[11px] text-slate-400 mr-1 shrink-0">미노출</span>
            <span v-for="b in failedBranches" :key="b.branch"
              class="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-red-50 border border-red-100 rounded text-[11px] text-red-600">
              {{ shortName(b) }}
            </span>
            <template v-if="midalBranches.length > 0">
              <span class="text-slate-300 mx-1">|</span>
              <span class="text-[11px] text-slate-400 mr-1 shrink-0">미점유</span>
              <span v-for="b in midalBranches" :key="b.branch"
                class="px-1.5 py-0.5 bg-slate-50 border border-slate-200 rounded text-[11px] text-slate-500">
                {{ shortName(b) }}
              </span>
            </template>
          </div>
        </div>
      </div>

      <!-- ─── ROW 3: 실행사 카드 ─── -->
      <div v-if="canSeeAgency && agencyStats.length > 0" class="grid gap-2 px-5 pb-1.5 shrink-0"
        :style="{ gridTemplateColumns: `repeat(${Math.min(agencyStats.length, 4)}, 1fr)` }">
        <div v-for="a in agencyStats" :key="a.name"
          class="bg-white border border-slate-200 rounded-lg px-3 py-2 relative overflow-hidden">
          <!-- 미갱신 블러 오버레이 -->
          <div v-if="a.notUpdated"
            class="absolute inset-0 z-10 flex items-center justify-center rounded-lg backdrop-blur-[2px] bg-white/60">
            <span class="text-[10px] text-slate-400 font-medium">미갱신</span>
          </div>
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-xs font-bold text-slate-700">{{ a.name }}</span>
            <span class="text-[10px] text-slate-400">{{ a.total }}지점</span>
          </div>
          <!-- 노출률 게이지 + % -->
          <div class="flex items-center gap-2 mb-1.5">
            <div class="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <div class="h-full rounded-full transition-all"
                :class="a.total > 0 && (a.success / a.total) <= 0.5 ? 'bg-red-400' : 'bg-blue-400'"
                :style="{ width: pct(a.success, a.total) + '%' }"></div>
            </div>
            <span class="text-[11px] font-semibold shrink-0"
              :class="a.total > 0 && (a.success / a.total) <= 0.5 ? 'text-red-500' : 'text-blue-500'">{{ pct(a.success, a.total) }}%</span>
          </div>
          <!-- 한 줄 요약 -->
          <div class="flex items-center gap-1 text-[11px] whitespace-nowrap overflow-hidden">
            <span class="text-blue-600 font-medium shrink-0">노출 {{ a.success }}</span><span class="text-slate-300">·</span>
            <span class="text-red-500 font-medium shrink-0">미노출 {{ a.fail }}</span><span class="text-slate-300">·</span>
            <span class="shrink-0" :class="a.midal > 0 ? 'text-red-400' : 'text-slate-400'">미점유 {{ a.midal }}</span>
            <span class="ml-auto text-slate-400 shrink-0">평균 {{ a.avgNosul }}일</span>
          </div>
        </div>
      </div>

      <!-- ─── ROW 4: 메인 테이블 + 사이드 막대그래프 ─── -->
      <div class="flex flex-col lg:flex-row gap-3 px-5 pb-3 flex-1 min-h-0">

        <!-- 테이블 -->
        <div class="flex flex-col min-h-0 flex-1 lg:flex-[3_1_0%]" style="min-width: 0">
          <div class="bg-white border border-slate-200 rounded-lg overflow-hidden flex-1 min-h-0">
            <div class="h-full overflow-y-auto overflow-x-hidden">
              <table class="w-full text-xs">
                <thead>
                  <tr class="bg-slate-50/95 border-b border-slate-200">
                    <th @click="toggleSort('branch')"    class="th-cell text-left pl-3 pr-2 w-[80px] min-w-[120px]">지점 <span class="sort-icon">{{ sortIcon('branch') }}</span></th>
                    <th @click="toggleSort('keyword')"    class="th-cell text-left px-2 w-[100px]">키워드 <span class="sort-icon">{{ sortIcon('keyword') }}</span></th>
                    <th @click="toggleSort('today_exposed')" title="오늘 노출 성공 여부 (O/X)" class="th-cell text-center w-[44px]">오늘 <span class="sort-icon">{{ sortIcon('today_exposed') }}</span></th>
                    <th title="최근 5일간 일별 노출 여부" class="th-cell text-center w-[100px]">최근 5일</th>
                    <th @click="toggleSort('streak')"     title="끊김 없이 연속 노출된 일수" class="th-cell text-center w-[42px]">연속 <span class="sort-icon">{{ sortIcon('streak') }}</span></th>
                    <th @click="toggleSort('nosul_count')" title="시트 AF열 기준 당월 노출일수" class="th-cell text-center w-[36px]">노출일수 <span class="sort-icon">{{ sortIcon('nosul_count') }}</span></th>
                    <th @click="toggleSort('total_exposed')" title="전체 이력 중 노출 성공한 총 일수" class="th-cell text-center w-[36px]">총노출 <span class="sort-icon">{{ sortIcon('total_exposed') }}</span></th>
                    <th @click="toggleSort('work_days')"   title="작업 시작일부터 현재까지 총 진행일수" class="th-cell text-center w-[36px]">총진행일 <span class="sort-icon">{{ sortIcon('work_days') }}</span></th>
                    <th @click="toggleSort('status')"      title="노출: 오늘 노출됨 / 미노출: 오늘 미노출 / 미점유: 데이터 없음" class="th-cell text-center w-[44px]">상태 <span class="sort-icon">{{ sortIcon('status') }}</span></th>
                    <th v-if="canSeeAgency && agencyStats.length > 0" @click="toggleSort('agency')" title="해당 지점 담당 실행사" class="th-cell text-center pr-3 w-[64px]">실행사 <span class="sort-icon">{{ sortIcon('agency') }}</span></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="filteredBranches.length === 0">
                    <td :colspan="canSeeAgency && agencyStats.length > 0 ? 10 : 9" class="px-3 py-6 text-center text-slate-400">검색 결과가 없습니다</td>
                  </tr>
                  <template v-for="b in filteredBranches" :key="b.branch">
                  <tr @click="isEditor && toggleBranch(b)"
                    :class="['border-b border-slate-100 transition-colors',
                      isEditor ? 'cursor-pointer' : '',
                      getRecoveryInfo(b).show
                        ? (expandedBranch === b.branch ? 'bg-emerald-100/60' : 'bg-emerald-50/60 hover:bg-emerald-100/60')
                        : (expandedBranch === b.branch ? 'bg-blue-50/50' : 'hover:bg-blue-50/30')]">
                    <td class="pl-3 pr-2 py-[5px] text-slate-800 font-medium whitespace-nowrap min-w-[120px]">
                      <span v-if="isEditor" class="text-[10px] text-slate-300 mr-1">{{ expandedBranch === b.branch ? '▼' : '▶' }}</span>
                      {{ shortName(b) }}
                      <span v-if="getRecoveryInfo(b).show" class="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 ml-1 align-middle" :title="getRecoveryInfo(b).label"></span>
                    </td>
                    <td class="px-2 py-[5px] text-slate-500 whitespace-nowrap">{{ b.keyword }}</td>
                    <td class="py-[5px] text-center whitespace-nowrap">
                      <span v-if="b.status === '미달'" class="text-slate-300">-</span>
                      <span v-else :class="b.today_exposed ? 'text-blue-600 font-semibold' : 'text-red-400'"
                      >{{ b.today_exposed ? 'O' : 'X' }}</span>
                    </td>
                    <td class="py-[5px] text-center whitespace-nowrap">
                      <span class="inline-flex gap-0.5">
                        <span v-for="(r, i) in recentDays(b)" :key="i"
                          class="text-[11px] font-medium"
                          :class="r.exposed === 1 ? 'text-blue-600' : r.mark === '' ? 'text-slate-200' : 'text-red-400'"
                        >{{ r.exposed === 1 ? 'O' : r.mark === '' ? '-' : 'X' }}<span v-if="i < recentDays(b).length - 1" class="text-slate-200 mx-px">·</span></span>
                      </span>
                    </td>
                    <td class="py-[5px] text-center text-slate-500 tabular-nums">{{ b.streak > 0 ? b.streak + '일' : '-' }}</td>
                    <td class="py-[5px] text-center font-semibold tabular-nums"
                      :class="b.nosul_count >= 23 ? 'text-red-500' : b.nosul_count >= 15 ? 'text-amber-500' : 'text-blue-600'">
                      {{ b.nosul_count }}
                    </td>
                    <td class="py-[5px] text-center text-blue-600 font-medium tabular-nums">{{ b.total_exposed || 0 }}</td>
                    <td class="py-[5px] text-center text-slate-400 tabular-nums">{{ b.work_days > 0 ? b.work_days + '일' : '-' }}</td>
                    <td class="py-[5px] text-center">
                      <span class="inline-block px-1.5 py-0.5 rounded text-[10px] font-semibold" :class="statusBadge(b.status).cls">
                        {{ statusBadge(b.status).text }}
                      </span>
                    </td>
                    <td v-if="canSeeAgency && agencyStats.length > 0" class="pr-3 py-[5px] text-center text-[11px] text-slate-400 whitespace-nowrap">{{ getAgency(b.branch) }}</td>
                  </tr>
                  <!-- 상세 분석 패널 -->
                  <tr v-if="expandedBranch === b.branch && isEditor" class="bg-slate-50/80">
                    <td :colspan="canSeeAgency && agencyStats.length > 0 ? 10 : 9" class="px-6 py-3">
                      <div v-if="detailLoading" class="text-xs text-slate-400">불러오는 중...</div>
                      <div v-else-if="detailError" class="text-xs text-red-500">{{ detailError }}</div>
                      <template v-else-if="detailData && detailData.success_rate.all.total > 0">
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3 text-xs max-w-3xl">

                          <!-- 왼쪽 열: 성공률 + 연속 -->
                          <div class="grid grid-cols-[auto_auto_auto_auto] gap-x-3 gap-y-0.5">

                            <!-- ── 성공률 섹션 ── -->
                            <!-- 전체 -->
                            <span class="text-[11px] font-semibold text-slate-500 uppercase tracking-wide self-center py-0.5 min-w-[48px]">성공률</span>
                            <span class="text-xs text-slate-500 self-center py-0.5">전체</span>
                            <span class="text-xs font-medium text-slate-900 self-center py-0.5 tabular-nums">
                              {{ detailData.success_rate.all.success }}/{{ detailData.success_rate.all.total }}일
                            </span>
                            <span class="text-[11px] text-slate-400 self-center py-0.5 tabular-nums">({{ detailData.success_rate.all.pct }}%)</span>
                            <!-- 이번 달 -->
                            <span class="py-0.5"></span>
                            <span class="text-xs text-slate-500 self-center py-0.5">이번 달</span>
                            <span class="text-xs font-medium text-slate-900 self-center py-0.5 tabular-nums">
                              <template v-if="detailData.success_rate.this_month.total > 0">{{ detailData.success_rate.this_month.success }}/{{ detailData.success_rate.this_month.total }}일</template>
                              <span v-else class="text-slate-300">-</span>
                            </span>
                            <span class="text-[11px] text-slate-400 self-center py-0.5 tabular-nums">
                              <template v-if="detailData.success_rate.this_month.total > 0">({{ detailData.success_rate.this_month.pct }}%)</template>
                            </span>
                            <!-- 지난 달 -->
                            <span class="py-0.5"></span>
                            <span class="text-xs text-slate-500 self-center py-0.5">지난 달</span>
                            <span class="text-xs font-medium text-slate-900 self-center py-0.5 tabular-nums">
                              <template v-if="detailData.success_rate.last_month.total > 0">{{ detailData.success_rate.last_month.success }}/{{ detailData.success_rate.last_month.total }}일</template>
                              <span v-else class="text-slate-300">-</span>
                            </span>
                            <span class="text-[11px] text-slate-400 self-center py-0.5 tabular-nums">
                              <template v-if="detailData.success_rate.last_month.total > 0">({{ detailData.success_rate.last_month.pct }}%)</template>
                            </span>

                            <!-- ── 연속 섹션 구분선 ── -->
                            <div class="col-span-4 border-t border-slate-100 my-0.5"></div>

                            <!-- 현재 연속 -->
                            <span class="text-[11px] font-semibold text-slate-500 uppercase tracking-wide self-center py-0.5 min-w-[48px]">연속</span>
                            <span class="text-xs text-slate-500 self-center py-0.5">현재 연속</span>
                            <span class="text-xs font-medium text-slate-900 self-center py-0.5 tabular-nums">
                              <template v-if="detailData.current_success && detailData.current_success.days > 0">{{ detailData.current_success.days }}일</template>
                              <span v-else class="text-slate-300">-</span>
                            </span>
                            <span class="text-[11px] text-slate-400 self-center py-0.5 tabular-nums">
                              <template v-if="detailData.current_success && detailData.current_success.days > 0">
                                {{ fmtDate(detailData.current_success.from) }} ~ 진행중
                              </template>
                            </span>
                            <!-- 최장 노출 -->
                            <span class="text-[11px] font-semibold text-slate-500 uppercase tracking-wide self-center py-0.5 min-w-[48px]"></span>
                            <span class="text-xs text-slate-500 self-center py-0.5">최장 노출</span>
                            <span class="text-xs font-medium text-slate-900 self-center py-0.5 tabular-nums">
                              <template v-if="detailData.longest.success.days > 0">{{ detailData.longest.success.days }}일</template>
                              <span v-else class="text-slate-300">-</span>
                            </span>
                            <span class="text-[11px] text-slate-400 self-center py-0.5 tabular-nums">
                              <template v-if="detailData.longest.success.days > 0">
                                {{ fmtDate(detailData.longest.success.from) }} ~
                                <template v-if="detailData.longest.success.to">{{ fmtDate(detailData.longest.success.to) }}</template>
                                <template v-else>진행중</template>
                              </template>
                            </span>
                            <!-- 최장 미노출 -->
                            <span class="py-0.5"></span>
                            <span class="text-xs text-slate-500 self-center py-0.5">최장 미노출</span>
                            <span class="text-xs font-medium text-slate-900 self-center py-0.5 tabular-nums">
                              <template v-if="detailData.longest.fail.days > 0">{{ detailData.longest.fail.days }}일</template>
                              <span v-else class="text-slate-300">-</span>
                            </span>
                            <span class="text-[11px] text-slate-400 self-center py-0.5 tabular-nums">
                              <template v-if="detailData.longest.fail.days > 0">
                                {{ fmtDate(detailData.longest.fail.from) }} ~
                                <template v-if="detailData.longest.fail.to">{{ fmtDate(detailData.longest.fail.to) }}</template>
                                <template v-else>진행중</template>
                              </template>
                            </span>

                          </div>

                          <!-- 오른쪽 열: 회복 (0건이면 미렌더) -->
                          <div v-if="detailData.recovery_history.length > 0"
                            class="grid grid-cols-[auto_auto_auto_auto] gap-x-3 gap-y-0.5">
                            <template v-for="(ev, idx) in detailData.recovery_history.slice(0, 10)" :key="ev.recovery_date">
                              <span class="text-[11px] font-semibold text-slate-500 uppercase tracking-wide self-center py-0.5 min-w-[48px]">{{ idx === 0 ? '회복' : '' }}</span>
                              <span class="text-xs text-slate-500 self-center py-0.5 tabular-nums">{{ fmtDate(ev.recovery_date) }}</span>
                              <span class="text-xs font-medium text-slate-900 self-center py-0.5 col-span-2">
                                <span v-if="ev.is_first_success" class="text-slate-400">첫 성공</span>
                                <span v-else class="tabular-nums">{{ ev.gap_days }}일 만에</span>
                              </span>
                            </template>
                          </div>

                        </div>
                      </template>
                      <div v-else-if="detailData" class="text-xs text-slate-300">이력 없음</div>
                    </td>
                  </tr>
                  </template>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- 노출일수 막대그래프 -->
        <div class="flex flex-col min-h-0 flex-1 lg:flex-[2_1_0%]" style="min-width: 0">
          <div class="bg-white border border-slate-200 rounded-lg p-3 flex-1 min-h-0 flex flex-col overflow-hidden">
            <div class="flex items-center justify-between mb-2 shrink-0">
              <h3 class="text-xs font-bold text-slate-600">노출일수 현황</h3>
              <div class="flex items-center gap-2 text-[10px] text-slate-400">
                <span class="flex items-center gap-1"><span class="inline-block w-2 h-2 rounded-sm bg-red-400"></span>23+</span>
                <span class="flex items-center gap-1"><span class="inline-block w-2 h-2 rounded-sm bg-amber-400"></span>15+</span>
                <span class="flex items-center gap-1"><span class="inline-block w-2 h-2 rounded-sm bg-blue-400"></span>1+</span>
              </div>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto space-y-[3px]">
              <div v-for="b in sortedByNosul" :key="b.branch" class="flex items-center gap-1.5">
                <span class="w-16 text-[11px] text-right text-slate-500 truncate shrink-0">{{ shortName(b) }}</span>
                <div class="flex-1 h-[14px] bg-slate-100 rounded-sm overflow-hidden">
                  <div class="h-full rounded-sm transition-all duration-300" :class="barColor(b.nosul_count)"
                    :style="{ width: barWidth(b.nosul_count) + '%' }"></div>
                </div>
                <span class="w-6 text-[11px] text-right font-semibold tabular-nums shrink-0"
                  :class="b.nosul_count >= 23 ? 'text-red-500' : 'text-slate-600'">{{ b.nosul_count }}</span>
              </div>
            </div>
            <div v-if="midalBranches.length > 0" class="mt-2 pt-2 border-t border-slate-100 shrink-0">
              <div class="flex items-center gap-1.5">
                <span class="text-[11px] text-slate-400">미점유:</span>
                <span v-for="b in midalBranches" :key="b.branch"
                  class="text-[11px] text-slate-400 bg-slate-50 px-1.5 py-0.5 rounded">{{ shortName(b) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.th-cell {
  position: sticky;
  top: 0;
  z-index: 10;
  background-color: rgb(248 250 252);
  padding-top: 8px;
  padding-bottom: 8px;
  font-size: 11px;
  font-weight: 600;
  color: rgb(100 116 139);
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}
.th-cell:hover {
  color: rgb(51 65 85);
}
.sort-icon {
  color: rgb(203 213 225);
  margin-left: 2px;
  font-size: 10px;
}
</style>
