<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getPublicReport } from '@/api/reports'
import { mergeReportData, type ReportData } from '@/components/reports/reportSchema'
import ResultContent from '@/components/reports/ResultContent.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

const route = useRoute()
const weekStart = route.params.weekStart as string

const loading = ref(true)
const error = ref('')
const title = ref('')
const periodLabel = ref('')
const data = ref<ReportData | null>(null)

function calcPeriodLabel(start: string, end: string): string {
  const fmt = (s: string) => s.replace(/-/g, '.').slice(0, 10)
  return `${fmt(start)} \u2013 ${fmt(end)}`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data: res } = await getPublicReport(weekStart)
    title.value = res.title || '주간 보고서'
    periodLabel.value = calcPeriodLabel(res.week_start, res.week_end)
    data.value = mergeReportData(res.data ?? {})
  } catch (e: any) {
    if (e.response?.status === 404) {
      error.value = '해당 주차 보고서를 찾을 수 없습니다.'
    } else if (e.response?.status === 400) {
      error.value = '잘못된 URL입니다.'
    } else {
      error.value = '보고서를 불러올 수 없습니다.'
    }
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="min-h-screen bg-slate-50 flex flex-col">
    <!-- 공개 헤더 -->
    <header class="bg-white border-b border-slate-200 px-5 py-3 shrink-0">
      <div class="max-w-4xl mx-auto flex items-center justify-between">
        <div>
          <div class="text-[10px] text-slate-400 tracking-wide">유앤아이의원</div>
          <div class="text-sm font-bold text-slate-800">주간 보고서</div>
        </div>
      </div>
    </header>

    <!-- 본문 -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <LoadingSpinner message="보고서 불러오는 중..." />
    </div>

    <div v-else-if="error" class="flex items-center justify-center py-20">
      <div class="text-center">
        <p class="text-sm text-slate-600 mb-2">{{ error }}</p>
        <p class="text-xs text-slate-400">담당자에게 새 링크를 요청해 주세요.</p>
      </div>
    </div>

    <div v-else-if="data" class="flex-1 overflow-hidden">
      <ResultContent
        :title="title"
        :period-label="periodLabel"
        :data="data"
        :show-anchor-nav="true"
      />
    </div>
  </div>
</template>
