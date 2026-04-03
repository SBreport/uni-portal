<script setup lang="ts">
import { ref, watch } from 'vue'
import api from '@/api/client'

// Search
const searchQuery = ref('')
const searchResults = ref<any[]>([])
const searching = ref(false)

// Detail
const selectedItem = ref<any>(null)
const crossData = ref<any>(null)
const loadingDetail = ref(false)

// Debounced search
let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(searchQuery, (q) => {
  if (searchTimer) clearTimeout(searchTimer)
  if (!q || q.length < 2) {
    searchResults.value = []
    return
  }
  searchTimer = setTimeout(async () => {
    searching.value = true
    try {
      const { data } = await api.get('/treatment-catalog/search', { params: { q } })
      searchResults.value = data
    } finally {
      searching.value = false
    }
  }, 300)
})

async function selectItem(item: any) {
  selectedItem.value = item
  loadingDetail.value = true
  try {
    const { data } = await api.get(`/treatment-catalog/${item.id}/crossref`)
    crossData.value = data
  } finally {
    loadingDetail.value = false
  }
}

const typeLabels: Record<string, { label: string; color: string }> = {
  device: { label: '장비', color: 'bg-purple-100 text-purple-700' },
  material: { label: '재료', color: 'bg-amber-100 text-amber-700' },
  method: { label: '시술법', color: 'bg-teal-100 text-teal-700' },
}

function formatPrice(p: number | null) {
  if (!p) return '-'
  return (p / 10000).toFixed(0) + '만원'
}
</script>

<template>
  <div class="max-w-3xl mx-auto py-6 px-4">
    <h2 class="text-xl font-bold text-slate-800 mb-2">크로스체크</h2>
    <p class="text-sm text-slate-400 mb-6">시술/장비를 검색하면 관련 장비정보, 이벤트, 논문, 콘텐츠를 한눈에 확인합니다.</p>

    <!-- Search Bar -->
    <div class="relative mb-6">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="시술명 또는 장비명 검색 (예: 포텐자, 보톡스, 울쎄라)"
        class="w-full border border-slate-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
      />
      <div v-if="searching" class="absolute right-4 top-3.5 text-xs text-slate-400">검색 중...</div>
    </div>

    <!-- Search Results -->
    <div v-if="searchResults.length && !selectedItem" class="space-y-1 mb-6">
      <div
        v-for="r in searchResults" :key="r.id"
        @click="selectItem(r)"
        class="p-3 bg-white rounded-lg border border-slate-200 cursor-pointer hover:border-blue-300 transition flex items-center justify-between"
      >
        <div>
          <span class="font-medium text-slate-800">{{ r.display_name }}</span>
          <span class="text-xs text-slate-400 ml-2">{{ r.category }}</span>
        </div>
        <span :class="['text-xs px-2 py-0.5 rounded-full', typeLabels[r.item_type]?.color]">
          {{ typeLabels[r.item_type]?.label }}
        </span>
      </div>
    </div>

    <!-- Cross Reference Detail -->
    <div v-if="crossData && selectedItem">
      <!-- Back button -->
      <button
        @click="selectedItem = null; crossData = null; searchResults = []"
        class="text-sm text-blue-600 hover:underline mb-4"
      >&larr; 검색으로 돌아가기</button>

      <!-- Header -->
      <div class="p-4 bg-white rounded-xl border border-slate-200 mb-4">
        <div class="flex items-center gap-3 mb-2">
          <h3 class="text-lg font-bold text-slate-800">{{ crossData.catalog.display_name }}</h3>
          <span :class="['text-xs px-2 py-0.5 rounded-full', typeLabels[crossData.catalog.item_type]?.color]">
            {{ typeLabels[crossData.catalog.item_type]?.label }}
          </span>
        </div>
        <div class="text-sm text-slate-500">
          카테고리: {{ crossData.catalog.category }}
          <span v-if="crossData.catalog.description" class="ml-4">{{ crossData.catalog.description }}</span>
        </div>
      </div>

      <!-- Device Info -->
      <div v-if="crossData.device_info" class="p-4 bg-white rounded-xl border border-slate-200 mb-4">
        <h4 class="text-sm font-semibold text-slate-700 mb-2">장비 정보</h4>
        <div class="text-sm text-slate-600 space-y-1">
          <p v-if="crossData.device_info.summary"><span class="text-slate-400">요약:</span> {{ crossData.device_info.summary }}</p>
          <p v-if="crossData.device_info.target"><span class="text-slate-400">타겟:</span> {{ crossData.device_info.target }}</p>
          <p v-if="crossData.device_info.mechanism"><span class="text-slate-400">원리:</span> {{ crossData.device_info.mechanism }}</p>
        </div>
        <!-- Branches that have this equipment -->
        <div v-if="crossData.equipment_branches.length" class="mt-3">
          <span class="text-xs text-slate-400">보유 지점 ({{ crossData.equipment_branches.length }}개):</span>
          <div class="flex flex-wrap gap-1 mt-1">
            <span
              v-for="eq in crossData.equipment_branches.slice(0, 15)" :key="eq.id"
              class="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded"
            >{{ eq.branch_name || eq.name }}</span>
            <span v-if="crossData.equipment_branches.length > 15" class="text-xs text-slate-400">
              +{{ crossData.equipment_branches.length - 15 }}개
            </span>
          </div>
        </div>
      </div>

      <!-- Events -->
      <div v-if="crossData.events.length" class="p-4 bg-white rounded-xl border border-slate-200 mb-4">
        <h4 class="text-sm font-semibold text-slate-700 mb-2">관련 이벤트 ({{ crossData.events.length }}건)</h4>
        <div class="space-y-2">
          <div v-for="ev in crossData.events" :key="ev.id" class="flex items-center justify-between text-sm">
            <div>
              <span class="text-slate-700">{{ ev.display_name || ev.raw_event_name }}</span>
              <span class="text-xs text-slate-400 ml-2">{{ ev.branch_name }}</span>
            </div>
            <div class="text-right">
              <span class="font-medium text-blue-600">{{ formatPrice(ev.event_price) }}</span>
              <span v-if="ev.regular_price" class="text-xs text-slate-400 line-through ml-1">{{ formatPrice(ev.regular_price) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Papers -->
      <div v-if="crossData.papers.length" class="p-4 bg-white rounded-xl border border-slate-200 mb-4">
        <h4 class="text-sm font-semibold text-slate-700 mb-2">관련 논문 ({{ crossData.papers.length }}건)</h4>
        <div class="space-y-2">
          <div v-for="p in crossData.papers" :key="p.id" class="text-sm">
            <div class="font-medium text-slate-700">{{ p.title_ko || p.title }}</div>
            <div class="text-xs text-slate-400">
              {{ p.authors }} | {{ p.journal }} {{ p.pub_year }}
              <span v-if="p.evidence_level" class="ml-2">근거수준 Lv.{{ p.evidence_level }}</span>
            </div>
            <p v-if="p.one_line_summary" class="text-xs text-slate-500 mt-0.5">{{ p.one_line_summary }}</p>
          </div>
        </div>
      </div>

      <!-- Blog Posts -->
      <div v-if="crossData.blog_posts.length" class="p-4 bg-white rounded-xl border border-slate-200 mb-4">
        <h4 class="text-sm font-semibold text-slate-700 mb-2">관련 블로그 ({{ crossData.blog_posts.length }}건)</h4>
        <div class="space-y-2">
          <div v-for="bp in crossData.blog_posts" :key="bp.id" class="text-sm flex items-center justify-between">
            <div>
              <span class="text-slate-700">{{ bp.title }}</span>
              <span class="text-xs text-slate-400 ml-2">{{ bp.author }}</span>
            </div>
            <a v-if="bp.published_url" :href="bp.published_url" target="_blank" class="text-xs text-blue-500 hover:underline">링크</a>
          </div>
        </div>
      </div>

      <!-- No data message -->
      <div
        v-if="!crossData.device_info && !crossData.events.length && !crossData.papers.length && !crossData.blog_posts.length"
        class="p-6 bg-white rounded-xl border border-slate-200 text-center text-sm text-slate-400"
      >
        연결된 정보가 없습니다. 데이터가 축적되면 여기에 표시됩니다.
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loadingDetail" class="text-center py-12 text-sm text-slate-400">
      데이터 로딩 중...
    </div>

    <!-- Initial state -->
    <div v-if="!searchQuery && !selectedItem" class="text-center py-16 text-sm text-slate-400">
      시술명 또는 장비명을 입력하여 크로스체크를 시작하세요.
    </div>
  </div>
</template>
