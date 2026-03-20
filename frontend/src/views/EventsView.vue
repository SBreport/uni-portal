<script setup lang="ts">
import { onMounted } from 'vue'
import { useEventsStore } from '@/stores/events'
import DataTable from '@/components/common/DataTable.vue'
import { createColumnHelper, type CellContext } from '@tanstack/vue-table'
import { h } from 'vue'

const store = useEventsStore()
const col = createColumnHelper<any>()

onMounted(() => store.loadAll())

function priceCell(info: CellContext<any, any>) {
  const v = info.getValue()
  if (v == null) return ''
  return Number(v).toLocaleString() + '원'
}

const columns = [
  col.accessor('지점명', { header: '지점', size: 90 }),
  col.accessor('카테고리', { header: '카테고리', size: 90 }),
  col.accessor('이벤트명', { header: '이벤트명', size: 250 }),
  col.accessor('회차', { header: '회차', size: 55 }),
  col.accessor('이벤트가', {
    header: '이벤트가',
    size: 100,
    cell: (info) => h('span', { class: 'text-red-600 font-semibold' }, priceCell(info)),
  }),
  col.accessor('정상가', {
    header: '정상가',
    size: 100,
    cell: priceCell,
  }),
  col.accessor('할인율', {
    header: '할인율',
    size: 60,
    cell: (info) => info.getValue() ? Math.round(info.getValue()) + '%' : '',
  }),
  col.accessor('비고', { header: '비고', size: 150 }),
]
</script>

<template>
  <div class="p-5 max-w-7xl">
    <h2 class="text-xl font-bold text-slate-800 mb-4">
      이벤트
      <span v-if="store.isFallback" class="text-xs text-amber-500 font-normal ml-2">(이전 기간 데이터)</span>
    </h2>

    <!-- 필터 바 -->
    <div class="flex items-center gap-3 mb-4 flex-wrap">
      <select v-model="store.filterBranch" @change="store.loadAll()"
        class="px-3 py-1.5 border border-slate-300 rounded-md text-sm bg-white">
        <option value="">전체 지점</option>
        <option v-for="b in store.branches" :key="b.id" :value="b.name">{{ b.name }}</option>
      </select>

      <select v-model="store.filterCategory" @change="store.loadAll()"
        class="px-3 py-1.5 border border-slate-300 rounded-md text-sm bg-white">
        <option value="">전체 카테고리</option>
        <option v-for="c in store.categories" :key="c.id" :value="c.name">{{ c.name }}</option>
      </select>

      <input v-model="store.filterSearch" placeholder="이벤트명 검색"
        class="px-3 py-1.5 border border-slate-300 rounded-md text-sm w-48 focus:outline-none focus:ring-1 focus:ring-blue-400" />

      <span v-if="store.loading" class="text-xs text-slate-400">로딩 중...</span>
    </div>

    <!-- 테이블 -->
    <DataTable
      :data="store.filteredEvents"
      :columns="columns"
      :page-size="100"
      searchable
      search-placeholder="테이블 내 검색"
      height="600px"
    />
  </div>
</template>
