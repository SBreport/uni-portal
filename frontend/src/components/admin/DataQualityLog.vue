<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as blogApi from '@/api/blog'

const summary = ref<any>(null)
const details = ref<any>(null)
const activeCategory = ref('deleted')
const loading = ref(false)

const categories = [
  { key: 'deleted', label: '삭제된 글', desc: '404 반환', color: 'bg-red-400', countColor: 'text-red-500' },
  { key: 'cafe_fail', label: '카페 수집불가', desc: '로그인 필요', color: 'bg-amber-400', countColor: 'text-amber-500' },
  { key: 'needs_review', label: '검토 필요', desc: '이상 데이터', color: 'bg-purple-400', countColor: 'text-purple-500' },
  { key: 'no_title', label: '제목 미수집', desc: '스크래핑 실패', color: 'bg-slate-400', countColor: 'text-slate-500' },
  { key: 'no_branch', label: '지점 미매핑', desc: '유앤아이 미연결', color: 'bg-sky-400', countColor: 'text-sky-500' },
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
  <div>
    <!-- 헤더 -->
    <div class="flex items-center justify-between mb-4">
      <div>
        <p class="text-xs text-slate-400">총 {{ summary?.total?.toLocaleString() ?? '-' }}건 기준</p>
      </div>
      <button @click="loadSummary" class="text-xs text-blue-600 hover:text-blue-800 px-2 py-1 rounded hover:bg-blue-50">
        새로고침
      </button>
    </div>

    <!-- 2열 레이아웃: 좌측 카테고리 + 우측 상세 -->
    <div class="flex gap-4" style="min-height: 500px;">

      <!-- 좌측: 품질 현황 카테고리 -->
      <div class="w-56 shrink-0 space-y-1">
        <button
          v-for="cat in categories"
          :key="cat.key"
          @click="selectCategory(cat.key)"
          :class="[
            'w-full flex items-center justify-between px-3 py-2.5 rounded-lg border transition text-left',
            activeCategory === cat.key
              ? 'border-blue-400 bg-blue-50'
              : 'border-slate-200 bg-white hover:bg-slate-50'
          ]"
        >
          <div class="flex items-center gap-2 min-w-0">
            <span class="w-2 h-2 rounded-full shrink-0" :class="cat.color"></span>
            <div class="min-w-0">
              <p class="text-xs font-medium text-slate-700 truncate">{{ cat.label }}</p>
              <p class="text-[10px] text-slate-400 truncate">{{ cat.desc }}</p>
            </div>
          </div>
          <span class="text-xs font-bold shrink-0 ml-2" :class="cat.countColor">
            {{ (summary?.[cat.key] ?? 0).toLocaleString() }}
          </span>
        </button>
      </div>

      <!-- 우측: 상세 테이블 -->
      <div class="flex-1 border border-slate-200 rounded-lg overflow-hidden bg-white">
        <!-- 헤더 -->
        <div class="px-4 py-2.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <span class="text-xs font-semibold text-slate-600">
            {{ categories.find(c => c.key === activeCategory)?.label }} 상세
          </span>
          <span v-if="details" class="text-xs text-slate-400">
            {{ details.total?.toLocaleString() }}건 중 {{ details.items?.length }}건 표시
          </span>
        </div>

        <!-- 로딩 -->
        <div v-if="loading" class="flex items-center justify-center py-16">
          <div class="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
          <span class="ml-2 text-sm text-slate-400">로딩 중...</span>
        </div>

        <!-- 테이블 -->
        <div v-else-if="details?.items?.length" class="overflow-auto" style="max-height: calc(500px - 41px);">
          <table class="w-full text-xs">
            <thead class="bg-slate-50 sticky top-0">
              <tr>
                <th class="text-left px-3 py-2 text-slate-500 font-medium w-12">채널</th>
                <th class="text-left px-3 py-2 text-slate-500 font-medium">제목 / 키워드</th>
                <th class="text-left px-3 py-2 text-slate-500 font-medium w-24">지점</th>
                <th class="text-left px-3 py-2 text-slate-500 font-medium w-20">날짜</th>
                <th class="text-left px-3 py-2 text-slate-500 font-medium w-14">상태</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-50">
              <tr v-for="item in details.items" :key="item.id" class="hover:bg-slate-50">
                <td class="px-3 py-2">
                  <span class="px-1.5 py-0.5 rounded-full text-[10px] font-medium" :class="channelClass(item.blog_channel)">
                    {{ channelLabel(item.blog_channel) }}
                  </span>
                </td>
                <td class="px-3 py-2">
                  <a v-if="item.published_url" :href="item.published_url" target="_blank"
                    class="text-slate-700 hover:text-blue-600 block truncate max-w-sm">
                    {{ item.title || item.keyword || '(없음)' }}
                  </a>
                  <span v-else class="text-slate-400 block truncate max-w-sm">
                    {{ item.title || item.keyword || '(없음)' }}
                  </span>
                </td>
                <td class="px-3 py-2 text-slate-400 truncate">{{ item.branch_name || '-' }}</td>
                <td class="px-3 py-2 text-slate-400">{{ item.published_at?.slice(0, 10) || '-' }}</td>
                <td class="px-3 py-2">
                  <span :class="statusClass(item)">{{ statusText(item) }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 빈 상태 -->
        <div v-else class="flex items-center justify-center py-16 text-sm text-slate-400">
          해당 항목 없음
        </div>
      </div>
    </div>
  </div>
</template>
