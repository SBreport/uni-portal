<script setup lang="ts">
import { ref, watch } from 'vue'
import { getByDevice } from '@/api/explorer'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

const props = defineProps<{
  deviceId: number
}>()

interface DeviceData {
  device_info: {
    id: number
    name: string
    category: string
    summary?: string
    mechanism?: string
  } | null
  branches: Array<{
    branch_id: number
    branch_name: string
    quantity: number
  }>
  events: Array<{
    event_id: number
    title: string
    branch_name: string
    price_min?: number
    price_max?: number
    category?: string
  }>
  papers: Array<{
    id: number
    title: string
    title_ko?: string
    year?: number
  }>
  blogs: Array<{
    id: number
    title: string
    published_at?: string
    keyword?: string
  }>
  treatments: Array<{
    id: number
    name: string
    category?: string
  }>
}

const loading = ref(false)
const data = ref<DeviceData | null>(null)

// Collapsible sections
const openSections = ref<Set<string>>(new Set(['branches', 'events']))

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
    data.value = await getByDevice(id)
  } catch (e) {
    console.error('[ExplorerDeviceDetail] 로드 실패:', e)
  } finally {
    loading.value = false
  }
}

watch(() => props.deviceId, (id) => {
  if (id) load(id)
}, { immediate: true })

function formatPrice(min?: number, max?: number): string {
  if (!min && !max) return '-'
  if (min && max && min !== max) return `${(min / 10000).toFixed(0)}~${(max / 10000).toFixed(0)}만원`
  if (min) return `${(min / 10000).toFixed(0)}만원~`
  return '-'
}
</script>

<template>
  <div class="bg-white border border-slate-200 rounded-lg overflow-hidden">
    <!-- 로딩 -->
    <div v-if="loading" class="flex items-center justify-center py-10">
      <LoadingSpinner message="장비 정보 로딩 중..." />
    </div>

    <template v-else-if="data">
      <!-- 헤더 -->
      <div class="px-5 py-4 bg-blue-50 border-b border-blue-100">
        <div class="flex items-start justify-between">
          <div>
            <h3 class="text-base font-bold text-slate-800">
              {{ data.device_info?.name ?? '알 수 없는 장비' }}
            </h3>
            <span v-if="data.device_info?.category"
              class="inline-block mt-1 px-2 py-0.5 bg-blue-100 text-blue-600 text-xs rounded-full font-medium">
              {{ data.device_info.category }}
            </span>
          </div>
          <span class="text-xs text-slate-400">ID {{ deviceId }}</span>
        </div>
        <p v-if="data.device_info?.summary" class="mt-2 text-sm text-slate-600 leading-relaxed">
          {{ data.device_info.summary }}
        </p>
        <p v-if="data.device_info?.mechanism" class="mt-1 text-xs text-slate-500">
          작용 원리: {{ data.device_info.mechanism }}
        </p>
      </div>

      <!-- 섹션들 -->
      <div class="divide-y divide-slate-100">

        <!-- 보유지점 -->
        <div>
          <button
            @click="toggleSection('branches')"
            class="w-full flex items-center justify-between px-5 py-3 hover:bg-slate-50 transition text-left"
          >
            <span class="text-sm font-semibold text-slate-700">보유 지점</span>
            <div class="flex items-center gap-2">
              <span class="text-xs bg-blue-100 text-blue-600 font-bold px-2 py-0.5 rounded-full">
                {{ data.branches.length }}
              </span>
              <svg class="w-4 h-4 text-slate-400 transition-transform"
                :class="{ 'rotate-180': openSections.has('branches') }"
                fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </button>
          <div v-if="openSections.has('branches')" class="px-5 pb-3">
            <div v-if="data.branches.length" class="space-y-1.5">
              <div v-for="b in data.branches" :key="b.branch_id"
                class="flex items-center justify-between py-1.5 px-3 bg-slate-50 rounded text-sm">
                <span class="text-slate-700">{{ b.branch_name }}</span>
                <span class="text-xs text-slate-500 font-medium">{{ b.quantity }}대</span>
              </div>
            </div>
            <p v-else class="text-sm text-slate-400 py-2">보유 지점 없음</p>
          </div>
        </div>

        <!-- 이벤트 -->
        <div>
          <button
            @click="toggleSection('events')"
            class="w-full flex items-center justify-between px-5 py-3 hover:bg-slate-50 transition text-left"
          >
            <span class="text-sm font-semibold text-slate-700">이벤트</span>
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
                class="py-2 px-3 bg-slate-50 rounded text-sm">
                <div class="flex items-start justify-between gap-2">
                  <span class="text-slate-700 text-xs leading-snug flex-1">{{ ev.title }}</span>
                  <span class="text-xs text-amber-600 font-medium whitespace-nowrap">
                    {{ formatPrice(ev.price_min, ev.price_max) }}
                  </span>
                </div>
                <span class="text-[11px] text-slate-400 mt-0.5 block">{{ ev.branch_name }}</span>
              </div>
            </div>
            <p v-else class="text-sm text-slate-400 py-2">이벤트 없음</p>
          </div>
        </div>

        <!-- 관련 논문 -->
        <div>
          <button
            @click="toggleSection('papers')"
            class="w-full flex items-center justify-between px-5 py-3 hover:bg-slate-50 transition text-left"
          >
            <span class="text-sm font-semibold text-slate-700">관련 논문</span>
            <div class="flex items-center gap-2">
              <span class="text-xs bg-purple-100 text-purple-600 font-bold px-2 py-0.5 rounded-full">
                {{ data.papers.length }}
              </span>
              <svg class="w-4 h-4 text-slate-400 transition-transform"
                :class="{ 'rotate-180': openSections.has('papers') }"
                fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </button>
          <div v-if="openSections.has('papers')" class="px-5 pb-3">
            <div v-if="data.papers.length" class="space-y-1.5">
              <div v-for="p in data.papers" :key="p.id"
                class="py-1.5 px-3 bg-slate-50 rounded text-sm">
                <p class="text-slate-700 text-xs leading-snug">{{ p.title_ko || p.title }}</p>
                <span v-if="p.year" class="text-[11px] text-slate-400">{{ p.year }}년</span>
              </div>
            </div>
            <p v-else class="text-sm text-slate-400 py-2">관련 논문 없음</p>
          </div>
        </div>

        <!-- 관련 블로그 -->
        <div>
          <button
            @click="toggleSection('blogs')"
            class="w-full flex items-center justify-between px-5 py-3 hover:bg-slate-50 transition text-left"
          >
            <span class="text-sm font-semibold text-slate-700">관련 블로그</span>
            <div class="flex items-center gap-2">
              <span class="text-xs bg-emerald-100 text-emerald-600 font-bold px-2 py-0.5 rounded-full">
                {{ data.blogs.length }}
              </span>
              <svg class="w-4 h-4 text-slate-400 transition-transform"
                :class="{ 'rotate-180': openSections.has('blogs') }"
                fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </button>
          <div v-if="openSections.has('blogs')" class="px-5 pb-3">
            <div v-if="data.blogs.length" class="space-y-1.5">
              <div v-for="b in data.blogs" :key="b.id"
                class="py-1.5 px-3 bg-slate-50 rounded text-sm">
                <p class="text-slate-700 text-xs leading-snug">{{ b.title }}</p>
                <div class="flex items-center gap-2 mt-0.5">
                  <span v-if="b.keyword" class="text-[11px] text-blue-500">{{ b.keyword }}</span>
                  <span v-if="b.published_at" class="text-[11px] text-slate-400">{{ b.published_at.slice(0, 10) }}</span>
                </div>
              </div>
            </div>
            <p v-else class="text-sm text-slate-400 py-2">관련 블로그 없음</p>
          </div>
        </div>

        <!-- 관련 시술 -->
        <div>
          <button
            @click="toggleSection('treatments')"
            class="w-full flex items-center justify-between px-5 py-3 hover:bg-slate-50 transition text-left"
          >
            <span class="text-sm font-semibold text-slate-700">관련 시술</span>
            <div class="flex items-center gap-2">
              <span class="text-xs bg-rose-100 text-rose-600 font-bold px-2 py-0.5 rounded-full">
                {{ data.treatments.length }}
              </span>
              <svg class="w-4 h-4 text-slate-400 transition-transform"
                :class="{ 'rotate-180': openSections.has('treatments') }"
                fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </button>
          <div v-if="openSections.has('treatments')" class="px-5 pb-3">
            <div v-if="data.treatments.length" class="flex flex-wrap gap-2">
              <span v-for="t in data.treatments" :key="t.id"
                class="px-2 py-1 bg-rose-50 text-rose-600 text-xs rounded-full font-medium">
                {{ t.name }}
              </span>
            </div>
            <p v-else class="text-sm text-slate-400 py-2">관련 시술 없음</p>
          </div>
        </div>

      </div>
    </template>

    <!-- 에러 / 빈 상태 -->
    <div v-else class="flex items-center justify-center py-10 text-slate-400 text-sm">
      장비 정보를 불러올 수 없습니다
    </div>
  </div>
</template>
