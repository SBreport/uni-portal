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
  <div class="p-5">
    <h2 class="text-xl font-bold text-slate-800 mb-4">관리자 모드</h2>

    <TabBar :model-value="activeTab" :tabs="tabs" @update:model-value="(v: string) => activeTab = v as AdminTab" />

    <SyncSettings v-if="activeTab === 'sync'" :branches="branches" />
    <DataQualityLog v-if="activeTab === 'quality'" />
    <AgencyManagement v-if="activeTab === 'agency'" :branches="branches" />
    <RankChecker v-if="activeTab === 'sb-checker'" :branches="branches" />
    <EncyclopediaAdmin v-if="activeTab === 'encyclopedia'" />
    <UserManagement v-if="activeTab === 'users'" :branches="branches" />

  </div>
</template>
