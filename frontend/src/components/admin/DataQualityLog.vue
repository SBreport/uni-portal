<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as blogApi from '@/api/blog'

const summary = ref<any>(null)
const details = ref<any>(null)
const activeCategory = ref('')
const loading = ref(false)

const categories = [
  { key: 'deleted', label: '삭제된 글', desc: '블로그가 실제로 삭제되어 404 반환', color: 'red' },
  { key: 'cafe_fail', label: '카페 수집불가', desc: '카페 URL은 로그인 필요하여 제목 추출 불가', color: 'amber' },
  { key: 'needs_review', label: '검토 필요', desc: '제목에 URL이 포함되거나 이상 데이터', color: 'purple' },
  { key: 'no_title', label: '제목 미수집', desc: '스크래핑 실패 또는 미실행', color: 'slate' },
  { key: 'no_branch', label: '지점 미매핑', desc: 'evt_branches와 연결 안 된 유앤아이 글', color: 'sky' },
]

async function loadSummary() {
  try {
    const { data } = await blogApi.getDataQuality()
    summary.value = data
  } catch (e) { console.error(e) }
}

async function toggleDetails(key: string) {
  if (activeCategory.value === key) {
    activeCategory.value = ''
    details.value = null
    return
  }
  activeCategory.value = key
  loading.value = true
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

function statusLabel(item: any) {
  if (item.scraped_title === '(삭제됨)') return { text: '삭제됨', class: 'text-red-400' }
  if (item.scraped_title === '(카페-수집불가)') return { text: '수집불가', class: 'text-amber-400' }
  if (item.needs_review) return { text: '검토필요', class: 'text-purple-400' }
  return { text: '—', class: 'text-slate-300' }
}

const colorMap: Record<string, string> = {
  red: 'bg-red-400', amber: 'bg-amber-400', purple: 'bg-purple-400',
  slate: 'bg-slate-400', sky: 'bg-sky-400',
}
const countColorMap: Record<string, string> = {
  red: 'text-red-500', amber: 'text-amber-500', purple: 'text-purple-500',
  slate: 'text-slate-500', sky: 'text-sky-500',
}

onMounted(loadSummary)
</script>

<template>
  <div class="max-w-4xl space-y-4">
    <!-- 헤더 -->
    <div class="flex items-center justify-between">
      <div>
        <h3 class="text-sm font-bold text-slate-700">블로그 데이터 품질 현황</h3>
        <p class="text-xs text-slate-400 mt-0.5">총 {{ summary?.total?.toLocaleString() ?? '-' }}건 기준 · 항목 클릭 시 상세 목록</p>
      </div>
      <button @click="loadSummary" class="text-xs text-blue-600 hover:text-blue-800 px-2 py-1 rounded hover:bg-blue-50">
        새로고침
      </button>
    </div>

    <!-- 품질 지표 카드 -->
    <div v-if="summary" class="space-y-1">
      <button
        v-for="cat in categories"
        :key="cat.key"
        @click="toggleDetails(cat.key)"
        :class="[
          'w-full flex items-center justify-between px-4 py-3 rounded-lg border transition text-left',
          activeCategory === cat.key
            ? 'border-blue-300 bg-blue-50'
            : 'border-slate-200 bg-white hover:bg-slate-50'
        ]"
      >
        <div class="flex items-center gap-3">
          <span class="w-2.5 h-2.5 rounded-full" :class="colorMap[cat.color]"></span>
          <div>
            <span class="text-sm font-medium text-slate-700">{{ cat.label }}</span>
            <span class="text-xs text-slate-400 ml-2">{{ cat.desc }}</span>
          </div>
        </div>
        <span class="text-sm font-bold" :class="countColorMap[cat.color]">
          {{ (summary[cat.key] ?? 0).toLocaleString() }}건
        </span>
      </button>
    </div>

    <!-- 상세 목록 -->
    <div v-if="activeCategory" class="border border-slate-200 rounded-lg overflow-hidden bg-white">
      <div class="px-4 py-2.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
        <span class="text-xs font-semibold text-slate-600">
          {{ categories.find(c => c.key === activeCategory)?.label }} 상세
        </span>
        <span v-if="details" class="text-xs text-slate-400">
          {{ details.total?.toLocaleString() }}건 중 {{ details.items?.length }}건 표시
        </span>
      </div>

      <div v-if="loading" class="px-4 py-8 text-sm text-slate-400 text-center">로딩 중...</div>

      <div v-else-if="details?.items?.length" class="max-h-[500px] overflow-auto">
        <table class="w-full text-xs">
          <thead class="bg-slate-50 sticky top-0">
            <tr>
              <th class="text-left px-3 py-2 text-slate-500 font-medium w-14">채널</th>
              <th class="text-left px-3 py-2 text-slate-500 font-medium">제목 / 키워드</th>
              <th class="text-left px-3 py-2 text-slate-500 font-medium w-24">지점</th>
              <th class="text-left px-3 py-2 text-slate-500 font-medium w-20">날짜</th>
              <th class="text-left px-3 py-2 text-slate-500 font-medium w-16">상태</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-50">
            <tr v-for="item in details.items" :key="item.id" class="hover:bg-slate-50">
              <td class="px-3 py-2">
                <span class="px-1.5 py-0.5 rounded-full text-[10px] font-medium" :class="channelClass(item.blog_channel)">
                  {{ channelLabel(item.blog_channel) }}
                </span>
              </td>
              <td class="px-3 py-2 max-w-sm">
                <a v-if="item.published_url" :href="item.published_url" target="_blank"
                  class="text-slate-700 hover:text-blue-600 block truncate">
                  {{ item.title || item.keyword || '(없음)' }}
                </a>
                <span v-else class="text-slate-400 block truncate">{{ item.title || item.keyword || '(없음)' }}</span>
              </td>
              <td class="px-3 py-2 text-slate-400 truncate">{{ item.branch_name || '-' }}</td>
              <td class="px-3 py-2 text-slate-400">{{ item.published_at?.slice(0, 10) || '-' }}</td>
              <td class="px-3 py-2">
                <span :class="statusLabel(item).class">{{ statusLabel(item).text }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <p v-else class="px-4 py-6 text-sm text-slate-400 text-center">해당 항목 없음</p>
    </div>
  </div>
</template>
