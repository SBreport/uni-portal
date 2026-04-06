<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useBranchStore } from '@/stores/branches'
import UserManagement from '@/components/admin/UserManagement.vue'
import SyncSettings from '@/components/admin/SyncSettings.vue'
import RankChecker from '@/components/admin/RankChecker.vue'
import EncyclopediaAdmin from '@/components/admin/EncyclopediaAdmin.vue'
import TabBar from '@/components/common/TabBar.vue'

const branchStore = useBranchStore()
const activeTab = ref<'users' | 'sync' | 'rank-checker' | 'encyclopedia'>('users')
const branches = computed(() => branchStore.branches)

const tabs = [
  { key: 'users', label: '사용자' },
  { key: 'sync', label: '데이터 동기화' },
  { key: 'rank-checker', label: 'SB체커' },
  { key: 'encyclopedia', label: '백과사전 관리' },
]

onMounted(() => branchStore.loadBranches())
</script>

<template>
  <div class="p-5">
    <h2 class="text-xl font-bold text-slate-800 mb-4">관리자 모드</h2>

    <TabBar :model-value="activeTab" :tabs="tabs" @update:model-value="(v: string) => activeTab = v as 'users' | 'sync' | 'rank-checker' | 'encyclopedia'" />

    <UserManagement v-if="activeTab === 'users'" :branches="branches" />
    <SyncSettings v-if="activeTab === 'sync'" :branches="branches" />
    <RankChecker v-if="activeTab === 'rank-checker'" :branches="branches" />
    <EncyclopediaAdmin v-if="activeTab === 'encyclopedia'" />
  </div>
</template>
