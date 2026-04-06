<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useBranchStore } from '@/stores/branches'
import api from '@/api/client'

const auth = useAuthStore()
const branchStore = useBranchStore()
const isBranch = computed(() => auth.role === 'branch')
const isInternal = computed(() => auth.role === 'admin' || auth.role === 'editor')

// State
const branches = computed(() => branchStore.branches)
const selectedBranch = ref<number | null>(null)
const selectedYear = ref(new Date().getFullYear())
const selectedMonth = ref(new Date().getMonth() + 1)
const summaryData = ref<any[]>([])
const branchReport = ref<any>(null)
const loading = ref(false)

// 월 옵션
const monthOptions = computed(() => {
  const opts = []
  for (let m = 1; m <= 12; m++) {
    opts.push({ value: m, label: `${m}월` })
  }
  return opts
})

const sectionIcons: Record<string, string> = {
  brand_blog: 'B',
  opt_blog: 'O',
  cafe: 'C',
  place: 'P',
  webpage: 'W',
  complaints: 'M',
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
    const { data } = await api.get(`/reports/branch/${branchId}`, {
      params: { year: selectedYear.value, month: selectedMonth.value }
    })
    branchReport.value = data
  } finally {
    loading.value = false
  }
}

function openExport() {
  if (!selectedBranch.value) return
  const params = `?year=${selectedYear.value}&month=${selectedMonth.value}`
  window.open(`/api/reports/branch/${selectedBranch.value}/export${params}`, '_blank')
}

function formatPrice(p: number | null) {
  if (!p) return '-'
  return (p / 10000).toFixed(0) + '만원'
}

// 월 변경 시 자동 새로고침
watch([selectedYear, selectedMonth], () => {
  if (selectedBranch.value) loadBranchReport(selectedBranch.value)
})

onMounted(async () => {
  await branchStore.loadBranches()
  if (isBranch.value && auth.branchId) {
    selectedBranch.value = auth.branchId
    await loadBranchReport(auth.branchId)
  }
  if (!isBranch.value) loadSummary()
})
</script>

<template>
  <div class="max-w-3xl mx-auto py-6 px-4">
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-bold text-slate-800">보고서</h2>
      <div v-if="branchReport" class="flex items-center gap-2">
        <button
          @click="openExport"
          class="px-3 py-1.5 bg-slate-700 text-white text-sm rounded-lg hover:bg-slate-800"
        >HTML/PDF 내보내기</button>
      </div>
    </div>

    <!-- 지점 + 월 선택 -->
    <div class="flex gap-3 mb-5">
      <select
        v-if="!isBranch"
        v-model="selectedBranch"
        @change="selectedBranch && loadBranchReport(selectedBranch)"
        class="text-sm border rounded-lg px-3 py-2 flex-1"
      >
        <option :value="null" disabled>지점 선택</option>
        <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.name }}</option>
      </select>
      <select v-model="selectedYear" class="text-sm border rounded-lg px-3 py-2 w-24">
        <option :value="2025">2025</option>
        <option :value="2026">2026</option>
      </select>
      <select v-model="selectedMonth" class="text-sm border rounded-lg px-3 py-2 w-20">
        <option v-for="m in monthOptions" :key="m.value" :value="m.value">{{ m.label }}</option>
      </select>
    </div>

    <!-- Summary Table (지점 미선택 시) -->
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
            <span v-if="s.place_exposed_days">플레이스 {{ s.place_exposed_days }}일</span>
            <span v-if="s.webpage_exposed_days">웹 {{ s.webpage_exposed_days }}일</span>
            <span v-if="s.open_complaints" class="text-orange-500">민원 {{ s.open_complaints }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Branch Report -->
    <div v-if="branchReport && !loading">
      <div class="flex items-center gap-3 mb-4">
        <button
          v-if="!isBranch"
          @click="branchReport = null; selectedBranch = null"
          class="text-sm text-blue-600 hover:underline"
        >&larr; 전체 목록</button>
        <h3 class="text-lg font-bold text-slate-800">
          {{ branchReport.branch_name }}
          <span class="text-sm font-normal text-slate-400 ml-2">{{ selectedYear }}년 {{ selectedMonth }}월</span>
        </h3>
      </div>

      <!-- 데이터가 없을 때 -->
      <div v-if="!branchReport.sections?.length" class="text-center py-12 text-sm text-slate-400">
        해당 기간에 진행된 마케팅 내역이 없습니다.
      </div>

      <!-- 섹션별 렌더링 (순서대로) -->
      <div v-for="section in branchReport.sections" :key="section.key" class="mb-5">
        <div class="p-4 bg-white rounded-xl border border-slate-200">
          <h4 class="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
            <span class="w-5 h-5 rounded bg-blue-100 text-blue-600 text-xs flex items-center justify-center font-bold">
              {{ sectionIcons[section.key] || '?' }}
            </span>
            {{ section.title }}
            <span class="text-xs font-normal text-slate-400">
              {{ section.data.total || section.data.total_days || 0 }}{{ section.key.includes('blog') || section.key === 'cafe' ? '건' : '일' }}
            </span>
          </h4>

          <!-- 블로그 (brand_blog, opt_blog) -->
          <template v-if="section.key === 'brand_blog' || section.key === 'opt_blog'">
            <div class="space-y-1.5">
              <div v-for="p in section.data.posts?.slice(0, 15)" :key="p.id" class="text-sm flex items-center gap-3">
                <a v-if="p.published_url" :href="p.published_url" target="_blank" class="text-blue-500 hover:underline shrink-0">링크</a>
                <span class="text-slate-700 min-w-0 truncate">{{ p.title || '(제목 없음)' }}</span>
                <span v-if="isInternal && p.author" class="text-xs text-slate-400 shrink-0">{{ p.author }}</span>
              </div>
            </div>
          </template>

          <!-- 카페 -->
          <template v-if="section.key === 'cafe'">
            <div class="space-y-1.5">
              <div v-for="a in section.data.articles?.slice(0, 10)" :key="a.id" class="text-sm flex items-center justify-between">
                <span class="text-slate-700">{{ a.title || '(제목 없음)' }}</span>
                <span class="text-xs text-slate-400">{{ a.status }}</span>
              </div>
            </div>
          </template>

          <!-- 플레이스 / 웹사이트 -->
          <template v-if="section.key === 'place' || section.key === 'webpage'">
            <div class="flex gap-6 text-sm">
              <div><span class="text-2xl font-bold text-blue-600">{{ section.data.exposed_days }}</span> <span class="text-slate-400">노출일</span></div>
              <div><span class="text-2xl font-bold text-slate-600">{{ section.data.exposure_rate }}%</span> <span class="text-slate-400">노출률</span></div>
            </div>
          </template>

          <!-- 민원 -->
          <template v-if="section.key === 'complaints'">
            <div class="flex gap-4 text-sm mb-2">
              <span class="text-yellow-600">접수 {{ section.data.status_counts?.received || 0 }}</span>
              <span class="text-blue-600">처리중 {{ section.data.status_counts?.processing || 0 }}</span>
              <span class="text-green-600">완료 {{ section.data.status_counts?.resolved || 0 }}</span>
            </div>
            <div v-if="section.data.recent?.length" class="space-y-1">
              <div v-for="c in section.data.recent" :key="c.id" class="text-xs text-slate-500">
                {{ c.title }} <span class="text-slate-400">{{ c.status }}</span>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-12 text-sm text-slate-400">데이터 로딩 중...</div>
  </div>
</template>
