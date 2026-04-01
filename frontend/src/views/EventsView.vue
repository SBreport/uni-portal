<script setup lang="ts">
import { onMounted } from 'vue'
import { useEventsStore } from '@/stores/events'
import DataTable from '@/components/common/DataTable.vue'
import { createColumnHelper, type CellContext } from '@tanstack/vue-table'
import { h } from 'vue'

const store = useEventsStore()
const col = createColumnHelper<any>()

onMounted(async () => {
  try { await store.loadAll() } catch (e) { console.error('[EventsView] 로드 실패:', e) }
})

function priceCell(info: CellContext<any, any>) {
  const v = info.getValue()
  if (v == null) return ''
  return Number(v).toLocaleString() + '원'
}

const columns = [
  col.accessor('지점명', { header: '지점', size: 80 }),
  col.accessor('카테고리', { header: '카테고리', size: 80 }),
  col.accessor('이벤트명', { header: '이벤트명', size: 320 }),
  col.accessor('회차', { header: '회차', size: 50 }),
  col.accessor('이벤트가', {
    header: '이벤트가',
    size: 95,
    cell: (info) => h('span', { class: 'text-red-600 font-semibold' }, priceCell(info)),
  }),
  col.accessor('정상가', {
    header: '정상가',
    size: 95,
    cell: priceCell,
  }),
  col.accessor('할인율', {
    header: '할인',
    size: 50,
    cell: (info) => info.getValue() ? Math.round(info.getValue()) + '%' : '',
  }),
  col.accessor('비고', {
    header: '비고',
    size: 100,
    cell: (info) => {
      const v = info.getValue() || ''
      return h('span', {
        class: 'block truncate max-w-[100px] cursor-default',
        title: v,
      }, v)
    },
  }),
]

function handlePriceInput(field: 'min' | 'max', e: Event) {
  const val = (e.target as HTMLInputElement).value
  const num = val ? parseInt(val) : null
  if (field === 'min') store.filterPriceMin = num
  else store.filterPriceMax = num
}
</script>

<template>
  <div class="p-5">
    <h2 class="text-xl font-bold text-slate-800 mb-4">
      이벤트
      <span v-if="store.isFallback" class="text-xs text-amber-500 font-normal ml-2">(이전 기간 데이터)</span>
    </h2>

    <!-- 필터 바 -->
    <div class="flex items-center gap-2.5 mb-4 flex-wrap">
      <select v-model="store.filterBranch"
        class="px-3 py-1.5 border border-slate-300 rounded-md text-sm bg-white">
        <option value="">전체 지점</option>
        <option v-for="b in store.branches" :key="b.id" :value="b.name">{{ b.name }}</option>
      </select>

      <select v-model="store.filterCategory"
        class="px-3 py-1.5 border border-slate-300 rounded-md text-sm bg-white">
        <option value="">전체 카테고리</option>
        <option v-for="c in store.categories" :key="c.id" :value="c.name">{{ c.name }}</option>
      </select>

      <input v-model="store.filterSearch" placeholder="이벤트명 검색"
        class="px-3 py-1.5 border border-slate-300 rounded-md text-sm w-40 focus:outline-none focus:ring-1 focus:ring-blue-400" />

      <input v-model="store.filterGlobal" placeholder="테이블 내 검색"
        class="px-3 py-1.5 border border-slate-300 rounded-md text-sm w-36 focus:outline-none focus:ring-1 focus:ring-blue-400" />

      <!-- 가격대 필터 -->
      <div class="flex items-center gap-1 text-sm text-slate-500">
        <input :value="store.filterPriceMin ?? ''" @input="handlePriceInput('min', $event)"
          type="number" placeholder="최소" min="0"
          class="w-20 px-2 py-1.5 border border-slate-300 rounded-md text-sm text-right focus:outline-none focus:ring-1 focus:ring-blue-400" />
        <span class="text-xs text-slate-400">만원</span>
        <span class="text-slate-300 px-0.5">~</span>
        <input :value="store.filterPriceMax ?? ''" @input="handlePriceInput('max', $event)"
          type="number" placeholder="최대" min="0"
          class="w-20 px-2 py-1.5 border border-slate-300 rounded-md text-sm text-right focus:outline-none focus:ring-1 focus:ring-blue-400" />
        <span class="text-xs text-slate-400">만원</span>
      </div>

      <span class="text-xs text-slate-400 ml-auto">{{ store.filteredEvents.length.toLocaleString() }}건</span>
      <span v-if="store.loading" class="text-xs text-slate-400">로딩 중...</span>
    </div>

    <!-- 테이블 -->
    <DataTable
      :data="store.filteredEvents"
      :columns="columns"
      :page-size="100"
      height="600px"
    />
  </div>
</template>
