<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useAgencyVisibility } from '@/composables/useAgencyVisibility'
import { getWebpageRankingDaily, syncWebpageToDB, getWebpageLastSync } from '@/api/webpage'
import { fetchAgencyMap } from '@/api/branches'

const auth = useAuthStore()
const isBranch = computed(() => auth.role === 'branch')
const { canSeeAgency } = useAgencyVisibility()

interface DailyData {
  day: number
  exposed: number
  mark: string  // ㅇ, x, 빈값
}

interface BranchRanking {
  branch: string
  keyword: string
  nosul_count: number
  total_exposed: number
  today_exposed: boolean
  streak: number
  status: 'active' | 'fail' | '미달' | 'stopped'
  work_days: number
  daily: DailyData[]
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
const syncing = ref(false)
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
      shortName(b.branch).toLowerCase().includes(q)
    )
  }

  const dir = sortAsc.value ? 1 : -1
  list.sort((a, b) => {
    let av: any, bv: any
    switch (sortKey.value) {
      case 'branch': av = shortName(a.branch); bv = shortName(b.branch); break
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
  // 성공(노출)이 단 한 건도 없을 때 (미노출 + 미달 전부 포함)
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
    const notUpdated = total > 0 && branches.every(b => !b.today_exposed)
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
    case '미달': return { text: '미측정', cls: 'bg-slate-100 text-slate-400' }
    default: return { text: status, cls: 'bg-yellow-100 text-yellow-700' }
  }
}

function shortName(branch: string): string {
  return branch.replace('유앤아이의원 ', '').replace('유앤아이의원', '').replace('유앤아이 ', '').replace('점', '')
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

async function handleSync() {
  if (!confirm('구글시트 데이터를 DB에 동기화합니다. 시간이 걸릴 수 있습니다.')) return
  syncing.value = true
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

      <button v-if="isAdmin" @click="handleSync" :disabled="syncing"
        class="text-xs px-3 py-1 rounded border border-slate-300 hover:bg-slate-50 disabled:opacity-50 shrink-0">
        {{ syncing ? '동기화 중...' : '시트 → DB 동기화' }}
      </button>
      <span v-if="lastSync" class="text-[10px] text-slate-400 shrink-0">최종 동기화: {{ lastSync }}</span>
      <!-- 노출/미노출/미달 큰 숫자 -->
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
      <!-- ─── ROW 2: 미노출 · 미달 태그 ─── -->
      <div class="px-5 pb-1.5 shrink-0">
        <div class="bg-white border border-slate-200 rounded-lg px-3 py-2">
          <div class="flex flex-wrap items-center gap-1">
            <span class="text-[11px] text-slate-400 mr-1 shrink-0">미노출</span>
            <span v-for="b in failedBranches" :key="b.branch"
              class="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-red-50 border border-red-100 rounded text-[11px] text-red-600">
              {{ shortName(b.branch) }}
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
                    <th @click="toggleSort('branch')"    class="th-cell text-left pl-3 pr-2 w-[80px]">지점 <span class="sort-icon">{{ sortIcon('branch') }}</span></th>
                    <th @click="toggleSort('keyword')"    class="th-cell text-left px-2 w-[100px]">키워드 <span class="sort-icon">{{ sortIcon('keyword') }}</span></th>
                    <th @click="toggleSort('today_exposed')" title="오늘 노출 성공 여부 (O/X)" class="th-cell text-center w-[44px]">오늘 <span class="sort-icon">{{ sortIcon('today_exposed') }}</span></th>
                    <th title="최근 5일간 일별 노출 여부" class="th-cell text-center w-[100px]">최근 5일</th>
                    <th @click="toggleSort('streak')"     title="끊김 없이 연속 노출된 일수" class="th-cell text-center w-[42px]">연속 <span class="sort-icon">{{ sortIcon('streak') }}</span></th>
                    <th @click="toggleSort('nosul_count')" title="시트 AF열 기준 당월 노출일수" class="th-cell text-center w-[36px]">노출일수 <span class="sort-icon">{{ sortIcon('nosul_count') }}</span></th>
                    <th @click="toggleSort('total_exposed')" title="전체 이력 중 노출 성공한 총 일수" class="th-cell text-center w-[36px]">총노출 <span class="sort-icon">{{ sortIcon('total_exposed') }}</span></th>
                    <th @click="toggleSort('work_days')"   title="작업 시작일부터 현재까지 총 진행일수" class="th-cell text-center w-[36px]">총진행일 <span class="sort-icon">{{ sortIcon('work_days') }}</span></th>
                    <th @click="toggleSort('status')"      title="노출: 오늘 노출됨 / 미노출: 오늘 미노출 / 미달: 데이터 없음" class="th-cell text-center w-[44px]">상태 <span class="sort-icon">{{ sortIcon('status') }}</span></th>
                    <th v-if="canSeeAgency && agencyStats.length > 0" @click="toggleSort('agency')" title="해당 지점 담당 실행사" class="th-cell text-center pr-3 w-[64px]">실행사 <span class="sort-icon">{{ sortIcon('agency') }}</span></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="filteredBranches.length === 0">
                    <td :colspan="canSeeAgency && agencyStats.length > 0 ? 10 : 9" class="px-3 py-6 text-center text-slate-400">검색 결과가 없습니다</td>
                  </tr>
                  <tr v-for="b in filteredBranches" :key="b.branch"
                    class="border-b border-slate-100 hover:bg-blue-50/30 transition-colors">
                    <td class="pl-3 pr-2 py-[5px] text-slate-800 font-medium whitespace-nowrap">{{ shortName(b.branch) }}</td>
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
