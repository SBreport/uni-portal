<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import * as rcApi from '@/api/rankChecker'
import { shortName } from '@/utils/branchName'

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
const activeTab = ref<Tab>('keywords')

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

// 지점별 그룹핑
const groupedKeywords = computed(() => {
  const groups: Record<string, any[]> = {}
  for (const kw of keywords.value) {
    const name = kw.branch_name
    if (!groups[name]) groups[name] = []
    groups[name].push(kw)
  }
  return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b))
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

onMounted(loadKeywords)
</script>

<template>
  <div>
    <!-- 탭 -->
    <div class="flex gap-3 mb-4 border-b border-slate-200">
      <button v-for="tab in [{ key: 'keywords', label: '키워드 관리' }, { key: 'history', label: '체크 이력' }]"
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

      <!-- 키워드 테이블 (지점별 그룹) -->
      <div v-if="loading" class="text-sm text-slate-400 py-4 text-center">로딩 중...</div>
      <div v-else-if="groupedKeywords.length === 0" class="text-sm text-slate-400 py-8 text-center">
        등록된 키워드가 없습니다. 위 버튼으로 키워드를 등록하세요.
      </div>
      <div v-else class="space-y-3">
        <div v-for="[branchName, kws] in groupedKeywords" :key="branchName"
          class="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <!-- 지점 헤더 -->
          <div class="flex items-center justify-between px-3 py-2 bg-slate-50 border-b border-slate-200">
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-700">{{ shortName(branchName) }}</span>
              <span class="text-[10px] text-slate-400">{{ kws.length }}개 키워드</span>
            </div>
            <button @click="runCheckBranch(kws[0].branch_id)" :disabled="checking"
              class="text-[10px] px-2 py-0.5 bg-amber-100 text-amber-700 rounded hover:bg-amber-200 disabled:opacity-50 transition">
              체크 실행
            </button>
          </div>
          <!-- 키워드 행 -->
          <table class="w-full text-xs">
            <thead>
              <tr class="border-b border-slate-100 text-slate-400">
                <th class="text-left px-3 py-1.5 font-medium">키워드</th>
                <th class="text-left px-2 py-1.5 font-medium">검색어</th>
                <th class="text-left px-2 py-1.5 font-medium">Place ID</th>
                <th class="text-center px-2 py-1.5 font-medium w-16">보장순위</th>
                <th class="text-left px-2 py-1.5 font-medium">메모</th>
                <th class="text-center px-2 py-1.5 font-medium w-20">액션</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="kw in kws" :key="kw.id" class="border-b border-slate-50 hover:bg-blue-50/30">
                <template v-if="editingId === kw.id">
                  <td class="px-3 py-1.5"><input v-model="editForm.keyword" class="w-full text-xs border rounded px-1.5 py-0.5" /></td>
                  <td class="px-2 py-1.5"><input v-model="editForm.search_keyword" class="w-full text-xs border rounded px-1.5 py-0.5" /></td>
                  <td class="px-2 py-1.5"><input v-model="editForm.place_id" class="w-full text-xs border rounded px-1.5 py-0.5" /></td>
                  <td class="px-2 py-1.5 text-center"><input v-model.number="editForm.guaranteed_rank" type="number" class="w-12 text-xs border rounded px-1 py-0.5 text-center" /></td>
                  <td class="px-2 py-1.5"><input v-model="editForm.memo" class="w-full text-xs border rounded px-1.5 py-0.5" /></td>
                  <td class="px-2 py-1.5 text-center">
                    <button @click="saveEdit" class="text-blue-600 hover:underline mr-1">저장</button>
                    <button @click="cancelEdit" class="text-slate-400 hover:underline">취소</button>
                  </td>
                </template>
                <template v-else>
                  <td class="px-3 py-1.5 text-slate-700 font-medium">{{ kw.keyword }}</td>
                  <td class="px-2 py-1.5 text-slate-500">{{ kw.search_keyword || '-' }}</td>
                  <td class="px-2 py-1.5 text-slate-500 font-mono text-[11px]">{{ kw.place_id }}</td>
                  <td class="px-2 py-1.5 text-center text-slate-600">{{ kw.guaranteed_rank }}위</td>
                  <td class="px-2 py-1.5 text-slate-400">{{ kw.memo || '-' }}</td>
                  <td class="px-2 py-1.5 text-center">
                    <button @click="startEdit(kw)" class="text-blue-500 hover:underline mr-1">수정</button>
                    <button @click="removeKeyword(kw)" class="text-red-400 hover:underline">삭제</button>
                  </td>
                </template>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <!-- ═══ 체크 이력 탭 ═══ -->
    <template v-if="activeTab === 'history'">
      <!-- 헤더 + 요약 -->
      <div class="mb-3 flex items-center justify-between">
        <div>
          <p class="text-xs text-slate-400">
            측정일: {{ snapshotDate || '아직 측정 데이터 없음' }}
          </p>
          <p v-if="snapshotItems.length" class="text-sm font-medium text-slate-700 mt-0.5">
            {{ snapshotSummary.total }}건 ·
            <span class="text-blue-600">노출 {{ snapshotSummary.exposed }}</span> ·
            <span class="text-slate-500">미노출 {{ snapshotSummary.missed_exposed }}</span> ·
            <span class="text-rose-600">보장 미달 {{ snapshotSummary.missed_guaranteed }}</span>
          </p>
        </div>
        <button @click="loadSnapshot" :disabled="snapshotLoading"
                class="px-3 py-1.5 text-xs font-medium border border-slate-300 rounded hover:bg-slate-50 disabled:opacity-50">
          {{ snapshotLoading ? '로딩...' : '새로고침' }}
        </button>
      </div>

      <!-- 검색/필터 -->
      <div v-if="snapshotItems.length" class="mb-3 flex items-center gap-2 flex-wrap">
        <input type="text" v-model="searchQuery" placeholder="지점명·키워드 검색..."
               class="flex-1 min-w-48 px-3 py-1.5 text-xs border border-slate-300 rounded" />
        <label class="flex items-center gap-1.5 text-xs text-slate-600 cursor-pointer">
          <input type="checkbox" v-model="filterExposedOnly" /> 노출만
        </label>
        <label class="flex items-center gap-1.5 text-xs text-slate-600 cursor-pointer">
          <input type="checkbox" v-model="filterMissedOnly" /> 보장 미달만
        </label>
        <span class="text-xs text-slate-400 ml-auto">{{ filteredItems.length }}건 표시</span>
      </div>

      <!-- 측정 데이터 없음 -->
      <div v-if="!snapshotLoading && !snapshotItems.length"
           class="bg-slate-50 border border-slate-200 rounded-lg p-8 text-center">
        <p class="text-sm text-slate-500 mb-1">아직 측정 데이터가 없습니다</p>
        <p class="text-xs text-slate-400">
          <button class="underline" @click="activeTab = 'keywords'">키워드 관리 탭</button>에서
          [전체 순위 체크 실행]을 먼저 눌러주세요.
        </p>
      </div>

      <!-- 로딩 중 -->
      <div v-else-if="snapshotLoading" class="py-8 text-center text-sm text-slate-400">
        로딩 중...
      </div>

      <!-- 평면 테이블 -->
      <div v-else class="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <table class="w-full text-xs">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr class="text-slate-500">
              <th class="text-left px-3 py-2 font-medium cursor-pointer hover:text-slate-700"
                  @click="toggleSort('keyword')">
                키워드 <span v-if="sortKey === 'keyword'">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
              </th>
              <th class="text-left px-3 py-2 font-medium cursor-pointer hover:text-slate-700"
                  @click="toggleSort('branch')">
                지점 <span v-if="sortKey === 'branch'">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
              </th>
              <th class="text-center px-3 py-2 font-medium w-16 cursor-pointer hover:text-slate-700"
                  @click="toggleSort('rank')">
                순위 <span v-if="sortKey === 'rank'">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
              </th>
              <th class="text-center px-3 py-2 font-medium w-16">노출</th>
              <th class="text-center px-3 py-2 font-medium w-16">보장</th>
              <th class="text-center px-3 py-2 font-medium w-16 cursor-pointer hover:text-slate-700"
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
              <td class="px-3 py-1.5">{{ item.keyword }}</td>
              <td class="px-3 py-1.5">{{ item.branch_name }}</td>
              <td class="text-center px-3 py-1.5 tabular-nums font-medium">
                <span v-if="item.rank">{{ item.rank }}위</span>
                <span v-else class="text-slate-300">—</span>
              </td>
              <td class="text-center px-3 py-1.5">
                <span v-if="item.is_exposed === 1" class="text-blue-600">노출</span>
                <span v-else-if="item.is_exposed === 0" class="text-slate-400">미노출</span>
                <span v-else class="text-slate-300">—</span>
              </td>
              <td class="text-center px-3 py-1.5 text-slate-500 tabular-nums">{{ item.guaranteed_rank }}위</td>
              <td class="text-center px-3 py-1.5 tabular-nums">
                <span :class="trendLabel(item.trend).color">{{ trendLabel(item.trend).text }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 우측 슬라이드 패널 (지점 30일 매트릭스) -->
      <Teleport to="body">
        <div v-if="expandedBranchId !== null"
             class="fixed inset-0 z-40"
             @click.self="onToggleExpand(expandedBranchId!)">
          <!-- 오버레이 -->
          <div class="absolute inset-0 bg-slate-900/30" @click="onToggleExpand(expandedBranchId!)"></div>
          <!-- 패널 -->
          <div class="absolute right-0 top-0 bottom-0 w-full max-w-2xl bg-white shadow-2xl border-l border-slate-200 overflow-y-auto"
               @click.stop>
            <div class="sticky top-0 bg-white border-b border-slate-200 px-5 py-3 flex items-center justify-between">
              <div>
                <p class="text-xs text-slate-400">지점 측정 이력</p>
                <p class="text-sm font-bold text-slate-700">
                  {{ snapshotItems.find(i => i.branch_id === expandedBranchId)?.branch_name || '' }}
                  <span class="text-xs font-normal text-slate-400 ml-2">최근 30일</span>
                </p>
              </div>
              <button @click="onToggleExpand(expandedBranchId!)"
                      class="text-slate-400 hover:text-slate-700 text-lg leading-none">✕</button>
            </div>
            <div class="p-5">
              <p v-if="historyLoading" class="text-xs text-slate-400">로딩 중...</p>
              <div v-else-if="historyMatrix.dates.length" class="overflow-x-auto">
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
              <p v-else class="text-xs text-slate-400">측정 이력 없음</p>
            </div>
          </div>
        </div>
      </Teleport>
    </template>
  </div>
</template>
