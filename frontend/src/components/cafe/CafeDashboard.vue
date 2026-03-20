<script setup lang="ts">
import { onMounted, computed, h } from 'vue'
import { useCafeStore } from '@/stores/cafe'
import DataTable from '@/components/common/DataTable.vue'
import { createColumnHelper } from '@tanstack/vue-table'

const store = useCafeStore()
const col = createColumnHelper<any>()

onMounted(() => store.loadSummary())

const statusColors: Record<string, string> = {
  '작성대기': 'text-slate-400', '작성완료': 'text-amber-500', '수정요청': 'text-red-500',
  '검수완료': 'text-blue-500', '발행완료': 'text-emerald-500', '보류': 'text-purple-500',
}

const kpi = computed(() => {
  const s = store.summary
  const total = s.reduce((a: number, r: any) => a + (r.total || 0), 0)
  const published = s.reduce((a: number, r: any) => a + (r['발행완료'] || 0), 0)
  const pending = s.reduce((a: number, r: any) => a + (r['작성대기'] || 0), 0)
  const rate = total > 0 ? Math.round((published / total) * 100) : 0
  return { total, published, pending, rate, branches: s.length }
})

const statusFields = ['작성대기', '작성완료', '수정요청', '검수완료', '발행완료', '보류'] as const

const columns = [
  col.accessor('branch_name', { header: '지점', size: 90 }),
  col.accessor('smart_manager', { header: '담당자', size: 80 }),
  col.accessor('total', { header: '총건수', size: 65 }),
  ...statusFields.map(s =>
    col.accessor(s, {
      header: s,
      size: 70,
      cell: (info) => {
        const v = info.getValue()
        if (!v || v === 0) return h('span', { class: 'text-slate-200' }, '0')
        return h('span', { class: `font-semibold ${statusColors[s]}` }, v)
      },
    })
  ),
]
</script>

<template>
  <div>
    <!-- KPI 카드 -->
    <div class="grid grid-cols-5 gap-3 mb-5">
      <div v-for="item in [
        { label: '전체 원고', value: kpi.total, color: 'text-slate-700' },
        { label: '발행 완료', value: kpi.published, color: 'text-emerald-600' },
        { label: '미착수', value: kpi.pending, color: 'text-slate-400' },
        { label: '발행률', value: kpi.rate + '%', color: 'text-blue-600' },
        { label: '지점 수', value: kpi.branches, color: 'text-slate-500' },
      ]" :key="item.label"
        class="bg-white rounded-lg border border-slate-200 p-4"
      >
        <p class="text-xs text-slate-400">{{ item.label }}</p>
        <p class="text-2xl font-bold mt-1" :class="item.color">{{ item.value }}</p>
      </div>
    </div>

    <!-- 테이블 -->
    <DataTable
      :data="store.summary"
      :columns="columns"
      :page-size="50"
      height="500px"
    />
  </div>
</template>
