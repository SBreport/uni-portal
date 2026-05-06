<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useBranchStore } from '@/stores/branches'
import UserManagement from '@/components/admin/UserManagement.vue'
import SyncSettings from '@/components/admin/SyncSettings.vue'
import DataQualityLog from '@/components/admin/DataQualityLog.vue'
import AgencyManagement from '@/components/admin/AgencyManagement.vue'
import RankChecker from '@/components/admin/RankChecker.vue'
import EncyclopediaAdmin from '@/components/admin/EncyclopediaAdmin.vue'
import TabBar from '@/components/common/TabBar.vue'

const branchStore = useBranchStore()
const route = useRoute()
type AdminTab = 'sync' | 'quality' | 'agency' | 'sb-checker' | 'encyclopedia' | 'users'
const activeTab = ref<AdminTab>('sync')
const branches = computed(() => branchStore.branches)

const tabs = [
  { key: 'sync', label: '데이터 동기화' },
  { key: 'quality', label: '데이터 로그' },
  { key: 'agency', label: '상위노출 관리' },
  { key: 'sb-checker', label: 'SB체커' },
  { key: 'encyclopedia', label: '백과사전 관리' },
  { key: 'users', label: '사용자 관리' },
]

const validTabKeys = tabs.map(t => t.key)

onMounted(() => {
  branchStore.loadBranches()
  const queryTab = route.query.tab
  if (typeof queryTab === 'string' && validTabKeys.includes(queryTab)) {
    activeTab.value = queryTab as AdminTab
  }
})
</script>

<template>
  <!-- height 체인: 부모(main)에서 h-screen 받아 flex-col로 분배 -->
  <div class="h-full flex flex-col p-5 overflow-hidden">
    <h2 class="text-xl font-bold text-slate-800 mb-4 shrink-0">관리자 모드</h2>

    <div class="shrink-0">
      <TabBar :model-value="activeTab" :tabs="tabs" @update:model-value="(v: string) => activeTab = v as AdminTab" />
    </div>

    <!-- 탭 콘텐츠 영역: 남은 공간 차지 + 자체 스크롤 (자식이 자체 처리하면 발동 안 함) -->
    <div class="flex-1 min-h-0 mt-4 overflow-y-auto">
      <SyncSettings v-if="activeTab === 'sync'" :branches="branches" />
      <DataQualityLog v-if="activeTab === 'quality'" />
      <AgencyManagement v-if="activeTab === 'agency'" :branches="branches" />
      <RankChecker v-if="activeTab === 'sb-checker'" :branches="branches" class="h-full" />
      <EncyclopediaAdmin v-if="activeTab === 'encyclopedia'" />
      <UserManagement v-if="activeTab === 'users'" :branches="branches" />
    </div>
  </div>
</template>
