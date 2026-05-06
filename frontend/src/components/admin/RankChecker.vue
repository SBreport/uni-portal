<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { Line, Doughnut, Bar } from 'vue-chartjs'
import * as rcApi from '@/api/rankChecker'
import { shortName } from '@/utils/branchName'
import PageLayout from '@/components/common/PageLayout.vue'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, ArcElement, BarElement, Title, Tooltip, Legend)

const props = defineProps<{ branches: { id: number; name: string }[] }>()

// ── 상태 ──
const keywords = ref<any[]>([])
const loading = ref(false)
const error = ref('')
const successMsg = ref('')

// 체크 실행 (SSE 스트리밍)
const checking = ref(false)
const checkResult = ref<any>(null)
const streamLogs = ref<{ time: string; text: string; type: string }[]>([])
const streamProgress = ref({ checked: 0, total: 0, branches: 0, totalBranches: 0 })
const logContainer = ref<HTMLElement | null>(null)

// 이력
const historyBranchId = ref<number | null>(null)
const history = ref<any[]>([])
const historyLoading = ref(false)

// 키워드 등록 폼
const showForm = ref(false)
const form = ref({
  branch_id: 0,
  branch_name: '',
  keyword: '',
  search_keyword: '',
  place_id: '',
  guaranteed_rank: 5,
  memo: '',
})

// SB DB 임포트
const importing = ref(false)
const importResult = ref<any>(null)

// 수정 모드
const editingId = ref<number | null>(null)
const editForm = ref<Record<string, any>>({})

// place_id 자동 매칭
const needsPlaceIdMatching = ref(true)
const matching = ref(false)
const matchResult = ref<any>(null)
const reviewSelection = ref<Record<number, string>>({})
const manualInput = ref<Record<number, string>>({})
const brandPrefix = ref('')  // 검색 시 prefix로 결합 (예: '유앤아이의원')

// ── 탭 ──
type Tab = 'keywords' | 'history'
const activeTab = ref<Tab>('history')

// ── 키워드 관리 ──
async function loadKeywords() {
  loading.value = true
  error.value = ''
  try {
    keywords.value = (await rcApi.getKeywords()).data
  } catch (e: any) {
    error.value = e.response?.data?.detail || '키워드 목록 로드 실패'
  } finally {
    loading.value = false
  }
}

// 키워드 정렬
const keywordsSortKey = ref<'branch' | 'keyword'>('branch')
const keywordsSortDir = ref<'asc' | 'desc'>('asc')

function toggleKeywordsSort(key: typeof keywordsSortKey.value) {
  if (keywordsSortKey.value === key) {
    keywordsSortDir.value = keywordsSortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    keywordsSortKey.value = key
    keywordsSortDir.value = 'asc'
  }
}

const sortedFilteredKeywords = computed(() => {
  const dir = keywordsSortDir.value === 'asc' ? 1 : -1
  return [...keywords.value].sort((a, b) => {
    const av = keywordsSortKey.value === 'branch' ? a.branch_name : a.keyword
    const bv = keywordsSortKey.value === 'branch' ? b.branch_name : b.keyword
    return av.localeCompare(bv) * dir
  })
})


// 등록
function onBranchSelect() {
  const b = props.branches.find(b => b.id === form.value.branch_id)
  form.value.branch_name = b?.name || ''
}

async function submitKeyword() {
  if (!form.value.branch_id || !form.value.keyword || !form.value.place_id) {
    error.value = '지점, 키워드, Place ID는 필수입니다'
    return
  }
  error.value = ''
  try {
    await rcApi.createKeyword({
      branch_id: form.value.branch_id,
      branch_name: form.value.branch_name,
      keyword: form.value.keyword,
      search_keyword: form.value.search_keyword || undefined,
      place_id: form.value.place_id,
      guaranteed_rank: form.value.guaranteed_rank,
      memo: form.value.memo || undefined,
    })
    showForm.value = false
    form.value = { branch_id: 0, branch_name: '', keyword: '', search_keyword: '', place_id: '', guaranteed_rank: 5, memo: '' }
    await loadKeywords()
    flashSuccess('키워드 등록 완료')
  } catch (e: any) {
    error.value = e.response?.data?.detail || '등록 실패'
  }
}

// 수정
function startEdit(kw: any) {
  editingId.value = kw.id
  editForm.value = {
    keyword: kw.keyword,
    search_keyword: kw.search_keyword,
    place_id: kw.place_id,
    guaranteed_rank: kw.guaranteed_rank,
    memo: kw.memo,
  }
}

async function saveEdit() {
  if (!editingId.value) return
  try {
    await rcApi.updateKeyword(editingId.value, editForm.value)
    editingId.value = null
    await loadKeywords()
    flashSuccess('수정 완료')
  } catch (e: any) {
    error.value = e.response?.data?.detail || '수정 실패'
  }
}

function cancelEdit() {
  editingId.value = null
}

// 삭제
async function removeKeyword(kw: any) {
  if (!confirm(`"${kw.keyword}" 키워드를 비활성화합니까?`)) return
  try {
    await rcApi.deleteKeyword(kw.id)
    await loadKeywords()
    flashSuccess('비활성화 완료')
  } catch (e: any) {
    error.value = e.response?.data?.detail || '삭제 실패'
  }
}

// ── 순위 체크 실행 (SSE 스트리밍) ──
function addLog(text: string, type: string = 'info') {
  const now = new Date()
  const time = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`
  streamLogs.value.push({ time, text, type })
  nextTick(() => {
    if (logContainer.value) logContainer.value.scrollTop = logContainer.value.scrollHeight
  })
}

function runCheckAll() {
  if (!confirm('전체 지점 순위 체크를 실행합니다.')) return
  checking.value = true
  checkResult.value = null
  streamLogs.value = []
  streamProgress.value = { checked: 0, total: 0, branches: 0, totalBranches: 0 }
  error.value = ''

  const token = localStorage.getItem('token')
  const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api'
  const url = `${baseUrl}/rank-checker/check-all-stream`

  addLog('전체 순위 체크 시작...', 'info')

  fetch(url, { headers: { 'Authorization': `Bearer ${token}` } })
    .then(response => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      function read(): Promise<void> {
        return reader.read().then(({ done, value }) => {
          if (done) {
            checking.value = false
            return
          }
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            try {
              const evt = JSON.parse(line.slice(6))
              handleStreamEvent(evt)
            } catch { /* skip */ }
          }
          return read()
        })
      }
      return read()
    })
    .catch(e => {
      error.value = `스트리밍 오류: ${e.message}`
      addLog(`오류: ${e.message}`, 'error')
      checking.value = false
    })
}

function handleStreamEvent(evt: any) {
  switch (evt.type) {
    case 'start':
      streamProgress.value.total = evt.total_keywords
      streamProgress.value.totalBranches = evt.total_branches
      addLog(`${evt.total_branches}개 지점, ${evt.total_keywords}개 키워드 체크 시작`, 'info')
      break
    case 'checking':
      streamProgress.value.checked = evt.checked
      addLog(`${evt.branch_name} > ${evt.keyword} 체크 중...`, 'checking')
      break
    case 'result': {
      streamProgress.value.checked = evt.checked
      const rank = evt.rank ? `${evt.rank}위` : '미노출'
      const icon = evt.is_exposed ? 'O' : 'X'
      addLog(`${evt.branch_name} > ${evt.keyword} → ${rank} ${icon}`, evt.is_exposed ? 'success' : 'fail')
      break
    }
    case 'branch_done':
      streamProgress.value.branches = evt.branch_idx
      addLog(`── ${evt.branch_name} 완료 (${evt.branch_idx}/${evt.total_branches}) ──`, 'branch')
      break
    case 'done':
      addLog(`전체 완료: ${evt.total_branches}개 지점, ${evt.total_checked}건 체크`, 'done')
      checking.value = false
      flashSuccess(`체크 완료: ${evt.total_branches}개 지점, ${evt.total_checked}건`)
      break
    case 'error':
      addLog(`오류: ${evt.branch_name} > ${evt.keyword} — ${evt.error}`, 'error')
      break
  }
}

async function runCheckBranch(branchId: number) {
  checking.value = true
  checkResult.value = null
  error.value = ''
  try {
    const { data } = await rcApi.checkBranch(branchId)
    checkResult.value = data
    flashSuccess(`체크 완료: ${data.checked}건`)
  } catch (e: any) {
    error.value = e.response?.data?.detail || '체크 실행 실패'
  } finally {
    checking.value = false
  }
}

// ── 이력 조회 ──
async function loadHistory() {
  if (!historyBranchId.value) return
  historyLoading.value = true
  try {
    history.value = (await rcApi.getHistory(historyBranchId.value)).data
  } catch (e: any) {
    error.value = e.response?.data?.detail || '이력 조회 실패'
  } finally {
    historyLoading.value = false
  }
}

// ── 체크 이력 — Level 1: 최근 스냅샷 ──
const snapshotDate = ref<string | null>(null)
const prevDate = ref<string | null>(null)
const snapshotItems = ref<Array<{
  keyword_id: number
  branch_id: number
  branch_name: string
  keyword: string
  search_keyword: string
  guaranteed_rank: number
  rank: number | null
  is_exposed: number | null
  checked_at: string | null
  prev_rank: number | null
  trend: number | null
}>>([])
const snapshotLoading = ref(false)

// Level 2 (우측 슬라이드 패널) — 펼친 지점 ID
const expandedBranchId = ref<number | null>(null)

// 체크 이력 — 검색/필터/정렬
const searchQuery = ref('')
const filterExposedOnly = ref(false)
const filterMissedOnly = ref(false)
const sortKey = ref<'keyword' | 'branch' | 'rank' | 'trend'>('keyword')
const sortDir = ref<'asc' | 'desc'>('asc')

// 필터+정렬 적용된 평면 리스트 (이미 받은 데이터 가공 — 룰 예외 영역)
const filteredItems = computed(() => {
  let items = snapshotItems.value

  // 검색 (지점명 또는 키워드 부분 매칭)
  const q = searchQuery.value.trim().toLowerCase()
  if (q) {
    items = items.filter(i =>
      i.keyword.toLowerCase().includes(q) ||
      i.branch_name.toLowerCase().includes(q)
    )
  }

  // 노출만
  if (filterExposedOnly.value) {
    items = items.filter(i => i.is_exposed === 1)
  }

  // 보장 미달만 (rank > guaranteed_rank, 또는 미노출)
  if (filterMissedOnly.value) {
    items = items.filter(i =>
      i.rank == null || i.rank > i.guaranteed_rank
    )
  }

  // 정렬
  const dir = sortDir.value === 'asc' ? 1 : -1
  items = [...items].sort((a, b) => {
    let av: any, bv: any
    switch (sortKey.value) {
      case 'keyword': av = a.keyword; bv = b.keyword; break
      case 'branch': av = a.branch_name; bv = b.branch_name; break
      case 'rank': av = a.rank ?? 9999; bv = b.rank ?? 9999; break
      case 'trend': av = a.trend ?? -9999; bv = b.trend ?? -9999; break
    }
    if (typeof av === 'string') return av.localeCompare(bv) * dir
    return (av - bv) * dir
  })

  return items
})

// 요약 카운트
const snapshotSummary = computed(() => {
  const total = snapshotItems.value.length
  const exposed = snapshotItems.value.filter(i => i.is_exposed === 1).length
  const missed_exposed = snapshotItems.value.filter(i =>
    i.rank != null && i.is_exposed === 0
  ).length
  const missed_guaranteed = snapshotItems.value.filter(i =>
    i.rank == null || i.rank > i.guaranteed_rank
  ).length
  return { total, exposed, missed_exposed, missed_guaranteed }
})

// ── KPI 변동 계산 ──
const newlyDropped = computed(() =>
  snapshotItems.value.filter(i => {
    if (i.prev_rank === null || i.prev_rank === undefined) return false
    const wasIn = i.prev_rank <= i.guaranteed_rank
    const nowOut = i.rank === null || i.rank > i.guaranteed_rank
    return wasIn && nowOut
  })
)

const recovered = computed(() =>
  snapshotItems.value.filter(i => {
    if (i.prev_rank === null || i.prev_rank === undefined) return false
    const wasOut = i.prev_rank > i.guaranteed_rank
    const nowIn = i.rank !== null && i.rank <= i.guaranteed_rank
    return wasOut && nowIn
  })
)

// ── 도넛 차트 데이터 ──
const doughnutData = computed(() => {
  const exposed = snapshotSummary.value.exposed
  const notExposed = snapshotSummary.value.total - exposed
  return {
    labels: ['노출', '미노출'],
    datasets: [{
      data: [exposed, notExposed],
      backgroundColor: ['#10b981', '#f87171'],
      borderWidth: 0,
    }],
  }
})

const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: { enabled: true },
  },
  cutout: '65%',
} as const

// ── 순위 분포 막대 차트 ──
const rankDistData = computed(() => {
  const items = snapshotItems.value
  const b1 = items.filter(i => i.rank !== null && i.rank >= 1 && i.rank <= 3).length
  const b2 = items.filter(i => i.rank !== null && i.rank >= 4 && i.rank <= 5).length
  const b3 = items.filter(i => i.rank !== null && i.rank >= 6 && i.rank <= 10).length
  const b4 = items.filter(i => i.rank !== null && i.rank > 10).length
  const b5 = items.filter(i => i.rank === null).length
  return {
    labels: ['1~3위', '4~5위', '6~10위', '11위+', '미측정'],
    datasets: [{
      data: [b1, b2, b3, b4, b5],
      backgroundColor: ['#10b981', '#34d399', '#94a3b8', '#f87171', '#e2e8f0'],
      borderWidth: 0,
      borderRadius: 3,
    }],
  }
})

const rankDistOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: { enabled: true },
  },
  scales: {
    x: { grid: { display: false }, ticks: { font: { size: 10 } } },
    y: { grid: { color: '#f1f5f9' }, ticks: { font: { size: 10 }, precision: 0 } },
  },
} as const

// ── 선택 지점 미니 라인 차트 ──
const branchLineData = computed(() => {
  if (!expandedBranchId.value || !history.value.length) return null
  const branchHistory = [...history.value].sort((a: any, b: any) => a.date.localeCompare(b.date))
  const uniqueKeywords = [...new Set(branchHistory.map((h: any) => h.keyword as string))]

  const colors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444']

  const datasets = uniqueKeywords.slice(0, 5).map((kw, idx) => {
    const kwData = branchHistory.filter((h: any) => h.keyword === kw)
    return {
      label: kw as string,
      data: kwData.map((h: any) => h.rank ?? null),
      borderColor: colors[idx % colors.length],
      backgroundColor: 'transparent',
      tension: 0.3,
      pointRadius: 3,
      spanGaps: true,
    }
  })

  const dates = [...new Set(branchHistory.map((h: any) => h.date as string))].sort()

  // guaranteed_rank: 첫 번째 키워드 기준 (지점별 동일 가정)
  const gRank = history.value[0]?.guaranteed_rank as number | undefined

  const annotationDataset = gRank !== undefined ? [{
    label: `보장(${gRank}위)`,
    data: dates.map(() => gRank),
    borderColor: '#94a3b8',
    backgroundColor: 'transparent',
    borderDash: [4, 4],
    borderWidth: 1,
    pointRadius: 0,
    tension: 0,
  }] : []

  return {
    labels: dates,
    datasets: [...datasets, ...annotationDataset],
  }
})

const branchLineOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: true, labels: { font: { size: 10 }, boxWidth: 10 } },
    tooltip: { enabled: true },
  },
  scales: {
    x: { grid: { display: false }, ticks: { font: { size: 10 }, maxTicksLimit: 6 } },
    y: {
      reverse: true,
      grid: { color: '#f1f5f9' },
      ticks: { font: { size: 10 }, precision: 0 },
      title: { display: false },
    },
  },
}))

// ── 변동 요약: 신규이탈/회복 리스트 (최대 5개) ──
const newlyDroppedList = computed(() => newlyDropped.value.slice(0, 5))
const recoveredList = computed(() => recovered.value.slice(0, 5))

function toggleSort(key: typeof sortKey.value) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDir.value = 'asc'
  }
}

function trendLabel(trend: number | null | undefined): { text: string; color: string } {
  if (trend === null || trend === undefined) return { text: '─', color: 'text-slate-300' }
  if (trend > 0) return { text: `↑${trend}`, color: 'text-emerald-600' }
  if (trend < 0) return { text: `↓${Math.abs(trend)}`, color: 'text-rose-600' }
  return { text: '→', color: 'text-slate-400' }
}

// 매트릭스 변환 (history → 날짜 × 키워드 셀)
const historyMatrix = computed(() => {
  if (!history.value.length) return { dates: [], keywords: [], cells: {} as Record<string, { rank: number | null; is_exposed: number }> }
  const dates = [...new Set(history.value.map((h: any) => h.date))].sort().reverse()
  const keywords = [...new Set(history.value.map((h: any) => h.keyword))]
  const cells: Record<string, { rank: number | null; is_exposed: number }> = {}
  for (const h of history.value) {
    cells[`${h.date}|${h.keyword}`] = { rank: h.rank, is_exposed: h.is_exposed }
  }
  return { dates, keywords, cells }
})

async function loadSnapshot() {
  snapshotLoading.value = true
  error.value = ''
  try {
    const res = await rcApi.getLatestSnapshot()
    snapshotDate.value = res.data.snapshot_date
    prevDate.value = res.data.prev_date || null
    snapshotItems.value = res.data.items
    // 패널이 열려 있으면 닫기
    expandedBranchId.value = null
    history.value = []
  } catch (e: any) {
    error.value = e.response?.data?.detail || '최근 측정 결과 로드 실패'
  } finally {
    snapshotLoading.value = false
  }
}

async function onToggleExpand(branchId: number) {
  if (expandedBranchId.value === branchId) {
    expandedBranchId.value = null
    history.value = []
    return
  }
  expandedBranchId.value = branchId
  historyBranchId.value = branchId
  await loadHistory()
}

watch(activeTab, (v) => {
  if (v === 'history' && snapshotItems.value.length === 0) {
    loadSnapshot()
  }
})

// ── SB DB 임포트 ──
async function handleImportSbDb(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!confirm('SB_CHECKER data.db에서 키워드를 가져옵니다.')) {
    input.value = ''
    return
  }
  importing.value = true
  importResult.value = null
  error.value = ''
  try {
    const { data } = await rcApi.importSbDb(file)
    importResult.value = data
    flashSuccess(`임포트 완료: ${data.imported}건 추가, ${data.skipped}건 스킵`)
    await loadKeywords()
  } catch (e: any) {
    error.value = e.response?.data?.detail || '임포트 실패'
  } finally {
    importing.value = false
    input.value = ''
  }
}

// ── place_id 자동 매칭 ──
async function onAutoMatch() {
  matching.value = true
  try {
    const res = await rcApi.autoMatchBranches(brandPrefix.value.trim() || undefined)
    matchResult.value = res.data
    // 검토 대기 항목의 기본 선택: 1순위 후보
    for (const item of res.data.pending_review) {
      if (item.candidates && item.candidates.length) {
        reviewSelection.value[item.branch_id] = item.candidates[0].place_id
      }
    }
    // 자동 매칭 성공이 있으면 키워드 목록 갱신
    if (res.data.stats.auto_matched > 0) {
      await loadKeywords()
    }
    // 미등록 지점이 0건이면 배너 숨기기
    if (res.data.stats.total === 0) {
      needsPlaceIdMatching.value = false
    }
  } catch (e: any) {
    error.value = '자동 매칭 실패: ' + (e?.response?.data?.detail || e.message)
  } finally {
    matching.value = false
  }
}

async function onSaveSelections() {
  const items: { branch_id: number; place_id: string }[] = []
  for (const item of matchResult.value.pending_review) {
    const pid = reviewSelection.value[item.branch_id]
    if (pid) items.push({ branch_id: item.branch_id, place_id: pid })
  }
  for (const item of matchResult.value.manual_required) {
    const pid = (manualInput.value[item.branch_id] || '').trim()
    if (pid) items.push({ branch_id: item.branch_id, place_id: pid })
  }
  if (!items.length) {
    error.value = '저장할 항목이 없습니다'
    return
  }
  try {
    const res = await rcApi.savePlaceIds(items)
    flashSuccess(`저장 완료: ${res.data.saved}개 지점, ${res.data.activated_keywords}개 키워드 활성화`)
    matchResult.value = null
    reviewSelection.value = {}
    manualInput.value = {}
    await loadKeywords()
  } catch (e: any) {
    error.value = '저장 실패: ' + (e?.response?.data?.detail || e.message)
  }
}

// ── 유틸 ──
function flashSuccess(msg: string) {
  successMsg.value = msg
  setTimeout(() => { successMsg.value = '' }, 3000)
}

onMounted(async () => {
  await loadKeywords()
  // 디폴트 탭이 history이므로 초기 스냅샷 로드
  if (activeTab.value === 'history') {
    loadSnapshot()
  }
})
</script>

<template>
  <!-- height 체인: 부모(AdminView 탭 영역)에서 h-full 받아 flex-col로 분배 -->
  <div class="h-full flex flex-col">
    <!-- 탭 -->
    <div class="flex gap-3 mb-4 border-b border-slate-200 shrink-0">
      <button v-for="tab in [{ key: 'history', label: '체크 이력' }, { key: 'keywords', label: '키워드 관리' }]"
        :key="tab.key" @click="activeTab = tab.key as Tab"
        :class="['pb-2 text-sm font-medium border-b-2 transition',
          activeTab === tab.key ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-400 hover:text-slate-600']">
        {{ tab.label }}
      </button>
    </div>

    <!-- 메시지 -->
    <div v-if="error" class="mb-3 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-600">{{ error }}</div>
    <div v-if="successMsg" class="mb-3 p-2 bg-green-50 border border-green-200 rounded text-xs text-green-600">{{ successMsg }}</div>

    <!-- ═══ 키워드 관리 탭 ═══ -->
    <template v-if="activeTab === 'keywords'">

      <!-- 지점 place_id 자동 매칭 배너 -->
      <div class="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg" v-if="needsPlaceIdMatching && !matchResult">
        <div class="flex items-center justify-between mb-2">
          <p class="text-sm font-bold text-amber-800">지점 place_id 미등록 — 측정 불가</p>
          <button class="px-3 py-1.5 text-xs font-medium bg-amber-600 text-white rounded hover:bg-amber-700 disabled:opacity-50 transition"
                  :disabled="matching"
                  @click="onAutoMatch">
            {{ matching ? '매칭 중...' : '자동 매칭 시작' }}
          </button>
        </div>
        <p class="text-xs text-amber-700 mb-2">네이버 검색으로 각 지점의 place_id를 자동으로 찾습니다. 약 30~60초 소요.</p>
        <div class="flex items-center gap-2">
          <label class="text-xs text-amber-800 whitespace-nowrap">브랜드명 prefix</label>
          <input type="text" v-model="brandPrefix" placeholder="예: 유앤아이의원"
                 class="flex-1 px-2 py-1 text-xs border border-amber-300 rounded bg-white" />
          <span class="text-[11px] text-amber-700 whitespace-nowrap">→ "강남점" 검색 시 "유앤아이의원 강남점"으로 보냄</span>
        </div>
      </div>

      <!-- 매칭 결과 -->
      <div v-if="matchResult" class="mb-4 bg-white border border-slate-200 rounded-lg p-4">
        <div class="flex items-center gap-3 mb-3">
          <span class="text-sm font-bold">매칭 결과</span>
          <span class="text-xs text-emerald-600">자동 {{ matchResult.stats.auto_matched }}건</span>
          <span class="text-xs text-amber-600">검토 {{ matchResult.stats.pending_review }}건</span>
          <span class="text-xs text-rose-600">수동 {{ matchResult.stats.manual_required }}건</span>
          <button class="ml-auto text-xs text-slate-400 hover:text-slate-600" @click="matchResult = null">닫기</button>
        </div>

        <!-- 자동 매칭 완료 목록 -->
        <div v-if="matchResult.matched.length" class="mb-3">
          <p class="text-xs font-bold text-slate-600 mb-2">자동 저장 완료 ({{ matchResult.matched.length }}건)</p>
          <div class="flex flex-col gap-1">
            <div v-for="item in matchResult.matched" :key="item.branch_id"
                 class="flex items-center gap-2 text-xs p-2 bg-emerald-50 border border-emerald-100 rounded">
              <span class="font-medium text-slate-700 w-40 shrink-0">{{ item.branch_name }}</span>
              <span class="text-emerald-700">{{ item.matched_name }}</span>
              <span class="text-slate-400 font-mono">({{ item.place_id }})</span>
              <span class="text-slate-400">유사도 {{ Math.round(item.score * 100) }}%</span>
            </div>
          </div>
        </div>

        <!-- 검토 대기: 후보 중 선택 -->
        <div v-if="matchResult.pending_review.length" class="mb-3">
          <p class="text-xs font-bold text-slate-600 mb-2">검토 필요 ({{ matchResult.pending_review.length }}건) — 후보 선택</p>
          <div class="flex flex-col gap-2">
            <div v-for="item in matchResult.pending_review" :key="item.branch_id"
                 class="border border-slate-200 rounded p-2">
              <p class="text-sm font-medium mb-1">{{ item.branch_name }}</p>
              <div class="flex flex-col gap-1">
                <label v-for="c in item.candidates" :key="c.place_id"
                       class="flex items-center gap-2 text-xs cursor-pointer">
                  <input type="radio" :name="'review_' + item.branch_id"
                         :value="c.place_id" v-model="reviewSelection[item.branch_id]" />
                  <span class="font-medium">{{ c.name }}</span>
                  <span class="text-slate-400 font-mono">({{ c.place_id }})</span>
                  <span class="text-slate-500">유사도 {{ Math.round(c.score * 100) }}%</span>
                </label>
                <label class="flex items-center gap-2 text-xs cursor-pointer">
                  <input type="radio" :name="'review_' + item.branch_id" value=""
                         v-model="reviewSelection[item.branch_id]" />
                  <span class="text-slate-500">건너뜀 (수동 입력으로)</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        <!-- 수동 입력 필요 -->
        <div v-if="matchResult.manual_required.length" class="mb-3">
          <p class="text-xs font-bold text-slate-600 mb-2">수동 입력 필요 ({{ matchResult.manual_required.length }}건)</p>
          <div class="flex flex-col gap-1">
            <div v-for="item in matchResult.manual_required" :key="item.branch_id"
                 class="flex items-center gap-2 text-xs border border-slate-200 rounded p-2">
              <span class="font-medium flex-1">{{ item.branch_name }}</span>
              <a :href="`https://map.naver.com/v5/search/${encodeURIComponent(item.branch_name)}`"
                 target="_blank" class="text-blue-500 underline shrink-0">네이버 지도 열기</a>
              <input type="text" placeholder="place_id 입력"
                     class="px-2 py-1 border border-slate-300 rounded w-32 tabular-nums text-xs"
                     v-model="manualInput[item.branch_id]" />
            </div>
          </div>
        </div>

        <button v-if="matchResult.pending_review.length || matchResult.manual_required.length"
                class="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded hover:bg-blue-700 transition"
                @click="onSaveSelections">
          선택/입력 항목 저장
        </button>
      </div>

      <!-- 상단: 버튼 -->
      <div class="flex items-center gap-2 mb-4">
        <button @click="showForm = !showForm"
          class="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded hover:bg-blue-700 transition">
          {{ showForm ? '취소' : '+ 키워드 등록' }}
        </button>
        <button @click="runCheckAll" :disabled="checking"
          class="px-3 py-1.5 text-xs font-medium bg-amber-500 text-white rounded hover:bg-amber-600 disabled:opacity-50 transition">
          {{ checking ? '체크 중...' : '전체 순위 체크 실행' }}
        </button>
        <label class="px-3 py-1.5 text-xs font-medium bg-slate-600 text-white rounded hover:bg-slate-700 transition cursor-pointer"
          :class="{ 'opacity-50 pointer-events-none': importing }">
          {{ importing ? '임포트 중...' : 'SB DB 임포트' }}
          <input type="file" accept=".db" class="hidden" @change="handleImportSbDb" />
        </label>
        <span v-if="keywords.length" class="text-xs text-slate-400 ml-2">{{ keywords.length }}개 키워드</span>
      </div>

      <!-- 임포트 결과 -->
      <div v-if="importResult" class="mb-4 p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs">
        <div class="font-medium text-slate-700 mb-1">임포트 결과</div>
        <div class="text-slate-500">
          SB DB: {{ importResult.total_in_sb }}건 / 추가: {{ importResult.imported }}건 / 스킵: {{ importResult.skipped }}건
        </div>
        <div v-if="importResult.unmatched_branches?.length" class="mt-1 text-amber-600">
          미매칭 지점: {{ importResult.unmatched_branches.join(', ') }}
        </div>
      </div>

      <!-- 실시간 로그 -->
      <div v-if="streamLogs.length > 0" class="mb-4 border border-slate-300 rounded-lg overflow-hidden">
        <!-- 진행률 바 -->
        <div v-if="checking || streamProgress.checked > 0" class="px-3 py-2 bg-slate-800 text-white flex items-center gap-3">
          <span class="text-xs font-mono">
            {{ checking ? '실행 중...' : '완료' }}
            ({{ streamProgress.branches }}/{{ streamProgress.totalBranches }}지점,
             {{ streamProgress.checked }}/{{ streamProgress.total }}키워드)
          </span>
          <div class="flex-1 h-1.5 bg-slate-600 rounded-full overflow-hidden">
            <div class="h-full bg-amber-400 rounded-full transition-all duration-300"
              :style="{ width: (streamProgress.total > 0 ? (streamProgress.checked / streamProgress.total) * 100 : 0) + '%' }"></div>
          </div>
          <span class="text-xs font-mono text-amber-300">
            {{ streamProgress.total > 0 ? Math.round((streamProgress.checked / streamProgress.total) * 100) : 0 }}%
          </span>
        </div>
        <!-- 로그 출력 -->
        <div ref="logContainer" class="bg-slate-900 p-3 max-h-64 overflow-y-auto font-mono text-[11px] leading-5">
          <div v-for="(log, i) in streamLogs" :key="i"
            :class="{
              'text-slate-400': log.type === 'info' || log.type === 'checking',
              'text-green-400': log.type === 'success',
              'text-red-400': log.type === 'fail' || log.type === 'error',
              'text-amber-300 font-bold': log.type === 'branch',
              'text-cyan-300 font-bold': log.type === 'done',
            }">
            <span class="text-slate-600 mr-2">{{ log.time }}</span>{{ log.text }}
          </div>
          <div v-if="checking" class="text-slate-500 animate-pulse">_</div>
        </div>
      </div>

      <!-- 등록 폼 -->
      <div v-if="showForm" class="mb-4 p-4 bg-slate-50 border border-slate-200 rounded-lg">
        <div class="grid grid-cols-3 gap-3">
          <div>
            <label class="block text-xs text-slate-500 mb-1">지점</label>
            <select v-model="form.branch_id" @change="onBranchSelect"
              class="w-full text-xs border rounded px-2 py-1.5">
              <option :value="0" disabled>선택</option>
              <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.name }}</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-slate-500 mb-1">키워드</label>
            <input v-model="form.keyword" class="w-full text-xs border rounded px-2 py-1.5" placeholder="선릉피부과" />
          </div>
          <div>
            <label class="block text-xs text-slate-500 mb-1">검색어 (미입력시 키워드 사용)</label>
            <input v-model="form.search_keyword" class="w-full text-xs border rounded px-2 py-1.5" placeholder="" />
          </div>
          <div>
            <label class="block text-xs text-slate-500 mb-1">Place ID</label>
            <input v-model="form.place_id" class="w-full text-xs border rounded px-2 py-1.5" placeholder="1234567890" />
          </div>
          <div>
            <label class="block text-xs text-slate-500 mb-1">보장순위</label>
            <input v-model.number="form.guaranteed_rank" type="number" min="1" max="50"
              class="w-full text-xs border rounded px-2 py-1.5" />
          </div>
          <div>
            <label class="block text-xs text-slate-500 mb-1">메모</label>
            <input v-model="form.memo" class="w-full text-xs border rounded px-2 py-1.5" />
          </div>
        </div>
        <div class="mt-3 flex justify-end">
          <button @click="submitKeyword"
            class="px-4 py-1.5 text-xs font-medium bg-blue-600 text-white rounded hover:bg-blue-700 transition">
            등록
          </button>
        </div>
      </div>

      <!-- 평면 테이블 — 자연 폭 (PageLayout mode="table"이 w-fit + max-w-full 자동 적용) -->
      <div v-if="loading" class="text-sm text-slate-400 py-4 text-center">로딩 중...</div>
      <PageLayout v-else mode="table">
       <div class="bg-white border border-slate-200 rounded-lg">
        <table class="text-xs">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr class="text-slate-500">
              <th class="text-left px-3 py-2 font-medium cursor-pointer hover:text-slate-700"
                  @click="toggleKeywordsSort('branch')">
                지점 <span v-if="keywordsSortKey === 'branch'">{{ keywordsSortDir === 'asc' ? '↑' : '↓' }}</span>
              </th>
              <th class="text-left px-3 py-2 font-medium cursor-pointer hover:text-slate-700"
                  @click="toggleKeywordsSort('keyword')">
                키워드 <span v-if="keywordsSortKey === 'keyword'">{{ keywordsSortDir === 'asc' ? '↑' : '↓' }}</span>
              </th>
              <th class="text-left px-3 py-2 font-medium">검색어</th>
              <th class="text-left px-3 py-2 font-medium">Place ID</th>
              <th class="text-center px-3 py-2 font-medium w-20">보장순위</th>
              <th class="text-left px-3 py-2 font-medium">메모</th>
              <th class="text-center px-3 py-2 font-medium w-28">액션</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="kw in sortedFilteredKeywords" :key="kw.id"
                class="border-b border-slate-100 last:border-0 hover:bg-slate-50">
              <template v-if="editingId === kw.id">
                <td class="px-3 py-1.5 text-slate-700">{{ shortName(kw.branch_name) }}</td>
                <td class="px-3 py-1.5"><input v-model="editForm.keyword" class="w-full text-xs border rounded px-1.5 py-0.5" /></td>
                <td class="px-3 py-1.5"><input v-model="editForm.search_keyword" class="w-full text-xs border rounded px-1.5 py-0.5" /></td>
                <td class="px-3 py-1.5"><input v-model="editForm.place_id" class="w-full text-xs border rounded px-1.5 py-0.5 font-mono" /></td>
                <td class="px-3 py-1.5 text-center"><input v-model.number="editForm.guaranteed_rank" type="number" class="w-12 text-xs border rounded px-1 py-0.5 text-center" /></td>
                <td class="px-3 py-1.5"><input v-model="editForm.memo" class="w-full text-xs border rounded px-1.5 py-0.5" /></td>
                <td class="px-3 py-1.5 text-center">
                  <button @click="saveEdit" class="text-blue-600 hover:underline mr-2">저장</button>
                  <button @click="cancelEdit" class="text-slate-400 hover:underline">취소</button>
                </td>
              </template>
              <template v-else>
                <td class="px-3 py-1.5 text-slate-700 font-medium">{{ shortName(kw.branch_name) }}</td>
                <td class="px-3 py-1.5 text-slate-700">{{ kw.keyword }}</td>
                <td class="px-3 py-1.5 text-slate-500">{{ kw.search_keyword || '-' }}</td>
                <td class="px-3 py-1.5 text-slate-500 font-mono text-[11px]">{{ kw.place_id }}</td>
                <td class="px-3 py-1.5 text-center text-slate-600 tabular-nums">{{ kw.guaranteed_rank }}위</td>
                <td class="px-3 py-1.5 text-slate-400 max-w-[12rem] truncate">{{ kw.memo || '-' }}</td>
                <td class="px-3 py-1.5 text-center whitespace-nowrap">
                  <button @click="runCheckBranch(kw.branch_id)" :disabled="checking"
                          class="text-amber-600 hover:underline mr-2 disabled:opacity-50">체크</button>
                  <button @click="startEdit(kw)" class="text-blue-500 hover:underline mr-2">수정</button>
                  <button @click="removeKeyword(kw)" class="text-red-400 hover:underline">삭제</button>
                </td>
              </template>
            </tr>
          </tbody>
        </table>
        <p v-if="!keywords.length && !loading" class="text-sm text-slate-400 py-8 text-center">
          등록된 키워드가 없습니다.
        </p>
       </div>
      </PageLayout>
    </template>

    <!-- ═══ 체크 이력 탭 ═══ -->
    <template v-if="activeTab === 'history'">
      <!-- 스크롤 분리 컨테이너 (부모 height 체인에서 받기 — magic number 제거) -->
      <div class="flex-1 min-h-0 flex flex-col">

        <!-- 헤더: KPI 4카드 + 측정일/새로고침 (위계 강화: 메인 24px / 라벨 12px = 2배) -->
        <div class="shrink-0 mb-2 flex items-stretch gap-2">
          <!-- 전체 -->
          <div class="bg-white border border-slate-200 rounded px-3 py-2 flex items-center justify-center gap-2 flex-1 min-w-0">
            <span class="text-xs text-slate-500 shrink-0">전체</span>
            <span class="text-2xl font-bold tabular-nums text-slate-800">{{ snapshotSummary.total }}</span>
          </div>
          <!-- 노출 -->
          <div class="bg-white border border-slate-200 rounded px-3 py-2 flex items-center justify-center gap-2 flex-1 min-w-0">
            <span class="text-xs text-slate-500 shrink-0">노출</span>
            <div class="flex items-baseline gap-1">
              <span class="text-2xl font-bold tabular-nums text-emerald-600">{{ snapshotSummary.exposed }}</span>
              <span class="text-xs text-emerald-500 tabular-nums">
                {{ snapshotSummary.total > 0 ? Math.round(snapshotSummary.exposed / snapshotSummary.total * 100) : 0 }}%
              </span>
            </div>
          </div>
          <!-- 미노출 -->
          <div class="bg-white border border-slate-200 rounded px-3 py-2 flex items-center justify-center gap-2 flex-1 min-w-0">
            <span class="text-xs text-slate-500 shrink-0">미노출</span>
            <div class="flex items-baseline gap-1">
              <span class="text-2xl font-bold tabular-nums text-red-500">
                {{ snapshotSummary.total - snapshotSummary.exposed }}
              </span>
              <span class="text-xs text-red-400 tabular-nums">
                {{ snapshotSummary.total > 0 ? Math.round((snapshotSummary.total - snapshotSummary.exposed) / snapshotSummary.total * 100) : 0 }}%
              </span>
            </div>
          </div>
          <!-- 변동 -->
          <div class="bg-white border border-slate-200 rounded px-3 py-2 flex items-center justify-center gap-3 flex-1 min-w-0">
            <span class="text-xs text-slate-500 shrink-0">변동</span>
            <div class="flex items-center gap-3">
              <span class="flex items-baseline gap-1">
                <span class="text-xl font-bold tabular-nums text-red-500">&#9660;{{ newlyDropped.length }}</span>
                <span class="text-[11px] text-slate-400">이탈</span>
              </span>
              <span class="flex items-baseline gap-1">
                <span class="text-xl font-bold tabular-nums text-emerald-600">&#9650;{{ recovered.length }}</span>
                <span class="text-[11px] text-slate-400">회복</span>
              </span>
            </div>
          </div>
          <!-- 측정일 + 새로고침 -->
          <div class="bg-white border border-slate-200 rounded px-3 py-2 flex items-center gap-2 shrink-0">
            <div class="text-xs text-slate-500 leading-tight">
              <div>측정일</div>
              <div class="text-sm text-slate-700 tabular-nums font-medium">{{ snapshotDate || '—' }}</div>
            </div>
            <button @click="loadSnapshot" :disabled="snapshotLoading"
                    class="ml-1 px-2 py-1 text-xs font-medium border border-slate-300 rounded hover:bg-slate-50 disabled:opacity-50 shrink-0">
              {{ snapshotLoading ? '...' : '새로고침' }}
            </button>
          </div>
        </div>

        <!-- 검색/필터 행 (shrink-0) -->
        <div v-if="snapshotItems.length" class="shrink-0 mb-2 flex items-center gap-2 flex-wrap">
          <input type="text" v-model="searchQuery" placeholder="지점명·키워드 검색..."
                 class="flex-1 min-w-48 px-3 py-1.5 text-xs border border-slate-300 rounded" />
          <label class="flex items-center gap-1.5 text-xs text-slate-600 cursor-pointer">
            <input type="checkbox" v-model="filterExposedOnly" /> 노출만
          </label>
          <label class="flex items-center gap-1.5 text-xs text-slate-600 cursor-pointer">
            <input type="checkbox" v-model="filterMissedOnly" /> 보장 미달만
          </label>
          <span class="text-xs text-slate-400 ml-auto">{{ filteredItems.length }}건 표시
            <span v-if="prevDate" class="ml-2 text-slate-300">이전: {{ prevDate }}</span>
          </span>
        </div>

        <!-- 측정 데이터 없음 -->
        <div v-if="!snapshotLoading && !snapshotItems.length"
             class="flex-1 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-center">
          <div class="text-center">
            <p class="text-sm text-slate-500 mb-1">아직 측정 데이터가 없습니다</p>
            <p class="text-xs text-slate-400">
              <button class="underline" @click="activeTab = 'keywords'">키워드 관리 탭</button>에서
              [전체 순위 체크 실행]을 먼저 눌러주세요.
            </p>
          </div>
        </div>

        <!-- 로딩 중 -->
        <div v-else-if="snapshotLoading" class="flex-1 flex items-center justify-center text-sm text-slate-400">
          로딩 중...
        </div>

        <!-- 본문: lg 이상 [그래프 | 메인 | 측정이력] 3분할 균등,
                    lg 미만 [메인 → 그래프 → 측정이력] vertical stack -->
        <div v-else class="flex-1 min-h-0 flex flex-col lg:flex-row gap-3 overflow-y-auto lg:overflow-visible">

          <!-- 메인 테이블 (lg에서 가운데, 미만에서 1번째) -->
          <div class="lg:flex-1 lg:min-w-0 lg:min-h-0 lg:overflow-y-auto overflow-x-auto max-w-full lg:max-w-[600px] order-1 lg:order-2">
            <div class="bg-white border border-slate-200 rounded-lg w-full">
              <table class="text-xs w-full">
                <thead class="bg-slate-50 border-b border-slate-200 sticky top-0">
                  <tr class="text-slate-500">
                    <th class="text-left px-3 py-2 font-medium whitespace-nowrap cursor-pointer hover:text-slate-700"
                        @click="toggleSort('keyword')">
                      키워드 <span v-if="sortKey === 'keyword'">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
                    </th>
                    <th class="text-left px-3 py-2 font-medium whitespace-nowrap cursor-pointer hover:text-slate-700"
                        @click="toggleSort('branch')">
                      지점 <span v-if="sortKey === 'branch'">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
                    </th>
                    <th class="text-center px-3 py-2 font-medium w-16 cursor-pointer hover:text-slate-700"
                        @click="toggleSort('rank')">
                      순위 <span v-if="sortKey === 'rank'">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
                    </th>
                    <th class="text-center px-3 py-2 font-medium w-16">노출</th>
                    <th class="text-center px-3 py-2 font-medium w-16">보장</th>
                    <th v-if="prevDate" class="text-center px-3 py-2 font-medium w-16 cursor-pointer hover:text-slate-700"
                        @click="toggleSort('trend')">
                      변동 <span v-if="sortKey === 'trend'">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in filteredItems" :key="item.keyword_id"
                      class="border-b border-slate-100 last:border-0 hover:bg-slate-50 cursor-pointer"
                      :class="expandedBranchId === item.branch_id ? 'bg-blue-50' : ''"
                      @click="onToggleExpand(item.branch_id)">
                    <td class="px-3 py-1.5 whitespace-nowrap">{{ item.keyword }}</td>
                    <td class="px-3 py-1.5 whitespace-nowrap">{{ shortName(item.branch_name) }}</td>
                    <td class="text-center px-3 py-1.5 tabular-nums font-medium">
                      <span v-if="item.rank !== null"
                            :class="item.rank <= item.guaranteed_rank ? 'text-emerald-600' : 'text-red-500'">
                        {{ item.rank }}위
                      </span>
                      <span v-else class="text-slate-400">—</span>
                    </td>
                    <td class="text-center px-3 py-1.5">
                      <span v-if="item.is_exposed === 1"
                            class="bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded text-[10px] font-semibold">
                        노출
                      </span>
                      <span v-else-if="item.is_exposed === 0"
                            class="bg-red-50 text-red-700 px-1.5 py-0.5 rounded text-[10px] font-semibold">
                        미노출
                      </span>
                      <span v-else class="text-slate-300">—</span>
                    </td>
                    <td class="text-center px-3 py-1.5 text-slate-500 tabular-nums">{{ item.guaranteed_rank }}위</td>
                    <td v-if="prevDate" class="text-center px-3 py-1.5 tabular-nums">
                      <span :class="trendLabel(item.trend).color">{{ trendLabel(item.trend).text }}</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- 측정 이력 (lg에서 3번째 가장 우측, 미만에서 stack 3번째) -->
          <div class="lg:flex-1 lg:min-w-0 lg:min-h-0 lg:overflow-y-auto order-3 lg:order-3 flex flex-col gap-3">
              <template v-if="expandedBranchId !== null">
                <!-- 헤더 -->
                <div class="bg-white border border-slate-200 rounded px-3 py-2 flex items-center justify-between shrink-0">
                  <div class="min-w-0">
                    <p class="text-[11px] text-slate-400">지점 측정 이력</p>
                    <p class="text-sm font-bold text-slate-700 truncate">
                      {{ snapshotItems.find(i => i.branch_id === expandedBranchId)?.branch_name || '' }}
                      <span class="text-[11px] font-normal text-slate-400 ml-1">최근 30일</span>
                    </p>
                  </div>
                  <button @click="onToggleExpand(expandedBranchId!)"
                          class="text-slate-400 hover:text-slate-700 text-lg leading-none flex-shrink-0 ml-2">✕</button>
                </div>

                <p v-if="historyLoading" class="text-xs text-slate-400 text-center py-4">로딩 중...</p>

                <template v-else-if="historyMatrix.dates.length">
                  <!-- 미니 라인 차트 -->
                  <div class="bg-white border border-slate-200 rounded p-3">
                    <p class="text-[11px] font-medium text-slate-600 mb-1">순위 추이</p>
                    <div style="height: 110px">
                      <Line v-if="branchLineData" :data="branchLineData" :options="branchLineOptions" />
                    </div>
                  </div>

                  <!-- 매트릭스 -->
                  <div class="bg-white border border-slate-200 rounded p-3 overflow-x-auto">
                    <table class="text-xs border border-slate-200 rounded">
                      <thead class="bg-slate-50">
                        <tr class="text-slate-500 border-b border-slate-200">
                          <th class="text-left px-3 py-1.5 font-medium sticky left-0 bg-slate-50">날짜</th>
                          <th v-for="kw in historyMatrix.keywords" :key="kw"
                              class="text-center px-3 py-1.5 font-medium whitespace-nowrap">
                            {{ kw }}
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="d in historyMatrix.dates" :key="d"
                            class="border-b border-slate-100 last:border-0">
                          <td class="px-3 py-1.5 text-slate-600 tabular-nums sticky left-0 bg-white">{{ d }}</td>
                          <td v-for="kw in historyMatrix.keywords" :key="kw"
                              class="text-center px-3 py-1.5 tabular-nums whitespace-nowrap">
                            <template v-if="historyMatrix.cells[`${d}|${kw}`]">
                              <span v-if="historyMatrix.cells[`${d}|${kw}`].rank"
                                    :class="historyMatrix.cells[`${d}|${kw}`].is_exposed ? 'text-blue-600' : 'text-slate-400'">
                                {{ historyMatrix.cells[`${d}|${kw}`].rank }}위
                              </span>
                              <span v-else class="text-slate-300">미노출</span>
                            </template>
                            <span v-else class="text-slate-300">—</span>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </template>

                <p v-else class="text-xs text-slate-400 text-center py-4">측정 이력 없음</p>
              </template>

              <!-- 미선택 placeholder -->
              <div v-else
                   class="lg:flex-1 bg-slate-50/60 border border-dashed border-slate-200 rounded-lg flex items-center justify-center min-h-[200px]">
                <div class="text-center px-6">
                  <p class="text-sm text-slate-500 mb-1">테이블에서 지점을 클릭하세요</p>
                  <p class="text-[11px] text-slate-400">선택한 지점의 30일 순위 추이와 측정 이력이 여기에 표시됩니다</p>
                </div>
              </div>
            </div>

          <!-- 그래프 / 대시보드 (lg에서 1번째 가장 좌측, 미만에서 stack 2번째) -->
          <aside class="lg:flex-1 lg:min-w-0 lg:max-w-[420px] lg:min-h-0 lg:overflow-y-auto order-2 lg:order-1 flex flex-col gap-3">

            <!-- (a) 변동 요약 -->
            <div class="bg-white border border-slate-200 rounded p-3">
              <p class="text-[11px] font-medium text-slate-600 mb-2">변동 요약</p>
              <!-- 신규이탈 -->
              <div class="mb-2">
                <p class="text-[11px] text-red-500 font-medium mb-1">신규이탈 ({{ newlyDropped.length }}건)</p>
                <div v-if="newlyDroppedList.length" class="flex flex-col gap-0.5">
                  <div v-for="item in newlyDroppedList" :key="item.keyword_id"
                       class="flex items-center justify-between text-xs">
                    <span class="text-slate-600 truncate max-w-[120px]">{{ shortName(item.branch_name) }}</span>
                    <span class="text-slate-700 truncate max-w-[100px] mx-2">{{ item.keyword }}</span>
                    <span class="text-red-500 tabular-nums shrink-0">
                      {{ item.prev_rank }}위 → 이탈
                    </span>
                  </div>
                </div>
                <p v-else class="text-[11px] text-slate-400">없음</p>
              </div>
              <!-- 회복 -->
              <div>
                <p class="text-[11px] text-emerald-600 font-medium mb-1">회복 ({{ recovered.length }}건)</p>
                <div v-if="recoveredList.length" class="flex flex-col gap-0.5">
                  <div v-for="item in recoveredList" :key="item.keyword_id"
                       class="flex items-center justify-between text-xs">
                    <span class="text-slate-600 truncate max-w-[120px]">{{ shortName(item.branch_name) }}</span>
                    <span class="text-slate-700 truncate max-w-[100px] mx-2">{{ item.keyword }}</span>
                    <span class="text-emerald-600 tabular-nums shrink-0">
                      → {{ item.rank }}위
                    </span>
                  </div>
                </div>
                <p v-else class="text-[11px] text-slate-400">없음</p>
              </div>
            </div>

            <!-- (b) 노출 분포 도넛 -->
            <div class="bg-white border border-slate-200 rounded p-3">
              <p class="text-[11px] font-medium text-slate-600 mb-2">노출 분포</p>
              <div class="flex items-center gap-3">
                <div style="height: 80px; width: 80px; flex-shrink: 0">
                  <Doughnut :data="doughnutData" :options="doughnutOptions" />
                </div>
                <div class="flex flex-col gap-1">
                  <div class="flex items-center gap-1.5">
                    <span class="inline-block w-2 h-2 rounded-full bg-emerald-500"></span>
                    <span class="text-xs text-slate-600">노출 {{ snapshotSummary.exposed }}건</span>
                    <span class="text-[11px] text-slate-400 tabular-nums">
                      ({{ snapshotSummary.total > 0 ? Math.round(snapshotSummary.exposed / snapshotSummary.total * 100) : 0 }}%)
                    </span>
                  </div>
                  <div class="flex items-center gap-1.5">
                    <span class="inline-block w-2 h-2 rounded-full bg-red-400"></span>
                    <span class="text-xs text-slate-600">미노출 {{ snapshotSummary.total - snapshotSummary.exposed }}건</span>
                    <span class="text-[11px] text-slate-400 tabular-nums">
                      ({{ snapshotSummary.total > 0 ? Math.round((snapshotSummary.total - snapshotSummary.exposed) / snapshotSummary.total * 100) : 0 }}%)
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- (c) 순위 분포 막대 -->
            <div class="bg-white border border-slate-200 rounded p-3">
              <p class="text-[11px] font-medium text-slate-600 mb-2">순위 분포</p>
              <div style="height: 100px">
                <Bar :data="rankDistData" :options="rankDistOptions" />
              </div>
            </div>

          </aside>
        </div>

      </div>
    </template>
  </div>
</template>
