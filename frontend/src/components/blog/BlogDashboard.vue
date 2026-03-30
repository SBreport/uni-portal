<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import * as blogApi from '@/api/blog'
import { useAuthStore } from '@/stores/auth'
import { channelLabel, channelColor, typeColor } from '@/utils/blogFormatters'

const auth = useAuthStore()
const dashboard = ref<any>(null)
const loading = ref(false)

// Notion 동기화
const notionToken = ref('')
const syncing = ref(false)
const syncResult = ref<any>(null)
const syncStatus = ref<any>(null)
const showSyncPanel = ref(false)

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

async function runNotionSync() {
  if (!notionToken.value.trim()) return
  syncing.value = true
  syncResult.value = null
  try {
    const { data } = await blogApi.syncNotion(notionToken.value.trim())
    syncResult.value = data
    // 대시보드 새로고침
    const [dashRes, statusRes] = await Promise.all([
      blogApi.getBlogDashboard(),
      blogApi.getNotionSyncStatus(),
    ])
    dashboard.value = dashRes.data
    syncStatus.value = statusRes.data?.last_sync || null
  } catch (e: any) {
    syncResult.value = { message: e.response?.data?.detail || '동기화 실패' }
  } finally {
    syncing.value = false
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
      <!-- Notion 동기화 (관리자만) -->
      <div v-if="auth.role === 'admin'" class="bg-white border border-slate-200 rounded-lg p-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <button @click="showSyncPanel = !showSyncPanel"
                    class="px-3 py-1.5 bg-slate-700 text-white text-xs rounded hover:bg-slate-800 transition-colors">
              Notion 동기화
            </button>
            <span v-if="syncStatus" class="text-[11px] text-slate-400">
              마지막: {{ syncStatus.synced_at }}
              ({{ syncStatus.updated }}건 업데이트, {{ syncStatus.new_posts }}건 신규)
            </span>
            <span v-else class="text-[11px] text-slate-400">동기화 기록 없음</span>
          </div>
        </div>
        <!-- 동기화 패널 (토글) -->
        <div v-if="showSyncPanel" class="mt-3 pt-3 border-t border-slate-100 space-y-2">
          <div class="flex items-center gap-2">
            <input v-model="notionToken" type="password"
                   placeholder="Notion Integration 토큰 (ntn_...)"
                   class="border border-slate-300 rounded px-2 py-1 text-xs w-80 focus:border-blue-400 focus:outline-none" />
            <button @click="runNotionSync" :disabled="syncing || !notionToken.trim()"
                    class="px-3 py-1 bg-blue-500 text-white text-xs rounded hover:bg-blue-600 disabled:opacity-40 transition-colors">
              {{ syncing ? '동기화 중...' : '증분 동기화 실행' }}
            </button>
          </div>
          <p class="text-[10px] text-slate-400">마지막 동기화 이후 노션에서 수정된 게시글만 업데이트합니다.</p>
          <!-- 결과 -->
          <div v-if="syncResult" class="text-xs p-2 rounded"
               :class="syncResult.updated != null ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-600'">
            <p>{{ syncResult.message }}</p>
            <p v-if="syncResult.notion_pages" class="text-[10px] mt-1 text-slate-500">
              Notion {{ syncResult.notion_pages }}건 조회 / {{ syncResult.matched }}건 매칭 / {{ syncResult.new_posts }}건 신규
            </p>
          </div>
        </div>
      </div>

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
