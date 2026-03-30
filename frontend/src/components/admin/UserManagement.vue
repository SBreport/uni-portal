<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import * as usersApi from '@/api/users'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{ branches: { id: number; name: string }[] }>()
const auth = useAuthStore()

interface User { username: string; role: string; branch_id: number | null; memo: string }
const users = ref<User[]>([])
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

const branchMap = computed(() => {
  const m = new Map<number, string>()
  props.branches.forEach(b => m.set(b.id, b.name))
  return m
})

async function loadUsers() {
  loading.value = true
  try { users.value = (await usersApi.getUsers()).data } finally { loading.value = false }
}
onMounted(loadUsers)

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

</script>

<template>
  <div>
    <div class="max-w-3xl flex justify-end mb-3">
      <button @click="showForm = !showForm" class="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700">
        {{ showForm ? '취소' : '+ 사용자 추가' }}
      </button>
    </div>

    <div v-if="showForm" class="bg-white border border-slate-200 rounded-lg p-4 mb-4 max-w-3xl">
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

    <div class="bg-white border border-slate-200 rounded-lg overflow-hidden max-w-3xl">
      <table class="w-full text-sm">
        <thead class="bg-slate-50 border-b border-slate-200">
          <tr>
            <th class="text-left px-4 py-2 font-medium text-slate-500 w-28">ID</th>
            <th class="text-left px-4 py-2 font-medium text-slate-500 w-20">역할</th>
            <th class="text-left px-4 py-2 font-medium text-slate-500 w-28">지점</th>
            <th class="text-left px-4 py-2 font-medium text-slate-500">메모</th>
            <th class="text-right px-4 py-2 font-medium text-slate-500 w-24">작업</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.username" class="border-b border-slate-100 hover:bg-slate-50">
            <template v-if="editingUser !== user.username">
              <td class="px-4 py-2 font-medium">{{ user.username }}</td>
              <td class="px-4 py-2">
                <span class="px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap"
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
</template>
