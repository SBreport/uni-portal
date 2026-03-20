<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/client'

const auth = useAuthStore()

interface DashboardData {
  branches: number
  equipment: { total: number; photo_done: number }
  events: { label: string; count: number }
  cafe: { label: string; total: number; published: number; pending: number }
  dictionary: { total: number; verified: number }
  recent_syncs: { sync_type: string; added: number; skipped: number; conflicts: number; synced_at: string }[]
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
      <p class="text-slate-400">불러오는 중...</p>
    </div>

    <template v-else-if="data">
      <!-- KPI 카드 상단 -->
      <div class="grid grid-cols-5 gap-3 mb-5">
        <!-- 지점 수 -->
        <div class="bg-white border border-slate-200 rounded-lg px-4 py-4">
          <p class="text-xs text-slate-400 mb-1">전체 지점</p>
          <p class="text-2xl font-bold text-slate-800">{{ data.branches }}</p>
          <p class="text-xs text-slate-400 mt-1">개 지점</p>
        </div>

        <!-- 보유장비 -->
        <router-link to="/equipment" class="bg-white border border-slate-200 rounded-lg px-4 py-4 hover:border-blue-300 transition cursor-pointer block">
          <p class="text-xs text-slate-400 mb-1">보유장비</p>
          <p class="text-2xl font-bold text-blue-600">{{ data.equipment.total.toLocaleString() }}</p>
          <p class="text-xs text-slate-400 mt-1">사진 {{ photoRate }}% 완료</p>
        </router-link>

        <!-- 이벤트 -->
        <router-link to="/events" class="bg-white border border-slate-200 rounded-lg px-4 py-4 hover:border-blue-300 transition cursor-pointer block">
          <p class="text-xs text-slate-400 mb-1">이벤트 ({{ data.events.label }})</p>
          <p class="text-2xl font-bold text-amber-600">{{ data.events.count.toLocaleString() }}</p>
          <p class="text-xs text-slate-400 mt-1">건</p>
        </router-link>

        <!-- 카페 -->
        <router-link to="/cafe" class="bg-white border border-slate-200 rounded-lg px-4 py-4 hover:border-blue-300 transition cursor-pointer block">
          <p class="text-xs text-slate-400 mb-1">카페 원고 ({{ data.cafe.label }})</p>
          <p class="text-2xl font-bold text-emerald-600">{{ data.cafe.published }} <span class="text-base font-normal text-slate-400">/ {{ data.cafe.total }}</span></p>
          <p class="text-xs text-slate-400 mt-1">발행률 {{ cafeRate }}%</p>
        </router-link>

        <!-- 시술사전 -->
        <router-link to="/treatment-info" class="bg-white border border-slate-200 rounded-lg px-4 py-4 hover:border-blue-300 transition cursor-pointer block">
          <p class="text-xs text-slate-400 mb-1">시술사전</p>
          <p class="text-2xl font-bold text-purple-600">{{ data.dictionary.total }}</p>
          <p class="text-xs text-slate-400 mt-1">검증 {{ data.dictionary.verified }}건</p>
        </router-link>
      </div>

      <!-- 하단: 카페 현황 바 + 최근 동기화 -->
      <div class="grid grid-cols-2 gap-4">
        <!-- 카페 발행 현황 -->
        <div class="bg-white border border-slate-200 rounded-lg p-4">
          <h3 class="text-sm font-bold text-slate-700 mb-3">카페 원고 현황 ({{ data.cafe.label }})</h3>
          <div class="space-y-3">
            <div>
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
          </div>
        </div>

        <!-- 최근 동기화 이력 -->
        <div class="bg-white border border-slate-200 rounded-lg p-4">
          <h3 class="text-sm font-bold text-slate-700 mb-3">최근 동기화</h3>
          <div v-if="data.recent_syncs.length" class="space-y-2">
            <div v-for="(s, i) in data.recent_syncs" :key="i"
              class="flex items-center justify-between py-1.5 border-b border-slate-50 last:border-0">
              <div>
                <span class="text-xs font-medium px-2 py-0.5 rounded"
                  :class="{
                    'bg-blue-50 text-blue-600': s.sync_type === 'equipment',
                    'bg-amber-50 text-amber-600': s.sync_type === 'events',
                    'bg-emerald-50 text-emerald-600': s.sync_type === 'cafe',
                  }">
                  {{ s.sync_type === 'equipment' ? '장비' : s.sync_type === 'events' ? '이벤트' : s.sync_type }}
                </span>
                <span class="text-xs text-slate-400 ml-2">+{{ s.added }} / ={{ s.skipped }}</span>
              </div>
              <span class="text-xs text-slate-400">{{ formatDate(s.synced_at) }}</span>
            </div>
          </div>
          <p v-else class="text-sm text-slate-400 text-center py-4">동기화 이력 없음</p>
        </div>
      </div>

      <!-- 바로가기 -->
      <div class="mt-5">
        <h3 class="text-sm font-bold text-slate-700 mb-3">바로가기</h3>
        <div class="grid grid-cols-4 gap-3">
          <router-link to="/equipment" class="bg-white border border-slate-200 rounded-lg p-3 hover:border-blue-300 transition text-center">
            <p class="text-lg mb-1">📦</p>
            <p class="text-xs font-medium text-slate-600">보유장비</p>
          </router-link>
          <router-link to="/events" class="bg-white border border-slate-200 rounded-lg p-3 hover:border-blue-300 transition text-center">
            <p class="text-lg mb-1">📅</p>
            <p class="text-xs font-medium text-slate-600">이벤트</p>
          </router-link>
          <router-link to="/cafe" class="bg-white border border-slate-200 rounded-lg p-3 hover:border-blue-300 transition text-center">
            <p class="text-lg mb-1">☕</p>
            <p class="text-xs font-medium text-slate-600">카페 원고</p>
          </router-link>
          <router-link to="/treatment-info" class="bg-white border border-slate-200 rounded-lg p-3 hover:border-blue-300 transition text-center">
            <p class="text-lg mb-1">📖</p>
            <p class="text-xs font-medium text-slate-600">시술정보</p>
          </router-link>
        </div>
      </div>
    </template>
  </div>
</template>
