<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/client'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

const auth = useAuthStore()

interface PlaceSummary {
  total: number; success_today: number; fail_today: number; midal: number; month: string
}
interface BlogData {
  total: number; review_count: number; this_week: number
  weekly: { week: string; week_start: string; cnt: number }[]
}
interface DashboardData {
  branches: number
  equipment: { total: number; photo_done: number }
  events: { label: string; count: number }
  cafe: { label: string; total: number; published: number; pending: number }
  dictionary: { total: number; verified: number }
  recent_syncs: { sync_type: string; added: number; skipped: number; conflicts: number; synced_at: string; triggered_by?: string | null; detail?: string | null }[]
  blog: BlogData
  place: PlaceSummary
  webpage: PlaceSummary
}

const data = ref<DashboardData | null>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await api.get('/dashboard')
    data.value = res.data
  } catch (e) {
    console.error('Dashboard load failed:', e)
  } finally {
    loading.value = false
  }
})

const cafeRate = computed(() => {
  if (!data.value || !data.value.cafe.total) return 0
  return Math.round((data.value.cafe.published / data.value.cafe.total) * 100)
})

const photoRate = computed(() => {
  if (!data.value || !data.value.equipment.total) return 0
  return Math.round((data.value.equipment.photo_done / data.value.equipment.total) * 100)
})

const placeSuccessRate = computed(() => {
  if (!data.value || !data.value.place.total) return 0
  return Math.round((data.value.place.success_today / data.value.place.total) * 100)
})

/** 주간 차트 최대값 대비 높이 비율 */
const weeklyBars = computed(() => {
  if (!data.value?.blog?.weekly?.length) return []
  const items = [...data.value.blog.weekly].reverse().slice(-6)
  const max = Math.max(...items.map(w => w.cnt), 1)
  return items.map(w => ({
    label: w.week_start.slice(5),  // MM-DD
    cnt: w.cnt,
    pct: Math.round((w.cnt / max) * 100),
  }))
})

function formatDate(iso: string) {
  if (!iso) return '-'
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

function isFailedSync(detail?: string | null): boolean {
  return !!detail && detail.startsWith('실패')
}
</script>

<template>
  <div class="p-5 max-w-6xl">
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

      <!-- ━━ 섹션 1: 마케팅 성과 ━━ -->
      <h3 class="text-sm font-bold text-slate-500 mb-3 tracking-wide">마케팅 채널</h3>
      <div class="grid grid-cols-3 gap-4 mb-6">
        <!-- 블로그 -->
        <router-link to="/blog"
          class="bg-white border border-slate-200 rounded-lg p-4 hover:border-blue-300 transition block">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-semibold text-slate-700">블로그</span>
            <span class="text-xs text-slate-400">총 {{ data.blog.total.toLocaleString() }}건</span>
          </div>
          <div class="flex items-end gap-4">
            <div>
              <p class="text-2xl font-bold text-blue-600">{{ data.blog.this_week }}</p>
              <p class="text-xs text-slate-400">이번 주 발행</p>
            </div>
            <div v-if="data.blog.review_count" class="text-right">
              <p class="text-lg font-bold text-red-500">{{ data.blog.review_count.toLocaleString() }}</p>
              <p class="text-xs text-red-400">검토 필요</p>
            </div>
          </div>
        </router-link>

        <!-- 플레이스 -->
        <router-link to="/place"
          class="bg-white border border-slate-200 rounded-lg p-4 hover:border-blue-300 transition block">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-semibold text-slate-700">플레이스 상위노출</span>
            <span class="text-xs text-slate-400">{{ data.place.month }}</span>
          </div>
          <div class="flex items-end gap-3">
            <div>
              <p class="text-2xl font-bold text-blue-600">{{ data.place.success_today }}</p>
              <p class="text-xs text-slate-400">성공</p>
            </div>
            <div>
              <p class="text-lg font-bold text-red-500">{{ data.place.fail_today }}</p>
              <p class="text-xs text-red-400">실패</p>
            </div>
            <div>
              <p class="text-lg font-bold text-slate-400">{{ data.place.midal }}</p>
              <p class="text-xs text-slate-400">미점유</p>
            </div>
          </div>
          <div class="mt-2 w-full bg-slate-100 rounded-full h-1.5">
            <div class="bg-blue-500 h-1.5 rounded-full transition-all"
              :style="{ width: placeSuccessRate + '%' }"></div>
          </div>
        </router-link>

        <!-- 웹페이지 -->
        <router-link to="/webpage"
          class="bg-white border border-slate-200 rounded-lg p-4 hover:border-blue-300 transition block">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-semibold text-slate-700">웹페이지 노출</span>
            <span class="text-xs text-slate-400">{{ data.webpage.month }}</span>
          </div>
          <div class="flex items-end gap-3">
            <div>
              <p class="text-2xl font-bold text-emerald-600">{{ data.webpage.success_today }}</p>
              <p class="text-xs text-slate-400">노출</p>
            </div>
            <div>
              <p class="text-lg font-bold text-amber-500">{{ data.webpage.fail_today }}</p>
              <p class="text-xs text-amber-400">미노출</p>
            </div>
            <div>
              <p class="text-lg font-bold text-slate-400">{{ data.webpage.midal }}</p>
              <p class="text-xs text-slate-400">미점유</p>
            </div>
          </div>
        </router-link>
      </div>

      <!-- ━━ 섹션 2: 카페 진행 + 블로그 주간 추이 ━━ -->
      <div class="grid grid-cols-2 gap-4 mb-6">
        <!-- 카페 발행 현황 -->
        <router-link to="/cafe"
          class="bg-white border border-slate-200 rounded-lg p-4 hover:border-blue-300 transition block">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-semibold text-slate-700">카페 원고 ({{ data.cafe.label }})</h3>
            <span class="text-xs text-emerald-600 font-bold">{{ cafeRate }}%</span>
          </div>
          <div class="mb-3">
            <div class="flex justify-between text-xs text-slate-500 mb-1">
              <span>발행 진행률</span>
              <span>{{ data.cafe.published }} / {{ data.cafe.total }}</span>
            </div>
            <div class="w-full bg-slate-100 rounded-full h-2.5">
              <div class="bg-emerald-500 h-2.5 rounded-full transition-all" :style="{ width: cafeRate + '%' }"></div>
            </div>
          </div>
          <div class="grid grid-cols-3 gap-2 text-center">
            <div class="bg-slate-50 rounded p-2">
              <p class="text-lg font-bold text-amber-500">{{ data.cafe.total - data.cafe.published - data.cafe.pending }}</p>
              <p class="text-xs text-slate-400">진행중</p>
            </div>
            <div class="bg-slate-50 rounded p-2">
              <p class="text-lg font-bold text-emerald-500">{{ data.cafe.published }}</p>
              <p class="text-xs text-slate-400">발행완료</p>
            </div>
            <div class="bg-slate-50 rounded p-2">
              <p class="text-lg font-bold text-slate-400">{{ data.cafe.pending }}</p>
              <p class="text-xs text-slate-400">미착수</p>
            </div>
          </div>
        </router-link>

        <!-- 블로그 주간 발행 추이 -->
        <router-link to="/blog"
          class="bg-white border border-slate-200 rounded-lg p-4 hover:border-blue-300 transition block">
          <h3 class="text-sm font-semibold text-slate-700 mb-3">블로그 주간 발행 추이
            <span class="text-xs font-normal text-slate-400 ml-1">최근 6주</span>
          </h3>
          <div v-if="weeklyBars.length" class="flex items-end gap-2 h-28">
            <div v-for="bar in weeklyBars" :key="bar.label"
              class="flex-1 flex flex-col items-center justify-end h-full">
              <span class="text-xs font-bold text-slate-600 mb-1">{{ bar.cnt }}</span>
              <div class="w-full bg-violet-400 rounded-t transition-all"
                :style="{ height: bar.pct + '%', minHeight: '4px' }"></div>
              <span class="text-[10px] text-slate-400 mt-1">{{ bar.label }}</span>
            </div>
          </div>
          <p v-else class="text-sm text-slate-400 text-center py-8">데이터 없음</p>
        </router-link>
      </div>

      <!-- ━━ 섹션 3: 운영 현황 (축소) ━━ -->
      <h3 class="text-sm font-bold text-slate-500 mb-3 tracking-wide">운영 현황</h3>
      <div class="grid grid-cols-4 gap-3 mb-6">
        <div class="bg-white border border-slate-200 rounded-lg px-4 py-3">
          <p class="text-xs text-slate-400 mb-0.5">전체 지점</p>
          <p class="text-xl font-bold text-slate-800">{{ data.branches }}<span class="text-xs font-normal text-slate-400 ml-1">개</span></p>
        </div>
        <router-link to="/equipment"
          class="bg-white border border-slate-200 rounded-lg px-4 py-3 hover:border-blue-300 transition block">
          <p class="text-xs text-slate-400 mb-0.5">보유장비</p>
          <p class="text-xl font-bold text-blue-600">{{ data.equipment.total.toLocaleString() }}
            <span class="text-xs font-normal text-slate-400 ml-1">사진 {{ photoRate }}%</span>
          </p>
        </router-link>
        <router-link to="/events"
          class="bg-white border border-slate-200 rounded-lg px-4 py-3 hover:border-blue-300 transition block">
          <p class="text-xs text-slate-400 mb-0.5">이벤트 ({{ data.events.label }})</p>
          <p class="text-xl font-bold text-amber-600">{{ data.events.count.toLocaleString() }}<span class="text-xs font-normal text-slate-400 ml-1">건</span></p>
        </router-link>
        <router-link to="/treatment-info"
          class="bg-white border border-slate-200 rounded-lg px-4 py-3 hover:border-blue-300 transition block">
          <p class="text-xs text-slate-400 mb-0.5">시술사전</p>
          <p class="text-xl font-bold text-purple-600">{{ data.dictionary.total }}
            <span class="text-xs font-normal text-slate-400 ml-1">검증 {{ data.dictionary.verified }}건</span>
          </p>
        </router-link>
      </div>

      <!-- ━━ 섹션 4: 동기화 이력 (admin만 표시) ━━ -->
      <div v-if="auth.role === 'admin' && data.recent_syncs.length" class="mb-6">
        <h3 class="text-sm font-bold text-slate-500 mb-3 tracking-wide">
          최근 동기화
          <span class="text-xs font-normal text-slate-400 ml-2">매일 18:30 자동 실행</span>
        </h3>
        <div class="bg-white border border-slate-200 rounded-lg p-4">
          <div class="space-y-2">
            <div v-for="(s, i) in data.recent_syncs" :key="i"
              class="border-b border-slate-50 last:border-0"
              :class="isFailedSync(s.detail) ? 'bg-red-50 border-l-2 border-red-300 pl-2' : ''">
              <div class="flex flex-col gap-0.5 py-1.5">
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <span class="text-xs font-medium px-2 py-0.5 rounded"
                      :class="{
                        'bg-blue-50 text-blue-600': s.sync_type === 'equipment',
                        'bg-amber-50 text-amber-600': s.sync_type === 'events',
                        'bg-emerald-50 text-emerald-600': s.sync_type === 'cafe',
                        'bg-rose-50 text-rose-600': s.sync_type === 'place_sheets_to_db',
                        'bg-violet-50 text-violet-600': s.sync_type === 'webpage_sheets_to_db',
                      }">
                      {{
                        s.sync_type === 'equipment' ? '장비' :
                        s.sync_type === 'events' ? '이벤트' :
                        s.sync_type === 'cafe' ? '카페' :
                        s.sync_type === 'place_sheets_to_db' ? '플레이스' :
                        s.sync_type === 'webpage_sheets_to_db' ? '웹페이지' :
                        s.sync_type
                      }}
                    </span>
                    <span v-if="isFailedSync(s.detail)"
                      class="text-xs font-medium px-1.5 py-0.5 rounded bg-red-100 text-red-700">
                      실패
                    </span>
                    <span class="text-xs px-1.5 py-0.5 rounded"
                      :class="s.triggered_by === 'auto' ? 'bg-sky-50 text-sky-500' : 'bg-slate-100 text-slate-400'">
                      {{ s.triggered_by === 'auto' ? '자동' : '수동' }}
                    </span>
                    <span class="text-xs text-slate-400">+{{ s.added }} / ={{ s.skipped }}</span>
                  </div>
                  <span class="text-xs text-slate-400">{{ formatDate(s.synced_at) }}</span>
                </div>
                <p v-if="isFailedSync(s.detail)"
                  class="text-xs text-red-500 line-clamp-1">{{ s.detail }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

    </template>
  </div>
</template>
