<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import {
  getComplaints, getComplaint, createComplaint,
  changeComplaintStatus, getComplaintLogs,
  type Complaint, type ComplaintLog
} from '@/api/complaints'
import api from '@/api/client'

const auth = useAuthStore()
const isBranch = computed(() => auth.role === 'branch')
const isAdmin = computed(() => auth.role === 'admin' || auth.role === 'editor')

// State
const complaints = ref<Complaint[]>([])
const branches = ref<{ id: number; name: string }[]>([])
const selectedComplaint = ref<Complaint | null>(null)
const logs = ref<ComplaintLog[]>([])
const loading = ref(false)

// Filters
const filterStatus = ref('')
const filterBranch = ref<number | ''>('')

// Create form
const showCreate = ref(false)
const form = ref({
  branch_id: 0,
  title: '',
  content: '',
  category: '',
  severity: 'normal',
})

// Status labels
const statusLabels: Record<string, { label: string; color: string }> = {
  received: { label: '접수', color: 'bg-yellow-100 text-yellow-700' },
  processing: { label: '처리중', color: 'bg-blue-100 text-blue-700' },
  resolved: { label: '처리완료', color: 'bg-green-100 text-green-700' },
  closed: { label: '종결', color: 'bg-slate-100 text-slate-500' },
}

const severityLabels: Record<string, string> = {
  low: '낮음',
  normal: '보통',
  high: '높음',
  critical: '긴급',
}

async function loadBranches() {
  try {
    const { data } = await api.get('/events/branches')
    branches.value = data
  } catch { /* ignore */ }
}

async function loadComplaints() {
  loading.value = true
  try {
    const params: any = {}
    if (filterStatus.value) params.status = filterStatus.value
    if (filterBranch.value) params.branch_id = filterBranch.value
    const { data } = await getComplaints(params)
    complaints.value = data
  } finally {
    loading.value = false
  }
}

async function selectComplaint(c: Complaint) {
  selectedComplaint.value = c
  const { data } = await getComplaintLogs(c.id)
  logs.value = data
}

async function handleCreate() {
  if (!form.value.title || !form.value.branch_id) return
  await createComplaint(form.value)
  showCreate.value = false
  form.value = { branch_id: 0, title: '', content: '', category: '', severity: 'normal' }
  await loadComplaints()
}

async function handleStatusChange(newStatus: string) {
  if (!selectedComplaint.value) return
  const note = prompt('상태 변경 메모 (선택사항):') || ''
  await changeComplaintStatus(selectedComplaint.value.id, newStatus, note)
  await loadComplaints()
  await selectComplaint({ ...selectedComplaint.value, status: newStatus })
}

function formatDate(d: string) {
  if (!d) return '-'
  return d.slice(0, 16).replace('T', ' ')
}

const nextStatuses = computed(() => {
  if (!selectedComplaint.value) return []
  const transitions: Record<string, string[]> = {
    received: ['processing'],
    processing: ['resolved', 'received'],
    resolved: ['closed', 'processing'],
    closed: [],
  }
  return transitions[selectedComplaint.value.status] || []
})

onMounted(() => {
  loadBranches()
  loadComplaints()
  if (isBranch.value && auth.branchId) {
    form.value.branch_id = auth.branchId
  }
})

watch([filterStatus, filterBranch], loadComplaints)
</script>

<template>
  <div class="max-w-3xl mx-auto py-6 px-4">
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-bold text-slate-800">민원 관리</h2>
      <button
        @click="showCreate = true"
        class="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
      >+ 민원 등록</button>
    </div>

    <!-- Filters -->
    <div class="flex gap-3 mb-4" v-if="isAdmin">
      <select v-model="filterBranch" class="text-sm border rounded-lg px-3 py-1.5">
        <option value="">전체 지점</option>
        <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.name }}</option>
      </select>
      <select v-model="filterStatus" class="text-sm border rounded-lg px-3 py-1.5">
        <option value="">전체 상태</option>
        <option value="received">접수</option>
        <option value="processing">처리중</option>
        <option value="resolved">처리완료</option>
        <option value="closed">종결</option>
      </select>
    </div>

    <!-- List -->
    <div class="space-y-2">
      <div
        v-for="c in complaints" :key="c.id"
        @click="selectComplaint(c)"
        :class="[
          'p-4 bg-white rounded-lg border cursor-pointer hover:border-blue-300 transition',
          selectedComplaint?.id === c.id ? 'border-blue-500 ring-1 ring-blue-200' : 'border-slate-200'
        ]"
      >
        <div class="flex items-center justify-between mb-1">
          <span class="font-medium text-slate-800">{{ c.title }}</span>
          <span :class="['text-xs px-2 py-0.5 rounded-full', statusLabels[c.status]?.color]">
            {{ statusLabels[c.status]?.label }}
          </span>
        </div>
        <div class="flex gap-4 text-xs text-slate-400">
          <span>{{ c.branch_name || '지점 #' + c.branch_id }}</span>
          <span>{{ severityLabels[c.severity] || c.severity }}</span>
          <span>{{ formatDate(c.created_at) }}</span>
          <span v-if="c.assigned_to">담당: {{ c.assigned_to }}</span>
        </div>
      </div>
      <p v-if="!complaints.length && !loading" class="text-sm text-slate-400 text-center py-8">
        등록된 민원이 없습니다.
      </p>
    </div>

    <!-- Detail Panel -->
    <div v-if="selectedComplaint" class="mt-6 p-5 bg-white rounded-lg border border-slate-200">
      <h3 class="text-lg font-bold text-slate-800 mb-3">{{ selectedComplaint.title }}</h3>
      <p class="text-sm text-slate-600 whitespace-pre-wrap mb-4">{{ selectedComplaint.content || '(내용 없음)' }}</p>

      <div class="grid grid-cols-2 gap-2 text-sm text-slate-500 mb-4">
        <div>상태: <span :class="['px-2 py-0.5 rounded-full text-xs', statusLabels[selectedComplaint.status]?.color]">{{ statusLabels[selectedComplaint.status]?.label }}</span></div>
        <div>심각도: {{ severityLabels[selectedComplaint.severity] }}</div>
        <div>등록자: {{ selectedComplaint.reported_by }}</div>
        <div>담당자: {{ selectedComplaint.assigned_to || '-' }}</div>
      </div>

      <!-- Status Actions -->
      <div v-if="nextStatuses.length" class="flex gap-2 mb-4">
        <button
          v-for="ns in nextStatuses" :key="ns"
          @click="handleStatusChange(ns)"
          class="px-3 py-1 text-xs rounded-lg border hover:bg-slate-50"
        >{{ statusLabels[ns]?.label }}(으)로 변경</button>
      </div>

      <!-- Resolution -->
      <div v-if="selectedComplaint.resolution" class="p-3 bg-green-50 rounded-lg text-sm mb-4">
        <span class="font-medium text-green-700">처리 결과:</span>
        <p class="text-green-600 mt-1">{{ selectedComplaint.resolution }}</p>
      </div>

      <!-- Logs -->
      <div v-if="logs.length">
        <h4 class="text-sm font-medium text-slate-600 mb-2">상태 이력</h4>
        <div class="space-y-1">
          <div v-for="log in logs" :key="log.id" class="text-xs text-slate-400 flex gap-2">
            <span>{{ formatDate(log.changed_at) }}</span>
            <span>{{ statusLabels[log.old_status]?.label }} -> {{ statusLabels[log.new_status]?.label }}</span>
            <span v-if="log.changed_by">by {{ log.changed_by }}</span>
            <span v-if="log.note" class="text-slate-500">{{ log.note }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Modal -->
    <div v-if="showCreate" class="fixed inset-0 bg-black/30 flex items-center justify-center z-50" @click.self="showCreate = false">
      <div class="bg-white rounded-xl p-6 w-full max-w-md">
        <h3 class="text-lg font-bold mb-4">민원 등록</h3>
        <div class="space-y-3">
          <select v-if="isAdmin" v-model="form.branch_id" class="w-full border rounded-lg px-3 py-2 text-sm">
            <option :value="0" disabled>지점 선택</option>
            <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.name }}</option>
          </select>
          <input v-model="form.title" placeholder="민원 제목" class="w-full border rounded-lg px-3 py-2 text-sm" />
          <textarea v-model="form.content" placeholder="민원 내용" rows="4" class="w-full border rounded-lg px-3 py-2 text-sm" />
          <select v-model="form.severity" class="w-full border rounded-lg px-3 py-2 text-sm">
            <option value="low">낮음</option>
            <option value="normal">보통</option>
            <option value="high">높음</option>
            <option value="critical">긴급</option>
          </select>
          <div class="flex justify-end gap-2 pt-2">
            <button @click="showCreate = false" class="px-4 py-2 text-sm text-slate-500">취소</button>
            <button @click="handleCreate" class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">등록</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
