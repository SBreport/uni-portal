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

// 폴더 탐색기
const showFolderBrowser = ref(false)
const folderBrowsing = ref(false)
const folderDirs = ref<{ name: string; path: string; pdf_count: number }[]>([])
const folderParent = ref('')
const folderBrowserError = ref('')

// 자주 쓰는 논문 폴더 경로 (사전 등록)
const presetFolders = [
  { label: '전체 논문', path: 'Z:\\NAS\\논문' },
  { label: '리프팅', path: 'Z:\\NAS\\논문\\00_리프팅시술' },
  { label: '필러', path: 'Z:\\NAS\\논문\\01_필러' },
  { label: '보톡스', path: 'Z:\\NAS\\논문\\02_보톡스' },
  { label: '레이저', path: 'Z:\\NAS\\논문\\03_레이저' },
  { label: '스킨부스터', path: 'Z:\\NAS\\논문\\04_스킨부스터' },
]

function selectPresetFolder(path: string) {
  paperFolderPath.value = path
  paperScanResult.value = null
  paperAnalyzeResult.value = null
  paperError.value = ''
}

async function browseFolders(path?: string) {
  const target = path || paperFolderPath.value.trim()
  if (!target) return
  folderBrowsing.value = true
  folderBrowserError.value = ''
  try {
    const { data } = await papersApi.listDirs(target)
    folderDirs.value = data.dirs
    folderParent.value = data.parent
    showFolderBrowser.value = true
    if (data.pdf_count > 0 && !path) {
      // 현재 폴더에 PDF가 있으면 스캔도 실행
      paperFolderPath.value = target
    }
  } catch (e: any) {
    folderBrowserError.value = e.response?.data?.detail || '폴더 탐색 실패'
  } finally {
    folderBrowsing.value = false
  }
}

function selectBrowserFolder(dir: { name: string; path: string; pdf_count: number }) {
  paperFolderPath.value = dir.path
  paperScanResult.value = null
  paperAnalyzeResult.value = null
  showFolderBrowser.value = false
  scanPaperFolder()
}

function navigateUp() {
  const parent = folderParent.value
  const upPath = parent.substring(0, parent.lastIndexOf('\\')) || parent.substring(0, parent.lastIndexOf('/'))
  if (upPath && upPath !== parent) {
    browseFolders(upPath)
  }
}

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

      <!-- ① 구글 시트 동기화 -->
      <div class="bg-white border border-slate-200 rounded-lg p-4">
        <div class="flex items-center justify-between mb-3">
          <div>
            <h3 class="text-sm font-bold text-slate-700">구글 장비시트 데이터 동기화</h3>
            <p class="text-xs text-slate-400 mt-0.5">Google Sheets에서 보유장비 데이터를 가져옵니다.</p>
          </div>
          <button @click="syncEquipment" :disabled="syncing"
            class="px-4 py-1.5 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap">
            {{ syncing ? '동기화 중...' : '장비 동기화' }}
          </button>
        </div>
      </div>

      <!-- ② 이벤트 동기화 -->
      <div class="bg-white border border-slate-200 rounded-lg p-4">
        <div class="flex items-center justify-between mb-2">
          <div>
            <h3 class="text-sm font-bold text-slate-700">유앤아이 지점별 이벤트 데이터 동기화</h3>
            <p class="text-xs text-slate-400 mt-0.5">마지막 갱신: <strong>{{ evtYear }}년 {{ evtStartMonth }}-{{ evtEndMonth }}월</strong></p>
          </div>
          <button @click="syncEvents" :disabled="syncing"
            class="px-4 py-1.5 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap">
            {{ syncing ? '수집 중...' : '이벤트 수집' }}
          </button>
        </div>
        <div class="flex gap-3 items-center text-xs">
          <label class="flex items-center gap-1">
            <input type="radio" v-model="evtSyncMethod" value="url" /> 링크
          </label>
          <label class="flex items-center gap-1">
            <input type="radio" v-model="evtSyncMethod" value="file" /> 파일
          </label>
          <input v-if="evtSyncMethod === 'url'" v-model="evtSheetUrl" placeholder="Google Sheets URL"
            class="flex-1 px-2 py-1 border border-slate-300 rounded text-xs" />
          <input v-else type="file" accept=".xlsx,.xls" @change="onEvtFileChange"
            class="flex-1 text-xs text-slate-500 file:mr-2 file:py-0.5 file:px-2 file:rounded file:border-0 file:bg-slate-100 file:text-xs" />
        </div>
      </div>

      <!-- ③ 카페 원고 -->
      <div class="bg-white border border-slate-200 rounded-lg p-4">
        <div class="flex items-center justify-between mb-2">
          <h3 class="text-sm font-bold text-slate-700">카페 원고 가져오기</h3>
          <button @click="syncCafe" :disabled="syncing"
            class="px-4 py-1.5 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap">
            {{ syncing ? '가져오는 중...' : '원고 가져오기' }}
          </button>
        </div>
        <div class="flex gap-3 items-center text-xs">
          <input v-model="cafeSheetUrl" placeholder="Google Sheets URL" class="flex-1 px-2 py-1 border border-slate-300 rounded text-xs" />
          <select v-model="cafeBranch" class="px-2 py-1 border border-slate-300 rounded text-xs">
            <option value="">전체 지점</option>
            <option v-for="b in branches" :key="b.id" :value="b.name">{{ b.name }}</option>
          </select>
        </div>
      </div>

      <!-- ④ 시술사전 & 논문 DB 관리 -->
      <div class="bg-white border border-slate-200 rounded-lg p-4">
        <div class="flex items-center justify-between mb-2">
          <div>
            <h3 class="text-sm font-bold text-slate-700">시술사전 · 논문 DB 관리</h3>
            <p class="text-xs text-slate-400 mt-0.5">로컬에서 작업한 시술사전(device_info)과 논문(papers) 데이터를 서버 DB에 병합합니다. 장비·이벤트·카페 등 기존 데이터는 유지됩니다.</p>
          </div>
        </div>

        <div v-if="dbMsg" class="mb-2 px-3 py-1.5 rounded text-xs"
          :class="dbMsg.startsWith('오류') ? 'bg-red-50 border border-red-200 text-red-700' : 'bg-emerald-50 border border-emerald-200 text-emerald-700'">
          {{ dbMsg }}
        </div>

        <div v-if="dbResult" class="mb-2 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded text-xs text-slate-600">
          <span class="font-semibold text-slate-700">{{ dbResult.message }}</span>
          <span class="ml-2">시술사전 {{ dbResult.device_info_count }}건 · 논문 {{ dbResult.papers_count }}건</span>
        </div>

        <div class="flex gap-2">
          <label class="px-3 py-1.5 bg-blue-600 text-white text-xs rounded cursor-pointer hover:bg-blue-700"
            :class="{ 'opacity-50 pointer-events-none': dbUploading }">
            {{ dbUploading ? '업로드 중...' : 'DB 업로드' }}
            <input type="file" accept=".db" class="hidden" @change="uploadDb" :disabled="dbUploading" />
          </label>
          <button @click="downloadDb"
            class="px-3 py-1.5 bg-slate-500 text-white text-xs rounded hover:bg-slate-600">
            DB 다운로드
          </button>
        </div>
      </div>

      <!-- ⑤ Google 인증 -->
      <div class="bg-white border border-slate-200 rounded-lg p-4">
        <div class="flex items-center justify-between">
          <div>
            <h3 class="text-sm font-bold text-slate-700">Google 인증 파일</h3>
            <p class="text-xs text-slate-400 mt-0.5">장비·이벤트·카페 시트 동기화에 필요합니다. 최초 1회 업로드하면 이후 자동 적용됩니다.</p>
          </div>
          <label class="px-3 py-1.5 bg-amber-600 text-white text-xs rounded cursor-pointer hover:bg-amber-700 whitespace-nowrap"
            :class="{ 'opacity-50 pointer-events-none': credUploading }">
            {{ credUploading ? '업로드 중...' : 'credentials.json 업로드' }}
            <input type="file" accept=".json" class="hidden" @change="uploadCred" :disabled="credUploading" />
          </label>
        </div>
        <div v-if="credMsg" class="mt-2 px-3 py-1.5 rounded text-xs"
          :class="credMsg.startsWith('오류') ? 'bg-red-50 border border-red-200 text-red-700' : 'bg-emerald-50 border border-emerald-200 text-emerald-700'">
          {{ credMsg }}
        </div>
      </div>
    </div>

    <!-- 시술사전 관리 탭 제거됨 — DB 업로드/다운로드는 동기화 탭에서 처리 -->

  </div>
</template>
