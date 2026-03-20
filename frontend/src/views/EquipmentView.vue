<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useEquipmentStore } from '@/stores/equipment'
import DataTable from '@/components/common/DataTable.vue'
import { createColumnHelper } from '@tanstack/vue-table'

const store = useEquipmentStore()
const col = createColumnHelper<any>()

onMounted(async () => {
  await Promise.all([store.loadBranches(), store.loadCategories()])
  await store.loadEquipment()
})

const columns = [
  col.accessor('지점', { header: '지점', size: 90 }),
  col.accessor('카테고리', { header: '카테고리', size: 90 }),
  col.accessor('기기명', { header: '장비명', size: 200 }),
  col.accessor('수량', { header: '수량', size: 55 }),
  col.accessor('사진', {
    header: '사진',
    size: 55,
    cell: (info) => info.getValue() === '있음' ? '✅' : '',
  }),
  col.accessor('비고', { header: '비고', size: 150 }),
]

function handleSearch() {
  store.loadEquipment()
}
</script>

<template>
  <div class="p-5 max-w-6xl">
    <h2 class="text-xl font-bold text-slate-800 mb-4">보유장비</h2>

    <!-- 필터 바 -->
    <div class="flex items-center gap-3 mb-4 flex-wrap">
      <select v-model="store.filterBranch" @change="handleSearch"
        class="px-3 py-1.5 border border-slate-300 rounded-md text-sm bg-white">
        <option value="">전체 지점</option>
        <option v-for="b in store.branches" :key="b.id" :value="b.name">{{ b.name }}</option>
      </select>

      <select v-model="store.filterCategory" @change="handleSearch"
        class="px-3 py-1.5 border border-slate-300 rounded-md text-sm bg-white">
        <option value="">전체 카테고리</option>
        <option v-for="c in store.categories" :key="c.id" :value="c.name">{{ c.name }}</option>
      </select>

      <input v-model="store.filterSearch" placeholder="장비명 검색"
        class="px-3 py-1.5 border border-slate-300 rounded-md text-sm w-48 focus:outline-none focus:ring-1 focus:ring-blue-400"
        @input="handleSearch" />
    </div>

    <!-- 테이블 -->
    <DataTable
      :data="store.rows"
      :columns="columns"
      :page-size="50"
      height="600px"
    />
  </div>
</template>
