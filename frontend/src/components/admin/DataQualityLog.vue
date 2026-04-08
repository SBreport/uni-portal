<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as blogApi from '@/api/blog'

const summary = ref<any>(null)
const details = ref<any>(null)
const activeCategory = ref('deleted')
const loading = ref(false)

const categories = [
  { key: 'deleted', label: '삭제된 글', color: 'text-red-500 border-red-400' },
  { key: 'cafe_fail', label: '카페 수집불가', color: 'text-amber-500 border-amber-400' },
  { key: 'needs_review', label: '검토 필요', color: 'text-purple-500 border-purple-400' },
  { key: 'no_title', label: '제목 미수집', color: 'text-slate-500 border-slate-400' },
  { key: 'no_branch', label: '지점 미매핑', color: 'text-sky-500 border-sky-400' },
]

async function loadSummary() {
  try {
    const { data } = await blogApi.getDataQuality()
    summary.value = data
  } catch (e) { console.error(e) }
}

async function selectCategory(key: string) {
  activeCategory.value = key
  loading.value = true
  details.value = null
  try {
    const { data } = await blogApi.getDataQualityDetails(key, 100)
    details.value = data
  } catch (e) { console.error(e) }
  finally { loading.value = false }
}

function channelLabel(ch: string) {
  if (ch === 'br') return '브블'
  if (ch === 'opt') return '최블'
  if (ch === 'cafe') return '카페'
  return ch || '-'
}

function channelClass(ch: string) {
  if (ch === 'br') return 'bg-emerald-50 text-emerald-600'
  if (ch === 'opt') return 'bg-violet-50 text-violet-600'
  return 'bg-slate-100 text-slate-500'
}

function statusText(item: any) {
  if (item.scraped_title === '(삭제됨)') return '삭제됨'
  if (item.scraped_title === '(카페-수집불가)') return '수집불가'
  if (item.needs_review) return '검토필요'
  return '—'
}

function statusClass(item: any) {
  if (item.scraped_title === '(삭제됨)') return 'text-red-400'
  if (item.scraped_title === '(카페-수집불가)') return 'text-amber-400'
  if (item.needs_review) return 'text-purple-400'
  return 'text-slate-300'
}

onMounted(() => {
  loadSummary()
  selectCategory('deleted')
})
</script>

<template>
  <div class="max-w-3xl">
    <!-- 헤더 -->
    <div class="flex items-center justify-between mb-3">
      <p class="text-xs text-slate-400">총 {{ summary?.total?.toLocaleString() ?? '-' }}건 기준</p>
      <button @click="loadSummary" class="text-xs text-blue-600 hover:text-blue-800">새로고침</button>
    </div>

    <!-- 카테고리 가로 탭 -->
    <div v-if="summary" class="flex gap-2 mb-4">
      <button
        v-for="cat in categories"
        :key="cat.key"
        @click="selectCategory(cat.key)"
        :class="[
          'px-3 py-2 rounded-lg border text-center transition min-w-0',
          activeCategory === cat.key
            ? 'border-blue-400 bg-blue-50'
            : 'border-slate-200 bg-white hover:bg-slate-50'
        ]"
      >
        <p class="text-lg font-bold" :class="cat.color.split(' ')[0]">
          {{ (summary[cat.key] ?? 0).toLocaleString() }}
        </p>
        <p class="text-[11px] text-slate-500 whitespace-nowrap">{{ cat.label }}</p>
      </button>
    </div>

    <!-- 상세 테이블 -->
    <div class="border border-slate-200 rounded-lg overflow-hidden bg-white">
      <div class="px-4 py-2.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
        <span class="text-xs font-semibold text-slate-600">
          {{ categories.find(c => c.key === activeCategory)?.label }} 상세
        </span>
        <span v-if="details" class="text-xs text-slate-400">
          {{ details.total?.toLocaleString() }}건 중 {{ details.items?.length }}건 표시
        </span>
      </div>

      <div v-if="loading" class="flex items-center justify-center py-16">
        <div class="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
        <span class="ml-2 text-sm text-slate-400">로딩 중...</span>
      </div>

      <div v-else-if="details?.items?.length" class="overflow-auto" style="max-height: 500px;">
        <div class="divide-y divide-slate-50">
            <div v-for="item in details.items" :key="item.id"
              class="px-3 py-2.5 hover:bg-slate-50 flex items-start gap-2">
              <span class="shrink-0 mt-0.5 px-1.5 py-0.5 rounded-full text-[10px] font-medium"
                :class="channelClass(item.blog_channel)">
                {{ channelLabel(item.blog_channel) }}
              </span>
              <div class="min-w-0 flex-1">
                <a v-if="item.published_url" :href="item.published_url" target="_blank"
                  class="text-xs text-slate-700 hover:text-blue-600 block truncate leading-snug">
                  {{ item.title || item.keyword || '(없음)' }}
                </a>
                <span v-else class="text-xs text-slate-400 block truncate leading-snug">
                  {{ item.title || item.keyword || '(없음)' }}
                </span>
                <div class="flex items-center gap-2 mt-0.5 text-[10px] text-slate-400">
                  <span v-if="item.branch_name">{{ item.branch_name }}</span>
                  <span>{{ item.published_at?.slice(0, 10) || '-' }}</span>
                  <span :class="statusClass(item)">{{ statusText(item) }}</span>
                </div>
              </div>
            </div>
        </div>
      </div>

      <div v-else class="flex items-center justify-center py-16 text-sm text-slate-400">
        해당 항목 없음
      </div>
    </div>
  </div>
</template>
