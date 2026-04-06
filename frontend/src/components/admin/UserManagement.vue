<script setup lang="ts">
import { ref, onMounted, computed, h } from 'vue'
import * as usersApi from '@/api/users'
import { useAuthStore } from '@/stores/auth'
import DataTable from '@/components/common/DataTable.vue'
import { createColumnHelper } from '@tanstack/vue-table'

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

const roleBadgeClass: Record<string, string> = {
  viewer: 'bg-slate-100 text-slate-600',
  branch: 'bg-blue-100 text-blue-700',
  editor: 'bg-amber-100 text-amber-700',
  admin:  'bg-red-100 text-red-700',
}

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
function startEdit(user: User) {
  editingUser.value = user.username
  editRole.value = user.role
  editPassword.value = ''
  editMemo.value = user.memo || ''
  editBranchId.value = user.branch_id
}
async function handleUpdate() {
  if (!editingUser.value) return
  const u: Record<string, any> = {}
  if (editRole.value) u.role = editRole.value
  if (editPassword.value) u.password = editPassword.value
  if (editMemo.value !== undefined) u.memo = editMemo.value
  u.branch_id = editBranchId.value
  await usersApi.updateUser(editingUser.value, u); editingUser.value = null; await loadUsers()
}

// ── Column definitions ────────────────────────────────────────────
const col = createColumnHelper<User>()

const columns = computed(() => [
  col.accessor('username', {
    header: 'ID',
    size: 112,
    cell: (info) => h('span', { class: 'font-medium' }, info.getValue()),
  }),

  col.accessor('role', {
    header: '역할',
    size: 80,
    cell: (info) => {
      const user = info.row.original
      if (editingUser.value === user.username) {
        return h('select', {
          value: editRole.value,
          onChange: (e: Event) => { editRole.value = (e.target as HTMLSelectElement).value },
          class: 'px-2 py-1 border border-slate-300 rounded text-xs',
        }, roles.map(r => h('option', { value: r.value, selected: editRole.value === r.value }, r.label)))
      }
      const label = roles.find(r => r.value === info.getValue())?.label || info.getValue()
      return h('span', {
        class: `px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap ${roleBadgeClass[info.getValue()] || 'bg-slate-100 text-slate-600'}`,
      }, label)
    },
  }),

  col.accessor('branch_id', {
    header: '지점',
    size: 112,
    cell: (info) => {
      const user = info.row.original
      if (editingUser.value === user.username) {
        return h('select', {
          value: editBranchId.value ?? '',
          onChange: (e: Event) => {
            const v = (e.target as HTMLSelectElement).value
            editBranchId.value = v === '' ? null : Number(v)
          },
          class: 'px-2 py-1 border border-slate-300 rounded text-xs',
        }, [
          h('option', { value: '' }, '없음'),
          ...props.branches.map(b => h('option', { value: b.id, selected: editBranchId.value === b.id }, b.name)),
        ])
      }
      const bid = info.getValue()
      return h('span', { class: 'text-sm text-slate-600' }, bid ? (branchMap.value.get(bid) || '-') : '-')
    },
  }),

  col.accessor('memo', {
    header: '메모',
    cell: (info) => {
      const user = info.row.original
      if (editingUser.value === user.username) {
        return h('div', { class: 'flex gap-2' }, [
          h('input', {
            type: 'password',
            value: editPassword.value,
            placeholder: '새 비밀번호',
            onInput: (e: Event) => { editPassword.value = (e.target as HTMLInputElement).value },
            class: 'flex-1 px-2 py-1 border border-slate-300 rounded text-xs',
          }),
          h('input', {
            value: editMemo.value,
            placeholder: '메모',
            onInput: (e: Event) => { editMemo.value = (e.target as HTMLInputElement).value },
            class: 'flex-1 px-2 py-1 border border-slate-300 rounded text-xs',
          }),
        ])
      }
      return h('span', { class: 'text-slate-400' }, info.getValue() || '-')
    },
  }),

  col.display({
    id: 'actions',
    header: '작업',
    size: 96,
    cell: (info) => {
      const user = info.row.original
      if (editingUser.value === user.username) {
        return h('div', { class: 'flex justify-end gap-2' }, [
          h('button', {
            onClick: (e: MouseEvent) => { e.stopPropagation(); handleUpdate() },
            class: 'text-emerald-500 text-xs',
          }, '저장'),
          h('button', {
            onClick: (e: MouseEvent) => { e.stopPropagation(); editingUser.value = null },
            class: 'text-slate-400 text-xs',
          }, '취소'),
        ])
      }
      return h('div', { class: 'flex justify-end gap-2' }, [
        h('button', {
          onClick: (e: MouseEvent) => { e.stopPropagation(); startEdit(user) },
          class: 'text-blue-500 hover:text-blue-700 text-xs',
        }, '수정'),
        ...(user.username !== auth.username
          ? [h('button', {
              onClick: (e: MouseEvent) => { e.stopPropagation(); handleDelete(user.username) },
              class: 'text-red-400 hover:text-red-600 text-xs',
            }, '삭제')]
          : []),
      ])
    },
  }),
])
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

    <div class="max-w-3xl">
      <DataTable
        :data="users"
        :columns="columns"
        :page-size="50"
        height="600px"
        :searchable="false"
      />
    </div>
  </div>
</template>
