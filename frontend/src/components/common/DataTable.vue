<script setup lang="ts">
import { computed } from 'vue'
import {
  useVueTable,
  getCoreRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  getFilteredRowModel,
  FlexRender,
  type ColumnDef,
  type SortingState,
} from '@tanstack/vue-table'
import { ref } from 'vue'

const props = withDefaults(defineProps<{
  data: any[]
  columns: ColumnDef<any, any>[]
  pageSize?: number
  searchable?: boolean
  searchPlaceholder?: string
  onRowClick?: (row: any) => void
  stickyHeader?: boolean
  height?: string
}>(), {
  pageSize: 50,
  searchable: false,
  searchPlaceholder: '검색...',
  stickyHeader: true,
  height: '650px',
})

const sorting = ref<SortingState>([])
const globalFilter = ref('')

const table = useVueTable({
  get data() { return props.data },
  get columns() { return props.columns },
  state: {
    get sorting() { return sorting.value },
    get globalFilter() { return globalFilter.value },
  },
  onSortingChange: (updater) => {
    sorting.value = typeof updater === 'function' ? updater(sorting.value) : updater
  },
  onGlobalFilterChange: (updater) => {
    globalFilter.value = typeof updater === 'function' ? updater(globalFilter.value) : updater
  },
  getCoreRowModel: getCoreRowModel(),
  getSortedRowModel: getSortedRowModel(),
  getPaginationRowModel: getPaginationRowModel(),
  getFilteredRowModel: getFilteredRowModel(),
  initialState: {
    pagination: { pageSize: props.pageSize },
  },
})

const pageInfo = computed(() => {
  const state = table.getState()
  const totalRows = table.getFilteredRowModel().rows.length
  const start = state.pagination.pageIndex * state.pagination.pageSize + 1
  const end = Math.min(start + state.pagination.pageSize - 1, totalRows)
  return { start, end, total: totalRows }
})
</script>

<template>
  <div class="flex flex-col gap-3">
    <!-- 검색 + 건수 -->
    <div v-if="searchable" class="flex items-center gap-3">
      <input
        v-model="globalFilter"
        :placeholder="searchPlaceholder"
        class="px-3 py-1.5 border border-slate-300 rounded-md text-sm w-56 focus:outline-none focus:ring-1 focus:ring-blue-400"
      />
      <span class="text-xs text-slate-400 ml-auto">{{ pageInfo.total }}건</span>
    </div>
    <div v-else class="flex justify-end">
      <span class="text-xs text-slate-400">{{ pageInfo.total }}건</span>
    </div>

    <!-- 테이블 -->
    <div class="border border-slate-200 rounded-lg overflow-hidden" :style="{ maxHeight: height }">
      <div class="overflow-auto" :style="{ maxHeight: height }">
        <table class="w-full text-sm">
          <thead :class="stickyHeader ? 'sticky top-0 z-10' : ''">
            <tr v-for="headerGroup in table.getHeaderGroups()" :key="headerGroup.id">
              <th
                v-for="header in headerGroup.headers"
                :key="header.id"
                :style="{ width: header.getSize() !== 150 ? `${header.getSize()}px` : undefined }"
                class="bg-slate-50 border-b border-slate-200 px-3 py-2.5 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider select-none"
                :class="header.column.getCanSort() ? 'cursor-pointer hover:bg-slate-100' : ''"
                @click="header.column.getToggleSortingHandler()?.($event)"
              >
                <div class="flex items-center gap-1">
                  <FlexRender :render="header.column.columnDef.header" :props="header.getContext()" />
                  <span v-if="header.column.getIsSorted() === 'asc'" class="text-blue-500">↑</span>
                  <span v-else-if="header.column.getIsSorted() === 'desc'" class="text-blue-500">↓</span>
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in table.getRowModel().rows"
              :key="row.id"
              class="border-b border-slate-100 transition-colors"
              :class="onRowClick ? 'cursor-pointer hover:bg-blue-50' : 'hover:bg-slate-50'"
              @click="onRowClick?.(row.original)"
            >
              <td
                v-for="cell in row.getVisibleCells()"
                :key="cell.id"
                class="px-3 py-2 text-slate-700"
              >
                <FlexRender :render="cell.column.columnDef.cell" :props="cell.getContext()" />
              </td>
            </tr>
            <tr v-if="table.getRowModel().rows.length === 0">
              <td :colspan="columns.length" class="px-3 py-8 text-center text-slate-400">
                데이터가 없습니다
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 페이지네이션 -->
    <div v-if="pageInfo.total > pageSize" class="flex items-center justify-between text-xs text-slate-500">
      <span>{{ pageInfo.start }}-{{ pageInfo.end }} / {{ pageInfo.total }}</span>
      <div class="flex items-center gap-1">
        <button
          :disabled="!table.getCanPreviousPage()"
          class="px-2.5 py-1 rounded border border-slate-300 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed"
          @click="table.previousPage()"
        >이전</button>
        <span class="px-2">{{ table.getState().pagination.pageIndex + 1 }} / {{ table.getPageCount() }}</span>
        <button
          :disabled="!table.getCanNextPage()"
          class="px-2.5 py-1 rounded border border-slate-300 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed"
          @click="table.nextPage()"
        >다음</button>
      </div>
    </div>
  </div>
</template>
