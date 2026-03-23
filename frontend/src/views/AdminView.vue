<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import * as usersApi from '@/api/users'
import * as equipApi from '@/api/equipment'
import * as eventsApi from '@/api/events'
import * as cafeApi from '@/api/cafe'
import * as papersApi from '@/api/papers'
// equipApi는 동기화 탭(장비시트 동기화)에서 사용
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

// ── 탭 ──
const activeTab = ref<'users' | 'sync' | 'device'>('users')

// ── 사용자 관리 ──
interface User { username: string; role: string; branch_id: number | null; memo: string }
const users = ref<User[]>([])
const branches = ref<{ id: number; name: string }[]>([])
const loading = ref(false)
const showForm = ref(false)
const newUsername = ref('')
const newPassword = ref('')
const newRole = ref('viewer')
const newBranchId = ref<number | null>(null)
const newMemo = ref('')
const formError = ref('')
const editingUser = ref<string | null>(null)
const editRole = ref('')
const editPassword = ref('')
const editMemo = ref('')
const editBranchId = ref<number | null>(null)

const roles = [
  { value: 'viewer', label: '뷰어' },
  { value: 'branch', label: '지점담당' },
  { value: 'editor', label: '편집자' },
  { value: 'admin', label: '관리자' },
]

// 지점 ID→이름 매핑
const branchMap = computed(() => {
  const m = new Map<number, string>()
  branches.value.forEach(b => m.set(b.id, b.name))
  return m
})

async function loadUsers() {
  loading.value = true
  try { users.value = (await usersApi.getUsers()).data } finally { loading.value = false }
}
async function loadBranches() { branches.value = (await equipApi.getBranches()).data }
onMounted(() => { loadUsers(); loadBranches() })

async function handleCreate() {
  formError.value = ''
  if (!newUsername.value || !newPassword.value) { formError.value = 'ID와 비밀번호를 입력해주세요.'; return }
  try {
    await usersApi.createUser({ username: newUsername.value, password: newPassword.value, role: newRole.value, branch_id: newBranchId.value || undefined, memo: newMemo.value })
    showForm.value = false; newUsername.value = ''; newPassword.value = ''; newRole.value = 'viewer'; newMemo.value = ''
    await loadUsers()
  } catch (e: any) { formError.value = e.response?.data?.detail || '생성 실패' }
}
async function handleDelete(username: string) {
  if (username === auth.username) return
  await usersApi.deleteUser(username); await loadUsers()
}
function startEdit(user: User) { editingUser.value = user.username; editRole.value = user.role; editPassword.value = ''; editMemo.value = user.memo || ''; editBranchId.value = user.branch_id }
async function handleUpdate() {
  if (!editingUser.value) return
  const u: Record<string, any> = {}
  if (editRole.value) u.role = editRole.value
  if (editPassword.value) u.password = editPassword.value
  if (editMemo.value !== undefined) u.memo = editMemo.value
  u.branch_id = editBranchId.value
  await usersApi.updateUser(editingUser.value, u); editingUser.value = null; await loadUsers()
}

// ── 동기화 ──
const syncMsg = ref('')
const syncError = ref('')
const syncing = ref(false)

// 장비
async function syncEquipment() {
  syncing.value = true; syncMsg.value = ''; syncError.value = ''
  try {
    const { data } = await equipApi.syncFromSheets()
    syncMsg.value = `장비 동기화 완료: +${data.added} ↻${data.updated} =${data.skipped}`
  } catch (e: any) { syncError.value = e.response?.data?.detail || '장비 동기화 실패' }
  finally { syncing.value = false }
}

// 이벤트
const now = new Date()
const evtBiMonth = computed(() => {
  const idx = Math.min(Math.floor((now.getMonth()) / 2), 5)
  const pairs = [[1,2],[3,4],[5,6],[7,8],[9,10],[11,12]]
  return pairs[idx]!
})
const evtYear = ref(now.getFullYear())
const evtStartMonth = computed(() => evtBiMonth.value[0]!)
const evtEndMonth = computed(() => evtBiMonth.value[1]!)
const evtSyncMethod = ref<'url' | 'file'>('url')
const evtSheetUrl = ref('')
const evtFile = ref<File | null>(null)

async function syncEvents() {
  syncing.value = true; syncMsg.value = ''; syncError.value = ''
  try {
    let data: any
    if (evtSyncMethod.value === 'url') {
      if (!evtSheetUrl.value) { syncError.value = 'URL을 입력해주세요.'; syncing.value = false; return }
      data = (await eventsApi.syncEventsFromUrl({ year: evtYear.value, start_month: evtStartMonth.value, end_month: evtEndMonth.value, source_url: evtSheetUrl.value })).data
    } else {
      if (!evtFile.value) { syncError.value = '파일을 선택해주세요.'; syncing.value = false; return }
      data = (await eventsApi.syncEventsFromFile(evtFile.value, evtYear.value, evtStartMonth.value, evtEndMonth.value)).data
    }
    const errors = data.errors || []
    syncMsg.value = `이벤트 수집 완료: ${data.processed}개 지점, ${data.total_items?.toLocaleString()}건` + (errors.length ? ` (오류 ${errors.length}건)` : '')
  } catch (e: any) { syncError.value = e.response?.data?.detail || '이벤트 동기화 실패' }
  finally { syncing.value = false }
}

function onEvtFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  evtFile.value = target.files?.[0] || null
}

// 카페
const cafeBranch = ref('')
const cafeSheetUrl = ref('')

async function syncCafe() {
  syncing.value = true; syncMsg.value = ''; syncError.value = ''
  try {
    const now = new Date()
    const { data } = await cafeApi.syncCafe(now.getFullYear(), now.getMonth() + 1, cafeBranch.value, cafeSheetUrl.value)
    const errors = data.errors || []
    syncMsg.value = `카페 원고 완료: ${data.processed}개 지점, ${data.total_articles}건` + (errors.length ? ` (오류 ${errors.length}건)` : '')
  } catch (e: any) {
    const detail = e.response?.data?.detail
    const status = e.response?.status
    if (detail) {
      syncError.value = `카페 동기화 실패 (${status}): ${detail}`
    } else if (e.code === 'ECONNABORTED') {
      syncError.value = '카페 동기화 실패: 요청 시간 초과 (30초). 다시 시도해주세요.'
    } else if (!e.response) {
      syncError.value = '카페 동기화 실패: 서버에 연결할 수 없습니다.'
    } else {
      syncError.value = `카페 동기화 실패 (${status}): 알 수 없는 오류`
    }
  }
  finally { syncing.value = false }
}

// ── 시술사전 관리 ──
const deviceMsg = ref('')
const deviceSyncing = ref(false)

async function updateDeviceCounts() {
  deviceSyncing.value = true; deviceMsg.value = ''
  try {
    await equipApi.updateDeviceCounts()
    deviceMsg.value = '보유수 업데이트 완료'
    setTimeout(() => deviceMsg.value = '', 3000)
  } catch (e: any) { deviceMsg.value = '오류: ' + (e.response?.data?.detail || e.message) }
  finally { deviceSyncing.value = false }
}

async function syncDeviceJson() {
  deviceSyncing.value = true; deviceMsg.value = ''
  try {
    await equipApi.syncDeviceJson()
    deviceMsg.value = 'JSON → DB 동기화 완료'
    setTimeout(() => deviceMsg.value = '', 3000)
  } catch (e: any) { deviceMsg.value = '오류: ' + (e.response?.data?.detail || e.message) }
  finally { deviceSyncing.value = false }
}

// ── DB 파일 관리 ──
const dbUploading = ref(false)
const dbMsg = ref('')
const dbResult = ref<any>(null)

async function uploadDb(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files?.length) return
  const file = input.files[0]

  dbUploading.value = true
  dbMsg.value = ''
  dbResult.value = null

  try {
    const formData = new FormData()
    formData.append('file', file)
    const res = await equipApi.uploadDb(formData)
    dbResult.value = res.data
    dbMsg.value = `DB 업로드 완료 (시술사전: ${res.data.device_info_count}건, 논문: ${res.data.papers_count}건)`
  } catch (e: any) {
    dbMsg.value = '오류: ' + (e.response?.data?.detail || e.message)
  } finally {
    dbUploading.value = false
    input.value = ''
  }
}

async function downloadDb() {
  try {
    const res = await equipApi.downloadDb()
    const blob = new Blob([res.data])
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'equipment.db'
    a.click()
    URL.revokeObjectURL(url)
  } catch (e: any) {
    dbMsg.value = '다운로드 오류: ' + (e.response?.data?.detail || e.message)
  }
}

// ── Google 인증 파일 ──
const credUploading = ref(false)
const credMsg = ref('')

async function uploadCred(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files?.length) return
  credUploading.value = true
  credMsg.value = ''
  try {
    const formData = new FormData()
    formData.append('file', input.files[0])
    const res = await equipApi.uploadCredentials(formData)
    credMsg.value = `업로드 완료: ${res.data.client_email} (${res.data.project_id})`
  } catch (e: any) {
    credMsg.value = '오류: ' + (e.response?.data?.detail || e.message)
  } finally {
    credUploading.value = false
    input.value = ''
  }
}

// ── 논문 폴더 분석 ──
const paperFolderPath = ref('')
const paperApiKey = ref('')
const paperDryRun = ref(false)
const paperScanning = ref(false)
const paperScanResult = ref<{ pdf_count: number; files: string[]; has_more: boolean } | null>(null)
const paperAnalyzing = ref(false)
const paperAnalyzeResult = ref<any>(null)
const paperError = ref('')

async function scanPaperFolder() {
  if (!paperFolderPath.value.trim()) return
  paperScanning.value = true
  paperScanResult.value = null
  paperAnalyzeResult.value = null
  paperError.value = ''
  try {
    const { data } = await papersApi.scanFolder(paperFolderPath.value.trim())
    paperScanResult.value = data
  } catch (e: any) {
    paperError.value = e.response?.data?.detail || '폴더 스캔 실패'
  } finally {
    paperScanning.value = false
  }
}

async function runPaperAnalysis() {
  if (!paperFolderPath.value.trim() || !paperApiKey.value.trim()) return
  paperAnalyzing.value = true
  paperAnalyzeResult.value = null
  paperError.value = ''
  try {
    const { data } = await papersApi.analyzeDir(paperFolderPath.value.trim(), paperApiKey.value.trim(), paperDryRun.value)
    paperAnalyzeResult.value = data
  } catch (e: any) {
    paperError.value = e.response?.data?.detail || '분석 실행 실패'
  } finally {
    paperAnalyzing.value = false
  }
}

</script>

<template>
  <div class="p-5">
    <h2 class="text-xl font-bold text-slate-800 mb-4">관리자 모드</h2>

    <!-- 서브 탭 -->
    <div class="flex gap-4 mb-5 border-b border-slate-200">
      <button v-for="tab in [
        { key: 'users', label: '사용자' },
        { key: 'sync', label: '데이터 동기화' },
        { key: 'device', label: '시술정보 관리' },
      ]" :key="tab.key"
        @click="activeTab = tab.key as any"
        :class="['pb-2 text-sm font-medium border-b-2 transition',
          activeTab === tab.key ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-400 hover:text-slate-600']"
      >{{ tab.label }}</button>
    </div>

    <!-- ========== 사용자 탭 ========== -->
    <div v-if="activeTab === 'users'">
      <div class="flex justify-end mb-3">
        <button @click="showForm = !showForm" class="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700">
          {{ showForm ? '취소' : '+ 사용자 추가' }}
        </button>
      </div>

      <!-- 새 사용자 폼 -->
      <div v-if="showForm" class="bg-white border border-slate-200 rounded-lg p-4 mb-4">
        <div class="grid grid-cols-5 gap-3">
          <input v-model="newUsername" placeholder="사용자 ID" class="px-3 py-1.5 border border-slate-300 rounded text-sm" />
          <input v-model="newPassword" type="password" placeholder="비밀번호" class="px-3 py-1.5 border border-slate-300 rounded text-sm" />
          <select v-model="newRole" class="px-3 py-1.5 border border-slate-300 rounded text-sm">
            <option v-for="r in roles" :key="r.value" :value="r.value">{{ r.label }}</option>
          </select>
          <select v-model="newBranchId" class="px-3 py-1.5 border border-slate-300 rounded text-sm">
            <option :value="null">지점 없음</option>
            <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.name }}</option>
          </select>
          <button @click="handleCreate" class="px-3 py-1.5 bg-emerald-600 text-white text-sm rounded hover:bg-emerald-700">생성</button>
        </div>
        <p v-if="formError" class="text-red-500 text-xs mt-2">{{ formError }}</p>
      </div>

      <!-- 사용자 테이블 -->
      <div class="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="text-left px-4 py-2 font-medium text-slate-500">ID</th>
              <th class="text-left px-4 py-2 font-medium text-slate-500">역할</th>
              <th class="text-left px-4 py-2 font-medium text-slate-500">지점</th>
              <th class="text-left px-4 py-2 font-medium text-slate-500">메모</th>
              <th class="text-right px-4 py-2 font-medium text-slate-500">작업</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.username" class="border-b border-slate-100 hover:bg-slate-50">
              <template v-if="editingUser !== user.username">
                <td class="px-4 py-2 font-medium">{{ user.username }}</td>
                <td class="px-4 py-2">
                  <span class="px-2 py-0.5 rounded text-xs font-medium"
                    :class="{ 'bg-slate-100 text-slate-600': user.role === 'viewer', 'bg-blue-100 text-blue-700': user.role === 'branch', 'bg-amber-100 text-amber-700': user.role === 'editor', 'bg-red-100 text-red-700': user.role === 'admin' }">
                    {{ roles.find(r => r.value === user.role)?.label || user.role }}
                  </span>
                </td>
                <td class="px-4 py-2 text-sm text-slate-600">{{ user.branch_id ? branchMap.get(user.branch_id) || '-' : '-' }}</td>
                <td class="px-4 py-2 text-slate-400">{{ user.memo || '-' }}</td>
                <td class="px-4 py-2 text-right space-x-2">
                  <button @click="startEdit(user)" class="text-blue-500 hover:text-blue-700 text-xs">수정</button>
                  <button v-if="user.username !== auth.username" @click="handleDelete(user.username)" class="text-red-400 hover:text-red-600 text-xs">삭제</button>
                </td>
              </template>
              <template v-else>
                <td class="px-4 py-2 font-medium">{{ user.username }}</td>
                <td class="px-4 py-2">
                  <select v-model="editRole" class="px-2 py-1 border border-slate-300 rounded text-xs">
                    <option v-for="r in roles" :key="r.value" :value="r.value">{{ r.label }}</option>
                  </select>
                </td>
                <td class="px-4 py-2">
                  <select v-model="editBranchId" class="px-2 py-1 border border-slate-300 rounded text-xs">
                    <option :value="null">없음</option>
                    <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.name }}</option>
                  </select>
                </td>
                <td class="px-4 py-2">
                  <div class="flex gap-2">
                    <input v-model="editPassword" type="password" placeholder="새 비밀번호" class="flex-1 px-2 py-1 border border-slate-300 rounded text-xs" />
                    <input v-model="editMemo" placeholder="메모" class="flex-1 px-2 py-1 border border-slate-300 rounded text-xs" />
                  </div>
                </td>
                <td class="px-4 py-2 text-right space-x-2">
                  <button @click="handleUpdate" class="text-emerald-500 text-xs">저장</button>
                  <button @click="editingUser = null" class="text-slate-400 text-xs">취소</button>
                </td>
              </template>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ========== 동기화 탭 ========== -->
    <div v-if="activeTab === 'sync'" class="space-y-6">
      <!-- 알림 -->
      <div v-if="syncMsg" class="px-4 py-2 bg-emerald-50 border border-emerald-200 rounded text-sm text-emerald-700">{{ syncMsg }}</div>
      <div v-if="syncError" class="px-4 py-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">{{ syncError }}</div>

      <!-- 장비 동기화 -->
      <div class="bg-white border border-slate-200 rounded-lg p-4">
        <h3 class="text-sm font-bold text-slate-700 mb-2">장비 데이터 동기화</h3>
        <p class="text-xs text-slate-400 mb-3">Google Sheets에서 최신 장비 데이터를 가져옵니다.</p>
        <button @click="syncEquipment" :disabled="syncing"
          class="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50">
          {{ syncing ? '동기화 중...' : '장비 시트 동기화' }}
        </button>
      </div>

      <!-- 이벤트 동기화 -->
      <div class="bg-white border border-slate-200 rounded-lg p-4">
        <h3 class="text-sm font-bold text-slate-700 mb-2">이벤트 데이터 동기화</h3>
        <p class="text-xs text-slate-400 mb-3">수집 기간: <strong>{{ evtYear }}년 {{ evtStartMonth }}-{{ evtEndMonth }}월</strong></p>

        <div class="flex gap-3 mb-3">
          <label class="flex items-center gap-1 text-sm">
            <input type="radio" v-model="evtSyncMethod" value="url" /> 링크 입력
          </label>
          <label class="flex items-center gap-1 text-sm">
            <input type="radio" v-model="evtSyncMethod" value="file" /> 파일 업로드
          </label>
        </div>

        <div v-if="evtSyncMethod === 'url'" class="space-y-2">
          <input v-model="evtSheetUrl" placeholder="https://docs.google.com/spreadsheets/d/..."
            class="w-full px-3 py-1.5 border border-slate-300 rounded text-sm" />
          <p class="text-xs text-slate-400">시트가 '링크가 있는 모든 사용자에게 공개'로 설정되어야 합니다.</p>
        </div>
        <div v-else class="space-y-2">
          <input type="file" accept=".xlsx,.xls" @change="onEvtFileChange"
            class="text-sm text-slate-500 file:mr-2 file:py-1 file:px-3 file:rounded file:border-0 file:bg-slate-100 file:text-sm file:text-slate-600" />
          <p class="text-xs text-slate-400">각 시트 탭 이름이 지점명(예: 강남, 잠실)이어야 합니다.</p>
        </div>

        <button @click="syncEvents" :disabled="syncing"
          class="mt-3 px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50">
          {{ syncing ? '수집 중...' : '이벤트 수집 실행' }}
        </button>
      </div>

      <!-- 카페 동기화 -->
      <div class="bg-white border border-slate-200 rounded-lg p-4">
        <h3 class="text-sm font-bold text-slate-700 mb-2">카페 원고 가져오기</h3>
        <div class="grid grid-cols-2 gap-3 mb-3">
          <div>
            <label class="text-xs text-slate-500">시트 링크</label>
            <input v-model="cafeSheetUrl" placeholder="Google Sheets URL" class="w-full px-3 py-1.5 border border-slate-300 rounded text-sm" />
          </div>
          <div>
            <label class="text-xs text-slate-500">지점</label>
            <select v-model="cafeBranch" class="w-full px-3 py-1.5 border border-slate-300 rounded text-sm">
              <option value="">전체 지점</option>
              <option v-for="b in branches" :key="b.id" :value="b.name">{{ b.name }}</option>
            </select>
          </div>
        </div>
        <button @click="syncCafe" :disabled="syncing"
          class="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50">
          {{ syncing ? '가져오는 중...' : '카페 원고 가져오기' }}
        </button>
      </div>

      <!-- DB 파일 관리 -->
      <div class="bg-white border border-slate-200 rounded-lg p-4">
        <h3 class="text-sm font-bold text-slate-700 mb-1">DB 파일 관리</h3>
        <p class="text-xs text-slate-400 mb-3">로컬 DB에서 <strong>시술사전·논문</strong>만 서버에 병합합니다. 카페 원고·이벤트·사용자 데이터는 유지됩니다.</p>

        <div v-if="dbMsg" class="mb-3 px-3 py-2 rounded text-sm"
          :class="dbMsg.startsWith('오류') ? 'bg-red-50 border border-red-200 text-red-700' : 'bg-emerald-50 border border-emerald-200 text-emerald-700'">
          {{ dbMsg }}
        </div>

        <div v-if="dbResult" class="mb-3 p-3 bg-slate-50 border border-slate-200 rounded text-xs text-slate-600">
          <p class="font-semibold text-slate-700 mb-1">{{ dbResult.message }}</p>
          <p>시술사전: {{ dbResult.device_info_count }}건 / 논문: {{ dbResult.papers_count }}건</p>
          <p>카페 원고: {{ dbResult.cafe_articles_count }}건 (기존 유지)</p>
        </div>

        <div class="flex gap-3">
          <label class="px-4 py-2 bg-blue-600 text-white text-sm rounded cursor-pointer hover:bg-blue-700"
            :class="{ 'opacity-50 pointer-events-none': dbUploading }">
            {{ dbUploading ? '업로드 중...' : 'DB 업로드' }}
            <input type="file" accept=".db" class="hidden" @change="uploadDb" :disabled="dbUploading" />
          </label>
          <button @click="downloadDb"
            class="px-4 py-2 bg-slate-600 text-white text-sm rounded hover:bg-slate-700">
            DB 다운로드 (백업)
          </button>
        </div>
      </div>

      <!-- Google 인증 파일 관리 -->
      <div class="bg-white border border-slate-200 rounded-lg p-5">
        <h3 class="text-sm font-semibold text-slate-700 mb-1">Google 인증 파일</h3>
        <p class="text-xs text-slate-400 mb-3">카페/이벤트 시트 동기화에 필요한 Google 서비스 계정 파일입니다.</p>

        <div v-if="credMsg" class="px-3 py-2 rounded text-xs mb-3"
          :class="credMsg.startsWith('오류') ? 'bg-red-50 border border-red-200 text-red-700' : 'bg-emerald-50 border border-emerald-200 text-emerald-700'">
          {{ credMsg }}
        </div>

        <label class="px-4 py-2 bg-amber-600 text-white text-sm rounded cursor-pointer hover:bg-amber-700"
          :class="{ 'opacity-50 pointer-events-none': credUploading }">
          {{ credUploading ? '업로드 중...' : 'credentials.json 업로드' }}
          <input type="file" accept=".json" class="hidden" @change="uploadCred" :disabled="credUploading" />
        </label>
      </div>
    </div>

    <!-- ========== 시술사전 관리 탭 ========== -->
    <div v-if="activeTab === 'device'" class="space-y-6">
      <div v-if="deviceMsg" class="px-4 py-2 rounded text-sm"
        :class="deviceMsg.startsWith('오류') ? 'bg-red-50 border border-red-200 text-red-700' : 'bg-emerald-50 border border-emerald-200 text-emerald-700'">
        {{ deviceMsg }}
      </div>

      <div class="bg-white border border-slate-200 rounded-lg p-4">
        <h3 class="text-sm font-bold text-slate-700 mb-2">보유수 업데이트</h3>
        <p class="text-xs text-slate-400 mb-3">장비 테이블 기준으로 각 시술의 보유 지점 수를 재계산합니다.</p>
        <button @click="updateDeviceCounts" :disabled="deviceSyncing"
          class="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50">
          {{ deviceSyncing ? '처리 중...' : '보유수 업데이트' }}
        </button>
      </div>

      <div class="bg-white border border-slate-200 rounded-lg p-4">
        <h3 class="text-sm font-bold text-slate-700 mb-2">JSON → DB 동기화</h3>
        <p class="text-xs text-slate-400 mb-3">device_info.json 파일의 시술 정보를 DB에 반영합니다.</p>
        <button @click="syncDeviceJson" :disabled="deviceSyncing"
          class="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50">
          {{ deviceSyncing ? '동기화 중...' : 'JSON → DB 동기화' }}
        </button>
      </div>

      <!-- 논문 폴더 분석 -->
      <div class="bg-white border border-slate-200 rounded-lg p-4">
        <h3 class="text-sm font-bold text-slate-700 mb-1">🔬 논문 폴더 분석</h3>
        <p class="text-xs text-slate-400 mb-3">로컬 폴더의 논문 PDF를 Claude API로 일괄 분석하여 DB에 저장합니다.</p>

        <!-- 폴더 경로 -->
        <div class="flex gap-2 mb-3">
          <input v-model="paperFolderPath" placeholder="논문 PDF 폴더 경로 (예: Z:\...\00_리프팅시술)"
            class="flex-1 px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-emerald-400"
            @keyup.enter="scanPaperFolder" />
          <button @click="scanPaperFolder" :disabled="!paperFolderPath.trim() || paperScanning"
            class="px-4 py-2 bg-slate-600 text-white text-xs font-medium rounded-md hover:bg-slate-700 disabled:opacity-50 shrink-0">
            {{ paperScanning ? '확인 중...' : '폴더 확인' }}
          </button>
        </div>

        <!-- 스캔 결과 -->
        <div v-if="paperScanResult" class="mb-3 p-3 bg-slate-50 border border-slate-200 rounded-lg">
          <p class="text-sm font-medium text-slate-700 mb-1">📁 PDF {{ paperScanResult.pdf_count }}건 발견</p>
          <div class="max-h-24 overflow-auto text-xs text-slate-500 space-y-0.5">
            <p v-for="f in paperScanResult.files" :key="f" class="truncate">· {{ f }}</p>
            <p v-if="paperScanResult.has_more" class="text-slate-400 italic">...외 {{ paperScanResult.pdf_count - 50 }}건</p>
          </div>
        </div>

        <!-- API 키 + 실행 -->
        <div v-if="paperScanResult && paperScanResult.pdf_count > 0">
          <input v-model="paperApiKey" type="password" placeholder="Anthropic API Key (sk-ant-api03-...)"
            class="w-full px-3 py-2 border border-slate-300 rounded-md text-sm mb-2 focus:outline-none focus:ring-1 focus:ring-emerald-400" />
          <div class="flex items-center gap-3 mb-3">
            <label class="flex items-center gap-1.5 text-xs text-slate-500 cursor-pointer">
              <input type="checkbox" v-model="paperDryRun" class="rounded" />
              테스트 모드 (DB 저장 안 함)
            </label>
            <span class="text-xs text-slate-400">
              예상: {{ Math.ceil(paperScanResult.pdf_count * 0.7) }}~{{ paperScanResult.pdf_count }}분
            </span>
          </div>
          <button @click="runPaperAnalysis" :disabled="!paperApiKey.trim() || paperAnalyzing"
            class="px-4 py-2 bg-emerald-600 text-white text-sm rounded hover:bg-emerald-700 disabled:opacity-50">
            <template v-if="paperAnalyzing">
              <span class="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin mr-1.5 align-middle"></span>
              분석 중... (창을 닫지 마세요)
            </template>
            <template v-else>🔬 {{ paperScanResult.pdf_count }}건 분석 시작</template>
          </button>
        </div>

        <!-- 에러/결과 -->
        <div v-if="paperError" class="mt-3 px-3 py-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">{{ paperError }}</div>
        <div v-if="paperAnalyzeResult" class="mt-3 p-3 rounded border"
          :class="paperAnalyzeResult.success ? 'bg-emerald-50 border-emerald-200' : 'bg-amber-50 border-amber-200'">
          <p class="text-sm font-bold mb-1" :class="paperAnalyzeResult.success ? 'text-emerald-700' : 'text-amber-700'">
            {{ paperAnalyzeResult.success ? '✅ 분석 완료' : '⚠️ 일부 오류' }}
          </p>
          <p class="text-xs text-slate-600">대상: {{ paperAnalyzeResult.pdf_count }}건 / 성공: {{ paperAnalyzeResult.analyzed }}건</p>
          <div v-if="paperAnalyzeResult.summary.length" class="mt-2 p-2 bg-white/50 rounded text-xs font-mono">
            <p v-for="(line, i) in paperAnalyzeResult.summary" :key="i">{{ line }}</p>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>
