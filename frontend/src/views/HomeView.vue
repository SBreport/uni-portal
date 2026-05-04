<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/client'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

const auth = useAuthStore()

interface ChannelSummary {
  as_of: string | null
  success: number
  leak: number
  midal: number
  total: number
}
interface BlogData {
  total: number
  review_count: number
  this_week: number
  last_week: number
}
interface DashboardData {
  branches: number
  equipment: { total: number; photo_done: number }
  events: { label: string; count: number }
  dictionary: { total: number; verified: number }
  recent_syncs: { sync_type: string; added: number; skipped: number; conflicts: number; synced_at: string; triggered_by?: string | null; detail?: string | null; is_failed?: number }[]
  blog: BlogData
  place: ChannelSummary
  webpage: ChannelSummary
  issues: { type: string; label: string; count: number; link: string }[]
}

const data = ref<DashboardData | null>(null)
const loading = ref(true)
const nextJobs = ref<{ id: string; label: string; next_run: string | null }[]>([])

onMounted(async () => {
  try {
    const res = await api.get('/dashboard')
    data.value = res.data
    if (auth.role === 'admin') {
      try {
        const s = await api.get('/admin/scheduler-status')
        nextJobs.value = s.data.jobs || []
      } catch (e) {
        console.warn('scheduler-status 호출 실패:', e)
      }
    }
  } catch (e) {
    console.error('Dashboard load failed:', e)
  } finally {
    loading.value = false
  }
})

const photoRate = computed(() => {
  if (!data.value || !data.value.equipment.total) return 0
  return Math.round((data.value.equipment.photo_done / data.value.equipment.total) * 100)
})

function formatJobNextRun(iso: string | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  const tomorrow = new Date(now)
  tomorrow.setDate(now.getDate() + 1)
  const isTomorrow = d.toDateString() === tomorrow.toDateString()
  const time = `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
  if (isToday) return `오늘 ${time}`
  if (isTomorrow) return `내일 ${time}`
  return `${d.getMonth() + 1}/${d.getDate()} ${time}`
}

const sortedNextJobs = computed(() => {
  return [...nextJobs.value]
    .filter(j => j.next_run)
    .sort((a, b) => new Date(a.next_run!).getTime() - new Date(b.next_run!).getTime())
})

const totalIssueCount = computed(() => {
  if (!data.value?.issues) return 0
  return data.value.issues.reduce((sum, i) => sum + i.count, 0)
})

function formatDate(iso: string) {
  if (!iso) return '-'
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}
</script>

<template>
  <div class="p-5">
    <!-- 헤더 -->
    <div class="mb-6">
      <h2 class="text-xl font-bold text-slate-800">대시보드</h2>
      <p class="text-sm text-slate-400 mt-1">
        <span class="font-medium text-slate-600">{{ auth.username }}</span>님 환영합니다
      </p>
    </div>

    <!-- 로딩 -->
    <div v-if="loading" class="flex items-center justify-center h-64">
      <LoadingSpinner />
    </div>

    <template v-else-if="data">
      <!-- 운영 이슈 배너 (admin only, 0건이면 hidden) -->
      <div v-if="auth.role === 'admin' && data.issues && data.issues.length" class="mb-6">
        <div class="bg-red-50 border border-red-200 rounded-lg p-3">
          <div class="flex items-center justify-between mb-2">
            <p class="text-sm font-bold text-red-700">운영 이슈 {{ totalIssueCount }}건</p>
          </div>
          <div class="flex flex-col gap-1">
            <router-link v-for="issue in data.issues" :key="issue.type"
                :to="{ path: '/admin', query: { tab: 'sb-checker' } }"
                class="flex items-center justify-between py-1 px-2 bg-white rounded border border-red-100 hover:bg-red-50 transition-colors">
              <span class="text-xs text-slate-700">{{ issue.label }}</span>
              <span class="text-xs font-bold text-red-600 tabular-nums">{{ issue.count }}건</span>
            </router-link>
          </div>
        </div>
      </div>

      <!-- 섹션 1: 마케팅 채널 (3 카드) -->
      <h3 class="text-sm font-bold text-slate-500 mb-3 tracking-wide">마케팅 채널</h3>
      <div class="grid grid-cols-[repeat(auto-fit,minmax(280px,1fr))] gap-4 mb-6">
        <!-- 블로그: 이번주 / 저번주 -->
        <router-link to="/blog"
          class="bg-white border border-slate-200 rounded-lg p-4 hover:border-blue-300 transition block">
          <div class="flex items-center justify-between mb-3">
            <span class="text-sm font-semibold text-slate-700">블로그 발행</span>
            <span class="text-xs text-slate-400">총 {{ data.blog.total.toLocaleString() }}건</span>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <p class="text-xs text-slate-400 mb-1">이번주</p>
              <p class="text-2xl font-bold text-blue-600 tabular-nums">{{ data.blog.this_week }}</p>
            </div>
            <div>
              <p class="text-xs text-slate-400 mb-1">저번주</p>
              <p class="text-2xl font-bold text-slate-500 tabular-nums">{{ data.blog.last_week }}</p>
            </div>
          </div>
          <p v-if="data.blog.review_count" class="text-xs text-red-500 mt-3">
            검토 필요 {{ data.blog.review_count.toLocaleString() }}건
          </p>
        </router-link>

        <!-- 플레이스: D-2 기준 성공/이탈/미점유 -->
        <router-link to="/place"
          class="bg-white border border-slate-200 rounded-lg p-4 hover:border-blue-300 transition block">
          <div class="flex items-center justify-between mb-3">
            <span class="text-sm font-semibold text-slate-700">플레이스 상위노출</span>
            <span class="text-xs text-slate-400">{{ data.place.as_of || '-' }} 기준</span>
          </div>
          <div class="grid grid-cols-3 gap-2">
            <div>
              <p class="text-xs text-slate-400 mb-1">성공</p>
              <p class="text-2xl font-bold text-blue-600 tabular-nums">{{ data.place.success }}</p>
            </div>
            <div>
              <p class="text-xs text-slate-400 mb-1">이탈</p>
              <p class="text-2xl font-bold text-rose-500 tabular-nums">{{ data.place.leak }}</p>
            </div>
            <div>
              <p class="text-xs text-slate-400 mb-1">미점유</p>
              <p class="text-2xl font-bold text-slate-400 tabular-nums">{{ data.place.midal }}</p>
            </div>
          </div>
        </router-link>

        <!-- 웹페이지: D-2 기준 -->
        <router-link to="/webpage"
          class="bg-white border border-slate-200 rounded-lg p-4 hover:border-blue-300 transition block">
          <div class="flex items-center justify-between mb-3">
            <span class="text-sm font-semibold text-slate-700">웹페이지 노출</span>
            <span class="text-xs text-slate-400">{{ data.webpage.as_of || '-' }} 기준</span>
          </div>
          <div class="grid grid-cols-3 gap-2">
            <div>
              <p class="text-xs text-slate-400 mb-1">성공</p>
              <p class="text-2xl font-bold text-emerald-600 tabular-nums">{{ data.webpage.success }}</p>
            </div>
            <div>
              <p class="text-xs text-slate-400 mb-1">이탈</p>
              <p class="text-2xl font-bold text-amber-500 tabular-nums">{{ data.webpage.leak }}</p>
            </div>
            <div>
              <p class="text-xs text-slate-400 mb-1">미점유</p>
              <p class="text-2xl font-bold text-slate-400 tabular-nums">{{ data.webpage.midal }}</p>
            </div>
          </div>
        </router-link>
      </div>

      <!-- 섹션 2: 운영 현황 (4 카드) -->
      <h3 class="text-sm font-bold text-slate-500 mb-3 tracking-wide">운영 현황</h3>
      <div class="grid grid-cols-[repeat(auto-fit,minmax(180px,1fr))] gap-3 mb-6">
        <router-link to="/branches"
          class="bg-white border border-slate-200 rounded-lg p-3 hover:border-blue-300 transition block">
          <p class="text-xs text-slate-400 mb-0.5">전체 지점</p>
          <p class="text-xl font-bold text-slate-700 tabular-nums">{{ data.branches }}<span class="text-xs font-normal text-slate-400 ml-1">개</span></p>
        </router-link>
        <router-link to="/equipment"
          class="bg-white border border-slate-200 rounded-lg p-3 hover:border-blue-300 transition block">
          <p class="text-xs text-slate-400 mb-0.5">보유장비</p>
          <p class="text-xl font-bold text-blue-600 tabular-nums">{{ data.equipment.total.toLocaleString() }}
            <span class="text-xs font-normal text-slate-400 ml-1">사진 {{ photoRate }}%</span>
          </p>
        </router-link>
        <router-link to="/events"
          class="bg-white border border-slate-200 rounded-lg p-3 hover:border-blue-300 transition block">
          <p class="text-xs text-slate-400 mb-0.5">이벤트 ({{ data.events.label }})</p>
          <p class="text-xl font-bold text-amber-600 tabular-nums">{{ data.events.count.toLocaleString() }}
            <span class="text-xs font-normal text-slate-400 ml-1">건</span>
          </p>
        </router-link>
        <router-link to="/encyclopedia"
          class="bg-white border border-slate-200 rounded-lg p-3 hover:border-blue-300 transition block">
          <p class="text-xs text-slate-400 mb-0.5">시술사전</p>
          <p class="text-xl font-bold text-purple-600 tabular-nums">{{ data.dictionary.total }}
            <span class="text-xs font-normal text-slate-400 ml-1">검증 {{ data.dictionary.verified }}건</span>
          </p>
        </router-link>
      </div>

      <!-- 섹션 3: 동기화 (admin only) -->
      <div v-if="auth.role === 'admin'" class="mb-6">
        <h3 class="text-sm font-bold text-slate-500 mb-3 tracking-wide">동기화</h3>
        <div class="grid grid-cols-[repeat(auto-fit,minmax(360px,1fr))] gap-4">
          <!-- 최근 동기화 -->
          <div class="bg-white border border-slate-200 rounded-lg p-4">
            <p class="text-xs font-medium text-slate-500 mb-3">최근 동기화</p>
            <div v-if="data.recent_syncs && data.recent_syncs.length" class="flex flex-col gap-1.5">
              <div v-for="(s, i) in data.recent_syncs" :key="i"
                   class="flex items-center justify-between text-xs"
                   :class="s.is_failed ? 'bg-red-50 border-l-2 border-red-300 pl-2 py-1' : 'py-1'">
                <div class="flex items-center gap-2 min-w-0">
                  <span class="text-xs font-medium px-2 py-0.5 rounded shrink-0"
                    :class="{
                      'bg-blue-50 text-blue-600': s.sync_type === 'equipment',
                      'bg-amber-50 text-amber-600': s.sync_type === 'events',
                      'bg-emerald-50 text-emerald-600': s.sync_type === 'cafe',
                      'bg-rose-50 text-rose-600': s.sync_type === 'place_sheets_to_db',
                      'bg-violet-50 text-violet-600': s.sync_type === 'webpage_sheets_to_db',
                      'bg-indigo-50 text-indigo-600': s.sync_type === 'blog_notion_sync',
                      'bg-slate-100 text-slate-500': !['equipment','events','cafe','place_sheets_to_db','webpage_sheets_to_db','blog_notion_sync'].includes(s.sync_type),
                    }">
                    {{
                      s.sync_type === 'place_sheets_to_db' ? '플레이스' :
                      s.sync_type === 'webpage_sheets_to_db' ? '웹페이지' :
                      s.sync_type === 'blog_notion_sync' ? '블로그 노션' :
                      s.sync_type === 'equipment' ? '장비' :
                      s.sync_type === 'events' ? '이벤트' :
                      s.sync_type === 'cafe' ? '카페' :
                      s.sync_type
                    }}
                  </span>
                  <span class="text-xs px-1.5 py-0.5 rounded shrink-0"
                    :class="s.triggered_by === 'auto' ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-500'">
                    {{ s.triggered_by === 'auto' ? '자동' : '수동' }}
                  </span>
                  <span class="text-xs text-slate-400 truncate">+{{ s.added }} / ={{ s.skipped }}</span>
                </div>
                <span class="text-xs text-slate-400 shrink-0 ml-2">{{ formatDate(s.synced_at) }}</span>
              </div>
            </div>
            <p v-else class="text-xs text-slate-400">동기화 이력 없음</p>
          </div>

          <!-- 다음 자동 실행 -->
          <div class="bg-white border border-slate-200 rounded-lg p-4">
            <p class="text-xs font-medium text-slate-500 mb-3">다음 자동 실행</p>
            <div v-if="sortedNextJobs.length" class="grid grid-cols-1 gap-1.5">
              <div v-for="job in sortedNextJobs" :key="job.id" class="flex items-center justify-between text-xs">
                <span class="text-slate-600">{{ job.label || job.id }}</span>
                <span class="font-medium text-slate-700 tabular-nums">{{ formatJobNextRun(job.next_run) }}</span>
              </div>
            </div>
            <p v-else class="text-xs text-slate-400">스케줄 없음</p>
          </div>
        </div>
      </div>

    </template>
  </div>
</template>
