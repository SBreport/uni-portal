<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import { useCafeStore } from '@/stores/cafe'
import CafeDashboard from '@/components/cafe/CafeDashboard.vue'
import ArticleListV1 from '@/components/cafe/ArticleListV1.vue'
import ArticleListV2 from '@/components/cafe/ArticleListV2.vue'
import ArticleEditor from '@/components/cafe/ArticleEditor.vue'

const store = useCafeStore()

const subView = ref<'dashboard' | 'list' | 'editor' | 'publish'>('dashboard')
const selectedBranchId = ref<number | null>(null)
const selectedYear = ref(new Date().getFullYear())
const selectedMonth = ref(new Date().getMonth() + 1)
const selectedArticleId = ref<number | null>(null)
const listVersion = ref<'v1' | 'v2'>('v1')

onMounted(async () => {
  await Promise.all([store.loadPeriods(), store.loadBranches()])
  // 전체 지점 대시보드 기본 로드
  await store.loadSummary()
})

// 지점/기간 변경 시 데이터 로드
watch([selectedBranchId, selectedYear, selectedMonth], async ([branchId, year, month]) => {
  if (branchId && year && month) {
    await store.selectBranchPeriod(branchId, year, month)
  }
  // 지점 변경 시 대시보드도 갱신
  if (subView.value === 'dashboard') {
    await store.loadSummary()
  }
})

// 선택된 지점명
const publishBranchName = computed(() => {
  if (!selectedBranchId.value) return '전체'
  const b = store.branches.find(b => b.id === selectedBranchId.value)
  return b?.name || '—'
})

function openArticle(articleId: number) {
  selectedArticleId.value = articleId
  subView.value = 'editor'
}

// 대시보드에서 지점 클릭 → 해당 지점 원고 목록으로 이동
function goToBranch(branchName: string) {
  const branch = store.branches.find(b => b.name === branchName)
  if (branch) {
    selectedBranchId.value = branch.id
    subView.value = 'list'
  }
}
</script>

<template>
  <div class="p-5">
    <!-- 필터 바 -->
    <div class="flex items-center gap-4 mb-4">
      <div class="flex-1 max-w-xs">
        <label class="block text-xs text-slate-500 mb-1">지점</label>
        <select v-model="selectedBranchId" class="w-full px-3 py-1.5 border border-slate-300 rounded text-sm">
          <option :value="null">전체 지점</option>
          <option v-for="b in store.branches" :key="b.id" :value="b.id">{{ b.name }}</option>
        </select>
      </div>
      <div>
        <label class="block text-xs text-slate-500 mb-1">연도</label>
        <input v-model.number="selectedYear" type="number" min="2024" max="2030"
          class="w-24 px-3 py-1.5 border border-slate-300 rounded text-sm" />
      </div>
      <div>
        <label class="block text-xs text-slate-500 mb-1">월</label>
        <input v-model.number="selectedMonth" type="number" min="1" max="12"
          class="w-20 px-3 py-1.5 border border-slate-300 rounded text-sm" />
      </div>
    </div>

    <!-- 서브뷰 탭 -->
    <div class="flex gap-4 mb-5 border-b border-slate-200">
      <button v-for="tab in [
        { key: 'dashboard', label: '대시보드' },
        { key: 'list', label: '원고 목록' },
        { key: 'editor', label: '원고 작성' },
        { key: 'publish', label: '발행 결과' },
      ]" :key="tab.key"
        @click="subView = tab.key as any"
        :class="[
          'pb-2 text-sm font-medium border-b-2 transition',
          subView === tab.key
            ? 'border-blue-600 text-blue-600'
            : 'border-transparent text-slate-400 hover:text-slate-600'
        ]"
      >{{ tab.label }}</button>
    </div>

    <!-- 지점 미선택 시 안내 (원고 목록/작성은 지점 필요) -->
    <template v-if="!selectedBranchId && (subView === 'list' || subView === 'editor')">
      <div class="flex items-center justify-center h-48 bg-white border border-slate-200 rounded-lg">
        <p class="text-slate-400 text-sm">지점을 선택하면 원고를 조회할 수 있습니다.</p>
      </div>
    </template>

    <!-- 서브뷰 콘텐츠 -->
    <template v-else>
      <CafeDashboard v-if="subView === 'dashboard'" @go-branch="goToBranch" />
      <div v-else-if="subView === 'list'">
        <!-- V1/V2 전환 토글 -->
        <div class="flex items-center gap-1 mb-3 justify-end">
          <span class="text-[10px] text-slate-400 mr-1">레이아웃</span>
          <button
            @click="listVersion = 'v1'"
            :class="[
              'px-2 py-0.5 rounded text-[10px] font-medium border transition',
              listVersion === 'v1'
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-slate-400 border-slate-300 hover:border-blue-400'
            ]"
          >V1 2단</button>
          <button
            @click="listVersion = 'v2'"
            :class="[
              'px-2 py-0.5 rounded text-[10px] font-medium border transition',
              listVersion === 'v2'
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-slate-400 border-slate-300 hover:border-blue-400'
            ]"
          >V2 3컬럼</button>
        </div>
        <ArticleListV1 v-if="listVersion === 'v1'" @open="openArticle" />
        <ArticleListV2 v-else @open="openArticle" />
      </div>
      <ArticleEditor v-else-if="subView === 'editor'" :article-id="selectedArticleId" @back="subView = 'list'" />

      <!-- 발행 결과 -->
      <div v-else-if="subView === 'publish'" class="bg-white border border-slate-200 rounded-lg p-6">
        <h3 class="text-sm font-semibold text-slate-700 mb-4">발행 결과</h3>
        <template v-if="store.articles.length">
          <div class="overflow-auto" style="max-height: calc(100vh - 300px)">
            <table class="w-full text-xs">
              <thead class="bg-slate-50 sticky top-0">
                <tr class="border-b border-slate-200">
                  <th class="px-3 py-2 text-left font-semibold text-slate-500" style="width:80px">지점명</th>
                  <th class="px-3 py-2 text-left font-semibold text-slate-500" style="width:40px">#</th>
                  <th class="px-3 py-2 text-left font-semibold text-slate-500" style="width:90px">발행일</th>
                  <th class="px-3 py-2 text-left font-semibold text-slate-500" style="width:100px">카페명</th>
                  <th class="px-3 py-2 text-left font-semibold text-slate-500">발행링크</th>
                  <th class="px-3 py-2 text-left font-semibold text-slate-500" style="width:70px">유형</th>
                  <th class="px-3 py-2 text-left font-semibold text-slate-500">제목</th>
                  <th class="px-3 py-2 text-center font-semibold text-slate-500" style="width:70px">발행여부</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="a in store.articles" :key="a.id"
                  class="border-b border-slate-100 hover:bg-slate-50">
                  <td class="px-3 py-2 text-slate-700 font-medium">{{ publishBranchName }}</td>
                  <td class="px-3 py-2 text-slate-400 font-mono">{{ a.article_order }}</td>
                  <td class="px-3 py-2 text-slate-500">{{ a.published_at || '—' }}</td>
                  <td class="px-3 py-2 text-slate-500">{{ a.keyword || '—' }}</td>
                  <td class="px-3 py-2">
                    <a v-if="a.published_url" :href="a.published_url" target="_blank"
                      class="text-blue-500 hover:underline truncate block max-w-sm">
                      {{ a.published_url }}
                    </a>
                    <span v-else class="text-slate-300">—</span>
                  </td>
                  <td class="px-3 py-2 text-slate-500">{{ a.category || '—' }}</td>
                  <td class="px-3 py-2 text-slate-800">{{ a.title || '(미작성)' }}</td>
                  <td class="px-3 py-2 text-center">
                    <span v-if="a.published_url"
                      class="inline-block px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-700">발행</span>
                    <span v-else
                      class="inline-block px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-400">미발행</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
        <div v-else class="text-center py-12 text-slate-400 text-sm">
          지점을 선택하면 발행 결과를 확인할 수 있습니다.
        </div>
      </div>
    </template>
  </div>
</template>
