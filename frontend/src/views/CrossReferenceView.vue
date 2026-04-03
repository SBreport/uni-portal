<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api/client'

const route = useRoute()

// All catalog items (loaded on mount)
const allItems = ref<any[]>([])
const categories = ref<string[]>([])
const loadingAll = ref(false)

// Search / filter
const searchQuery = ref('')
const filterCategory = ref('')

// Detail
const selectedItem = ref<any>(null)
const crossData = ref<any>(null)
const loadingDetail = ref(false)

// Filtered items
const filteredItems = computed(() => {
  let items = allItems.value
  if (filterCategory.value) {
    items = items.filter(i => i.category === filterCategory.value)
  }
  if (searchQuery.value && searchQuery.value.length >= 1) {
    const q = searchQuery.value.toLowerCase()
    items = items.filter(i =>
      i.item_name?.toLowerCase().includes(q) ||
      i.display_name?.toLowerCase().includes(q) ||
      i.category?.toLowerCase().includes(q) ||
      i.sub_option?.toLowerCase().includes(q)
    )
  }
  return items
})

// Group by category
const groupedItems = computed(() => {
  const map: Record<string, any[]> = {}
  for (const item of filteredItems.value) {
    const cat = item.category || '미분류'
    if (!map[cat]) map[cat] = []
    map[cat].push(item)
  }
  return Object.entries(map).sort((a, b) => a[0].localeCompare(b[0]))
})

async function loadAll() {
  loadingAll.value = true
  try {
    const [itemsRes, catsRes] = await Promise.all([
      api.get('/treatment-catalog'),
      api.get('/treatment-catalog/categories'),
    ])
    allItems.value = itemsRes.data
    categories.value = catsRes.data
  } finally {
    loadingAll.value = false
  }
}

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

function goBack() {
  selectedItem.value = null
  crossData.value = null
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

onMounted(() => {
  loadAll()
  // 외부에서 쿼리 파라미터로 검색어 전달받기
  if (route.query.q) {
    searchQuery.value = route.query.q as string
  }
})
</script>

<template>
  <div class="max-w-3xl mx-auto py-2 px-4">

    <!-- ========== 목록 모드 ========== -->
    <div v-if="!selectedItem">
      <!-- 검색 + 필터 -->
      <div class="flex gap-3 mb-4">
        <div class="relative flex-1">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="시술명, 장비명 검색..."
            class="w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 pl-10"
          />
          <svg class="absolute left-3.5 top-3 w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
          </svg>
        </div>
        <select v-model="filterCategory" class="text-sm border rounded-xl px-3 py-2.5">
          <option value="">전체 카테고리</option>
          <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
        </select>
      </div>

      <!-- 카테고리별 테이블 -->
      <div v-if="groupedItems.length">
        <div v-for="[category, items] in groupedItems" :key="category" class="mb-5">
          <h4 class="text-sm font-semibold text-slate-600 mb-2 flex items-center gap-2">
            {{ category }}
            <span class="text-xs font-normal text-slate-400">{{ items.length }}건</span>
          </h4>
          <div class="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <table class="w-full text-sm">
              <thead>
                <tr class="bg-slate-50 text-left">
                  <th class="px-4 py-2 font-medium text-slate-500">시술/장비명</th>
                  <th class="px-4 py-2 font-medium text-slate-500">세부</th>
                  <th class="px-4 py-2 font-medium text-slate-500 text-center w-16">유형</th>
                  <th class="px-4 py-2 font-medium text-slate-500 text-center w-16">장비연결</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="item in items" :key="item.id"
                  @click="selectItem(item)"
                  class="border-t border-slate-100 hover:bg-blue-50 cursor-pointer transition"
                >
                  <td class="px-4 py-2 text-slate-800">{{ item.item_name }}</td>
                  <td class="px-4 py-2 text-slate-500 text-xs">{{ item.sub_option || '-' }}</td>
                  <td class="px-4 py-2 text-center">
                    <span :class="['text-xs px-1.5 py-0.5 rounded-full', typeLabels[item.item_type]?.color]">
                      {{ typeLabels[item.item_type]?.label }}
                    </span>
                  </td>
                  <td class="px-4 py-2 text-center text-xs">
                    <span v-if="item.device_id" class="text-green-500">O</span>
                    <span v-else class="text-slate-300">-</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- 데이터 없을 때 -->
      <div v-else-if="!loadingAll" class="text-center py-12">
        <p class="text-slate-400 text-sm mb-2">
          {{ searchQuery || filterCategory ? '검색 결과가 없습니다.' : '등록된 시술 카탈로그가 없습니다.' }}
        </p>
        <p class="text-slate-300 text-xs">
          시술 카탈로그에 데이터를 등록하면 여기서 크로스체크할 수 있습니다.
        </p>
      </div>

      <div v-if="loadingAll" class="text-center py-12 text-sm text-slate-400">로딩 중...</div>
    </div>

    <!-- ========== 상세 모드 ========== -->
    <div v-if="selectedItem">
      <button @click="goBack" class="text-sm text-blue-600 hover:underline mb-4">&larr; 목록으로</button>

      <!-- Loading -->
      <div v-if="loadingDetail" class="text-center py-12 text-sm text-slate-400">데이터 로딩 중...</div>

      <div v-if="crossData && !loadingDetail">
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

        <!-- No related data -->
        <div
          v-if="!crossData.device_info && !crossData.events.length && !crossData.papers.length && !crossData.blog_posts.length"
          class="p-6 bg-white rounded-xl border border-slate-200 text-center text-sm text-slate-400"
        >
          연결된 정보가 없습니다. 데이터가 축적되면 여기에 표시됩니다.
        </div>
      </div>
    </div>
  </div>
</template>
