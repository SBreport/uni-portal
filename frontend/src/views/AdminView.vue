<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as equipApi from '@/api/equipment'
import UserManagement from '@/components/admin/UserManagement.vue'
import SyncSettings from '@/components/admin/SyncSettings.vue'
import RankChecker from '@/components/admin/RankChecker.vue'

const activeTab = ref<'users' | 'sync' | 'rank-checker'>('users')
const branches = ref<{ id: number; name: string }[]>([])

async function loadBranches() { branches.value = (await equipApi.getBranches()).data }
onMounted(loadBranches)
</script>

<template>
  <div class="p-5">
    <h2 class="text-xl font-bold text-slate-800 mb-4">관리자 모드</h2>

    <div class="flex gap-4 mb-5 border-b border-slate-200">
      <button v-for="tab in [
        { key: 'users', label: '사용자' },
        { key: 'sync', label: '데이터 동기화' },
        { key: 'rank-checker', label: 'SB체커' },
      ]" :key="tab.key"
        @click="activeTab = tab.key as any"
        :class="['pb-2 text-sm font-medium border-b-2 transition',
          activeTab === tab.key ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-400 hover:text-slate-600']"
      >{{ tab.label }}</button>
    </div>

    <UserManagement v-if="activeTab === 'users'" :branches="branches" />
    <SyncSettings v-if="activeTab === 'sync'" :branches="branches" />
    <RankChecker v-if="activeTab === 'rank-checker'" :branches="branches" />
  </div>
</template>
