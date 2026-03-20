<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import * as usersApi from '@/api/users'
import * as equipApi from '@/api/equipment'
import * as eventsApi from '@/api/events'
import * as cafeApi from '@/api/cafe'
// equipApi는 동기화 탭(장비시트 동기화)에서 사용
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

// ── 탭 ──
const activeTab = ref<'users' | 'sync'>('users')

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

const roles = [
  { value: 'viewer', label: '뷰어' },
  { value: 'branch', label: '지점담당' },
  { value: 'editor', label: '편집자' },
  { value: 'admin', label: '관리자' },
]

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
function startEdit(user: User) { editingUser.value = user.username; editRole.value = user.role; editPassword.value = ''; editMemo.value = user.memo || '' }
async function handleUpdate() {
  if (!editingUser.value) return
  const u: Record<string, string> = {}
  if (editRole.value) u.role = editRole.value
  if (editPassword.value) u.password = editPassword.value
  if (editMemo.value !== undefined) u.memo = editMemo.value
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
const cafeYear = ref(now.getFullYear())
const cafeMonth = ref(now.getMonth() + 1)
const cafeBranch = ref('동탄점')
const cafeSheetUrl = ref('')

async function syncCafe() {
  syncing.value = true; syncMsg.value = ''; syncError.value = ''
  try {
    if (cafeSheetUrl.value) {
      const match = cafeSheetUrl.value.match(/\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/)
      // URL에서 ID 추출은 서버에서 처리
    }
    const { data } = await cafeApi.syncCafe(cafeYear.value, cafeMonth.value, cafeBranch.value)
    const errors = data.errors || []
    syncMsg.value = `카페 원고 완료: ${data.processed}개 지점, ${data.total_articles}건` + (errors.length ? ` (오류 ${errors.length}건)` : '')
  } catch (e: any) { syncError.value = e.response?.data?.detail || '카페 동기화 실패' }
  finally { syncing.value = false }
}

</script>

<template>
  <div class="p-5">
    <h2 class="text-xl font-bold text-slate-800 mb-4">사용자 관리</h2>

    <!-- 서브 탭 -->
    <div class="flex gap-4 mb-5 border-b border-slate-200">
      <button v-for="tab in [
        { key: 'users', label: '사용자' },
        { key: 'sync', label: '동기화' },
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
        <div class="grid grid-cols-4 gap-3 mb-3">
          <div>
            <label class="text-xs text-slate-500">연도</label>
            <input v-model.number="cafeYear" type="number" min="2024" max="2030" class="w-full px-3 py-1.5 border border-slate-300 rounded text-sm" />
          </div>
          <div>
            <label class="text-xs text-slate-500">월</label>
            <input v-model.number="cafeMonth" type="number" min="1" max="12" class="w-full px-3 py-1.5 border border-slate-300 rounded text-sm" />
          </div>
          <div>
            <label class="text-xs text-slate-500">지점 필터</label>
            <input v-model="cafeBranch" placeholder="빈 칸이면 전체" class="w-full px-3 py-1.5 border border-slate-300 rounded text-sm" />
          </div>
          <div>
            <label class="text-xs text-slate-500">시트 URL</label>
            <input v-model="cafeSheetUrl" placeholder="Google Sheets URL" class="w-full px-3 py-1.5 border border-slate-300 rounded text-sm" />
          </div>
        </div>
        <button @click="syncCafe" :disabled="syncing"
          class="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50">
          {{ syncing ? '가져오는 중...' : '카페 원고 가져오기' }}
        </button>
      </div>
    </div>

  </div>
</template>
