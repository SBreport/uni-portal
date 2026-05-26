<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/client'
import BranchDashboard from '@/components/branch/BranchDashboard.vue'

const props = withDefaults(defineProps<{
  embedded?: boolean
}>(), { embedded: false })

const auth = useAuthStore()
const isBranch = computed(() => auth.role === 'branch')

// State
const branches = ref<any[]>([])
const selectedBranch = ref<{ id: number; name: string } | null>(null)
const loadingBranches = ref(false)
const searchQuery = ref('')

// Filtered branches
const filteredBranches = computed(() => {
  if (!searchQuery.value) return branches.value
  return branches.value.filter((b: any) =>
    b.branch_name.includes(searchQuery.value)
  )
})

async function loadBranches() {
  loadingBranches.value = true
  try {
    const { data } = await api.get('/branch-info/all/summary')
    branches.value = data
    // branch 역할은 자동 선택
    if (isBranch.value && auth.branchId) {
      const found = data.find((b: any) => b.branch_id === auth.branchId)
      if (found) selectBranch(found.branch_id, found.branch_name)
    }
  } catch { /* ignore */ } finally {
    loadingBranches.value = false
  }
}

function selectBranch(branchId: number, branchName: string) {
  selectedBranch.value = { id: branchId, name: branchName }
}

function clearBranch() {
  selectedBranch.value = null
}

onMounted(loadBranches)
</script>

<template>
  <div class="h-full flex flex-col overflow-hidden">
    <h2 v-if="!embedded && !selectedBranch" class="shrink-0 text-xl font-bold text-slate-800 px-6 pt-5 pb-2">지점 정보</h2>

    <!-- ── 지점 선택 화면 ────────────────────────────────────────── -->
    <div v-if="!selectedBranch" class="flex-1 min-h-0 overflow-y-auto px-6 pb-6">
      <p class="text-sm text-slate-400 mb-4">지점을 선택하면 카테고리별 보유장비·이벤트를 확인합니다.</p>

      <!-- 검색 -->
      <div class="relative mb-4">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="지점명 검색..."
          class="w-full border border-slate-300 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 pl-9"
        />
        <svg class="absolute left-3 top-3 w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
        </svg>
        <span v-if="searchQuery" class="absolute right-3 top-2.5 text-xs text-slate-400">
          {{ filteredBranches.length }}개
        </span>
      </div>

      <!-- 로딩 -->
      <div v-if="loadingBranches" class="text-center py-8 text-sm text-slate-400">불러오는 중...</div>

      <!-- 카드 그리드 -->
      <div
        v-else
        class="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 2xl:grid-cols-10 gap-2"
      >
        <div
          v-for="b in filteredBranches"
          :key="b.branch_id"
          @click="selectBranch(b.branch_id, b.branch_name)"
          class="p-3 bg-white rounded-lg border border-slate-200 cursor-pointer hover:border-blue-400 hover:shadow-sm transition group"
        >
          <p class="text-sm font-semibold text-slate-700 group-hover:text-blue-600 transition truncate mb-1">
            {{ b.branch_name }}
          </p>
          <div class="flex gap-2 flex-wrap">
            <span class="text-xs text-blue-500">장비 {{ b.equipment_count }}</span>
            <span class="text-xs text-purple-500">이벤트 {{ b.event_count }}</span>
            <span v-if="b.open_complaints" class="text-xs text-orange-500">민원 {{ b.open_complaints }}</span>
          </div>
        </div>
      </div>

      <p v-if="!loadingBranches && !filteredBranches.length && searchQuery" class="text-center text-sm text-slate-400 py-8">
        '{{ searchQuery }}' 검색 결과가 없습니다.
      </p>
    </div>

    <!-- ── 지점 대시보드 ─────────────────────────────────────────── -->
    <BranchDashboard
      v-else
      :branch-id="selectedBranch.id"
      :branch-name="selectedBranch.name"
      class="flex-1 min-h-0"
      @back="clearBranch"
    />
  </div>
</template>
