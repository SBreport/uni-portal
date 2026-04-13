<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { fetchAgencyMap, saveAgencyMap, fetchAgencySheets, saveAgencySheets } from '@/api/branches'
import RankChecker from '@/components/admin/RankChecker.vue'
import api from '@/api/client'

const props = defineProps<{ branches: { id: number; name: string }[] }>()

// Sub-tabs
type SubTab = 'mapping' | 'place-stats' | 'webpage-stats' | 'rank-checker'
const subTab = ref<SubTab>('mapping')

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
  }[]
}

const statsData = ref<{ agencies: AgencyStatDetail[]; period: string } | null>(null)
const statsLoading = ref(false)
const statsMonths = ref(6)
const statsFilter = ref('')  // agency filter

async function loadStats(type: 'place' | 'webpage') {
  statsLoading.value = true
  try {
    const { data } = await api.get('/config/agency-stats', { params: { type, months: statsMonths.value } })
    statsData.value = data
    await loadAgencyHistory(type)
  } catch {
    statsData.value = null
  } finally {
    statsLoading.value = false
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
  monthly: Record<string, { total: number; exposed: number; rate: number }>
}

const flatBranches = computed<FlatBranch[]>(() => {
  const list: FlatBranch[] = []
  for (const a of filteredAgencies.value) {
    for (const b of a.branches) {
      list.push({ branch: b.branch, agency: a.agency, rate: b.rate, streak: b.streak, monthly: b.monthly })
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

onMounted(() => {
  loadAgencyMaps()
  loadAgencySheets()
  document.addEventListener('click', handleClickOutside, true)
})
onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside, true)
})
</script>

<template>
  <div class="max-w-5xl">
    <!-- Sub-tabs -->
    <div class="flex gap-1 mb-4 border-b border-slate-200">
      <button v-for="t in [
        { key: 'mapping', label: '매핑 관리' },
        { key: 'place-stats', label: '플레이스 성과' },
        { key: 'webpage-stats', label: '웹페이지 성과' },
        { key: 'rank-checker', label: 'SB체커' },
      ]" :key="t.key"
        @click="subTab = t.key as SubTab; if (t.key === 'place-stats') loadStats('place'); if (t.key === 'webpage-stats') loadStats('webpage')"
        :class="['px-3 py-2 text-sm font-medium transition border-b-2 -mb-px',
          subTab === t.key ? 'border-slate-700 text-slate-800' : 'border-transparent text-slate-400 hover:text-slate-600']"
      >{{ t.label }}</button>
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
            <!-- 시트 링크 -->
            <div class="pb-3 border-b border-slate-100">
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
        </div>
      </div>
    </div>

    <!-- ═══ 플레이스/웹페이지 성과 ═══ -->
    <div v-if="subTab === 'place-stats' || subTab === 'webpage-stats'">
      <div class="space-y-4">
        <!-- 기간 + 필터 -->
        <div class="flex items-center gap-3 text-xs">
          <label class="text-slate-500">기간:</label>
          <select v-model="statsMonths" @change="loadStats(subTab === 'place-stats' ? 'place' : 'webpage')" class="px-2 py-1 border border-slate-300 rounded text-xs">
            <option :value="1">최근 1개월</option>
            <option :value="3">최근 3개월</option>
            <option :value="6">최근 6개월</option>
          </select>
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
          <!-- 실행사 요약 카드 -->
          <div class="grid gap-2" :style="{ gridTemplateColumns: `repeat(${Math.min(filteredAgencies.length, 4)}, 1fr)` }">
            <div v-for="a in filteredAgencies" :key="a.agency"
              class="bg-white border rounded-lg p-3 border-l-4"
              :class="[agencyColor(a.agency).border]">
              <div class="flex items-center justify-between mb-2">
                <span class="text-sm font-bold" :class="agencyColor(a.agency).text">{{ a.agency }}</span>
                <span class="text-[10px] text-slate-400">{{ a.branch_count }}지점</span>
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
              <!-- 월별 미니 바 + 수치 -->
              <div class="flex gap-0.5 mt-2">
                <div v-for="m in allMonths" :key="m" class="flex-1 text-center" :title="`${m}: ${a.monthly[m] || 0}%`">
                  <div class="text-[9px] font-medium tabular-nums mb-0.5"
                    :class="(a.monthly[m] || 0) >= 80 ? 'text-blue-600' : (a.monthly[m] || 0) >= 50 ? 'text-slate-500' : (a.monthly[m] || 0) > 0 ? 'text-red-500' : 'text-slate-300'">
                    {{ a.monthly[m] != null ? a.monthly[m] + '%' : '-' }}
                  </div>
                  <div class="h-6 bg-slate-50 rounded-sm relative overflow-hidden">
                    <div class="absolute bottom-0 w-full rounded-sm transition-all" :class="(a.monthly[m] || 0) >= 50 ? 'bg-blue-300' : 'bg-red-300'" :style="{ height: (a.monthly[m] || 0) + '%' }"></div>
                  </div>
                  <div class="text-[9px] text-slate-400 mt-0.5">{{ m.split('-')[1] }}월</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 지점별 상세 테이블 (정렬 가능) -->
          <div class="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <table class="w-full text-xs">
              <thead>
                <tr class="bg-slate-50 border-b select-none">
                  <th @click="toggleStatsSort('branch')" class="text-left pl-3 py-2 font-medium text-slate-500 cursor-pointer hover:text-slate-700">
                    지점 <span class="text-[10px]">{{ statsSortIcon('branch') }}</span>
                  </th>
                  <th @click="toggleStatsSort('agency')" class="text-left px-2 py-2 font-medium text-slate-500 cursor-pointer hover:text-slate-700">
                    실행사 <span class="text-[10px]">{{ statsSortIcon('agency') }}</span>
                  </th>
                  <th v-for="m in allMonths" :key="m" @click="toggleStatsSort(m)" class="text-center px-2 py-2 font-medium text-slate-500 w-16 cursor-pointer hover:text-slate-700">
                    {{ m.split('-')[1] }}월 <span class="text-[10px]">{{ statsSortIcon(m) }}</span>
                  </th>
                  <th @click="toggleStatsSort('rate')" class="text-center px-2 py-2 font-medium text-slate-500 w-16 cursor-pointer hover:text-slate-700">
                    전체 <span class="text-[10px]">{{ statsSortIcon('rate') }}</span>
                  </th>
                  <th @click="toggleStatsSort('streak')" class="text-center px-2 py-2 font-medium text-slate-500 w-12 cursor-pointer hover:text-slate-700">
                    연속 <span class="text-[10px]">{{ statsSortIcon('streak') }}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="b in flatBranches" :key="b.branch"
                  :class="[agencyColor(b.agency).bg, 'border-b border-slate-100 border-l-2', agencyColor(b.agency).border, 'hover:bg-blue-50/40']">
                  <td class="pl-3 py-1.5 text-slate-700 font-medium">
                    {{ b.branch }}
                    <span v-if="changedBranches.has(b.branch)"
                      class="ml-1 text-[9px] text-amber-500 cursor-help"
                      :title="getChangeInfo(b.branch)">&#9889;변경</span>
                  </td>
                  <td class="px-2 py-1.5">
                    <span class="inline-block px-1.5 py-0.5 rounded text-[10px] font-medium" :class="agencyColor(b.agency).badge">{{ b.agency }}</span>
                  </td>
                  <td v-for="m in allMonths" :key="m" class="text-center py-1.5 tabular-nums"
                    :class="(b.monthly[m]?.rate || 0) >= 80 ? 'text-blue-600 font-medium' : (b.monthly[m]?.rate || 0) >= 50 ? 'text-slate-600' : (b.monthly[m]?.rate || 0) > 0 ? 'text-red-500' : 'text-slate-300'">
                    {{ b.monthly[m] ? b.monthly[m].rate + '%' : '-' }}
                  </td>
                  <td class="text-center py-1.5 font-semibold tabular-nums" :class="b.rate >= 50 ? 'text-blue-600' : 'text-red-500'">{{ b.rate }}%</td>
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
