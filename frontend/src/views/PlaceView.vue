<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { getPlaceRankingDaily, syncPlaceToDB, getPlaceLastSync } from '@/api/place'
import { getComparison } from '@/api/rankChecker'
import { fetchAgencyMap } from '@/api/branches'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

const auth = useAuthStore()
const isBranch = computed(() => auth.role === 'branch')

interface DailyData {
  day: number
  success: number | null
  rank: number | null
}

interface BranchRanking {
  branch: string
  branch_id: number
  keyword: string
  nosul_count: number
  today_rank: number | null
  today_success: boolean
  streak: number
  status: 'active' | 'fail' | '미달' | 'stopped'
  work_days: number
  daily: DailyData[]
}

interface PlaceData {
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
const data = ref<PlaceData | null>(null)
const syncing = ref(false)
const lastSync = ref<string | null>(null)

// 날짜 선택 (기본: 오늘)
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
const isEditor = computed(() => ['admin', 'editor'].includes(auth.role))

// ── SB체커 토글 ──
const expandedBranch = ref<string | null>(null)
const comparisonData = ref<any>(null)
const comparisonLoading = ref(false)

async function toggleBranch(b: BranchRanking) {
  if (!isEditor.value) return
  if (expandedBranch.value === b.branch) {
    expandedBranch.value = null
    comparisonData.value = null
    return
  }
  expandedBranch.value = b.branch
  comparisonLoading.value = true
  comparisonData.value = null
  try {
    const { data: res } = await getComparison(b.branch_id)
    comparisonData.value = res
  } catch {
    comparisonData.value = { comparisons: [], mismatch_count: 0 }
  } finally {
    comparisonLoading.value = false
  }
}

// 검색 + 정렬
const searchQuery = ref('')
type SortKey = 'branch' | 'keyword' | 'today_rank' | 'streak' | 'nosul_count' | 'work_days' | 'status' | 'agency'
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
      shortName(b.branch).toLowerCase().includes(q)
    )
  }

  const dir = sortAsc.value ? 1 : -1
  list.sort((a, b) => {
    let av: any, bv: any
    switch (sortKey.value) {
      case 'branch': av = shortName(a.branch); bv = shortName(b.branch); break
      case 'keyword': av = a.keyword; bv = b.keyword; break
      case 'today_rank': av = a.today_rank ?? 999; bv = b.today_rank ?? 999; break
      case 'streak': av = a.streak; bv = b.streak; break
      case 'nosul_count': av = a.nosul_count; bv = b.nosul_count; break
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
  return data.value.branches.every((b: BranchRanking) => b.status === 'fail')
})

// 실행사별 성과 집계
interface AgencyStat {
  name: string
  total: number
  success: number
  fail: number
  midal: number
  avgNosul: number
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
    return { name, total, success, fail, midal, avgNosul: total > 0 ? Math.round(sumNosul / total) : 0 }
  })
})

function pct(count: number, total: number): string {
  if (total === 0) return '0'
  return Math.round((count / total) * 100).toString()
}

function recentRanks(b: BranchRanking): { day: number; rank: number | null }[] {
  return b.daily || []
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

function rankClass(rank: number | null): string {
  if (rank === null) return 'text-slate-300'
  if (rank <= 5) return 'text-emerald-600 font-semibold'
  return 'text-red-500 font-semibold'
}

function statusBadge(status: string): { text: string; cls: string } {
  switch (status) {
    case 'active': return { text: '성공', cls: 'bg-blue-100 text-blue-700' }
    case 'fail': return { text: '실패', cls: 'bg-red-100 text-red-600' }
    case '미달': return { text: '미달', cls: 'bg-slate-100 text-slate-500' }
    default: return { text: status, cls: 'bg-yellow-100 text-yellow-700' }
  }
}

function shortName(branch: string): string {
  return branch.replace('유앤아이', '').replace('유앤', '')
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const { data: res } = await getPlaceRankingDaily(selectedDate.value)
    data.value = res
  } catch (e: any) {
    error.value = e.response?.data?.detail || '데이터를 불러올 수 없습니다'
    data.value = null
  } finally {
    loading.value = false
  }
}

async function handleSync() {
  if (!confirm('구글시트 데이터를 DB에 동기화합니다. 시간이 걸릴 수 있습니다.')) return
  syncing.value = true
  error.value = ''
  try {
    const { data: res } = await syncPlaceToDB()
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

async function loadLastSync() {
  try {
    const { data: res } = await getPlaceLastSync()
    lastSync.value = res.synced_at || null
  } catch { /* ignore */ }
}

watch(selectedDate, () => loadData())

onMounted(async () => {
  loadData()
  loadLastSync()
  try {
    const data = await fetchAgencyMap('place')
    agencyMap.value = data
  } catch {}
})
</script>

<template>
  <div class="place-page flex flex-col overflow-hidden" style="height: calc(100vh - 48px)">

    <!-- ─── ROW 1: 타이틀 + 년/월 + 동기화 + 오늘 요약 숫자 ─── -->
    <div class="flex flex-wrap items-center gap-x-4 gap-y-1 px-5 pt-3 pb-2 shrink-0">
      <h2 class="text-lg font-bold text-slate-800 shrink-0">상위노출</h2>

      <!-- 날짜 선택 -->
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

      <!-- 동기화 버튼 (admin) + 마지막 동기화 -->
      <button v-if="isAdmin" @click="handleSync" :disabled="syncing"
        class="text-xs px-3 py-1 rounded border border-slate-300 hover:bg-slate-50 disabled:opacity-50 shrink-0">
        {{ syncing ? '동기화 중...' : '시트 → DB 동기화' }}
      </button>
      <span v-if="lastSync" class="text-[10px] text-slate-400 shrink-0">최종 동기화: {{ lastSync }}</span>
      <!-- 성공/실패/미달 큰 숫자 -->
      <template v-if="data">
        <div class="flex items-center gap-2 shrink-0">
          <div class="flex items-baseline gap-1 px-2 py-1 bg-blue-50 rounded-lg whitespace-nowrap">
            <span class="text-2xl font-bold text-blue-600">{{ data.summary.success_today }}</span>
            <span class="text-xs text-blue-400">성공 ({{ pct(data.summary.success_today, data.summary.total) }}%)</span>
          </div>
          <div class="flex items-baseline gap-1 px-2 py-1 bg-red-50 rounded-lg whitespace-nowrap">
            <span class="text-2xl font-bold text-red-500">{{ data.summary.fail_today }}</span>
            <span class="text-xs text-red-400">실패 ({{ pct(data.summary.fail_today, data.summary.total) }}%)</span>
          </div>
          <div class="flex items-baseline gap-1 px-2 py-1 bg-slate-100 rounded-lg whitespace-nowrap">
            <span class="text-2xl font-bold text-slate-500">{{ data.summary.midal }}</span>
            <span class="text-xs text-slate-400">미달 ({{ pct(data.summary.midal, data.summary.total) }}%)</span>
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
      <LoadingSpinner message="데이터를 불러오는 중..." />
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
      <!-- ─── ROW 2: 실패 · 미달 태그 ─── -->
      <div class="px-5 pb-1.5 shrink-0">
        <div class="bg-white border border-slate-200 rounded-lg px-3 py-2">
          <div class="flex flex-wrap items-center gap-1">
            <span class="text-[11px] text-slate-400 mr-1 shrink-0">실패</span>
            <span v-for="b in failedBranches" :key="b.branch"
              class="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-red-50 border border-red-100 rounded text-[11px] text-red-600">
              {{ shortName(b.branch) }}<span class="text-red-400 text-[10px]">{{ b.today_rank ? b.today_rank + '위' : '-' }}</span>
            </span>
            <template v-if="midalBranches.length > 0">
              <span class="text-slate-300 mx-1">|</span>
              <span class="text-[11px] text-slate-400 mr-1 shrink-0">미달</span>
              <span v-for="b in midalBranches" :key="b.branch"
                class="px-1.5 py-0.5 bg-slate-50 border border-slate-200 rounded text-[11px] text-slate-500">
                {{ shortName(b.branch) }}
              </span>
            </template>
          </div>
        </div>
      </div>

      <!-- ─── ROW 3: 실행사 카드 ─── -->
      <div v-if="!isBranch && agencyStats.length > 0" class="grid gap-2 px-5 pb-1.5 shrink-0"
        :style="{ gridTemplateColumns: `repeat(${Math.min(agencyStats.length, 4)}, 1fr)` }">
        <div v-for="a in agencyStats" :key="a.name"
          class="bg-white border border-slate-200 rounded-lg px-3 py-2">
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-xs font-bold text-slate-700">{{ a.name }}</span>
            <span class="text-[10px] text-slate-400">{{ a.total }}지점</span>
          </div>
          <!-- 성공률 게이지 + % -->
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
            <span class="text-blue-600 font-medium shrink-0">성공 {{ a.success }}</span><span class="text-slate-300">·</span>
            <span class="text-red-500 font-medium shrink-0">실패 {{ a.fail }}</span><span class="text-slate-300">·</span>
            <span class="shrink-0" :class="a.midal > 0 ? 'text-red-400' : 'text-slate-400'">미달 {{ a.midal }}</span>
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
                    <th @click="toggleSort('branch')"   class="th-cell text-left pl-3 pr-2 w-[70px]">지점 <span class="sort-icon">{{ sortIcon('branch') }}</span></th>
                    <th @click="toggleSort('keyword')"   class="th-cell text-left px-2 w-[100px]">키워드 <span class="sort-icon">{{ sortIcon('keyword') }}</span></th>
                    <th @click="toggleSort('today_rank')" class="th-cell text-center w-[44px]">오늘 <span class="sort-icon">{{ sortIcon('today_rank') }}</span></th>
                    <th class="th-cell text-center w-[100px]">최근 5일</th>
                    <th @click="toggleSort('streak')"     class="th-cell text-center w-[42px]">연속 <span class="sort-icon">{{ sortIcon('streak') }}</span></th>
                    <th @click="toggleSort('nosul_count')" class="th-cell text-center w-[36px]">총노출 <span class="sort-icon">{{ sortIcon('nosul_count') }}</span></th>
                    <th @click="toggleSort('work_days')"   class="th-cell text-center w-[36px]">진행 <span class="sort-icon">{{ sortIcon('work_days') }}</span></th>
                    <th @click="toggleSort('status')"      class="th-cell text-center w-[44px]">상태 <span class="sort-icon">{{ sortIcon('status') }}</span></th>
                    <th v-if="!isBranch" @click="toggleSort('agency')" class="th-cell text-center pr-3 w-[64px]">실행사 <span class="sort-icon">{{ sortIcon('agency') }}</span></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="filteredBranches.length === 0">
                    <td :colspan="isBranch ? 8 : 9" class="px-3 py-6 text-center text-slate-400">검색 결과가 없습니다</td>
                  </tr>
                  <template v-for="b in filteredBranches" :key="b.branch">
                    <tr @click="isEditor && toggleBranch(b)"
                      :class="['border-b border-slate-100 hover:bg-blue-50/30 transition-colors',
                        isEditor ? 'cursor-pointer' : '',
                        expandedBranch === b.branch ? 'bg-blue-50/50' : '']">
                      <td class="pl-3 pr-2 py-[5px] text-slate-800 font-medium whitespace-nowrap">
                        <span v-if="isEditor" class="text-[10px] text-slate-300 mr-1">{{ expandedBranch === b.branch ? '▼' : '▶' }}</span>{{ shortName(b.branch) }}
                      </td>
                      <td class="px-2 py-[5px] text-slate-500 whitespace-nowrap">{{ b.keyword }}</td>
                      <td class="py-[5px] text-center whitespace-nowrap" :class="rankClass(b.today_rank)">
                        {{ b.today_rank ? b.today_rank + '위' : '-' }}
                      </td>
                      <td class="py-[5px] text-center whitespace-nowrap">
                        <span class="inline-flex gap-0.5">
                          <span v-for="(r, i) in recentRanks(b)" :key="i"
                            class="text-[11px] font-medium tabular-nums"
                            :class="r.rank === null ? 'text-slate-300' : r.rank <= 5 ? 'text-emerald-600' : 'text-red-500'"
                          >{{ r.rank ?? '-' }}<span v-if="i < recentRanks(b).length - 1" class="text-slate-200 mx-px">·</span></span>
                        </span>
                      </td>
                      <td class="py-[5px] text-center text-slate-500 tabular-nums">{{ b.streak > 0 ? b.streak + '일' : '-' }}</td>
                      <td class="py-[5px] text-center font-semibold tabular-nums"
                        :class="b.nosul_count >= 23 ? 'text-red-500' : b.nosul_count >= 15 ? 'text-amber-500' : 'text-blue-600'">
                        {{ b.nosul_count }}
                      </td>
                      <td class="py-[5px] text-center text-slate-400 tabular-nums">{{ b.work_days > 0 ? b.work_days + '일' : '-' }}</td>
                      <td class="py-[5px] text-center">
                        <span class="inline-block px-1.5 py-0.5 rounded text-[10px] font-semibold" :class="statusBadge(b.status).cls">
                          {{ statusBadge(b.status).text }}
                        </span>
                      </td>
                      <td v-if="!isBranch" class="pr-3 py-[5px] text-center text-[11px] text-slate-400 whitespace-nowrap">{{ getAgency(b.branch) }}</td>
                    </tr>
                    <!-- SB체커 비교 하위 행 -->
                    <tr v-if="expandedBranch === b.branch && isEditor" class="bg-amber-50/50">
                      <td :colspan="isBranch ? 8 : 9" class="px-3 py-2">
                        <div v-if="comparisonLoading" class="text-xs text-slate-400 py-2 text-center">비교 데이터 로딩 중...</div>
                        <div v-else-if="comparisonData && comparisonData.comparisons.length > 0">
                          <div class="flex items-center gap-2 mb-1.5">
                            <span class="text-[10px] font-bold text-amber-700">SB체커 비교</span>
                            <span class="text-[10px] text-slate-400">{{ comparisonData.date }}</span>
                            <span v-if="comparisonData.mismatch_count > 0"
                              class="text-[10px] px-1.5 py-0.5 bg-red-100 text-red-600 rounded font-medium">
                              불일치 {{ comparisonData.mismatch_count }}건
                            </span>
                          </div>
                          <table class="w-full text-[11px]">
                            <thead>
                              <tr class="text-slate-400">
                                <th class="text-left px-2 py-1 font-medium">키워드</th>
                                <th class="text-center px-2 py-1 font-medium">SB순위</th>
                                <th class="text-center px-2 py-1 font-medium">SB노출</th>
                                <th class="text-center px-2 py-1 font-medium">실행사순위</th>
                                <th class="text-center px-2 py-1 font-medium">실행사노출</th>
                                <th class="text-center px-2 py-1 font-medium">일치</th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr v-for="c in comparisonData.comparisons.filter((c: any) => !expandedBranch || filteredBranches.some((fb: any) => fb.branch === expandedBranch && fb.keyword === c.keyword))" :key="c.keyword"
                                :class="c.mismatch ? 'bg-red-50/80' : ''">
                                <td class="px-2 py-1 text-slate-700 font-medium">{{ c.keyword }}</td>
                                <td class="px-2 py-1 text-center" :class="c.checker?.rank && c.checker.rank <= (c.checker.guaranteed_rank || 5) ? 'text-emerald-600 font-semibold' : 'text-red-500'">
                                  {{ c.checker?.rank ? c.checker.rank + '위' : '-' }}
                                </td>
                                <td class="px-2 py-1 text-center" :class="c.checker?.is_exposed ? 'text-emerald-600' : 'text-red-400'">
                                  {{ c.checker ? (c.checker.is_exposed ? 'O' : 'X') : '-' }}
                                </td>
                                <td class="px-2 py-1 text-center" :class="c.agency?.rank && c.agency.rank <= 5 ? 'text-emerald-600 font-semibold' : c.agency?.rank ? 'text-red-500' : 'text-slate-300'">
                                  {{ c.agency?.rank ? c.agency.rank + '위' : '-' }}
                                </td>
                                <td class="px-2 py-1 text-center" :class="c.agency?.is_exposed ? 'text-emerald-600' : 'text-red-400'">
                                  {{ c.agency ? (c.agency.is_exposed ? 'O' : 'X') : '-' }}
                                </td>
                                <td class="px-2 py-1 text-center font-medium"
                                  :class="c.mismatch ? 'text-red-600' : !c.checker || !c.agency ? 'text-slate-300' : 'text-emerald-600'">
                                  {{ c.mismatch ? '불일치' : !c.checker ? '(신규)' : !c.agency ? '(없음)' : '일치' }}
                                </td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                        <div v-else class="text-xs text-slate-400 py-2 text-center">비교 데이터가 없습니다 (키워드 미등록 또는 체크 미실행)</div>
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
                <span class="w-16 text-[11px] text-right text-slate-500 truncate shrink-0">{{ shortName(b.branch) }}</span>
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
                <span class="text-[11px] text-slate-400">미달:</span>
                <span v-for="b in midalBranches" :key="b.branch"
                  class="text-[11px] text-slate-400 bg-slate-50 px-1.5 py-0.5 rounded">{{ shortName(b.branch) }}</span>
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
  background-color: rgb(248 250 252); /* slate-50 */
  padding-top: 8px;
  padding-bottom: 8px;
  font-size: 11px;
  font-weight: 600;
  color: rgb(100 116 139); /* slate-500 */
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}
.th-cell:hover {
  color: rgb(51 65 85); /* slate-700 */
}
.sort-icon {
  color: rgb(203 213 225); /* slate-300 */
  margin-left: 2px;
  font-size: 10px;
}
</style>
