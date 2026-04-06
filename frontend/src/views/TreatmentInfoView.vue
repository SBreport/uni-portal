<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import * as equipApi from '@/api/equipment'
import api from '@/api/client'
import PapersView from '@/views/PapersView.vue'
import EncyclopediaView from '@/components/treatment/EncyclopediaView.vue'
import TabBar from '@/components/common/TabBar.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const isInternal = computed(() => auth.role === 'admin' || auth.role === 'editor')

// ── 탭: 시술카탈로그 / 시술논문 ──
const activeTab = ref<'encyclopedia' | 'catalog' | 'papers'>('encyclopedia')
const tabs = [
  { key: 'encyclopedia', label: '시술백과' },
  { key: 'catalog', label: '시술카탈로그' },
  { key: 'papers', label: '시술논문' },
]

// ── 카탈로그 뷰 모드: list(목록) / detail(크로스체크 상세) ──
const viewMode = ref<'list' | 'detail'>('list')

// ── 카탈로그 데이터 ──
const catalogItems = ref<any[]>([])
const catalogCategories = ref<string[]>([])
const catalogSearch = ref('')
const catalogFilter = ref('')
const catalogLoading = ref(false)

// ── 크로스체크 상세 ──
const selectedItem = ref<any>(null)
const crossData = ref<any>(null)
const loadingDetail = ref(false)

// 필터링
const filteredCatalog = computed(() => {
  let items = catalogItems.value
  if (catalogFilter.value) items = items.filter(i => i.category === catalogFilter.value)
  if (catalogSearch.value) {
    const q = catalogSearch.value.toLowerCase()
    items = items.filter(i =>
      i.item_name?.toLowerCase().includes(q) ||
      i.display_name?.toLowerCase().includes(q) ||
      i.sub_option?.toLowerCase().includes(q)
    )
  }
  return items
})

// 카테고리별 그룹
const catalogGrouped = computed(() => {
  const map: Record<string, any[]> = {}
  for (const item of filteredCatalog.value) {
    const cat = item.category || '미분류'
    if (!map[cat]) map[cat] = []
    map[cat].push(item)
  }
  return Object.entries(map).sort((a, b) => a[0].localeCompare(b[0]))
})

// 카테고리별 → 아이템명별 → 세부옵션 그룹핑
// "보톡스" → [{name: "보톡스", subs: ["턱","침샘","이마"...], items: [...]}]
const catalogCards = computed(() => {
  const result: Array<{
    category: string
    mainType: string
    groups: Array<{ name: string; subs: string[]; items: any[] }>
  }> = []

  for (const [cat, items] of catalogGrouped.value) {
    // 아이템명별 그룹
    const nameMap: Record<string, { subs: string[]; items: any[] }> = {}
    let mainType = ''
    for (const item of items) {
      if (!mainType) mainType = item.item_type
      const name = item.item_name
      if (!nameMap[name]) nameMap[name] = { subs: [], items: [] }
      if (item.sub_option) nameMap[name].subs.push(item.sub_option)
      nameMap[name].items.push(item)
    }

    const groups = Object.entries(nameMap).map(([name, data]) => ({
      name,
      subs: data.subs,
      items: data.items,
    }))

    result.push({ category: cat, mainType, groups })
  }
  return result
})

async function loadCatalog() {
  catalogLoading.value = true
  try {
    const [itemsRes, catsRes] = await Promise.all([
      api.get('/treatment-catalog'),
      api.get('/treatment-catalog/categories'),
    ])
    catalogItems.value = itemsRes.data
    catalogCategories.value = catsRes.data
  } finally {
    catalogLoading.value = false
  }
}

// 카탈로그 항목 클릭 → 크로스체크 상세
async function selectCatalogItem(item: any) {
  selectedItem.value = item
  viewMode.value = 'detail'
  // 히스토리에 상세 상태 추가 (브라우저 뒤로가기 대응)
  history.pushState({ treatmentDetail: true }, '')
  loadingDetail.value = true
  try {
    // catalog ID가 있으면 catalog 기반, 없으면 이름 기반
    if (item.id) {
      const { data } = await api.get(`/treatment-catalog/${item.id}/crossref`)
      crossData.value = data
    } else {
      const { data } = await api.get('/treatment-catalog/crossref-by-name', { params: { q: item.display_name || item.item_name } })
      crossData.value = data
    }
  } finally {
    loadingDetail.value = false
  }
}

// 이름으로 직접 크로스체크 (지점정보에서 연결)
async function searchByName(query: string) {
  selectedItem.value = { display_name: query, item_type: 'search' }
  viewMode.value = 'detail'
  history.pushState({ treatmentDetail: true }, '')
  loadingDetail.value = true
  try {
    const { data } = await api.get('/treatment-catalog/crossref-by-name', { params: { q: query } })
    crossData.value = data
  } finally {
    loadingDetail.value = false
  }
}

function goBackToList() {
  viewMode.value = 'list'
  selectedItem.value = null
  crossData.value = null
  externalHandled.value = false
  // URL에 쿼리가 남아있으면 제거
  if (route.query.q) {
    router.replace({ path: route.path })
  }
}

function formatPrice(p: number | null) {
  if (!p) return '-'
  return (p / 10000).toFixed(0) + '만원'
}

const typeLabels: Record<string, { label: string; color: string }> = {
  device: { label: '장비', color: 'bg-purple-100 text-purple-700' },
  material: { label: '재료', color: 'bg-amber-100 text-amber-700' },
  method: { label: '시술법', color: 'bg-teal-100 text-teal-700' },
}

// 외부 진입 처리 완료 플래그
const externalHandled = ref(false)

// 브라우저 뒤로가기(popstate) 감지 — 상세 모드면 목록으로 복귀
function handlePopState() {
  if (viewMode.value === 'detail') {
    viewMode.value = 'list'
    selectedItem.value = null
    crossData.value = null
  }
}

onMounted(async () => {
  window.addEventListener('popstate', handlePopState)
  loadCatalog()
  // 외부에서 쿼리 파라미터로 진입 (지점정보 → 크로스체크)
  if (route.query.q && !externalHandled.value) {
    const q = route.query.q as string
    externalHandled.value = true
    await searchByName(q)
    router.replace({ path: route.path })
  }
})

onUnmounted(() => {
  window.removeEventListener('popstate', handlePopState)
})
</script>

<template>
  <div class="p-5">
    <h2 class="text-xl font-bold text-slate-800 mb-4">시술정보</h2>

    <!-- 서브 탭 -->
    <TabBar :model-value="activeTab" :tabs="tabs" @update:model-value="(v) => { activeTab = v as any; viewMode = 'list' }" />

    <!-- ========== 시술백과 탭 ========== -->
    <EncyclopediaView v-if="activeTab === 'encyclopedia'" />

    <!-- ========== 시술카탈로그 탭 ========== -->
    <div v-if="activeTab === 'catalog'">

      <!-- 목록 모드 -->
      <div v-if="viewMode === 'list'" class="max-w-2xl">
        <!-- 검색 + 필터 -->
        <div class="flex gap-3 mb-4">
          <input
            v-model="catalogSearch"
            type="text"
            placeholder="시술명 검색..."
            class="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <select v-model="catalogFilter" class="text-sm border rounded-lg px-3 py-2">
            <option value="">전체 카테고리</option>
            <option v-for="c in catalogCategories" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>

        <!-- 카테고리별 카드 -->
        <div v-for="card in catalogCards" :key="card.category" class="mb-4">
          <div class="bg-white rounded-xl border border-slate-200 p-4">
            <!-- 카테고리 헤더 -->
            <div class="flex items-center justify-between mb-3">
              <h4 class="text-sm font-bold text-slate-800">{{ card.category }}</h4>
              <span :class="['text-xs px-2 py-0.5 rounded-full', typeLabels[card.mainType]?.color]">
                {{ typeLabels[card.mainType]?.label }}
              </span>
            </div>
            <!-- 아이템 나열 (클릭 가능한 태그) -->
            <div class="flex flex-wrap gap-1.5">
              <template v-for="group in card.groups" :key="group.name">
                <template v-if="group.subs.length">
                  <!-- 세부옵션 있음: 메인 태그 + 서브 태그들 -->
                  <span class="flex items-center gap-0.5">
                    <span
                      @click="selectCatalogItem(group.items[0])"
                      class="px-2 py-1 bg-slate-100 text-slate-700 rounded-lg text-xs font-medium hover:bg-blue-100 hover:text-blue-700 cursor-pointer transition"
                    >{{ group.name }}</span>
                    <span
                      v-for="(sub, idx) in group.subs" :key="sub"
                      @click="selectCatalogItem(group.items[idx])"
                      class="px-1.5 py-1 bg-slate-50 text-slate-500 rounded text-xs hover:bg-blue-50 hover:text-blue-600 cursor-pointer transition"
                    >{{ sub }}</span>
                  </span>
                </template>
                <template v-else>
                  <!-- 세부옵션 없음: 단일 태그 -->
                  <span
                    @click="selectCatalogItem(group.items[0])"
                    class="px-2.5 py-1 bg-slate-100 text-slate-700 rounded-lg text-xs font-medium hover:bg-blue-100 hover:text-blue-700 cursor-pointer transition"
                  >{{ group.name }}</span>
                </template>
              </template>
            </div>
          </div>
        </div>

        <p v-if="!catalogCards.length && !catalogLoading" class="text-center text-sm text-slate-400 py-8">
          {{ catalogSearch || catalogFilter ? '검색 결과가 없습니다.' : '등록된 카탈로그가 없습니다.' }}
        </p>
        <div v-if="catalogLoading" class="text-center py-8 text-sm text-slate-400">로딩 중...</div>
      </div>

      <!-- 상세 모드 (크로스체크) -->
      <div v-if="viewMode === 'detail'" class="max-w-3xl">
        <button @click="goBackToList" class="text-sm text-blue-600 hover:underline mb-4">&larr; 목록으로</button>

        <div v-if="loadingDetail" class="text-center py-12 text-sm text-slate-400">로딩 중...</div>

        <div v-if="crossData && !loadingDetail">
          <!-- 시술 상세 카드 (카탈로그 정보 + device_info 통합) -->
          <div class="p-5 bg-white rounded-xl border border-slate-200 mb-4">
            <!-- 제목 + 유형 배지 -->
            <div class="flex items-center gap-3 mb-3">
              <h3 class="text-lg font-bold text-slate-800">
                {{ crossData.catalog?.display_name || crossData.query || selectedItem?.display_name || '검색 결과' }}
              </h3>
              <span v-if="crossData.catalog?.item_type || selectedItem?.item_type"
                :class="['text-xs px-2 py-0.5 rounded-full', typeLabels[crossData.catalog?.item_type || selectedItem?.item_type]?.color]">
                {{ typeLabels[crossData.catalog?.item_type || selectedItem?.item_type]?.label }}
              </span>
            </div>

            <!-- 카탈로그 기본 정보 -->
            <div class="text-sm text-slate-500 space-y-1 mb-3">
              <p v-if="crossData.catalog?.category">카테고리: <span class="text-slate-700">{{ crossData.catalog.category }}</span></p>
              <p v-if="crossData.catalog?.sub_option">세부: <span class="text-slate-700">{{ crossData.catalog.sub_option }}</span></p>
              <p v-if="crossData.catalog?.description">설명: <span class="text-slate-700">{{ crossData.catalog.description }}</span></p>
            </div>

            <!-- device_info 상세 (있으면 표시) -->
            <div v-if="crossData.device_info" class="border-t border-slate-100 pt-3 text-sm text-slate-600 space-y-1">
              <p v-if="crossData.device_info.summary"><span class="text-slate-400">요약:</span> {{ crossData.device_info.summary }}</p>
              <p v-if="crossData.device_info.target"><span class="text-slate-400">적용 부위:</span> {{ crossData.device_info.target }}</p>
              <p v-if="crossData.device_info.mechanism"><span class="text-slate-400">작용 원리:</span> {{ crossData.device_info.mechanism }}</p>
              <p v-if="crossData.device_info.aliases"><span class="text-slate-400">별칭:</span> {{ crossData.device_info.aliases }}</p>
            </div>

            <!-- 보유 지점 -->
            <div v-if="crossData.equipment_branches?.length" class="border-t border-slate-100 pt-3 mt-3">
              <span class="text-xs text-slate-400">보유 지점 ({{ crossData.equipment_branches.length }}개):</span>
              <div class="flex flex-wrap gap-1 mt-1">
                <span v-for="eq in crossData.equipment_branches.slice(0, 15)" :key="eq.id"
                  class="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded">{{ eq.branch_name || eq.name }}</span>
                <span v-if="crossData.equipment_branches.length > 15" class="text-xs text-slate-400">+{{ crossData.equipment_branches.length - 15 }}개</span>
              </div>
            </div>
          </div>

          <!-- Events -->
          <div v-if="crossData.events?.length" class="p-4 bg-white rounded-xl border border-slate-200 mb-4">
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
          <div v-if="crossData.papers?.length" class="p-4 bg-white rounded-xl border border-slate-200 mb-4">
            <h4 class="text-sm font-semibold text-slate-700 mb-2">관련 논문 ({{ crossData.papers.length }}건)</h4>
            <div class="space-y-2">
              <div v-for="p in crossData.papers" :key="p.id" class="text-sm">
                <div class="font-medium text-slate-700">{{ p.title_ko || p.title }}</div>
                <div class="text-xs text-slate-400">
                  {{ p.authors }} | {{ p.journal }} {{ p.pub_year }}
                  <span v-if="p.evidence_level" class="ml-2">근거수준 Lv.{{ p.evidence_level }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Blog Posts -->
          <div v-if="crossData.blog_posts?.length" class="p-4 bg-white rounded-xl border border-slate-200 mb-4">
            <h4 class="text-sm font-semibold text-slate-700 mb-2">관련 블로그 ({{ crossData.blog_posts.length }}건)</h4>
            <div class="space-y-2">
              <div v-for="bp in crossData.blog_posts" :key="bp.id" class="text-sm flex items-center gap-3">
                <a v-if="bp.published_url" :href="bp.published_url" target="_blank" class="text-blue-500 hover:underline shrink-0">링크</a>
                <span class="text-slate-700 min-w-0 truncate">{{ bp.title || '(제목 없음)' }}</span>
                <span v-if="isInternal && bp.author" class="text-xs text-slate-400 shrink-0">{{ bp.author }}</span>
              </div>
            </div>
          </div>

          <!-- No data -->
          <div v-if="!crossData.device_info && !crossData.events?.length && !crossData.papers?.length && !crossData.blog_posts?.length"
            class="p-6 bg-white rounded-xl border border-slate-200 text-center text-sm text-slate-400">
            연결된 정보가 없습니다. 데이터가 축적되면 여기에 표시됩니다.
          </div>
        </div>
      </div>
    </div>

    <!-- ========== 시술논문 탭 ========== -->
    <div v-if="activeTab === 'papers'">
      <PapersView />
    </div>
  </div>
</template>
