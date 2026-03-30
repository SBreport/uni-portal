<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import * as blogApi from '@/api/blog'
import { channelLabel, channelColor, typeColor } from '@/utils/blogFormatters'

const dashboard = ref<any>(null)
const loading = ref(false)
const syncStatus = ref<any>(null)

async function loadDashboard() {
  loading.value = true
  try {
    const [dashRes, statusRes] = await Promise.all([
      blogApi.getBlogDashboard(),
      blogApi.getNotionSyncStatus(),
    ])
    dashboard.value = dashRes.data
    syncStatus.value = statusRes.data?.last_sync || null
  } catch (e) {
    console.error('대시보드 로드 실패:', e)
  } finally {
    loading.value = false
  }
}

const maxBranchCount = computed(() => {
  if (!dashboard.value?.by_branch?.length) return 1
  return Math.max(...dashboard.value.by_branch.map((b: any) => b.cnt))
})
const maxMonthlyCount = computed(() => {
  if (!dashboard.value?.monthly?.length) return 1
  return Math.max(...dashboard.value.monthly.map((m: any) => m.cnt))
})
const sortedMonthly = computed(() => {
  if (!dashboard.value?.monthly) return []
  return [...dashboard.value.monthly].sort((a: any, b: any) => a.month.localeCompare(b.month))
})

onMounted(loadDashboard)
</script>

<template>
  <div class="flex-1 overflow-auto space-y-4">
    <div v-if="loading" class="text-center py-12 text-slate-400">로딩 중...</div>
    <template v-else-if="dashboard">
      <!-- 요약 카드 -->
      <div class="grid grid-cols-5 gap-3">
        <div class="bg-white border border-slate-200 rounded-lg p-4">
          <p class="text-xs text-slate-400">전체 게시글</p>
          <p class="text-2xl font-bold text-slate-800 mt-1">{{ dashboard.total?.toLocaleString() }}</p>
        </div>
        <div class="bg-white border border-blue-200 rounded-lg p-4">
          <p class="text-xs text-blue-500">브랜드</p>
          <p class="text-2xl font-bold text-blue-700 mt-1">{{ (dashboard.by_channel?.br || 0).toLocaleString() }}</p>
        </div>
        <div class="bg-white border border-purple-200 rounded-lg p-4">
          <p class="text-xs text-purple-500">최적</p>
          <p class="text-2xl font-bold text-purple-700 mt-1">{{ (dashboard.by_channel?.opt || 0).toLocaleString() }}</p>
        </div>
        <div class="bg-white border border-orange-200 rounded-lg p-4">
          <p class="text-xs text-orange-500">카페</p>
          <p class="text-2xl font-bold text-orange-700 mt-1">{{ (dashboard.by_channel?.cafe || 0).toLocaleString() }}</p>
        </div>
        <div class="bg-white border border-amber-200 rounded-lg p-4">
          <p class="text-xs text-amber-500">검토 필요</p>
          <p class="text-2xl font-bold text-amber-700 mt-1">{{ (dashboard.review_count || 0).toLocaleString() }}</p>
          <p v-if="syncStatus" class="text-[10px] text-slate-400 mt-2 leading-relaxed">
            마지막 동기화: {{ syncStatus.synced_at?.slice(0, 10) }}
          </p>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <!-- 지점별 게시글 수 -->
        <div class="bg-white border border-slate-200 rounded-lg p-4">
          <h3 class="text-sm font-semibold text-slate-700 mb-3">지점별 게시글 수</h3>
          <div class="space-y-1.5">
            <div v-for="b in dashboard.by_branch" :key="b.branch_name" class="flex items-center gap-2 text-xs">
              <span class="w-20 text-right text-slate-600 truncate shrink-0">{{ b.branch_name }}</span>
              <div class="flex-1 bg-slate-100 rounded-full h-4 overflow-hidden">
                <div class="bg-blue-400 h-full rounded-full transition-all"
                     :style="{ width: (b.cnt / maxBranchCount * 100) + '%' }"></div>
              </div>
              <span class="w-10 text-right text-slate-500 shrink-0">{{ b.cnt }}</span>
            </div>
          </div>
        </div>

        <!-- 월별 발행 추이 -->
        <div class="bg-white border border-slate-200 rounded-lg p-4">
          <h3 class="text-sm font-semibold text-slate-700 mb-3">월별 발행 추이</h3>
          <div class="flex items-end gap-1 h-40">
            <div v-for="m in sortedMonthly" :key="m.month"
                 class="flex-1 flex flex-col items-center justify-end">
              <span class="text-[9px] text-slate-500 mb-1">{{ m.cnt }}</span>
              <div class="w-full bg-purple-400 rounded-t transition-all min-h-[2px]"
                   :style="{ height: (m.cnt / maxMonthlyCount * 120) + 'px' }"></div>
              <span class="text-[9px] text-slate-400 mt-1 rotate-[-45deg] origin-center whitespace-nowrap">
                {{ m.month.slice(2) }}
              </span>
            </div>
          </div>
        </div>

        <!-- 종류별 분포 -->
        <div class="bg-white border border-slate-200 rounded-lg p-4">
          <h3 class="text-sm font-semibold text-slate-700 mb-3">종류별 분포</h3>
          <div class="space-y-2">
            <div v-for="t in dashboard.by_type" :key="t.post_type_main" class="flex items-center gap-2">
              <span class="text-[10px] px-1.5 py-0.5 rounded font-medium shrink-0"
                    :class="typeColor(t.post_type_main)">
                {{ t.post_type_main }}
              </span>
              <div class="flex-1 bg-slate-100 rounded-full h-3 overflow-hidden">
                <div class="bg-emerald-300 h-full rounded-full"
                     :style="{ width: (t.cnt / dashboard.total * 100) + '%' }"></div>
              </div>
              <span class="text-xs text-slate-500 w-14 text-right">{{ t.cnt.toLocaleString() }}</span>
            </div>
          </div>
        </div>

        <!-- 최근 발행 -->
        <div class="bg-white border border-slate-200 rounded-lg p-4">
          <h3 class="text-sm font-semibold text-slate-700 mb-3">최근 발행</h3>
          <div class="space-y-1.5">
            <div v-for="r in dashboard.recent" :key="r.id"
                 class="flex items-center gap-2 text-xs border-b border-slate-50 pb-1.5">
              <span class="text-[10px] px-1 py-0.5 rounded-full shrink-0"
                    :class="channelColor(r.blog_channel)">
                {{ channelLabel(r.blog_channel) }}
              </span>
              <span class="text-slate-600 truncate flex-1">{{ r.clean_title || r.keyword || '-' }}</span>
              <span class="text-slate-400 shrink-0">{{ r.published_at?.slice(5) }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
