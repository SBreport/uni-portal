<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { getWebpageMonths, getWebpageRanking } from '@/api/webpage'

const auth = useAuthStore()
const isBranch = computed(() => auth.role === 'branch')

interface DailyData {
  day: number
  exposed: number
  mark: string  // ㅇ, x, 빈값
}

interface BranchRanking {
  branch: string
  keyword: string
  nosul_count: number
  today_exposed: boolean
  streak: number
  status: 'active' | 'fail' | '미달' | 'stopped'
  month_exposed_count: number
  work_days: number
  daily: DailyData[]
}

interface WebpageData {
  year: number
  month: number
  days: number
  today_index: number
  branches: BranchRanking[]
  summary: { total: number; success_today: number; fail_today: number; midal: number }
}

// ── 실행사 매핑 (추후 기입 예정) ──
const AGENCY_MAP: Record<string, string> = {
  '유앤아이의원 천호점': '채움AD', '유앤아이의원 광명점': '채움AD', '유앤아이의원 부천점': '채움AD',
  '유앤아이의원 일산점': '채움AD', '유앤아이의원 다산점': '채움AD', '유앤아이의원 김포점': '채움AD',
  '유앤아이의원 안양점': '채움AD', '유앤아이의원 안산점': '채움AD', '유앤아이의원 천안점': '채움AD',
  '유앤아이의원 광주점': '채움AD', '유앤아이의원 대구점': '채움AD', '유앤아이의원 과천점': '채움AD',
  '유앤아이의원 하남미사점': '채움AD', '유앤아이의원 화성봉담점': '채움AD', '유앤아이의원 동탄점': '채움AD',
  '유앤아이의원 목동점': '채움AD', '유앤아이의원 강남점': '채움AD', '유앤아이의원 영등포점': '채움AD',
  '유앤아이의원 대전점': '채움AD', '유앤아이의원 서면점': '채움AD', '유앤아이의원 광교점': '채움AD',
  '유앤아이의원 수원점': '채움AD', '유앤아이의원 검단점': '채움AD', '유앤아이의원 경기광주점': '채움AD',
  '유앤아이의원 명동점': '채움AD', '유앤아이의원 목포점': '채움AD', '유앤아이의원 잠실점': '채움AD',
  '유앤아이의원 의정부점': '채움AD', '유앤아이의원 창원점': '채움AD', '유앤아이의원 평택점': '채움AD',
  '유앤아이의원 홍대점': '채움AD',
}

function getAgency(branch: string): string {
  return AGENCY_MAP[branch] || '-'
}

const AGENCIES = ['채움AD'] as const

const loading = ref(true)
const error = ref('')
const months = ref<string[]>([])
const monthIndex = ref(0)
const data = ref<WebpageData | null>(null)

const selectedMonth = computed(() => months.value[monthIndex.value] ?? '')
const canPrev = computed(() => monthIndex.value < months.value.length - 1)
const canNext = computed(() => monthIndex.value > 0)

function goPrev() { if (canPrev.value) monthIndex.value++ }
function goNext() { if (canNext.value) monthIndex.value-- }

// 검색 + 정렬
const searchQuery = ref('')
type SortKey = 'branch' | 'keyword' | 'today_exposed' | 'streak' | 'month_exposed_count' | 'work_days' | 'nosul_count' | 'status' | 'agency'
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
      case 'month_exposed_count': av = a.month_exposed_count; bv = b.month_exposed_count; break
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
  if (!data.value || AGENCIES.length === 0) return []
  return AGENCIES.map(name => {
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

function recentDays(b: BranchRanking): { day: number; exposed: number; mark: string }[] {
  if (!data.value) return []
  const ti = data.value.today_index
  const start = Math.max(0, ti - 5)
  return b.daily.slice(start, ti).map(d => ({ day: d.day, exposed: d.exposed, mark: d.mark }))
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
    case '미달': return { text: '미달', cls: 'bg-slate-100 text-slate-500' }
    default: return { text: status, cls: 'bg-yellow-100 text-yellow-700' }
  }
}

function shortName(branch: string): string {
  return branch.replace('유앤아이의원 ', '').replace('유앤아이의원', '').replace('유앤아이 ', '').replace('점', '')
}

async function loadMonths() {
  try {
    const { data: res } = await getWebpageMonths()
    months.value = res
    monthIndex.value = 0
  } catch (e: any) {
    error.value = e.response?.data?.detail || '월 목록을 불러올 수 없습니다'
  }
}

async function loadData() {
  if (!selectedMonth.value) return
  loading.value = true
  error.value = ''
  try {
    const { data: res } = await getWebpageRanking(selectedMonth.value)
    data.value = res
  } catch (e: any) {
    error.value = e.response?.data?.detail || '데이터를 불러올 수 없습니다'
    data.value = null
  } finally {
    loading.value = false
  }
}

watch(selectedMonth, () => loadData())

onMounted(async () => {
  await loadMonths()
  await loadData()
})
</script>

<template>
  <div class="webpage-page flex flex-col overflow-hidden" style="height: calc(100vh - 48px)">

    <!-- ─── ROW 1: 타이틀 + 월 + 오늘 요약 숫자 ─── -->
    <div class="flex items-center gap-4 px-5 pt-3 pb-2 shrink-0">
      <h2 class="text-lg font-bold text-slate-800 shrink-0">웹페이지</h2>
      <!-- 월 네비 -->
      <div class="flex items-center gap-1 shrink-0">
        <button @click="goPrev" :disabled="!canPrev"
          class="w-7 h-7 flex items-center justify-center rounded-md border border-slate-200 text-slate-400 hover:bg-slate-50 disabled:opacity-30 transition text-xs">&lt;</button>
        <span class="px-2 text-sm font-medium text-slate-700 min-w-[100px] text-center">{{ selectedMonth }}</span>
        <button @click="goNext" :disabled="!canNext"
          class="w-7 h-7 flex items-center justify-center rounded-md border border-slate-200 text-slate-400 hover:bg-slate-50 disabled:opacity-30 transition text-xs">&gt;</button>
      </div>
      <!-- 노출/미노출/미달 큰 숫자 -->
      <template v-if="data">
        <div class="flex items-center gap-2 ml-2">
          <div class="flex items-baseline gap-1 px-3 py-1 bg-blue-50 rounded-lg">
            <span class="text-2xl font-bold text-blue-600">{{ data.summary.success_today }}</span>
            <span class="text-xs text-blue-400">노출 ({{ pct(data.summary.success_today, data.summary.total) }}%)</span>
          </div>
          <div class="flex items-baseline gap-1 px-3 py-1 bg-red-50 rounded-lg">
            <span class="text-2xl font-bold text-red-500">{{ data.summary.fail_today }}</span>
            <span class="text-xs text-red-400">미노출 ({{ pct(data.summary.fail_today, data.summary.total) }}%)</span>
          </div>
          <div class="flex items-baseline gap-1 px-3 py-1 bg-slate-100 rounded-lg">
            <span class="text-2xl font-bold text-slate-500">{{ data.summary.midal }}</span>
            <span class="text-xs text-slate-400">미달 ({{ pct(data.summary.midal, data.summary.total) }}%)</span>
          </div>
        </div>
        <!-- 검색 -->
        <div class="shrink-0">
          <input v-model="searchQuery" type="text" placeholder="지점 · 키워드 검색"
            class="w-44 px-2.5 py-1 border border-slate-200 rounded-md text-xs bg-white focus:outline-none focus:ring-1 focus:ring-blue-400 placeholder:text-slate-400" />
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
      <!-- ─── ROW 2: 미노출 지점 태그 + 실행사 카드 ─── -->
      <div class="flex flex-wrap gap-2 px-5 pb-2 shrink-0">
        <!-- 미노출 지점 태그 -->
        <div class="bg-white border border-slate-200 rounded-lg px-3 py-2 min-w-0" :style="agencyStats.length > 0 ? 'flex: 2 1 300px' : 'flex: 1 1 0'">
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
        <!-- 실행사 카드 (매핑 완료 시 표시) -->
        <template v-if="!isBranch && agencyStats.length > 0">
          <div v-for="a in agencyStats" :key="a.name"
            class="bg-white border border-slate-200 rounded-lg px-3 py-2" style="flex: 1 1 140px; min-width: 140px">
            <div class="flex items-baseline justify-between mb-1">
              <span class="text-xs font-bold text-slate-700">{{ a.name }}</span>
              <span class="text-[10px] text-slate-400">{{ a.total }}지점</span>
            </div>
            <div class="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[11px]">
              <span class="text-blue-600 font-medium">노출 {{ a.success }}곳</span>
              <span class="text-blue-400 text-right">({{ pct(a.success, a.total) }}%)</span>
              <span class="text-red-500 font-medium">미노출 {{ a.fail }}곳</span>
              <span class="text-red-300 text-right">({{ pct(a.fail, a.total) }}%)</span>
              <span :class="a.midal > 0 ? 'text-red-500 font-medium' : 'text-slate-400'">미달 {{ a.midal }}</span>
              <span class="text-slate-400 text-right">평균 {{ a.avgNosul }}일</span>
            </div>
          </div>
        </template>
      </div>

      <!-- ─── ROW 3: 메인 테이블 + 사이드 막대그래프 ─── -->
      <div class="flex flex-wrap gap-3 px-5 pb-3 flex-1 min-h-0">

        <!-- 테이블 -->
        <div class="flex flex-col min-h-0" style="flex: 3 1 500px; min-width: 0">
          <div class="bg-white border border-slate-200 rounded-lg overflow-hidden flex-1 min-h-0">
            <div class="h-full overflow-y-auto">
              <table class="w-full text-xs">
                <thead>
                  <tr class="bg-slate-50/95 border-b border-slate-200">
                    <th @click="toggleSort('branch')"    class="th-cell text-left pl-3 pr-2 w-[80px]">지점 <span class="sort-icon">{{ sortIcon('branch') }}</span></th>
                    <th @click="toggleSort('keyword')"    class="th-cell text-left px-2 w-[100px]">키워드 <span class="sort-icon">{{ sortIcon('keyword') }}</span></th>
                    <th @click="toggleSort('today_exposed')" class="th-cell text-center w-[44px]">오늘 <span class="sort-icon">{{ sortIcon('today_exposed') }}</span></th>
                    <th class="th-cell text-center w-[100px]">최근 5일</th>
                    <th @click="toggleSort('streak')"     class="th-cell text-center w-[42px]">연속 <span class="sort-icon">{{ sortIcon('streak') }}</span></th>
                    <th @click="toggleSort('month_exposed_count')" class="th-cell text-center w-[36px]">총노출 <span class="sort-icon">{{ sortIcon('month_exposed_count') }}</span></th>
                    <th @click="toggleSort('work_days')"   class="th-cell text-center w-[36px]">진행 <span class="sort-icon">{{ sortIcon('work_days') }}</span></th>
                    <th @click="toggleSort('nosul_count')" class="th-cell text-center w-[36px]">노출 <span class="sort-icon">{{ sortIcon('nosul_count') }}</span></th>
                    <th @click="toggleSort('status')"      class="th-cell text-center w-[44px]">상태 <span class="sort-icon">{{ sortIcon('status') }}</span></th>
                    <th v-if="!isBranch && AGENCIES.length > 0" @click="toggleSort('agency')" class="th-cell text-center pr-3 w-[64px]">실행사 <span class="sort-icon">{{ sortIcon('agency') }}</span></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="filteredBranches.length === 0">
                    <td :colspan="isBranch || AGENCIES.length === 0 ? 9 : 10" class="px-3 py-6 text-center text-slate-400">검색 결과가 없습니다</td>
                  </tr>
                  <tr v-for="b in filteredBranches" :key="b.branch"
                    class="border-b border-slate-100 hover:bg-blue-50/30 transition-colors">
                    <td class="pl-3 pr-2 py-[5px] text-slate-800 font-medium whitespace-nowrap">{{ shortName(b.branch) }}</td>
                    <td class="px-2 py-[5px] text-slate-500 whitespace-nowrap">{{ b.keyword }}</td>
                    <td class="py-[5px] text-center whitespace-nowrap">
                      <span :class="b.today_exposed ? 'text-blue-600 font-semibold' : 'text-red-400'"
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
                    <td class="py-[5px] text-center text-blue-500 tabular-nums">{{ b.month_exposed_count > 0 ? b.month_exposed_count + '일' : '-' }}</td>
                    <td class="py-[5px] text-center text-slate-400 tabular-nums">{{ b.work_days > 0 ? b.work_days + '일' : '-' }}</td>
                    <td class="py-[5px] text-center font-semibold tabular-nums"
                      :class="b.nosul_count >= 23 ? 'text-red-500' : b.nosul_count >= 15 ? 'text-amber-500' : 'text-slate-600'">
                      {{ b.nosul_count }}
                    </td>
                    <td class="py-[5px] text-center">
                      <span class="inline-block px-1.5 py-0.5 rounded text-[10px] font-semibold" :class="statusBadge(b.status).cls">
                        {{ statusBadge(b.status).text }}
                      </span>
                    </td>
                    <td v-if="!isBranch && AGENCIES.length > 0" class="pr-3 py-[5px] text-center text-[11px] text-slate-400 whitespace-nowrap">{{ getAgency(b.branch) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- 노출일수 막대그래프 -->
        <div class="flex flex-col min-h-0" style="flex: 2 1 240px; min-width: 240px">
          <div class="bg-white border border-slate-200 rounded-lg p-3 flex-1 min-h-0 flex flex-col">
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
