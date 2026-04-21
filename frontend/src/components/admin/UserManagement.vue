<script setup lang="ts">
import { ref, onMounted, computed, h } from 'vue'
import * as usersApi from '@/api/users'
import { useAuthStore } from '@/stores/auth'
import DataTable from '@/components/common/DataTable.vue'
import { createColumnHelper } from '@tanstack/vue-table'

const props = defineProps<{ branches: { id: number; name: string }[] }>()
const auth = useAuthStore()

// ── 프리셋 정의 ──────────────────────────────────────────────────────
interface Preset {
  id: string
  label: string
  description: string
  role: string
  branch_id: number | null
  permissions: string[]
  requiresBranch: boolean
}

const PRESETS: Preset[] = [
  {
    id: 'admin',
    label: '관리자',
    description: '관리자 — 전체 시스템 접근 및 관리 권한',
    role: 'admin',
    branch_id: null,
    permissions: [],
    requiresBranch: false,
  },
  {
    id: 'editor_agency',
    label: '편집자(대행사)',
    description: '편집자(대행사) — 콘텐츠 편집 및 관리 권한',
    role: 'editor',
    branch_id: null,
    permissions: [],
    requiresBranch: false,
  },
  {
    id: 'editor_blog',
    label: '블로그 작가',
    description: '블로그 작가 — 블로그 원고 작성 권한',
    role: 'editor',
    branch_id: null,
    permissions: ['blog_write'],
    requiresBranch: false,
  },
  {
    id: 'editor_cafe',
    label: '카페 작가',
    description: '카페 작가 — 카페 원고 작성 권한',
    role: 'editor',
    branch_id: null,
    permissions: ['cafe_write'],
    requiresBranch: false,
  },
  {
    id: 'editor_publisher',
    label: '발행사',
    description: '발행사 — 카페 게시물 발행 권한',
    role: 'editor',
    branch_id: null,
    permissions: ['cafe_publish'],
    requiresBranch: false,
  },
  {
    id: 'viewer_hq',
    label: '본사 viewer',
    description: '본사 viewer — 전체 데이터 열람 권한',
    role: 'viewer',
    branch_id: null,
    permissions: [],
    requiresBranch: false,
  },
  {
    id: 'viewer_branch',
    label: '지점 원장 viewer',
    description: '지점 원장 viewer — 담당 지점 데이터 열람 권한 (지점 선택 필수)',
    role: 'viewer',
    branch_id: null,
    permissions: [],
    requiresBranch: true,
  },
]

// ── 프리셋 역산 헬퍼 ──────────────────────────────────────────────────
interface UserLike {
  role: string
  branch_id?: number | null
  permissions?: string[]
}

function getPresetLabel(user: UserLike): string {
  const perms = (user.permissions ?? []).slice().sort().join(',')
  const hasBranch = !!user.branch_id

  for (const preset of PRESETS) {
    const presetPerms = preset.permissions.slice().sort().join(',')
    if (preset.role !== user.role) continue
    if (preset.requiresBranch && !hasBranch) continue
    if (!preset.requiresBranch && hasBranch) continue
    if (presetPerms !== perms) continue
    return preset.label
  }
  // fallback: 매칭 안 되면 원래 role 이름
  return user.role
}

// ── User 인터페이스 ───────────────────────────────────────────────────
interface User {
  username: string
  role: string
  branch_id: number | null
  permissions: string[]
  memo: string
}

// ── 상태 ─────────────────────────────────────────────────────────────
const users = ref<User[]>([])
const loading = ref(false)
const showForm = ref(false)
const formError = ref('')

// 생성 폼 상태
const newUsername = ref('')
const newPassword = ref('')
const newPresetId = ref<string>('viewer_hq')
const newBranchId = ref<number | null>(null)
const newMemo = ref('')

// 수정 상태
const editingUser = ref<string | null>(null)
const editRole = ref('')
const editPassword = ref('')
const editMemo = ref('')
const editBranchId = ref<number | null>(null)

// ── 계산 속성 ─────────────────────────────────────────────────────────
const selectedPreset = computed<Preset | undefined>(
  () => PRESETS.find(p => p.id === newPresetId.value)
)

const isBranchRequired = computed(() => selectedPreset.value?.requiresBranch ?? false)

const branchMap = computed(() => {
  const m = new Map<number, string>()
  props.branches.forEach(b => m.set(b.id, b.name))
  return m
})

// ── 데이터 로드 ───────────────────────────────────────────────────────
async function loadUsers() {
  loading.value = true
  try {
    users.value = (await usersApi.getUsers()).data
  } finally {
    loading.value = false
  }
}
onMounted(loadUsers)

// ── 생성 ─────────────────────────────────────────────────────────────
async function handleCreate() {
  formError.value = ''
  if (!newUsername.value || !newPassword.value) {
    formError.value = 'ID와 비밀번호를 입력해주세요.'
    return
  }
  const preset = selectedPreset.value
  if (!preset) {
    formError.value = '역할을 선택해주세요.'
    return
  }
  if (preset.requiresBranch && !newBranchId.value) {
    formError.value = '지점 원장 viewer는 지점을 선택해야 합니다.'
    return
  }
  try {
    await usersApi.createUser({
      username: newUsername.value,
      password: newPassword.value,
      role: preset.role,
      branch_id: preset.requiresBranch ? newBranchId.value : null,
      permissions: preset.permissions,
      memo: newMemo.value || undefined,
    })
    showForm.value = false
    newUsername.value = ''
    newPassword.value = ''
    newPresetId.value = 'viewer_hq'
    newBranchId.value = null
    newMemo.value = ''
    await loadUsers()
  } catch (e: any) {
    formError.value = e.response?.data?.detail || '생성 실패'
  }
}

// ── 삭제 ─────────────────────────────────────────────────────────────
async function handleDelete(username: string) {
  if (username === auth.username) return
  await usersApi.deleteUser(username)
  await loadUsers()
}

// ── 수정 ─────────────────────────────────────────────────────────────
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
  await usersApi.updateUser(editingUser.value, u)
  editingUser.value = null
  await loadUsers()
}

// ── 배지 스타일 ───────────────────────────────────────────────────────
const roleBadgeClass: Record<string, string> = {
  viewer: 'bg-slate-100 text-slate-600',
  branch: 'bg-blue-100 text-blue-700',
  editor: 'bg-amber-100 text-amber-700',
  admin: 'bg-red-100 text-red-700',
}

const editRoles = [
  { value: 'viewer', label: '뷰어' },
  { value: 'branch', label: '지점담당' },
  { value: 'editor', label: '편집자' },
  { value: 'admin', label: '관리자' },
]

// ── 컬럼 정의 ─────────────────────────────────────────────────────────
const col = createColumnHelper<User>()

const columns = computed(() => [
  col.accessor('username', {
    header: 'ID',
    size: 112,
    cell: (info) => h('span', { class: 'font-medium' }, info.getValue()),
  }),

  col.accessor('role', {
    header: '역할',
    size: 140,
    cell: (info) => {
      const user = info.row.original
      if (editingUser.value === user.username) {
        return h('select', {
          value: editRole.value,
          onChange: (e: Event) => {
            editRole.value = (e.target as HTMLSelectElement).value
          },
          class: 'px-2 py-1 border border-slate-300 rounded text-xs',
        }, editRoles.map(r => h('option', { value: r.value, selected: editRole.value === r.value }, r.label)))
      }
      const label = getPresetLabel(user)
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
          ...props.branches.map(b =>
            h('option', { value: b.id, selected: editBranchId.value === b.id }, b.name)
          ),
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
      <button
        @click="showForm = !showForm"
        class="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
      >
        {{ showForm ? '취소' : '+ 사용자 추가' }}
      </button>
    </div>

    <div v-if="showForm" class="bg-white border border-slate-200 rounded-lg p-4 mb-4 max-w-3xl">
      <div class="flex flex-col gap-3">
        <!-- ID / 비밀번호 -->
        <div class="flex gap-3">
          <input
            v-model="newUsername"
            placeholder="사용자 ID"
            class="flex-1 px-3 py-1.5 border border-slate-300 rounded text-sm"
          />
          <input
            v-model="newPassword"
            type="password"
            placeholder="비밀번호"
            class="flex-1 px-3 py-1.5 border border-slate-300 rounded text-sm"
          />
        </div>

        <!-- 역할 프리셋 -->
        <div class="flex flex-col gap-1">
          <select
            v-model="newPresetId"
            class="w-full px-3 py-1.5 border border-slate-300 rounded text-sm"
          >
            <option v-for="p in PRESETS" :key="p.id" :value="p.id">{{ p.label }}</option>
          </select>
          <p v-if="selectedPreset" class="text-xs text-slate-500 pl-1">
            {{ selectedPreset.description }}
          </p>
        </div>

        <!-- 지점 선택 (지점 원장 viewer 선택 시에만 활성화) -->
        <select
          v-model="newBranchId"
          :disabled="!isBranchRequired"
          class="w-full px-3 py-1.5 border border-slate-300 rounded text-sm disabled:bg-slate-50 disabled:text-slate-400 disabled:cursor-not-allowed"
        >
          <option :value="null">{{ isBranchRequired ? '지점 선택 (필수)' : '지점 없음' }}</option>
          <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.name }}</option>
        </select>

        <!-- 메모 + 생성 버튼 -->
        <div class="flex gap-3">
          <input
            v-model="newMemo"
            placeholder="메모 (선택)"
            class="flex-1 px-3 py-1.5 border border-slate-300 rounded text-sm"
          />
          <button
            @click="handleCreate"
            class="px-4 py-1.5 bg-emerald-600 text-white text-sm rounded hover:bg-emerald-700"
          >
            생성
          </button>
        </div>
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
