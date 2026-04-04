<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import * as rcApi from '@/api/rankChecker'

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

// 수정 모드
const editingId = ref<number | null>(null)
const editForm = ref<Record<string, any>>({})

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

function shortName(name: string) {
  return name.replace('유앤아이', '')
}

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
    flashSuccess('키���드 등록 완료')
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

// ���제
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
    error.value = e.response?.data?.detail || '체�� 실행 실패'
  } finally {
    checking.value = false
  }
}

// ── 이력 조��� ──
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

// 이력 날짜별 그��핑
const groupedHistory = computed(() => {
  const groups: Record<string, any[]> = {}
  for (const h of history.value) {
    if (!groups[h.date]) groups[h.date] = []
    groups[h.date].push(h)
  }
  return Object.entries(groups).sort(([a], [b]) => b.localeCompare(a))
})

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
      <!-- 상단: 버튼 -->
      <div class="flex items-center gap-2 mb-4">
        <button @click="showForm = !showForm"
          class="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded hover:bg-blue-700 transition">
          {{ showForm ? '취소' : '+ 키워드 등록' }}
        </button>
        <button @click="runCheckAll" :disabled="checking"
          class="px-3 py-1.5 text-xs font-medium bg-amber-500 text-white rounded hover:bg-amber-600 disabled:opacity-50 transition">
          {{ checking ? '체크 ��...' : '전체 순위 체크 실행' }}
        </button>
        <span v-if="keywords.length" class="text-xs text-slate-400 ml-2">{{ keywords.length }}개 키워드</span>
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
                <th class="text-left px-3 py-1.5 font-medium">키���드</th>
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

    <!-- ═══ 체크 이력 ��� ═══ -->
    <template v-if="activeTab === 'history'">
      <div class="flex items-center gap-3 mb-4">
        <select v-model="historyBranchId" @change="loadHistory"
          class="text-xs border rounded px-2 py-1.5">
          <option :value="null" disabled>지점 선택</option>
          <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.name }}</option>
        </select>
        <span v-if="history.length" class="text-xs text-slate-400">{{ history.length }}건</span>
        <div v-if="historyLoading" class="text-xs text-slate-400">로딩 중...</div>
      </div>

      <div v-if="!historyBranchId" class="text-sm text-slate-400 py-8 text-center">
        지점을 선택하면 체크 이력을 표시합니다.
      </div>
      <div v-else-if="groupedHistory.length === 0 && !historyLoading" class="text-sm text-slate-400 py-8 text-center">
        체크 이력이 없습니다.
      </div>
      <div v-else class="space-y-3">
        <div v-for="[date, records] in groupedHistory" :key="date"
          class="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <div class="px-3 py-2 bg-slate-50 border-b border-slate-200">
            <span class="text-xs font-bold text-slate-700">{{ date }}</span>
            <span class="text-[10px] text-slate-400 ml-2">{{ records.length }}건</span>
          </div>
          <table class="w-full text-xs">
            <thead>
              <tr class="border-b border-slate-100 text-slate-400">
                <th class="text-left px-3 py-1.5 font-medium">키워드</th>
                <th class="text-center px-2 py-1.5 font-medium w-16">순위</th>
                <th class="text-center px-2 py-1.5 font-medium w-16">노출</th>
                <th class="text-center px-2 py-1.5 font-medium w-16">보장</th>
                <th class="text-left px-2 py-1.5 font-medium">체크 시각</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in records" :key="r.keyword" class="border-b border-slate-50">
                <td class="px-3 py-1.5 text-slate-700 font-medium">{{ r.keyword }}</td>
                <td class="px-2 py-1.5 text-center font-semibold"
                  :class="r.rank && r.rank <= r.guaranteed_rank ? 'text-emerald-600' : 'text-red-500'">
                  {{ r.rank ? r.rank + '위' : '미노출' }}
                </td>
                <td class="px-2 py-1.5 text-center">
                  <span :class="r.is_exposed ? 'text-emerald-600' : 'text-red-400'">
                    {{ r.is_exposed ? 'O' : 'X' }}
                  </span>
                </td>
                <td class="px-2 py-1.5 text-center text-slate-500">{{ r.guaranteed_rank }}위</td>
                <td class="px-2 py-1.5 text-slate-400">{{ r.checked_at?.slice(11, 16) || '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>
