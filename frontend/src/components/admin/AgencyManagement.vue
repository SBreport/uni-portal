<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { fetchAgencyMap, saveAgencyMap, fetchAgencySheets, saveAgencySheets } from '@/api/branches'
import RankChecker from '@/components/admin/RankChecker.vue'
import api from '@/api/client'

const props = defineProps<{ branches: { id: number; name: string }[] }>()

// Sub-tabs
type SubTab = 'dashboard' | 'mapping' | 'place-stats' | 'webpage-stats' | 'rank-checker'
const subTab = ref<SubTab>('dashboard')

// ════════════════════════════════════════════
// 매핑 관리 (from SyncSettings — agency mapping section)
// ════════════════════════════════════════════
const agencyTab = ref<'place' | 'webpage'>('place')

// Agency maps
const agencyMaps = ref<{ place: Record<string, string>; webpage: Record<string, string> }>({ place: {}, webpage: {} })
const currentAgencyMap = computed(() => agencyMaps.value[agencyTab.value])
const savingAgency = ref(false)
const agencySaveMsg = ref('')
const agencySaveError = ref(false)

async function loadAgencyMaps() {
  try {
    const [place, webpage] = await Promise.all([
      fetchAgencyMap('place').catch(() => ({})),
      fetchAgencyMap('webpage').catch(() => ({})),
    ])
    agencyMaps.value.place = { ...place }
    agencyMaps.value.webpage = { ...webpage }
  } catch {}
}

async function saveAgencyMapHandler() {
  savingAgency.value = true
  agencySaveMsg.value = ''
  agencySaveError.value = false
  try {
    await saveAgencyMap(agencyTab.value, currentAgencyMap.value)
    agencySaveMsg.value = '저장 완료'
  } catch (e: any) {
    agencySaveError.value = true
    agencySaveMsg.value = e.response?.data?.detail || '저장 실패'
  } finally {
    savingAgency.value = false
    setTimeout(() => { agencySaveMsg.value = '' }, 3000)
  }
}

// Agency sheets
const agencySheets = ref<{ place: Record<string, string>; webpage: Record<string, string> }>({ place: {}, webpage: {} })
const currentSheets = computed(() => agencySheets.value[agencyTab.value])
const newSheetAgency = ref('')
const newSheetUrl = ref('')
const savingSheetsMsg = ref('')

async function loadAgencySheets() {
  try {
    const [place, webpage] = await Promise.all([
      fetchAgencySheets('place').catch(() => ({})),
      fetchAgencySheets('webpage').catch(() => ({})),
    ])
    agencySheets.value.place = { ...place }
    agencySheets.value.webpage = { ...webpage }
  } catch {}
}

async function saveAgencySheetsHandler() {
  try {
    await saveAgencySheets(agencyTab.value, currentSheets.value)
    savingSheetsMsg.value = '저장 완료'
    setTimeout(() => { savingSheetsMsg.value = '' }, 3000)
  } catch {
    savingSheetsMsg.value = '저장 실패'
  }
}

function addSheetEntry() {
  const name = newSheetAgency.value.trim()
  const url = newSheetUrl.value.trim()
  if (!name || !url) return
  agencySheets.value[agencyTab.value][name] = url
  newSheetAgency.value = ''
  newSheetUrl.value = ''
}

function removeSheetEntry(name: string) {
  delete agencySheets.value[agencyTab.value][name]
}

// Agency names, groups, assign/unassign
const agencyNames = computed(() => {
  const names = new Set<string>()
  for (const map of [agencyMaps.value.place, agencyMaps.value.webpage]) {
    for (const v of Object.values(map)) {
      if (v?.trim()) names.add(v.trim())
    }
  }
  return [...names].sort()
})

const agencyGroups = computed(() => {
  const map = currentAgencyMap.value
  const groups: Record<string, string[]> = {}
  const unassigned: string[] = []
  const allBranches = Object.keys(map).sort()
  for (const branch of allBranches) {
    const agency = map[branch]?.trim()
    if (agency) {
      if (!groups[agency]) groups[agency] = []
      groups[agency].push(branch)
    } else {
      unassigned.push(branch)
    }
  }
  return { groups, unassigned }
})

const newAgencyName = ref('')
function addAgency() {
  newAgencyName.value = ''
}

function assignBranch(branch: string, agency: string) {
  agencyMaps.value[agencyTab.value][branch] = agency
  assigningBranch.value = null
}

function unassignBranch(branch: string) {
  agencyMaps.value[agencyTab.value][branch] = ''
}

function removeAgency(agencyNameToRemove: string) {
  const map = agencyMaps.value[agencyTab.value]
  for (const branch of Object.keys(map)) {
    if (map[branch]?.trim() === agencyNameToRemove) {
      map[branch] = ''
    }
  }
}

const assigningBranch = ref<string | null>(null)
function toggleAssigning(branch: string) {
  assigningBranch.value = assigningBranch.value === branch ? null : branch
}

function handleClickOutside(e: MouseEvent) {
  if (assigningBranch.value && !(e.target as HTMLElement).closest('[data-agency-dropdown]')) {
    assigningBranch.value = null
  }
}

// ════════════════════════════════════════════
// 성과 통계
// ════════════════════════════════════════════
interface AgencyStatDetail {
  agency: string
  branch_count: number
  rate: number
  avg_streak: number
  trend: string
  monthly: Record<string, number>
  branches: {
    branch: string
    total_days: number
    exposed_days: number
    rate: number
    streak: number
    monthly: Record<string, { total: number; exposed: number; rate: number }>
    monthly_agency?: Record<string, string>
  }[]
}

const statsData = ref<{ agencies: AgencyStatDetail[]; period: string } | null>(null)
const statsLoading = ref(false)
const statsMonths = ref(6)
const statsCustom = ref(false)
const statsDateFrom = ref('')
const statsDateTo = ref('')
const statsFilter = ref('')  // agency filter

async function loadStats(type: 'place' | 'webpage') {
  statsLoading.value = true
  try {
    const params: Record<string, any> = { type }
    if (statsCustom.value && statsDateFrom.value && statsDateTo.value) {
      params.date_from = statsDateFrom.value + '-01'
      params.date_to = statsDateTo.value + '-28'
    } else {
      params.months = statsMonths.value
    }
    const { data } = await api.get('/config/agency-stats', { params })
    statsData.value = data
    await loadAgencyHistory(type)
  } catch {
    statsData.value = null
  } finally {
    statsLoading.value = false
  }
}

function selectPreset(months: number) {
  statsCustom.value = false
  statsMonths.value = months
  loadStats(subTab.value === 'place-stats' ? 'place' : 'webpage')
}

function enableCustomRange() {
  statsCustom.value = true
  if (!statsDateFrom.value) {
    const now = new Date()
    const from = new Date(now.getFullYear(), now.getMonth() - 6, 1)
    statsDateFrom.value = `${from.getFullYear()}-${String(from.getMonth()+1).padStart(2,'0')}`
    statsDateTo.value = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}`
  }
}

// 실행사 카드 정렬 + 색상 (플레이스 페이지와 동일)
const AGENCY_ORDER = ['애드드림즈', '일프로', '간달프', '에이치']
const AGENCY_COLORS: Record<string, { bg: string; border: string; text: string; badge: string }> = {
  '애드드림즈': { bg: 'bg-blue-50/40', border: 'border-l-blue-400', text: 'text-blue-600', badge: 'bg-blue-100 text-blue-700' },
  '일프로':     { bg: 'bg-violet-50/40', border: 'border-l-violet-400', text: 'text-violet-600', badge: 'bg-violet-100 text-violet-700' },
  '간달프':     { bg: 'bg-emerald-50/40', border: 'border-l-emerald-400', text: 'text-emerald-600', badge: 'bg-emerald-100 text-emerald-700' },
  '에이치':     { bg: 'bg-amber-50/40', border: 'border-l-amber-400', text: 'text-amber-600', badge: 'bg-amber-100 text-amber-700' },
}
const defaultColor = { bg: 'bg-slate-50/40', border: 'border-l-slate-400', text: 'text-slate-600', badge: 'bg-slate-100 text-slate-700' }
function agencyColor(name: string) { return AGENCY_COLORS[name] || defaultColor }

const filteredAgencies = computed(() => {
  if (!statsData.value) return []
  let list = statsData.value.agencies
  if (statsFilter.value) {
    list = list.filter(a => a.agency === statsFilter.value)
  }
  return [...list].sort((a, b) => {
    const ai = AGENCY_ORDER.indexOf(a.agency)
    const bi = AGENCY_ORDER.indexOf(b.agency)
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi)
  })
})

// All months across all agencies for table headers
const allMonths = computed(() => {
  if (!statsData.value) return []
  const months = new Set<string>()
  for (const a of statsData.value.agencies) {
    for (const m of Object.keys(a.monthly)) months.add(m)
  }
  return [...months].sort()
})

// 테이블 정렬
type StatsSortKey = 'branch' | 'agency' | 'rate' | 'streak' | string  // string = month key
const statsSortKey = ref<StatsSortKey>('agency')
const statsSortDesc = ref(false)

function toggleStatsSort(key: StatsSortKey) {
  if (statsSortKey.value === key) {
    statsSortDesc.value = !statsSortDesc.value
  } else {
    statsSortKey.value = key
    statsSortDesc.value = key !== 'branch' && key !== 'agency'  // 수치는 내림차순 기본
  }
}

function statsSortIcon(key: StatsSortKey): string {
  if (statsSortKey.value !== key) return ''
  return statsSortDesc.value ? '↓' : '↑'
}

// 플랫 지점 리스트 (정렬 가능)
interface FlatBranch {
  branch: string
  agency: string
  rate: number
  streak: number
  total_days: number
  exposed_days: number
  monthly: Record<string, { total: number; exposed: number; rate: number }>
  monthly_agency: Record<string, string>
}

const flatBranches = computed<FlatBranch[]>(() => {
  const list: FlatBranch[] = []
  for (const a of filteredAgencies.value) {
    for (const b of a.branches) {
      list.push({ branch: b.branch, agency: a.agency, rate: b.rate, streak: b.streak, total_days: b.total_days, exposed_days: b.exposed_days, monthly: b.monthly, monthly_agency: b.monthly_agency || {} })
    }
  }
  // 정렬
  const key = statsSortKey.value
  const desc = statsSortDesc.value
  list.sort((a, b) => {
    let av: number | string = 0, bv: number | string = 0
    if (key === 'branch') { av = a.branch; bv = b.branch }
    else if (key === 'agency') {
      const ai = AGENCY_ORDER.indexOf(a.agency)
      const bi = AGENCY_ORDER.indexOf(b.agency)
      av = ai === -1 ? 99 : ai; bv = bi === -1 ? 99 : bi
    }
    else if (key === 'rate') { av = a.rate; bv = b.rate }
    else if (key === 'total_days') { av = a.total_days; bv = b.total_days }
    else if (key === 'exposed_days') { av = a.exposed_days; bv = b.exposed_days }
    else if (key === 'streak') { av = a.streak; bv = b.streak }
    else { av = a.monthly[key]?.rate ?? -1; bv = b.monthly[key]?.rate ?? -1 }  // month key
    if (av < bv) return desc ? 1 : -1
    if (av > bv) return desc ? -1 : 1
    return 0
  })
  return list
})

// 실행사 변경 이력
const agencyHistory = ref<{branch_name: string; from_agency: string; to_agency: string; changed_at: string}[]>([])

async function loadAgencyHistory(type: 'place' | 'webpage') {
  try {
    const { data } = await api.get('/config/agency-history', { params: { type } })
    agencyHistory.value = data
  } catch {
    agencyHistory.value = []
  }
}

// Branch names that have changed agencies
const changedBranches = computed(() => {
  const set = new Set<string>()
  for (const h of agencyHistory.value) set.add(h.branch_name)
  return set
})

function getChangeInfo(branch: string): string {
  const changes = agencyHistory.value.filter(h => h.branch_name === branch)
  if (changes.length === 0) return ''
  return changes.map(c => `${c.changed_at}: ${c.from_agency} → ${c.to_agency}`).join('\n')
}

// ════════════════════════════════════════════
// 대시보드 통계
// ════════════════════════════════════════════
interface DashboardStats {
  type: string
  period: string
  total_branches: number
  overall_rate: number
  total_days: number
  exposed_days: number
  yesterday_exposed: number
  day_before_exposed: number
  avg_streak: number
  perfect_count: number
  monthly_rates: Record<string, number>
  distribution: { excellent: number; good: number; fair: number; poor: number }
  top_changes: { branch: string; prev_rate: number; curr_rate: number; diff: number }[]
}

const dashboardPlace = ref<DashboardStats | null>(null)
const dashboardWebpage = ref<DashboardStats | null>(null)
const dashboardLoading = ref(false)
const dashboardMonths = ref(6)

async function loadDashboard() {
  dashboardLoading.value = true
  try {
    const [p, w] = await Promise.all([
      api.get('/config/dashboard-stats', { params: { type: 'place', months: dashboardMonths.value } }).then(r => r.data).catch(() => null),
      api.get('/config/dashboard-stats', { params: { type: 'webpage', months: dashboardMonths.value } }).then(r => r.data).catch(() => null),
    ])
    dashboardPlace.value = p
    dashboardWebpage.value = w
  } finally {
    dashboardLoading.value = false
  }
}

// ════════════════════════════════════════════

onMounted(() => {
  loadAgencyMaps()
  loadAgencySheets()
  loadDashboard()  // 기본 탭: 대시보드
  document.addEventListener('click', handleClickOutside, true)
})
onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside, true)
})
</script>

<template>
  <div class="max-w-6xl">
    <!-- Sub-tabs -->
    <div class="flex gap-1 mb-4 border-b border-slate-200">
      <button v-for="t in [
        { key: 'dashboard', label: '대시보드' },
        { key: 'place-stats', label: '플레이스 성과' },
        { key: 'webpage-stats', label: '웹페이지 성과' },
        { key: 'mapping', label: '매핑 관리' },
        { key: 'rank-checker', label: 'SB체커' },
      ]" :key="t.key"
        @click="subTab = t.key as SubTab; if (t.key === 'dashboard') loadDashboard(); if (t.key === 'place-stats') loadStats('place'); if (t.key === 'webpage-stats') loadStats('webpage')"
        :class="['px-3 py-2 text-sm font-medium transition border-b-2 -mb-px',
          subTab === t.key ? 'border-slate-700 text-slate-800' : 'border-transparent text-slate-400 hover:text-slate-600']"
      >{{ t.label }}</button>
    </div>

    <!-- ═══ 대시보드 (2열 밀집 레이아웃) ═══ -->
    <div v-if="subTab === 'dashboard'" class="max-w-4xl">
      <!-- 기간 선택 -->
      <div class="flex items-center gap-2 text-xs mb-3">
        <label class="text-slate-500">기간:</label>
        <div class="flex gap-1">
          <button v-for="p in [{v:1,l:'1개월'},{v:3,l:'3개월'},{v:6,l:'6개월'},{v:12,l:'1년'}]" :key="p.v"
            @click="dashboardMonths = p.v; loadDashboard()"
            :class="dashboardMonths === p.v ? 'bg-blue-600 text-white' : 'bg-white text-slate-500 hover:text-slate-700'"
            class="px-2 py-0.5 rounded border text-[11px]">{{ p.l }}</button>
        </div>
      </div>

      <div v-if="dashboardLoading" class="text-center py-8 text-sm text-slate-400">로딩 중...</div>

      <template v-else>
        <!-- 2열 배치 -->
        <div class="grid grid-cols-2 gap-3">
          <!-- ━━━ 플레이스 ━━━ -->
          <div v-if="dashboardPlace" class="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div class="flex items-center gap-2 px-3 py-2 bg-sky-50 border-b border-sky-100">
              <span class="w-1 h-4 bg-sky-500 rounded-full"></span>
              <h3 class="text-sm font-bold text-sky-700">플레이스 총 성과</h3>
              <span class="text-[11px] text-slate-500 ml-auto">{{ dashboardPlace.period }}</span>
            </div>
            <div class="p-3 space-y-4">
              <!-- KPI 2x2 -->
              <div class="grid grid-cols-2 gap-1.5">
                <div class="border border-slate-200 rounded-md p-3">
                  <div class="text-[11px] text-slate-500">전체 성공률</div>
                  <div class="text-2xl font-bold leading-none my-1" :class="dashboardPlace.overall_rate >= 50 ? 'text-sky-600' : 'text-red-500'">{{ dashboardPlace.overall_rate }}%</div>
                  <div class="text-[11px] text-slate-500">{{ dashboardPlace.exposed_days.toLocaleString() }} / {{ dashboardPlace.total_days.toLocaleString() }}일</div>
                </div>
                <div class="border border-slate-200 rounded-md p-3">
                  <div class="text-[11px] text-slate-500">어제 노출</div>
                  <div class="text-lg font-bold text-slate-700 leading-tight">{{ dashboardPlace.yesterday_exposed }} / {{ dashboardPlace.total_branches }}</div>
                  <div class="text-[10px]" :class="(dashboardPlace.yesterday_exposed - dashboardPlace.day_before_exposed) > 0 ? 'text-blue-500' : (dashboardPlace.yesterday_exposed - dashboardPlace.day_before_exposed) < 0 ? 'text-red-500' : 'text-slate-400'">
                    {{ (dashboardPlace.yesterday_exposed - dashboardPlace.day_before_exposed) > 0 ? '↑ 그저께 +' + (dashboardPlace.yesterday_exposed - dashboardPlace.day_before_exposed) : (dashboardPlace.yesterday_exposed - dashboardPlace.day_before_exposed) < 0 ? '↓ 그저께 ' + (dashboardPlace.yesterday_exposed - dashboardPlace.day_before_exposed) : '→ 동일' }}
                  </div>
                </div>
                <div class="border border-slate-200 rounded-md p-3">
                  <div class="text-[11px] text-slate-500">평균 연속</div>
                  <div class="text-lg font-bold text-slate-700 leading-tight">{{ dashboardPlace.avg_streak }}일</div>
                  <div class="text-[11px] text-slate-500">지점 평균</div>
                </div>
                <div class="border border-slate-200 rounded-md p-3">
                  <div class="text-[11px] text-slate-500">100% 유지</div>
                  <div class="text-lg font-bold text-sky-600 leading-tight">{{ dashboardPlace.perfect_count }}개</div>
                  <div class="text-[11px] text-slate-500">만점 지점</div>
                </div>
              </div>

              <!-- 월별 추이 -->
              <div>
                <p class="text-[11px] font-semibold text-slate-600 mb-2">월별 전체 성공률</p>
                <div class="flex gap-1" style="height: 80px">
                  <div v-for="(rate, m) in dashboardPlace.monthly_rates" :key="m" class="flex-1 flex flex-col items-center">
                    <!-- 바 + 바 위에 붙는 수치 -->
                    <div class="w-full bg-slate-50 rounded relative flex-1">
                      <div class="absolute bottom-0 left-0 right-0 rounded"
                        :class="rate >= 50 ? 'bg-sky-400' : 'bg-red-400'"
                        :style="{ height: rate + '%' }"></div>
                      <div class="absolute left-0 right-0 text-center text-[11px] font-semibold tabular-nums leading-none"
                        :class="rate >= 80 ? 'text-sky-700' : rate >= 50 ? 'text-slate-600' : 'text-red-600'"
                        :style="{ bottom: `calc(${rate}% + 2px)` }">
                        {{ rate }}
                      </div>
                    </div>
                    <div class="text-[10px] text-slate-400 mt-1">{{ parseInt(String(m).split('-')[1] || '0') }}월</div>
                  </div>
                </div>
              </div>

              <!-- 분포 스택 바 (단일 행) -->
              <div>
                <p class="text-[11px] font-semibold text-slate-600 mb-2">지점 성공률 분포 ({{ dashboardPlace.total_branches }}개)</p>
                <div class="flex h-7 rounded overflow-hidden">
                  <div v-if="dashboardPlace.distribution.excellent > 0"
                    class="bg-sky-500 flex items-center justify-center text-white text-xs font-semibold"
                    :style="{ width: (dashboardPlace.distribution.excellent / dashboardPlace.total_branches * 100) + '%' }"
                    :title="`우수 ${dashboardPlace.distribution.excellent}개`">{{ dashboardPlace.distribution.excellent }}</div>
                  <div v-if="dashboardPlace.distribution.good > 0"
                    class="bg-sky-300 flex items-center justify-center text-white text-xs font-semibold"
                    :style="{ width: (dashboardPlace.distribution.good / dashboardPlace.total_branches * 100) + '%' }"
                    :title="`양호 ${dashboardPlace.distribution.good}개`">{{ dashboardPlace.distribution.good }}</div>
                  <div v-if="dashboardPlace.distribution.fair > 0"
                    class="bg-amber-400 flex items-center justify-center text-white text-xs font-semibold"
                    :style="{ width: (dashboardPlace.distribution.fair / dashboardPlace.total_branches * 100) + '%' }"
                    :title="`보통 ${dashboardPlace.distribution.fair}개`">{{ dashboardPlace.distribution.fair }}</div>
                  <div v-if="dashboardPlace.distribution.poor > 0"
                    class="bg-red-400 flex items-center justify-center text-white text-xs font-semibold"
                    :style="{ width: (dashboardPlace.distribution.poor / dashboardPlace.total_branches * 100) + '%' }"
                    :title="`부진 ${dashboardPlace.distribution.poor}개`">{{ dashboardPlace.distribution.poor }}</div>
                </div>
                <div class="flex justify-between text-[10px] text-slate-500 mt-1.5">
                  <span><span class="inline-block w-2 h-2 rounded-full bg-sky-500 mr-1"></span>우수(90%+)</span>
                  <span><span class="inline-block w-2 h-2 rounded-full bg-sky-300 mr-1"></span>양호(70~89)</span>
                  <span><span class="inline-block w-2 h-2 rounded-full bg-amber-400 mr-1"></span>보통(50~69)</span>
                  <span><span class="inline-block w-2 h-2 rounded-full bg-red-400 mr-1"></span>부진(&lt;50)</span>
                </div>
              </div>

              <!-- 급변 -->
              <div v-if="dashboardPlace.top_changes.length > 0">
                <p class="text-[11px] font-semibold text-slate-600 mb-2">전월 대비 급변 (±15%)</p>
                <div class="flex flex-wrap gap-1">
                  <div v-for="c in dashboardPlace.top_changes" :key="c.branch"
                    class="px-2 py-1 rounded text-[11px] font-medium tabular-nums"
                    :class="c.diff > 0 ? 'bg-blue-50 text-blue-700' : 'bg-red-50 text-red-700'"
                    :title="`${c.prev_rate}% → ${c.curr_rate}%`">
                    {{ c.branch.replace('유앤아이', '') }} {{ c.diff > 0 ? '+' : '' }}{{ c.diff }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- ━━━ 웹페이지 ━━━ -->
          <div v-if="dashboardWebpage" class="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div class="flex items-center gap-2 px-3 py-2 bg-indigo-50 border-b border-indigo-100">
              <span class="w-1 h-4 bg-indigo-500 rounded-full"></span>
              <h3 class="text-sm font-bold text-indigo-700">웹페이지 총 성과</h3>
              <span class="text-[11px] text-slate-500 ml-auto">{{ dashboardWebpage.period }}</span>
            </div>
            <div class="p-3 space-y-4">
              <!-- KPI 2x2 -->
              <div class="grid grid-cols-2 gap-1.5">
                <div class="border border-slate-200 rounded-md p-3">
                  <div class="text-[11px] text-slate-500">전체 성공률</div>
                  <div class="text-2xl font-bold leading-none my-1" :class="dashboardWebpage.overall_rate >= 50 ? 'text-indigo-600' : 'text-red-500'">{{ dashboardWebpage.overall_rate }}%</div>
                  <div class="text-[11px] text-slate-500">{{ dashboardWebpage.exposed_days.toLocaleString() }} / {{ dashboardWebpage.total_days.toLocaleString() }}일</div>
                </div>
                <div class="border border-slate-200 rounded-md p-3">
                  <div class="text-[11px] text-slate-500">어제 노출</div>
                  <div class="text-lg font-bold text-slate-700 leading-tight">{{ dashboardWebpage.yesterday_exposed }} / {{ dashboardWebpage.total_branches }}</div>
                  <div class="text-[10px]" :class="(dashboardWebpage.yesterday_exposed - dashboardWebpage.day_before_exposed) > 0 ? 'text-blue-500' : (dashboardWebpage.yesterday_exposed - dashboardWebpage.day_before_exposed) < 0 ? 'text-red-500' : 'text-slate-400'">
                    {{ (dashboardWebpage.yesterday_exposed - dashboardWebpage.day_before_exposed) > 0 ? '↑ 그저께 +' + (dashboardWebpage.yesterday_exposed - dashboardWebpage.day_before_exposed) : (dashboardWebpage.yesterday_exposed - dashboardWebpage.day_before_exposed) < 0 ? '↓ 그저께 ' + (dashboardWebpage.yesterday_exposed - dashboardWebpage.day_before_exposed) : '→ 동일' }}
                  </div>
                </div>
                <div class="border border-slate-200 rounded-md p-3">
                  <div class="text-[11px] text-slate-500">평균 연속</div>
                  <div class="text-lg font-bold text-slate-700 leading-tight">{{ dashboardWebpage.avg_streak }}일</div>
                  <div class="text-[11px] text-slate-500">지점 평균</div>
                </div>
                <div class="border border-slate-200 rounded-md p-3">
                  <div class="text-[11px] text-slate-500">100% 유지</div>
                  <div class="text-lg font-bold text-indigo-600 leading-tight">{{ dashboardWebpage.perfect_count }}개</div>
                  <div class="text-[11px] text-slate-500">만점 지점</div>
                </div>
              </div>

              <!-- 월별 추이 -->
              <div>
                <p class="text-[11px] font-semibold text-slate-600 mb-2">월별 전체 성공률</p>
                <div class="flex gap-1" style="height: 80px">
                  <div v-for="(rate, m) in dashboardWebpage.monthly_rates" :key="m" class="flex-1 flex flex-col items-center">
                    <div class="w-full bg-slate-50 rounded relative flex-1">
                      <div class="absolute bottom-0 left-0 right-0 rounded"
                        :class="rate >= 50 ? 'bg-indigo-400' : 'bg-red-400'"
                        :style="{ height: rate + '%' }"></div>
                      <div class="absolute left-0 right-0 text-center text-[11px] font-semibold tabular-nums leading-none"
                        :class="rate >= 80 ? 'text-indigo-700' : rate >= 50 ? 'text-slate-600' : 'text-red-600'"
                        :style="{ bottom: `calc(${rate}% + 2px)` }">
                        {{ rate }}
                      </div>
                    </div>
                    <div class="text-[10px] text-slate-400 mt-1">{{ parseInt(String(m).split('-')[1] || '0') }}월</div>
                  </div>
                </div>
              </div>

              <!-- 분포 스택 바 -->
              <div>
                <p class="text-[11px] font-semibold text-slate-600 mb-2">지점 성공률 분포 ({{ dashboardWebpage.total_branches }}개)</p>
                <div class="flex h-7 rounded overflow-hidden">
                  <div v-if="dashboardWebpage.distribution.excellent > 0"
                    class="bg-indigo-500 flex items-center justify-center text-white text-xs font-semibold"
                    :style="{ width: (dashboardWebpage.distribution.excellent / dashboardWebpage.total_branches * 100) + '%' }">{{ dashboardWebpage.distribution.excellent }}</div>
                  <div v-if="dashboardWebpage.distribution.good > 0"
                    class="bg-indigo-300 flex items-center justify-center text-white text-xs font-semibold"
                    :style="{ width: (dashboardWebpage.distribution.good / dashboardWebpage.total_branches * 100) + '%' }">{{ dashboardWebpage.distribution.good }}</div>
                  <div v-if="dashboardWebpage.distribution.fair > 0"
                    class="bg-amber-400 flex items-center justify-center text-white text-xs font-semibold"
                    :style="{ width: (dashboardWebpage.distribution.fair / dashboardWebpage.total_branches * 100) + '%' }">{{ dashboardWebpage.distribution.fair }}</div>
                  <div v-if="dashboardWebpage.distribution.poor > 0"
                    class="bg-red-400 flex items-center justify-center text-white text-xs font-semibold"
                    :style="{ width: (dashboardWebpage.distribution.poor / dashboardWebpage.total_branches * 100) + '%' }">{{ dashboardWebpage.distribution.poor }}</div>
                </div>
                <div class="flex justify-between text-[10px] text-slate-500 mt-1.5">
                  <span><span class="inline-block w-2 h-2 rounded-full bg-indigo-500 mr-1"></span>우수(90%+)</span>
                  <span><span class="inline-block w-2 h-2 rounded-full bg-indigo-300 mr-1"></span>양호(70~89)</span>
                  <span><span class="inline-block w-2 h-2 rounded-full bg-amber-400 mr-1"></span>보통(50~69)</span>
                  <span><span class="inline-block w-2 h-2 rounded-full bg-red-400 mr-1"></span>부진(&lt;50)</span>
                </div>
              </div>

              <!-- 급변 -->
              <div v-if="dashboardWebpage.top_changes.length > 0">
                <p class="text-[11px] font-semibold text-slate-600 mb-2">전월 대비 급변 (±15%)</p>
                <div class="flex flex-wrap gap-1">
                  <div v-for="c in dashboardWebpage.top_changes" :key="c.branch"
                    class="px-2 py-1 rounded text-[11px] font-medium tabular-nums"
                    :class="c.diff > 0 ? 'bg-blue-50 text-blue-700' : 'bg-red-50 text-red-700'"
                    :title="`${c.prev_rate}% → ${c.curr_rate}%`">
                    {{ c.branch.replace('유앤아이의원', '').replace('유앤아이', '').trim() }} {{ c.diff > 0 ? '+' : '' }}{{ c.diff }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- ═══ 매핑 관리 ═══ -->
    <div v-if="subTab === 'mapping'">
      <div class="border border-slate-200 rounded-lg overflow-hidden">
        <!-- 헤더 -->
        <div class="px-4 py-3 bg-slate-50 border-b flex justify-between items-center">
          <div>
            <div class="text-sm font-semibold text-slate-700">실행사 매핑</div>
            <div class="text-xs text-slate-400">플레이스/웹페이지 지점별 실행사 배정</div>
          </div>
          <div class="flex gap-2">
            <button @click="agencyTab = 'place'" :class="agencyTab === 'place' ? 'bg-blue-600 text-white' : 'bg-white text-slate-600'" class="px-3 py-1 text-xs rounded border">플레이스</button>
            <button @click="agencyTab = 'webpage'" :class="agencyTab === 'webpage' ? 'bg-blue-600 text-white' : 'bg-white text-slate-600'" class="px-3 py-1 text-xs rounded border">웹페이지</button>
          </div>
        </div>

        <div class="p-4 space-y-4">
          <div v-if="Object.keys(currentAgencyMap).length === 0" class="text-xs text-slate-400 py-4 text-center">등록된 매핑이 없습니다.</div>
          <template v-else>
            <!-- 새 실행사 추가 -->
            <div class="flex items-center gap-2 pb-3 border-b border-slate-100">
              <span class="text-xs text-slate-500 whitespace-nowrap">새 실행사 추가</span>
              <input v-model="newAgencyName" @keydown.enter="addAgency" placeholder="실행사 이름" class="flex-1 px-2.5 py-1 border border-slate-300 rounded text-xs focus:border-blue-400 focus:outline-none" />
              <button @click="addAgency" class="px-3 py-1 bg-slate-600 text-white text-xs rounded hover:bg-slate-700 whitespace-nowrap">추가</button>
            </div>

            <!-- 실행사별 그룹 -->
            <div class="space-y-3">
              <div v-for="(branches, agencyName) in agencyGroups.groups" :key="agencyName" class="border-l-2 border-blue-300 pl-3">
                <div class="flex items-center justify-between mb-1.5">
                  <span class="text-xs font-semibold text-slate-700">{{ agencyName }} <span class="ml-1 font-normal text-slate-400">({{ branches.length }}개 지점)</span></span>
                  <button @click="removeAgency(agencyName)" title="실행사 삭제" class="text-xs text-slate-400 hover:text-red-500 px-1.5 py-0.5 rounded hover:bg-red-50">−</button>
                </div>
                <div class="flex flex-wrap gap-1">
                  <div v-for="branch in branches" :key="branch" class="relative" data-agency-dropdown>
                    <button @click="toggleAssigning(branch)" class="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition-colors cursor-pointer">
                      {{ branch }} <span class="text-blue-400 text-[10px]">▾</span>
                    </button>
                    <div v-if="assigningBranch === branch" class="absolute bottom-full left-0 mb-1 z-20 bg-white border border-slate-200 rounded shadow-md py-1 min-w-max">
                      <button v-for="name in agencyNames.filter(n => n !== agencyName)" :key="name" @click="assignBranch(branch, name)" class="block w-full text-left px-3 py-1.5 text-xs text-slate-700 hover:bg-blue-50 hover:text-blue-700">{{ name }}</button>
                      <button @click="unassignBranch(branch); assigningBranch = null" class="block w-full text-left px-3 py-1.5 text-xs text-red-500 hover:bg-red-50 border-t border-slate-100">배정 해제</button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 미배정 -->
              <div v-if="agencyGroups.unassigned.length > 0" class="border-l-2 border-amber-300 pl-3">
                <div class="text-xs font-semibold text-slate-500 mb-1.5">미배정 <span class="ml-1 font-normal text-slate-400">({{ agencyGroups.unassigned.length }}개 지점)</span></div>
                <div class="flex flex-wrap gap-1">
                  <div v-for="branch in agencyGroups.unassigned" :key="branch" class="relative" data-agency-dropdown>
                    <button @click="toggleAssigning(branch)" class="inline-flex items-center px-2 py-0.5 text-xs rounded-full bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100">{{ branch }} ▾</button>
                    <div v-if="assigningBranch === branch" class="absolute bottom-full left-0 mb-1 z-20 bg-white border border-slate-200 rounded shadow-md py-1 min-w-max">
                      <div v-if="agencyNames.length === 0" class="px-3 py-1.5 text-xs text-slate-400">실행사가 없습니다</div>
                      <button v-for="name in agencyNames" :key="name" @click="assignBranch(branch, name)" class="block w-full text-left px-3 py-1.5 text-xs text-slate-700 hover:bg-blue-50 hover:text-blue-700">{{ name }}</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <!-- 저장 -->
          <div class="flex items-center gap-2 pt-2 border-t border-slate-100">
            <button @click="saveAgencyMapHandler" :disabled="savingAgency" class="px-4 py-1.5 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50">{{ savingAgency ? '저장 중...' : '저장' }}</button>
            <span v-if="agencySaveMsg" class="text-xs" :class="agencySaveError ? 'text-red-500' : 'text-emerald-500'">{{ agencySaveMsg }}</span>
          </div>

          <!-- 시트 링크 (하단 배치) -->
          <div class="pt-3 border-t border-slate-100">
            <p class="text-xs font-semibold text-slate-500 mb-2">실행사별 시트 링크</p>
            <div class="space-y-1.5">
              <div v-for="(url, name) in currentSheets" :key="name" class="flex items-center gap-2 text-xs">
                <span class="font-medium text-slate-700 w-20 shrink-0">{{ name }}</span>
                <input v-model="agencySheets[agencyTab][name]" class="flex-1 px-2 py-1 border border-slate-200 rounded text-xs text-slate-500 focus:border-blue-400 focus:outline-none" placeholder="시트 URL 또는 ID" />
                <button @click="removeSheetEntry(name)" class="text-slate-400 hover:text-red-500 px-1">×</button>
              </div>
            </div>
            <div class="flex items-center gap-2 mt-2">
              <input v-model="newSheetAgency" placeholder="실행사명" class="w-20 px-2 py-1 border border-slate-300 rounded text-xs focus:border-blue-400 focus:outline-none" />
              <input v-model="newSheetUrl" placeholder="Google Sheets URL" @keydown.enter="addSheetEntry" class="flex-1 px-2 py-1 border border-slate-300 rounded text-xs focus:border-blue-400 focus:outline-none" />
              <button @click="addSheetEntry" class="px-2 py-1 bg-slate-600 text-white text-xs rounded hover:bg-slate-700">추가</button>
            </div>
            <div class="flex items-center gap-2 mt-2">
              <button @click="saveAgencySheetsHandler" class="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700">시트 저장</button>
              <span v-if="savingSheetsMsg" class="text-xs text-emerald-500">{{ savingSheetsMsg }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ 플레이스/웹페이지 성과 ═══ -->
    <div v-if="subTab === 'place-stats' || subTab === 'webpage-stats'">
      <div class="space-y-4">
        <!-- 기간 + 필터 -->
        <div class="flex items-center gap-2 text-xs flex-wrap">
          <label class="text-slate-500">기간:</label>
          <div class="flex gap-1">
            <button v-for="p in [{v:1,l:'1개월'},{v:3,l:'3개월'},{v:6,l:'6개월'},{v:12,l:'1년'}]" :key="p.v"
              @click="selectPreset(p.v)"
              :class="!statsCustom && statsMonths === p.v ? 'bg-blue-600 text-white' : 'bg-white text-slate-500 hover:text-slate-700'"
              class="px-2 py-0.5 rounded border text-[11px]">{{ p.l }}</button>
            <button @click="enableCustomRange"
              :class="statsCustom ? 'bg-blue-600 text-white' : 'bg-white text-slate-500 hover:text-slate-700'"
              class="px-2 py-0.5 rounded border text-[11px]">직접 선택</button>
          </div>
          <template v-if="statsCustom">
            <input type="month" v-model="statsDateFrom" class="px-1.5 py-0.5 border border-slate-300 rounded text-[11px]" />
            <span class="text-slate-400">~</span>
            <input type="month" v-model="statsDateTo" class="px-1.5 py-0.5 border border-slate-300 rounded text-[11px]" />
            <button @click="loadStats(subTab === 'place-stats' ? 'place' : 'webpage')"
              class="px-2 py-0.5 bg-blue-600 text-white rounded text-[11px]">조회</button>
          </template>
          <label class="text-slate-500 ml-2">실행사:</label>
          <select v-model="statsFilter" class="px-2 py-1 border border-slate-300 rounded text-xs">
            <option value="">전체</option>
            <option v-for="a in statsData?.agencies" :key="a.agency" :value="a.agency">{{ a.agency }}</option>
          </select>
          <span v-if="statsData" class="ml-auto text-slate-400">{{ statsData.period }}</span>
        </div>

        <!-- 로딩 -->
        <div v-if="statsLoading" class="text-center py-8 text-sm text-slate-400">통계 로딩 중...</div>

        <template v-else-if="statsData">
          <!-- 실행사 요약 카드 (월 개수에 따라 열 수 조절) -->
          <div class="grid gap-2"
            :style="{ gridTemplateColumns: `repeat(${Math.min(filteredAgencies.length, allMonths.length > 12 ? 1 : allMonths.length > 6 ? 2 : 4)}, 1fr)` }">
            <div v-for="a in filteredAgencies" :key="a.agency"
              class="bg-white border rounded-lg p-3 border-l-4"
              :class="[agencyColor(a.agency).border]">
              <div class="flex items-center justify-between mb-2">
                <span class="text-sm font-bold" :class="agencyColor(a.agency).text">{{ a.agency }}</span>
                <span class="text-[11px] text-slate-500">{{ a.branch_count }}지점</span>
              </div>
              <div class="flex items-center gap-2 mb-2">
                <div class="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div class="h-full rounded-full" :class="a.rate >= 50 ? 'bg-blue-400' : 'bg-red-400'" :style="{ width: a.rate + '%' }"></div>
                </div>
                <span class="text-sm font-bold" :class="a.rate >= 50 ? 'text-blue-600' : 'text-red-500'">{{ a.rate }}%</span>
              </div>
              <div class="flex items-center gap-2 text-[11px] text-slate-500">
                <span>평균연속 {{ a.avg_streak }}일</span>
                <span class="ml-auto" :class="a.trend === '↑' ? 'text-blue-500' : a.trend === '↓' ? 'text-red-500' : 'text-slate-400'">추이 {{ a.trend }}</span>
              </div>
              <!-- 월별 미니 바 + 수치 (카드 너비에 맞춰 꽉 차게) -->
              <div class="flex gap-0.5 mt-2">
                <div v-for="m in allMonths" :key="m"
                  class="flex-1 text-center min-w-0"
                  :title="`${m}: ${a.monthly[m] != null ? a.monthly[m] + '%' : '데이터 없음'}`">
                  <div v-if="allMonths.length <= 9" class="text-[9px] font-medium tabular-nums mb-0.5 overflow-hidden"
                    :class="(a.monthly[m] || 0) >= 80 ? 'text-blue-600' : (a.monthly[m] || 0) >= 50 ? 'text-slate-500' : (a.monthly[m] || 0) > 0 ? 'text-red-500' : 'text-slate-300'">
                    {{ a.monthly[m] != null ? a.monthly[m] + '%' : '-' }}
                  </div>
                  <div class="h-6 bg-slate-50 rounded-sm relative overflow-hidden">
                    <div class="absolute bottom-0 w-full rounded-sm transition-all" :class="(a.monthly[m] || 0) >= 50 ? 'bg-blue-300' : 'bg-red-300'" :style="{ height: (a.monthly[m] || 0) + '%' }"></div>
                  </div>
                  <div class="text-[9px] text-slate-400 mt-0.5 whitespace-nowrap overflow-hidden">{{ parseInt(m.split('-')[1] || '0') }}월</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 지점별 상세 테이블 (정렬 가능, 헤더 고정, 가로 스크롤) -->
          <div class="bg-white border border-slate-200 rounded-lg overflow-auto max-h-[600px]">
            <table class="text-xs whitespace-nowrap" style="min-width: 100%">
              <thead>
                <tr class="bg-slate-50 border-b select-none sticky top-0 z-10">
                  <th @click="toggleStatsSort('branch')" class="text-left pl-3 pr-2 py-2 font-medium text-slate-500 cursor-pointer hover:text-slate-700 bg-slate-50 sticky left-0 z-20" style="min-width: 90px">
                    지점 <span class="text-[10px]">{{ statsSortIcon('branch') }}</span>
                  </th>
                  <th @click="toggleStatsSort('agency')" class="text-left px-2 py-2 font-medium text-slate-500 cursor-pointer hover:text-slate-700" style="min-width: 76px">
                    현 실행사 <span class="text-[10px]">{{ statsSortIcon('agency') }}</span>
                  </th>
                  <th v-for="m in allMonths" :key="m" @click="toggleStatsSort(m)" class="text-center px-1.5 py-2 font-medium text-slate-500 cursor-pointer hover:text-slate-700" style="min-width: 52px">
                    {{ m.split('-')[1] }}월 <span class="text-[10px]">{{ statsSortIcon(m) }}</span>
                  </th>
                  <th @click="toggleStatsSort('rate')" class="text-center px-1.5 py-2 font-medium text-slate-500 cursor-pointer hover:text-slate-700" style="min-width: 52px" title="전체 기간 성공률">
                    전체 <span class="text-[10px]">{{ statsSortIcon('rate') }}</span>
                  </th>
                  <th @click="toggleStatsSort('exposed_days')" class="text-center px-1.5 py-2 font-medium text-slate-500 cursor-pointer hover:text-slate-700" style="min-width: 52px" title="전체 기간 노출 성공 일수">
                    총노출 <span class="text-[10px]">{{ statsSortIcon('exposed_days') }}</span>
                  </th>
                  <th @click="toggleStatsSort('total_days')" class="text-center px-1.5 py-2 font-medium text-slate-500 cursor-pointer hover:text-slate-700" style="min-width: 52px" title="전체 기간 작업 진행 일수">
                    총진행 <span class="text-[10px]">{{ statsSortIcon('total_days') }}</span>
                  </th>
                  <th @click="toggleStatsSort('streak')" class="text-center pr-3 pl-1.5 py-2 font-medium text-slate-500 cursor-pointer hover:text-slate-700" style="min-width: 50px" title="연속 노출 일수">
                    연속 <span class="text-[10px]">{{ statsSortIcon('streak') }}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="b in flatBranches" :key="b.branch"
                  :class="[agencyColor(b.agency).bg, 'border-b border-slate-100 border-l-2', agencyColor(b.agency).border, 'hover:bg-blue-50/40']">
                  <td class="pl-3 pr-2 py-1.5 text-slate-700 font-medium sticky left-0 z-[1]"
                    :class="agencyColor(b.agency).bg">
                    {{ b.branch }}
                    <span v-if="changedBranches.has(b.branch)"
                      class="ml-1 text-[9px] text-amber-500 cursor-help"
                      :title="getChangeInfo(b.branch)">&#9889;변경</span>
                  </td>
                  <td class="px-2 py-1.5">
                    <span class="inline-block px-1.5 py-0.5 rounded text-[10px] font-medium" :class="agencyColor(b.agency).badge">{{ b.agency }}</span>
                  </td>
                  <td v-for="m in allMonths" :key="m" class="text-center py-1 tabular-nums leading-tight">
                    <template v-if="b.monthly[m]">
                      <div class="text-[11px] font-medium"
                        :class="b.monthly[m].rate >= 80 ? 'text-blue-600' : b.monthly[m].rate >= 50 ? 'text-slate-600' : 'text-red-500'">
                        {{ b.monthly[m].rate }}%
                      </div>
                      <div v-if="b.monthly_agency[m]" class="text-[9px] mt-0.5"
                        :class="b.monthly_agency[m] !== b.agency ? 'text-amber-500 font-medium' : 'text-slate-300'">
                        {{ b.monthly_agency[m] !== b.agency ? b.monthly_agency[m] : '' }}
                      </div>
                    </template>
                    <span v-else class="text-slate-300 text-[11px]">-</span>
                  </td>
                  <td class="text-center py-1.5 font-semibold tabular-nums" :class="b.rate >= 50 ? 'text-blue-600' : 'text-red-500'">{{ b.rate }}%</td>
                  <td class="text-center py-1.5 text-blue-600 tabular-nums">{{ b.exposed_days }}</td>
                  <td class="text-center py-1.5 text-slate-400 tabular-nums">{{ b.total_days }}</td>
                  <td class="text-center py-1.5 text-slate-500 tabular-nums">{{ b.streak }}일</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </div>
    </div>

    <!-- ═══ SB체커 ═══ -->
    <div v-if="subTab === 'rank-checker'">
      <RankChecker :branches="branches" />
    </div>
  </div>
</template>
