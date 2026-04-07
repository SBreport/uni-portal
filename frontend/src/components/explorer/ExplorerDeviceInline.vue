<script setup lang="ts">
import { ref, watch } from 'vue'
import { getByDevice } from '@/api/explorer'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

const props = defineProps<{
  deviceId: number
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
      <p v-if="data.device?.target" class="text-xs text-slate-500">
        <span class="font-medium text-slate-600">적응증:</span> {{ data.device.target }}
      </p>
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
      <p class="text-xs font-semibold text-slate-500 mb-1">
        이벤트
        <span class="ml-1 font-normal text-slate-400">({{ data.events.length }}건)</span>
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
            <tr v-for="(ev, idx) in data.events" :key="idx" class="hover:bg-slate-50">
              <td class="px-3 py-1.5 text-slate-500 truncate max-w-[6rem]">{{ ev.branch_name }}</td>
              <td class="px-3 py-1.5 text-slate-700 leading-snug">{{ ev.display_name }}</td>
              <td class="px-3 py-1.5 text-right text-red-500 font-bold whitespace-nowrap">
                {{ formatPrice(ev.event_price) }}
              </td>
              <td class="px-3 py-1.5 text-right">
                <span v-if="ev.discount_rate" class="text-emerald-600 font-medium">
                  {{ ev.discount_rate }}%
                </span>
                <span v-else class="text-slate-300">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 타 지점 가격 비교 (2개 이상 지점) -->
      <div v-if="data.owning_branches?.length >= 2" class="mt-2 p-2 bg-amber-50 border border-amber-100 rounded text-xs text-amber-700">
        이 장비는 {{ data.owning_branches.length }}개 지점에서 운영 중입니다. 가격 정책이 지점별로 다를 수 있습니다.
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

    <!-- 블로그 키워드 + 최근 글 -->
    <div v-if="data.blog_posts?.length">
      <p class="text-xs font-semibold text-slate-500 mb-1">
        관련 블로그
        <span class="ml-1 font-normal text-slate-400">({{ data.blog_posts.length }}건)</span>
      </p>
      <!-- 키워드 요약 -->
      <div v-if="blogKeywords(data.blog_posts).length" class="flex flex-wrap gap-1 mb-2">
        <span
          v-for="kw in blogKeywords(data.blog_posts).slice(0, 8)"
          :key="kw"
          class="px-2 py-0.5 bg-blue-50 text-blue-600 text-[11px] rounded-full border border-blue-100"
        >
          {{ kw }}
        </span>
      </div>
      <!-- 최근 3건 -->
      <div class="space-y-1">
        <div
          v-for="b in data.blog_posts.slice(0, 3)"
          :key="b.id"
          class="px-3 py-1.5 bg-slate-50 rounded text-xs"
        >
          <p class="text-slate-700 leading-snug">{{ b.title }}</p>
          <div class="flex gap-2 mt-0.5 text-[11px] text-slate-400">
            <span v-if="b.keyword" class="text-blue-500">{{ b.keyword }}</span>
            <span v-if="b.published_at">{{ b.published_at.slice(0, 10) }}</span>
            <span v-if="b.author">{{ b.author }}</span>
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
