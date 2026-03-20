<script setup lang="ts">
import { h } from 'vue'
import { useCafeStore } from '@/stores/cafe'
import DataTable from '@/components/common/DataTable.vue'
import { createColumnHelper } from '@tanstack/vue-table'

const emit = defineEmits<{ open: [id: number] }>()
const store = useCafeStore()
const col = createColumnHelper<any>()

const statusBg: Record<string, string> = {
  '작성대기': 'bg-slate-400', '작성완료': 'bg-amber-500', '수정요청': 'bg-red-500',
  '검수완료': 'bg-blue-500', '발행완료': 'bg-emerald-500', '보류': 'bg-purple-500',
}

const columns = [
  col.accessor('article_order', { header: '순번', size: 55 }),
  col.accessor('equipment_name', {
    header: '장비',
    size: 120,
    cell: (info) => h('span', { class: 'text-blue-700 font-medium' }, info.getValue() || '-'),
  }),
  col.accessor('title', {
    header: '제목',
    size: 300,
    cell: (info) => h('span', {
      class: 'text-slate-700 hover:text-blue-600 cursor-pointer',
    }, info.getValue() || '(미작성)'),
  }),
  col.accessor('status', {
    header: '상태',
    size: 80,
    cell: (info) => {
      const v = info.getValue() || '작성대기'
      return h('span', {
        class: `inline-block px-2 py-0.5 rounded text-xs font-semibold text-white ${statusBg[v] || 'bg-slate-400'}`,
      }, v)
    },
  }),
  col.accessor('published_url', {
    header: '링크',
    size: 50,
    cell: (info) => {
      const url = info.getValue()
      if (!url) return ''
      return h('a', {
        href: url, target: '_blank', class: 'text-blue-500 hover:text-blue-700',
        onClick: (e: Event) => e.stopPropagation(),
      }, '🔗')
    },
  }),
]

function handleRowClick(row: any) {
  if (row.id) emit('open', row.id)
}
</script>

<template>
  <div>
    <p v-if="!store.articles.length" class="text-sm text-slate-400 py-8 text-center">
      지점과 기간을 선택하면 원고 목록이 표시됩니다.
    </p>
    <DataTable
      v-else
      :data="store.articles"
      :columns="columns"
      :page-size="25"
      :on-row-click="handleRowClick"
      height="600px"
    />
  </div>
</template>
