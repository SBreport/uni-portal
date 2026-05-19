<script setup lang="ts">
import { ref } from 'vue'
import DataQualityContent from '@/components/admin/DataQualityContent.vue'
import MigrationPanel from '@/components/admin/MigrationPanel.vue'

type QualitySubTab = 'quality' | 'migration'
const activeSubTab = ref<QualitySubTab>('quality')

const subTabs = [
  { key: 'quality', label: '데이터 품질' },
  { key: 'migration', label: 'DB 마이그레이션' },
]
</script>

<template>
  <div class="h-full flex flex-col">
    <!-- 서브탭 헤더 -->
    <div class="shrink-0 flex gap-1 mb-4">
      <button
        v-for="tab in subTabs"
        :key="tab.key"
        @click="activeSubTab = tab.key as QualitySubTab"
        :class="[
          'px-3 py-1.5 text-xs rounded border transition',
          activeSubTab === tab.key
            ? 'bg-slate-700 text-white border-slate-700'
            : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
        ]"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- 서브탭 콘텐츠 -->
    <div class="flex-1 min-h-0 overflow-y-auto">
      <DataQualityContent v-if="activeSubTab === 'quality'" />
      <MigrationPanel v-if="activeSubTab === 'migration'" class="h-full" />
    </div>
  </div>
</template>
