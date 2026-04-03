<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/client'

const router = useRouter()
const auth = useAuthStore()
const isBranch = computed(() => auth.role === 'branch')

// State
const branches = ref<any[]>([])
const selectedBranchId = ref<number | null>(null)
const branchData = ref<any>(null)
const loading = ref(false)
const searchQuery = ref('')

// Filtered branches
const filteredBranches = computed(() => {
  if (!searchQuery.value) return branches.value
  return branches.value.filter((b: any) =>
    b.branch_name.includes(searchQuery.value)
  )
})

async function loadBranches() {
  try {
    const { data } = await api.get('/branch-info/all/summary')
    branches.value = data
    // branch 역할은 자동 선택
    if (isBranch.value && auth.branchId) {
      selectBranch(auth.branchId)
    }
  } catch { /* ignore */ }
}

async function selectBranch(branchId: number) {
  selectedBranchId.value = branchId
  loading.value = true
  try {
    const { data } = await api.get(`/branch-info/${branchId}`)
    branchData.value = data
  } finally {
    loading.value = false
  }
}

function goToCrossref(itemName: string) {
  // 시술정보 크로스체크로 이동 (쿼리 파라미터)
  router.push({ path: '/treatment-info', query: { tab: 'crossref', q: itemName } })
}

function formatPrice(p: number | null) {
  if (!p) return '-'
  return (p / 10000).toFixed(0) + '만원'
}

function formatDate(d: string) {
  if (!d) return '-'
  return d.slice(0, 10)
}

const statusLabels: Record<string, { label: string; color: string }> = {
  received: { label: '접수', color: 'bg-yellow-100 text-yellow-700' },
  processing: { label: '처리중', color: 'bg-blue-100 text-blue-700' },
  resolved: { label: '처리완료', color: 'bg-green-100 text-green-700' },
  closed: { label: '종결', color: 'bg-slate-100 text-slate-500' },
}

onMounted(loadBranches)
</script>

<template>
  <div class="max-w-3xl mx-auto py-6 px-4">
    <h2 class="text-xl font-bold text-slate-800 mb-2">지점 정보</h2>
    <p class="text-sm text-slate-400 mb-6">지점을 선택하면 보유장비, 이벤트, 민원을 한눈에 확인합니다.</p>

    <!-- Branch selector (when no branch selected) -->
    <div v-if="!branchData">
      <!-- 검색 -->
      <div class="relative mb-5">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="지점명 검색..."
          class="w-full border border-slate-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 pl-10"
        />
        <svg class="absolute left-3.5 top-3.5 w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
        </svg>
        <span v-if="searchQuery" class="absolute right-3.5 top-3 text-xs text-slate-400">
          {{ filteredBranches.length }}개 지점
        </span>
      </div>

      <!-- 카드 그리드 -->
      <div class="grid grid-cols-2 gap-3">
        <div
          v-for="b in filteredBranches" :key="b.branch_id"
          @click="selectBranch(b.branch_id)"
          class="p-4 bg-white rounded-xl border border-slate-200 cursor-pointer hover:border-blue-400 hover:shadow-sm transition group"
        >
          <div class="font-semibold text-slate-800 text-sm mb-3 group-hover:text-blue-600 transition">
            {{ b.branch_name }}
          </div>
          <div class="flex gap-4 text-xs">
            <div class="text-center">
              <div class="text-base font-bold text-blue-600">{{ b.equipment_count }}</div>
              <div class="text-slate-400">장비</div>
            </div>
            <div class="text-center">
              <div class="text-base font-bold text-purple-600">{{ b.event_count }}</div>
              <div class="text-slate-400">이벤트</div>
            </div>
            <div v-if="b.open_complaints" class="text-center">
              <div class="text-base font-bold text-orange-500">{{ b.open_complaints }}</div>
              <div class="text-orange-400">민원</div>
            </div>
          </div>
        </div>
      </div>

      <p v-if="!filteredBranches.length && searchQuery" class="text-center text-sm text-slate-400 py-8">
        '{{ searchQuery }}' 검색 결과가 없습니다.
      </p>
    </div>

    <!-- Branch detail -->
    <div v-if="branchData && !loading">
      <!-- Header -->
      <div class="flex items-center gap-3 mb-5">
        <button
          v-if="!isBranch"
          @click="branchData = null; selectedBranchId = null"
          class="text-sm text-blue-600 hover:underline"
        >&larr; 전체 지점</button>
        <h3 class="text-lg font-bold text-slate-800">{{ branchData.branch_name }}</h3>
      </div>

      <!-- Summary cards -->
      <div class="grid grid-cols-3 gap-3 mb-5">
        <div class="bg-blue-50 rounded-lg p-3 text-center">
          <div class="text-lg font-bold text-blue-700">{{ branchData.summary?.equipment_count || 0 }}</div>
          <div class="text-xs text-blue-500">보유장비</div>
        </div>
        <div class="bg-purple-50 rounded-lg p-3 text-center">
          <div class="text-lg font-bold text-purple-700">{{ branchData.summary?.event_count || 0 }}</div>
          <div class="text-xs text-purple-500">이벤트</div>
        </div>
        <div class="bg-orange-50 rounded-lg p-3 text-center">
          <div class="text-lg font-bold text-orange-700">{{ branchData.summary?.complaint_open || 0 }}</div>
          <div class="text-xs text-orange-500">진행 민원</div>
        </div>
      </div>

      <!-- Equipment -->
      <div class="p-4 bg-white rounded-xl border border-slate-200 mb-4">
        <h4 class="text-sm font-semibold text-slate-700 mb-3">
          보유장비 ({{ branchData.equipment?.length || 0 }}건)
        </h4>
        <div v-if="branchData.equipment?.length" class="space-y-1.5">
          <div
            v-for="eq in branchData.equipment" :key="eq.id"
            class="flex items-center justify-between text-sm group"
          >
            <div class="flex items-center gap-2">
              <span
                @click="goToCrossref(eq.name)"
                class="text-slate-700 hover:text-blue-600 cursor-pointer hover:underline"
              >{{ eq.name }}</span>
              <span class="text-xs text-slate-400">{{ eq.category }}</span>
            </div>
            <div class="flex items-center gap-3 text-xs text-slate-400">
              <span>{{ eq.quantity || 1 }}대</span>
              <span :class="eq.photo_status === '있음' || eq.photo_status === 'O' ? 'text-green-500' : 'text-slate-300'">
                사진{{ eq.photo_status === '있음' || eq.photo_status === 'O' ? 'O' : 'X' }}
              </span>
            </div>
          </div>
        </div>
        <p v-else class="text-xs text-slate-400">보유장비 정보 없음</p>
      </div>

      <!-- Events -->
      <div class="p-4 bg-white rounded-xl border border-slate-200 mb-4">
        <h4 class="text-sm font-semibold text-slate-700 mb-3">
          이벤트 ({{ branchData.events?.length || 0 }}건)
        </h4>
        <div v-if="branchData.events?.length" class="space-y-1.5">
          <div
            v-for="ev in branchData.events" :key="ev.id"
            class="flex items-center justify-between text-sm"
          >
            <div class="flex items-center gap-2">
              <span
                @click="goToCrossref(ev.display_name || ev.raw_event_name)"
                class="text-slate-700 hover:text-blue-600 cursor-pointer hover:underline"
              >{{ ev.display_name || ev.raw_event_name }}</span>
              <span class="text-xs text-slate-400">{{ ev.category }}</span>
            </div>
            <div class="text-right">
              <span class="text-sm font-medium text-blue-600">{{ formatPrice(ev.event_price) }}</span>
              <span v-if="ev.regular_price" class="text-xs text-slate-400 line-through ml-1">{{ formatPrice(ev.regular_price) }}</span>
            </div>
          </div>
        </div>
        <p v-else class="text-xs text-slate-400">등록된 이벤트 없음</p>
      </div>

      <!-- Complaints -->
      <div class="p-4 bg-white rounded-xl border border-slate-200 mb-4">
        <h4 class="text-sm font-semibold text-slate-700 mb-3">
          민원 ({{ branchData.complaints?.length || 0 }}건)
        </h4>
        <div v-if="branchData.complaints?.length" class="space-y-1.5">
          <div
            v-for="c in branchData.complaints" :key="c.id"
            class="flex items-center justify-between text-sm"
          >
            <div class="flex items-center gap-2">
              <span :class="['text-xs px-1.5 py-0.5 rounded-full', statusLabels[c.status]?.color]">
                {{ statusLabels[c.status]?.label }}
              </span>
              <span class="text-slate-700">{{ c.title }}</span>
            </div>
            <span class="text-xs text-slate-400">{{ formatDate(c.created_at) }}</span>
          </div>
        </div>
        <p v-else class="text-xs text-slate-400">등록된 민원 없음</p>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-12 text-sm text-slate-400">로딩 중...</div>
  </div>
</template>
