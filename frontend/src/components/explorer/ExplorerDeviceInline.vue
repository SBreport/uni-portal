<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { getByDevice } from '@/api/explorer'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

const props = defineProps<{
  deviceId: number
  currentBranchName?: string  // 현재 보고 있는 지점명 (지점별 탭에서 넘어온 경우)
}>()

interface DeviceData {
  device: {
    id: number
    name: string
    category: string
    summary?: string
    target?: string
    mechanism?: string
    aliases?: string
  } | null
  owning_branches: Array<{
    branch_name: string
    quantity: number
  }>
  events: Array<{
    branch_name: string
    display_name: string
    event_price?: number
    regular_price?: number
    discount_rate?: number
  }>
  papers: Array<{
    id: number
    title: string
    title_ko?: string
    journal?: string
    pub_year?: number
    one_line_summary?: string
  }>
  blog_posts: Array<{
    id: number
    title: string
    keyword?: string
    published_at?: string
    published_url?: string
    branch_name?: string
    author?: string
  }>
  related_treatments: Array<{
    id: number
    name: string
    item_type?: string
  }>
}

const loading = ref(false)
const data = ref<DeviceData | null>(null)
const error = ref(false)

async function load(id: number) {
  loading.value = true
  data.value = null
  error.value = false
  try {
    data.value = await getByDevice(id)
  } catch (e) {
    console.error('[ExplorerDeviceInline] 로드 실패:', e)
    error.value = true
  } finally {
    loading.value = false
  }
}

// 현재 지점 vs 타 지점 분리
const currentBranchEvents = computed(() => {
  if (!data.value?.events || !props.currentBranchName) return []
  return data.value.events.filter(e => e.branch_name === props.currentBranchName)
})
const otherBranchEvents = computed(() => {
  if (!data.value?.events) return data.value?.events ?? []
  if (!props.currentBranchName) return data.value.events
  return data.value.events.filter(e => e.branch_name !== props.currentBranchName)
})
const currentBranchBlogs = computed(() => {
  if (!data.value?.blog_posts || !props.currentBranchName) return []
  return data.value.blog_posts.filter(b => b.branch_name === props.currentBranchName)
})
const otherBranchBlogs = computed(() => {
  if (!data.value?.blog_posts) return data.value?.blog_posts ?? []
  if (!props.currentBranchName) return data.value.blog_posts
  return data.value.blog_posts.filter(b => b.branch_name !== props.currentBranchName)
})

watch(() => props.deviceId, (id) => {
  if (id) load(id)
}, { immediate: true })

function formatPrice(price?: number): string {
  if (!price) return '-'
  return `${(price / 10000).toFixed(0)}만`
}

// Unique keywords from blog_posts
function blogKeywords(posts: DeviceData['blog_posts']): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const p of posts) {
    if (p.keyword && !seen.has(p.keyword)) {
      seen.add(p.keyword)
      out.push(p.keyword)
    }
  }
  return out
}
</script>

<template>
  <!-- Loading -->
  <div v-if="loading" class="py-4 flex justify-center">
    <LoadingSpinner size="sm" message="장비 정보 로딩 중..." />
  </div>

  <!-- Error -->
  <div v-else-if="error" class="py-3 text-xs text-slate-400 text-center">
    장비 정보를 불러올 수 없습니다
  </div>

  <!-- Content -->
  <div v-else-if="data" class="space-y-3 text-sm">

    <!-- 기기 요약 -->
    <div v-if="data.device?.summary || data.device?.target" class="space-y-1">
      <p v-if="data.device?.summary" class="text-xs text-slate-600 leading-relaxed">
        {{ data.device.summary }}
      </p>
      <div v-if="data.device?.target" class="mb-1">
        <p class="text-xs font-semibold text-slate-500 mb-1.5">적응증</p>
        <div class="flex flex-wrap gap-1.5">
          <span
            v-for="(t, idx) in data.device.target.split(/[,，·\s]+/).filter((s: string) => s.trim())"
            :key="idx"
            class="px-2 py-0.5 bg-emerald-50 text-emerald-700 text-xs rounded-full border border-emerald-200"
          >
            {{ t.trim() }}
          </span>
        </div>
      </div>
      <p v-if="data.device?.mechanism" class="text-xs text-slate-500">
        <span class="font-medium text-slate-600">작용 원리:</span> {{ data.device.mechanism }}
      </p>
    </div>

    <!-- 보유 지점 -->
    <div v-if="data.owning_branches?.length">
      <p class="text-xs font-semibold text-slate-500 mb-1">
        보유 지점
        <span class="ml-1 font-normal text-slate-400">({{ data.owning_branches.length }}곳)</span>
      </p>
      <div class="flex flex-wrap gap-1.5">
        <span
          v-for="b in data.owning_branches"
          :key="b.branch_name"
          class="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded border border-blue-100"
        >
          {{ b.branch_name }}
          <span class="text-blue-400 ml-0.5">{{ b.quantity }}대</span>
        </span>
      </div>
    </div>

    <!-- 이벤트 테이블 -->
    <div v-if="data.events?.length">
      <!-- 현재 지점 이벤트 (지점별 탭에서 진입한 경우) -->
      <div v-if="currentBranchEvents.length">
        <p class="text-xs font-semibold text-blue-600 mb-1">
          📍 {{ currentBranchName }} 이벤트
          <span class="ml-1 font-normal text-slate-400">({{ currentBranchEvents.length }}건)</span>
        </p>
        <div class="border border-blue-200 rounded overflow-hidden mb-2">
          <table class="w-full text-xs">
            <thead class="bg-blue-50">
              <tr>
                <th class="text-left px-3 py-1.5 text-blue-500 font-medium">이벤트명</th>
                <th class="text-right px-3 py-1.5 text-blue-500 font-medium w-16">가격</th>
                <th class="text-right px-3 py-1.5 text-blue-500 font-medium w-14">할인</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-blue-50">
              <tr v-for="(ev, idx) in currentBranchEvents" :key="'c'+idx" class="hover:bg-blue-50/50">
                <td class="px-3 py-1.5 text-slate-700 leading-snug">{{ ev.display_name }}</td>
                <td class="px-3 py-1.5 text-right text-red-500 font-bold whitespace-nowrap">
                  {{ formatPrice(ev.event_price) }}
                </td>
                <td class="px-3 py-1.5 text-right">
                  <span v-if="ev.discount_rate" class="text-emerald-600 font-medium">{{ ev.discount_rate }}%</span>
                  <span v-else class="text-slate-300">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 타 지점 이벤트 -->
      <div v-if="otherBranchEvents.length">
        <p class="text-xs font-semibold text-slate-500 mb-1">
          {{ currentBranchName ? '타 지점 이벤트' : '이벤트' }}
          <span class="ml-1 font-normal text-slate-400">({{ otherBranchEvents.length }}건)</span>
        </p>
        <div class="border border-slate-200 rounded overflow-hidden">
          <table class="w-full text-xs">
            <thead class="bg-slate-50">
              <tr>
                <th class="text-left px-3 py-1.5 text-slate-500 font-medium w-24">지점</th>
                <th class="text-left px-3 py-1.5 text-slate-500 font-medium">이벤트명</th>
                <th class="text-right px-3 py-1.5 text-slate-500 font-medium w-16">가격</th>
                <th class="text-right px-3 py-1.5 text-slate-500 font-medium w-14">할인</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr v-for="(ev, idx) in otherBranchEvents" :key="'o'+idx" class="hover:bg-slate-50">
                <td class="px-3 py-1.5 text-slate-500 truncate max-w-[6rem]">{{ ev.branch_name }}</td>
                <td class="px-3 py-1.5 text-slate-700 leading-snug">{{ ev.display_name }}</td>
                <td class="px-3 py-1.5 text-right text-red-500 font-bold whitespace-nowrap">
                  {{ formatPrice(ev.event_price) }}
                </td>
                <td class="px-3 py-1.5 text-right">
                  <span v-if="ev.discount_rate" class="text-emerald-600 font-medium">{{ ev.discount_rate }}%</span>
                  <span v-else class="text-slate-300">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 관련 논문 -->
    <div v-if="data.papers?.length">
      <p class="text-xs font-semibold text-slate-500 mb-1">
        관련 논문
        <span class="ml-1 font-normal text-slate-400">({{ data.papers.length }}건)</span>
      </p>
      <div class="space-y-1">
        <div
          v-for="p in data.papers.slice(0, 5)"
          :key="p.id"
          class="px-3 py-2 bg-purple-50 border border-purple-100 rounded"
        >
          <p class="text-xs text-slate-700 leading-snug">{{ p.title_ko || p.title }}</p>
          <div class="flex gap-2 mt-0.5 text-[11px] text-slate-400">
            <span v-if="p.pub_year">{{ p.pub_year }}년</span>
            <span v-if="p.journal">{{ p.journal }}</span>
          </div>
          <p v-if="p.one_line_summary" class="mt-1 text-[11px] text-slate-500 italic">
            {{ p.one_line_summary }}
          </p>
        </div>
        <p v-if="data.papers.length > 5" class="text-[11px] text-slate-400 pl-1">
          외 {{ data.papers.length - 5 }}편 더 있음
        </p>
      </div>
    </div>

    <!-- 블로그: 현재 지점 -->
    <div v-if="currentBranchBlogs.length">
      <p class="text-xs font-semibold text-blue-600 mb-1">
        📍 {{ currentBranchName }} 블로그
        <span class="ml-1 font-normal text-slate-400">({{ currentBranchBlogs.length }}건)</span>
      </p>
      <div v-if="blogKeywords(currentBranchBlogs).length" class="flex flex-wrap gap-1 mb-2">
        <span v-for="kw in blogKeywords(currentBranchBlogs).slice(0, 8)" :key="kw"
          class="px-2 py-0.5 bg-blue-50 text-blue-600 text-[11px] rounded-full border border-blue-100">
          {{ kw }}
        </span>
      </div>
      <div class="space-y-1 mb-3">
        <div v-for="b in currentBranchBlogs.slice(0, 5)" :key="b.id"
          class="px-3 py-1.5 bg-blue-50/50 rounded text-xs border border-blue-100">
          <a v-if="b.published_url" :href="b.published_url" target="_blank"
            class="text-slate-700 leading-snug hover:text-blue-600 transition block">{{ b.title }}</a>
          <p v-else class="text-slate-700 leading-snug">{{ b.title }}</p>
          <div class="flex gap-2 mt-0.5 text-[11px] text-slate-400">
            <span v-if="b.keyword" class="text-blue-500">{{ b.keyword }}</span>
            <span v-if="b.published_at">{{ b.published_at.slice(0, 10) }}</span>
            <span v-if="b.author">{{ b.author }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 블로그: 타 지점 -->
    <div v-if="otherBranchBlogs.length">
      <p class="text-xs font-semibold text-slate-500 mb-1">
        {{ currentBranchName ? '타 지점 블로그' : '관련 블로그' }}
        <span class="ml-1 font-normal text-slate-400">({{ otherBranchBlogs.length }}건)</span>
      </p>
      <div v-if="blogKeywords(otherBranchBlogs).length" class="flex flex-wrap gap-1 mb-2">
        <span v-for="kw in blogKeywords(otherBranchBlogs).slice(0, 8)" :key="kw"
          class="px-2 py-0.5 bg-slate-100 text-slate-500 text-[11px] rounded-full border border-slate-200">
          {{ kw }}
        </span>
      </div>
      <div class="space-y-1">
        <div v-for="b in otherBranchBlogs.slice(0, 5)" :key="b.id"
          class="px-3 py-1.5 bg-slate-50 rounded text-xs">
          <a v-if="b.published_url" :href="b.published_url" target="_blank"
            class="text-slate-700 leading-snug hover:text-blue-600 transition block">{{ b.title }}</a>
          <p v-else class="text-slate-700 leading-snug">{{ b.title }}</p>
          <div class="flex gap-2 mt-0.5 text-[11px] text-slate-400">
            <span v-if="b.branch_name" class="text-slate-500 font-medium">[{{ b.branch_name }}]</span>
            <span v-if="b.keyword" class="text-blue-500">{{ b.keyword }}</span>
            <span v-if="b.published_at">{{ b.published_at.slice(0, 10) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 관련 시술 칩 -->
    <div v-if="data.related_treatments?.length">
      <p class="text-xs font-semibold text-slate-500 mb-1">관련 시술</p>
      <div class="flex flex-wrap gap-1.5">
        <span
          v-for="t in data.related_treatments"
          :key="t.id"
          class="px-2 py-0.5 bg-rose-50 text-rose-600 text-xs rounded-full border border-rose-100"
        >
          {{ t.name }}
        </span>
      </div>
    </div>

    <!-- 데이터 없음 -->
    <div
      v-if="!data.owning_branches?.length && !data.events?.length && !data.papers?.length && !data.blog_posts?.length"
      class="py-2 text-xs text-slate-400 text-center"
    >
      연결된 정보가 없습니다
    </div>
  </div>
</template>
