<script setup lang="ts">
import { ref, watch } from 'vue'
import { getByBranch } from '@/api/explorer'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

const props = defineProps<{
  branchId: number
}>()

interface BranchData {
  branch: {
    id: number
    name: string
    region_name?: string
  } | null
  equipment: Array<{
    device_id?: number
    device_name: string
    category?: string
    quantity: number
  }>
  events: Array<{
    event_id: number
    title: string
    category?: string
    price_min?: number
    price_max?: number
  }>
  place_ranking?: {
    keyword: string
    rank: number
  }[]
  webpage_ranking?: {
    keyword: string
    rank: number
  }[]
  blog_count?: number
  complaint_count?: number
}

const loading = ref(false)
const data = ref<BranchData | null>(null)
const openSections = ref<Set<string>>(new Set(['equipment', 'events']))

function toggleSection(key: string) {
  if (openSections.value.has(key)) {
    openSections.value.delete(key)
  } else {
    openSections.value.add(key)
  }
}

async function load(id: number) {
  loading.value = true
  data.value = null
  try {
    data.value = await getByBranch(id)
  } catch (e) {
    console.error('[ExplorerBranchDetail] 로드 실패:', e)
  } finally {
    loading.value = false
  }
}

watch(() => props.branchId, (id) => {
  if (id) load(id)
}, { immediate: true })

const emit = defineEmits<{
  deviceClick: [deviceId: number]
}>()
</script>

<template>
  <div class="bg-white border border-slate-200 rounded-lg overflow-hidden">
    <!-- 로딩 -->
    <div v-if="loading" class="flex items-center justify-center py-10">
      <LoadingSpinner message="지점 정보 로딩 중..." />
    </div>

    <template v-else-if="data">
      <!-- 헤더 -->
      <div class="px-5 py-4 bg-slate-50 border-b border-slate-200">
        <h3 class="text-base font-bold text-slate-800">
          {{ data.branch?.name ?? '알 수 없는 지점' }}
        </h3>
        <p v-if="data.branch?.region_name" class="text-xs text-slate-500 mt-0.5">{{ data.branch.region_name }}</p>
        <!-- 요약 통계 -->
        <div class="flex gap-4 mt-3">
          <div class="text-center">
            <p class="text-lg font-bold text-blue-600">{{ data.equipment.length }}</p>
            <p class="text-[11px] text-slate-400">장비 종류</p>
          </div>
          <div class="text-center">
            <p class="text-lg font-bold text-amber-500">{{ data.events.length }}</p>
            <p class="text-[11px] text-slate-400">이벤트</p>
          </div>
          <div v-if="data.blog_count !== undefined" class="text-center">
            <p class="text-lg font-bold text-emerald-600">{{ data.blog_count }}</p>
            <p class="text-[11px] text-slate-400">블로그</p>
          </div>
          <div v-if="data.complaint_count !== undefined" class="text-center">
            <p class="text-lg font-bold text-rose-500">{{ data.complaint_count }}</p>
            <p class="text-[11px] text-slate-400">민원</p>
          </div>
        </div>
      </div>

      <div class="divide-y divide-slate-100">

        <!-- 보유 장비 -->
        <div>
          <button
            @click="toggleSection('equipment')"
            class="w-full flex items-center justify-between px-5 py-3 hover:bg-slate-50 transition text-left"
          >
            <span class="text-sm font-semibold text-slate-700">보유 장비</span>
            <div class="flex items-center gap-2">
              <span class="text-xs bg-blue-100 text-blue-600 font-bold px-2 py-0.5 rounded-full">
                {{ data.equipment.length }}
              </span>
              <svg class="w-4 h-4 text-slate-400 transition-transform"
                :class="{ 'rotate-180': openSections.has('equipment') }"
                fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </button>
          <div v-if="openSections.has('equipment')" class="px-5 pb-3">
            <div v-if="data.equipment.length" class="space-y-1.5">
              <button
                v-for="eq in data.equipment"
                :key="eq.device_name"
                @click="eq.device_id && emit('deviceClick', eq.device_id)"
                :class="[
                  'w-full flex items-center justify-between py-1.5 px-3 rounded text-sm transition',
                  eq.device_id
                    ? 'bg-slate-50 hover:bg-blue-50 hover:text-blue-700 cursor-pointer'
                    : 'bg-slate-50 cursor-default'
                ]"
              >
                <div class="flex items-center gap-2 text-left">
                  <span class="text-slate-700 text-xs">{{ eq.device_name }}</span>
                  <span v-if="eq.category" class="text-[10px] text-slate-400">{{ eq.category }}</span>
                </div>
                <span class="text-xs text-slate-500 font-medium">{{ eq.quantity }}대</span>
              </button>
            </div>
            <p v-else class="text-sm text-slate-400 py-2">보유 장비 없음</p>
          </div>
        </div>

        <!-- 이벤트 -->
        <div>
          <button
            @click="toggleSection('events')"
            class="w-full flex items-center justify-between px-5 py-3 hover:bg-slate-50 transition text-left"
          >
            <span class="text-sm font-semibold text-slate-700">진행 이벤트</span>
            <div class="flex items-center gap-2">
              <span class="text-xs bg-amber-100 text-amber-600 font-bold px-2 py-0.5 rounded-full">
                {{ data.events.length }}
              </span>
              <svg class="w-4 h-4 text-slate-400 transition-transform"
                :class="{ 'rotate-180': openSections.has('events') }"
                fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </button>
          <div v-if="openSections.has('events')" class="px-5 pb-3">
            <div v-if="data.events.length" class="space-y-1.5">
              <div v-for="ev in data.events" :key="ev.event_id"
                class="py-1.5 px-3 bg-slate-50 rounded text-sm">
                <p class="text-slate-700 text-xs leading-snug">{{ ev.title }}</p>
                <span v-if="ev.category" class="text-[11px] text-slate-400">{{ ev.category }}</span>
              </div>
            </div>
            <p v-else class="text-sm text-slate-400 py-2">진행 이벤트 없음</p>
          </div>
        </div>

        <!-- 플레이스 순위 -->
        <div v-if="data.place_ranking && data.place_ranking.length">
          <button
            @click="toggleSection('place')"
            class="w-full flex items-center justify-between px-5 py-3 hover:bg-slate-50 transition text-left"
          >
            <span class="text-sm font-semibold text-slate-700">플레이스 순위</span>
            <div class="flex items-center gap-2">
              <span class="text-xs bg-green-100 text-green-600 font-bold px-2 py-0.5 rounded-full">
                {{ data.place_ranking.length }}
              </span>
              <svg class="w-4 h-4 text-slate-400 transition-transform"
                :class="{ 'rotate-180': openSections.has('place') }"
                fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </button>
          <div v-if="openSections.has('place')" class="px-5 pb-3">
            <div class="space-y-1.5">
              <div v-for="pr in data.place_ranking" :key="pr.keyword"
                class="flex items-center justify-between py-1.5 px-3 bg-slate-50 rounded text-sm">
                <span class="text-xs text-slate-700">{{ pr.keyword }}</span>
                <span class="text-xs font-bold"
                  :class="pr.rank <= 3 ? 'text-green-600' : pr.rank <= 10 ? 'text-blue-600' : 'text-slate-500'">
                  {{ pr.rank }}위
                </span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </template>

    <div v-else class="flex items-center justify-center py-10 text-slate-400 text-sm">
      지점 정보를 불러올 수 없습니다
    </div>
  </div>
</template>
