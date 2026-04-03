<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/client'

const auth = useAuthStore()
const isBranch = computed(() => auth.role === 'branch')

// State
const branches = ref<{ id: number; name: string }[]>([])
const selectedBranch = ref<number | null>(null)
const summaryData = ref<any[]>([])
const branchReport = ref<any>(null)
const loading = ref(false)

async function loadBranches() {
  try {
    const { data } = await api.get('/events/branches')
    branches.value = data
    if (isBranch.value && auth.branchId) {
      selectedBranch.value = auth.branchId
      await loadBranchReport(auth.branchId)
    }
  } catch { /* ignore */ }
}

async function loadSummary() {
  loading.value = true
  try {
    const { data } = await api.get('/reports/summary')
    summaryData.value = data
  } finally {
    loading.value = false
  }
}

async function loadBranchReport(branchId: number) {
  loading.value = true
  selectedBranch.value = branchId
  try {
    const { data } = await api.get(`/reports/branch/${branchId}`)
    branchReport.value = data
  } finally {
    loading.value = false
  }
}

function openExport(branchId: number) {
  window.open(`/api/reports/branch/${branchId}/export`, '_blank')
}

function formatPrice(p: number | null) {
  if (!p) return '-'
  return (p / 10000).toFixed(0) + '만원'
}

onMounted(() => {
  loadBranches()
  if (!isBranch.value) loadSummary()
})
</script>

<template>
  <div class="max-w-3xl mx-auto py-6 px-4">
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-bold text-slate-800">보고서</h2>
      <button
        v-if="branchReport && selectedBranch"
        @click="openExport(selectedBranch)"
        class="px-3 py-1.5 bg-slate-700 text-white text-sm rounded-lg hover:bg-slate-800"
      >HTML/PDF 내보내기</button>
    </div>

    <!-- Branch Selector (admin/editor) -->
    <div v-if="!isBranch" class="mb-6">
      <select
        v-model="selectedBranch"
        @change="selectedBranch && loadBranchReport(selectedBranch)"
        class="text-sm border rounded-lg px-3 py-2 w-full max-w-xs"
      >
        <option :value="null" disabled>지점 선택</option>
        <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.name }}</option>
      </select>
    </div>

    <!-- Summary Table (admin/editor only, when no branch selected) -->
    <div v-if="!isBranch && !branchReport && summaryData.length" class="mb-6">
      <h3 class="text-sm font-semibold text-slate-600 mb-3">전 지점 요약</h3>
      <div class="space-y-1">
        <div
          v-for="s in summaryData" :key="s.branch_id"
          @click="loadBranchReport(s.branch_id)"
          class="p-3 bg-white rounded-lg border border-slate-200 cursor-pointer hover:border-blue-300 transition flex items-center justify-between"
        >
          <span class="font-medium text-slate-700 text-sm">{{ s.branch_name }}</span>
          <div class="flex gap-4 text-xs text-slate-400">
            <span>장비 {{ s.equipment_count }}</span>
            <span>이벤트 {{ s.event_count }}</span>
            <span>플레이스 {{ s.place_exposed_days }}일</span>
            <span>웹 {{ s.webpage_exposed_days }}일</span>
            <span v-if="s.open_complaints" class="text-orange-500">민원 {{ s.open_complaints }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Branch Detail Report -->
    <div v-if="branchReport">
      <div class="flex items-center gap-3 mb-4">
        <button
          v-if="!isBranch"
          @click="branchReport = null; selectedBranch = null"
          class="text-sm text-blue-600 hover:underline"
        >&larr; 전체 목록</button>
        <h3 class="text-lg font-bold text-slate-800">{{ branchReport.branch_name }}</h3>
      </div>

      <!-- Equipment -->
      <div class="p-4 bg-white rounded-xl border border-slate-200 mb-3">
        <h4 class="text-sm font-semibold text-slate-600 mb-2">보유장비</h4>
        <div class="flex gap-6 text-sm">
          <div><span class="text-2xl font-bold text-blue-600">{{ branchReport.equipment?.total || 0 }}</span> <span class="text-slate-400">전체</span></div>
          <div><span class="text-2xl font-bold text-green-600">{{ branchReport.equipment?.with_photo || 0 }}</span> <span class="text-slate-400">사진보유</span></div>
        </div>
      </div>

      <!-- Events -->
      <div class="p-4 bg-white rounded-xl border border-slate-200 mb-3">
        <h4 class="text-sm font-semibold text-slate-600 mb-2">이벤트 ({{ branchReport.events?.total || 0 }}건)</h4>
        <div v-if="branchReport.events?.items?.length" class="space-y-1">
          <div v-for="ev in branchReport.events.items.slice(0, 5)" :key="ev.display_name" class="flex justify-between text-sm">
            <span class="text-slate-700">{{ ev.display_name }}</span>
            <span class="text-blue-600 font-medium">{{ formatPrice(ev.event_price) }}</span>
          </div>
        </div>
        <p v-else class="text-xs text-slate-400">등록된 이벤트 없음</p>
      </div>

      <!-- Place -->
      <div class="p-4 bg-white rounded-xl border border-slate-200 mb-3">
        <h4 class="text-sm font-semibold text-slate-600 mb-2">플레이스 상위노출</h4>
        <div class="flex gap-6 text-sm">
          <div><span class="text-2xl font-bold text-blue-600">{{ branchReport.place?.exposed_days || 0 }}</span> <span class="text-slate-400">노출일</span></div>
          <div><span class="text-2xl font-bold text-slate-600">{{ branchReport.place?.exposure_rate || 0 }}%</span> <span class="text-slate-400">노출률</span></div>
        </div>
      </div>

      <!-- Webpage -->
      <div class="p-4 bg-white rounded-xl border border-slate-200 mb-3">
        <h4 class="text-sm font-semibold text-slate-600 mb-2">웹페이지 노출</h4>
        <div class="flex gap-6 text-sm">
          <div><span class="text-2xl font-bold text-blue-600">{{ branchReport.webpage?.exposed_days || 0 }}</span> <span class="text-slate-400">노출일</span></div>
          <div><span class="text-2xl font-bold text-slate-600">{{ branchReport.webpage?.exposure_rate || 0 }}%</span> <span class="text-slate-400">노출률</span></div>
        </div>
      </div>

      <!-- Cafe -->
      <div class="p-4 bg-white rounded-xl border border-slate-200 mb-3">
        <h4 class="text-sm font-semibold text-slate-600 mb-2">카페 마케팅 ({{ branchReport.cafe?.total || 0 }}건)</h4>
        <div v-if="branchReport.cafe?.articles?.length" class="space-y-1">
          <div v-for="a in branchReport.cafe.articles.slice(0, 5)" :key="a.id" class="text-sm text-slate-600">
            {{ a.title || '(제목 없음)' }}
            <span class="text-xs text-slate-400 ml-1">{{ a.status }}</span>
          </div>
        </div>
      </div>

      <!-- Blog -->
      <div class="p-4 bg-white rounded-xl border border-slate-200 mb-3">
        <h4 class="text-sm font-semibold text-slate-600 mb-2">블로그 ({{ branchReport.blog?.total || 0 }}건)</h4>
        <div v-if="branchReport.blog?.posts?.length" class="space-y-1">
          <div v-for="p in branchReport.blog.posts.slice(0, 5)" :key="p.id" class="text-sm text-slate-600">
            {{ p.title }}
            <span class="text-xs text-slate-400 ml-1">{{ p.status }}</span>
          </div>
        </div>
      </div>

      <!-- Complaints -->
      <div class="p-4 bg-white rounded-xl border border-slate-200 mb-3">
        <h4 class="text-sm font-semibold text-slate-600 mb-2">민원 ({{ branchReport.complaints?.total || 0 }}건)</h4>
        <div class="flex gap-4 text-sm mb-2">
          <span class="text-yellow-600">접수 {{ branchReport.complaints?.status_counts?.received || 0 }}</span>
          <span class="text-blue-600">처리중 {{ branchReport.complaints?.status_counts?.processing || 0 }}</span>
          <span class="text-green-600">완료 {{ branchReport.complaints?.status_counts?.resolved || 0 }}</span>
          <span class="text-slate-400">종결 {{ branchReport.complaints?.status_counts?.closed || 0 }}</span>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-12 text-sm text-slate-400">데이터 로딩 중...</div>

    <!-- Empty state -->
    <div v-if="!loading && !branchReport && !summaryData.length && !isBranch" class="text-center py-16 text-sm text-slate-400">
      보고서 데이터를 불러오는 중...
    </div>
  </div>
</template>
