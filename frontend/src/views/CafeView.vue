<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useCafeStore } from '@/stores/cafe'
import CafeDashboard from '@/components/cafe/CafeDashboard.vue'
import ArticleList from '@/components/cafe/ArticleList.vue'
import ArticleEditor from '@/components/cafe/ArticleEditor.vue'

const store = useCafeStore()

const subView = ref<'dashboard' | 'list' | 'editor'>('dashboard')
const selectedBranchId = ref<number | null>(null)
const selectedYear = ref(new Date().getFullYear())
const selectedMonth = ref(new Date().getMonth() + 1)
const selectedArticleId = ref<number | null>(null)

onMounted(async () => {
  await Promise.all([store.loadPeriods(), store.loadBranches()])
})

// 지점/기간 변경 시 데이터 로드
watch([selectedBranchId, selectedYear, selectedMonth], async ([branchId, year, month]) => {
  if (branchId && year && month) {
    await store.selectBranchPeriod(branchId, year, month)
  }
})

function openArticle(articleId: number) {
  selectedArticleId.value = articleId
  subView.value = 'editor'
}
</script>

<template>
  <div class="p-5">
    <!-- 필터 바 -->
    <div class="flex items-center gap-4 mb-4">
      <div class="flex-1 max-w-xs">
        <label class="block text-xs text-slate-500 mb-1">지점</label>
        <select v-model="selectedBranchId" class="w-full px-3 py-1.5 border border-slate-300 rounded text-sm">
          <option :value="null" disabled>지점 선택</option>
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

    <!-- 서브뷰 콘텐츠 -->
    <CafeDashboard v-if="subView === 'dashboard'" />
    <ArticleList v-else-if="subView === 'list'" @open="openArticle" />
    <ArticleEditor v-else-if="subView === 'editor'" :article-id="selectedArticleId" @back="subView = 'list'" />
  </div>
</template>
